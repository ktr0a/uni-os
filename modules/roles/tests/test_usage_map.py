"""Tests for modules/roles/scripts/usage_map.py with synthetic Claude Code transcripts.

Run from the repo root:  python -m unittest discover -s modules/roles/tests
Everything happens in a temp folder; no real transcript is read.
"""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("usage_map", HERE.parent / "scripts" / "usage_map.py")
um = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(um)


def assistant(mid, ts, model="claude-sonnet-4-5", i=0, o=0, cw=0, cr=0):
    return {"type": "assistant", "timestamp": ts,
            "message": {"id": mid, "model": model, "usage": {"input_tokens": i, "output_tokens": o,
                                                             "cache_creation_input_tokens": cw,
                                                             "cache_read_input_tokens": cr}}}


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


class UsageMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        proj = self.root / "C--vault"
        # a titled long-lived session: 2 turns, a big context
        self.write(proj / "aaa.jsonl", [
            {"type": "custom-title", "customTitle": "Uni coordinator"}, user("you are the coordinator"),
            assistant("m1", "2026-11-05T10:00:00Z", model="claude-opus-4-1", i=10, o=1000, cw=2000, cr=300000),
            assistant("m2", "2026-11-05T11:00:00Z", model="claude-opus-4-1", i=10, o=1000, cw=0, cr=310000),
            assistant("m0", "2026-11-01T11:00:00Z", model="claude-opus-4-1", o=99999),   # before --since: ignored
        ])
        # an untitled scheduled job (laptop header) and a dry run: both "scheduled jobs"
        self.write(proj / "bbb.jsonl", [user("You are running the scheduled job \"Daily study prep\" ..."),
                                        assistant("m3", "2026-11-05T17:31:00Z", o=200, cr=20000)])
        self.write(proj / "ccc.jsonl", [user("DRY RUN (test of this job): ..."),
                                        assistant("m4", "2026-11-06T17:31:00Z", o=100, cr=10000)])
        # an untitled chat whose first message holds a mail address
        self.write(proj / "ddd.jsonl", [user("please write to someone@example.org about the sheet"),
                                        assistant("m5", "2026-11-06T09:00:00Z", model="claude-haiku-4-5", o=300)])
        # a subagent of the coordinator, plus a duplicate of m2 (the same message in two files)
        self.write(proj / "aaa" / "subagents" / "agent-1.jsonl", [
            user("look something up"), assistant("m6", "2026-11-05T10:30:00Z", o=500, cr=1000),
            assistant("m2", "2026-11-05T11:00:00Z", model="claude-opus-4-1", i=10, o=1000, cr=310000)])

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in records) + "\nnot json\n", encoding="utf-8")

    def rows(self, **kw):
        return {r["label"]: r for r in um.scan(str(self.root), "2026-11-04T09:00", "laptop", **kw)}

    def test_last_reset(self):
        now = dt.datetime(2026, 11, 7, 12, 0, tzinfo=dt.timezone.utc)          # a Saturday
        self.assertEqual(um.last_reset(now, "Wed", "09:00"), "2026-11-04T09:00")
        self.assertEqual(um.last_reset(now, "Sat", "13:00"), "2026-10-31T13:00", "later today: last week's")
        self.assertEqual(um.last_reset(now, "Sat", "11:00"), "2026-11-07T11:00")
        self.assertEqual(um.last_reset(now, "monday", "00:30"), "2026-11-02T00:30")

    def test_grouping_and_units(self):
        r = self.rows()
        self.assertEqual(set(r), {"Uni coordinator", "Uni coordinator (its agents)", "scheduled jobs",
                                  "please write to <mail> about the sheet"})
        coord = r["Uni coordinator"]
        self.assertEqual(coord["turns"], 2, "the message before --since is left out")
        # (10 + 1.25*2000 + 0.1*300000 + 5*1000) * 5/3 / 1000 + (10 + 0.1*310000 + 5*1000) * 5/3 / 1000
        want = ((10 + 2500 + 30000 + 5000) + (10 + 31000 + 5000)) * (5 / 3) / 1000
        self.assertAlmostEqual(coord["cost"], want, places=6)
        self.assertEqual(coord["now"], 310010, "context at the last turn")
        self.assertEqual(r["scheduled jobs"]["turns"], 2, "job header and dry-run preamble both count as jobs")
        self.assertEqual(r["scheduled jobs"]["now"], 0, "no 'Now' for the jobs group")
        agents = r["Uni coordinator (its agents)"]
        self.assertEqual(agents["turns"], 1, "the duplicated message is counted once")
        self.assertAlmostEqual(r["please write to <mail> about the sheet"]["cost"], 5 * 300 / 3 / 1000, places=6)

    def test_factors_and_prefixes(self):
        r = self.rows(factors={"opus": 1.0, "sonnet": 1.0, "haiku": 1.0})
        self.assertAlmostEqual(r["please write to <mail> about the sheet"]["cost"], 1.5, places=6)
        r = self.rows(job_prefixes=("please write",))
        self.assertIn("scheduled jobs", r)
        self.assertEqual(r["scheduled jobs"]["turns"], 1, "only the custom prefix now")

    def test_labels(self):
        long = "x" * 40 + " someone.else@example.org wrote"
        self.assertNotIn("someone", um.group_of(long, None), "masked before the 48-character cut")
        self.assertEqual(um.group_of("hi", "job: Daily study prep · Tue 17:30"), "scheduled jobs")
        self.assertEqual(um.group_of('Relay request: please forward "x" to the session named y', None),
                         "relayed messages")
        self.assertEqual(um.group_of("", None), "(no text)")

    def test_old_files_are_skipped(self):
        old = self.root / "C--vault" / "old.jsonl"
        self.write(old, [user("old"), assistant("m9", "2026-11-05T10:00:00Z", o=1)])
        t = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp()
        os.utime(old, (t, t))
        self.assertNotIn("old", self.rows())

    def run_main(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = um.main(["--projects", str(self.root), "--now", "2026-11-07T12:00", *argv])
        return code, buf.getvalue()

    def test_table_and_json(self):
        code, out = self.run_main("--host", "laptop")
        self.assertEqual(code, 0)
        self.assertIn("Since 2026-11-04T09:00 UTC, laptop; cloud sessions are not visible.", out)
        self.assertIn("| Session | Where | Units | Share | Turns | Output | Re-read per turn | Now | Model |", out)
        lines = [ln for ln in out.splitlines() if ln.startswith("| Uni coordinator |")]
        self.assertEqual(len(lines), 1)
        self.assertIn("| 310k | opus-4-1 |", lines[0])
        self.assertIn("Per day: 11-05 ", out)
        self.assertNotIn("someone@example.org", out, "mail addresses are masked")
        code, out = self.run_main("--json")
        data = json.loads(out)
        self.assertEqual(sorted(r["label"] for r in data)[0], "Uni coordinator")
        self.assertTrue(all(isinstance(r["days"], dict) for r in data))
        code, out = self.run_main("--top", "1")
        self.assertIn("| 3 others |", out)

    def test_remote_merge(self):
        rows = [{"label": "Plan & progress (VM)", "host": "vm", "cost": 12.0, "turns": 3, "out": 3000, "cr": 9000,
                 "now": 90000, "last": "", "days": {"2026-11-06": 12.0}, "models": {"sonnet-4-5": 3}}]
        fake = Path(self.tmp.name) / "remote.py"
        fake.write_text("import json, sys\nassert '--since' in sys.argv\nprint(json.dumps(%r))\n" % rows, encoding="utf-8")
        code, out = self.run_main("--host", "laptop", "--remote", '"%s" "%s"' % (sys.executable, fake))
        self.assertEqual(code, 0)
        self.assertIn("| Plan & progress (VM) | vm |", out)
        self.assertIn("laptop, vm", out)
        code, out = self.run_main("--remote", '"%s" -c "import sys; sys.exit(3)"' % sys.executable)
        self.assertIn("Remote not reached", out)
        self.assertIn("| Uni coordinator |", out, "local rows still shown")

    def test_missing_folder(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(um.main(["--projects", str(self.root / "nope")]), 1)


if __name__ == "__main__":
    unittest.main()
