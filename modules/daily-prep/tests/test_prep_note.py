"""Tests for modules/daily-prep/scripts/prep_note.py (run: python -m unittest discover -s modules/daily-prep/tests)."""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prep_note as p  # noqa: E402

NOTE = """---
type: prep
audience: me
date: 2026-11-10
generated: 2026-11-09T17:31+01:00
run: "17:30"
status: ready-with-gaps
tags: [uni/prep]
---
# Prep for Tue 10 Nov 2026 (week 8)

Written by the 17:30 run. Two study blocks and one lecture.

> [!la] 08:00-09:45 LA_ hand-in first, then core tasks
> - Recap: [la-vector-spaces-study-page](../../LA/notes/la-vector-spaces-study-page.md)
> - Hand-in task first: `LA/assignments/assignment08.pdf`
>   (feedback only)

> [!prog] 10:15-12:00 L: PROG
> - Script chapter 6: `PROG/script and slides/lecture15.pdf`

> [!ad] 13:30-16:00 AD_ Sheet 8 (deep)
> - Sheet: `AD/assignments/sheet08.pdf` (bonus tasks first; coaching only)
> - Page: [dp](<../../A&D notes/dp page.md>) and [web](https://example.org/x.pdf)

## Gaps
- AD sheet 8 not in the vault yet (released today 18:00); fallback: the LMS
"""


class Naming(unittest.TestCase):
    def test_revision(self):
        self.assertEqual(p.revision_of("prep-2026-11-10.md"), ("2026-11-10", 1))
        self.assertEqual(p.revision_of("prep-2026-11-10-r3.md"), ("2026-11-10", 3))
        self.assertIsNone(p.revision_of("README.md"))
        self.assertIsNone(p.revision_of("prep-2026-11-10 (1).md"))

    def test_newest(self):
        with tempfile.TemporaryDirectory() as d:
            prep = Path(d)
            (prep / "prep-2026-11-10.md").write_text(NOTE, encoding="utf-8")
            (prep / "prep-2026-11-10-r2.md").write_text(NOTE.replace("17:31", "19:32"), encoding="utf-8")
            (prep / "prep-2026-11-10-r10.md").write_text(NOTE, encoding="utf-8")
            (prep / "prep-2026-11-11.md").write_text(NOTE, encoding="utf-8")
            self.assertEqual(p.newest(prep, "2026-11-10").name, "prep-2026-11-10-r10.md")


class Parse(unittest.TestCase):
    def test_callouts_items_gaps(self):
        r = p.parse_prep(NOTE)
        self.assertEqual([c["course"] for c in r["callouts"]], ["la", "prog", "ad"])
        self.assertEqual(r["callouts"][0]["start"], "08:00")
        self.assertEqual(r["callouts"][1]["title"], "L: PROG")
        self.assertEqual(len(r["callouts"][0]["items"]), 2)
        self.assertIn("(feedback only)", r["callouts"][0]["items"][1])
        self.assertEqual(len(r["gaps"]), 1)
        self.assertTrue(r["intro"].startswith("Written by the 17:30 run"))

    def test_none_gap(self):
        r = p.parse_prep(NOTE.replace("- AD sheet 8 not in the vault yet (released today 18:00); fallback: the LMS", "- none"))
        self.assertEqual(r["gaps"], [])

    def test_valid(self):
        self.assertEqual(p.validate(NOTE, "prep-2026-11-10.md"), [])

    def test_invalid(self):
        bad = (NOTE.replace("status: ready-with-gaps", "status: ready")
               .replace("13:30-16:00", "07:30-07:00")
               .replace('run: "17:30"', "run: evening"))
        problems = p.validate(bad, "prep-2026-11-11.md")
        joined = "\n".join(problems)
        for word in ["status ready but", "ends before", "time order", "run 'evening'", "differs from the file name"]:
            self.assertIn(word, joined)

    def test_gaps_must_be_last(self):
        bad = NOTE + "\n## Extra\n- x\n"
        self.assertTrue(any("last section" in x for x in p.validate(bad, "prep-2026-11-10.md")))


class Paths(unittest.TestCase):
    def test_paths(self):
        paths = p.paths_in(NOTE)
        self.assertIn("LA/notes/la-vector-spaces-study-page.md", paths)
        self.assertIn("LA/assignments/assignment08.pdf", paths)
        self.assertIn("PROG/script and slides/lecture15.pdf", paths)
        self.assertIn("A&D notes/dp page.md", paths)
        self.assertFalse(any("example.org" in x for x in paths))

    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            v = Path(d)
            (v / "LA" / "assignments").mkdir(parents=True)
            (v / "LA" / "assignments" / "assignment08.pdf").write_bytes(b"%PDF")
            missing = p.missing_paths(v, NOTE)
            self.assertNotIn("LA/assignments/assignment08.pdf", missing)
            self.assertIn("AD/assignments/sheet08.pdf", missing)

    def test_material_header(self):
        h = p.material_header("prep-2026-11-10-r2.md", dt.datetime(2026, 11, 9, 17, 31))
        self.assertEqual(h, "MATERIAL (daily prep, Mon 9 Nov 17:31; all of it in Obsidian: semester/prep/prep-2026-11-10-r2)")


if __name__ == "__main__":
    unittest.main()
