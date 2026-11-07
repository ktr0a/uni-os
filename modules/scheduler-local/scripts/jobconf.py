"""Shared helpers for the scheduler-local scripts (stdlib only, Python 3.11+).

- parse_conf(path): job.conf -> dict, with bash `source` semantics for the cases job.conf
  uses (KEY="v", KEY='v', KEY=v, several assignments on a line, `export KEY=v`, comments,
  multi-line quoted values). Values are kept raw: no $VAR expansion.
- load_jobs(vault): every rendered job in <vault>/_agent/jobs/<job>/job.conf.
- Schedule helpers: SLOTS/DAYS/DATES/EVERY_MIN -> cron lines, nominal slot of a run.
- assemble_prompt(): host header (_agent/jobs/_header.md) + the job's prompt.md, with the
  run-time placeholders {{host.*}} and {{job.*}} filled in.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Defaults of the job.conf keys (the key table in docs/file-formats.md, section "job.conf"); a job.conf only needs the keys it changes.
CONF_DEFAULTS = {
    "TITLE": "", "KIND": "agent", "COMMAND": "", "SLOTS": "", "DAYS": ",".join(DAY_NAMES),
    "DATES": "", "SCHEDULE": "", "EVERY_MIN": "", "SESSION": "print", "KEEP_H": "8",
    "MODEL": "", "EFFORT": "high", "TIMEOUT_MIN": "45", "NEEDS_VAULT": "yes", "PRECHECK": "",
    "QUIET_OK": "no", "DRY_OK": "no", "NOTIFY_DONE": "", "NOTIFY_GATE": "",
    "AGENT_LOCK": "shared", "LOCK_WAIT_MIN": "20", "LAPTOP_TASK": "", "FAILOVER_DELAY_MIN": "25",
    "MARKER": "yes", "RUNTIME": "any", "DEFAULT_MODE": "off",
}


# ---------------------------------------------------------------------------- job.conf

def parse_conf_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    buf = ""
    for line in text.splitlines():
        buf = f"{buf}\n{line}" if buf else line
        try:
            tokens = shlex.split(buf, comments=True, posix=True)
        except ValueError:      # an open quote: the value continues on the next line
            continue
        buf = ""
        for tok in tokens:
            if tok == "export" or "=" not in tok:
                continue
            key, _, value = tok.partition("=")
            if KEY_RE.match(key):
                out[key] = value
    return out


def parse_conf(path: str | Path) -> dict[str, str]:
    return parse_conf_text(Path(path).read_text(encoding="utf-8"))


@dataclass
class Job:
    id: str
    dir: Path
    conf: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str:
        return self.conf.get(key, CONF_DEFAULTS.get(key, ""))

    @property
    def title(self) -> str:
        return self.get("TITLE") or self.id

    @property
    def prompt_path(self) -> Path:
        return self.dir / "prompt.md"


def jobs_dir(vault: str | Path) -> Path:
    return Path(vault) / "_agent" / "jobs"


DISABLED_MARKER = "DISABLED"   # `uni-os disable <module>` drops this file into its jobs' folders


def is_disabled(job: Job) -> bool:
    return (job.dir / DISABLED_MARKER).exists()


def load_jobs(vault: str | Path, include_disabled: bool = False) -> list[Job]:
    root = jobs_dir(vault)
    jobs = []
    if not root.is_dir():
        return jobs
    for d in sorted(root.iterdir()):
        conf = d / "job.conf"
        if d.is_dir() and conf.is_file():
            job = Job(d.name, d, parse_conf(conf))
            if include_disabled or not is_disabled(job):
                jobs.append(job)
    return jobs


def load_job(vault: str | Path, job_id: str) -> Job:
    d = jobs_dir(vault) / job_id
    conf = d / "job.conf"
    if not conf.is_file():
        raise FileNotFoundError(f"no job.conf for job {job_id!r} in {d}")
    return Job(job_id, d, parse_conf(conf))


# ---------------------------------------------------------------------------- schedules

def parse_slots(s: str) -> list[tuple[int, int]]:
    out = []
    for part in re.split(r"[,\s]+", s or ""):
        if not part:
            continue
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", part)
        if not m:
            raise ValueError(f"bad slot {part!r}, expected HH:MM")
        h, mi = int(m.group(1)), int(m.group(2))
        if h > 23 or mi > 59:
            raise ValueError(f"bad slot {part!r}")
        out.append((h, mi))
    return sorted(set(out))


def parse_days(s: str) -> list[int]:
    """'Mon,Tue' -> [0, 1] (Monday = 0). Empty = every day.

    Accepts ranges written 'Mon..Fri' (systemd style, as the VM runner reads them)
    or 'Mon-Fri'; a range may wrap ('Sat..Mon')."""
    if not (s or "").strip():
        return list(range(7))
    days: set[int] = set()
    for part in re.split(r"[,\s]+", s.strip()):
        if not part:
            continue
        sep = ".." if ".." in part else ("-" if "-" in part else None)
        if sep:
            a, b = (DAY_NAMES.index(x[:3].title()) for x in part.split(sep, 1))
            rng = range(a, b + 1) if a <= b else list(range(a, 7)) + list(range(0, b + 1))
            days.update(rng)
        else:
            days.add(DAY_NAMES.index(part[:3].title()))
    return sorted(days)


def parse_dates(s: str) -> list[tuple[date, date]]:
    """'2026-11-09..2026-11-29; 2026-12-05' -> [(from, to), (d, d)]. Empty = no limit."""
    out = []
    for part in (s or "").split(";"):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("..")
        d1 = date.fromisoformat(a.strip())
        d2 = date.fromisoformat(b.strip()) if b.strip() else d1
        out.append((d1, d2))
    return out


def date_allowed(d: date, ranges: list[tuple[date, date]]) -> bool:
    return not ranges or any(a <= d <= b for a, b in ranges)


def _cron_dow(days: list[int]) -> str:
    if len(days) == 7:
        return "*"
    cron = sorted({(d + 1) % 7 for d in days})   # cron: Sun = 0, Mon = 1
    groups: list[list[int]] = []
    for d in cron:
        if groups and d == groups[-1][-1] + 1:
            groups[-1].append(d)
        else:
            groups.append([d])
    return ",".join(f"{g[0]}-{g[-1]}" if len(g) >= 3 else ",".join(map(str, g)) for g in groups)


def cron_lines(job: Job) -> tuple[list[str], list[str]]:
    """(cron lines, notes) for a job. One cron line per distinct minute value, because one
    cron expression can't mix minutes (07:50 and 13:05 need two lines/tasks)."""
    notes: list[str] = []
    days = parse_days(job.get("DAYS"))
    dow = _cron_dow(days)
    lines: list[str] = []
    every = job.get("EVERY_MIN").strip()
    if every:
        lines.append(f"*/{int(every)} * * * {dow}")
    by_minute: dict[int, list[int]] = {}
    for h, m in parse_slots(job.get("SLOTS")):
        by_minute.setdefault(m, []).append(h)
    for m in sorted(by_minute):
        hours = ",".join(str(h) for h in sorted(by_minute[m]))
        lines.append(f"{m} {hours} * * {dow}")
    if job.get("DATES").strip():
        notes.append("DATES limits the job to certain dates; cron can't express that: keep the "
                     "cron line(s) and let the prompt's date guard (or the runner) skip other days, "
                     "or create one-off tasks (fireAt) for single dates.")
    if job.get("SCHEDULE").strip() and not lines:
        notes.append("only a raw SCHEDULE (systemd OnCalendar) is set: translate it by hand.")
    if len(lines) > 1:
        notes.append("several cron lines: the desktop app takes one cron expression per task, "
                     "so create one task per line (e.g. <job>, <job>-2) with the same prompt.")
    if not lines and not job.get("SCHEDULE").strip():
        notes.append("no schedule: started on demand or by another job only.")
    return lines, notes


def nominal_slot(job: Job, now: datetime) -> datetime | None:
    """The latest scheduled time of the job at or before `now` (the slot a late or catch-up
    run belongs to), ignoring any offset the scheduler adds. None if the job has no slots."""
    slots = parse_slots(job.get("SLOTS"))
    every = job.get("EVERY_MIN").strip()
    days = parse_days(job.get("DAYS"))
    ranges = parse_dates(job.get("DATES"))
    if every:
        n = int(every)
        t = now.replace(second=0, microsecond=0)
        t -= timedelta(minutes=t.minute % n)
        return t
    if not slots:
        return None
    for back in range(0, 8):
        day = (now - timedelta(days=back)).date()
        if day.weekday() not in days or not date_allowed(day, ranges):
            continue
        for h, m in reversed(slots):
            t = datetime(day.year, day.month, day.day, h, m)
            if t <= now.replace(tzinfo=None):
                return t
    return None


def describe_when(job: Job) -> str:
    parts = []
    if job.get("EVERY_MIN").strip():
        parts.append(f"every {job.get('EVERY_MIN')} min")
    if job.get("SLOTS").strip():
        parts.append(job.get("SLOTS"))
    days = parse_days(job.get("DAYS"))
    if len(days) < 7:
        parts.append(",".join(DAY_NAMES[d] for d in days))
    if job.get("DATES").strip():
        parts.append(f"dates {job.get('DATES')}")
    if not parts and job.get("SCHEDULE").strip():
        parts.append(f"OnCalendar {job.get('SCHEDULE')}")
    return " ".join(parts) or "on demand"


# ---------------------------------------------------------------------------- ran markers

def ran_marker_slot(vault: str | Path, job: Job) -> str | None:
    """`slot:` of _agent/vm/ran/<task>.md (written by the always-on host after a failover run)."""
    name = job.get("LAPTOP_TASK") or job.id
    path = Path(vault) / "_agent" / "vm" / "ran" / f"{name}.md"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("slot:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------- prompts

FALLBACK_HEADER = """You are running as the scheduled job "{{job.title}}" ({{job.id}}) on {{host.name}}, unattended.
The vault is `{{host.vault}}`; paths in the task are relative to it. Get the date and time with
`{{host.date_cmd}}`, never from memory. Ask nothing unless the task has an explicit ask step.

--- task (verbatim) ---
"""

DRY_RUN_PREAMBLE = """DRY RUN (test of this job): do every read step for real (files, calendar, mail), but do NOT
create, edit, move or delete any file, calendar event or message, and do not send anything. At the
end, list exactly what you WOULD have changed, and every problem you hit (missing tools, paths,
permissions).

"""


@dataclass
class Host:
    name: str = "laptop"
    kind: str = "laptop"          # laptop | vm | cloud
    vault: str = "."
    date_cmd: str = "date"
    python: str = "python"
    session: str = "app"          # app | print | rc
    framework: str = field(default_factory=lambda: str(framework_root()))  # the Uni OS clone: tools/uni_os.py


def fill_runtime(text: str, job: Job, host: Host) -> str:
    values = {
        "host.name": host.name, "host.kind": host.kind, "host.vault": host.vault,
        "host.date_cmd": host.date_cmd, "host.python": host.python, "host.session": host.session,
        "host.framework": host.framework,
        "job.id": job.id, "job.title": job.title, "job.slots": job.get("SLOTS") or describe_when(job),
        "job.days": job.get("DAYS"), "job.timeout_min": job.get("TIMEOUT_MIN"),
    }
    return re.sub(r"\{\{\s*((?:host|job)\.[a-z_]+)\s*\}\}",
                  lambda m: values.get(m.group(1), m.group(0)), text)


def assemble_prompt(vault: str | Path, job: Job, host: Host, dry_run: bool = False) -> str:
    header_path = jobs_dir(vault) / "_header.md"
    try:
        header = header_path.read_text(encoding="utf-8")
    except OSError:
        header = FALLBACK_HEADER
    header = re.sub(r"^<!--.*?-->\s*", "", header, flags=re.S)  # drop the explanatory comment
    body = job.prompt_path.read_text(encoding="utf-8")
    text = fill_runtime(header.rstrip() + "\n\n" + body, job, host)
    return (DRY_RUN_PREAMBLE + text) if dry_run else text


def framework_root() -> Path:
    return Path(__file__).resolve().parents[3]
