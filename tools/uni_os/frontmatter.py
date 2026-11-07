"""A tiny reader for Markdown frontmatter (the ``---`` properties block).

Only the YAML subset the vault uses is supported: ``key: value`` lines with
plain, quoted, integer, boolean or ``[a, b]`` inline-list values, and block lists
(``key:`` followed by ``  - item`` lines). Nested maps are skipped. This is
enough for doctor contract checks and for reading role/skill metadata without a
YAML dependency.
"""

from __future__ import annotations

import re
from typing import Any

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.*)$")


def split(text: str) -> tuple[str | None, str]:
    """Return ``(frontmatter_text, body)``; frontmatter is ``None`` if absent."""
    if text.startswith("﻿"):
        text = text[1:]
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :])
    return None, text


def _scalar(value: str) -> Any:
    value = value.strip()
    if " #" in value and not value.startswith(("\"", "'")):
        value = value.split(" #", 1)[0].rstrip()
    if not value:
        return ""
    if (value[0] == value[-1]) and value[0] in "\"'" and len(value) >= 2:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",")]
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.match(r"^-?\d+$", value):
        return int(value)
    return value


def parse(text: str) -> dict:
    """Parse the frontmatter of a Markdown document (empty dict if there is none)."""
    fm, _ = split(text)
    if fm is None:
        return {}
    data: dict[str, Any] = {}
    current: str | None = None  # key whose value may continue as a block list
    for raw in fm.split("\n"):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        if current and (stripped.startswith("- ") or stripped == "-"):
            if not isinstance(data.get(current), list):
                data[current] = []
            data[current].append(_scalar(stripped[2:]) if len(stripped) > 1 else "")
            continue
        if line != stripped:  # nested mapping content we do not model
            continue
        m = _KEY_RE.match(line)
        if not m:
            current = None
            continue
        key, value = m.group(1), m.group(2)
        if value.strip() == "":
            data[key] = ""  # becomes a list if "- item" lines follow
            current = key
        else:
            data[key] = _scalar(value)
            current = None
    return data


def headings(text: str) -> list[str]:
    """All Markdown ATX headings (``# ...``) of the body, outside fenced code blocks."""
    _, body = split(text)
    out = []
    fenced = False
    for line in body.split("\n"):
        if line.strip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced and re.match(r"^#{1,6}\s", line):
            out.append(line.rstrip())
    return out


def set_value(text: str, key: str, value: str) -> tuple[str, bool]:
    """Replace ``key: ...`` inside the frontmatter. Returns ``(text, changed)``."""
    fm, body = split(text)
    if fm is None:
        return text, False
    lines = fm.split("\n")
    changed = False
    for idx, line in enumerate(lines):
        m = _KEY_RE.match(line)
        if m and m.group(1) == key:
            new = f"{key}: {value}"
            if line != new:
                lines[idx] = new
                changed = True
            break
    if not changed:
        return text, False
    bom = "﻿" if text.startswith("﻿") else ""
    return f"{bom}---\n" + "\n".join(lines) + "\n---\n" + body, True
