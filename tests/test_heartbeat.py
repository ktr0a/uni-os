"""Tests of the heartbeat's deterministic side (`uni-os heartbeat`, tools/uni_os/heartbeat_rules.py).

Ported from the original system's heartbeat test suite: a fake vault in a temp dir, fake
sends only (UNI_OS_PUSH_FAKE_SEND), no job starts (UNI_OS_NO_START=1), simulated time
(--now). Run from the repo root:  python -m unittest tests.test_heartbeat -v
"""
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
try:
    import uni_os  # noqa: F401
    if not hasattr(uni_os, "__path__"):
        raise ImportError
except ImportError:
    _pkg = types.ModuleType("uni_os")
    _pkg.__path__ = [str(TOOLS / "uni_os")]
    sys.modules["uni_os"] = _pkg

from uni_os import heartbeat_rules as hr  # noqa: E402
from uni_os import pushgate  # noqa: E402
from uni_os.commands import heartbeat as hb_cmd  # noqa: E402

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None


def raw_load_config(vault, config_path=None, modules_dir=None):
    """Test stub: read <vault>/_agent/uni-os.toml as it is, so these tests do not depend on
    the shared loader's module catalogue (other modules may not be installed yet)."""
    p = Path(config_path) if config_path else Path(vault) / "_agent" / "uni-os.toml"
    if not p.is_file():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)
try:
    from zoneinfo import ZoneInfo
    ZONE = ZoneInfo("Europe/Zurich")
except Exception:  # pragma: no cover
    ZONE = None

ENV_KEYS = ["UNI_OS_STATE", "UNI_STATE_DIR", "UNI_OS_PUSH_STATE", "UNI_OS_HEARTBEAT_STATE", "UNI_OS_PUSH_FAKE_SEND", "UNI_DRY_RUN",
            "UNI_OS_NOW", "UNI_OS_VAULT", "UNI_OS_NO_START", "UNI_OS_HEARTBEAT_FORCE", "UNI_OS_HEARTBEAT_DRY_DIR",
            "UNI_OS_HEARTBEAT_ACT_MODE", "UNI_OS_PUSH_DRY_LOG", "UNI_VAULT", "UNI_HOST", "UNI_JOB_START", "UNI_JOB"]

CONFIG = """
[student]
name = "Alex Example"

[term]
label = "Autumn 2026"
timezone = "Europe/Zurich"
week0_monday = 2026-09-14
last_lecture_day = 2026-12-18
exam_session_start = 2027-01-18
exam_session_end = 2027-02-12

[paths]
agent_dir = "_agent"
inbox = "inbox"

[notify]
provider = "none"
quiet_hours = "21:00-07:30"
quiet_windows = [
  {{ from = "2026-12-08 16:45", to = "2026-12-08 19:15", reason = "PROG timed task 2" }},
  {{ day = "Mon", from = "08:00", to = "10:00", until = "2026-12-21", reason = "weekly AD quiz" }},
]

[schedule]
daily_prep = ["17:30", "19:30"]
prep_check = "07:30"
week_page = {{ day = "Sun", time = "10:00" }}
check_in = {{ day = "Sat", time = "19:45", every = "week" }}
heartbeat = ["07:50", "13:05", "18:05"]
heartbeat_days = ["Mon", "Tue", "Wed", "Thu", "Fri"]

[heartbeat]
start_job_command = "{start}"

[modules]
enabled = [{modules}]

[[courses]]
id = "algo"
name = "Algorithms and Data Structures"
short = "AD"
folder = "AD"
slug = "ad"
assistance = "hints-only"

[[courses]]
id = "la"
name = "Linear Algebra"
short = "LA"
folder = "LA"
slug = "la"
assistance = "hints-only"
"""
MODULES = ["core", "progress", "planning", "daily-prep", "check-in", "notifications", "heartbeat", "inbox-sync"]

WEEK_PAGE = """---
type: week
week: 8
start: 2026-11-09
end: 2026-11-15
status: current
---
# Week 08

## Due this week
| Item | Official deadline | Personal target | Bonus | Status |
|---|---|---|---|---|
| AD quiz "Week 9" | Mon 9 Nov 09:15 | | 4 pts | open |
| LA A7 hand-in | Tue 10 Nov 23:59 | Sun 8 Nov | feedback only | open |
| PROG exercise 8 | Tue 10 Nov 23:59 | | bonus | done 5/5 |
| AD peer grading 7 | Mon 9 Nov 23:59 | | 1 pt | open |

## Results this week

## End-of-week check-in
- Done:
- Rolls over:
"""


def ts_of(s):
    """Timestamp of a simulated local time, for file mtimes."""
    d = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    return (d.replace(tzinfo=ZONE) if ZONE else d).timestamp()


class HeartbeatBase(unittest.TestCase):
    modules = MODULES
    start_command = "true {job}"

    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ENV_KEYS}
        self._orig_load = pushgate.load_config
        pushgate.load_config = raw_load_config
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        self.tmp = Path(tempfile.mkdtemp(prefix="uni-os-hb-test-"))
        os.environ["UNI_OS_STATE"] = str(self.tmp / "state")
        os.environ["UNI_OS_NO_START"] = "1"
        self.sent = self.tmp / "sent.txt"
        os.environ["UNI_OS_PUSH_FAKE_SEND"] = str(self.sent)
        self.v = self.tmp / "vault"
        self.st = self.tmp / "state" / "heartbeat"
        self.fresh()

    def tearDown(self):
        pushgate.load_config = self._orig_load
        for k, val in self._env.items():
            if val is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = val
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- the fake vault (the original's fixture, with the example student's courses) -----
    def fresh(self, extra_config=""):
        if self.v.exists():
            shutil.rmtree(self.v)
        for d in ("_agent/daily-prep", "_agent/heartbeat", "_agent/logs", "progress/weeks", "semester/prep",
                  "semester/plans", "inbox", "AD", "LA"):
            (self.v / d).mkdir(parents=True, exist_ok=True)
        self.write_config(extra_config)
        (self.v / "_agent" / "agent-start.md").write_text("start\n", encoding="utf-8")
        (self.v / "inbox" / "inbox.md").write_text("# Inbox\n", encoding="utf-8")
        self.write("_agent/daily-prep/state.json", json.dumps({"days": {
            "2026-11-10": {"prep_file_name": "prep-2026-11-10.md", "verified": "2026-11-10 07:40", "gaps": []},
            "2026-11-11": {"prep_file_name": "prep-2026-11-11.md", "gaps": []}}}))
        self.write("semester/prep/prep-2026-11-10.md", "---\ntype: prep\n---\n"
                   "> [!la] 08:00-09:45 LA_ A7 core first\n"
                   "> [!algo] 10:15-12:00 L: Algorithms lecture\n"
                   "> [!algo] 13:30-16:00 AD_ Sheet 8 (deep)\n\n## Gaps\n- none\n")
        self.write("semester/prep/prep-2026-11-11.md", "---\ntype: prep\n---\n> [!dm] 08:00-09:45 DM_ recall\n\n## Gaps\n- none\n")
        self.write("progress/weeks/week-08.md", WEEK_PAGE)
        self.write("_agent/heartbeat/requests.md", "# Requests\n")

    def write_config(self, extra=""):
        text = CONFIG.format(modules=", ".join('"%s"' % m for m in self.modules), start=self.start_command) + extra
        self.write("_agent/uni-os.toml", text)

    def write(self, rel, text):
        p = self.v / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    # ---- running commands ---------------------------------------------------------------
    def hb(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hb_cmd.main(["heartbeat", *argv, "--vault", str(self.v)])
        return code, buf.getvalue().strip()

    def gate(self, now, *extra):
        return self.hb("precheck", "--now", now, *extra)

    def rep(self, now):
        code, out = self.hb("report", "--json", "--now", now)
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def level(self, now, fid):
        return next((x["level"] for x in self.rep(now)["findings"] if x["id"] == fid), None)

    def commit_at(self, now, extra_flags=None):
        """A run that flags what the rules found, as the agent would."""
        r = self.rep(now)
        dec = {"flags": [{"id": x["id"], "level": x["level"], "text": x["text"], "source": x["source"]}
                         for x in r["findings"] if x["level"] != "grey"] + (extra_flags or []),
               "log": "test run"}
        p = self.tmp / "dec.json"
        p.write_text(json.dumps(dec), encoding="utf-8")
        code, out = self.hb("commit", str(p), "--now", now)
        self.assertEqual(code, 0, out)

    def flags_doc(self):
        return json.loads((self.v / "_agent" / "heartbeat" / "flags.json").read_text(encoding="utf-8"))

    def state_doc(self):
        return json.loads((self.v / "_agent" / "heartbeat" / "state.json").read_text(encoding="utf-8"))


class Rules(HeartbeatBase):
    def test_due_table(self):
        now = "2026-11-10 10:00"
        self.assertEqual(self.level(now, "due:ad-peer-grading-7:overdue"), "red", "overdue: red")
        r = self.rep(now)
        ids = [x["id"] for x in r["findings"]]
        self.assertIn("due:ad-quiz-week-9:result", [m["id"] for m in r["missing_results"]], "past quiz: missing result")
        self.assertNotIn("due:ad-quiz-week-9:overdue", ids, "a quiz is never overdue")
        self.assertEqual(self.level(now, "due:la-a7-hand-in:behind"), "amber", "personal target passed")
        self.assertFalse(any("prog-exercise-8" in i for i in ids), "done 5/5 counts as done")

    def test_week_pages(self):
        (self.v / "progress/weeks/week-08.md").unlink()
        self.assertEqual(self.level("2026-11-10 10:00", "week:missing:week-08.md"), "red")
        self.write("progress/weeks/week-08.md", WEEK_PAGE)
        self.write("progress/weeks/week-07.md", WEEK_PAGE.replace("week: 8", "week: 7"))
        self.assertEqual(self.level("2026-11-10 10:00", "week:two-current"), "amber")
        self.assertIsNone(self.level("2026-12-30 10:00", "week:missing:week-15.md"), "no week pages after the lectures")

    def test_next_week_page_and_checkin(self):
        self.assertIsNone(self.level("2026-11-15 10:30", "week:next-missing:week-09.md"), "before slot + 2 x grace")
        self.assertEqual(self.level("2026-11-15 10:41", "week:next-missing:week-09.md"), "amber")
        self.assertIsNone(self.level("2026-11-15 11:30", "week:checkin-empty:week-08.md"), "check-in slot + 16 h not reached")
        self.assertEqual(self.level("2026-11-15 12:00", "week:checkin-empty:week-08.md"), "amber")
        self.write("progress/weeks/week-08.md", WEEK_PAGE.replace("- Done:\n", "- Done: LA A7, AD sheet 8\n"))
        self.assertIsNone(self.level("2026-11-15 12:00", "week:checkin-empty:week-08.md"), "filled check-in")

    def test_prep_rules(self):
        self.assertIsNone(self.level("2026-11-10 10:00", "prep:today-missing:2026-11-10"))
        self.assertIsNone(self.level("2026-11-10 17:45", "prep:tomorrow-missing:2026-11-11"))
        (self.v / "semester/prep/prep-2026-11-11.md").unlink()
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"].pop("2026-11-11")
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        self.assertIsNone(self.level("2026-11-10 17:45", "prep:tomorrow-missing:2026-11-11"), "first slot + grace")
        self.assertEqual(self.level("2026-11-10 17:51", "prep:tomorrow-missing:2026-11-11"), "amber")
        self.assertEqual(self.level("2026-11-10 19:51", "prep:tomorrow-missing:2026-11-11"), "red")
        (self.v / "semester/prep/prep-2026-11-10.md").unlink()
        self.assertIsNone(self.level("2026-11-10 07:55", "prep:today-missing:2026-11-10"))
        self.assertEqual(self.level("2026-11-10 08:01", "prep:today-missing:2026-11-10"), "red")

    def test_prep_unverified_and_gaps(self):
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"]["2026-11-10"]["verified"] = "2026-11-09 07:40"
        st["days"]["2026-11-10"]["gaps"] = ["LA A7 sheet not in the vault yet"]
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        self.assertIsNone(self.level("2026-11-10 07:45", "prep:today-unverified:2026-11-10"))
        self.assertEqual(self.level("2026-11-10 07:51", "prep:today-unverified:2026-11-10"), "amber")
        self.assertEqual(self.level("2026-11-10 10:00", "prep:gap:2026-11-10"), "amber")
        self.write("semester/prep/prep-2026-11-11-r2.md", "---\ntype: prep\n---\n## Gaps\n- DM notes missing\n")
        self.assertEqual(self.level("2026-11-10 10:00", "prep:gap:2026-11-11"), "amber", "gaps from the newest -rN note")

    def test_inbox_stuck(self):
        p = self.write("inbox/2026-11-10-la-update.md", "update\n")
        os.utime(p, (ts_of("2026-11-10 05:00"), ts_of("2026-11-10 05:00")))
        tap = self.write("inbox/2026-11-10_cockpit-done-x-update.md", "tap\n")
        os.utime(tap, (ts_of("2026-11-10 05:00"), ts_of("2026-11-10 05:00")))
        self.assertIsNone(self.level("2026-11-10 08:30", "inbox:stuck:2026-11-10-la-update-md"))
        self.assertEqual(self.level("2026-11-10 09:01", "inbox:stuck:2026-11-10-la-update-md"), "amber")
        self.assertIsNone(self.level("2026-11-10 09:01", "inbox:stuck:2026-11-10-cockpit-done-x-update-md"), "taps get 14 h")
        r = self.rep("2026-11-10 09:01")
        f = next(x for x in r["findings"] if x["id"] == "inbox:stuck:2026-11-10-la-update-md")
        self.assertEqual(f["push"], "update note waiting in the inbox for over 4 h, not applied by the inbox sync")
        self.assertNotIn("la-update", f["push"], "no file name in the push")

    def test_inbox_threshold_is_the_one_notify_key(self):
        p = self.write("inbox/2026-11-10-la-update.md", "update\n")
        os.utime(p, (ts_of("2026-11-10 05:00"), ts_of("2026-11-10 05:00")))
        text = (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8")
        self.write("_agent/uni-os.toml", text.replace('provider = "none"', 'provider = "none"\ninbox_stale_hours = 6'))
        self.assertIsNone(self.level("2026-11-10 10:30", "inbox:stuck:2026-11-10-la-update-md"), "5.5 h < 6 h")
        self.assertEqual(self.level("2026-11-10 11:00", "inbox:stuck:2026-11-10-la-update-md"), "amber")
        # the old heartbeat key is only an alias: 0 (its default) defers, a non-zero value overrides
        self.write("_agent/uni-os.toml", (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8")
                   .replace("[heartbeat]\n", "[heartbeat]\ninbox_stuck_hours = 2\n"))
        self.assertEqual(self.level("2026-11-10 07:01", "inbox:stuck:2026-11-10-la-update-md"), "amber")

    def test_failure_flag_and_jobs_log(self):
        self.write("_agent/logs/flags/daily-study-prep.md", "---\njob: daily-study-prep\nat: 2026-11-10 17:31\n---\n"
                   "calendar write denied; prep note written without MATERIAL blocks\n")
        (self.tmp / "state").mkdir(parents=True, exist_ok=True)
        (self.tmp / "state" / "jobs.log").write_text("2026-11-10 07:15 | inbox-sync | exit 0 | 40s | x.log\n"
                                                     "2026-11-10 13:15 | inbox-sync | exit 1 | 12s | y.log\n",
                                                     encoding="utf-8")
        r = self.rep("2026-11-10 18:00")
        lv = {x["id"]: x for x in r["findings"]}
        self.assertEqual(lv["job:daily-study-prep:failed"]["level"], "red")
        self.assertIn("calendar write denied", lv["job:daily-study-prep:failed"]["text"])
        self.assertEqual(lv["job:inbox-sync:failed"]["level"], "red")

    def test_host_snapshot(self):
        snap = {"schema": 1, "generated": "2026-11-10T09:50:00+01:00",
                "host": {"mount_ok": True, "remote_control_ok": True, "mem_available_mb": 1800},
                "jobs": [{"name": "heartbeat", "on": True, "exit": 0}], "job_sessions": [],
                "roles": [{"role": "plan-and-progress", "title": "Plan & progress", "state": "down"},
                          {"role": "course-files-fetch", "state": "off"}], "alerts": []}
        self.write("_agent/vm/snapshot.json", json.dumps(snap))
        self.assertIsNone(self.level("2026-11-10 10:00", "host:snapshot-stale"), "10 min old: fine")
        self.assertEqual(self.level("2026-11-10 10:31", "host:snapshot-stale"), "red", "41 min old: stale")
        self.assertEqual(self.level("2026-11-10 10:00", "role:plan-and-progress:down"), "red")
        self.assertIsNone(self.level("2026-11-10 10:00", "role:course-files-fetch:off"), "on-demand role ignored")

    def test_laptop_ping_note_only_with_failover_jobs(self):
        snap = {"schema": 1, "generated": "2026-11-10T09:50:00+01:00", "host": {"mem_available_mb": 1800},
                "laptop": {"online": None, "app_open": None, "seen": None},
                "jobs": [{"name": "inbox-sync", "on": True, "mode": "always", "exit": 0}],
                "job_sessions": [], "roles": [], "alerts": []}
        self.write("_agent/vm/snapshot.json", json.dumps(snap))
        lap = lambda: [c for c in self.rep("2026-11-10 10:00")["cantsee"] if c.startswith("Laptop not seen")]
        self.assertEqual(lap(), [], "mode always: no laptop ping by design, so no note")
        snap["jobs"].append({"name": "daily-study-prep", "on": True, "mode": "failover", "exit": 0})
        self.write("_agent/vm/snapshot.json", json.dumps(snap))
        self.assertEqual(len(lap()), 1)
        self.assertIn("daily-study-prep", lap()[0])
        snap["laptop"] = {"online": True, "seen": "2026-11-10T09:55:00+01:00"}
        self.write("_agent/vm/snapshot.json", json.dumps(snap))
        self.assertEqual(lap(), [], "laptop seen: fine")

    def test_host_oom_rows(self):
        self.write("_agent/uni-os.toml", (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace(
            '"inbox-sync"]', '"inbox-sync", "vm"]'))
        self.write("_agent/vm/performance.md", "# Host performance\n\n## Daily (CET)\n"
                   "| Day | Memory available min / typical (MB) | Swap used max (MB) | Load max | CPU steal avg / max (%) "
                   "| Agent sessions peak | OOM kills | Swap-in max (pages/s) |\n|---|---|---|---|---|---|---|---|\n"
                   "| Sat 31 Oct | 420 / 900 | 10 | 1.2 | 0.1 / 2 | 7 | 1 | 3 |\n"
                   "| Mon 09 Nov | 380 / 850 | 12 | 1.5 | 0.2 / 3 | 8 | 2 | 5 |\n\n## Latest verdict\nNone yet.\n")
        r = self.rep("2026-11-10 10:00")
        ids = [x["id"] for x in r["findings"]]
        self.assertIn("host:oom:mon-09-nov", ids)
        self.assertNotIn("host:oom:sat-31-oct", ids, "older than 3 days: history, not a flag")
        # status.md: a placeholder is "can't see", never "old"; parts that are DOWN are red
        self.write("_agent/vm/status.md", "# Host status\n\n**Not written yet.** The health check overwrites this file.\n")
        r = self.rep("2026-11-10 10:00")
        self.assertNotIn("host:status-old", [x["id"] for x in r["findings"]])
        self.assertTrue(any("not written yet" in c for c in r["cantsee"]))
        self.write("_agent/vm/status.md", "# Host status (uni-vm)\n\n**Overall: PROBLEM: drive** (checked Tue 10 Nov 2026 "
                   "09:45 CET)\n\n| Part | State |\n|---|---|\n| Vault `/home/x/vault` | DOWN |\n"
                   "| Agent login (claude) | ok |\n| Free memory | 812 MB |\n")
        lv = {x["id"]: x["level"] for x in self.rep("2026-11-10 10:00")["findings"]}
        self.assertEqual((lv.get("host:status-overall"), lv.get("host:part:vault")), ("red", "red"))
        self.assertNotIn("host:part:agent-login", lv)
        self.assertNotIn("host:status-old", lv, "checked 15 min ago")
        self.assertEqual(self.level("2026-11-11 12:00", "host:status-old"), "amber", "checked over 26 h ago")

    def test_vault_watch_missed_run(self):
        text = (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace(
            'prep_check = "07:30"', 'prep_check = "07:30"\nvault_watch = ["08:17", "13:17", "18:17", "22:17"]').replace(
            '"inbox-sync"]', '"inbox-sync", "vault-watch"]')
        self.write("_agent/uni-os.toml", text)
        self.write("_agent/vault-watch/log.md", "# Vault watch log\n")
        self.assertIsNone(self.level("2026-11-10 13:43", "watch:missed-run"), "never ran yet: nothing to judge")
        self.write("_agent/vault-watch/log.md", "# Vault watch log\n- 2026-11-10 08:17 | new 1, changed 2, deleted 0\n")
        self.assertIsNone(self.level("2026-11-10 13:30", "watch:missed-run"), "13:17 slot still within the grace")
        self.assertEqual(self.level("2026-11-10 13:43", "watch:missed-run"), "amber")
        self.write("_agent/vault-watch/log.md", "# Vault watch log\n- 2026-11-10 13:18 | new 0, changed 1, deleted 0\n")
        self.assertIsNone(self.level("2026-11-10 13:43", "watch:missed-run"))

    def test_snapshot_missed_slot(self):
        self.write("_agent/jobs/inbox-sync/job.conf", 'TITLE="Inbox sync"\nSLOTS="07:15, 13:15, 18:15"\nDAYS="Mon,Tue,Wed,Thu,Fri,Sat,Sun"\n')
        snap = {"schema": 1, "generated": "2026-11-10T13:50:00+01:00", "host": {},
                "jobs": [{"name": "inbox-sync", "on": True, "exit": 0, "last_run": "2026-11-10T07:15:30+01:00"}]}
        self.write("_agent/vm/snapshot.json", json.dumps(snap))
        self.assertIsNone(self.level("2026-11-10 13:30", "job:inbox-sync:missed"), "within the grace")
        self.assertEqual(self.level("2026-11-10 13:40", "job:inbox-sync:missed"), "red")

    def test_bonus_pace(self):
        self.write("AD/ad.md", '---\ncourse: algo\nbonus_banked: "20 / 30"\nbonus_target: "80 % of ~120"\n---\n# AD\n')
        self.assertEqual(self.level("2026-11-10 10:00", "bonus:algo:pace"), "red")
        self.write("AD/ad.md", '---\ncourse: algo\nbonus_banked: "23.5 / 30"\nbonus_target: "80 %"\n---\n')
        self.assertEqual(self.level("2026-11-10 10:00", "bonus:algo:pace"), "amber")

    def test_results_after_graded_fixture(self):
        r = self.rep("2026-12-09 10:00")
        self.assertIn("result:prog-timed-task-2", [m["id"] for m in r["missing_results"]])

    def test_rule_error_becomes_grey(self):
        text =(self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace('prep_check = "07:30"', 'prep_check = "31:99"')
        self.write("_agent/uni-os.toml", text)
        self.assertEqual(self.level("2026-11-10 10:00", "rule-error:prep"), "grey")
        self.assertEqual(self.level("2026-11-10 10:00", "due:ad-peer-grading-7:overdue"), "red", "other rules still run")


class ModulesOff(HeartbeatBase):
    modules = ["core", "notifications", "heartbeat"]

    def test_rules_degrade(self):
        p = self.write("inbox/2026-11-10-la-update.md", "update\n")
        os.utime(p, (ts_of("2026-11-01 05:00"), ts_of("2026-11-01 05:00")))
        (self.v / "semester/prep/prep-2026-11-10.md").unlink()
        r = self.rep("2026-11-10 10:00")
        self.assertEqual([x["id"] for x in r["findings"] if x["level"] != "grey"], [], "no module, no rule")
        self.assertEqual(r["due"], [])


class GateAndTriggers(HeartbeatBase):
    def test_flow(self):
        code, out = self.gate("2026-11-10 10:00")
        self.assertEqual(code, 0)
        self.assertIn("first run", out)
        self.commit_at("2026-11-10 10:00")
        self.assertEqual(self.flags_doc()["schema"], 1)
        self.assertEqual(self.state_doc()["last_run"]["at"][:16], "2026-11-10T10:00")
        self.assertEqual(self.gate("2026-11-10 10:05"), (1, "skip: nothing fired since the last run"))
        code, out = self.gate("2026-11-10 16:01")
        self.assertEqual(code, 0)
        self.assertIn("block ended", out)
        fired = [f["trigger"] for f in self.rep("2026-11-10 12:01")["fired"]]
        self.assertNotIn("block ended", fired, "a lecture end is no trigger")
        self.write("progress/weeks/week-08.md", WEEK_PAGE.replace("| feedback only | open |", "| feedback only | submitted |"))
        code, out = self.gate("2026-11-10 10:06")
        self.assertIn("inputs changed", out)
        self.commit_at("2026-11-10 10:06")
        self.write("progress/weeks/week-08.md", (self.v / "progress/weeks/week-08.md").read_text(encoding="utf-8").replace(
            "| AD peer grading 7 |", "| AD theory sheet 8 | Wed 11 Nov 12:00 | | 4 pts | open |\n| AD peer grading 7 |"))
        self.commit_at("2026-11-10 10:07")
        fired = [f["trigger"] for f in self.rep("2026-11-10 12:01")["fired"]]
        self.assertIn("due in 24 h", fired)
        fired = [f["trigger"] for f in self.rep("2026-11-11 06:01")["fired"]]
        self.assertIn("due in 6 h", fired)

    def test_outcome_trigger(self):
        self.commit_at("2026-11-10 19:00")
        (self.v / "semester/prep/prep-2026-11-11.md").unlink()
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"].pop("2026-11-11")
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        code, out = self.gate("2026-11-10 19:52")
        self.assertEqual(code, 0)
        self.assertIn("outcome check", out)
        x = next(x for x in self.rep("2026-11-10 19:52")["findings"] if x["id"] == "prep:tomorrow-missing:2026-11-11")
        self.assertTrue(x["outcome"])

    def test_skips_and_force(self):
        self.commit_at("2026-12-08 10:00")
        self.assertEqual(self.gate("2026-12-08 17:00")[0], 1)
        self.assertIn("quiet window: PROG timed task 2", self.gate("2026-12-08 17:00")[1])
        log = (self.tmp / "state" / "heartbeat" / "precheck.log").read_text(encoding="utf-8")
        self.assertIn("2026-12-08 17:00 | gate | skip: quiet window: PROG timed task 2", log,
                      "a skip inside a hard window is still logged")
        self.assertEqual(self.gate("2026-11-10 10:09", "--force"), (0, "run: forced"))
        soft = '  { from = "2026-11-20", to = "2026-11-20", reason = "soft day", urgent_ok = true },\n'
        text = (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace(
            "quiet_windows = [\n", "quiet_windows = [\n" + soft)
        self.write("_agent/uni-os.toml", text)
        self.assertNotIn("quiet window", self.gate("2026-11-20 10:00")[1], "soft windows don't stop the heartbeat")
        code, out = self.gate("2027-03-01 10:00")
        self.assertEqual(code, 1)
        self.assertIn("after the term", out)

    def test_requests_snooze_by_id(self):
        self.commit_at("2026-11-10 09:00")
        st = self.state_doc()
        st["flagged"].pop("due:ad-peer-grading-7:overdue", None)
        (self.v / "_agent/heartbeat/state.json").write_text(json.dumps(st), encoding="utf-8")
        fired = [f.get("id") for f in self.rep("2026-11-10 09:30")["fired"] if f["trigger"] == "new red"]
        self.assertIn("due:ad-peer-grading-7:overdue", fired)
        self.write("_agent/heartbeat/requests.md", "# Requests\n- 2026-11-10 09:20 | snooze | the AD peer grading, "
                   "`due:ad-peer-grading-*` | until 2026-11-12 | Alex to the coordinator\n")
        r = self.rep("2026-11-10 09:30")
        x = next(x for x in r["findings"] if x["id"] == "due:ad-peer-grading-7:overdue")
        self.assertTrue(x["snoozed"])
        self.assertNotIn("due:ad-peer-grading-7:overdue", [f.get("id") for f in r["fired"] if f["trigger"] == "new red"])
        self.assertFalse(next(x for x in self.rep("2026-11-13 09:30")["findings"]
                              if x["id"] == "due:ad-peer-grading-7:overdue")["snoozed"], "snooze expired")

    def test_acting_mode(self):
        self.assertEqual(self.rep("2026-11-10 10:00")["effective_acting"], "safe")
        os.environ["UNI_OS_HEARTBEAT_ACT_MODE"] = "full"
        self.assertEqual(self.rep("2026-11-10 10:00")["effective_acting"], "full")
        text = (self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace(
            "[heartbeat]\n", '[heartbeat]\nsafe_windows = [ { from = "2026-11-09", to = "2026-11-29", reason = "plan freeze" } ]\n')
        self.write("_agent/uni-os.toml", text)
        r = self.rep("2026-11-10 10:00")
        self.assertEqual(r["effective_acting"], "safe")
        self.assertEqual(self.rep("2026-11-30 10:00")["effective_acting"], "full")


class Commit(HeartbeatBase):
    def test_commit(self):
        self.commit_at("2026-11-10 10:00")
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"flags": [{"id": "x", "level": "pink", "text": "t"}], "log": "l"}), encoding="utf-8")
        self.assertEqual(self.hb("commit", str(bad), "--now", "2026-11-10 10:10")[0], 2, "bad level refused")
        ino = os.stat(self.v / "_agent/heartbeat/flags.json").st_ino
        good = self.tmp / "good.json"
        good.write_text(json.dumps({
            "flags": [{"id": "judgment:la-a8", "level": "amber", "text": "LA A8 not started", "source": "judgment"}],
            "snoozes": {"judgment:old": {"until": "2026-11-01", "why": "x"}, "judgment:keep": {"until": None, "why": "Alex"}},
            "pushed": {"ids": ["judgment:la-a8"], "at": "2026-11-10T10:10:00+01:00"}, "log": "flagged LA A8"}), encoding="utf-8")
        self.assertEqual(self.hb("commit", str(good), "--now", "2026-11-10 10:10")[0], 0)
        self.assertEqual(os.stat(self.v / "_agent/heartbeat/flags.json").st_ino, ino, "rewritten in place")
        f = self.flags_doc()["flags"][0]
        self.assertEqual((f["since"][:16], f["pushed_at"][:16]), ("2026-11-10T10:10", "2026-11-10T10:10"))
        self.hb("commit", str(good), "--now", "2026-11-10 13:10")
        self.assertEqual(self.flags_doc()["flags"][0]["since"][:16], "2026-11-10T10:10", "since kept")
        self.assertEqual(sorted(self.state_doc()["snoozes"]), ["judgment:keep"], "expired snooze dropped")
        log = (self.v / "_agent/heartbeat/heartbeat-log.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"\| slot \| ", log)), 3)

    def test_dry_run_commit_and_tracker(self):
        self.commit_at("2026-11-10 10:00")
        before = [(self.v / "_agent/heartbeat" / n).read_bytes() for n in ("flags.json", "state.json")]
        dry = self.tmp / "dry"
        os.environ["UNI_OS_HEARTBEAT_DRY_DIR"] = str(dry)
        os.environ["UNI_DRY_RUN"] = "1"
        self.commit_at("2026-11-10 13:20")
        self.assertEqual([(self.v / "_agent/heartbeat" / n).read_bytes() for n in ("flags.json", "state.json")], before)
        self.assertEqual(sorted(p.name for p in dry.iterdir()), ["flags.json", "heartbeat-log.md", "state.json"])
        self.hb("tracker", "asked Plan & progress to move the LA block", "--now", "2026-11-10 13:20")
        self.assertIn("(heartbeat): asked Plan", (dry / "tracker-log-lines.md").read_text(encoding="utf-8"))
        self.assertFalse((self.v / "progress/tracker-log.md").exists())
        os.environ.pop("UNI_DRY_RUN")
        self.hb("tracker", "asked Plan & progress to move the LA block", "--now", "2026-11-10 13:21")
        last = (self.v / "progress/tracker-log.md").read_text(encoding="utf-8").strip().splitlines()[-1]
        self.assertEqual(last, "- Tue 10 Nov 2026 ~13:21 (heartbeat): asked Plan & progress to move the LA block")

    def test_log_state_flags(self):
        self.assertEqual(self.hb("log", "WOULD message Plan & progress: x", "--now", "2026-11-10 10:00")[0], 0)
        self.assertIn("| note | WOULD message", (self.v / "_agent/heartbeat/heartbeat-log.md").read_text(encoding="utf-8"))
        code, out = self.hb("flags", "--now", "2026-11-10 10:00")
        self.assertIn("no flags yet", out)
        self.commit_at("2026-11-10 10:00")
        code, out = self.hb("flags", "--now", "2026-11-10 10:01")
        self.assertIn("due:ad-peer-grading-7:overdue", out)
        code, out = self.hb("state", "--json", "--now", "2026-11-10 10:01")
        self.assertEqual(json.loads(out)["flags"], len(self.flags_doc()["flags"]))


class Ask(HeartbeatBase):
    def test_session_ask(self):
        self.hb("state", "--ask-test", "--now", "2026-11-10 13:00")
        self.assertTrue(self.rep("2026-11-10 13:00")["ask_test_due"])
        code, out = self.hb("ask", "--ids", "due:ad-quiz-week-9:result", "--text", "AD quiz Week 9 score?",
                            "--now", "2026-11-16 07:50")
        self.assertEqual(code, 10, "10 min before the weekly quiz window: not asked")
        self.assertTrue((self.st / "ask-test-due").exists(), "marker kept")
        os.environ["UNI_DRY_RUN"] = "1"
        os.environ["UNI_OS_HEARTBEAT_DRY_DIR"] = str(self.tmp / "dry")
        self.assertEqual(self.hb("ask", "--ids", "test:ask-path", "--text", "test", "--now", "2026-11-10 13:22")[0], 0)
        self.assertTrue((self.st / "ask-test-due").exists(), "a dry ask keeps the marker")
        os.environ.pop("UNI_DRY_RUN")
        code, out = self.hb("ask", "--ids", "due:ad-quiz-week-9:result", "--text", "AD quiz Week 9 score?",
                            "--now", "2026-11-10 13:22")
        self.assertEqual(code, 0, out)
        self.assertIn("would run: true heartbeat-ask", out)
        self.assertFalse((self.st / "ask-test-due").exists(), "a real ask removes the marker")
        self.assertEqual(self.hb("ask", "--has-pending", "--now", "2026-11-10 13:23")[0], 0)
        self.assertEqual(self.hb("ask", "--gate-id", "--now", "2026-11-10 13:23")[1], "heartbeat-ask")
        code, out = self.hb("ask", "--take", "--now", "2026-11-10 13:30")
        self.assertEqual(json.loads(out)["question"], "AD quiz Week 9 score?")
        self.assertEqual(self.hb("ask", "--has-pending", "--now", "2026-11-10 13:31")[0], 1, "asked once")
        self.assertTrue(list((self.st / "ask").glob("taken-*.json")))


class AskInline(HeartbeatBase):
    start_command = ""

    def test_inline_ask_is_a_gated_push(self):
        code, out = self.hb("ask", "--ids", "due:ad-quiz-week-9:result", "--text", "AD quiz Week 9 score?",
                            "--now", "2026-11-10 13:22")
        self.assertEqual(code, 0, out)
        self.assertIn("One question: AD quiz Week 9 score?", self.sent.read_text(encoding="utf-8"))
        code, out = self.hb("ask", "--ids", "due:la-quiz-4:result", "--text", "LA quiz 4 score?", "--now", "2026-11-10 17:00")
        self.assertEqual(code, 12, "at most one question a day")

    def test_watch_needs_a_start_command(self):
        code, out = self.hb("watch", "--now", "2026-11-10 10:30")
        self.assertIn("no way to start a job here", out)

    def test_start_command_fallbacks(self):
        ctx = hb_cmd._ctx(type("A", (), {"vault": str(self.v), "now": "2026-11-10 10:30", "dry_run": False})())
        self.assertEqual(hr.start_command(ctx), ("", None))
        self.assertEqual(hr.ask_mode(ctx), "inline")
        os.environ["UNI_JOB_START"] = 'python run_job.py --job {job}'
        self.assertEqual(hr.start_command(ctx)[1], "runner")
        self.assertEqual(hr.ask_mode(ctx), "inline", "a laptop runner can't host the question session")
        os.environ.pop("UNI_JOB_START")
        os.environ["UNI_HOST"] = "vm"
        self.assertEqual(hr.start_command(ctx), (hr.VM_START, "host"))
        self.assertEqual(hr.ask_mode(ctx), "session")
        self.assertEqual(self.rep("2026-11-10 10:30")["ask_mode"], "session")

    def test_session_mode_without_a_start_command_asks_inline(self):
        text =(self.v / "_agent/uni-os.toml").read_text(encoding="utf-8").replace(
            "[heartbeat]\n", '[heartbeat]\nask_mode = "session"\n')
        self.write("_agent/uni-os.toml", text)
        code, out = self.hb("ask", "--ids", "due:ad-quiz-week-9:result", "--text", "AD quiz Week 9 score?",
                            "--now", "2026-11-10 13:22")
        self.assertEqual(code, 0, out)
        self.assertIn("asking inline instead", out)
        self.assertEqual(self.hb("ask", "--has-pending", "--now", "2026-11-10 13:23")[0], 1, "no orphan question")
        self.assertIn("One question: AD quiz Week 9 score?", self.sent.read_text(encoding="utf-8"))


class Watch(HeartbeatBase):
    def test_watch(self):
        self.commit_at("2026-11-10 09:55")
        self.assertEqual(self.hb("watch", "--now", "2026-11-10 10:30")[1], "no event run: nothing urgent")
        (self.v / "semester/prep/prep-2026-11-10.md").unlink()
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"].pop("2026-11-10")
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        self.assertEqual(self.hb("watch", "--now", "2026-11-10 12:30")[1], "no event run: the 13:05 slot is near")
        self.assertEqual(self.hb("watch", "--now", "2026-11-10 21:00")[1], "no event run: outside 07:30-20:45")
        code, out = self.hb("watch", "--now", "2026-11-10 10:30")
        self.assertIn("event run started", out)
        code, out = self.gate("2026-11-10 10:31")
        self.assertTrue(out.startswith("run: event"), out)
        self.assertTrue((self.st / "event-current.json").exists())
        self.commit_at("2026-11-10 10:33")
        self.assertFalse((self.st / "event-current.json").exists(), "commit clears the event marker")
        self.assertEqual(self.flags_doc()["run"]["kind"], "event")
        self.write("inbox/2026-11-10-la-update.md", "x\n")
        os.utime(self.v / "inbox/2026-11-10-la-update.md", (ts_of("2026-11-10 08:00"), ts_of("2026-11-10 08:00")))
        self.assertIn("event run started", self.hb("watch", "--now", "2026-11-10 15:00")[1])
        self.commit_at("2026-11-10 15:02")
        self.write("inbox/2026-11-10-dm-update.md", "y\n")
        os.utime(self.v / "inbox/2026-11-10-dm-update.md", (ts_of("2026-11-10 09:00"), ts_of("2026-11-10 09:00")))
        self.assertEqual(self.hb("watch", "--now", "2026-11-10 16:00")[1], "no event run: event cap reached (2 today)")


class Outcomes(HeartbeatBase):
    def test_outcomes_push(self):
        (self.v / "semester/prep/prep-2026-11-11.md").unlink()
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"].pop("2026-11-11")
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        code, out = self.hb("outcomes", "--now", "2026-11-10 19:52")
        self.assertIn("OUTCOME prep:tomorrow-missing:2026-11-11: no prep note for Wed 11 Nov yet", out)
        self.assertFalse(self.sent.exists(), "without --push nothing is sent")
        code, out = self.hb("outcomes", "--push", "--now", "2026-11-10 19:53")
        self.assertEqual(code, 0)
        self.assertIn("Outcome check: no prep note for Wed 11 Nov yet", self.sent.read_text(encoding="utf-8"))
        self.hb("outcomes", "--push", "--now", "2026-11-10 20:08")
        self.assertEqual(len(self.sent.read_text(encoding="utf-8").splitlines()), 1, "same problem: dedupe")

    def test_gap_open_for_a_day(self):
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"]["2026-11-11"]["gaps"] = ["DM notes not in the vault yet"]
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        out = self.hb("outcomes", "--now", "2026-11-10 09:00")[1]
        self.assertNotIn("gap-open", out, "first seen now")
        out = self.hb("outcomes", "--now", "2026-11-11 09:01")[1]
        self.assertIn("OUTCOME prep:gap-open:2026-11-11: prep gap open for over 24 h for Wed 11 Nov\n", out + "\n")
        self.assertNotIn("DM notes", out, "gap text never in an outcome push")
        self.assertNotIn("prep-2026", out, "no file name in an outcome push")

    def test_one_sender(self):
        """Exactly one machine pushes outcome checks: with the vm module, only the host."""
        self.assertEqual(hr.outcome_sender(hr.Context(self.v, now=dt.datetime(2026, 11, 10, 10, 0)))[0], "heartbeat",
                         "laptop app tasks only: the heartbeat pushes these findings itself")
        self.write_config('\n[runtime]\nlaptop_scheduler = "os"\n')
        self.assertEqual(hr.outcome_sender(hr.Context(self.v, now=dt.datetime(2026, 11, 10, 10, 0)))[0], "job")
        self.assertIn("Outcome sender: job", self.hb("report", "--now", "2026-11-10 10:00")[1])
        self.modules = MODULES + ["vm"]
        self.write_config('\n[runtime]\nlaptop_scheduler = "os"\n')
        self.assertEqual(hr.outcome_sender(hr.Context(self.v, now=dt.datetime(2026, 11, 10, 10, 0)))[0], "host")
        (self.v / "semester/prep/prep-2026-11-11.md").unlink()
        st = json.loads((self.v / "_agent/daily-prep/state.json").read_text(encoding="utf-8"))
        st["days"].pop("2026-11-11")
        self.write("_agent/daily-prep/state.json", json.dumps(st))
        code, out = self.hb("outcomes", "--push", "--now", "2026-11-10 19:53")
        self.assertEqual(code, 0)
        self.assertIn("OUTCOME prep:tomorrow-missing:2026-11-11", out)
        self.assertIn("push: not from this machine", out)
        self.assertFalse(self.sent.exists(), "the laptop leaves the push to the host")
        os.environ["UNI_HOST"] = "vm"
        self.hb("outcomes", "--push", "--now", "2026-11-10 19:54")
        self.assertIn("Outcome check: no prep note for Wed 11 Nov yet", self.sent.read_text(encoding="utf-8"),
                      "on the host the job pushes")

    def test_off_switch(self):
        self.st.mkdir(parents=True, exist_ok=True)
        (self.st / "outcomes-off").write_text("off\n", encoding="utf-8")
        (self.v / "semester/prep/prep-2026-11-10.md").unlink()
        self.assertEqual(self.hb("outcomes", "--push", "--now", "2026-11-10 10:00"), (0, ""))


class ReportAndFiles(HeartbeatBase):
    def test_report_renders(self):
        code, out = self.hb("report", "--now", "2026-11-10 10:00")
        self.assertEqual(code, 0)
        self.assertIn("# Heartbeat pre-check, 2026-11-10 10:00 (Tue, term week 8)", out)
        self.assertIn("`due:ad-peer-grading-7:overdue`", out)
        self.assertIn("13:30-16:00 AD_ Sheet 8 (deep) [study]", out)
        self.assertIn("10:15-12:00 L: Algorithms lecture [other]", out)
        code, out = self.hb("precheck", "--report", "--now", "2026-11-10 10:00")
        self.assertEqual(code, 0)

    def test_no_vault_is_an_error(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hb_cmd.main(["heartbeat", "report", "--vault", str(self.tmp / "nope")])
        self.assertEqual(code, 2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hb_cmd.main(["heartbeat", "precheck", "--vault", str(self.tmp / "nope")])
        self.assertEqual(code, 0, "the pre-check fails open: a runner reads any non-zero exit as skip")
        self.assertTrue(buf.getvalue().startswith("run: pre-check error: no vault found"), buf.getvalue())


class PrecheckFailsOpen(HeartbeatBase):
    """An internal pre-check error must not read as "skip" (exit 1 or 2 both skip in the
    runners): it prints "run: pre-check error: ...", writes the job's failure flag, exits 0."""
    FLAG = "_agent/logs/flags/heartbeat.md"

    def flag(self, name="heartbeat"):
        p = self.v / "_agent" / "logs" / "flags" / (name + ".md")
        return p.read_text(encoding="utf-8") if p.exists() else None

    def test_invalid_config(self):
        self.write("_agent/uni-os.toml", "[term\ntimezone = Europe/Zurich\n")
        code, out = self.gate("2026-11-10 10:00")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("run: pre-check error: "), out)
        self.assertNotIn("Traceback", out)
        flag = self.flag()
        self.assertIsNotNone(flag, "the failure flag is written")
        self.assertEqual(hr.frontmatter(flag), {"job": "heartbeat", "at": "2026-11-10 10:00", "level": "red"})
        body = [ln for ln in re.sub(r"^---[\s\S]*?---", "", flag, count=1).split("\n") if ln.strip()]
        self.assertTrue(body[0].startswith("pre-check error: "), body)
        self.assertIn("precheck | ", (self.st / "precheck.log").read_text(encoding="utf-8"))

    def test_invalid_config_through_the_real_loader(self):
        pushgate.load_config = self._orig_load
        self.write("_agent/uni-os.toml", "[notify]\nquiet_hours = 21:00-07:30\n")
        with self.assertRaises(pushgate.ConfigUnreadable) as cm:
            pushgate.load_config(self.v)
        self.assertIn("_agent/uni-os.toml is not valid TOML", str(cm.exception))
        self.assertIsInstance(cm.exception, ValueError)
        code, out = self.gate("2026-11-10 10:00")
        self.assertEqual(code, 0, out)
        self.assertIn("run: pre-check error: ", out)
        self.assertIn("not valid TOML", out)
        self.assertIsNotNone(self.flag())

    def test_internal_error_and_the_rule_flag(self):
        orig = hr.compute

        def broken(ctx):
            raise RuntimeError("simulated bug")
        hr.compute = broken
        try:
            code, out = self.gate("2026-11-10 10:00")
            self.assertEqual((code, out), (0, "run: pre-check error: RuntimeError: simulated bug"))
            code, out = self.hb("precheck", "--report", "--now", "2026-11-10 10:00")
            self.assertEqual(code, 2, "--report is not a PRECHECK: errors stay exit 2")
        finally:
            hr.compute = orig
        self.assertIn("simulated bug", self.flag())
        # the next pre-check turns the flag into a red finding (the agent deletes it once it commits)
        self.assertEqual(self.level("2026-11-10 10:05", "job:heartbeat:failed"), "red")

    def test_job_name_json_and_dry_run(self):
        self.write("_agent/uni-os.toml", "not toml at all = = =\n")
        os.environ["UNI_JOB"] = "heartbeat-weekend"
        code, out = self.hb("precheck", "--json", "--now", "2026-11-15 17:40")
        self.assertEqual(code, 0, out)
        doc = json.loads(out)
        self.assertTrue(doc["run"])
        self.assertTrue(doc["decision"].startswith("run: pre-check error: "))
        self.assertEqual(doc["flag"], "_agent/logs/flags/heartbeat-weekend.md")
        self.assertIn("job: heartbeat-weekend", self.flag("heartbeat-weekend"))
        self.assertIsNone(self.flag())
        os.environ["UNI_JOB"] = "daily-study-prep"
        self.hb("precheck", "--now", "2026-11-15 17:45")
        self.assertIsNotNone(self.flag(), "a non-heartbeat UNI_JOB falls back to heartbeat.md")
        (self.v / self.FLAG).unlink()
        code, out = self.hb("precheck", "--dry-run", "--now", "2026-11-15 17:50")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("run: pre-check error: "), out)
        self.assertIsNone(self.flag(), "a dry run writes no flag")


class RealLoader(HeartbeatBase):
    """The same fake vault through the framework's own config loader (module defaults merged,
    modules.enabled resolved against the catalogue), when that loader exists."""

    def setUp(self):
        super().setUp()
        pushgate.load_config = self._orig_load
        try:
            from uni_os import config  # noqa: F401
        except ImportError:
            self.skipTest("uni_os.config (the framework loader) is not there yet")

    def test_commands_run(self):
        code, out = self.hb("report", "--json", "--now", "2026-11-10 10:00")
        self.assertEqual(code, 0, out)
        r = json.loads(out)
        self.assertFalse([x for x in r["findings"] if x["id"].startswith("rule-error:")], r["findings"])
        self.assertIn(self.gate("2026-11-10 10:00")[0], (0, 1))
        self.commit_at("2026-11-10 10:00")
        self.assertEqual(self.flags_doc()["schema"], 1)


class ModuleFiles(unittest.TestCase):
    def test_defaults_match_code(self):
        if tomllib is None:
            self.skipTest("tomllib missing")
        with open(REPO / "modules" / "heartbeat" / "module.toml", "rb") as f:
            m = tomllib.load(f)
        self.assertEqual(m["id"], "heartbeat")
        self.assertEqual(m["defaults"]["heartbeat"], hr.DEFAULTS)
        self.assertEqual(m["defaults"]["schedule"], hr.SCHEDULE_DEFAULTS)
        for key in hr.DEFAULTS:
            self.assertIn("heartbeat." + key, m["config_keys"])
        jobs = sorted(j["id"] for j in m["jobs"])
        self.assertEqual(jobs, sorted(p.name for p in (REPO / "modules" / "heartbeat" / "jobs").iterdir()))

    def test_job_confs(self):
        keys = {"TITLE", "KIND", "COMMAND", "SLOTS", "DAYS", "DATES", "SCHEDULE", "SESSION", "KEEP_H", "MODEL", "EFFORT",
                "TIMEOUT_MIN", "NEEDS_VAULT", "PRECHECK", "QUIET_OK", "DRY_OK", "NOTIFY_DONE", "NOTIFY_GATE", "AGENT_LOCK",
                "LOCK_WAIT_MIN", "LAPTOP_TASK", "FAILOVER_DELAY_MIN", "MARKER", "RUNTIME", "DEFAULT_MODE"}
        for conf in list((REPO / "modules").glob("heartbeat/jobs/*/job.conf")) + \
                list((REPO / "modules").glob("notifications/jobs/*/job.conf")):
            c = hr.parse_conf(conf)
            self.assertTrue(keys <= set(c) <= keys | {"EVERY_MIN"}, (conf, set(c) ^ keys))
            for k in ("PRECHECK", "COMMAND"):
                self.assertNotRegex(c[k], r"^uni-os ", "%s %s: uni-os is not on a laptop's PATH" % (conf, k))
            self.assertIn(c["KIND"], ("agent", "command"))
            if c["KIND"] == "agent":
                self.assertTrue((conf.parent / "prompt.md").exists(), conf)
        hb = hr.parse_conf(REPO / "modules/heartbeat/jobs/heartbeat/job.conf")
        self.assertTrue(hb["PRECHECK"].endswith('/tools/uni_os.py" heartbeat precheck'), hb["PRECHECK"])
        self.assertEqual((hb["AGENT_LOCK"], hb["SESSION"], hb["DEFAULT_MODE"]), ("exclusive", "print", "off"))
        self.assertEqual(hb["SLOTS"], "{{schedule.heartbeat}}")

    def test_no_personal_data(self):
        # generic patterns only (no personal literals in the repo): Windows user folders other
        # than the <you> placeholder, ntfy topic URLs, mail addresses outside example domains
        banned = re.compile(r"C:[\\/]+Users[\\/]+(?!<you>)\w|ntfy\.sh/[A-Za-z0-9]|"
                            r"[\w.+-]+@(?!example\.)[\w-]+\.[a-z]{2,}", re.I)
        roots = [REPO / "modules" / "heartbeat", REPO / "modules" / "notifications"]
        files = [p for r in roots for p in r.rglob("*") if p.is_file()]
        files += [TOOLS / "uni_os" / n for n in ("pushgate.py", "heartbeat_rules.py")]
        files += [TOOLS / "uni_os" / "commands" / n for n in ("push.py", "heartbeat.py")]
        for p in files:
            text = p.read_text(encoding="utf-8")
            m = banned.search(text)
            self.assertIsNone(m, "%s: %r" % (p, m and m.group(0)))
            self.assertNotIn("{{heartbeat.", text, "%s: heartbeat.* is not a template root" % p)


if __name__ == "__main__":
    unittest.main()
