"""Comment-preserving edit of ``[modules] enabled`` in a TOML file.

``uni-os enable`` / ``disable`` (and ``init --modules``) must change one value in
the user's hand-written, commented config without touching anything else.
Python's stdlib can read TOML but not write it, so this module rewrites only the
text of that one array and verifies the result by parsing it again.
"""

from __future__ import annotations

import re
import tomllib

from .errors import ConfigError

_HEADER_RE = re.compile(r"^[ \t]*\[[ \t]*modules[ \t]*\][ \t]*(#.*)?$")
_ANY_HEADER_RE = re.compile(r"^[ \t]*\[\[?[ \t]*[A-Za-z0-9_\-.\"' ]+[ \t]*\]\]?[ \t]*(#.*)?$")
_KEY_RE = re.compile(r"^[ \t]*enabled[ \t]*=[ \t]*")


def format_array(values: list[str], indent: str = "") -> str:
    """TOML array text: inline for up to three ids, otherwise one id per line."""
    quoted = [f'"{v}"' for v in values]
    if len(values) <= 3:
        return "[" + ", ".join(quoted) + "]"
    inner = "".join(f"{indent}  {q},\n" for q in quoted)
    return "[\n" + inner + indent + "]"


def _array_end(text: str, start: int) -> int:
    """Index just after the array value starting at ``text[start] == '['``."""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "#":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue
        if ch in "\"'":
            triple = text[i : i + 3] == ch * 3
            if triple:
                end = text.find(ch * 3, i + 3)
                if end == -1:
                    raise ConfigError("unterminated string in [modules] enabled")
                i = end + 3
                continue
            j = i + 1
            while j < n and text[j] != ch:
                if ch == '"' and text[j] == "\\":
                    j += 1
                j += 1
            i = j + 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ConfigError("unterminated array in [modules] enabled")


def _value_end(text: str, start: int) -> int:
    """End of a non-array value (to the end of the line, before a comment)."""
    nl = text.find("\n", start)
    return len(text) if nl == -1 else nl


def set_modules_enabled(text: str, values: list[str]) -> str:
    """Return ``text`` with ``[modules] enabled`` set to ``values``.

    Adds a ``[modules]`` table at the end if there is none. Raises
    :class:`ConfigError` if the file uses a layout this editor cannot handle
    (then the user edits the line by hand).
    """
    lines = text.split("\n")
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1

    header_idx = next((i for i, line in enumerate(lines) if _HEADER_RE.match(line)), None)
    if header_idx is None:
        sep = "" if text.endswith("\n") or not text else "\n"
        new_text = text + sep + "\n[modules]\nenabled = " + format_array(values) + "\n"
    else:
        end_idx = len(lines)
        for i in range(header_idx + 1, len(lines)):
            if _ANY_HEADER_RE.match(lines[i]):
                end_idx = i
                break
        key_idx = None
        for i in range(header_idx + 1, end_idx):
            if _KEY_RE.match(lines[i]):
                key_idx = i
                break
        if key_idx is None:
            insert_at = offsets[header_idx] + len(lines[header_idx]) + 1
            insert_at = min(insert_at, len(text))
            addition = "enabled = " + format_array(values) + "\n"
            if insert_at == len(text) and not text.endswith("\n"):
                addition = "\n" + addition
            new_text = text[:insert_at] + addition + text[insert_at:]
        else:
            m = _KEY_RE.match(lines[key_idx])
            value_start = offsets[key_idx] + m.end()
            if value_start < len(text) and text[value_start] == "[":
                value_end = _array_end(text, value_start)
            else:
                value_end = _value_end(text, value_start)
            new_text = text[:value_start] + format_array(values) + text[value_end:]

    try:
        parsed = tomllib.loads(new_text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"could not update modules.enabled automatically ({exc})", hint="edit [modules] enabled by hand") from None
    got = (parsed.get("modules") or {}).get("enabled")
    if got != list(values):
        raise ConfigError("could not update modules.enabled automatically", hint="edit [modules] enabled by hand")
    try:
        before = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        before = None
    if before is not None:
        before.setdefault("modules", {})
        if isinstance(before["modules"], dict):
            before["modules"]["enabled"] = list(values)
        if before != parsed:
            raise ConfigError("updating modules.enabled would change other settings; refusing", hint="edit [modules] enabled by hand")
    return new_text
