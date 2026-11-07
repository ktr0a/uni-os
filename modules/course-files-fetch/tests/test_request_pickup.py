"""Tests for scripts/request_pickup.py (stdlib unittest; any OS).

    python -m unittest discover -s modules/course-files-fetch/tests
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import request_pickup as rp  # noqa: E402

CFG = {
    "courses": [
        {"id": "algo", "short": "AD", "folder": "A&D", "official_subfolders": ["assignments", "assignments/solutions"]},
        {"id": "dm", "short": "DM", "folder": "DM", "official_subfolders": ["assignments", "script and slides"]},
    ],
    "course_fetch": {
        "date_guards": [{"course": "dm", "pattern": "(?i)solution[_ -]?0*6(\\D|$)", "not_before": "2026-10-29",
                         "reason": "graded quiz solution"}],
    },
}


class Helpers(unittest.TestCase):
    def test_check_name(self):
        self.assertIsNone(rp.check_name("Exercise_07.pdf"))
        self.assertIsNone(rp.check_name("week 3 (v2, EN).pdf"))
        for bad in ["../x.pdf", "a/b.pdf", "a\\b.pdf", ".hidden.pdf", "x.pdf.", "x.pdf ", "", "a" * 201, "c:x.pdf"]:
            self.assertIsNotNone(rp.check_name(bad), bad)

    def test_make_id(self):
        now = dt.datetime(2026, 11, 7, 9, 5, 3)
        self.assertEqual(rp.make_id("Ex 07 (1).pdf", now), "20261107-090503-Ex_07__1_.pdf")
        self.assertLessEqual(len(rp.make_id("x" * 300, now)), 16 + 60)

    def test_allowed_folders(self):
        self.assertEqual(rp.allowed_folders(CFG), ["A&D/assignments", "A&D/assignments/solutions",
                                                    "DM/assignments", "DM/script and slides"])
        self.assertEqual(rp.allowed_folders({}), [])

    def test_guard(self):
        before, after = dt.date(2026, 10, 28), dt.date(2026, 10, 29)
        self.assertIn("date guard", rp.guard_hit(CFG, "Solution_06.pdf", "DM/assignments", before))
        self.assertIsNone(rp.guard_hit(CFG, "Solution_06.pdf", "DM/assignments", after))
        self.assertIsNone(rp.guard_hit(CFG, "Solution_60.pdf", "DM/assignments", before))
        self.assertIsNone(rp.guard_hit(CFG, "Solution_06.pdf", "A&D/assignments", before))
        # without (?i) the guard is still case-insensitive, like the pick-up's PowerShell -match
        cfg = {"courses": CFG["courses"], "course_fetch": {"date_guards": [
            {"folder": "DM", "pattern": "solution_06", "not_before": "2026-10-29"}]}}
        self.assertIn("date guard", rp.guard_hit(cfg, "SOLUTION_06.pdf", "DM/assignments", before))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name) / "My Vault"
        (self.vault / "_agent").mkdir(parents=True)
        (self.vault / "_agent" / "uni-os.json").write_text(json.dumps(CFG), encoding="utf-8")
        (self.vault / "DM" / "assignments").mkdir(parents=True)
        self.queue = self.vault / "_agent" / "course-fetch"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rp.main(["--vault", str(self.vault), "--poll-s", "0.05", *args])
        return code, buf.getvalue()

    def fake_pickup(self, status="filed", content=b"%PDF-1.7 test", delay=0.2):
        """Plays the laptop: waits for the request, files the file, writes the result."""
        def work():
            end = time.monotonic() + 5
            while time.monotonic() < end:
                reqs = list((self.queue / "pending").glob("*.json"))
                if reqs:
                    req = reqs[0]
                    q = json.loads(req.read_text(encoding="utf-8"))
                    time.sleep(delay)
                    if status == "filed":
                        (self.vault / q["target"] / q["file"]).write_bytes(content)
                    res = {"id": req.stem, "file": q["file"], "target": q["target"], "status": status, "reason": "",
                           "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
                    (self.queue / "done" / f"{req.stem}.result.json").write_text(json.dumps(res), encoding="utf-8")
                    req.rename(self.queue / "done" / f"{req.stem}.request.json")
                    return
                time.sleep(0.02)
        t = threading.Thread(target=work, daemon=True)
        t.start()
        return t

    def test_filed_and_verified(self):
        t = self.fake_pickup()
        code, out = self.run_main("Exercise_07.pdf", "DM/assignments", "--timeout-min", "0.1", "--verify-min", "0.05")
        t.join()
        self.assertEqual(code, 0, out)
        self.assertIn('"status":"filed"', out)
        self.assertIn("verified here", out)
        req = json.loads(next((self.queue / "done").glob("*.request.json")).read_text(encoding="utf-8"))
        self.assertEqual(req["file"], "Exercise_07.pdf")
        self.assertEqual(req["target"], "DM/assignments")
        self.assertFalse(req["approved_large"])
        self.assertRegex(req["requested_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_not_found_exit_1(self):
        t = self.fake_pickup(status="not-found")
        code, out = self.run_main("Exercise_08.pdf", "DM/assignments", "--timeout-min", "0.1")
        t.join()
        self.assertEqual(code, 1)
        self.assertIn("NEW tab", out)

    def test_no_answer_exit_4_and_status(self):
        code, out = self.run_main("Exercise_09.pdf", "DM/assignments", "--timeout-min", "0.002")
        self.assertEqual(code, 4)
        req_id = out.split("requested: ")[1].split()[0]
        self.assertTrue((self.queue / "pending" / f"{req_id}.json").exists())
        code, out = self.run_main("--status", req_id)
        self.assertEqual(code, 4)
        self.assertIn("pending", out)
        code, out = self.run_main("--pending")
        self.assertIn(req_id, out)

    def test_local_refusals_write_nothing(self):
        for args in (["x.pdf", "DM/not-official"], ["../x.pdf", "DM/assignments"]):
            code, out = self.run_main(*args)
            self.assertEqual(code, 1, out)
            self.assertIn("refused here", out)
        self.assertFalse(any((self.queue / "pending").glob("*.json")) if (self.queue / "pending").exists() else False)

    def test_no_wait_and_machine(self):
        code, out = self.run_main("Exercise_10.pdf", "DM/assignments", "--no-wait", "--machine", "LAPTOP-1")
        self.assertEqual(code, 0)
        req = json.loads(next((self.queue / "pending").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(req["machine"], "LAPTOP-1")
        self.assertFalse(list((self.queue / "pending").glob(".*.part")))

    def test_usage(self):
        code, _ = self.run_main()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
