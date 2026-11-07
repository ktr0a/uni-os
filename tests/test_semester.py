"""Tests for term-week arithmetic, date formats and `uni-os week` / `uni-os new-week`."""

import datetime as dt
import json
import os
import unittest

import support
from uni_os import frontmatter, semester
from uni_os.errors import ConfigError

CFG = {
    "term": {
        "timezone": "Europe/Zurich",
        "week0_monday": dt.date(2026, 9, 14),
        "last_lecture_day": dt.date(2026, 12, 18),
        "lecture_free_from": dt.date(2026, 12, 19),
        "exam_session_start": dt.date(2027, 1, 25),
        "exam_session_end": dt.date(2027, 2, 19),
        "holidays": [{"name": "Reading day", "from": dt.date(2026, 11, 20), "to": dt.date(2026, 11, 20)}],
    }
}


class WeekMathTests(unittest.TestCase):
    def test_week0_and_week_n_start(self):
        self.assertEqual(semester.week_of(dt.date(2026, 9, 14), CFG), 0)
        self.assertEqual(semester.week_of(dt.date(2026, 9, 20), CFG), 0)  # Sunday of week 0
        self.assertEqual(semester.week_of(dt.date(2026, 9, 21), CFG), 1)
        for n in (0, 1, 7, 13, 20):
            monday = dt.date(2026, 9, 14) + dt.timedelta(days=7 * n)
            self.assertEqual(semester.week_of(monday, CFG), n)
            self.assertEqual(semester.week_of(monday - dt.timedelta(days=1), CFG), n - 1)

    def test_before_term_is_negative(self):
        self.assertEqual(semester.week_of(dt.date(2026, 9, 13), CFG), -1)
        self.assertEqual(semester.week_of(dt.date(2026, 9, 1), CFG), -2)

    def test_accepts_strings(self):
        self.assertEqual(semester.week_of("2026-11-07", CFG), 7)
        cfg = {"term": {"week0_monday": "2026-09-14"}}
        self.assertEqual(semester.week_of("2026-11-09", cfg), 8)

    def test_bounds_and_info(self):
        monday, sunday = semester.week_bounds(8, CFG)
        self.assertEqual((monday, sunday), (dt.date(2026, 11, 9), dt.date(2026, 11, 15)))
        info = semester.week_info(8, CFG)
        self.assertEqual(info["nn"], "08")
        self.assertEqual(info["label"], "Mon 9 Nov to Sun 15 Nov 2026")
        self.assertEqual(info["status"], "current")
        self.assertEqual((info["previous_nn"], info["next_nn"]), ("07", "09"))
        self.assertEqual(semester.week_info(0, CFG)["label"], "Mon 14 Sep to Sun 20 Sep 2026")

    def test_label_across_new_year(self):
        cfg = {"term": {"week0_monday": dt.date(2026, 12, 28)}}
        self.assertEqual(semester.week_info(0, cfg)["label"], "Mon 28 Dec 2026 to Sun 3 Jan 2027")

    def test_fmt_day(self):
        self.assertEqual(semester.fmt_day(dt.date(2026, 10, 26)), "Mon 26 Oct 2026")
        self.assertEqual(semester.fmt_day(dt.date(2026, 11, 3), year=False), "Tue 3 Nov")

    def test_phase(self):
        self.assertEqual(semester.phase("2026-09-01", CFG), "before-term")
        self.assertEqual(semester.phase("2026-10-01", CFG), "lectures")
        self.assertEqual(semester.phase("2026-11-20", CFG), "holiday: Reading day")
        self.assertEqual(semester.phase("2026-12-24", CFG), "lecture-free")
        self.assertEqual(semester.phase("2027-01-25", CFG), "exam-session")
        self.assertEqual(semester.phase("2027-03-01", CFG), "after-exams")

    def test_missing_week0(self):
        with self.assertRaises(ConfigError):
            semester.week_of("2026-11-07", {"term": {}})

    def test_today_override(self):
        old = os.environ.get("UNI_OS_TODAY")
        os.environ["UNI_OS_TODAY"] = "2026-12-01"
        try:
            self.assertEqual(semester.today(CFG), dt.date(2026, 12, 1))
        finally:
            if old is None:
                del os.environ["UNI_OS_TODAY"]
            else:
                os.environ["UNI_OS_TODAY"] = old

    def test_moment_format(self):
        when = dt.datetime(2026, 11, 3, 9, 5)
        self.assertEqual(semester.moment_format(when, "YYYY-MM-DD HH:mm"), "2026-11-03 09:05")
        self.assertEqual(semester.moment_format(when, "ddd D MMM"), "Tue 3 Nov")


class WeekCommandTests(support.TempDirTestCase):
    def test_week_command_with_config_only(self):
        _, out, _ = self.cli("week", "--config", str(self.config), "--modules-dir", str(support.FIXTURE_MODULES))
        self.assertEqual(out.strip(), "Week 7 (Mon 2 Nov to Sun 8 Nov 2026), lectures")
        _, out, _ = self.cli("week", "--number", "--date", "2026-12-24", "--config", str(self.config), "--modules-dir", str(support.FIXTURE_MODULES))
        self.assertEqual(out.strip(), "14")
        _, out, _ = self.cli("week", "--json", "--date", "2026-11-20", "--config", str(self.config), "--modules-dir", str(support.FIXTURE_MODULES))
        data = json.loads(out)
        self.assertEqual(data["phase"], "holiday: Reading day")
        self.assertEqual(data["nn"], "09")


class NewWeekTests(support.TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_creates_next_week_from_template(self):
        _, out, _ = self.in_vault("new-week")  # today = Sat 7 Nov 2026 (week 7) -> week 8
        self.assertIn("created progress/weeks/week-08.md", out)
        page = self.read("progress/weeks/week-08.md")
        fm = frontmatter.parse(page)
        self.assertEqual(fm["type"], "week")
        self.assertEqual(fm["week"], 8)
        self.assertEqual(fm["start"], "2026-11-09")
        self.assertEqual(fm["end"], "2026-11-15")
        self.assertEqual(fm["status"], "current")
        self.assertEqual(fm["updated"], "2026-11-07")
        self.assertIn("# Week 08: Mon 9 Nov to Sun 15 Nov 2026", page)
        self.assertIn("[week-08-plan.md](../../semester/plans/week-08-plan.md)", page)
        self.assertIn("| PROG sheet | | | | not released yet |", page)
        for heading in ("## Due this week", "## Results this week", "## Notes", "## End-of-week check-in"):
            self.assertIn(heading, page)
        self.assertNotIn("{{", page)

    def test_never_overwrites(self):
        self.in_vault("new-week")
        self.write("progress/weeks/week-08.md", "mine\n")
        _, out, _ = self.in_vault("new-week")
        self.assertIn("already exists", out)
        self.assertEqual(self.read("progress/weeks/week-08.md"), "mine\n")

    def test_current_week_and_explicit_week(self):
        self.in_vault("new-week", "--current")
        self.assertTrue((self.vault / "progress" / "weeks" / "week-07.md").is_file())
        self.in_vault("new-week", "--week", "12", "--status", "upcoming")
        self.assertEqual(frontmatter.parse(self.read("progress/weeks/week-12.md"))["status"], "upcoming")
        self.in_vault("new-week", "--date", "2026-09-14", "--current")
        self.assertTrue((self.vault / "progress" / "weeks" / "week-00.md").is_file())

    def test_close_previous(self):
        self.in_vault("new-week", "--current")
        self.in_vault("new-week", "--close-previous")
        self.assertEqual(frontmatter.parse(self.read("progress/weeks/week-07.md"))["status"], "done")
        self.assertEqual(frontmatter.parse(self.read("progress/weeks/week-08.md"))["status"], "current")

    def test_dry_run_and_negative_week(self):
        _, out, _ = self.in_vault("new-week", "--dry-run")
        self.assertIn("week: 8", out)
        self.assertFalse((self.vault / "progress" / "weeks" / "week-08.md").exists())
        _, _, err = self.in_vault("new-week", "--date", "2026-09-01", "--current", expect=1)
        self.assertIn("before week 0", err)

    def test_missing_template(self):
        (self.vault / "_templates" / "week-page.md").unlink()
        _, _, err = self.in_vault("new-week", expect=1)
        self.assertIn("progress module", err)


if __name__ == "__main__":
    unittest.main()
