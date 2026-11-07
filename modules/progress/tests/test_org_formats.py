"""Tests for modules/progress/scripts/org_formats.py (run: python -m unittest discover -s modules/progress/tests)."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import org_formats as f  # noqa: E402

WEEK = """---
type: week
week: 7
start: 2026-11-02
end: 2026-11-08
status: current
audience: me
updated: 2026-11-06
tags: [uni/week]
---
# Week 7: Mon 2 Nov to Sun 8 Nov 2026

Plan: [week-07-plan.md](../../semester/plans/week-07-plan.md)

## Due this week
| Item | Official deadline | Personal target | Bonus | Status |
|---|---|---|---|---|
| DM graded sheet 4 (out Mon 2 Nov) | Mon 9 Nov 12:00 | Sun 8 Nov | 2 pts (solo) | done 1.5 / 2 (Fri 6 Nov ~16:10) |
| AD exercise sheet 7 (out Thu 29 Oct) | Thu 5 Nov 23:59 | Sun 1 Nov | 10 pts | **submitted** (LMS, checked Wed 4 Nov) |
| AD exercise sheet 8 (out Thu 5 Nov) | tutorial Wed 11 Nov 14:15 | Sun 8 Nov | none | not released yet |
| LA exercise sheet 7 | Mon 9 Nov 09:00 | | feedback only | not submitted |
| PROG exercise 7 | Tue 10 Nov 18:00 | | none | tasks 1 and 2 done, 3 open |
| PROG lab test | Wed 4 Nov 10:15-12:00 | | 5 pts | result not reported yet |

## Results this week
- Fri 6 Nov ~16:10: DM graded sheet 4 = **1.5 / 2** (LMS feedback).

## Notes
- Created Sun 1 Nov 10:00 by the week-page job.

## End-of-week check-in
- Done: _To fill_
- Focused hours: _To fill_
"""


class StatusVocabulary(unittest.TestCase):
    def test_done_words_at_start(self):
        for cell in ["done", "Done 4/4", "**done 4 / 4** (Fri)", "submitted (LMS)", "closed", "handed in",
                     "uploaded as is", "dropped (no bonus)", "skipped by choice", "✓ Tue", "3.5 / 4", "2/2 (screenshot)",
                     "done (Tue 3 Nov 10:12, tapped). Before: open"]:
            self.assertTrue(f.is_done(cell), cell)

    def test_not_done(self):
        for cell in ["open", "", "in progress (2 of 4)", "tasks 1 and 2 done, 3 open", "not done",
                     "not submitted", "not released yet", "open: 2/3 done", "result pending"]:
            self.assertFalse(f.is_done(cell), cell)

    def test_pending_wins_and_whole_words(self):
        # the cockpit's order: a pending word anywhere beats a done word at the start
        self.assertEqual(f.status_state("submitted (score pending)"), "pending")
        self.assertEqual(f.status_state("done; result not reported"), "pending")
        # a Done-tap mark is done even when the old value behind "Before:" says "not reported"
        self.assertEqual(f.status_state("done (Tue 3 Nov 10:12, tapped). Before: not reported"), "done")
        # done words count as whole words only
        self.assertFalse(f.is_done("doneness unclear"))
        self.assertFalse(f.is_done("closedown of the LMS"))
        self.assertTrue(f.is_done("Done: all four tasks"))

    def test_states(self):
        self.assertEqual(f.status_state("not released yet"), "not-released")
        self.assertEqual(f.status_state("took place; result not reported"), "pending")
        self.assertEqual(f.status_state("not recorded"), "pending")
        self.assertEqual(f.status_state("open"), "open")

    def test_soft_and_no_bonus(self):
        self.assertTrue(f.is_soft("tutorial Tue 10 Nov 16:15"))
        self.assertTrue(f.is_soft("Wed 4 Nov 10:15 (tentative)"))
        self.assertFalse(f.is_soft("Tue 3 Nov 23:59"))
        for b in ["none", "no", "feedback only", ""]:
            self.assertTrue(f.no_bonus(b), b)
        self.assertFalse(f.no_bonus("4 pts"))


class WeekPage(unittest.TestCase):
    def test_due_rows(self):
        rows = f.due_rows(WEEK)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["state"] for r in rows], ["done", "done", "not-released", "open", "open", "pending"])
        self.assertEqual(rows[1]["target"], "Sun 1 Nov")
        self.assertTrue(rows[2]["soft"])
        self.assertTrue(rows[3]["no_bonus"])

    def test_checkin_marker(self):
        self.assertFalse(f.checkin_filled(WEEK))
        filled = WEEK.replace("- Done: _To fill_", "- **Done:** sheet 7").replace("- Focused hours: _To fill_", "- **Focused hours:** ~19 h")
        self.assertTrue(f.checkin_filled(filled))

    def test_valid_page(self):
        self.assertEqual(f.check_week_page(WEEK, "week-07.md"), [])

    def test_broken_page(self):
        bad = WEEK.replace("status: current", "status: live").replace("## Notes", "## Remarks")
        problems = f.check_week_page(bad, "week-08.md")
        self.assertTrue(any("status" in p for p in problems))
        self.assertTrue(any("Notes" in p for p in problems))
        self.assertTrue(any("disagree" in p for p in problems))

    def test_original_column_name_still_found(self):
        old = WEEK.replace("Personal target", "Sunday target")
        self.assertEqual(f.due_rows(old)[1]["target"], "Sun 1 Nov")

    def test_day_time(self):
        p = f.parse_day_time("Wed 4 Nov 10:15-12:00 (lab test)", 2026)
        self.assertEqual(p["date"], dt.date(2026, 11, 4))
        self.assertEqual((p["start"], p["end"]), (dt.time(10, 15), dt.time(12, 0)))
        self.assertTrue(p["weekday_ok"])
        self.assertEqual(f.year_for("Jan", dt.date(2026, 9, 14)), 2027)


class WhichWeek(unittest.TestCase):
    W0 = dt.date(2026, 9, 14)

    def test_week_page_target(self):
        self.assertEqual(f.week_page_target(dt.date(2026, 11, 1)), dt.date(2026, 11, 2))   # Sun -> next Mon
        self.assertEqual(f.week_page_target(dt.date(2026, 10, 30)), dt.date(2026, 11, 2))  # Fri -> next Mon
        self.assertEqual(f.week_page_target(dt.date(2026, 11, 3)), dt.date(2026, 11, 2))   # late run Tue
        self.assertEqual(f.term_week(dt.date(2026, 11, 2), self.W0), 7)

    def test_checkin_target(self):
        self.assertEqual(f.checkin_target(dt.date(2026, 11, 7)), dt.date(2026, 11, 2))   # Sat: this week
        self.assertEqual(f.checkin_target(dt.date(2026, 11, 8)), dt.date(2026, 11, 2))   # Sun: this week
        self.assertEqual(f.checkin_target(dt.date(2026, 11, 9)), dt.date(2026, 11, 2))   # Mon after: last week
        self.assertEqual(f.checkin_target(dt.date(2026, 11, 6)), dt.date(2026, 11, 2))   # Fri: this week


class CurrentStatus(unittest.TestCase):
    TEXT = """---
type: status
---
# Progress dashboard

**Snapshot: Sun 1 Nov 2026, evening (end of term week 6).** History in the log.

## Bonus standing
| Course | Banked | Bonus now | What's still needed | Full bonus at |
|---|---|---|---|---|

## Exercises: done vs. to do (as of Sun 1 Nov)
### AD
- sheet 6 submitted

## Self-rated understanding
PROG ~85 % · AD 70-75 % · **DM ~55 % · LA ~60 %** (user, Sun 1 Nov). Before: DM 65 %.

## Next 10 days
| When | What |
|---|---|
| Mon 2 Nov 12:00 | DM graded sheet 4 out · LA quiz 7 due Mon 9 Nov 09:00 |
"""

    def test_parse(self):
        p = f.parse_status(self.TEXT)
        self.assertTrue(p["snapshot"].startswith("Sun 1 Nov 2026"))
        self.assertEqual(p["ratings"], {"PROG": "85", "AD": "70-75", "DM": "55", "LA": "60"})
        self.assertEqual(p["next"][0]["when"], "Mon 2 Nov 12:00")
        self.assertEqual(f.check_status(self.TEXT), [])


if __name__ == "__main__":
    unittest.main()
