"""The deterministic side of the heartbeat (module `heartbeat`): no agent in here.

A port of the original system's `uni-heartbeat` tool, which itself ported the rule set
(`assess()`) of the student's system-overview dashboard so that the page, the pre-check
and the pushes never disagree. Generalised: every path, time and threshold comes from
the config (`[schedule]`, `[notify]`, `[heartbeat]`, `[term]`, `[paths]`, `[[courses]]`)
and the vault paths listed in ``docs/file-formats.md``; a rule whose module is not enabled, or whose input
file does not exist, is skipped (and listed under "can't see"), never treated as fine.

Levels: red = needs action, amber = watch, grey = unknown (never "fine").
Finding ids are stable across runs (the push gate dedupes on them, the flags file keeps
"since" by them, snoozes name them). A <slug> part is at most 50 characters (60 for file
and session names); a longer one ends in "-" plus 6 hex digits of the original text's
SHA-1 (see slug()):
  week:missing:<file>  week:two-current  week:status:<file>  week:next-missing:<file>
  week:checkin-empty:<file>  due:<item>:overdue|behind  due:<item>:result (candidate, not a flag)
  prep:today-missing:<date>  prep:today-unverified:<date>  prep:tomorrow-missing:<date>
  prep:gap:<date>  prep:gap-open:<date> (outcome check only)  inbox:stuck:<slug of the file name>
  job:<job>:failed|missed|did-not-fire  host:snapshot-stale  host:<part>  host:memory
  host:status-overall  host:part:<part>  host:status-old  host:alert:<hash>  host:oom:<day>  session:<name>:not-closed
  role:<role>:off|down  bonus:<course>:pace  watch:alert:<hash>  watch:missed-run
  outcome ids = the rule ids; every outcome sender (`outcomes`, the vm host's built-in check, the
  inbox poll's --push) uses exactly these ids and texts, and only ONE of them sends (outcome_sender)
The agent's own judgment flags use judgment:<topic>, duty:<row>, result:<item>, waiting:<item>.

Entry points (used by `uni-os heartbeat ...`): Context, compute, gate_decision, render,
watch, commit, append_log, tracker, ask, take_pending, rerun, outcomes, status.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

from uni_os import pushgate
from uni_os.pushgate import as_list, deep_get, iso, one_line, parse_when, to_local

# ---- defaults (must equal modules/heartbeat/module.toml [defaults.heartbeat]) ----------
DEFAULTS = {
    "act_mode": "safe",
    "safe_windows": [],
    "event_hours": "07:30-20:45",
    "event_cap": 2,
    "event_near_slot_min": 45,
    "event_min_gap_min": 30,
    "min_memory_mb": 600,
    "grace_min": 20,
    "inbox_stuck_hours": 0,       # alias: 0 = notify.inbox_stale_hours (the one threshold)
    "inbox_tap_stuck_hours": 0,   # alias: 0 = notify.inbox_stale_hours_taps
    "checkin_grace_hours": 16,
    "gap_open_hours": 24,
    "result_window_days": 7,
    "snapshot_file": "_agent/vm/snapshot.json",
    "snapshot_stale_min": 40,
    "jobs_log": "{state}/jobs.log",
    "flags_dir": "_agent/logs/flags",
    "block_log_glob": "",
    "non_study_block_prefixes": ["L:", "E:", "V:", "U:", "OP", "("],
    "done_words": ["✓", "done", "submitted", "closed", "handed in", "uploaded", "dropped", "skipped"],  # the progress done-status vocabulary
    "event_words": ["quiz", "timed", "oral", "exam", "midterm", "tutorial", "rehearsal", "test"],
    "on_demand_roles": ["course-files-fetch"],
    "ask_mode": "auto",
    "start_job_command": "",
    "rerun_allowed": ["study-prep-morning-check"],
    "outcome_prefix": "Outcome check: ",
}
# The one stuck-note threshold (module inbox-sync defaults it; every sender reads it).
STALE_DEFAULTS = {"inbox_stale_hours": 4, "inbox_stale_hours_taps": 14}
SCHEDULE_DEFAULTS = {
    "heartbeat": ["07:50", "13:05", "18:05"],
    "heartbeat_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "heartbeat_weekend": ["09:00", "17:40"],
    "heartbeat_weekend_days": ["Sun"],
}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/@+*-]{1,159}$")
TAP_RE = re.compile(r"_(quickview|cockpit)-(done|undo)-")
ASK_LOOKAHEAD_MIN = 15
ASK_GATE_ID = "heartbeat-ask"
EVENT_FRESH_MIN = 30


# ---- small helpers -----------------------------------------------------------------------
def slug(s, n=50):
    """Id part: lower case, runs of other characters -> "-", trimmed, at most n characters.
    A longer slug is cut and gets "-" plus the first 6 hex digits of the SHA-1 of the
    original text, so two long names that share their start never share an id; a slug of
    at most n characters is unchanged. The vm host's outcome-checks and inbox_poll.py use
    exactly this rule."""
    full = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")
    if len(full) <= n:
        return full or "x"
    head = full[:max(0, n - 7)].rstrip("-")
    tail = hashlib.sha1(str(s).encode("utf-8")).hexdigest()[:6]
    return head + "-" + tail if head else tail


def sha(t):
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()[:16]


def hm(t):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})", str(t))
    if not m:
        raise ValueError("not a HH:MM time: %r" % t)
    return int(m[1]), int(m[2])


def at_time(d, t):
    h, m = hm(t)
    return dt.datetime(d.year, d.month, d.day, h, m)


def as_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def fmt(d, now):
    if not d:
        return "unknown"
    t = d.strftime("%H:%M")
    return t + " today" if d.date() == now.date() else "%s %s" % (pushgate.fmt_day(d), t)


def ago(d, now):
    if not d:
        return "unknown"
    mins = round((now - d).total_seconds() / 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return "%d min ago" % mins
    h = round(mins / 60)
    return "%d h ago" % h if h < 48 else "%d days ago" % round(h / 24)


def frontmatter(text):
    m = re.match(r"﻿?---\r?\n(.*?)\r?\n---", text or "", re.S)
    out = {}
    for line in (m[1] if m else "").split("\n"):
        mm = re.match(r"^([\w-]+):\s*(.*)$", line)
        if mm:
            out[mm[1]] = mm[2].strip().strip('"').strip("'")
    return out


def table_rows(text, min_cells=2):
    """Markdown table -> (header cells or None, rows). Stops at the first non-table line."""
    header, rows, started = None, [], False
    for line in (text or "").split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
            continue
        if header is None:
            header = cells
            continue
        if len(cells) >= min_cells:
            rows.append(cells)
    return header, rows


def section(text, heading_re):
    m = re.search(r"^##\s+%s[^\n]*\n([\s\S]*?)(?=^##\s|\Z)" % heading_re, text or "", re.M | re.I)
    return m[1] if m else None


def parse_words(s, ref):
    """'Tue 3 Nov 23:59', '3 November', '3 Nov 2026 12:00', '2026-11-03 23:59' -> (datetime, has_time).
    `ref` (a date) picks the year when the text has none: the date nearest to `ref`. A date
    more than 180 days before `ref` belongs to the next year ('5 Jan' seen in December), one
    more than 180 days after it to the previous year ('28 Dec' seen in January)."""
    s = s or ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2}))?", s)
    try:
        if m:
            return dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0), int(m[5] or 0)), bool(m[4])
        m = re.search(r"(\d{1,2})\.? ([A-Z][a-z]{2})[a-z]*\.?(?: (\d{4}))?(?:,? (\d{1,2})[:.](\d{2}))?", s)
        if not m or m[2] not in MON:
            return None
        year = int(m[3]) if m[3] else ref.year
        d = dt.datetime(year, MON[m[2]], int(m[1]), int(m[4] or 0), int(m[5] or 0))
        if not m[3]:
            delta = (ref - d.date()).days
            if delta > 180:
                d = d.replace(year=year + 1)
            elif delta < -180:
                d = d.replace(year=year - 1)
        return d, bool(m[4])
    except ValueError:
        return None


def mem_available_mb():
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        return None
    return None


def hb_state_dir():
    if os.environ.get("UNI_OS_HEARTBEAT_STATE"):
        return Path(os.environ["UNI_OS_HEARTBEAT_STATE"]).expanduser()
    return pushgate.state_root() / "heartbeat"


def read_json_file(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def parse_conf(path):
    """job.conf -> dict. Uses ``uni_os.jobs.parse_conf`` when it is importable, else a minimal parser."""
    try:
        from uni_os import jobs as shared  # type: ignore
        if hasattr(shared, "parse_conf"):
            return dict(shared.parse_conf(path))
    except ImportError:
        pass
    out = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", s)
        if not m:
            continue
        v = m[2].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        else:
            v = re.sub(r"\s+#.*$", "", v)
        out[m[1]] = v
    return out


# ---- context -------------------------------------------------------------------------------
class Context:
    """Everything one heartbeat command needs: vault, config, now, settings, state dirs."""

    def __init__(self, vault, cfg=None, now=None, dry_run=False, force=False):
        self.vault = Path(vault)
        self.cfg = cfg if cfg is not None else pushgate.load_config(self.vault)
        self.tz = deep_get(self.cfg, "term.timezone")
        self.settings = pushgate.Settings.from_config(self.cfg, self.vault)
        self.now = now if now is not None else pushgate.now_local(self.tz)
        self.dry = pushgate.is_dry(dry_run)
        self.force = force or os.environ.get("UNI_OS_HEARTBEAT_FORCE") == "1"
        hb = dict(DEFAULTS)
        hb.update({k: v for k, v in (deep_get(self.cfg, "heartbeat", {}) or {}).items() if v is not None})
        self.hb = hb
        sched = dict(SCHEDULE_DEFAULTS)
        sched.update(deep_get(self.cfg, "schedule", {}) or {})
        self.schedule = sched
        self.agent = str(deep_get(self.cfg, "paths.agent_dir", "_agent") or "_agent").strip("/\\")
        self.inbox = str(deep_get(self.cfg, "paths.inbox", "inbox") or "inbox").strip("/\\")
        enabled = deep_get(self.cfg, "modules.enabled")
        self.enabled = set(enabled) if isinstance(enabled, list) else None
        self.state_dir = hb_state_dir()
        self.hb_dir = self.vault / self.agent / "heartbeat"
        t = deep_get(self.cfg, "term", {}) or {}
        self.week0 = as_date(t.get("week0_monday"))
        self.last_lecture = as_date(t.get("last_lecture_day"))
        self.exam_end = as_date(t.get("exam_session_end"))
        self.holidays = [(one_line(h.get("name") or "holiday"), as_date(h.get("from")), as_date(h.get("to")))
                         for h in (t.get("holidays") or []) if isinstance(h, dict)]

    # modules
    def on(self, module_id):
        return self.enabled is None or module_id in self.enabled

    def stuck_limits(self):
        """(hours, tap_hours) after which an inbox update note counts as stuck. The one
        threshold is notify.inbox_stale_hours / notify.inbox_stale_hours_taps; the old keys
        heartbeat.inbox_stuck_hours / inbox_tap_stuck_hours are aliases (0 = use notify.*)."""
        out = []
        for alias, canon in (("inbox_stuck_hours", "inbox_stale_hours"),
                             ("inbox_tap_stuck_hours", "inbox_stale_hours_taps")):
            v = self.hb.get(alias)
            try:
                if v not in (None, "") and float(v) > 0:
                    out.append(float(v))
                    continue
            except (TypeError, ValueError):
                pass
            c = deep_get(self.cfg, "notify." + canon)
            try:
                out.append(float(c) if c not in (None, "") and float(c) > 0 else float(STALE_DEFAULTS[canon]))
            except (TypeError, ValueError):
                out.append(float(STALE_DEFAULTS[canon]))
        return out[0], out[1]

    # paths and files (relative to the vault, forward slashes)
    def rel(self, rel):
        return rel.replace("_agent/", self.agent + "/", 1) if rel.startswith("_agent/") else rel

    def path(self, rel):
        return self.vault / self.rel(rel)

    def rd(self, rel):
        if not rel:
            return None
        try:
            with open(self.path(rel), encoding="utf-8") as f:
                return f.read().replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError):
            return None

    def read_any(self, spec):
        """Read a configured path: "{state}/..." = the uni-os state folder, "~/..." or an
        absolute path as it is, anything else relative to the vault."""
        if not spec:
            return None
        spec = str(spec)
        if spec.startswith("{state}"):
            p = pushgate.state_root() / spec[len("{state}"):].lstrip("/\\")
        elif spec.startswith("~") or os.path.isabs(spec):
            p = Path(os.path.expanduser(spec))
        else:
            return self.rd(spec)
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None

    def rjson(self, rel):
        t = self.rd(rel)
        try:
            return json.loads(t) if t else None
        except ValueError:
            return None

    def listdir(self, rel):
        try:
            return sorted(os.listdir(self.path(rel)))
        except OSError:
            return None

    def mtime(self, rel):
        """Modification time as wall-clock time in the term's zone (a cloud host often runs in UTC)."""
        try:
            ts = os.path.getmtime(self.path(rel))
        except OSError:
            return None
        z = pushgate.get_zone(self.tz)
        return dt.datetime.fromtimestamp(ts, z).replace(tzinfo=None) if z else dt.datetime.fromtimestamp(ts)

    def dry_dir(self):
        d = Path(os.environ.get("UNI_OS_HEARTBEAT_DRY_DIR") or (self.state_dir / "dry-run" / "latest"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    # term
    def week_of(self, d):
        if not self.week0:
            return None
        return (d - self.week0).days // 7

    def holiday(self, d):
        for name, a, b in self.holidays:
            if a and b and a <= d <= b:
                return name
        return None

    def in_lectures(self, d):
        if not self.week0 or d < self.week0:
            return False
        if self.last_lecture and d > self.last_lecture + dt.timedelta(days=6 - self.last_lecture.weekday()):
            return False
        return not self.holiday(d)

    def in_study_period(self, d):
        if not self.week0 or d < self.week0:
            return False
        end = self.exam_end or self.last_lecture
        if end and d > end:
            return False
        return not self.holiday(d)

    def outside_term(self, d):
        if not self.week0:
            return None
        if d < self.week0 - dt.timedelta(days=7):
            return "before the term (week 0 starts %s)" % self.week0.isoformat()
        end = self.exam_end or (self.last_lecture + dt.timedelta(days=60) if self.last_lecture else None)
        if end and d > end:
            return "after the term (ended %s)" % end.isoformat()
        return None

    # schedule helpers
    def slot_this_week(self, spec):
        """{day, time} -> that weekday's time in the current Mon-Sun week, or None."""
        if not isinstance(spec, dict) or not spec.get("day") or not spec.get("time"):
            return None
        day = str(spec["day"])[:3].title()
        if day not in WEEKDAYS:
            return None
        monday = self.now.date() - dt.timedelta(days=self.now.weekday())
        return at_time(monday + dt.timedelta(days=WEEKDAYS.index(day)), spec["time"])

    def heartbeat_slots(self):
        """[(weekday index 0=Mon, "HH:MM")] of the heartbeat jobs' own slots."""
        out = []
        for times_key, days_key in (("heartbeat", "heartbeat_days"), ("heartbeat_weekend", "heartbeat_weekend_days")):
            for d in as_list(self.schedule.get(days_key)):
                d = str(d)[:3].title()
                if d in WEEKDAYS:
                    out += [(WEEKDAYS.index(d), t) for t in as_list(self.schedule.get(times_key))]
        return out

    def next_heartbeat_slot(self):
        best = None
        for k in range(8):
            day = self.now.date() + dt.timedelta(days=k)
            for wd, t in self.heartbeat_slots():
                if wd == day.weekday():
                    s = at_time(day, t)
                    if s > self.now and (best is None or s < best):
                        best = s
        return best

    def acting(self):
        mode = os.environ.get("UNI_OS_HEARTBEAT_ACT_MODE") or str(self.hb.get("act_mode") or "safe")
        mode = "full" if mode == "full" else "safe"
        for w in self.hb.get("safe_windows") or []:
            hit = pushgate.window_hit(w, self.now)
            if hit:
                return mode, "safe", hit.replace("quiet window", "safe window")
        return mode, mode, None


# ---- findings --------------------------------------------------------------------------------
class Findings:
    def __init__(self):
        self.items = []

    def add(self, fid, level, text, source, where="", outcome=False, push=None):
        if not any(x["id"] == fid for x in self.items):
            self.items.append({"id": fid, "level": level, "text": one_line(text)[:300], "source": source,
                               "where": where, "outcome": bool(outcome), "push": push})


def prep_file(ctx, day, prep_state):
    """Newest prep note for a date: the highest -rN on disk (the prep contract: highest
    revision wins), else the prep state's prep_file_name if that file exists."""
    files = ctx.listdir("semester/prep") or []
    cands = [f for f in files if re.match(r"^prep-%s(-r(\d+))?\.md$" % re.escape(day), f)]
    if not cands:
        name = (((prep_state or {}).get("days") or {}).get(day) or {}).get("prep_file_name")
        if name and ctx.path("semester/prep/" + name).exists():
            return "semester/prep/" + name
        return None
    cands.sort(key=lambda f: int((re.search(r"-r(\d+)\.md$", f) or [0, 0])[1]))
    return "semester/prep/" + cands[-1]


def note_gaps(text):
    sec = section(text, r"Gaps")
    gaps = []
    for line in (sec or "").split("\n"):
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m and not re.match(r"^none\b", m[1].strip(), re.I):
            gaps.append(one_line(m[1]))
    if not gaps and frontmatter(text).get("status") == "ready-with-gaps":
        gaps.append("note marked ready-with-gaps")
    return gaps


def week_plan(ctx, n):
    files = ctx.listdir("semester/plans") or []
    best = None
    for f in files:
        m = re.match(r"^week-(\d+)-plan\.md$", f)
        if m and int(m[1]) <= n and (best is None or int(m[1]) > best[0]):
            best = (int(m[1]), f)
    return ("semester/plans/" + best[1], best[0]) if best else (None, None)


def checkin_filled(text):
    """True/False for the week page's check-in section; None if it has none."""
    body = section(text, r"[^\n]*check-in")
    if body is None:
        return None
    if re.search(r"_to fill_?", body, re.I):
        return False
    for line in body.split("\n"):
        s = line.strip()
        if not s or s.startswith("<!--") or s.startswith(">"):
            continue
        s = re.sub(r"^[-*]\s+", "", s).replace("**", "").strip()
        rest = s.partition(":")[2].strip() if ":" in s else s
        if rest:
            return True
    return False


def is_done(status, done_words):
    words = "|".join(re.escape(w) for w in done_words) or "done"
    return bool(re.match(r"^\s*\**\s*(?:\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?|%s)" % words, status or "", re.I))


def event_re(words):
    alts = "|".join("%s(?:s|es|zes)?" % re.escape(w) for w in words) or "quiz"
    return re.compile(r"\b(?:%s)\b" % alts, re.I)


# ---- the rule set ------------------------------------------------------------------------------
def assess(ctx, F):
    now, hb = ctx.now, ctx.hb
    today = now.date()
    a = {"week": ctx.week_of(today), "week_page": None, "due": [], "missing_results": [], "cantsee": [],
         "inbox": [], "jobs": {}, "bonus": [], "gaps": {}, "prep_state": None, "watch_alerts": []}
    grace = dt.timedelta(minutes=float(hb["grace_min"]))
    snap = {}

    def guarded(name, fn, *args):
        # A broken rule (odd file, bad config value) must not silence the others: it
        # becomes a grey finding ("unknown, never fine") and the report shows why.
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001
            F.add("rule-error:" + name, "grey", "Rule %s could not run: %s: %s" % (name, type(e).__name__, e),
                  "rule:" + name)
            return None

    guarded("weekly", _rule_weeks, ctx, F, a, grace)
    guarded("due", _rule_due, ctx, F, a)
    guarded("prep", _rule_prep, ctx, F, a, grace)
    guarded("inbox", _rule_inbox, ctx, F, a)
    snap = guarded("host", _rule_host, ctx, F, a)
    guarded("jobs", _rule_jobs, ctx, F, a, snap, grace)
    guarded("bonus", _rule_bonus, ctx, F, a)
    guarded("watch", _rule_vault_watch, ctx, F, a)
    guarded("results", _results_from_windows, ctx, a)
    a["cantsee"].append("Results only the student knows, until they report them (ask once a day at most).")
    a["cantsee"].append("Calendars: the agent reads them read-only through its connector; this pre-check cannot.")
    return a


def _rule_weeks(ctx, F, a, grace):
    if not ctx.on("progress"):
        return
    now, today = ctx.now, ctx.now.date()
    n = a["week"]
    if n is None:
        a["cantsee"].append("term.week0_monday is not set: week-page rules are off.")
        return
    names = ctx.listdir("progress/weeks")
    if names is None:
        a["cantsee"].append("progress/weeks/ does not exist yet.")
        return
    cur = "week-%02d.md" % n
    if cur not in names and "week-%d.md" % n in names:
        cur = "week-%d.md" % n
    nxt = "week-%02d.md" % (n + 1)
    a["week_page"] = "progress/weeks/" + cur
    if ctx.in_lectures(today) and n >= 0 and cur not in names:
        F.add("week:missing:" + cur, "red", "No page for the current term week (%s) in progress/weeks." % cur,
              "rule:weekly", "#weeks")
    current = []
    for name in names:
        if re.match(r"^week-\d+\.md$", name):
            if frontmatter(ctx.rd("progress/weeks/" + name)).get("status") == "current":
                current.append(name)
    if len(current) > 1:
        F.add("week:two-current", "amber", "%d week pages are marked status: current (%s); only the page of the "
              "term week should be." % (len(current), ", ".join(current)), "rule:weekly", "#weeks")
    wp = ctx.rd(a["week_page"])
    if wp:
        st = frontmatter(wp).get("status")
        if st and st != "current" and ctx.in_lectures(today):
            F.add("week:status:" + cur, "amber", "The current week page %s is marked status: %s (expected current)."
                  % (cur, st), "rule:weekly", "#weeks")
    if ctx.on("check-in"):
        slot = ctx.slot_this_week(ctx.schedule.get("week_page"))
        next_monday = today + dt.timedelta(days=7 - today.weekday())
        if slot and slot.weekday() != 0 and now >= slot + 2 * grace and ctx.in_lectures(next_monday) \
                and nxt not in names and "week-%d.md" % (n + 1) not in names:
            F.add("week:next-missing:" + nxt, "amber", "Next week's page (%s) was not created by the week-page job "
                  "(%s)." % (nxt, fmt(slot, now)), "rule:weekly", "#weeks")
        ci = ctx.schedule.get("check_in")
        every = str((ci or {}).get("every") or "week").lower() if isinstance(ci, dict) else "week"
        slot = ctx.slot_this_week(ci)
        if slot and every not in ("week", "weekly", "1 week", "1w"):
            a["cantsee"].append("Check-in every %r: the empty-check-in rule only knows weekly check-ins." % every)
        elif slot:
            if slot > now:
                slot -= dt.timedelta(days=7)
            hours = float(ctx.hb["checkin_grace_hours"])
            if slot + dt.timedelta(hours=hours) <= now < slot + dt.timedelta(days=3):
                wn = ctx.week_of(slot.date())
                page = "week-%02d.md" % wn
                if page not in names and "week-%d.md" % wn in names:
                    page = "week-%d.md" % wn
                text = ctx.rd("progress/weeks/" + page)
                if text and checkin_filled(text) is False:
                    F.add("week:checkin-empty:" + page, "amber", "The check-in section of %s is still empty %s after "
                          "the check-in slot (%s)." % (page, ago(slot, now).replace(" ago", ""), fmt(slot, now)),
                          "rule:weekly", "#weeks")


def _rule_due(ctx, F, a):
    if not ctx.on("progress") or not a["week_page"]:
        return
    wp = ctx.rd(a["week_page"])
    if not wp:
        return
    now = ctx.now
    ref = as_date(frontmatter(wp).get("start")) or now.date()
    sec = section(wp, r"Due")
    header, rows = table_rows(sec or "", 2)
    if not rows:
        return
    h = [c.lower() for c in (header or [])]

    def col(keys, default):
        for i, c in enumerate(h):
            if any(k in c for k in keys):
                return i
        return default

    i_dl, i_tg = col(["deadline", "due"], 1), col(["target"], 2)
    i_bo, i_st = col(["bonus", "counts", "points"], 3), col(["status"], 4)
    ev = event_re(as_list(ctx.hb["event_words"]))
    for c in rows:
        def cell(i):
            return c[i] if 0 <= i < len(c) else ""
        item, deadline, target, bonus, status = c[0], cell(i_dl), cell(i_tg), cell(i_bo), cell(i_st)
        if not item:
            continue
        done = is_done(status, as_list(ctx.hb["done_words"]))
        dl, tg = parse_words(deadline, ref), parse_words(target, ref)
        dl_at = (dl[0] if dl[1] else dl[0].replace(hour=23, minute=59)) if dl else None
        tg_at = tg[0].replace(hour=23, minute=59) if tg and not tg[1] else (tg[0] if tg else None)
        event = bool(ev.search(item + " " + deadline))
        sid = "due:" + slug(re.sub(r"[*_`]", "", item))
        verdict = "done" if done else "open"
        if not done and event and dl_at and dl_at < now:
            verdict = "took place; result not recorded"
            a["missing_results"].append({"id": sid + ":result", "item": item, "when": deadline, "bonus": bonus})
        elif not done and dl_at and dl_at < now:
            verdict = "overdue"
            F.add(sid + ":overdue", "red", "Overdue: %s (official deadline %s)." % (item, deadline), "rule:due",
                  "#progress")
        elif not done and tg_at and tg_at < now:
            verdict = "behind the personal target"
            F.add(sid + ":behind", "amber", "Behind the personal target: %s (target %s)." % (item, target),
                  "rule:due", "#progress")
        elif not done and dl_at and (dl_at - now).total_seconds() < 48 * 3600:
            verdict = "due within 48 h"
        a["due"].append({"id": sid, "item": item, "deadline": deadline, "deadline_at": dl_at.isoformat() if dl_at else None,
                         "target": target, "bonus": bonus, "status": status, "done": done, "event": event,
                         "verdict": verdict,
                         "hours_left": round((dl_at - now).total_seconds() / 3600, 1) if dl_at else None})


def _rule_prep(ctx, F, a, grace):
    if not ctx.on("daily-prep"):
        return
    now = ctx.now
    today, tomorrow = now.date(), now.date() + dt.timedelta(days=1)
    slots = sorted(as_list(ctx.schedule.get("daily_prep")), key=lambda t: hm(t))
    check = ctx.schedule.get("prep_check") or ""
    if not slots and not check:
        a["cantsee"].append("schedule.daily_prep and schedule.prep_check are empty: prep rules are off.")
        return
    ps = ctx.rjson("_agent/daily-prep/state.json")
    a["prep_state"] = ps
    days = (ps or {}).get("days") or {}
    td, tm = today.isoformat(), tomorrow.isoformat()

    def gaps_for(day):
        g = list(((days.get(day) or {}).get("gaps")) or [])
        rel = prep_file(ctx, day, ps)
        if not g and rel:
            g = note_gaps(ctx.rd(rel))
        return g, rel

    if ctx.in_study_period(today):
        g, rel = gaps_for(td)
        if not rel:
            due = at_time(today, check) + grace + dt.timedelta(minutes=10) if check else None
            if due is None or now >= due:
                F.add("prep:today-missing:" + td, "red", "No prep note for today (%s) in semester/prep." % td,
                      "rule:prep", "#prep", outcome=True, push="no prep note for today (%s)" % pushgate.fmt_day(now))
        else:
            if check and ps is not None and now >= at_time(today, check) + grace:
                ver = parse_when((days.get(td) or {}).get("verified"))
                if not (ver and to_local(ver, ctx.tz).date() == today):
                    F.add("prep:today-unverified:" + td, "amber", "Today's prep note (%s) was not verified by the "
                          "%s morning check." % (rel.split("/")[-1], check), "rule:prep", "#prep")
            if g:
                F.add("prep:gap:" + td, "amber", "Prep gap today: " + " | ".join(g), "rule:prep", "#prep")
                a["gaps"][td] = {"note": rel, "gaps": g}
    if ctx.in_study_period(tomorrow) and slots:
        g, rel = gaps_for(tm)
        first, last = at_time(today, slots[0]), at_time(today, slots[-1])
        if not rel:
            if now >= last + grace:
                F.add("prep:tomorrow-missing:" + tm, "red", "No prep note for tomorrow (%s) after the %s run(s)."
                      % (tm, ", ".join(slots)), "rule:prep", "#prep", outcome=True,
                      push="no prep note for %s yet" % pushgate.fmt_day(dt.datetime.combine(tomorrow, dt.time())))
            elif now >= first + grace:
                F.add("prep:tomorrow-missing:" + tm, "amber", "No prep note for tomorrow (%s) yet; the %s run should "
                      "have written it." % (tm, slots[0]), "rule:prep", "#prep")
        elif g:
            F.add("prep:gap:" + tm, "amber", "Prep gap tomorrow: " + " | ".join(g), "rule:prep", "#prep")
            a["gaps"][tm] = {"note": rel, "gaps": g}


def _rule_inbox(ctx, F, a):
    names = ctx.listdir(ctx.inbox)
    if names is None:
        return
    now = ctx.now
    note_h, tap_h = ctx.stuck_limits()
    for n in names:
        if n.lower() in ("inbox.md", "desktop.ini", "readme.md") or n.startswith("."):
            continue
        if ctx.path(ctx.inbox + "/" + n).is_dir():
            continue
        mod = ctx.mtime(ctx.inbox + "/" + n)
        age_h = (now - mod).total_seconds() / 3600 if mod else 0
        update = n.endswith("-update.md")
        tap = bool(TAP_RE.search(n))
        limit = tap_h if tap else note_h
        stuck = ctx.on("inbox-sync") and update and age_h >= limit
        a["inbox"].append({"title": n, "modified": mod.isoformat() if mod else None, "age_h": round(age_h, 1),
                           "update_note": update, "stuck": stuck})
        if stuck:
            what = "Done-tap note" if tap else "update note"
            F.add("inbox:stuck:" + slug(n, 60), "amber", "Inbox %s %s has waited %d h without being applied (limit %g h)."
                  % (what, n, age_h, limit), "rule:inbox", "#inbox", outcome=True,
                  # no file name in the push: names can contain personal details (the lock screen is public)
                  push=stuck_push_text(tap, limit))


def stuck_push_text(tap, limit):
    """The push text of a stuck-note alert. Every sender uses exactly this wording (the vm host's
    outcome-checks script and the inbox poll copy it), never with the file name."""
    return "%s waiting in the inbox for over %g h, not applied by the inbox sync" % (
        "Done-tap note" if tap else "update note", limit)


def _rule_host(ctx, F, a):
    now, hb = ctx.now, ctx.hb
    snap = ctx.rjson(hb["snapshot_file"]) if hb.get("snapshot_file") else None
    if snap is None:
        if ctx.on("vm") and ctx.enabled is not None:
            a["cantsee"].append("Host live state: %s unreadable or missing." % hb["snapshot_file"])
        else:
            a["cantsee"].append("Laptop scheduled tasks: no host snapshot, so missed slots can't be seen.")
    elif not snap.get("generated"):
        a["cantsee"].append("Host live state: the snapshot holds no write yet.")
        snap = None
    else:
        gen = to_local(parse_when(snap["generated"]), ctx.tz)
        host = snap.get("host") or {}
        if gen is None:
            a["cantsee"].append("Host snapshot time unreadable.")
        elif (now - gen).total_seconds() / 60 > float(hb["snapshot_stale_min"]):
            F.add("host:snapshot-stale", "red", "Host heartbeat stale: the snapshot was last written %s (expected every "
                  "15 min). The host, its vault mount or its health check may be down." % ago(gen, now), "rule:host", "#host")
        for k in ("mount_ok", "remote_control_ok", "agent_login_ok", "claude_login_ok"):
            if host.get(k) is False:
                F.add("host:" + k, "red", "Host reports %s = false." % k.replace("_", " "), "rule:host", "#host")
        mem = host.get("mem_available_mb")
        if isinstance(mem, (int, float)) and mem and mem < 500:
            F.add("host:memory", "red", "Host memory available is %d MB (under 500 MB)." % mem, "rule:host", "#host")
        elif isinstance(mem, (int, float)) and mem and mem < 700:
            F.add("host:memory", "amber", "Host memory available is %d MB (under 700 MB: idle job sessions get closed)."
                  % mem, "rule:host", "#host")
        # The laptop ping only matters for jobs in failover mode (the host runs a slot itself when
        # the laptop's copy missed it); in mode "always" there is no ping by design, so no note.
        lap = snap.get("laptop") or {}
        failover = sorted(j.get("name") or "?" for j in snap.get("jobs") or []
                          if j.get("mode") == "failover" and j.get("on") is not False)
        if failover and lap.get("online") is not True:
            a["cantsee"].append("Laptop not seen by the host%s: the host treats every slot of the failover jobs (%s) "
                                "as missed by the laptop and runs it itself; if the laptop is on, its ping task is not "
                                "reaching the host and both may run." % (
                                    " for " + ago(to_local(parse_when(lap.get("seen")), ctx.tz), now)
                                    if lap.get("seen") else "", ", ".join(failover)))
        on_demand = set(as_list(hb["on_demand_roles"]))
        for s in snap.get("job_sessions") or []:
            name = s.get("name", "")
            lim = s.get("closes_after_h") or 8
            started = to_local(parse_when(s.get("started")), ctx.tz)
            open_h = (now - started).total_seconds() / 3600 if started else None
            idle = s.get("idle_min")
            flag = ""
            if s.get("state") != "working" and idle is not None and idle > lim * 60 + 90:
                flag = "idle %d h, limit %s h" % (round(idle / 60), lim)
            elif s.get("state") != "working" and open_h is not None and open_h > lim + 1.5 and (idle is None or idle > lim * 60):
                flag = "open %d h, limit %s h" % (round(open_h), lim)
            if flag:
                F.add("session:%s:not-closed" % slug(name, 60), "amber", "Job session %s did not close: %s." % (name, flag),
                      "rule:host", "#host")
        for r in snap.get("roles") or []:
            name, state = r.get("role", ""), r.get("state", "")
            if state == "running" or name in on_demand:
                continue
            F.add("role:%s:%s" % (slug(name), state or "down"), "amber" if state == "off" else "red",
                  "Role session %s is %s." % (r.get("title") or name, state or "not running"), "rule:host", "#host")
        for t in snap.get("alerts") or []:
            t = t if isinstance(t, str) else json.dumps(t)
            lv = "red" if re.search(r"oom|swap|drive|mount|remote|login", t, re.I) else "amber"
            F.add("host:alert:" + hashlib.sha1(t.encode()).hexdigest()[:8], lv, "Host health alert: " + t, "rule:host", "#host")
    if ctx.on("vm") and ctx.enabled is not None:
        st = ctx.rd("_agent/vm/status.md")
        ov = re.search(r"\*\*Overall: ([^*]+)\*\*(?:\s*\(checked ([^)]*)\))?", st or "")
        if st and not ov:
            a["cantsee"].append("Host status: _agent/vm/status.md is not written yet (host not installed?).")
        elif ov:
            if not re.match(r"^ok\b", ov[1].strip(), re.I):
                F.add("host:status-overall", "red", "Host status file says overall: %s." % ov[1].strip(), "rule:host", "#host")
            # parts in its table that are not ok (DOWN, LOGGED OUT, ...): red
            _, parts = table_rows(st[ov.end():], 2)
            for c in parts:
                if re.search(r"\b(DOWN|LOGGED OUT|FAILED|MISSING)\b", c[1]):
                    F.add("host:part:" + slug(re.sub(r"`[^`]*`|\"[^\"]*\"|\([^)]*\)", "", c[0])), "red",
                          "Host status: %s is %s." % (re.sub(r"`[^`]*`", "", c[0]).strip(), c[1].strip()), "rule:host", "#host")
            checked = parse_words(ov[2], now.date()) if ov[2] else None
            mt = checked[0] if checked and checked[1] else ctx.mtime("_agent/vm/status.md")
            if mt and (now - mt).total_seconds() > 26 * 3600:
                F.add("host:status-old", "amber", "Host status file is old: last checked %s (it is rewritten at least "
                      "once a day)." % ago(mt, now), "rule:host", "#host")
        # OOM kills in the host's daily performance rows (last 3 days): red
        header, rows = table_rows(section(ctx.rd("_agent/vm/performance.md") or "", r"Daily") or "", 2)
        col = next((i for i, c in enumerate(header or []) if "oom" in c.lower()), None)
        for c in rows if col is not None else []:
            day = parse_words(c[0], now.date())
            n = re.match(r"^\s*(\d+)", c[col]) if col < len(c) else None
            if day and n and int(n[1]) > 0 and 0 <= (now.date() - day[0].date()).days <= 3:
                F.add("host:oom:" + slug(c[0]), "red", "OOM kill on the host on %s (%s): a session or job was killed for "
                      "lack of memory." % (c[0], n[1]), "rule:host", "#host")
    return snap


def _slots_due(conf, now, direction):
    """Slot datetimes of a job.conf (SLOTS + DAYS + DATES) around now."""
    slots = as_list(conf.get("SLOTS"))
    if not slots:
        return []
    days = [d[:3].title() for d in as_list(conf.get("DAYS"))] or WEEKDAYS
    dates = []
    for part in [p.strip() for p in str(conf.get("DATES") or "").split(";") if p.strip()]:
        a_, _, b_ = part.partition("..")
        da, db = as_date(a_), as_date(b_) if b_ else as_date(a_)
        if da and db:
            dates.append((da, db))
    out = []
    for k in range(9):
        d = now.date() + dt.timedelta(days=direction * k)
        if dates and not any(x <= d <= y for x, y in dates):
            continue
        if not dates and d.strftime("%a") not in days:
            continue
        for t in slots:
            try:
                out.append(at_time(d, t))
            except ValueError:
                pass
    return out


def _rule_jobs(ctx, F, a, snap, grace):
    now = ctx.now
    # 1. failure flags written by jobs ("write a flag" in the prompt anatomy)
    fdir = ctx.hb.get("flags_dir")
    for name in (ctx.listdir(fdir) or []) if fdir else []:
        if not name.endswith(".md"):
            continue
        text = ctx.rd(fdir + "/" + name) or ""
        fm = frontmatter(text)
        job = slug(fm.get("job") or name[:-3])
        body = [ln.strip() for ln in re.sub(r"^---[\s\S]*?---", "", text, count=1).split("\n")
                if ln.strip() and not ln.startswith("#")]
        lv = fm.get("level") if fm.get("level") in ("red", "amber", "grey") else "red"
        F.add("job:%s:failed" % job, lv, "Job %s wrote a failure flag%s: %s" % (
            job, (" at " + fm["at"]) if fm.get("at") else "", body[0] if body else name), "rule:jobs", "#jobs")
    # 2. the job runner's log (laptop scheduler or host runner, both write <state>/jobs.log):
    #    last run per job
    runs = {}
    jl = ctx.read_any(ctx.hb.get("jobs_log"))
    for m in re.finditer(r"^-?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \| ([\w.-]+) \| (.*)$", jl or "", re.M):
        at, job, rest = parse_when(m[1]), m[2], m[3]
        if "dry run" in rest:
            continue
        e = re.match(r"exit (\d+)", rest)
        rec = runs.setdefault(job, {"at": None, "exit": None, "skipped": None})
        if e:
            rec["at"], rec["exit"] = at, int(e[1])
        elif rest.startswith("skipped"):
            rec["skipped"] = at
    for job, rec in runs.items():
        recent = rec["at"] is not None and (now - rec["at"]).days < 7  # an old one-off failure is history
        if rec["exit"] not in (None, 0) and recent:
            F.add("job:%s:failed" % slug(job), "red", "Job %s failed: exit %s at %s." % (job, rec["exit"], fmt(rec["at"], now)),
                  "rule:jobs", "#jobs")
        a["jobs"][job] = {"state": "red" if rec["exit"] not in (None, 0) else "ok",
                          "note": "last run %s (exit %s)" % (fmt(rec["at"], now), rec["exit"]) if rec["at"] else "skipped"}
    # 3. the host snapshot: exit codes, missed slots (timetable from job.conf), did-not-fire
    if not snap:
        return
    for j in snap.get("jobs") or []:
        name = j.get("name") or ""
        on = j.get("on")
        last = to_local(parse_when(j.get("last_run")), ctx.tz)
        skipped = to_local(parse_when(j.get("last_skipped")), ctx.tz)
        nxt = to_local(parse_when(j.get("next_run")), ctx.tz)
        act = max([x for x in (last, skipped) if x], default=None)
        state, note = "grey", "not run yet"
        conf = parse_conf(ctx.path("_agent/jobs/%s/job.conf" % name))
        due = max([d for d in _slots_due(conf, now, -1) if d <= now], default=None)
        on_since = to_local(parse_when(j.get("on_since")), ctx.tz)
        if on is False:
            note = "switched off"
        elif j.get("exit") not in (None, 0):
            state, note = "red", "last run failed (exit %s)" % j.get("exit")
            F.add("job:%s:failed" % slug(name), "red", "Job %s failed: exit %s at %s." % (name, j.get("exit"), fmt(last, now)),
                  "rule:jobs", "#jobs")
        elif due and (now - due) > grace and (act is None or act < due) and (act or (on_since and due > on_since)):
            state, note = "red", "missed the %s slot" % fmt(due, now)
            F.add("job:%s:missed" % slug(name), "red", "Job %s missed its %s slot (last activity %s)." % (
                name, fmt(due, now), fmt(act, now)), "rule:jobs", "#jobs")
        elif not conf.get("SLOTS") and nxt and (now - nxt).total_seconds() > 1800 and (act is None or act < nxt):
            state, note = "red", "did not fire at " + fmt(nxt, now)
            F.add("job:%s:did-not-fire" % slug(name), "red", "Job %s did not fire at %s." % (name, fmt(nxt, now)),
                  "rule:jobs", "#jobs")
        elif act:
            state, note = "ok", ("skipped by its precheck " if act == skipped else "ran ") + fmt(act, now)
        a["jobs"][name] = {"state": state, "note": note}


def _rule_bonus(ctx, F, a):
    if not ctx.on("progress"):
        return
    for c in deep_get(ctx.cfg, "courses", []) or []:
        if not isinstance(c, dict) or not c.get("folder") or not c.get("slug"):
            continue
        fm = frontmatter(ctx.rd("%s/%s.md" % (c["folder"], c["slug"])))
        if not fm:
            continue
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", fm.get("bonus_banked", ""))]
        pct = re.search(r"(\d+(?:\.\d+)?)\s*%", fm.get("bonus_target", ""))
        row = {"course": c.get("id"), "banked": fm.get("bonus_banked"), "target": fm.get("bonus_target"),
               "next_bonus": fm.get("next_bonus"), "updated": fm.get("updated")}
        if pct and len(nums) > 1 and nums[1]:
            ratio, bar = round(nums[0] / nums[1], 3), float(pct[1]) / 100
            if ratio < bar:
                lv = "amber" if ratio >= bar - 0.05 else "red"
                F.add("bonus:%s:pace" % c.get("id"), lv, "%s bonus pace is %d %% of the points graded so far; the bar is "
                      "%d %%." % (c.get("short") or c.get("id"), round(ratio * 100), round(bar * 100)), "rule:bonus",
                      "#progress")
            row["ratio"] = ratio
        a["bonus"].append(row)


def _rule_vault_watch(ctx, F, a):
    if not ctx.on("vault-watch") or ctx.enabled is None:
        return
    now = ctx.now
    # Missed run: the laptop watcher writes one log line per run; no line since its last
    # slot + grace means the laptop was off or the task did not fire (amber: often expected).
    log = ctx.rd("_agent/vault-watch/log.md")
    times = as_list(ctx.schedule.get("vault_watch"))
    if log is not None and times:
        stamps = [parse_when(m[1]) for m in re.finditer(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \|", log, re.M)]
        last = max([s for s in stamps if s], default=None)
        due = None
        if last is None:  # never ran yet (not installed on the laptop): nothing to judge
            times = []
        for k in (0, 1):
            d = now.date() - dt.timedelta(days=k)
            for t in times:
                try:
                    s = at_time(d, t)
                except ValueError:
                    continue
                if s <= now and (due is None or s > due):
                    due = s
        grace = dt.timedelta(minutes=float(ctx.hb["grace_min"]) + 5)
        if due and now - due > grace and (last is None or last < due):
            F.add("watch:missed-run", "amber", "Vault watch (laptop) missed its %s run; last ran %s. Expected if the "
                  "laptop was off." % (fmt(due, now), fmt(last, now)), "rule:watch", "#watch")
    for m in re.finditer(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (\w+): (.*)$", ctx.rd("_agent/vault-watch/alerts.md") or "", re.M):
        d = parse_when(m[1])
        if d and 0 <= (now - d).total_seconds() < 86400:
            a["watch_alerts"].append({"at": d.isoformat(), "scope": m[2], "text": m[3]})
            hid = "watch:alert:" + hashlib.sha1(m[0].encode()).hexdigest()[:8]
            if re.search(r"conflict|Copy of|\(1\)", m[3]):
                F.add(hid, "amber", "Vault watch: " + m[3], "rule:watch", "#watch")
            elif re.search(r"deleted|missing", m[3], re.I):
                F.add(hid, "amber" if re.search("missing", m[3], re.I) else "grey",
                      "Vault watch (%s): %s" % (fmt(d, now), m[3]), "rule:watch", "#watch")


def _results_from_windows(ctx, a):
    """Graded fixtures (dated quiet windows) that ended recently: a result may be missing."""
    known = {m["id"] for m in a["missing_results"]}
    for reason, start, stop in pushgate.dated_windows_ended(ctx.settings, ctx.now, int(ctx.hb["result_window_days"])):
        rid = "result:" + slug(reason)
        if rid not in known:
            a["missing_results"].append({"id": rid, "item": reason, "when": start.strftime("%a %d %b %H:%M"),
                                         "bonus": "", "note": "graded fixture (quiet window); check the tracker log"})


# ---- blocks ----------------------------------------------------------------------------------
def blocks_for(ctx, day, prep_state, plan_rel, plan_week):
    """Planned blocks of a date: from its prep note's callouts, else the week plan."""
    rel = prep_file(ctx, day, prep_state)
    out, seen = [], set()
    if rel:
        for m in re.finditer(r"^>\s*\[!(\w[\w-]*)\][-+]?\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s+(.*)$",
                             ctx.rd(rel) or "", re.M):
            key = (m[2].zfill(5), m[3].zfill(5), m[4].strip()[:3])
            if key not in seen:
                seen.add(key)
                out.append({"start": m[2].zfill(5), "end": m[3].zfill(5), "title": m[4].strip(), "source": rel})
        if out:
            return out
    d = dt.date.fromisoformat(day)
    if plan_rel and plan_week == ctx.week_of(d):
        text = ctx.rd(plan_rel) or ""
        wd = d.strftime("%a")
        m = re.search(r"^- \*\*%s[a-z]*:?\*\*:?\s*(.*)$" % wd, text, re.M)
        if m:
            for b in re.split(r"\s+·\s+|\s+;\s+", m[1]):
                mm = re.match(r"\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2}) (.*)", b)
                if mm:
                    out.append({"start": mm[1].zfill(5), "end": mm[2].zfill(5), "title": mm[3].strip().rstrip("."),
                                "source": plan_rel})
        if not out:
            _, rows = table_rows(section(text, r"Blocks") or "", 2)
            for c in rows:
                mm = re.search(r"\b%s[a-z]*\.?\**\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})" % wd, c[0])
                if mm:
                    out.append({"start": mm[1].zfill(5), "end": mm[2].zfill(5), "title": c[1].strip("* "),
                                "source": plan_rel})
    return out


def block_kind(ctx, title):
    t = title.strip()
    for p in as_list(ctx.hb["non_study_block_prefixes"]):
        if p and t.upper().startswith(str(p).upper()):
            return "other"
    return "study"


def block_log_rows(ctx):
    g = ctx.hb.get("block_log_glob")
    rows = []
    if not g:
        return rows, []
    files = sorted(glob.glob(str(ctx.vault / g)))
    for path in files:
        rel = os.path.relpath(path, ctx.vault).replace(os.sep, "/")
        _, rs = table_rows(ctx.rd(rel), 2)
        rows += [{"date": c[0], "block": c[1], "file": rel} for c in rs]
    return rows, [os.path.relpath(p, ctx.vault).replace(os.sep, "/") for p in files]


# ---- memory: state.json, requests.md, snoozes --------------------------------------------
def read_state(ctx):
    s = ctx.rjson("_agent/heartbeat/state.json")
    return s if isinstance(s, dict) else {}


def request_snoozes(ctx):
    """'Stop telling me about X' lines in requests.md that name ids (or id prefixes ending
    in *) are honoured directly; free-text ones are mapped to ids by the agent run."""
    out = {}
    for line in (ctx.rd("_agent/heartbeat/requests.md") or "").split("\n"):
        m = re.match(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \| (snooze|resume) \| (.*?) \| (.*?)(?: \| (.*))?$", line.strip())
        if not m:
            continue
        ids = re.findall(r"`([^`\s]+)`", m[3]) or [t for t in m[3].split() if ":" in t and ID_RE.match(t)]
        until = None
        um = re.search(r"(\d{4}-\d{2}-\d{2})", m[4])
        if um:
            until = um[1]
        for i in ids:
            if not ID_RE.match(i):
                continue
            if m[2] == "resume":
                out.pop(i, None)
            else:
                out[i] = {"until": until, "why": "requests.md %s (%s)" % (m[1], one_line(m[5] or "unknown")),
                          "from": "requests.md"}
    return out


def snooze_for(fid, snoozes, today):
    for key, v in (snoozes or {}).items():
        v = v or {}
        hit = key == fid or (key.endswith("*") and fid.startswith(key[:-1]))
        if hit and (not v.get("until") or str(v["until"]) >= today):
            return v
    return None


def input_hashes(ctx, a, F, outcome_keys):
    n = a["week"] if a["week"] is not None else -1
    ps = a.get("prep_state")
    plan_rel, _ = week_plan(ctx, n)
    today, tomorrow = ctx.now.date().isoformat(), (ctx.now.date() + dt.timedelta(days=1)).isoformat()
    hashes = {}
    for label, rel in [("current-status", "progress/current-status.md"), ("week page", a["week_page"]),
                       ("week plan", plan_rel), ("prep today", prep_file(ctx, today, ps)),
                       ("prep tomorrow", prep_file(ctx, tomorrow, ps)), ("tracker log", "progress/tracker-log.md"),
                       ("duties", "_agent/heartbeat/duties.md"), ("requests", "_agent/heartbeat/requests.md")]:
        hashes[label] = sha(ctx.rd(rel) or "") if rel else "none"
    _, files = block_log_rows(ctx)
    hashes["block log"] = sha("".join(ctx.rd(f) or "" for f in files))
    hashes["inbox"] = sha("\n".join(x["title"] for x in a.get("inbox", [])))
    hashes["course cards"] = sha(json.dumps(a.get("bonus", []), sort_keys=True))
    hashes["rule verdicts"] = sha("\n".join(sorted("%s=%s" % (x["id"], x["level"]) for x in F.items if x["level"] != "grey")))
    hashes["outcome checks"] = sha("\n".join(sorted(outcome_keys)))
    return hashes


# ---- compute: findings + triggers ---------------------------------------------------------
def compute(ctx):
    now = ctx.now
    F = Findings()
    a = assess(ctx, F)
    st = read_state(ctx)
    snoozes = dict(st.get("snoozes") or {})
    snoozes.update(request_snoozes(ctx))
    flagged = st.get("flagged") or {}
    last_run = to_local(parse_when((st.get("last_run") or {}).get("at")), ctx.tz)
    outcome_keys = [x["id"] for x in F.items if x["outcome"]]
    hashes = input_hashes(ctx, a, F, outcome_keys)
    today = now.date().isoformat()
    for x in F.items:
        s = snooze_for(x["id"], snoozes, today)
        x["snoozed"] = bool(s)
        x["known_since"] = (flagged.get(x["id"]) or {}).get("first")
        x["last_pushed"] = (flagged.get(x["id"]) or {}).get("pushed")

    week = a["week"] if a["week"] is not None else -1
    plan_rel, plan_week = week_plan(ctx, week)
    rows, block_files = block_log_rows(ctx)
    blocks = []
    for k in (-1, 0, 1):
        d = now + dt.timedelta(days=k)
        label = pushgate.fmt_day(d)
        for b in blocks_for(ctx, d.date().isoformat(), a.get("prep_state"), plan_rel, plan_week):
            try:
                end, start = at_time(d.date(), b["end"]), at_time(d.date(), b["start"])
            except ValueError:
                continue
            logged = any(r["date"] in (label, d.date().isoformat()) and (b["start"] in r["block"] or b["start"].lstrip("0") in r["block"])
                         for r in rows)
            blocks.append(dict(b, date=d.date().isoformat(), day=label, kind=block_kind(ctx, b["title"]),
                               ended=end <= now, end_at=end.isoformat(), start_at=start.isoformat(), logged=logged))

    fired = []
    if not last_run:
        fired.append({"trigger": "first run", "detail": "no state.json with a last run yet"})
    prev = st.get("inputs") or {}
    changed = [k for k, v in hashes.items() if prev.get(k) != v] if last_run else []
    if changed:
        fired.append({"trigger": "inputs changed", "detail": ", ".join(changed)})
    lr = last_run or now - dt.timedelta(hours=6)
    for d in a["due"]:
        if d["done"] or not d["deadline_at"] or d["verdict"].startswith("took place"):
            continue
        dl = dt.datetime.fromisoformat(d["deadline_at"])
        for h in (24, 6):
            mark = dl - dt.timedelta(hours=h)
            if lr < mark <= now:
                fired.append({"trigger": "due in %d h" % h, "detail": "%s (deadline %s)" % (d["item"], d["deadline"]),
                              "id": d["id"], "hours": h})
    for b in blocks:
        end = dt.datetime.fromisoformat(b["end_at"])
        if b["kind"] == "study" and lr < end <= now:
            fired.append({"trigger": "block ended", "detail": "%s %s-%s %s%s" % (
                b["day"], b["start"], b["end"], b["title"], "" if b["logged"] or not block_files else " (no block-log row yet)")})
    old_keys = set(st.get("outcome_keys") or [])
    for x in F.items:
        if x["outcome"] and x["id"] not in old_keys and not x["snoozed"]:
            fired.append({"trigger": "outcome check", "detail": x["text"], "id": x["id"]})
    for x in F.items:
        if x["level"] == "red" and not x["snoozed"] and x["id"] not in flagged and not x["outcome"]:
            fired.append({"trigger": "new red", "detail": x["text"], "id": x["id"]})
    for w in a.get("watch_alerts", []):
        if dt.datetime.fromisoformat(w["at"]) > lr and re.search(r"conflict|Copy of|deleted|missing", w["text"], re.I):
            fired.append({"trigger": "vault-watch alert", "detail": w["text"]})

    mode, effective, why_safe = ctx.acting()
    ask_test = (ctx.state_dir / "ask-test-due").exists()
    sender, sender_why = outcome_sender(ctx)
    return {"now": iso(now, ctx.tz), "weekday": now.strftime("%a"), "term_week": a["week"],
            "act_mode": mode, "effective_acting": effective, "safe_because": why_safe,
            "ask_test_due": ask_test, "ask_mode": ask_mode(ctx), "dry_run": ctx.dry,
            "outcome_sender": sender, "outcome_sender_why": sender_why,
            "last_run": iso(last_run, ctx.tz) if last_run else None, "fired": fired, "findings": F.items,
            "due": a["due"], "missing_results": a["missing_results"], "blocks": blocks, "inbox": a["inbox"],
            "watch_alerts": a["watch_alerts"], "bonus": a["bonus"], "jobs": a["jobs"], "cantsee": a["cantsee"],
            "gaps": a["gaps"], "inputs": hashes, "inputs_changed": changed,
            "paths": {"week_page": a["week_page"], "week_plan": plan_rel,
                      "prep_today": prep_file(ctx, today, a.get("prep_state")),
                      "prep_tomorrow": prep_file(ctx, (now.date() + dt.timedelta(days=1)).isoformat(), a.get("prep_state")),
                      "block_logs": block_files},
            "push_gate": pushgate.status(ctx.settings, now), "snoozes": snoozes, "flagged_before": flagged,
            "event": read_json_file(ctx.state_dir / "event-current.json"),
            "mem_available_mb": mem_available_mb(), "outside_term": ctx.outside_term(now.date()),
            "modules": sorted(ctx.enabled) if ctx.enabled is not None else "all (modules.enabled not set)"}


# ---- the gate (the job's PRECHECK) -----------------------------------------------------------
def gate_decision(ctx, r):
    """('run: ...' | 'skip: ...', exit code 0 run / 1 skip)."""
    now = ctx.now
    reason = None
    window = pushgate.window_now(ctx.settings, now, hard_only=True)
    mem = r.get("mem_available_mb")
    ev = read_json_file(ctx.state_dir / "event-pending.json")
    if window:
        reason = "skip: " + window
    elif mem is not None and mem < int(ctx.hb["min_memory_mb"]):
        reason = "skip: only %d MB memory available (needs %d)" % (mem, int(ctx.hb["min_memory_mb"]))
    elif r.get("outside_term") and not ctx.force:
        reason = "skip: " + r["outside_term"]
    if reason is None:
        ev_at = to_local(parse_when((ev or {}).get("at")), ctx.tz)
        if ctx.force:
            reason = "run: forced"
        elif ev_at and 0 <= (now - ev_at).total_seconds() < EVENT_FRESH_MIN * 60:
            reason = "run: event (%s)" % "; ".join(f["trigger"] for f in ev.get("fired", []))
        elif r["fired"]:
            reason = "run: " + "; ".join(sorted(set(f["trigger"] for f in r["fired"])))
        else:
            reason = "skip: nothing fired since the last run"
    if not ctx.dry:
        ctx.state_dir.mkdir(parents=True, exist_ok=True)
        if ev and reason.startswith("run"):
            os.replace(ctx.state_dir / "event-pending.json", ctx.state_dir / "event-current.json")
        with open(ctx.state_dir / "precheck.log", "a", encoding="utf-8") as f:
            f.write("%s | gate | %s\n" % (now.strftime("%Y-%m-%d %H:%M"), reason))
    return reason, (0 if reason.startswith("run") else 1)


# ---- the report the agent reads first --------------------------------------------------------
def render(r):
    L = []
    w = L.append
    wk = "term week %s" % r["term_week"] if r["term_week"] is not None else "term week unknown"
    w("# Heartbeat pre-check, %s (%s, %s)%s" % (r["now"][:16].replace("T", " "), r["weekday"], wk,
                                                 "  [DRY RUN]" if r["dry_run"] else ""))
    w("Acting: %s (heartbeat.act_mode = %s%s). Ask mode: %s. Last run: %s." % (
        r["effective_acting"], r["act_mode"], "; " + r["safe_because"] if r.get("safe_because") else "",
        r.get("ask_mode", "inline"), r["last_run"] or "none"))
    if r.get("outcome_sender"):
        w("Outcome sender: %s (%s). %s" % (
            r["outcome_sender"], r.get("outcome_sender_why", ""),
            "Push findings marked \"outcome check\" yourself, with their ids." if r["outcome_sender"] == "heartbeat"
            else "Flag findings marked \"outcome check\"; don't push them: that sender does."))
    if r.get("ask_test_due"):
        w("Ask test: due. This is the agreed one-time live test of the question path: ask your one question this run "
          "(standing brief, section 5).")
    if r.get("event"):
        w("This is an EVENT run (started by the heartbeat watch at %s)." % r["event"].get("at"))
    if r.get("outside_term"):
        w("Outside the term: %s." % r["outside_term"])
    w("")
    w("## Why this run fired")
    for f in r["fired"] or [{"trigger": "nothing", "detail": "forced or manual run"}]:
        w("- %s: %s" % (f["trigger"], f["detail"]))
    w("")
    w("## Rule verdicts (stable ids; keep them in your flags)")
    for lv in ("red", "amber", "grey"):
        for x in [x for x in r["findings"] if x["level"] == lv]:
            extra = []
            if x.get("snoozed"):
                extra.append("SNOOZED")
            if x.get("outcome"):
                extra.append("outcome check")
            if x.get("known_since"):
                extra.append("flagged since " + str(x["known_since"])[:16].replace("T", " "))
            if x.get("last_pushed"):
                extra.append("pushed " + str(x["last_pushed"])[:16].replace("T", " "))
            w("- [%s] `%s` %s%s" % (lv, x["id"], x["text"], ("  (" + "; ".join(extra) + ")") if extra else ""))
    if not r["findings"]:
        w("- none")
    w("")
    w("## Due this week (%s)" % (r["paths"]["week_page"] or "no week page"))
    for d in r["due"]:
        w("- `%s` %s | deadline %s | target %s | %s | status: %s%s" % (
            d["id"], d["item"], d["deadline"] or "-", d["target"] or "-", d["verdict"], (d["status"] or "")[:120],
            " | %.1f h left" % d["hours_left"] if d["hours_left"] is not None and d["hours_left"] > 0 and not d["done"] else ""))
    if not r["due"]:
        w("- (no Due table found)")
    w("")
    w("## Results not recorded yet (candidates for the one combined question)")
    for m in r["missing_results"]:
        w("- `%s` %s (%s)%s" % (m["id"], m["item"], m["when"], "; " + m["note"] if m.get("note") else ""))
    if not r["missing_results"]:
        w("- none from the Due table or recent graded fixtures; also check the calendar since the last run")
    w("")
    w("## Blocks (planned; from the prep notes, else the week plan)")
    for b in r["blocks"]:
        w("- %s %s-%s %s [%s]%s%s" % (b["day"], b["start"], b["end"], b["title"][:90], b["kind"], " ENDED" if b["ended"] else "",
                                      " (block-log row found)" if b["logged"] else ""))
    if not r["blocks"]:
        w("- none found")
    w("")
    w("## Inputs")
    for k, v in r["paths"].items():
        w("- %s: %s" % (k, v if v else "none"))
    w("- changed since the last run: %s" % (", ".join(r["inputs_changed"]) or "none"))
    w("- inbox: %s" % (", ".join("%s (%s h)" % (x["title"], x["age_h"]) for x in r["inbox"]) or "empty"))
    if r["bonus"]:
        w("- bonus: " + "; ".join("%s %s (target %s, next %s)" % (b["course"], b["banked"] or "-", b["target"] or "-",
                                                                   b["next_bonus"] or "-") for b in r["bonus"]))
    for name, j in sorted(r["jobs"].items()):
        w("- job %s: %s" % (name, j["note"]))
    for c in r["cantsee"]:
        w("- can't see: " + c)
    g = r["push_gate"] or {}
    w("")
    w("## Push budget: %s of %s left today; held now by: %s; host alerts queued: %s; ids pushed recently: %s" % (
        g.get("left_today", "?"), g.get("day_max", "?"), g.get("held_now_by") or "nothing", g.get("held_queue", 0),
        ", ".join(g.get("ids_pushed_recently", [])) or "none"))
    if r["snoozes"]:
        w("## Snoozes: " + "; ".join("%s until %s" % (k, (v or {}).get("until") or "further notice") for k, v in r["snoozes"].items()))
    w("Memory available: %s. Modules: %s." % ("%s MB" % r["mem_available_mb"] if r["mem_available_mb"] is not None else "unknown",
                                                 ", ".join(r["modules"]) if isinstance(r["modules"], list) else r["modules"]))
    return "\n".join(L)


# ---- event wake-ups ----------------------------------------------------------------------------
VM_START = "systemctl --user start --no-block uni-job@{job}.service"


def start_command(ctx):
    """(command with {job}, where it came from) for starting a job now, or ("", None):
    heartbeat.start_job_command, else UNI_JOB_START (exported by the job runners), else
    the always-on host's systemd unit when this runs there (UNI_HOST=vm, set by its runner)."""
    cmd = str(ctx.hb.get("start_job_command") or "").strip()
    if cmd:
        return cmd, "config"
    env = os.environ.get("UNI_JOB_START", "").strip()
    if env:
        return env, "runner"
    if os.environ.get("UNI_HOST") == "vm":
        return VM_START, "host"
    return "", None


def start_job(ctx, job, out=print):
    """Start another job now, detached (it waits for the agent lock, so it really starts
    after this run ends). Returns True if a start command was launched."""
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", job):
        out("refused: bad job id %r" % job)
        return False
    cmd, _src = start_command(ctx)
    if not cmd:
        return False
    full = cmd.replace("{job}", job)
    if os.environ.get("UNI_OS_NO_START") == "1":
        out("(test) would run: " + full)
        return True
    try:
        # Detached and not waited for: a laptop runner's start command runs the whole job.
        # Windows: hand the command line to CreateProcess as it is (its own quoting rules);
        # POSIX: split it like a shell would, without running a shell.
        kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            # NEW_GROUP | NO_WINDOW. Not DETACHED_PROCESS: Windows ignores NO_WINDOW next to it,
            # and a console program the start command launches would open a visible window.
            kw["creationflags"] = 0x00000200 | 0x08000000
            subprocess.Popen(full, **kw)
        else:
            kw["start_new_session"] = True
            subprocess.Popen(shlex.split(full), **kw)
        return True
    except (OSError, ValueError) as e:
        out("could not start %s: %s" % (job, e))
        return False


def watch(ctx, r, out=print):
    """Start an extra heartbeat run when something urgent fired (cap per day)."""
    now = ctx.now
    if not start_command(ctx)[0]:
        out("no event run: no way to start a job here (heartbeat.start_job_command is empty and no job runner "
            "exported UNI_JOB_START; event wake-ups need a host that can start jobs)")
        return 0
    snap_jobs = {j.get("name"): j for j in ((ctx.rjson(ctx.hb["snapshot_file"]) or {}).get("jobs") or [])}
    if not ctx.force and snap_jobs.get("heartbeat", {}).get("on") is False:
        return 0  # the heartbeat itself is switched off: the watch does nothing
    try:
        a, _, b = str(ctx.hb["event_hours"]).partition("-")
        lo, hi = at_time(now.date(), a), at_time(now.date(), b)
    except ValueError:
        lo, hi = None, None
    why = None
    if lo and not (lo <= now <= hi):
        why = "outside %s" % ctx.hb["event_hours"]
    elif pushgate.window_now(ctx.settings, now, hard_only=True):
        why = pushgate.window_now(ctx.settings, now, hard_only=True)
    ev_log = ctx.state_dir / "events.log"
    n_today = 0
    try:
        with open(ev_log, encoding="utf-8") as f:
            n_today = sum(1 for line in f if line.startswith(now.strftime("%Y-%m-%d")) and "| started |" in line)
    except OSError:
        pass
    urgent = []
    nxt = ctx.next_heartbeat_slot()
    for f in r["fired"]:
        t = f["trigger"]
        if t in ("new red", "outcome check", "vault-watch alert"):
            urgent.append(f)
        elif t == "due in 6 h" and nxt:
            dl = next((dt.datetime.fromisoformat(d["deadline_at"]) for d in r["due"] if d["id"] == f.get("id")), None)
            if dl and nxt > dl - dt.timedelta(hours=1):
                urgent.append(f)
    if why is None and not urgent:
        why = "nothing urgent"
    if why is None and n_today >= int(ctx.hb["event_cap"]):
        why = "event cap reached (%d today)" % n_today
    if why is None and nxt and (nxt - now).total_seconds() < float(ctx.hb["event_near_slot_min"]) * 60:
        why = "the %s slot is near" % nxt.strftime("%H:%M")
    last = to_local(parse_when(r.get("last_run")), ctx.tz)
    if why is None and last and (now - last).total_seconds() < float(ctx.hb["event_min_gap_min"]) * 60:
        why = "last run under %s min ago" % ctx.hb["event_min_gap_min"]
    stamp = now.strftime("%Y-%m-%d %H:%M")
    if why:
        if urgent and not ctx.dry:
            ctx.state_dir.mkdir(parents=True, exist_ok=True)
            with open(ev_log, "a", encoding="utf-8") as f:
                f.write("%s | held | %s | %s\n" % (stamp, why, "; ".join(u["detail"][:80] for u in urgent)))
        out("no event run: " + why)
        return 0
    if ctx.dry:
        out("would start an event run: " + "; ".join(u["detail"][:100] for u in urgent))
        return 0
    ctx.state_dir.mkdir(parents=True, exist_ok=True)
    with open(ctx.state_dir / "event-pending.json", "w", encoding="utf-8") as f:
        json.dump({"at": iso(now, ctx.tz), "fired": urgent}, f, ensure_ascii=False)
    with open(ev_log, "a", encoding="utf-8") as f:
        f.write("%s | started | %s\n" % (stamp, "; ".join(u["detail"][:80] for u in urgent)))
    start_job(ctx, "heartbeat", out)
    out("event run started")
    return 0


# ---- writing the vault files ----------------------------------------------------------------------
def write_in_place(path, text):
    """Overwrite without temp file + rename, so a synced file keeps its id (dashboards on
    Google Drive find files by id)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def append_line(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    pre = ""
    try:
        with open(path, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                pre = "\n"
    except OSError:
        pass
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(pre + line + "\n")


def validate_decisions(dec):
    errors = []
    if not isinstance(dec, dict):
        return ["the decisions file must be a JSON object"]
    flags = dec.get("flags") or []
    if not isinstance(flags, list):
        return ["flags must be a list"]
    seen = set()
    for x in flags:
        if not isinstance(x, dict) or not ID_RE.match(str(x.get("id", ""))) or "*" in str(x.get("id", "")):
            errors.append("bad id: %r" % (x.get("id") if isinstance(x, dict) else x))
            continue
        if x["id"] in seen:
            errors.append("duplicate id: " + x["id"])
        seen.add(x["id"])
        if x.get("level") not in ("red", "amber", "grey"):
            errors.append("%s: level must be red, amber or grey" % x["id"])
        t = x.get("text")
        if not isinstance(t, str) or not t.strip() or "\n" in t or len(t) > 300:
            errors.append("%s: text must be one line of at most 300 characters" % x["id"])
    if not isinstance(dec.get("log"), str) or not dec["log"].strip():
        errors.append("log: one line required")
    for key, typ in (("snoozes", dict), ("actions", list), ("asks", list), ("pushed", dict)):
        if key in dec and dec[key] is not None and not isinstance(dec[key], typ):
            errors.append("%s must be a %s" % (key, typ.__name__))
    return errors


def commit(ctx, dec, out=print):
    """Write flags.json and state.json (in place) and one heartbeat-log line from the run's decisions."""
    now = ctx.now
    errors = validate_decisions(dec)
    if errors:
        out("commit refused:\n- " + "\n- ".join(errors))
        return 2
    st = read_state(ctx)
    prev_flagged = st.get("flagged") or {}
    pushed = dec.get("pushed") or {}
    p_ids, p_at = set(pushed.get("ids") or []), pushed.get("at") or iso(now, ctx.tz)
    today = now.date().isoformat()
    snoozes = {}
    source = dec.get("snoozes") if isinstance(dec.get("snoozes"), dict) else (st.get("snoozes") or {})
    for k, v in source.items():
        v = dict(v or {})
        if v.get("until") and str(v["until"]) < today:
            continue
        v.setdefault("added", ((st.get("snoozes") or {}).get(k) or {}).get("added") or iso(now, ctx.tz))
        snoozes[k] = v
    flagged, out_flags = {}, []
    for x in dec.get("flags") or []:
        p = prev_flagged.get(x["id"]) or {}
        rec = {"first": p.get("first") or iso(now, ctx.tz), "last": iso(now, ctx.tz), "level": x["level"],
               "text": one_line(x["text"]), "pushed": p_at if x["id"] in p_ids else p.get("pushed")}
        flagged[x["id"]] = rec
        s = snooze_for(x["id"], snoozes, today)
        out_flags.append({"id": x["id"], "level": x["level"], "text": rec["text"], "since": rec["first"],
                          "last_seen": rec["last"], "pushed_at": rec["pushed"],
                          "snoozed_until": ((s.get("until") or "indefinite") if s else None),
                          "source": x.get("source") or "judgment", "action": x.get("action") or "flagged",
                          "where": x.get("where") or ""})
    ev = read_json_file(ctx.state_dir / "event-current.json")
    kind = "event" if ev else "slot"
    mode, effective, _ = ctx.acting()
    flags_doc = {"schema": 1, "generated": iso(now, ctx.tz), "writer": "uni-os heartbeat",
                 "run": {"at": iso(now, ctx.tz), "kind": kind, "act_mode": effective, "dry_run": ctx.dry},
                 "flags": out_flags}
    r = compute(ctx)  # inputs as they are now, after this run's own writes
    state_doc = {"schema": 1, "updated": iso(now, ctx.tz),
                 "last_run": {"at": iso(now, ctx.tz), "kind": kind,
                              "fired": [f["trigger"] for f in (ev or {}).get("fired", [])] or sorted(set(f["trigger"] for f in r["fired"])),
                              "act_mode": effective},
                 "inputs": r["inputs"], "outcome_keys": [x["id"] for x in r["findings"] if x["outcome"]],
                 "flagged": flagged, "snoozes": snoozes,
                 "actions": (dec.get("actions") if isinstance(dec.get("actions"), list) else st.get("actions") or [])[-30:],
                 "asks": (dec.get("asks") if isinstance(dec.get("asks"), list) else st.get("asks") or [])[-20:]}
    line = "- %s | %s%s | %s" % (now.strftime("%Y-%m-%d %H:%M"), kind, " DRY-RUN" if ctx.dry else "", one_line(dec["log"]))
    target = ctx.dry_dir() if ctx.dry else ctx.hb_dir
    write_in_place(target / "flags.json", json.dumps(flags_doc, indent=1, ensure_ascii=False) + "\n")
    write_in_place(target / "state.json", json.dumps(state_doc, indent=1, ensure_ascii=False) + "\n")
    append_line(target / "heartbeat-log.md", line)
    if ctx.dry:
        out("dry run: wrote flags.json, state.json and the log line to %s" % target)
        return 0
    try:
        os.remove(ctx.state_dir / "event-current.json")
    except OSError:
        pass
    out("committed: %d flags, log line written" % len(out_flags))
    return 0


def append_log(ctx, text, kind="note", out=print):
    if kind not in ("note", "answer"):
        out("refused: --kind must be note or answer")
        return 2
    line = "- %s | %s%s | %s" % (ctx.now.strftime("%Y-%m-%d %H:%M"), kind, " DRY-RUN" if ctx.dry else "", one_line(text))
    append_line((ctx.dry_dir() if ctx.dry else ctx.hb_dir) / "heartbeat-log.md", line)
    out(line)
    return 0


def tracker(ctx, text, out=print):
    """One tracker-log line tagged "heartbeat", so a later evaluation can separate its effect."""
    if not ctx.on("progress"):
        out("refused: the progress module (tracker log) is not enabled; use `uni-os heartbeat log` instead")
        return 2
    n = ctx.now
    line = "- %s %d %s %d ~%s (heartbeat): %s" % (n.strftime("%a"), n.day, n.strftime("%b"), n.year, n.strftime("%H:%M"),
                                                 one_line(text))
    if ctx.dry:
        append_line(ctx.dry_dir() / "tracker-log-lines.md", line)
        out("dry run: would append to progress/tracker-log.md: " + line)
        return 0
    append_line(ctx.path("progress/tracker-log.md"), line)
    out("appended: " + line)
    return 0


# ---- the one combined question ------------------------------------------------------------------
def ask_mode(ctx):
    """auto = session on the always-on host (UNI_HOST=vm, or an explicit start_job_command:
    the question job needs an interactive remote session), inline everywhere else."""
    m = str(ctx.hb.get("ask_mode") or "auto")
    if m == "auto":
        cmd, src = start_command(ctx)
        return "session" if cmd and src in ("config", "host") else "inline"
    return m if m in ("session", "inline") else "inline"


def ask(ctx, ids, text, out=print):
    """Ask ONE combined question (missing results). Gate checked now and 15 min later, so no
    question session opens at the start of a quiet window. session: queue it for the job
    heartbeat-ask (an interactive session the student opens from the push); inline: the
    question itself goes out as the push."""
    ids = [i.strip() for i in ids if i.strip()]
    if not ids:
        out("refused: --ids needed (the flags the question is about)")
        return pushgate.REFUSED
    question = one_line(text)
    gid = ASK_GATE_ID  # one id for every question: the gate's dedupe makes "at most one question a day" hard
    sd = pushgate.gate_state_dir()
    st = pushgate.load_state(sd / "state.json")
    for mins in (0, ASK_LOOKAHEAD_MIN):
        at = ctx.now + dt.timedelta(minutes=mins)
        d = pushgate.decide(ctx.settings, st, at, [gid], question if mins == 0 else None)
        if d.code != pushgate.SENT:
            out("not asked now (%s%s); keep it as a flag" % (d.reason, " at %s" % at.strftime("%H:%M") if mins else ""))
            return d.code
    mode = ask_mode(ctx)
    q = {"at": iso(ctx.now, ctx.tz), "ids": ids, "gate_id": gid, "question": question, "mode": mode}
    if ctx.dry:
        append_line(ctx.dry_dir() / "asks.md", "- %s | %s | ids %s | %s" % (ctx.now.strftime("%Y-%m-%d %H:%M"), mode,
                                                                          ",".join(ids), question))
        out("dry run: would ask (%s): %s" % (mode, question))
        return 0
    marker = ctx.state_dir / "ask-test-due"
    if mode == "session":
        (ctx.state_dir / "ask").mkdir(parents=True, exist_ok=True)
        pending = ctx.state_dir / "ask" / "pending.json"
        with open(pending, "w", encoding="utf-8") as f:
            json.dump(q, f, ensure_ascii=False)
        if not start_job(ctx, "heartbeat-ask", out):
            os.remove(pending)
            out("could not start the question job; asking inline instead")
            mode = "inline"
    if mode == "inline":
        code = pushgate.push(ctx.settings, text="One question: " + question, ids=[gid], source="heartbeat-ask",
                             now=ctx.now, out=out)
        if code == 0 and marker.exists():
            marker.unlink()
            out("ask test: done (marker removed)")
        return code
    if marker.exists():
        marker.unlink()
        out("ask test: done (marker removed)")
    out("queued: the question session opens after this run ends")
    return 0


def take_pending(ctx, out=print):
    """For the heartbeat-ask session: print the pending question and rename the file to
    taken-<ts>.json, so the question is asked exactly once."""
    p = ctx.state_dir / "ask" / "pending.json"
    q = read_json_file(p)
    if not q:
        out("no pending question")
        return 1
    if not ctx.dry:
        os.replace(p, p.with_name("taken-%s.json" % ctx.now.strftime("%Y%m%d-%H%M")))
    out(json.dumps(q, ensure_ascii=False, indent=1))
    return 0


def has_pending(ctx):
    p = ctx.state_dir / "ask" / "pending.json"
    return p.exists() and p.stat().st_size > 0


def pending_gate_id(ctx):
    return (read_json_file(ctx.state_dir / "ask" / "pending.json") or {}).get("gate_id") or ASK_GATE_ID


def rerun(ctx, job, out=print):
    allowed = as_list(ctx.hb.get("rerun_allowed"))
    if job not in allowed:
        out("refused: %s is not in heartbeat.rerun_allowed (%s)" % (job, ", ".join(allowed) or "empty"))
        return 2
    if ctx.dry:
        append_line(ctx.dry_dir() / "actions.md", "- %s | would re-run %s" % (ctx.now.strftime("%Y-%m-%d %H:%M"), job))
        out("dry run: would start %s (it waits until this run ends)" % job)
        return 0
    if start_job(ctx, job, out):
        out("started %s; it runs after this heartbeat run ends (agent lock)" % job)
        return 0
    out("not started: no way to start a job here (heartbeat.start_job_command is empty and no job runner "
        "exported UNI_JOB_START); ask the owning role instead")
    return 2


# ---- outcome checks ("exit 0 is not success") -----------------------------------------------------
def outcomes(ctx, push=False, out=print):
    """Deterministic result checks, no agent: the findings marked as outcome checks plus
    prep gaps open for more than gap_open_hours. Prints `OUTCOME <id>: <text>`; with
    push, sends the fresh ones through the gate (shared budget, same ids as the heartbeat)."""
    if (ctx.state_dir / "outcomes-off").exists():
        return 0
    now = ctx.now
    F = Findings()
    a = assess(ctx, F)
    items = {x["id"]: x["push"] or x["text"] for x in F.items if x["outcome"]}
    st_path = ctx.state_dir / "outcomes.json"
    st = read_json_file(st_path) or {"gap_first": {}}
    first = st.setdefault("gap_first", {})
    for day, g in a["gaps"].items():
        seen = to_local(parse_when(first.get(day)), ctx.tz) or now
        first.setdefault(day, iso(now, ctx.tz))
        if (now - seen).total_seconds() >= float(ctx.hb["gap_open_hours"]) * 3600:
            d = dt.date.fromisoformat(day)
            items["prep:gap-open:" + day] = gap_open_text(float(ctx.hb["gap_open_hours"]), d)
    for day in list(first):
        if day not in a["gaps"]:
            first.pop(day)
    if not ctx.dry:
        ctx.state_dir.mkdir(parents=True, exist_ok=True)
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
    for k, v in items.items():
        out("OUTCOME %s: %s" % (k, v))
    if not push:
        return 0
    pushgate.flush(ctx.settings, now=now, dry_run=ctx.dry, out=lambda s: None)
    if not items:
        return 0
    sender, why = outcome_sender(ctx)
    if sender == "host" and os.environ.get("UNI_HOST") != "vm":
        # the gate's dedupe state is per machine: a second machine pushing would reach the phone twice
        out("push: not from this machine; %s" % why)
        return 0
    code = pushgate.push(ctx.settings, items=items, prefix=str(ctx.hb.get("outcome_prefix") or ""),
                         source="outcome-checks", now=now, dry_run=ctx.dry, out=out)
    return 0 if code in (0, 10, 11, 12) else code


def gap_open_text(hours, day):
    """Push text of prep:gap-open:<date> (never the gap text, never a file name)."""
    return "prep gap open for over %g h for %s" % (hours, pushgate.fmt_day(dt.datetime.combine(day, dt.time())))


def outcome_sender(ctx):
    """The ONE sender of outcome-check pushes (stuck inbox notes, missing prep notes, open prep
    gaps) in this setup, as (sender, reason). Every sender uses the same ids and texts, but the
    push gate's dedupe state lives on each machine, so two machines sending would reach the phone
    twice. Precedence, first match wins:
      host       the vm module is on: the always-on host sends (its job outcome-checks when that
                 is switched on there, else the built-in check of `uni-vm health`; never both).
                 `outcomes --push` on any other machine prints its findings and sends nothing.
      job        no vm module, and the laptop runs command jobs (runtime.laptop_scheduler = "os"):
                 the notifications module's job outcome-checks on the laptop.
      heartbeat  neither can run (an agent app's scheduled tasks run prompts, not commands): the
                 heartbeat agent pushes these findings itself, with the same ids.
    The inbox poll's optional --push only sends when neither the vm nor the notifications module
    is enabled (inbox_poll.py checks that itself)."""
    if (ctx.enabled is not None and "vm" in ctx.enabled) or deep_get(ctx.cfg, "runtime.use_vm") is True:
        return "host", ("the vm module is on: the always-on host sends outcome pushes, through its outcome-checks "
                        "job when that is switched on there, else through the built-in check in uni-vm health")
    sched = str(deep_get(ctx.cfg, "runtime.laptop_scheduler", "agent-app") or "agent-app")
    if sched == "os" and ctx.on("notifications") and not ctx.path("_agent/jobs/outcome-checks/DISABLED").exists():
        return "job", "the outcome-checks job on the laptop's OS scheduler sends outcome pushes"
    return "heartbeat", ("no outcome-checks job can run here, runtime.laptop_scheduler = %s and no always-on host: "
                         "the heartbeat pushes outcome findings itself, with their ids" % sched)


def status(ctx):
    st = read_state(ctx)
    def tail(p, n):
        try:
            with open(p, encoding="utf-8") as f:
                return [ln.rstrip("\n") for ln in f][-n:]
        except OSError:
            return []
    events = tail(ctx.state_dir / "events.log", 50)
    return {"last_run": st.get("last_run"), "flags": len(st.get("flagged") or {}), "snoozes": st.get("snoozes"),
            "event_runs_today": sum(1 for ln in events if ln.startswith(ctx.now.strftime("%Y-%m-%d")) and "| started |" in ln),
            "precheck_log_tail": tail(ctx.state_dir / "precheck.log", 5), "pending_question": has_pending(ctx),
            "ask_mode": ask_mode(ctx), "state_dir": str(ctx.state_dir), "vault_dir": str(ctx.hb_dir)}


def init_files(ctx, out=print):
    """Create the placeholder vault files if missing (normally `uni-os init` installs them)."""
    made = []
    docs = {"flags.json": {"schema": 1, "generated": None, "status": "not-switched-on", "writer": "uni-os heartbeat",
                           "run": None, "flags": []},
            "state.json": {"schema": 1, "updated": None, "last_run": None, "inputs": {}, "outcome_keys": [],
                           "flagged": {}, "snoozes": {}, "actions": [], "asks": []}}
    for name, doc in docs.items():
        p = ctx.hb_dir / name
        if not p.exists() and not ctx.dry:
            write_in_place(p, json.dumps(doc, indent=1) + "\n")
            made.append(name)
    out("created: %s" % (", ".join(made) or "nothing (all present)"))
    return 0
