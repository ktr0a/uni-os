"""Tests for modules/inbox-sync/scripts/inbox_poll.py.

Run from the repo root:  python -m unittest discover -s modules/inbox-sync/tests
"""
import hashlib
import importlib.util
import io
import os
import re
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("inbox_poll", HERE.parent / "scripts" / "inbox_poll.py")
ip = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ip)

# Two update notes whose slugs share their first 60 characters.
LONG_A = "2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part A-update.md"
LONG_B = "2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part B-update.md"


class PollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.vault = root / "vault"
        (self.vault / "inbox").mkdir(parents=True)
        self.state = root / "state"
        self.marker = root / "started.txt"
        # The start command appends the job id to a marker file, so tests can see starts.
        py = sys.executable
        self.start = f'"{py}" -c "import sys; open(sys.argv[1], \'a\').write(sys.argv[2] + chr(10))" "{self.marker}" {{job}}'
        os.environ.pop("UNI_DRY_RUN", None)

    def tearDown(self):
        self.tmp.cleanup()

    def note(self, name, age_h=0.0):
        p = self.vault / "inbox" / name
        p.write_text("x", encoding="utf-8")
        t = time.time() - age_h * 3600
        os.utime(p, (t, t))
        return p

    def poll(self, *extra, now="2026-11-09 10:00"):
        argv = ["poll", "--vault", str(self.vault), "--state-dir", str(self.state),
                "--start-cmd", self.start, "--now", now, "--stale-hours", "0", *extra]
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ip.main(argv)
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def starts(self):
        # the detached start may take a moment
        for _ in range(50):
            if self.marker.exists():
                break
            time.sleep(0.1)
        return self.marker.read_text().split() if self.marker.exists() else []

    def test_no_notes_does_nothing(self):
        (self.vault / "inbox" / "inbox.md").write_text("drop zone")
        out = self.poll()
        self.assertEqual(out, "")
        self.assertEqual(self.starts(), [])

    def test_new_note_starts_once(self):
        self.note("2026-11-09_0950_ad-exercise-help-update.md")
        out = self.poll()
        self.assertIn("starting the sync", out)
        self.assertEqual(self.starts(), ["inbox-sync"])
        # same note again: already seen -> nothing
        out2 = self.poll("--min-gap-min", "0")
        self.assertEqual(out2, "")

    def test_min_gap_waits(self):
        (self.state / "jobs" / "inbox-sync").mkdir(parents=True)
        log = self.state / "jobs" / "inbox-sync" / "2026-11-09_093000.log"
        log.write_text("# exit 0 after 60s")
        now = "2026-11-09 10:00"
        t = datetime.fromisoformat("2026-11-09 09:30").timestamp()
        os.utime(log, (t, t))
        self.note("2026-11-09_0955_la-lecture-rundown-update.md")
        out = self.poll(now=now)
        self.assertIn("waiting", out)
        self.assertFalse(self.marker.exists())

    def test_dry_run_logs_are_ignored_for_gap(self):
        (self.state / "jobs" / "inbox-sync").mkdir(parents=True)
        log = self.state / "jobs" / "inbox-sync" / "2026-11-09_095000-dry.log"
        log.write_text("dry")
        t = datetime.fromisoformat("2026-11-09 09:50").timestamp()
        os.utime(log, (t, t))
        self.note("2026-11-09_0955_la-lecture-rundown-update.md")
        out = self.poll()
        self.assertIn("starting", out)

    def test_done_taps_never_start(self):
        self.note("2026-11-09_0951_cockpit-done-ad-sheet-6-update.md")
        out = self.poll()
        self.assertEqual(out, "")
        self.assertEqual(self.starts(), [])

    def test_outside_window(self):
        self.note("2026-11-09_2250_dm-exercise-help-update.md")
        out = self.poll(now="2026-11-09 23:10")
        self.assertEqual(out, "")
        self.assertFalse(self.marker.exists())

    def test_dry_run_changes_nothing(self):
        self.note("2026-11-09_0950_ad-exercise-help-update.md")
        out = self.poll("--dry-run")
        self.assertIn("starting the sync", out)
        self.assertFalse((self.state / ip.SEEN_FILE).exists())
        self.assertFalse(self.marker.exists())

    def test_note_name_outside_the_console_code_page(self):
        # A scheduled command job's stdout on Windows is cp1252: a name it can't encode must not
        # stop the poll (exit 0, seen recorded, sync started), nor the stale report.
        self.note("2026-11-09_0950_note-λ-update.md", age_h=6)
        raw = io.BytesIO()
        fake = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="\n")
        old = sys.stdout
        sys.stdout = fake
        try:
            rc = ip.main(["poll", "--vault", str(self.vault), "--state-dir", str(self.state), "--start-cmd",
                          self.start, "--now", "2026-11-09 10:00", "--stale-hours", "4", "--window", "always"])
            rc_stale = ip.main(["stale", "--vault", str(self.vault), "--stale-hours", "4"])
        finally:
            sys.stdout = old
        fake.flush()
        self.assertEqual(rc, 0)
        self.assertEqual(rc_stale, 1)
        self.assertIn("λ", (self.state / ip.SEEN_FILE).read_text(encoding="utf-8"))
        self.assertEqual(self.starts(), ["inbox-sync"])
        self.assertIn("starting the sync", raw.getvalue().decode("utf-8"))

    def test_seen_cleared_when_inbox_empty(self):
        n = self.note("2026-11-09_0950_ad-exercise-help-update.md")
        self.poll()
        n.unlink()
        self.poll()
        self.assertEqual((self.state / ip.SEEN_FILE).read_text(), "")


class HelperTests(unittest.TestCase):
    def test_window(self):
        w = ip.parse_window("07:00-22:00")
        self.assertEqual(w, (420, 1320))
        self.assertIsNone(ip.parse_window("always"))
        at = lambda s: datetime.fromisoformat(s).timestamp()
        self.assertTrue(ip.in_window(at("2026-11-09 22:00"), w))
        self.assertFalse(ip.in_window(at("2026-11-09 22:01"), w))
        self.assertTrue(ip.in_window(at("2026-11-09 23:30"), ip.parse_window("22:00-02:00")))
        with self.assertRaises(ValueError):
            ip.parse_window("morning")

    def test_stale_and_check(self):
        with tempfile.TemporaryDirectory() as d:
            inbox = Path(d) / "inbox"
            inbox.mkdir()
            old = inbox / "2026-11-09_0600_ad-exercise-help-update.md"
            tap = inbox / "2026-11-09_0600_cockpit-done-x-update.md"
            for p in (old, tap):
                p.write_text("x")
                t = time.time() - 5 * 3600
                os.utime(p, (t, t))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ip.main(["stale", "--vault", d])
            self.assertEqual(rc, 1)
            # same id as the outcome checks (tools/uni_os/heartbeat_rules.py), so the gate dedupes
            self.assertIn("OUTCOME inbox:stuck:2026-11-09-0600-ad-exercise-help-update-md: ", buf.getvalue())
            self.assertIn("2026-11-09_0600_ad-exercise-help-update.md", buf.getvalue())
            self.assertNotIn("cockpit-done", buf.getvalue())  # taps get 14 h
            self.assertEqual(ip.main(["check", "--vault", d]), 0)
            old.unlink(); tap.unlink()
            self.assertEqual(ip.main(["check", "--vault", d]), 1)
            self.assertEqual(ip.main(["check", "--vault", str(Path(d) / "missing")]), 0)
            flag = Path(d) / "_agent" / "logs" / "flags" / "inbox-sync.md"
            flag.parent.mkdir(parents=True)
            flag.write_text("---\njob: inbox-sync\nat: 2026-11-09 07:15\nlevel: red\n---\ninbox not readable\n")
            self.assertEqual(ip.main(["check", "--vault", d]), 0, "a failure flag makes the next run clear it")

    def test_split_cmd(self):
        self.assertEqual(ip.split_cmd('a "b c" d'), ["a", "b c", "d"])

    def test_push_uses_gate_options(self):
        # The push gate (`uni-os push`) takes --source, --prefix and --item; an unknown option would
        # make every alert fail with a usage error. Record the argv of a fake push command.
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "argv.txt"
            fake = [sys.executable, "-c",
                    "import sys; open(sys.argv[1], 'w').write(chr(10).join(sys.argv[2:]))", str(rec)]
            push = ip.stuck_push_text(False, 4)
            ip.push_alerts([("inbox:stuck:x", push + ": x-update.md", push),
                            ("inbox:stuck:y", "", ip.stuck_push_text(True, 14))],
                           Path(d), time.time(), fake, dry=False)
            args = rec.read_text().split("\n")
            self.assertEqual(args[:4], ["--source", "inbox-sync", "--prefix", "Outcome check: "])
            self.assertEqual(args.count("--item"), 2, "one push for all stuck notes")
            self.assertIn("inbox:stuck:x=" + push, args)
            self.assertFalse([a for a in args if "x-update.md" in a], "the file name is never in a push")
            import argparse
            sys.path.insert(0, str(HERE.parents[2] / "tools"))
            try:
                from uni_os.commands import push as push_cmd
            except Exception:  # noqa: BLE001  framework not importable: skip the contract check
                return
            p = argparse.ArgumentParser()
            push_cmd.register(p.add_subparsers())
            ns = p.parse_args(["push", *args])
            self.assertEqual(len(ns.item), 2)
            self.assertEqual(ns.prefix, "Outcome check: ")

    def test_same_wording_as_the_heartbeat_rules(self):
        # Every sender of a stuck-note alert pushes the same text with the same id.
        sys.path.insert(0, str(HERE.parents[2] / "tools"))
        try:
            from uni_os import heartbeat_rules as hr
        except Exception:  # noqa: BLE001  framework not importable: nothing to compare with
            self.skipTest("tools/uni_os not importable")
        for tap, h in ((False, 4), (True, 14), (False, 4.5)):
            self.assertEqual(ip.stuck_push_text(tap, h), hr.stuck_push_text(tap, h))
        self.assertEqual(ip.slug("2026-11-09_0600_AD Sheet (v2)-update.md"),
                         hr.slug("2026-11-09_0600_AD Sheet (v2)-update.md", 60))
        for name in (LONG_A, LONG_B, "a" * 61, "a" * 52 + " " + "b" * 20, "Ü" * 70 + "-update.md"):
            self.assertEqual(ip.slug(name), hr.slug(name, 60), name)

    def test_long_slugs_get_a_hash_short_ones_stay(self):
        # A cut slug ends in "-" + 6 hex digits of the file name's SHA-1, so two long names that
        # share their start get two ids (the same literal is checked in tests/test_heartbeat_rules.py
        # and modules/vm/tests/t-outcome-checks.sh).
        self.assertEqual(ip.slug(LONG_A), "2026-11-04-0300-la-exercise-sheet-7-corrections-and-f-2d4bf8")
        self.assertNotEqual(ip.slug(LONG_A), ip.slug(LONG_B))
        self.assertLessEqual(len(ip.slug(LONG_B)), 60)
        self.assertEqual(ip.slug("2026-11-09_0600_AD Sheet (v2)-update.md"), "2026-11-09-0600-ad-sheet-v2-update-md")
        exactly = "a" * 60
        self.assertEqual(ip.slug(exactly), exactly, "60 characters: unchanged")
        self.assertEqual(ip.slug("a" * 61), "a" * 53 + "-" + hashlib.sha1(b"a" * 61).hexdigest()[:6])

    def test_long_stuck_notes_get_distinct_ids(self):
        with tempfile.TemporaryDirectory() as d:
            inbox = Path(d)
            t = time.time() - 5 * 3600
            for name in (LONG_A, LONG_B):
                (inbox / name).write_text("x", encoding="utf-8")
                os.utime(inbox / name, (t, t))
            ids = [i for i, _, _ in ip.stale_notes(inbox, sorted(os.listdir(inbox)),
                                                  re.compile(ip.DEFAULT_TAP_PATTERN), time.time(), 4, 14)]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2, ids)
        self.assertIn("inbox:stuck:2026-11-04-0300-la-exercise-sheet-7-corrections-and-f-2d4bf8", ids)

    def test_push_stands_down_when_another_sender_owns_it(self):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d)
            (vault / "_agent").mkdir()
            self.assertEqual(ip.push_owner(vault), "", "no config: this poll may push")
            cfg = vault / "_agent" / "uni-os.toml"
            cfg.write_text('[modules]\nenabled = ["core", "inbox-sync"]\n', encoding="utf-8")
            self.assertEqual(ip.push_owner(vault), "")
            cfg.write_text('[modules]\nenabled = ["core", "inbox-sync", "notifications"]\n', encoding="utf-8")
            self.assertIn("notifications", ip.push_owner(vault))
            (vault / "_agent" / "uni-os.json").write_text('{"modules": {"enabled": ["core", "vm"]}}', encoding="utf-8")
            self.assertIn("always-on host", ip.push_owner(vault), "the generated JSON wins over the toml")
            # end to end: a stuck note with --push and the notifications module on sends nothing
            (vault / "inbox").mkdir()
            note = vault / "inbox" / "2026-11-09_0500_dm-update.md"
            note.write_text("x", encoding="utf-8")
            t = datetime.fromisoformat("2026-11-09 05:00").timestamp()
            os.utime(note, (t, t))
            rec = Path(d) / "argv.txt"
            fake = f'"{sys.executable}" -c "open(r\'{rec}\', \'w\').write(\'sent\')"'
            buf = io.StringIO()
            with redirect_stdout(buf):
                ip.main(["poll", "--vault", str(vault), "--state-dir", str(Path(d) / "state"), "--now", "2026-11-09 23:30",
                         "--push", "--push-cmd", fake])
            self.assertIn("OUTCOME inbox:stuck:2026-11-09-0500-dm-update-md: ", buf.getvalue())
            self.assertIn("push: left to the one stuck-note sender", buf.getvalue())
            self.assertFalse(rec.exists())


if __name__ == "__main__":
    unittest.main()
