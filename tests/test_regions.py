"""Generated regions: parsing and merging (``uni_os.regions``)."""

import unittest

import support  # noqa: F401  (puts tools/ on sys.path)
from uni_os import regions

FRESH = """# Title
intro (template)
<!-- uni-os:begin map -->
| a | b |
| new | row |
<!-- uni-os:end map -->
middle (template)
<!-- uni-os:begin jobs -->
job list v2
<!-- uni-os:end jobs -->
tail (template)
"""

CURRENT = """# Title
intro, edited by the student
<!-- uni-os:begin map -->
| a | b |
<!-- uni-os:end map -->
my own paragraph
<!-- uni-os:begin jobs -->
job list v1
<!-- uni-os:end jobs -->
tail (template)
- 2026-11-07: my change-log line
"""


class ParseTests(unittest.TestCase):
    def test_well_formed(self):
        parsed = regions.parse(FRESH)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.names, ["map", "jobs"])
        self.assertEqual(parsed.body(FRESH, "map"), "| a | b |\n| new | row |\n")
        self.assertEqual(parsed.body(FRESH, "jobs"), "job list v2\n")

    def test_empty_region_and_indented_markers(self):
        text = "x\n  <!-- uni-os:begin a -->  \n  <!--uni-os:end a-->\ny\n"
        parsed = regions.parse(text)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.body(text, "a"), "")

    def test_errors(self):
        cases = {
            "<!-- uni-os:begin a -->\n<!-- uni-os:begin b -->\n<!-- uni-os:end b -->\n<!-- uni-os:end a -->\n": "do not nest",
            "<!-- uni-os:begin a -->\nx\n<!-- uni-os:end a -->\n<!-- uni-os:begin a -->\n<!-- uni-os:end a -->\n": "appears twice",
            "<!-- uni-os:begin a -->\nx\n": "never closed",
            "x\n<!-- uni-os:end a -->\n": "without a matching begin",
            "<!-- uni-os:begin a -->\n<!-- uni-os:end b -->\n": "closes region 'a'",
            "<!-- uni-os:begin -->\n": "malformed marker",
            "<!-- uni-os:start a -->\n": "malformed marker",
            "<!-- uni-os:begin Map -->\n<!-- uni-os:end Map -->\n": "malformed marker",
        }
        for text, needle in cases.items():
            with self.subTest(text=text):
                errors = regions.parse(text).errors
                self.assertTrue(any(needle in e for e in errors), errors)

    def test_inline_mention_is_not_a_marker(self):
        text = "Regions sit between `<!-- uni-os:begin <name> -->` and `<!-- uni-os:end <name> -->` lines.\n"
        parsed = regions.parse(text)
        self.assertEqual((parsed.names, parsed.errors), ([], []))
        self.assertFalse(regions.has_regions(text))


class MergeTests(unittest.TestCase):
    def test_merge_replaces_only_bodies(self):
        result = regions.merge(CURRENT, FRESH)
        self.assertIsNone(result.problem)
        self.assertEqual(result.changed, ["map", "jobs"])
        merged = result.text
        self.assertIn("intro, edited by the student", merged)
        self.assertIn("my own paragraph", merged)
        self.assertIn("- 2026-11-07: my change-log line", merged)
        self.assertIn("| new | row |", merged)
        self.assertIn("job list v2", merged)
        self.assertNotIn("job list v1", merged)
        self.assertNotIn("middle (template)", merged)  # outside the regions the file is the student's
        # merging again changes nothing
        again = regions.merge(merged, FRESH)
        self.assertEqual((again.text, again.changed), (merged, []))

    def test_current_regions_report_no_change(self):
        result = regions.merge(FRESH, FRESH)
        self.assertEqual(result.changed, [])
        self.assertEqual(result.text, FRESH)

    def test_region_order_of_the_file_is_kept(self):
        swapped = "<!-- uni-os:begin jobs -->\nold\n<!-- uni-os:end jobs -->\nmine\n<!-- uni-os:begin map -->\nold\n<!-- uni-os:end map -->\n"
        merged = regions.merge(swapped, FRESH).text
        self.assertLess(merged.index("job list v2"), merged.index("| new | row |"))
        self.assertIn("mine", merged)

    def test_missing_or_extra_region_is_skipped(self):
        only_map = CURRENT.split("my own paragraph")[0]
        result = regions.merge(only_map, FRESH)
        self.assertIsNone(result.text)
        self.assertIn("not in the file: jobs", result.problem)
        extra = CURRENT + "<!-- uni-os:begin old -->\nx\n<!-- uni-os:end old -->\n"
        self.assertIn("no longer generated: old", regions.merge(extra, FRESH).problem)

    def test_malformed_markers_are_never_guessed(self):
        broken = CURRENT.replace("<!-- uni-os:end map -->", "<!-- uni-os:end mapp -->")
        result = regions.merge(broken, FRESH)
        self.assertIsNone(result.text)
        self.assertIn("missing or malformed", result.problem)
        deleted = CURRENT.replace("<!-- uni-os:begin jobs -->\n", "")
        self.assertIn("missing or malformed", regions.merge(deleted, FRESH).problem)

    def test_template_without_regions(self):
        self.assertIn("no generated regions", regions.merge(CURRENT, "plain\n").problem)

    def test_bad_template_markers(self):
        self.assertIn("template", regions.merge(CURRENT, "<!-- uni-os:begin a -->\n").problem)

    def test_crlf_files_keep_crlf(self):
        current = CURRENT.replace("\n", "\r\n")
        merged = regions.merge(current, FRESH).text
        self.assertNotIn("\n", merged.replace("\r\n", ""))
        self.assertIn("| new | row |\r\n", merged)


if __name__ == "__main__":
    unittest.main()
