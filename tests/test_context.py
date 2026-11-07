"""Tests for the session's template context (``uni_os.context.Session.context``)."""

import datetime as dt

import support
from uni_os import template
from uni_os.context import open_session


class ContextTests(support.TempDirTestCase):
    def session(self):
        return open_session(config=self.config, modules_dir=support.FIXTURE_MODULES)

    def test_generated_date_and_date_long(self):
        gen = self.session().context(date=dt.date(2026, 11, 7))["generated"]
        self.assertEqual(gen["date"], "2026-11-07")
        self.assertEqual(gen["date_long"], "Sat 7 Nov 2026")
        gen = self.session().context(date=dt.date(2027, 2, 1))["generated"]
        self.assertEqual(gen["date_long"], "Mon 1 Feb 2027")

    def test_date_long_defaults_to_the_generation_date(self):
        # $UNI_OS_TODAY is 2026-11-07 in every TempDirTestCase
        self.assertEqual(self.session().context()["generated"]["date_long"], "Sat 7 Nov 2026")

    def test_date_long_renders_in_templates(self):
        ctx = self.session().context(date=dt.date(2026, 11, 7))
        self.assertEqual(template.render("- {{generated.date_long}}: set up", ctx), "- Sat 7 Nov 2026: set up")

    def test_term_weeks_render_as_a_table(self):
        """The fixture's last lecture day (Fri 18 Dec 2026) lies in week 13."""
        ctx = self.session().context(date=dt.date(2026, 11, 7))
        text = template.render("{{#each term.weeks}}| {{item.number}} | {{item.start}} |\n{{/each}}", ctx)
        rows = text.splitlines()
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[0], "| 0 | Mon 14 Sep 2026 |")
        self.assertEqual(rows[-1], "| 13 | Mon 14 Dec 2026 |")
        self.assertEqual(template.render("{{term.weeks.7.nn}} {{term.weeks.7.start_iso}}", ctx), "07 2026-11-02")

    def test_term_weeks_follow_the_config(self):
        self.config.write_text(self.config.read_text(encoding="utf-8").replace("last_lecture_day = 2026-12-18\n", ""), encoding="utf-8")
        weeks = self.session().context()["term"]["weeks"]
        self.assertEqual(len(weeks), 14, "no last lecture day: weeks 0 to 13")
        self.config.write_text(self.config.read_text(encoding="utf-8").replace("week0_monday = 2026-09-14", "week0_monday = 2026-09-14\nlast_lecture_day = 2027-01-15"), encoding="utf-8")
        weeks = self.session().context()["term"]["weeks"]
        self.assertEqual(weeks[-1]["number"], 17)
        self.assertEqual(weeks[-1]["start"], "Mon 11 Jan 2027")


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
