"""Load, merge, validate and export the Uni OS config (every key: ``config/schema.md``).

The config is one TOML file. In a vault it lives at ``<vault>/_agent/uni-os.toml``
and is the single source of truth for every parameter. Secrets never go in it.

Resolution (lowest priority first):

1. ``BASE_DEFAULTS`` below (every base key that has a sensible default),
2. the ``[defaults]`` of every discovered module that is *not* enabled (sorted by id),
3. the ``[defaults]`` of every enabled module (dependency order),
4. the user's file.

Tables are deep-merged, lists and scalars are replaced. ``[defaults.course]`` in a
module is applied to every ``[[courses]]`` entry that lacks those keys. After the
merge each course gets computed defaults (``language`` from ``student.language``,
``assistance`` from ``study.assistance_default``) and derived helper fields that
templates need but cannot compute (``colour_rgb``, ``colour_int``, ``card``,
``error_logs`` ...); see :func:`derive_course`. ``term.weeks`` is derived the same
way: one entry per teaching week for the term-week table (:func:`term_weeks`).

``load(vault)`` returns the resolved config as a plain ``dict``; ``validate(cfg)``
returns a list of :class:`~uni_os.errors.Issue`; ``export_json(cfg)`` produces the
machine copy written to ``<vault>/_agent/uni-os.json``.
"""

from __future__ import annotations

import copy
import datetime as dt
import difflib
import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterable

from . import __version__, paths
from . import secrets as _secrets
from .errors import ConfigError, Issue

GENERATED_NOTE = "do not edit; edit uni-os.toml"

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

#: ``term.weeks`` without a ``term.last_lecture_day``: this many teaching weeks (0 .. 13).
DEFAULT_TERM_WEEKS = 14
#: Upper bound for ``term.weeks`` (a mistyped year must not produce a table of hundreds of rows).
MAX_TERM_WEEKS = 60
#: Keys under ``[term]`` that the tools compute (never set them by hand).
DERIVED_TERM_KEYS = ("weeks",)
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TIME_RANGE_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SLOT_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d(\s.*)?$")
DATE_OR_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?$")
_TIMEISH_RE = re.compile(r"^\d{1,2}[:.]\d{1,2}$")  # looks like an attempt at "HH:MM"
_RANGEISH_RE = re.compile(r"^\d{1,2}[:.]\d{1,2}\s*-\s*\d{1,2}[:.]\d{1,2}$")

ASSISTANCE = ("solo", "hints-only", "coach", "full")
ASSESSMENT_KINDS = ("sheet", "quiz", "oral", "project", "midterm", "other")
COUNTS_FOR = ("bonus", "grade", "admission", "none")
BONUS_SCHEMES = ("none", "threshold", "points", "best-n", "custom")
FORMATS = ("html", "md", "pdf")
PRESET_NAMES = ("minimal", "standard", "full", "custom")

#: Keys of a ``notify.quiet_windows`` entry (the push gate reads exactly these).
QUIET_WINDOW_KEYS = ("from", "to", "reason", "label", "day", "days", "since", "until", "urgent_ok")
#: A hard (not ``urgent_ok``) dated quiet window longer than this gets a warning.
HARD_WINDOW_MAX_HOURS = 24

#: Keys of a ``[[courses.assessments]]`` entry that some template, skill or tool reads.
#: ``scope`` (optional): the official wording of what the work covers (course card,
#: course-facts skill, resources/course-verification.md).
ASSESSMENT_KEYS = ("name", "kind", "schedule", "counts_for", "assistance", "points_max", "dates", "scope")

#: Old alias keys still read, but no longer shown in the example configs:
#: ``0`` = use the one stuck-note threshold ``notify.inbox_stale_hours[_taps]``.
STUCK_ALIASES = {
    "heartbeat.inbox_stuck_hours": "notify.inbox_stale_hours",
    "heartbeat.inbox_tap_stuck_hours": "notify.inbox_stale_hours_taps",
    "vm.inbox_stuck_h": "notify.inbox_stale_hours",
    "vm.tap_stuck_h": "notify.inbox_stale_hours_taps",
}

#: Enumerated config values: dotted key -> allowed values.
ENUMS: dict[str, tuple[str, ...]] = {
    "uni_os.preset": PRESET_NAMES,
    "storage.provider": ("google-drive", "onedrive", "dropbox", "icloud", "syncthing", "git", "local"),
    "agent.primary": ("claude-code", "codex", "gemini-cli", "cursor", "other"),
    "agent.permission_posture": ("bypass", "accept-edits", "ask"),
    "study.math": ("katex", "mathjax", "none"),
    "study.assistance_default": ASSISTANCE,
    "notify.provider": ("ntfy", "none"),
    "calendar.provider": ("google", "other", "none"),
    "runtime.laptop_os": ("windows", "macos", "linux"),
    "vm.provider": ("gcp", "home-server", "other"),
}

#: Keys that must be present and non-empty.
REQUIRED = ("student.name", "university.name", "term.label", "term.timezone", "term.week0_monday")
COURSE_REQUIRED = ("id", "name", "short", "folder", "slug", "colour")

#: Keys holding a date (TOML date or "YYYY-MM-DD" string; "" = not set).
DATE_KEYS = (
    "term.week0_monday",
    "term.last_lecture_day",
    "term.lecture_free_from",
    "term.exam_session_start",
    "term.exam_session_end",
)

#: Vault top-level folders a course folder must not collide with.
RESERVED_FOLDERS = ("_agent", "_templates", "inbox", "me", "progress", "semester", "resources", "views", ".obsidian")

BASE_DEFAULTS: dict[str, Any] = {
    "uni_os": {"version": __version__, "preset": "standard"},
    "student": {"handle": "", "language": "English", "dictates": False, "pronouns": ""},
    "university": {"short": "", "programme": "", "lms": "Moodle", "lms_url": "", "website": ""},
    "term": {
        "last_lecture_day": "",
        "lecture_free_from": "",
        "exam_session_start": "",
        "exam_session_end": "",
        "holidays": [],
    },
    "paths": {"vault": "", "agent_dir": "_agent", "inbox": "inbox", "never_open": ["**/private/**"]},
    "storage": {"provider": "google-drive"},
    "obsidian": {"enabled": True},
    "agent": {
        "primary": "claude-code",
        "permission_posture": "accept-edits",
        "default_model": "",
        "heavy_model": "",
        "reply_rules": [],
        "skills_dir": ".claude/skills",
    },
    "study": {
        "formats": ["html", "md"],
        "math": "katex",
        "chunk_words": 750,
        "assistance_default": "hints-only",
        "personal_deadline_rule": "",
    },
    "courses": [],
    "schedule": {
        "daily_prep": ["17:30", "19:30"],
        "prep_check": "07:30",
        "week_page": {"day": "Sun", "time": "10:00"},
        "check_in": {"day": "Sat", "time": "19:45", "every": "week"},
        "heartbeat": ["07:50", "13:05", "18:05"],
        "heartbeat_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "inbox_sync": ["07:15", "13:15", "18:15"],
        "study_cutoff": "19:00",
    },
    "notify": {
        "provider": "ntfy",
        "ntfy_server": "https://ntfy.sh",
        "ntfy_topic_file": "~/.config/uni-os/ntfy-topic",
        "max_per_day": 3,
        "min_gap_hours": 2,
        "quiet_hours": "21:00-07:30",
        "dedupe_hours": 24,
        "never_all_good": True,
        "quiet_windows": [],
    },
    "calendar": {
        "provider": "google",
        "courses": "Courses",
        "study_blocks": "Study blocks",
        "events": "Events",
        "busy": "Busy",
        "notation": "default",
    },
    "runtime": {"laptop_os": "windows", "use_vm": False, "use_cloud_sessions": False},
    "vm": {
        "provider": "gcp",
        "host_alias": "uni-vm",
        "project": "",
        "zone": "",
        "machine_type": "e2-custom-small-4096",
        "linux_user": "",
        "remote_control_name": "Uni (VM)",
        "budget_month": 13,
        "budget_currency": "EUR",
    },
    "cockpit": {"enabled": True},
    "modules": {"enabled": []},
}

#: Defaults for every ``[[courses]]`` entry (before module ``[defaults.course]``).
COURSE_DEFAULTS: dict[str, Any] = {
    "colour_light": "",
    "lecturers": [],
    "lecture_slots": [],
    "exercise_slots": [],
    "sheet_release": "",
    "sheet_due": "",
    "official_subfolders": [],
    "error_log_streams": ["main"],
    "notes": [],
    "assessments": [],
    "bonus": {"scheme": "none", "description": "", "max_bonus": 0, "rule": ""},
}

#: Defaults for every ``[[courses.assessments]]`` entry.
ASSESSMENT_DEFAULTS: dict[str, Any] = {"kind": "other", "schedule": "", "counts_for": "none", "points_max": 0}

#: Fields computed per course (never set them by hand; they are overwritten only if absent).
DERIVED_COURSE_KEYS = (
    "colour_rgb",
    "colour_int",
    "colour_light_rgb",
    "colour_light_int",
    "card",
    "error_logs",
    "error_log_files",
    "handwritten_dir",
)


# --------------------------------------------------------------------------- reading / merging


def read_toml(path: str | Path) -> dict:
    """Parse a TOML file with a helpful error."""
    path = Path(path)
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"{path}: invalid TOML: {exc}",
            hint='times must be quoted strings like "07:30"; dates may be bare (2026-09-14) or quoted',
        ) from None
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from None


def deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict: ``override`` wins, nested tables merged, lists replaced."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _module_layers(catalog, enabled: Iterable[str]) -> list[tuple[str, dict]]:
    """``(source, defaults)`` layers from module ``[defaults]``, lowest priority first."""
    if catalog is None:
        return []
    enabled = [m for m in enabled if m in catalog.modules]
    others = sorted(m for m in catalog.modules if m not in enabled)
    layers = []
    for mid in others + enabled:
        defaults = catalog.modules[mid].defaults or {}
        if defaults:
            layers.append((f"module:{mid}", defaults))
    return layers


def layers_for(raw: dict, catalog=None, enabled: Iterable[str] = ()) -> list[tuple[str, dict]]:
    """All config layers, lowest priority first: base, modules, user."""
    layers = [("base", BASE_DEFAULTS)]
    for source, defaults in _module_layers(catalog, enabled):
        layers.append((source, {k: v for k, v in defaults.items() if k != "course"}))
    layers.append(("user", raw))
    return layers


def course_defaults_for(catalog=None, enabled: Iterable[str] = ()) -> dict:
    """Merged ``[defaults.course]`` tables (enabled modules win over others)."""
    merged = copy.deepcopy(COURSE_DEFAULTS)
    for _source, defaults in _module_layers(catalog, enabled):
        course = defaults.get("course")
        if isinstance(course, dict):
            merged = deep_merge(merged, course)
    return merged


def resolve(raw: dict, catalog=None, enabled: Iterable[str] = ()) -> dict:
    """Merge defaults under ``raw`` and fill in per-course defaults and derived fields."""
    enabled = list(enabled)
    cfg: dict = {}
    for _source, layer in layers_for(raw, catalog, enabled):
        cfg = deep_merge(cfg, layer)
    _normalise_dates(cfg)
    if isinstance(cfg.get("term"), dict):
        cfg["term"]["weeks"] = term_weeks(cfg)
    course_defaults = course_defaults_for(catalog, enabled)
    courses = cfg.get("courses")
    if isinstance(courses, list):
        cfg["courses"] = [
            derive_course(deep_merge(course_defaults, c), cfg) if isinstance(c, dict) else c for c in courses
        ]
    mods = cfg.setdefault("modules", {})
    if isinstance(mods, dict) and enabled:
        mods["enabled"] = enabled
    return cfg


def _normalise_dates(cfg: dict) -> None:
    for key in DATE_KEYS:
        table, name = key.split(".")
        section = cfg.get(table)
        if isinstance(section, dict) and isinstance(section.get(name), str):
            parsed = as_date(section[name])
            if parsed is not None:
                section[name] = parsed
    term = cfg.get("term")
    if isinstance(term, dict) and isinstance(term.get("holidays"), list):
        for hol in term["holidays"]:
            if isinstance(hol, dict):
                for k in ("from", "to"):
                    if isinstance(hol.get(k), str) and as_date(hol[k]) is not None:
                        hol[k] = as_date(hol[k])


def date_long(day: dt.date) -> str:
    """``Sat 7 Nov 2026``: the date format of the vault's text (locale-independent)."""
    return f"{DAYS[day.weekday()]} {day.day} {MONTHS[day.month - 1]} {day.year}"


def term_weeks(cfg: dict) -> list[dict]:
    """The derived ``term.weeks``: one entry per teaching week, for the term-week table.

    Week 0 starts on ``term.week0_monday`` and week *n* on ``week0_monday + 7n`` days (the
    numbering of ``uni-os week`` and every week page). The list runs from week 0 through
    the week of ``term.last_lecture_day``, or covers :data:`DEFAULT_TERM_WEEKS` weeks
    (0 .. 13) when that day is not set or lies before week 0; at most
    :data:`MAX_TERM_WEEKS`. Each entry: ``number`` (int), ``nn`` (two digits, as in
    ``week-07.md``), ``start`` (``Mon 14 Sep 2026``) and ``start_iso`` (``2026-09-14``).
    Empty when ``term.week0_monday`` is missing or not a date (validation reports it).
    """
    term = cfg.get("term") if isinstance(cfg.get("term"), dict) else {}
    week0 = as_date(term.get("week0_monday"))
    if week0 is None:
        return []
    last = as_date(term.get("last_lecture_day"))
    count = (last - week0).days // 7 + 1 if last is not None and last >= week0 else DEFAULT_TERM_WEEKS
    weeks = []
    for number in range(min(count, MAX_TERM_WEEKS)):
        monday = week0 + dt.timedelta(days=7 * number)
        weeks.append({"number": number, "nn": f"{number:02d}", "start": date_long(monday), "start_iso": monday.isoformat()})
    return weeks


def hex_to_rgb(colour: str) -> tuple[int, int, int]:
    colour = colour.lstrip("#")
    return int(colour[0:2], 16), int(colour[2:4], 16), int(colour[4:6], 16)


def tint(colour: str, amount: float = 0.4) -> str:
    """Mix a hex colour with white (``amount`` 0..1)."""
    r, g, b = hex_to_rgb(colour)
    mix = [round(c + (255 - c) * amount) for c in (r, g, b)]
    return "#{:02x}{:02x}{:02x}".format(*mix)


def error_log_entries(slug: str, folder: str, streams: list) -> list[dict]:
    """The error-log files of a course (``docs/file-formats.md``, section "Error-log row").

    One stream: ``<slug>-error-log.md``. Several: ``<slug>-error-log-<stream>.md`` each.
    """
    streams = [s for s in streams if isinstance(s, str) and s] or ["main"]
    entries = []
    for stream in streams:
        file = f"{slug}-error-log.md" if len(streams) == 1 else f"{slug}-error-log-{stream}.md"
        title = "Error log" if len(streams) == 1 else f"Error log ({stream})"
        entries.append({"stream": stream, "file": file, "path": f"{folder}/{file}", "title": title})
    return entries


def derive_course(course: dict, cfg: dict) -> dict:
    """Computed defaults and derived helper fields for one course (only where absent)."""
    student = cfg.get("student") if isinstance(cfg.get("student"), dict) else {}
    study = cfg.get("study") if isinstance(cfg.get("study"), dict) else {}
    course.setdefault("language", student.get("language", "English"))
    course.setdefault("assistance", study.get("assistance_default", "hints-only"))
    colour = course.get("colour")
    if isinstance(colour, str) and HEX_RE.match(colour):
        if not course.get("colour_light"):
            course["colour_light"] = tint(colour)
        course.setdefault("colour_rgb", ", ".join(str(c) for c in hex_to_rgb(colour)))
        course.setdefault("colour_int", int(colour[1:], 16))
        light = course.get("colour_light")
        if isinstance(light, str) and HEX_RE.match(light):
            course.setdefault("colour_light_rgb", ", ".join(str(c) for c in hex_to_rgb(light)))
            course.setdefault("colour_light_int", int(light[1:], 16))
    folder, slug = course.get("folder"), course.get("slug")
    if isinstance(folder, str) and isinstance(slug, str):
        course.setdefault("card", f"{folder}/{slug}.md")
        streams = course.get("error_log_streams") if isinstance(course.get("error_log_streams"), list) else ["main"]
        course.setdefault("error_logs", error_log_entries(slug, folder, streams))
        course.setdefault("error_log_files", [e["file"] for e in course["error_logs"]])
    if isinstance(folder, str):
        # The handwritten-notes folder inside the course folder ("" = "<folder> handwritten").
        hw = course.get("handwritten_folder")
        course.setdefault("handwritten_dir", hw.strip("/") if isinstance(hw, str) and hw.strip("/") else f"{folder} handwritten")
    bonus = course.get("bonus")
    if isinstance(bonus, dict):
        course["bonus"] = deep_merge(COURSE_DEFAULTS["bonus"], bonus)
    assessments = course.get("assessments")
    if isinstance(assessments, list):
        filled = []
        for item in assessments:
            if isinstance(item, dict):
                item = deep_merge(ASSESSMENT_DEFAULTS, item)
                item.setdefault("assistance", course.get("assistance", "hints-only"))
            filled.append(item)
        course["assessments"] = filled
    return course


# --------------------------------------------------------------------------- small value helpers


def as_date(value: Any) -> dt.date | None:
    """A ``date`` from a TOML date, datetime or ``YYYY-MM-DD`` string; else ``None``."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def is_time(value: Any) -> bool:
    return isinstance(value, str) and bool(TIME_RE.match(value))


def get_path(cfg: dict, dotted: str) -> Any:
    """Look up ``a.b.c`` (list indices and course ids allowed: ``courses.algo.name``).

    Raises ``KeyError`` with a helpful message if the key does not exist.
    """
    from .template import _Missing, walk  # local import: template has no config dependency

    segs = [s for s in dotted.split(".") if s]
    if not segs:
        return cfg
    if segs[0] not in cfg:
        close = difflib.get_close_matches(segs[0], list(cfg.keys()), n=1)
        raise KeyError(f"no key '{segs[0]}'" + (f" (did you mean '{close[0]}'?)" if close else ""))
    try:
        return walk(cfg[segs[0]], segs[1:], dotted)
    except _Missing as exc:
        parent = ".".join(segs[: exc.depth])
        missing = segs[exc.depth] if exc.depth < len(segs) else segs[-1]
        close = difflib.get_close_matches(missing, exc.available, n=1)
        raise KeyError(
            f"'{parent}' has no key '{missing}'" + (f" (did you mean '{parent}.{close[0]}'?)" if close else "")
        ) from None


def flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Leaf ``(dotted_key, value)`` pairs. Lists of tables use ids (``courses.algo.name``) or indices."""
    out: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        if not value and prefix:
            out.append((prefix, value))
        for k, v in value.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
        for idx, item in enumerate(value):
            name = item.get("id") if isinstance(item.get("id"), str) else str(idx)
            out.extend(flatten(item, f"{prefix}.{name}"))
    else:
        out.append((prefix, value))
    return out


# --------------------------------------------------------------------------- JSON export


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dt.time):
        return value.strftime("%H:%M") if value.second == 0 else value.isoformat()
    return value


def export_json(cfg: dict) -> str:
    """The text of ``<vault>/_agent/uni-os.json`` (deterministic, UTF-8, trailing newline)."""
    data = {"_generated": GENERATED_NOTE, "_framework_version": __version__}
    data.update(to_jsonable(cfg))
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------- loading


def load(vault: str | Path | None = None, *, modules_dir: str | Path | None = None, config_path: str | Path | None = None) -> dict:
    """The resolved config of a vault (finds ``<vault>/_agent/uni-os.toml``).

    ``vault=None`` discovers the vault (``$UNI_OS_VAULT`` or walking up from the
    current directory). Module problems (unknown ids) do not raise here, so
    helper scripts keep working; ``uni-os doctor`` reports them.
    """
    from .context import open_session

    return open_session(vault=vault, config=config_path, modules_dir=modules_dir, strict_modules=False).cfg


# --------------------------------------------------------------------------- validation


def _get(cfg: dict, dotted: str, default: Any = None) -> Any:
    cur: Any = cfg
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return default
        cur = cur[seg]
    return cur


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "table"
    if isinstance(value, dt.date):
        return "date"
    return type(value).__name__


def _same_kind(default: Any, value: Any) -> bool:
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list)
    if isinstance(default, dict):
        return isinstance(value, dict)
    return True


class _Collector:
    def __init__(self):
        self.issues: list[Issue] = []

    def error(self, where: str, message: str) -> None:
        self.issues.append(Issue("error", where, message))

    def warn(self, where: str, message: str) -> None:
        self.issues.append(Issue("warning", where, message))

    def info(self, where: str, message: str) -> None:
        self.issues.append(Issue("info", where, message))


def _check_date(c: _Collector, where: str, value: Any, *, required: bool = False) -> dt.date | None:
    if value in ("", None):
        if required:
            c.error(where, "required date is missing (format YYYY-MM-DD)")
        return None
    parsed = as_date(value)
    if parsed is None:
        c.error(where, f"'{value}' is not a date (format YYYY-MM-DD)")
    return parsed


def _check_folder(c: _Collector, where: str, value: Any) -> None:
    if not isinstance(value, str):
        c.error(where, "must be text")
        return
    problem = paths.check_name(value)
    if problem:
        c.error(where, f"'{value}' is not a valid folder name: {problem}")


def _check_schedule(c: _Collector, value: Any, where: str) -> None:
    """Generic checks for ``[schedule]``: times "HH:MM", days "Mon".."Sun"."""
    if isinstance(value, dict):
        for k, v in value.items():
            sub = f"{where}.{k}"
            if k == "day":
                if v not in DAYS:
                    c.error(sub, f"'{v}' is not a day (use one of {', '.join(DAYS)})")
            elif k.endswith("days") and k != "days_off":
                if not isinstance(v, list) or any(d not in DAYS for d in v):
                    c.error(sub, f"must be a list of days like [\"Mon\", \"Wed\"] (got {v!r})")
            elif k == "every":
                if not isinstance(v, str) or not v:
                    c.error(sub, "must be text such as \"week\"")
            else:
                _check_schedule(c, v, sub)
    elif isinstance(value, list):
        for idx, v in enumerate(value):
            _check_schedule(c, v, f"{where}[{idx}]")
    elif isinstance(value, str):
        text = value.strip()
        if where.endswith(".time"):
            if not TIME_RE.match(text):
                c.error(where, f"'{value}' is not a time; use 24-hour \"HH:MM\"")
        elif _TIMEISH_RE.match(text):
            if not TIME_RE.match(text):
                c.error(where, f"'{value}' is not a time; use 24-hour \"HH:MM\" (e.g. \"07:30\")")
        elif _RANGEISH_RE.match(text):
            if not TIME_RANGE_RE.match(text.replace(" ", "")):
                c.error(where, f"'{value}' is not a time range; use \"HH:MM-HH:MM\" (e.g. \"07:00-22:00\")")
        # anything else (e.g. a raw OnCalendar string a module defines) is not checked here
    elif isinstance(value, dt.time):
        c.error(where, "write times as quoted strings, e.g. \"07:30\"")


def _window_moment(value: Any, *, end: bool = False, base: dt.date | None = None) -> dt.datetime | None:
    """A dated quiet-window bound as the push gate reads it (``pushgate._bound``): a date
    is the start of that day (``end``: the end of it), "YYYY-MM-DD HH:MM" that minute, and a
    bare "HH:MM" (only for ``to``) that time on the ``from`` day. None = not readable."""
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, dt.date):
        start = dt.datetime(value.year, value.month, value.day)
        return start + dt.timedelta(days=1) if end else start
    if isinstance(value, dt.time):
        return dt.datetime.combine(base, value.replace(tzinfo=None)) if base else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if TIME_RE.match(text):
        return dt.datetime.combine(base, dt.time(int(text[:2]), int(text[3:]))) if base else None
    if not DATE_OR_DATETIME_RE.match(text):
        return None
    try:
        moment = dt.datetime.fromisoformat(text.replace("T", " "))
    except ValueError:
        return None
    return moment + dt.timedelta(days=1) if end and len(text) == 10 else moment


def _check_quiet_window(c: _Collector, where: str, win: Any) -> None:
    """One ``notify.quiet_windows`` entry, in the shapes the push gate reads
    (``tools/uni_os/pushgate.py``, ``window_hit``):

    - dated  ``{ from, to, reason }`` (dates, "YYYY-MM-DD HH:MM", or a bare "HH:MM" ``to``);
    - weekly ``{ day | days, from = "HH:MM", to = "HH:MM", since, until, reason }``;
    - either may add ``urgent_ok = true`` (soft: urgent and direct pushes pass and the
      heartbeat keeps running). A hard window holds every push and makes the heartbeat's
      pre-check skip, which is right for a timed quiz but not for days on end.
    """
    if not isinstance(win, dict):
        c.error(where, "must be a table { from, to, reason } (or weekly { day, from, to, reason })")
        return
    for key in win:
        if key not in QUIET_WINDOW_KEYS:
            close = difflib.get_close_matches(str(key), QUIET_WINDOW_KEYS, n=1)
            c.warn(f"{where}.{key}", "unknown quiet-window key" + (f" (did you mean '{close[0]}'?)" if close else "") + "; ignored by the push gate")
    soft = win.get("urgent_ok", False)
    if not isinstance(soft, bool):
        c.error(f"{where}.urgent_ok", f"must be true or false (got {soft!r})")
        soft = False
    days = win.get("days", win.get("day"))
    if days not in (None, "", []):
        # Weekly window.
        day_list = days if isinstance(days, list) else [days]
        for d in day_list:
            if not isinstance(d, str) or str(d)[:3].title() not in DAYS:
                c.error(f"{where}.{'days' if 'days' in win else 'day'}", f"'{d}' is not a day (use one of {', '.join(DAYS)})")
        times = {}
        for k in ("from", "to"):
            v = win.get(k)
            text = v.strftime("%H:%M") if isinstance(v, dt.time) else v
            if not isinstance(text, str) or not TIME_RE.match(text.strip()):
                c.error(f"{where}.{k}", "required in a weekly window: a time \"HH:MM\" (24-hour)")
            else:
                times[k] = text.strip()
        if len(times) == 2 and times["to"] <= times["from"]:
            c.error(f"{where}.to", f"'{times['to']}' must be after 'from' ({times['from']}); a weekly window cannot run past midnight, split it in two")
        for k in ("since", "until"):
            if win.get(k) not in (None, ""):
                _check_date(c, f"{where}.{k}", win.get(k))
        return
    # Dated window.
    start = _window_moment(win.get("from"))
    if start is None:
        c.error(f"{where}.from", "required: a date (2027-01-25) or \"YYYY-MM-DD HH:MM\"")
    to_value = win.get("to")
    stop = _window_moment(to_value, end=True, base=start.date() if start else None)
    time_only = isinstance(to_value, dt.time) or (isinstance(to_value, str) and bool(TIME_RE.match(to_value.strip())))
    if stop is None and not (start is None and time_only):
        c.error(f"{where}.to", "required: a date (2027-01-25), \"YYYY-MM-DD HH:MM\", or \"HH:MM\" on the 'from' day")
    if start is None or stop is None:
        return
    if stop <= start:
        c.error(f"{where}.to", "is not after 'from'")
        return
    hours = (stop - start).total_seconds() / 3600
    if not soft and hours > HARD_WINDOW_MAX_HOURS:
        span = f"{hours / 24:.0f} days" if hours >= 48 else f"{hours:.0f} hours"
        c.warn(where, f"a hard window of {span} ({win.get('reason') or 'no reason given'}): every push is held for that "
                      "whole time, urgent ones too, and the heartbeat skips its runs. For a long period such as an exam "
                      "session add urgent_ok = true (ordinary pushes stay held, urgent and direct pushes pass, the "
                      "heartbeat keeps running)")


def _known_keys(catalog) -> tuple[set[str], set[str]]:
    """Known ``table.key`` names and known course keys (base + every module default)."""
    known: set[str] = set(REQUIRED) | {k.split(".")[0] for k in REQUIRED}
    course_keys: set[str] = set(COURSE_DEFAULTS) | set(COURSE_REQUIRED) | set(DERIVED_COURSE_KEYS) | {"language", "assistance"}
    tables = [BASE_DEFAULTS]
    if catalog is not None:
        for mod in catalog.modules.values():
            defaults = mod.defaults or {}
            tables.append({k: v for k, v in defaults.items() if k != "course"})
            if isinstance(defaults.get("course"), dict):
                course_keys |= set(defaults["course"])
    for table in tables:
        for top, val in table.items():
            known.add(top)
            if isinstance(val, dict):
                for k in val:
                    known.add(f"{top}.{k}")
    return known, course_keys


def validate(cfg: dict, *, catalog=None, vault: str | Path | None = None, raw: dict | None = None) -> list[Issue]:
    """Validate a *resolved* config. Returns issues (errors first)."""
    c = _Collector()

    # Required keys. Checked in the user's own file when we have it: a module's
    # fallback default (e.g. a placeholder term label) must not hide a missing key.
    for key in REQUIRED:
        value = _get(raw if raw is not None else cfg, key)
        if value in (None, "") or (isinstance(value, (list, dict)) and not value):
            c.error(key, "required key is missing or empty")

    # Types of every base key (catches "true" vs true, "3" vs 3 ...).
    for top, section in BASE_DEFAULTS.items():
        val = cfg.get(top)
        if val is None:
            continue
        if isinstance(section, dict):
            if not isinstance(val, dict):
                c.error(top, f"must be a table [{top}], got {_type_name(val)}")
                continue
            for key, default in section.items():
                if key in val and f"{top}.{key}" not in DATE_KEYS and not _same_kind(default, val[key]):
                    c.error(f"{top}.{key}", f"must be {_type_name(default)}, got {_type_name(val[key])} ({val[key]!r})")
        elif isinstance(section, list) and not isinstance(val, list):
            c.error(top, f"must be a list ([[{top}]] tables), got {_type_name(val)}")

    # Enums.
    for key, allowed in ENUMS.items():
        value = _get(cfg, key)
        if value is not None and value not in allowed:
            close = difflib.get_close_matches(str(value), allowed, n=1)
            c.error(key, f"'{value}' is not one of: {', '.join(allowed)}" + (f" (did you mean '{close[0]}'?)" if close else ""))

    # uni_os.version
    version = _get(cfg, "uni_os.version")
    if isinstance(version, str):
        try:
            want = tuple(int(p) for p in version.split(".")[:2])
            have = tuple(int(p) for p in __version__.split(".")[:2])
            if want > have:
                c.warn("uni_os.version", f"config written for {version}, these tools are {__version__}; update the framework")
        except ValueError:
            c.warn("uni_os.version", f"'{version}' is not a version like \"0.1.0\"")

    handle = _get(cfg, "student.handle")
    if isinstance(handle, str) and handle and not re.match(r"^[A-Za-z0-9_.-]+$", handle):
        c.warn("student.handle", "use letters, digits, '-', '_' or '.' only")
    for key in ("university.lms_url", "university.website", "notify.ntfy_server"):
        value = _get(cfg, key)
        if isinstance(value, str) and value and not re.match(r"^https?://", value):
            c.warn(key, f"'{value}' should start with https://")

    # Term dates.
    term = cfg.get("term") if isinstance(cfg.get("term"), dict) else {}
    week0 = _check_date(c, "term.week0_monday", term.get("week0_monday"), required=False)
    if week0 is not None and week0.weekday() != 0:
        c.error("term.week0_monday", f"{week0.isoformat()} is a {week0.strftime('%A')}; week 0 must start on a Monday")
    dates = {}
    for key in ("last_lecture_day", "lecture_free_from", "exam_session_start", "exam_session_end"):
        dates[key] = _check_date(c, f"term.{key}", term.get(key))
    if week0 and dates["last_lecture_day"] and dates["last_lecture_day"] <= week0:
        c.warn("term.last_lecture_day", "is before week 0")
    if dates["last_lecture_day"] and dates["lecture_free_from"] and dates["lecture_free_from"] <= dates["last_lecture_day"]:
        c.warn("term.lecture_free_from", "should be after term.last_lecture_day")
    if dates["exam_session_start"] and dates["exam_session_end"] and dates["exam_session_end"] < dates["exam_session_start"]:
        c.error("term.exam_session_end", "is before term.exam_session_start")
    if week0 and dates["exam_session_start"] and dates["exam_session_start"] < week0:
        c.warn("term.exam_session_start", "is before week 0 (exam session of the previous term?)")
    tz = term.get("timezone")
    if isinstance(tz, str) and tz:
        try:
            import zoneinfo

            zoneinfo.ZoneInfo(tz)
        except Exception:  # noqa: BLE001 - ZoneInfoNotFoundError, ValueError
            try:
                import zoneinfo

                if zoneinfo.available_timezones():
                    c.error("term.timezone", f"'{tz}' is not a known IANA time zone (e.g. \"Europe/Zurich\")")
                elif not re.match(r"^[A-Za-z_]+(/[A-Za-z0-9_+\-]+)+$|^UTC$", tz):
                    c.error("term.timezone", f"'{tz}' does not look like an IANA time zone")
                else:
                    # Typical on Windows: Python ships no time-zone database there.
                    c.info("term.timezone", "this computer's Python has no time-zone database, so 'today' uses the computer's own clock zone; `python -m pip install tzdata` makes it exact (matters on a server in another zone)")
            except Exception:  # pragma: no cover
                pass
    holidays = term.get("holidays", [])
    if not isinstance(holidays, list):
        c.error("term.holidays", "must be a list of { name, from, to } tables")
    else:
        for idx, hol in enumerate(holidays):
            where = f"term.holidays[{idx}]"
            if not isinstance(hol, dict):
                c.error(where, "must be a table { name = \"...\", from = 2026-11-20, to = 2026-11-20 }")
                continue
            if not isinstance(hol.get("name"), str) or not hol.get("name"):
                c.error(f"{where}.name", "required")
            start = _check_date(c, f"{where}.from", hol.get("from"), required=True)
            end = _check_date(c, f"{where}.to", hol.get("to"), required=True)
            if start and end and end < start:
                c.error(f"{where}.to", "is before 'from'")

    # Paths.
    agent_dir = _get(cfg, "paths.agent_dir", "_agent")
    _check_folder(c, "paths.agent_dir", agent_dir)
    inbox = _get(cfg, "paths.inbox", "inbox")
    if isinstance(inbox, str):
        problem = paths.check_relpath(inbox)
        if problem:
            c.error("paths.inbox", f"'{inbox}' is not a valid vault-relative folder: {problem}")
    never_open = _get(cfg, "paths.never_open", [])
    if not isinstance(never_open, list) or any(not isinstance(p, str) for p in never_open):
        c.error("paths.never_open", "must be a list of glob patterns (text)")
    if agent_dir != "_agent":
        c.warn("paths.agent_dir", "changing it is not recommended: every document refers to _agent/")

    # Study.
    formats = _get(cfg, "study.formats")
    if isinstance(formats, list):
        bad = [f for f in formats if f not in FORMATS]
        if bad:
            c.error("study.formats", f"unknown format(s) {bad}; use a subset of {list(FORMATS)}")
        if not formats:
            c.error("study.formats", "pick at least one of html, md, pdf")
        if len(set(formats)) != len(formats):
            c.warn("study.formats", "contains duplicates")
    chunk = _get(cfg, "study.chunk_words")
    if isinstance(chunk, int) and not isinstance(chunk, bool) and not 100 <= chunk <= 5000:
        c.warn("study.chunk_words", f"{chunk} is unusual (the original used 700-800 words per chunk)")
    rules = _get(cfg, "agent.reply_rules")
    if isinstance(rules, list) and any(not isinstance(r, str) for r in rules):
        c.error("agent.reply_rules", "must be a list of text lines")

    # Courses.
    courses = cfg.get("courses", [])
    if isinstance(courses, list):
        if not courses:
            c.warn("courses", "no [[courses]] yet: most modules need at least one course")
        _validate_courses(c, courses, agent_dir, inbox)

    # Schedule.
    if isinstance(cfg.get("schedule"), dict):
        _check_schedule(c, cfg["schedule"], "schedule")

    # Notify.
    quiet = _get(cfg, "notify.quiet_hours")
    if isinstance(quiet, str) and quiet and not TIME_RANGE_RE.match(quiet):
        c.error("notify.quiet_hours", f"'{quiet}' must look like \"21:00-07:30\" (or be empty)")
    for key in ("notify.max_per_day", "notify.min_gap_hours", "notify.dedupe_hours", "vm.budget_month"):
        value = _get(cfg, key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
            c.error(key, "must not be negative")
    windows = _get(cfg, "notify.quiet_windows", [])
    if isinstance(windows, list):
        for idx, win in enumerate(windows):
            _check_quiet_window(c, f"notify.quiet_windows[{idx}]", win)
    topic_file = _get(cfg, "notify.ntfy_topic_file")
    if vault and isinstance(topic_file, str) and topic_file:
        tf = paths.expand(topic_file)
        if not tf.is_absolute():
            tf = Path(vault) / tf
        if paths.is_within(tf, Path(vault)):
            c.error("notify.ntfy_topic_file", "points inside the vault; secrets must live outside it (e.g. ~/.config/uni-os/ntfy-topic)")

    # Modules.
    enabled = _get(cfg, "modules.enabled", [])
    if not isinstance(enabled, list) or any(not isinstance(m, str) for m in enabled):
        c.error("modules.enabled", "must be a list of module ids")
    else:
        dupes = sorted({m for m in enabled if enabled.count(m) > 1})
        if dupes:
            c.warn("modules.enabled", f"listed twice: {', '.join(dupes)}")
        if catalog is not None:
            for mid in enabled:
                if mid not in catalog.modules:
                    close = difflib.get_close_matches(mid, list(catalog.modules), n=1)
                    c.error("modules.enabled", f"unknown module '{mid}'" + (f" (did you mean '{close[0]}'?)" if close else ""))

    # Secrets must never be in the config.
    for key, value in flatten(raw if raw is not None else cfg):
        last = key.rsplit(".", 1)[-1].lower()
        if isinstance(value, str) and value and re.search(r"(^|_)(token|api_?key|apikey|secret|password|passwd)$", last):
            c.error(key, "looks like a secret; secrets never go in the config or the vault. Store it in a file outside the vault and point to it with a *_file key")
        if isinstance(value, str):
            for hit in _secrets.scan_value(value):
                if hit.level == "error":
                    c.error(key, f"contains a {hit.description} ({hit.redacted}); remove it, secrets never go in the config")

    # Unknown keys (typo detection) - warnings only.
    if raw is not None:
        known, course_keys = _known_keys(catalog)
        for top, val in raw.items():
            if top not in known:
                close = difflib.get_close_matches(top, sorted(k for k in known if "." not in k), n=1)
                c.warn(top, "unknown table" + (f" (did you mean [{close[0]}]?)" if close else ""))
                continue
            if isinstance(val, dict) and top not in ("modules",):
                for key in val:
                    name = f"{top}.{key}"
                    if top == "term" and key in DERIVED_TERM_KEYS:
                        c.warn(name, "is computed by the tools (from term.week0_monday and term.last_lecture_day) and "
                                     "your value is ignored; remove this line")
                    elif name not in known:
                        close = difflib.get_close_matches(name, sorted(known), n=1)
                        c.warn(name, "unknown key" + (f" (did you mean '{close[0]}'?)" if close else "") + "; ignored unless a module uses it")
        for idx, course in enumerate(raw.get("courses", []) if isinstance(raw.get("courses"), list) else []):
            if isinstance(course, dict):
                for key in course:
                    if key not in course_keys:
                        close = difflib.get_close_matches(key, sorted(course_keys), n=1)
                        c.warn(f"courses[{idx}].{key}", "unknown course key" + (f" (did you mean '{close[0]}'?)" if close else ""))
                assessments = course.get("assessments")
                label = course.get("id") if isinstance(course.get("id"), str) and course.get("id") else None
                base = f"courses.{label}" if label else f"courses[{idx}]"
                for aidx, item in enumerate(assessments if isinstance(assessments, list) else []):
                    if not isinstance(item, dict):
                        continue
                    for key in item:
                        if key not in ASSESSMENT_KEYS:
                            close = difflib.get_close_matches(str(key), ASSESSMENT_KEYS, n=1)
                            c.warn(f"{base}.assessments[{aidx}].{key}", "unknown assessment key"
                                   + (f" (did you mean '{close[0]}'?)" if close else "")
                                   + f"; known: {', '.join(ASSESSMENT_KEYS)}")
        for alias, canon in STUCK_ALIASES.items():
            value = _get(raw, alias)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                scope = "the heartbeat rules" if alias.startswith("heartbeat.") else "the always-on host's check"
                c.info(alias, f"old alias: {value} overrides {canon} for {scope} only; prefer setting {canon} "
                              "(the one stuck-note threshold every sender uses) and remove this line")
        if catalog is not None:
            _check_keys_of_disabled_modules(c, cfg, raw, catalog)

    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(c.issues, key=lambda i: order.get(i.level, 3))


#: Tables never checked for keys of modules that are not enabled.
_NO_OWNER_TABLES = ("uni_os", "modules", "courses")
_ABSENT = object()


def _dict_leaves(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """``(dotted_key, value)`` for every non-table value; lists (also of tables) are leaves."""
    if not isinstance(value, dict) or (not value and prefix):
        return [(prefix, value)] if prefix else []
    out: list[tuple[str, Any]] = []
    for key, val in value.items():
        out.extend(_dict_leaves(val, f"{prefix}.{key}" if prefix else str(key)))
    return out


def _prefixes(key: str) -> list[str]:
    """``a.b.c`` -> ``["a.b.c", "a.b", "a"]`` (longest first)."""
    parts = key.split(".")
    return [".".join(parts[:i]) for i in range(len(parts), 0, -1)]


def _enabled_for_check(cfg: dict, raw: dict, catalog) -> set[str] | None:
    """The enabled modules, dependencies included (``None`` if they cannot be resolved)."""
    from . import modules as _modules

    listed = _get(cfg, "modules.enabled")
    if not isinstance(listed, list) or not listed:
        listed = _modules.requested_from_config(raw)
    known = [m for m in listed if isinstance(m, str) and m in catalog.modules]
    try:
        return set(_modules.resolve(known, catalog))
    except Exception:  # noqa: BLE001 - a dependency cycle: reported as a module problem elsewhere
        return None


def _check_keys_of_disabled_modules(c: _Collector, cfg: dict, raw: dict, catalog) -> None:
    """Note values you set that only modules which are not enabled read.

    A key belongs to the modules whose ``[defaults]`` define it; the modules whose
    ``config_keys`` name it read it too. Skipped: keys of the base defaults (any template
    or tool may read those), keys no module defines (the unknown-key check covers them),
    keys an enabled module defines or reads, and values equal to the module's default
    (left over from the example config, harmless). What is left is a setting that does
    nothing until its module is enabled. That is a note, not a warning: ``disable`` keeps
    a module's settings in the file on purpose, so enabling it again restores them, and a
    full example config used with a smaller preset carries such values too.
    """
    enabled = _enabled_for_check(cfg, raw, catalog)
    if enabled is None:
        return
    base = {key for key, _ in _dict_leaves(BASE_DEFAULTS)}
    owners: dict[str, set[str]] = {}
    readers: dict[str, set[str]] = {}
    for mid, mod in catalog.modules.items():
        defaults = {k: v for k, v in (mod.defaults or {}).items() if k != "course"}
        for key, _ in _dict_leaves(defaults):
            owners.setdefault(key, set()).add(mid)
        for key in mod.config_keys or []:
            if isinstance(key, str):
                readers.setdefault(key, set()).add(mid)
    reported: set[str] = set()
    for leaf, _value in _dict_leaves(raw):
        if leaf.split(".")[0] in _NO_OWNER_TABLES:
            continue
        prefixes = _prefixes(leaf)
        if any(p in base for p in prefixes):
            continue
        owned = next((p for p in prefixes if p in owners), None)
        if owned is None or owned in reported:
            continue
        mods = owners[owned]
        who_reads = set(mods).union(*(readers.get(p, set()) for p in prefixes))
        if who_reads & enabled:
            continue
        value = _get(raw, owned, _ABSENT)
        if any(_get(catalog.modules[m].defaults or {}, owned, _ABSENT) == value for m in mods):
            continue
        reported.add(owned)
        names = sorted(mods)
        if len(names) == 1:
            c.info(owned, f"is set, but its module {names[0]} is not enabled, so the value has no effect "
                          f"(enable the module with `uni-os enable {names[0]}`, or remove the line)")
        else:
            c.info(owned, f"is set, but none of its modules ({', '.join(names)}) is enabled, so the value has no "
                          "effect (enable one of them with `uni-os enable <id>`, or remove the line)")


def _validate_courses(c: _Collector, courses: list, agent_dir: Any, inbox: Any) -> None:
    seen: dict[str, dict[str, int]] = {"id": {}, "slug": {}, "folder": {}, "short": {}}
    reserved = {f.lower() for f in RESERVED_FOLDERS}
    if isinstance(agent_dir, str):
        reserved.add(agent_dir.lower())
    if isinstance(inbox, str):
        reserved.add(inbox.split("/")[0].lower())
    for idx, course in enumerate(courses):
        where = f"courses[{idx}]"
        if not isinstance(course, dict):
            c.error(where, "must be a [[courses]] table")
            continue
        label = course.get("id") if isinstance(course.get("id"), str) else idx
        where = f"courses[{idx}]" if label == idx else f"courses.{label}"
        for key in COURSE_REQUIRED:
            if not course.get(key):
                c.error(f"{where}.{key}", "required")
        cid = course.get("id")
        if isinstance(cid, str) and cid and not ID_RE.match(cid):
            c.error(f"{where}.id", f"'{cid}' must be lowercase letters/digits/'-'/'_' starting with a letter")
        slug = course.get("slug")
        if isinstance(slug, str) and slug and not SLUG_RE.match(slug):
            c.error(f"{where}.slug", f"'{slug}' must be lowercase-kebab-case (used in file names like {slug.lower()}-error-log.md)")
        folder = course.get("folder")
        if folder:
            _check_folder(c, f"{where}.folder", folder)
            if isinstance(folder, str) and folder.lower() in reserved:
                c.error(f"{where}.folder", f"'{folder}' collides with a vault system folder")
        for key in ("id", "slug", "folder", "short"):
            value = course.get(key)
            if isinstance(value, str) and value:
                norm = value.lower()  # Windows and macOS file systems are case-insensitive
                if norm in seen[key]:
                    msg = f"'{value}' is used by more than one course"
                    (c.warn if key == "short" else c.error)(f"{where}.{key}", msg)
                seen[key][norm] = idx
        for key in ("colour", "colour_light"):
            value = course.get(key)
            if value not in (None, "") and (not isinstance(value, str) or not HEX_RE.match(value)):
                c.error(f"{where}.{key}", f"'{value}' is not a hex colour like \"#1e66f5\"")
        for key in ("lecture_slots", "exercise_slots"):
            slots = course.get(key, [])
            if not isinstance(slots, list):
                c.error(f"{where}.{key}", "must be a list like [\"Mon 10:15-12:00\"]")
                continue
            for slot in slots:
                if not isinstance(slot, str) or not SLOT_RE.match(slot):
                    c.warn(f"{where}.{key}", f"'{slot}' does not follow \"Ddd HH:MM-HH:MM\" (e.g. \"Tue 10:15-12:00\"); agents read it as free text")
        subs = course.get("official_subfolders", [])
        if not isinstance(subs, list):
            c.error(f"{where}.official_subfolders", "must be a list of folder names")
        else:
            for sub in subs:
                problem = paths.check_relpath(sub) if isinstance(sub, str) else "must be text"
                if problem:
                    c.error(f"{where}.official_subfolders", f"'{sub}': {problem}")
        hw = course.get("handwritten_folder", "")
        if not isinstance(hw, str):
            c.error(f"{where}.handwritten_folder", "must be a folder name (\"\" = \"<folder> handwritten\")")
        elif hw.strip("/"):
            problem = paths.check_relpath(hw.strip("/"))
            if problem:
                c.error(f"{where}.handwritten_folder", f"'{hw}': {problem}")
        streams = course.get("error_log_streams", ["main"])
        if not isinstance(streams, list) or not streams:
            c.error(f"{where}.error_log_streams", "must be a non-empty list like [\"main\"] or [\"theory\", \"programming\"]")
        else:
            for s in streams:
                if not isinstance(s, str) or not SLUG_RE.match(s):
                    c.error(f"{where}.error_log_streams", f"'{s}' must be lowercase-kebab-case (it becomes part of a file name)")
            if len(set(streams)) != len(streams):
                c.error(f"{where}.error_log_streams", "contains duplicates")
        assistance = course.get("assistance")
        if assistance is not None and assistance not in ASSISTANCE:
            c.error(f"{where}.assistance", f"'{assistance}' is not one of: {', '.join(ASSISTANCE)}")
        for key in ("notes", "lecturers"):
            value = course.get(key, [])
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                c.error(f"{where}.{key}", "must be a list of text lines")
        assessments = course.get("assessments", [])
        if not isinstance(assessments, list):
            c.error(f"{where}.assessments", "must be a list of [[courses.assessments]] tables")
        else:
            for aidx, item in enumerate(assessments):
                awhere = f"{where}.assessments[{aidx}]"
                if not isinstance(item, dict):
                    c.error(awhere, "must be a table")
                    continue
                if not item.get("name"):
                    c.error(f"{awhere}.name", "required")
                if item.get("kind") not in ASSESSMENT_KINDS:
                    c.error(f"{awhere}.kind", f"'{item.get('kind')}' is not one of: {', '.join(ASSESSMENT_KINDS)}")
                if item.get("counts_for") not in COUNTS_FOR:
                    c.error(f"{awhere}.counts_for", f"'{item.get('counts_for')}' is not one of: {', '.join(COUNTS_FOR)}")
                if item.get("assistance") not in ASSISTANCE:
                    c.error(f"{awhere}.assistance", f"'{item.get('assistance')}' is not one of: {', '.join(ASSISTANCE)}")
                pm = item.get("points_max", 0)
                if not isinstance(pm, (int, float)) or isinstance(pm, bool) or pm < 0:
                    c.error(f"{awhere}.points_max", "must be a number >= 0 (0 = unknown)")
                sittings = item.get("dates", [])
                if not isinstance(sittings, list):
                    c.error(f"{awhere}.dates", "must be a list like [\"2026-11-19 08:00\", \"2026-12-03\"]")
                else:
                    for d in sittings:
                        if not isinstance(d, dt.date) and not (isinstance(d, str) and DATE_OR_DATETIME_RE.match(d.strip())):
                            c.error(f"{awhere}.dates", f"'{d}' is not \"YYYY-MM-DD\" or \"YYYY-MM-DD HH:MM\"")
                for key in ("schedule", "scope"):
                    if key in item and not isinstance(item[key], str):
                        c.error(f"{awhere}.{key}", "must be text")
        bonus = course.get("bonus", {})
        if not isinstance(bonus, dict):
            c.error(f"{where}.bonus", "must be a table [courses.bonus]")
        else:
            if bonus.get("scheme") not in BONUS_SCHEMES:
                c.error(f"{where}.bonus.scheme", f"'{bonus.get('scheme')}' is not one of: {', '.join(BONUS_SCHEMES)}")
            mb = bonus.get("max_bonus", 0)
            if not isinstance(mb, (int, float)) or isinstance(mb, bool) or mb < 0:
                c.error(f"{where}.bonus.max_bonus", "must be a number >= 0")
