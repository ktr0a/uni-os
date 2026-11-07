"""Unit tests of small helpers in tools/uni_os/heartbeat_rules.py (no fake vault needed).

Run from the repo root:  python -m unittest tests.test_heartbeat_rules -v
"""
import datetime as dt
import hashlib
import sys
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

# Two update notes whose slugs share their first 60 characters (the old cut made them one id).
LONG_A = "2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part A-update.md"
LONG_B = "2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part B-update.md"
# The same literal is checked in modules/inbox-sync/tests and modules/vm/tests/t-outcome-checks.sh.
LONG_A_ID = "2026-11-04-0300-la-exercise-sheet-7-corrections-and-f-2d4bf8"


class ParseWords(unittest.TestCase):
    def test_explicit_year_and_iso_dates_are_kept(self):
        ref = dt.date(2026, 12, 20)
        self.assertEqual(hr.parse_words("2027-01-05 09:15", ref), (dt.datetime(2027, 1, 5, 9, 15), True))
        self.assertEqual(hr.parse_words("5 Jan 2026", ref), (dt.datetime(2026, 1, 5), False))
        self.assertEqual(hr.parse_words("28 Dec 2025, 12:00", dt.date(2026, 1, 3)),
                         (dt.datetime(2025, 12, 28, 12, 0), True))

    def test_january_date_with_a_december_reference_is_next_year(self):
        self.assertEqual(hr.parse_words("Tue 5 Jan 23:59", dt.date(2026, 12, 20)),
                         (dt.datetime(2027, 1, 5, 23, 59), True))

    def test_december_date_with_a_january_reference_is_previous_year(self):
        self.assertEqual(hr.parse_words("Mon 28 Dec 23:59", dt.date(2027, 1, 3)),
                         (dt.datetime(2026, 12, 28, 23, 59), True))
        self.assertEqual(hr.parse_words("14 December", dt.date(2027, 1, 18)), (dt.datetime(2026, 12, 14), False))

    def test_dates_within_half_a_year_stay_in_the_reference_year(self):
        ref = dt.date(2026, 11, 10)
        self.assertEqual(hr.parse_words("Tue 10 Nov 23:59", ref)[0], dt.datetime(2026, 11, 10, 23, 59))
        self.assertEqual(hr.parse_words("3 Jun", ref)[0], dt.datetime(2026, 6, 3), "160 days back: same year")
        self.assertEqual(hr.parse_words("1 May", ref)[0], dt.datetime(2027, 5, 1), "193 days back: next year")
        ref = dt.date(2026, 3, 1)
        self.assertEqual(hr.parse_words("20 Aug", ref)[0], dt.datetime(2026, 8, 20), "172 days ahead: same year")
        self.assertEqual(hr.parse_words("20 Oct", ref)[0], dt.datetime(2025, 10, 20), "233 days ahead: previous year")

    def test_not_a_date(self):
        self.assertIsNone(hr.parse_words("", dt.date(2026, 11, 10)))
        self.assertIsNone(hr.parse_words("soon", dt.date(2026, 11, 10)))
        self.assertIsNone(hr.parse_words("31 Feb", dt.date(2026, 11, 10)))


class Slug(unittest.TestCase):
    def test_short_slugs_are_unchanged(self):
        self.assertEqual(hr.slug("2026-11-04_0300_AD Sheet 6 (v2)-update.md", 60),
                         "2026-11-04-0300-ad-sheet-6-v2-update-md")
        self.assertEqual(hr.slug('AD quiz "Week 9"'), "ad-quiz-week-9")
        self.assertEqual(hr.slug("***"), "x")
        exactly = "a" * 30 + "-" + "b" * 29
        self.assertEqual(len(exactly), 60)
        self.assertEqual(hr.slug(exactly, 60), exactly, "exactly n characters: not cut, no hash")

    def test_cut_slugs_end_in_a_hash_of_the_original_text(self):
        self.assertEqual(hr.slug(LONG_A, 60), LONG_A_ID)
        self.assertNotEqual(hr.slug(LONG_A, 60), hr.slug(LONG_B, 60), "long names sharing their start: two ids")
        one_more = "a" * 61
        want = "a" * 53 + "-" + hashlib.sha1(one_more.encode("utf-8")).hexdigest()[:6]
        self.assertEqual(hr.slug(one_more, 60), want)
        for s, n in ((LONG_A, 60), (LONG_B, 50), ("x" * 200, 50)):
            self.assertLessEqual(len(hr.slug(s, n)), n)

    def test_cut_drops_a_trailing_dash_before_the_hash(self):
        s = "a" * 42 + " " + "b" * 20  # the 43rd slug character, the last one kept for n=50, is "-"
        got = hr.slug(s)
        self.assertEqual(got, "a" * 42 + "-" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:6])
        self.assertNotIn("--", got)

    def test_the_hash_is_of_the_original_text_not_the_slug(self):
        # Same slug, different originals (case, punctuation): different ids once cut.
        a, b = "Long Name " * 8, "long-name-" * 8
        self.assertEqual(hr.slug(a, 10**6), hr.slug(b, 10**6))
        self.assertNotEqual(hr.slug(a), hr.slug(b))
        self.assertEqual(hr.slug(a), hr.slug(a), "stable across calls")


if __name__ == "__main__":
    unittest.main()
