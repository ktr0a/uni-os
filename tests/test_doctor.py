"""Tests for `uni-os doctor`: secrets scan, contract checks (registry + declarative), install state."""

import json
import unittest

import support
from uni_os import doctor, secrets

# Fake secrets are assembled at run time so no key-like literal sits in the repo.
FAKE_ANTHROPIC = "sk-" + "ant-" + "Q7wZ" * 8
FAKE_GITHUB = "gh" + "p_" + "R4nD0m" * 7
FAKE_AWS = "AK" + "IA" + "QWERTYUIOPASDFGH"
FAKE_ICAL = "https://calendar.google.com/calendar/ical/someone%40mail.test/private-" + "0123456789abcdef" * 2 + "/basic.ics"
FAKE_PRIVATE_KEY = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"


class ScanTextTests(unittest.TestCase):
    def names(self, text, **kw):
        return [h.pattern for h in secrets.scan_text(text, **kw)]

    def test_detects_common_secrets(self):
        text = "\n".join([FAKE_ANTHROPIC, FAKE_GITHUB, FAKE_AWS, FAKE_ICAL, FAKE_PRIVATE_KEY, "push to https://ntfy.sh/zq81-hidden-topic"])
        names = self.names(text)
        for name in ("anthropic-key", "github-token", "aws-access-key", "ical-google-private", "private-key", "ntfy-topic-url"):
            self.assertIn(name, names)

    def test_redaction_never_shows_the_secret(self):
        hits = secrets.scan_text(FAKE_ANTHROPIC)
        self.assertEqual(len(hits), 1)
        self.assertNotIn(FAKE_ANTHROPIC, hits[0].redacted)
        self.assertIn("chars", hits[0].redacted)

    def test_placeholders_and_docs_are_ignored(self):
        text = "\n".join([
            "sk-ant-your-key-here-xxxxxxxxxxxxxxxxxx",
            "https://calendar.google.com/calendar/ical/.../private-.../basic.ics",
            "open https://ntfy.sh/app or https://ntfy.sh/docs",
            "ntfy_topic_file = \"~/.config/uni-os/ntfy-topic\"",
            "AKIAIOSFODNN7EXAMPLE",
            f"{FAKE_ANTHROPIC}  uni-os: allow-secret",
        ])
        self.assertEqual(self.names(text), [])

    def test_literal_topic(self):
        hits = secrets.scan_text("my topic is zq81hiddentopic", literals=[("ntfy topic", "zq81hiddentopic")])
        self.assertEqual([h.redacted for h in hits], ["(value hidden)"])

    def test_assignment_heuristic_is_a_warning(self):
        hits = secrets.scan_text('api_key = "Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5"')
        self.assertEqual([h.level for h in hits], ["warning"])


class DoctorRunTests(support.TempDirTestCase):
    def doctor(self, *extra, expect=None):
        return self.in_vault("doctor", *extra, expect=expect)

    def test_clean_vault_passes(self):
        self.init()
        code, out, _ = self.doctor()
        self.assertEqual(code, 0, out)
        self.assertIn("0 error(s)", out)

    def test_secrets_are_found_and_redacted(self):
        self.init()
        self.topic_file.write_text("zq81hiddentopic\n", encoding="utf-8")
        self.write("inbox/2026-11-07_leak.md", f"key {FAKE_ANTHROPIC}\ncal {FAKE_ICAL}\nntfy https://ntfy.sh/zq81hiddentopic\n")
        self.write("Notes/private/diary.md", f"{FAKE_ANTHROPIC}\n")  # never opened (paths.never_open)
        code, out, _ = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("inbox/2026-11-07_leak.md: line 1: Anthropic API key", out)
        self.assertIn("private Google Calendar iCal address", out)
        self.assertIn("your ntfy topic", out)
        self.assertNotIn(FAKE_ANTHROPIC, out)
        self.assertNotIn("zq81hiddentopic", out)
        self.assertNotIn("diary.md", out)

    def test_no_secrets_flag(self):
        self.init()
        self.write("inbox/leak.md", FAKE_ANTHROPIC + "\n")
        code, _, _ = self.doctor("--no-secrets")
        self.assertEqual(code, 0)

    def test_week_page_contract(self):
        self.init()
        self.in_vault("new-week")
        self.write("progress/weeks/week-09.md", "---\ntype: week\nweek: 9\nstatus: current\n---\n# Week 09\n## Due this week\n| Item | Status |\n|---|---|\n## Notes\n")
        code, out, _ = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("week-09.md: missing heading '## Results this week'", out)
        self.assertIn("week-09.md: missing heading '## End-of-week check-in'", out)
        self.assertIn("no deadline column", out)
        self.assertIn("2 week pages have status: current", out)
        self.assertNotIn("week-08.md: missing heading", out)

    def test_week_status_values_follow_the_progress_contract(self):
        """upcoming | current | done (modules/progress); anything else is a warning."""
        self.assertEqual(doctor.WEEK_STATUSES, ("upcoming", "current", "done"))
        self.init()
        page = self.read("_templates/week-page.md")
        self.write("progress/weeks/week-12.md", page.replace("{{week.status}}", "upcoming").replace("week: {{week.number}}", "week: 12"))
        self.write("progress/weeks/week-13.md", page.replace("{{week.status}}", "planned").replace("week: {{week.number}}", "week: 13"))
        _, out, _ = self.doctor()
        self.assertNotIn("week-12.md: status", out)
        self.assertIn("week-13.md: status 'planned' should be one of upcoming, current, done", out)

    def test_declarative_contract_from_module_toml(self):
        self.init()
        self.write("progress/tracker-log.md", "---\ntype: notes\n---\n# Tracker\n")
        _, out, _ = self.doctor()
        self.assertIn("missing heading '## Entries' (tracker log keeps its heading)", out)
        self.assertIn("frontmatter type: notes should be log", out)

    def test_install_state_findings(self):
        self.init()
        (self.vault / "AGENTS.md").unlink()
        self.write("README.md", "edited\n")
        self.write("_agent/uni-os.json", "{}\n")
        _, out, _ = self.doctor("-v")
        self.assertIn("AGENTS.md: installed file is missing", out)
        self.assertIn("README.md: edited since install", out)
        self.assertIn("uni-os.json is out of date", out)

    def test_unrendered_placeholder_in_edited_file(self):
        self.init()
        text = self.read("progress/tracker-log.md") + "copied {{course.name}}\n"
        self.write("progress/tracker-log.md", text)
        _, out, _ = self.doctor()
        self.assertIn("progress/tracker-log.md: unrendered placeholder {{course.name}}", out)
        self.assertNotIn("README.md: unrendered", out)  # escaped example in the README is fine
        self.assertNotIn("ad-demo.html: unrendered", out)  # verbatim file

    def test_bad_job_conf(self):
        self.init()
        self.write("_agent/jobs/week-page/job.conf", 'KIND="agent"\nSLOTS="7:30"\n')
        code, out, _ = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("SLOTS entry '7:30'", out)

    def test_config_errors_and_strict(self):
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('colour = "#d20f39"', 'colour = "red"'), encoding="utf-8")
        code, out, _ = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("courses.prog.colour", out)

    def test_json_output_and_strict_warnings(self):
        self.init()
        self.write("README.md", "edited {{course.name}}\n")
        code, out, _ = self.doctor("--json")
        data = json.loads(out)
        self.assertEqual(data["errors"], 0)
        self.assertGreaterEqual(data["warnings"], 1)
        self.assertEqual(code, 0)
        code, _, _ = self.doctor("--strict")
        self.assertEqual(code, 1)

    def test_not_initialised(self):
        self.vault.mkdir()
        (self.vault / "_agent").mkdir()
        (self.vault / "_agent" / "uni-os.toml").write_text(self.config.read_text(encoding="utf-8"), encoding="utf-8")
        code, out, _ = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("not set up with `uni-os init`", out)

    def test_config_only_mode(self):
        code, out, _ = self.cli("doctor", "--config", str(self.config), "--modules-dir", str(support.FIXTURE_MODULES), expect=None)
        self.assertEqual(code, 0, out)
        self.assertIn("(no vault)", out)


class SkillCopyTests(support.TempDirTestCase):
    """Copies in agent.skills_dir that no longer match _agent/skills/ are a warning."""

    def copy_skills(self, target=".claude/skills"):
        import shutil

        shutil.copytree(self.vault / "_agent" / "skills", self.vault / target, dirs_exist_ok=True)

    def set_skills_dir(self, value):
        toml = self.vault / "_agent" / "uni-os.toml"
        text = toml.read_text(encoding="utf-8").replace("[notify]", f'[agent]\nskills_dir = "{value}"\n\n[notify]', 1)
        toml.write_text(text, encoding="utf-8")
        self.in_vault("render")

    def test_current_copy_passes_strict(self):
        self.init()
        self.copy_skills()
        code, out, _ = self.in_vault("doctor", "--strict", expect=None)
        self.assertEqual(code, 0, out)
        self.assertNotIn("skill copies", out)
        self.assertNotIn("not copied", out)

    def test_stale_copy_warns_and_prints_the_copy_command(self):
        self.init()
        self.copy_skills()
        skill = self.vault / ".claude" / "skills" / "course-facts" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("EIT", "OLD"), encoding="utf-8")
        code, out, _ = self.in_vault("doctor", "--strict", expect=None)
        self.assertEqual(code, 1, out)
        self.assertIn("WARN  .claude/skills: skill copies are out of date with _agent/skills/: course-facts (SKILL.md differs)", out)
        self.assertIn("setup/PLAYBOOK.md, step 7.3", out)
        vault = self.vault.as_posix()
        self.assertIn(f'cp -R "{vault}/_agent/skills/." "{vault}/.claude/skills/"', out)
        self.assertIn(f'Copy-Item -Recurse -Force "{vault}/_agent/skills/*" "{vault}/.claude/skills/"', out)
        self.assertEqual(self.in_vault("doctor", expect=None)[0], 0, "a warning, not an error")
        # a file missing from the copy counts too; copying again fixes both
        skill.unlink()
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertIn("course-facts (SKILL.md missing)", out)
        self.copy_skills()
        code, out, _ = self.in_vault("doctor", "--strict", expect=None)
        self.assertEqual(code, 0, out)

    def test_extra_files_in_the_copy_are_ignored(self):
        self.init()
        self.copy_skills()
        (self.vault / ".claude" / "skills" / "course-facts" / "my-notes.md").write_text("mine\n", encoding="utf-8")
        (self.vault / ".claude" / "skills" / "my-own-skill").mkdir()
        code, out, _ = self.in_vault("doctor", "--strict", expect=None)
        self.assertEqual(code, 0, out)

    def test_missing_copy_is_only_info(self):
        self.init()
        code, out, _ = self.in_vault("doctor", "--strict", expect=None)
        self.assertEqual(code, 0, out)
        self.assertIn("ok    .claude/skills: 1 skill(s) not copied here: course-facts", out)

    def test_skills_dir_outside_the_vault_is_not_checked(self):
        self.init()
        self.set_skills_dir("~/.claude/skills")
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertNotIn("not copied", out)
        self.assertEqual(doctor.skill_copy_findings(self.vault, {"agent": {"skills_dir": "C:/Tools/skills"}}, "_agent"), [])
        self.assertEqual(doctor.skill_copy_findings(self.vault, {"agent": {"skills_dir": "../skills"}}, "_agent"), [])

    def test_skills_dir_pointing_at_the_installed_skills_is_not_checked(self):
        self.init()
        self.assertEqual(doctor.skill_copy_findings(self.vault, {"agent": {"skills_dir": "_agent/skills"}}, "_agent"), [])

    def test_only_skills_of_enabled_modules(self):
        self.init()
        findings = doctor.skill_copy_findings(self.vault, {"agent": {"skills_dir": ".claude/skills"}}, "_agent", skill_ids=[])
        self.assertEqual(findings, [])


class RegistryTests(support.TempDirTestCase):
    def test_custom_check_registration(self):
        calls = []

        @doctor.contract("test-only-check", modules=("study",))
        def _check(ctx):
            calls.append(ctx.vault)
            yield doctor.Finding("warning", "contracts", "custom finding", "x.md")

        try:
            self.init()
            _, out, _ = self.in_vault("doctor")
            self.assertIn("x.md: custom finding", out)
            self.assertEqual(len(calls), 1)
        finally:
            doctor.REGISTRY[:] = [c for c in doctor.REGISTRY if c.name != "test-only-check"]

    def test_check_skipped_when_module_disabled(self):
        @doctor.contract("needs-ghost", modules=("ghost-module",))
        def _check(ctx):
            yield doctor.Finding("error", "contracts", "should not run")

        try:
            self.init()
            _, out, _ = self.in_vault("doctor")
            self.assertNotIn("should not run", out)
        finally:
            doctor.REGISTRY[:] = [c for c in doctor.REGISTRY if c.name != "needs-ghost"]


if __name__ == "__main__":
    unittest.main()
