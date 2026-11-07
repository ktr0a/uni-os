#!/usr/bin/env python3
"""Reference parser for the progress module's file contracts (stdlib only, Python 3.9+).

The organisation layer of Uni OS keeps its state in plain Markdown that dashboards (the
cockpit plugin), the heartbeat pre-check, `uni-os doctor` and the scheduled jobs all read.
This file is the executable version of those contracts, as written in
modules/progress/README.md ("File formats") and in the vault's _agent/progress-tracking.md:

  * the done-status vocabulary of the "Due this week" table (verdict at the START of the cell)
  * the week page (frontmatter, the four headings, the `_To fill_` check-in marker)
  * which week the week-page job creates and which week a check-in covers
  * the parsed parts of progress/current-status.md (snapshot, self-ratings, next 10 days)

Other tools may import it or copy the rules; the unit tests in modules/progress/tests pin them.

CLI (read-only):
  python org_formats.py check <vault>          validate week pages and current-status.md
  python org_formats.py due <week-page.md>     print the parsed "Due this week" rows as JSON
  python org_formats.py targets [--date D] --week0 YYYY-MM-DD
                                                print the week-page target and check-in weeks
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

WEEK_HEADINGS = ["Due this week", "Results this week", "Notes", "End-of-week check-in"]
TODO_MARKER = "_To fill_"
WEEK_STATUSES = {"upcoming", "current", "done"}

DONE_WORDS = ["✓", "done", "submitted", "closed", "handed in", "uploaded", "dropped", "skipped"]
PENDING_WORDS = ["not reported", "pending", "not recorded"]
NO_BONUS_WORDS = ["none", "no", "feedback only"]
SOFT_PREFIXES = ["tutorial"]
SOFT_MARKERS = ["(tentative)"]

_SCORE_START = re.compile(r"^\d+(?:[.,]\d+)?\s*/\s*\d+(?:[.,]\d+)?")
_EMPHASIS = re.compile(r"^[\s*_]+")
_DAYTIME = re.compile(
    r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"(?:\s+(\d{4}))?(?:\s+(\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?)?"
)


# ---------------------------------------------------------------- Markdown helpers

def split_frontmatter(text: str) -> tuple[dict, str]:
    """Flat `key: value` frontmatter (enough for the org-layer files) and the body."""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta: dict = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    body = text[end + 4:]
    return meta, body.lstrip("\n")


def section(body: str, heading: str, level: int = 2) -> str | None:
    """Text under the first heading of `level` that starts with `heading`, up to the next heading of
    the same or a higher level. None when missing."""
    lines = body.splitlines()
    start = None
    pat = re.compile(r"^(#{1,6})\s+(.*)$")
    for i, line in enumerate(lines):
        m = pat.match(line)
        if not m:
            continue
        lvl = len(m.group(1))
        if start is None:
            if lvl == level and m.group(2).strip().lower().startswith(heading.lower()):
                start = i + 1
        elif lvl <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:]) if start is not None else None


def first_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Header and rows of the first pipe table in `text` (separator row skipped)."""
    header: list[str] = []
    rows: list[list[str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not header:
            header = cells
        elif all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        else:
            rows.append(cells)
    return header, rows


def plain(cell: str) -> str:
    return _EMPHASIS.sub("", cell or "").strip()


# ---------------------------------------------------------------- the done-status vocabulary

_TAP_MARK = re.compile(r"^done \([^)]*\btapped\)", re.I)


def _starts_with_word(s: str, w: str) -> bool:
    """`s` starts with `w` as a whole word (a symbol like the check mark needs no boundary)."""
    if not s.startswith(w):
        return False
    if not w[-1].isalnum():
        return True
    rest = s[len(w):]
    return rest == "" or not (rest[0].isalnum() or rest[0] == "_")


def status_state(cell: str) -> str:
    """'done' | 'not-released' | 'pending' | 'open' for a Status cell, in the cockpit's order:

    1. a Done-tap mark "done (<when>, tapped). Before: ..." is done;
    2. "not reported" / "pending" / "not recorded" anywhere is pending (wins over a done word:
       "submitted (score pending)" is pending until the score is in);
    3. done when the cell STARTS with a done word (whole word) or a score `x / y` (after emphasis);
       a cell that starts with "not" never does ("not done", "not submitted");
    4. "not released" marks a future item; anything else is open."""
    s = plain(cell).lower()
    if _TAP_MARK.match(s):
        return "done"
    if any(w in s for w in PENDING_WORDS):
        return "pending"
    if any(_starts_with_word(s, w) for w in DONE_WORDS) or _SCORE_START.match(s):
        return "done"
    if "not released" in s:
        return "not-released"
    return "open"


def is_done(cell: str) -> bool:
    return status_state(cell) == "done"


def is_soft(deadline_cell: str) -> bool:
    s = plain(deadline_cell).lower()
    return any(s.startswith(p) for p in SOFT_PREFIXES) or any(m in s for m in SOFT_MARKERS)


def no_bonus(bonus_cell: str) -> bool:
    s = plain(bonus_cell).lower()
    return s == "" or any(s == w or s.startswith(w + " ") or s.startswith(w + "(") for w in NO_BONUS_WORDS)


def parse_day_time(cell: str, year: int) -> dict | None:
    """First `Ddd D Mon[ YYYY][ HH:MM[-HH:MM]]` in the cell. `year` is the year to assume when none is
    written (pick it from the term: months before the term start belong to the next year)."""
    m = _DAYTIME.search(cell or "")
    if not m:
        return None
    y = int(m.group(4)) if m.group(4) else year
    d = dt.date(y, MONTHS.index(m.group(3)) + 1, int(m.group(2)))
    start = dt.time(int(m.group(5)), int(m.group(6))) if m.group(5) else None
    end = dt.time(int(m.group(7)), int(m.group(8))) if m.group(7) else None
    return {"date": d, "start": start, "end": end, "weekday_ok": WEEKDAYS[d.weekday()] == m.group(1)}


def year_for(month_abbr: str, week0: dt.date) -> int:
    """Year of a 'D Mon' date within a term that starts at week0 (dates before the start month are next year)."""
    month = MONTHS.index(month_abbr) + 1
    return week0.year + (1 if month < week0.month else 0)


# ---------------------------------------------------------------- week pages

_COLS = {
    "item": re.compile(r"item", re.I),
    "deadline": re.compile(r"official|deadline", re.I),
    "target": re.compile(r"target|sunday", re.I),
    "bonus": re.compile(r"bonus", re.I),
    "status": re.compile(r"status", re.I),
}


def due_rows(week_page: str) -> list[dict]:
    _, body = split_frontmatter(week_page)
    sec = section(body, "Due this week")
    if sec is None:
        return []
    header, rows = first_table(sec)
    idx = {}
    for key, pat in _COLS.items():
        for i, h in enumerate(header):
            if pat.search(h) and i not in idx.values():
                idx[key] = i
                break
    out = []
    for r in rows:
        get = lambda k: r[idx[k]] if k in idx and idx[k] < len(r) else ""
        if not any(c.strip() for c in r):
            continue
        out.append({
            "item": get("item"), "deadline": get("deadline"), "target": get("target"),
            "bonus": get("bonus"), "status": get("status"), "state": status_state(get("status")),
            "soft": is_soft(get("deadline")), "no_bonus": no_bonus(get("bonus")),
        })
    return out


def checkin_filled(week_page: str) -> bool:
    _, body = split_frontmatter(week_page)
    sec = section(body, "End-of-week check-in")
    return sec is not None and TODO_MARKER not in sec


def check_week_page(text: str, name: str = "") -> list[str]:
    problems = []
    meta, body = split_frontmatter(text)
    if meta.get("type") != "week":
        problems.append(f"{name}: frontmatter type is not 'week'")
    if not re.fullmatch(r"\d+", meta.get("week", "")):
        problems.append(f"{name}: 'week' is not a number")
    for key in ("start", "end"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get(key, "")):
            problems.append(f"{name}: '{key}' is not an ISO date")
    if meta.get("status") not in WEEK_STATUSES:
        problems.append(f"{name}: status '{meta.get('status')}' is not one of upcoming | current | done")
    m = re.fullmatch(r"week-(\d{2,})\.md", name) if name else None
    if m and meta.get("week", "").isdigit() and int(m.group(1)) != int(meta["week"]):
        problems.append(f"{name}: file name and 'week' disagree")
    last = -1
    for h in WEEK_HEADINGS:
        m2 = re.search(r"^## " + re.escape(h) + r"\b", body, re.M)
        if not m2:
            problems.append(f"{name}: heading '## {h}' missing")
        elif m2.start() < last:
            problems.append(f"{name}: heading '## {h}' out of order")
        else:
            last = m2.start()
    header, _ = first_table(section(body, "Due this week") or "")
    for key in ("item", "deadline", "target", "bonus", "status"):
        if not any(_COLS[key].search(h) for h in header):
            problems.append(f"{name}: 'Due this week' has no {key} column")
    return problems


# ---------------------------------------------------------------- which week

def term_week(day: dt.date, week0: dt.date) -> int:
    return (day - week0).days // 7


def monday_of(day: dt.date) -> dt.date:
    return day - dt.timedelta(days=day.weekday())


def week_page_target(today: dt.date) -> dt.date:
    """Monday of the week the week-page job creates: the coming week when run Fri-Sun, else this week
    (a late run on Mon-Thu still creates the current week's page if it is missing)."""
    if today.weekday() >= 4:
        return monday_of(today) + dt.timedelta(days=7)
    return monday_of(today)


def checkin_target(today: dt.date) -> dt.date:
    """Monday of the week a check-in covers: the current week when run Thu-Sun, the previous week when
    run Mon-Wed. A check-in every 2 weeks also covers the week before (oldest first)."""
    if today.weekday() >= 3:
        return monday_of(today)
    return monday_of(today) - dt.timedelta(days=7)


# ---------------------------------------------------------------- current-status.md

def parse_status(text: str) -> dict:
    _, body = split_frontmatter(text)
    snap = re.search(r"\*\*Snapshot:\s*(.*?)\*\*", body)
    ratings = {}
    sec = section(body, "Self-rated") or ""
    first = next((ln for ln in sec.splitlines() if ln.strip()), "")
    for part in first.split("·"):
        m = re.search(r"([A-Za-z][\w&+ -]*?)\s+~?\s*(\d{1,3}(?:\s*-\s*\d{1,3})?)\s*%", plain(part))
        if m:
            ratings[m.group(1).strip()] = m.group(2).replace(" ", "")
    nxt = []
    header, rows = first_table(section(body, "Next 10 days") or "")
    for r in rows:
        if len(r) >= 2 and (r[0].strip() or r[1].strip()):
            nxt.append({"when": r[0], "what": r[1]})
    return {
        "snapshot": snap.group(1).strip() if snap else None,
        "ratings": ratings,
        "next": nxt,
        "has": {h: section(body, h) is not None for h in
                ["Bonus standing", "Exercises", "Self-rated understanding", "Next 10 days"]},
    }


def check_status(text: str) -> list[str]:
    p = parse_status(text)
    problems = [] if p["snapshot"] else ["current-status.md: no '**Snapshot: ...**' line"]
    problems += [f"current-status.md: section '## {h}' missing" for h, ok in p["has"].items() if not ok]
    return problems


# ---------------------------------------------------------------- CLI

def _check(vault: Path) -> int:
    problems: list[str] = []
    weeks = sorted((vault / "progress" / "weeks").glob("week-*.md"))
    current = []
    for w in weeks:
        text = w.read_text(encoding="utf-8")
        problems += check_week_page(text, w.name)
        if split_frontmatter(text)[0].get("status") == "current":
            current.append(w.name)
    if len(current) > 1:
        problems.append("more than one week page has status current: " + ", ".join(current))
    status = vault / "progress" / "current-status.md"
    if status.exists():
        problems += check_status(status.read_text(encoding="utf-8"))
    else:
        problems.append("progress/current-status.md is missing")
    for p in problems:
        print("PROBLEM " + p)
    print(f"checked {len(weeks)} week page(s); {len(problems)} problem(s)")
    return 1 if problems else 0


def utf8_stdio():
    """Print UTF-8 whatever the console or pipe encoding is (a Windows pipe defaults to cp1252,
    which cannot encode many symbols that vault notes contain)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # not a real text stream (tests redirect to StringIO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("vault")
    d = sub.add_parser("due")
    d.add_argument("file")
    t = sub.add_parser("targets")
    t.add_argument("--date", default=None)
    t.add_argument("--week0", required=True)
    utf8_stdio()
    a = ap.parse_args(argv)
    if a.cmd == "check":
        return _check(Path(a.vault))
    if a.cmd == "due":
        print(json.dumps(due_rows(Path(a.file).read_text(encoding="utf-8")), indent=2, ensure_ascii=False))
        return 0
    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    w0 = dt.date.fromisoformat(a.week0)
    wp, ci = week_page_target(today), checkin_target(today)
    print(json.dumps({"today": today.isoformat(), "term_week": term_week(today, w0),
                      "week_page": {"monday": wp.isoformat(), "week": term_week(wp, w0)},
                      "check_in": {"monday": ci.isoformat(), "week": term_week(ci, w0)}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
