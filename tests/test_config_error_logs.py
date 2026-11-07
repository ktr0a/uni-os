"""Per-stream error logs (``courses[].error_logs``) and the session titles built from them.

The roles page ``_agent/roles/README.md`` and the exercise-help brief title one Exercise-help session per
course and error-log stream. Both templates tell the single-stream case apart by the derived entry title
"Error log", so this test pins that title and renders the real session-titles region (read-only).
"""

import re
import unittest

import support  # noqa: F401  (puts tools/ on sys.path)
from uni_os import config as c
from uni_os import template as t

ROLES_PAGE = support.REPO / "modules" / "roles" / "vault" / "_agent" / "roles" / "README.md"
REGION = re.compile(r"<!-- uni-os:begin session-titles -->\n(.*?)<!-- uni-os:end session-titles -->", re.S)


def course(cid, short, streams):
    entry = {"id": cid, "name": cid.upper(), "short": short, "folder": short, "slug": cid, "error_log_streams": streams}
    return c.derive_course(entry, {})


class ErrorLogEntriesTest(unittest.TestCase):
    def test_one_stream_is_the_plain_error_log(self):
        self.assertEqual(
            c.error_log_entries("ad", "AD", ["main"]),
            [{"stream": "main", "file": "ad-error-log.md", "path": "AD/ad-error-log.md", "title": "Error log"}],
        )

    def test_several_streams_get_one_file_and_title_each(self):
        entries = c.error_log_entries("prog", "PROG", ["theory", "programming"])
        self.assertEqual([e["file"] for e in entries], ["prog-error-log-theory.md", "prog-error-log-programming.md"])
        self.assertEqual([e["title"] for e in entries], ["Error log (theory)", "Error log (programming)"])


class SessionTitlesTest(unittest.TestCase):
    def render_region(self, courses, enabled):
        region = REGION.search(ROLES_PAGE.read_text(encoding="utf-8"))
        self.assertIsNotNone(region, "session-titles region not found in the roles page")
        ctx = t.build_context({"courses": courses}, enabled=enabled, generated={"date": "2026-11-07", "version": "test"})
        return t.render(region.group(1), ctx, filename=str(ROLES_PAGE))

    def test_one_exercise_help_session_per_stream(self):
        out = self.render_region(
            [course("ad", "AD", ["main"]), course("prog", "PROG", ["theory", "programming"])],
            ["roles", "exercise-help", "lecture-rundowns"],
        )
        lines = out.strip().split("\n")
        self.assertEqual(lines[0], "| Course | Folder | Lecture rundown | Exercise help |")
        self.assertEqual(lines[2], "| AD | `AD/` | AD · Lecture rundown | AD · Exercise help |")
        self.assertEqual(
            lines[3],
            "| PROG | `PROG/` | PROG · Lecture rundown | PROG · Exercise help (theory)<br>PROG · Exercise help (programming) |",
        )
        self.assertEqual(len(lines), 4)

    def test_no_exercise_help_column_without_the_module(self):
        out = self.render_region([course("prog", "PROG", ["theory", "programming"])], ["roles"])
        self.assertNotIn("Exercise help", out)
        self.assertIn("| PROG | `PROG/` |\n", out)


if __name__ == "__main__":
    unittest.main()
