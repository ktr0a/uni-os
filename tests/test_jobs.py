"""Tests for job.conf parsing (bash-compatible quoting) and job listing/validation."""

import unittest

import support
from uni_os import jobs


class ParseConfTests(unittest.TestCase):
    def test_quoting_rules(self):
        text = (
            '# comment\n'
            'TITLE="Daily study prep"   # trailing comment\n'
            "KIND=agent\n"
            "PRECHECK='! ls \"$HOME/Uni/inbox\" >/dev/null 2>&1 || compgen -G \"$HOME/Uni/inbox/*-update.md\"'\n"
            'COMMAND="echo \\"hi\\" \\$HOME"\n'
            'MIXED="a"\'b\'c\n'
            'EMPTY=""\n'
            'HASH="a # not a comment"\n'
            'NOTIFY_GATE=$(jq -r ".gate_id // \\"ask\\"" pending.json)\n'
            "export HEARTBEAT_ACT_MODE=freeze-safe\n"
            "export ALREADY\n"
            "if true; then echo nope; fi\n"
        )
        values, exported = jobs.parse_conf_text(text)
        self.assertEqual(values["TITLE"], "Daily study prep")
        self.assertEqual(values["KIND"], "agent")
        self.assertEqual(values["PRECHECK"], '! ls "$HOME/Uni/inbox" >/dev/null 2>&1 || compgen -G "$HOME/Uni/inbox/*-update.md"')
        self.assertEqual(values["COMMAND"], 'echo "hi" $HOME')
        self.assertEqual(values["MIXED"], "abc")
        self.assertEqual(values["EMPTY"], "")
        self.assertEqual(values["HASH"], "a # not a comment")
        self.assertTrue(values["NOTIFY_GATE"].startswith("$(jq -r"))
        self.assertEqual(values["HEARTBEAT_ACT_MODE"], "freeze-safe")
        self.assertEqual(exported, {"HEARTBEAT_ACT_MODE", "ALREADY"})
        self.assertNotIn("if", values)

    def test_multiline_quoted_value_and_crlf(self):
        values, _ = jobs.parse_conf_text('SCHEDULE="*-*-* 07:15:00;\r\n*-*-* 13:15:00"\r\nKIND=command\r\n')
        self.assertEqual(values["SCHEDULE"], "*-*-* 07:15:00;\n*-*-* 13:15:00")
        self.assertEqual(values["KIND"], "command")

    def test_unterminated_quote(self):
        with self.assertRaises(jobs.ConfParseError):
            jobs.parse_conf_text('TITLE="oops\n')

    def test_parse_conf_accepts_path_or_text(self):
        path = support.FIXTURE_MODULES / "winaddon" / "jobs" / "win-watch" / "job.conf"
        self.assertEqual(jobs.parse_conf(path)["KIND"], "command")
        self.assertEqual(jobs.parse_conf(str(path))["COMMAND"], "echo watch")
        self.assertEqual(jobs.parse_conf('TITLE="x"')["TITLE"], "x")
        values, exported = jobs.parse_conf("export A=1\n", with_exports=True)
        self.assertEqual((values, exported), ({"A": "1"}, {"A"}))

    def test_split_list(self):
        self.assertEqual(jobs.split_list("07:15, 13:15,18:15"), ["07:15", "13:15", "18:15"])
        self.assertEqual(jobs.split_list(""), [])


class JobListTests(support.TempDirTestCase):
    def test_list_and_validate_installed_jobs(self):
        self.init("--modules", "winaddon")
        found = jobs.list_jobs(self.vault)
        self.assertEqual([j.id for j in found], ["week-page", "win-watch"])
        week = found[0]
        self.assertEqual(week.title, "Week page")
        self.assertEqual(week.slots, ["10:00"])
        self.assertEqual(week.days, ["Sun"])
        self.assertEqual(week.module, "progress")
        self.assertEqual(week.conf["EFFORT"], "high")  # default filled in
        self.assertEqual(week.conf["TIMEOUT_MIN"], "30")
        self.assertIsNotNone(week.prompt_path)
        self.assertEqual([p for p in jobs.validate_job(week) if p[0] != "info"], [])
        watch = found[1]
        self.assertEqual(watch.slots, ["07:00", "19:00"])
        self.assertEqual(watch.to_dict()["default_mode"], "always")

    def test_validation_catches_bad_values(self):
        folder = self.tmp / "jobs" / "bad"
        folder.mkdir(parents=True)
        (folder / "job.conf").write_text('KIND="robot"\nSLOTS="7:30, 25:00"\nDAYS="Mon,Funday"\nTIMEOUT_MIN="soon"\nDATES="2026-11-09..2026-11-29;nov"\nMYSTERY=1\n', encoding="utf-8")
        problems = [m for level, m in jobs.validate_job(jobs.load_job(folder)) if level == "error"]
        text = "\n".join(problems)
        for frag in ("KIND", "'7:30'", "'25:00'", "'Funday'", "TIMEOUT_MIN", "'nov'"):
            self.assertIn(frag, text)
        warnings = [m for level, m in jobs.validate_job(jobs.load_job(folder)) if level == "warning"]
        self.assertTrue(any("MYSTERY" in w for w in warnings))

    def test_every_min_and_day_ranges(self):
        """EVERY_MIN (polling jobs) and DAYS ranges are read like the host runners read them."""
        folder = self.tmp / "jobs" / "poll"
        folder.mkdir(parents=True)
        (folder / "job.conf").write_text('KIND="command"\nCOMMAND="echo poll"\nSLOTS=""\nEVERY_MIN="10"\nDAYS="Mon..Wed,Fri"\n', encoding="utf-8")
        job = jobs.load_job(folder)
        self.assertEqual(job.every_min, "10")
        self.assertEqual(job.days, ["Mon", "Tue", "Wed", "Fri"])
        self.assertEqual(job.to_dict()["every_min"], "10")
        problems = jobs.validate_job(job)  # no "unknown key", no "only started by other tools"
        self.assertEqual([p for p in problems if p[0] in ("error", "warning")], [])  # both runners read ranges
        (folder / "job.conf").write_text('KIND="command"\nCOMMAND="echo poll"\nEVERY_MIN="10"\nDAYS="Mon-Wed,Fri"\n', encoding="utf-8")
        dashed = jobs.load_job(folder)
        self.assertEqual(dashed.days, ["Mon", "Tue", "Wed", "Fri"])
        self.assertEqual([p for p in jobs.validate_job(dashed) if p[0] in ("error", "warning")], [])
        self.assertEqual(jobs.expand_days(""), list(jobs.DAYS))  # empty DAYS = every day
        self.assertEqual(jobs.expand_days("Sat-Mon"), ["Mon", "Sat", "Sun"])
        (folder / "job.conf").write_text('KIND="command"\nCOMMAND="x"\nEVERY_MIN="90"\nDAYS="Mon..Funday"\n', encoding="utf-8")
        errors = [m for level, m in jobs.validate_job(jobs.load_job(folder)) if level == "error"]
        self.assertTrue(any("EVERY_MIN" in m for m in errors))
        self.assertTrue(any("Mon..Funday" in m for m in errors))
        (folder / "job.conf").write_text('KIND="command"\nCOMMAND="x"\nEVERY_MIN="120"\n', encoding="utf-8")
        self.assertEqual([p for p in jobs.validate_job(jobs.load_job(folder)) if p[0] == "error"], [])

    def test_agent_job_needs_prompt(self):
        folder = self.tmp / "jobs" / "noprompt"
        folder.mkdir(parents=True)
        (folder / "job.conf").write_text('KIND="agent"\nSLOTS="08:00"\n', encoding="utf-8")
        problems = [m for level, m in jobs.validate_job(jobs.load_job(folder)) if level == "error"]
        self.assertTrue(any("prompt.md" in m for m in problems))

    def test_disabled_jobs_are_hidden(self):
        self.init()
        (self.vault / "_agent" / "jobs" / "week-page" / jobs.DISABLED_MARKER).write_text("off\n", encoding="utf-8")
        self.assertEqual(jobs.list_jobs(self.vault), [])
        self.assertTrue(jobs.list_jobs(self.vault, include_disabled=True)[0].disabled)

    def test_jobs_command(self):
        self.init("--modules", "winaddon")
        _, out, _ = self.in_vault("jobs")
        self.assertIn("week-page", out)
        self.assertIn("07:00, 19:00", out)
        import json

        _, out, _ = self.in_vault("jobs", "--json")
        rows = json.loads(out)
        self.assertEqual(rows[0]["dir"], "_agent/jobs/week-page")


if __name__ == "__main__":
    unittest.main()
