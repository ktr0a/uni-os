"""Job definitions: ``job.conf`` parsing and the list of installed jobs.

A job is a folder ``<vault>/_agent/jobs/<job-id>/`` with a ``job.conf`` (shell-style
``KEY="value"`` lines, also sourced by bash on the VM) and, for agent jobs, a
``prompt.md``. Hosts (the laptop scheduler, the VM runner) read jobs from there.

``parse_conf`` follows bash quoting rules closely enough for these files:
``KEY="double"`` (backslash escapes ``\\" \\\\ \\$ \\```), ``KEY='single'`` (literal),
``KEY=bare``, concatenations like ``KEY="a"'b'``, values spanning lines inside
quotes, ``export KEY=...`` (the ``export`` keyword is ignored for the value;
exported names are reported separately), comments (``#`` at the start of a word).
``$VAR`` and ``$(...)`` are kept literally (no expansion).

A job whose folder contains a file named ``DISABLED`` belongs to a disabled
module (``uni-os disable``); hosts must skip it. ``list_jobs`` hides such jobs
unless ``include_disabled=True``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .config import DAYS, TIME_RE

DISABLED_MARKER = "DISABLED"

#: Defaults of every job.conf key (the key table in ``docs/file-formats.md``, section
#: "job.conf"); TITLE defaults to the job id.
JOB_DEFAULTS: dict[str, str] = {
    "TITLE": "",
    "KIND": "agent",
    "COMMAND": "",
    "SLOTS": "",
    "EVERY_MIN": "",  # contract addition: fixed polling interval (scheduler-local, vm runner)
    "DAYS": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
    "DATES": "",
    "SCHEDULE": "",
    "SESSION": "print",
    "KEEP_H": "8",
    "MODEL": "",
    "EFFORT": "high",
    "TIMEOUT_MIN": "45",
    "NEEDS_VAULT": "yes",
    "PRECHECK": "",
    "QUIET_OK": "no",
    "DRY_OK": "no",
    "NOTIFY_DONE": "",
    "NOTIFY_GATE": "",
    "AGENT_LOCK": "shared",
    "LOCK_WAIT_MIN": "20",
    "LAPTOP_TASK": "",
    "FAILOVER_DELAY_MIN": "25",
    "MARKER": "yes",
    "RUNTIME": "any",
    "DEFAULT_MODE": "off",
}

ENUM_KEYS: dict[str, tuple[str, ...]] = {
    "KIND": ("agent", "command"),
    "SESSION": ("print", "rc"),
    "AGENT_LOCK": ("shared", "exclusive", "none"),
    "RUNTIME": ("any", "laptop", "vm"),
    "DEFAULT_MODE": ("off", "always", "failover"),
    "NEEDS_VAULT": ("yes", "no"),
    "QUIET_OK": ("yes", "no"),
    "DRY_OK": ("yes", "no"),
    "MARKER": ("yes", "no"),
}
INT_KEYS = ("KEEP_H", "TIMEOUT_MIN", "LOCK_WAIT_MIN", "FAILOVER_DELAY_MIN")

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DATES_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(\.\.\d{4}-\d{2}-\d{2})?$")


class ConfParseError(ValueError):
    """A job.conf line could not be parsed."""


def _read_word(text: str, i: int, line_no: list[int]) -> tuple[str, int]:
    """Read one shell word starting at ``i``; returns (value, index after word)."""
    out: list[str] = []
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t":
            break
        if ch == "\n":
            break
        if ch == "'":
            end = text.find("'", i + 1)
            if end == -1:
                raise ConfParseError(f"line {line_no[0]}: unterminated single quote")
            segment = text[i + 1 : end]
            line_no[0] += segment.count("\n")
            out.append(segment)
            i = end + 1
            continue
        if ch == '"':
            i += 1
            while True:
                if i >= n:
                    raise ConfParseError(f"line {line_no[0]}: unterminated double quote")
                c = text[i]
                if c == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    if nxt in '"\\$`':
                        out.append(nxt)
                        i += 2
                        continue
                    if nxt == "\n":
                        line_no[0] += 1
                        i += 2
                        continue
                    out.append(c)
                    i += 1
                    continue
                if c == '"':
                    i += 1
                    break
                if c == "\n":
                    line_no[0] += 1
                out.append(c)
                i += 1
            continue
        if ch == "\\" and i + 1 < n:
            if text[i + 1] == "\n":
                line_no[0] += 1
                i += 2
                continue
            out.append(text[i + 1])
            i += 2
            continue
        if ch == "$" and text.startswith("$(", i):
            depth = 0
            j = i
            while j < n:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append(text[i : j + 1])
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), i


def parse_conf_text(text: str) -> tuple[dict[str, str], set[str]]:
    """Parse job.conf text into ``(values, exported_names)``."""
    values: dict[str, str] = {}
    exported: set[str] = set()
    text = text.replace("\r\n", "\n")
    i = 0
    n = len(text)
    line_no = [1]
    while i < n:
        # skip blank space at line start
        while i < n and text[i] in " \t":
            i += 1
        if i >= n:
            break
        if text[i] == "\n":
            line_no[0] += 1
            i += 1
            continue
        if text[i] == "#":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue
        is_export = False
        if text.startswith("export", i) and i + 6 < n and text[i + 6] in " \t":
            is_export = True
            i += 6
            while i < n and text[i] in " \t":
                i += 1
        m = _NAME_RE.match(text, i)
        if not m or m.end() >= n or text[m.end()] != "=":
            if is_export and m:
                exported.add(m.group(0))
            nl = text.find("\n", i)  # not an assignment: ignore the line
            i = n if nl == -1 else nl
            continue
        name = m.group(0)
        value, i = _read_word(text, m.end() + 1, line_no)
        values[name] = value
        if is_export:
            exported.add(name)
        # rest of the line: whitespace and an optional comment
        while i < n and text[i] in " \t":
            i += 1
        if i < n and text[i] not in "\n#":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
    return values, exported


def parse_conf(path_or_text: str | Path, *, with_exports: bool = False):
    """Parse a job.conf file (path) or its text.

    Returns ``{KEY: value}``; with ``with_exports=True`` returns
    ``(values, exported_names)``.
    """
    if isinstance(path_or_text, Path):
        is_path = True
    else:
        text_arg = str(path_or_text)
        is_path = "\n" not in text_arg and (os.path.isfile(text_arg) or "=" not in text_arg)
    text = paths.read_text(Path(path_or_text)) if is_path else str(path_or_text)
    values, exported = parse_conf_text(text)
    return (values, exported) if with_exports else values


def split_list(value: str) -> list[str]:
    """``"07:15, 13:15"`` or ``"Mon,Tue Wed"`` -> list of items."""
    return [p for p in re.split(r"[,\s]+", value or "") if p]


_DAY_RANGE_RE = re.compile(r"^([A-Za-z]{3})(?:\.\.|-)([A-Za-z]{3})$")


def bad_days(value: str) -> list[str]:
    """DAYS tokens that are neither a day (``Mon``) nor a range (``Mon..Fri`` / ``Mon-Fri``)."""
    bad = []
    for tok in split_list(value):
        m = _DAY_RANGE_RE.match(tok)
        names = [m.group(1), m.group(2)] if m else [tok]
        if any(n not in DAYS for n in names):
            bad.append(tok)
    return bad


def expand_days(value: str) -> list[str]:
    """``"Mon..Wed,Fri"`` -> ``["Mon", "Tue", "Wed", "Fri"]`` in week order.

    Empty means every day (both host runners read it that way); ranges may wrap
    (``Sat..Mon``). Unknown tokens are dropped here; :func:`bad_days` reports them.
    """
    if not split_list(value):
        return list(DAYS)
    chosen: set[int] = set()
    for tok in split_list(value):
        m = _DAY_RANGE_RE.match(tok)
        if m and m.group(1) in DAYS and m.group(2) in DAYS:
            a, b = DAYS.index(m.group(1)), DAYS.index(m.group(2))
            chosen.update(range(a, b + 1) if a <= b else list(range(a, 7)) + list(range(0, b + 1)))
        elif tok in DAYS:
            chosen.add(DAYS.index(tok))
    return [DAYS[i] for i in sorted(chosen)]


@dataclass
class Job:
    """One installed job (merged with ``JOB_DEFAULTS``)."""

    id: str
    dir: Path
    conf: dict[str, str]
    raw: dict[str, str] = field(default_factory=dict)
    exports: set[str] = field(default_factory=set)
    disabled: bool = False
    module: str | None = None

    @property
    def title(self) -> str:
        return self.conf.get("TITLE") or self.id

    @property
    def kind(self) -> str:
        return self.conf.get("KIND", "agent")

    @property
    def slots(self) -> list[str]:
        return split_list(self.conf.get("SLOTS", ""))

    @property
    def every_min(self) -> str:
        return (self.conf.get("EVERY_MIN") or "").strip()

    @property
    def days(self) -> list[str]:
        """Weekdays the job runs on (ranges expanded; empty DAYS = every day)."""
        return expand_days(self.conf.get("DAYS", ""))

    @property
    def prompt_path(self) -> Path | None:
        p = self.dir / "prompt.md"
        return p if p.is_file() else None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "slots": self.slots,
            "every_min": self.every_min,
            "days": self.days,
            "dates": self.conf.get("DATES", ""),
            "session": self.conf.get("SESSION", "print"),
            "runtime": self.conf.get("RUNTIME", "any"),
            "default_mode": self.conf.get("DEFAULT_MODE", "off"),
            "module": self.module,
            "disabled": self.disabled,
            "dir": self.dir.as_posix(),
        }


def load_job(folder: Path, *, module: str | None = None) -> Job:
    """Read ``<folder>/job.conf`` (raises ``ConfParseError`` / ``OSError``)."""
    folder = Path(folder)
    raw, exports = parse_conf(folder / "job.conf", with_exports=True)
    conf = dict(JOB_DEFAULTS)
    conf.update(raw)
    if not conf.get("TITLE"):
        conf["TITLE"] = folder.name
    return Job(
        id=folder.name,
        dir=folder,
        conf=conf,
        raw=raw,
        exports=exports,
        disabled=(folder / DISABLED_MARKER).exists(),
        module=module,
    )


def jobs_dir(vault: Path, agent_dir: str | None = None) -> Path:
    return Path(vault) / (agent_dir or paths.DEFAULT_AGENT_DIR) / "jobs"


def list_jobs(vault: str | Path, *, include_disabled: bool = False, agent_dir: str | None = None) -> list[Job]:
    """Installed jobs of a vault, sorted by id. Broken job.conf files are skipped."""
    base = jobs_dir(Path(vault), agent_dir)
    if not base.is_dir():
        return []
    modules_of: dict[str, str] = {}
    try:
        from .manifest import Manifest

        man = Manifest.load(Path(vault), agent_dir or paths.DEFAULT_AGENT_DIR)
        prefix = f"{agent_dir or paths.DEFAULT_AGENT_DIR}/jobs/"
        for rel, entry in man.files.items():
            if rel.startswith(prefix):
                modules_of[rel[len(prefix):].split("/")[0]] = entry.get("module")
    except Exception:  # noqa: BLE001 - the manifest is optional here
        pass
    out = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or not (child / "job.conf").is_file():
            continue
        try:
            job = load_job(child, module=modules_of.get(child.name))
        except (ConfParseError, OSError):
            continue
        if job.disabled and not include_disabled:
            continue
        out.append(job)
    return out


def validate_job(job: Job) -> list[tuple[str, str]]:
    """Problems of one job as ``(level, message)`` pairs."""
    problems: list[tuple[str, str]] = []
    conf = job.conf
    for key, allowed in ENUM_KEYS.items():
        if conf.get(key) not in allowed:
            problems.append(("error", f"{key}=\"{conf.get(key)}\" must be one of {', '.join(allowed)}"))
    for key in INT_KEYS:
        if not re.match(r"^\d+$", conf.get(key, "")):
            problems.append(("error", f"{key}=\"{conf.get(key)}\" must be a whole number"))
    for slot in job.slots:
        if not TIME_RE.match(slot):
            problems.append(("error", f"SLOTS entry '{slot}' is not a time \"HH:MM\""))
    every = job.every_min
    if every:
        n = int(every) if every.isdigit() else -1
        if not (1 <= n <= 59 or (n >= 60 and n % 60 == 0 and n <= 1440)):
            problems.append(("error", f"EVERY_MIN=\"{every}\" must be minutes 1-59 or a whole number of hours (60, 120, ... 1440)"))
    bad = bad_days(conf.get("DAYS", ""))
    for day in bad:
        problems.append(("error", f"DAYS entry '{day}' is not one of {', '.join(DAYS)} (or a range like Mon..Fri)"))
    # Ranges ("Mon..Fri" or "Mon-Fri") are read the same way by both host runners.
    for part in [p.strip() for p in conf.get("DATES", "").split(";") if p.strip()]:
        if not _DATES_RE.match(part):
            problems.append(("error", f"DATES entry '{part}' must be YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD"))
    if conf.get("KIND") == "agent" and job.prompt_path is None:
        problems.append(("error", "KIND=agent but prompt.md is missing"))
    if conf.get("KIND") == "command" and not conf.get("COMMAND"):
        problems.append(("error", "KIND=command but COMMAND is empty"))
    if conf.get("SESSION") == "rc" and conf.get("KIND") != "agent":
        problems.append(("warning", "SESSION=rc only makes sense for agent jobs"))
    if not job.slots and not job.every_min and not conf.get("SCHEDULE") and not conf.get("DATES"):
        problems.append(("info", "no SLOTS/SCHEDULE: only started by other tools"))
    unknown = sorted(k for k in job.raw if k not in JOB_DEFAULTS and k not in job.exports)
    for key in unknown:
        problems.append(("warning", f"unknown key {key} (use `export {key}=...` to pass environment to the job)"))
    return problems
