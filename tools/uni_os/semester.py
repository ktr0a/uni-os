"""Term-week arithmetic and the date formats used across the vault.

Rules (also in ``config/schema.md``, ``[term]``, and ``docs/file-formats.md``):

- Week 0 is the Monday ``term.week0_monday``; week *n* starts ``week0 + 7n`` days.
  Days before week 0 belong to negative weeks.
- Dates in text are written ``Ddd D Mon YYYY`` (``Mon 26 Oct 2026``), times
  ``HH:MM`` local; week file names use the zero-padded number (``week-07.md``).
- "Today" is computed in the term's time zone (``term.timezone``), so a VM in UTC
  and a laptop in Zurich agree on the date. ``$UNI_OS_TODAY`` (YYYY-MM-DD)
  overrides it for tests and reproducible runs.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from .config import as_date
from .errors import ConfigError

ENV_TODAY = "UNI_OS_TODAY"


def week0(cfg: dict) -> dt.date:
    """The Monday of week 0 (``term.week0_monday``)."""
    term = cfg.get("term") if isinstance(cfg.get("term"), dict) else {}
    value = as_date(term.get("week0_monday"))
    if value is None:
        raise ConfigError("term.week0_monday is missing or not a date (YYYY-MM-DD)")
    return value


def today(cfg: dict | None = None) -> dt.date:
    """Today's date in the term time zone (or ``$UNI_OS_TODAY``)."""
    env = os.environ.get(ENV_TODAY)
    if env:
        parsed = as_date(env)
        if parsed is None:
            raise ConfigError(f"${ENV_TODAY}='{env}' is not a date (YYYY-MM-DD)")
        return parsed
    tz = None
    if cfg and isinstance(cfg.get("term"), dict):
        tz = cfg["term"].get("timezone")
    if tz:
        try:
            from zoneinfo import ZoneInfo

            return dt.datetime.now(ZoneInfo(tz)).date()
        except Exception:  # noqa: BLE001 - missing tz database: fall back to local time
            pass
    return dt.date.today()


def now(cfg: dict | None = None) -> dt.datetime:
    """The current local time in the term time zone (naive if unavailable)."""
    tz = None
    if cfg and isinstance(cfg.get("term"), dict):
        tz = cfg["term"].get("timezone")
    if tz:
        try:
            from zoneinfo import ZoneInfo

            return dt.datetime.now(ZoneInfo(tz))
        except Exception:  # noqa: BLE001
            pass
    return dt.datetime.now()


def week_of(date: Any, cfg: dict) -> int:
    """The term week number of ``date`` (week 0 = the week of ``term.week0_monday``)."""
    day = as_date(date)
    if day is None:
        raise ConfigError(f"'{date}' is not a date (YYYY-MM-DD)")
    return (day - week0(cfg)).days // 7


def week_bounds(number: int, cfg: dict) -> tuple[dt.date, dt.date]:
    """(Monday, Sunday) of week ``number``."""
    monday = week0(cfg) + dt.timedelta(days=7 * number)
    return monday, monday + dt.timedelta(days=6)


def fmt_day(day: dt.date, *, year: bool = True) -> str:
    """``Mon 26 Oct 2026`` (or ``Mon 26 Oct`` with ``year=False``)."""
    text = f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"
    return f"{text} {day.year}" if year else text


def week_label(monday: dt.date, sunday: dt.date) -> str:
    """``Mon 14 Sep to Sun 20 Sep 2026``; both years shown if the week spans New Year."""
    if monday.year != sunday.year:
        return f"{fmt_day(monday)} to {fmt_day(sunday)}"
    return f"{fmt_day(monday, year=False)} to {fmt_day(sunday)}"


def nn(number: int) -> str:
    """Zero-padded week number for file names (``7`` -> ``07``)."""
    return f"{number:02d}" if number >= 0 else str(number)


def week_info(number: int, cfg: dict, *, status: str = "current") -> dict:
    """The reserved ``week`` template root for ``uni-os new-week``."""
    monday, sunday = week_bounds(number, cfg)
    return {
        "number": number,
        "nn": nn(number),
        "monday": monday.isoformat(),
        "sunday": sunday.isoformat(),
        "label": week_label(monday, sunday),
        "status": status,
        "previous_nn": nn(number - 1),
        "next_nn": nn(number + 1),
    }


def phase(date: Any, cfg: dict) -> str:
    """Where in the term ``date`` falls.

    One of ``before-term``, ``holiday: <name>``, ``lectures``, ``lecture-free``,
    ``exam-session``, ``after-exams``. Unknown boundaries are skipped.
    """
    day = as_date(date)
    if day is None:
        raise ConfigError(f"'{date}' is not a date (YYYY-MM-DD)")
    term = cfg.get("term") if isinstance(cfg.get("term"), dict) else {}
    start = week0(cfg)
    if day < start:
        return "before-term"
    for hol in term.get("holidays") or []:
        if isinstance(hol, dict):
            frm, to = as_date(hol.get("from")), as_date(hol.get("to"))
            if frm and to and frm <= day <= to:
                return f"holiday: {hol.get('name', 'holiday')}"
    exam_start, exam_end = as_date(term.get("exam_session_start")), as_date(term.get("exam_session_end"))
    if exam_end and day > exam_end:
        return "after-exams"
    if exam_start and day >= exam_start:
        return "exam-session"
    last = as_date(term.get("last_lecture_day"))
    free = as_date(term.get("lecture_free_from"))
    if (free and day >= free) or (last and day > last):
        return "lecture-free"
    return "lectures"


def describe(date: Any, cfg: dict) -> dict:
    """Everything ``uni-os week`` prints, as a dict."""
    day = as_date(date)
    number = week_of(day, cfg)
    info = week_info(number, cfg)
    info.pop("status")
    info.update({"date": day.isoformat(), "day": fmt_day(day), "phase": phase(day, cfg)})
    return info


_MOMENT_TOKENS = [
    ("YYYY", "%Y"),
    ("MMMM", "%B"),
    ("MMM", "%b"),
    ("MM", "%m"),
    ("dddd", "%A"),
    ("ddd", "%a"),
    ("DD", "%d"),
    ("HH", "%H"),
    ("mm", "%M"),
]


def moment_format(when: dt.datetime, fmt: str) -> str:
    """Format a datetime with the common Moment.js tokens Obsidian templates use.

    Supported: ``YYYY MMMM MMM MM DD D dddd ddd HH mm``.
    """
    out = []
    i = 0
    while i < len(fmt):
        for token, code in _MOMENT_TOKENS:
            if fmt.startswith(token, i):
                out.append(when.strftime(code))
                i += len(token)
                break
        else:
            if fmt[i] == "D":
                out.append(str(when.day))
            else:
                out.append(fmt[i])
            i += 1
    return "".join(out)
