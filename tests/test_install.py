"""End-to-end tests of init / render / enable / disable against the fixture modules."""

import json
import tomllib
import unittest
from unittest import mock

import support
from uni_os import install, paths
from uni_os.manifest import Manifest


class InitTests(support.TempDirTestCase):
    def test_init_renders_all_areas(self):
        _, out, _ = self.init()
        self.assertIn("created", out)
        # vault templates, per-course expansion with "&" in the folder name
        self.assertIn("Alex Example", self.read("AGENTS.md"))
        card = self.read("A&D/ad.md")
        self.assertIn("course: algo", card)
        self.assertIn("| Graded quiz | quiz | bonus | solo |", card)
        self.assertIn("(up to 0.25)", card)
        self.assertTrue((self.vault / "PROG" / "prog.md").is_file())
        # per-error-log expansion: one stream vs two streams
        self.assertTrue((self.vault / "A&D" / "ad-error-log.md").is_file())
        self.assertIn("stream: theory", self.read("PROG/prog-error-log-theory.md"))
        self.assertTrue((self.vault / "PROG" / "prog-error-log-programming.md").is_file())
        # jobs, roles, skills go to _agent/
        conf = self.read("_agent/jobs/week-page/job.conf")
        self.assertIn('SLOTS="10:00"', conf)
        self.assertIn('DAYS="Sun"', conf)
        self.assertIn("Alex Example", self.read("_agent/jobs/week-page/prompt.md"))
        self.assertIn("Owns the week pages of Alex Example", self.read("_agent/roles/plan-and-progress.md"))
        skill = self.read("_agent/skills/course-facts/SKILL.md")
        self.assertIn("description: Facts about the EIT courses.", skill)
        self.assertIn("- Graded quiz (quiz, counts for bonus, assistance solo)", skill)
        self.assertIn("- no graded work", skill)

    def test_readme_uses_generated_info_and_keeps_foreign_placeholders(self):
        self.init()
        readme = self.read("README.md")
        self.assertIn("| Progress (fixture) | standard |", readme)
        self.assertIn("- Plan & progress (progress): _agent/roles/plan-and-progress.md", readme)
        self.assertIn("[Algorithms and Data Structures](<A&D/ad.md>) colour #1e66f5 / rgb 30, 102, 245", readme)
        self.assertIn("(last)", readme)
        self.assertIn("Progress lives in progress/.", readme)
        self.assertIn("Study pages come as HTML.", readme)
        self.assertIn("{{date:YYYY-MM-DD}} and {{title}}", readme)
        self.assertIn("Escaped: {{student.name}}", readme)
        self.assertIn("Generated 2026-11-07", readme)

    def test_week_template_keeps_reserved_week_root(self):
        self.init()
        tpl = self.read("_templates/week-page.md")
        self.assertIn("week: {{week.number}}", tpl)
        self.assertIn("# Week {{week.nn}}: {{week.label}}", tpl)
        self.assertIn("updated: {{date}}", tpl)
        self.assertIn("| AD sheet | | | | not released yet |", tpl)  # install-time loop rendered
        self.assertIn("## End-of-week check-in (Sat)", tpl)

    def test_verbatim_binary_and_dir_markers(self):
        self.init()
        self.assertIn("{{course.name}} stays raw", self.read("A&D/notes/ad-demo.html"))
        src = (support.FIXTURE_MODULES / "core" / "vault" / "views" / "pixel.png").read_bytes()
        self.assertEqual((self.vault / "views" / "pixel.png").read_bytes(), src)
        self.assertTrue((self.vault / "PROG" / "notes").is_dir())
        self.assertTrue((self.vault / "progress" / "weeks").is_dir())
        self.assertFalse((self.vault / "progress" / "weeks" / ".gitkeep").exists())

    def test_line_endings_are_lf(self):
        self.init()
        self.assertNotIn(b"\r\n", (self.vault / "README.md").read_bytes())

    def test_manifest_config_copy_and_json(self):
        self.init()
        man = Manifest.load(self.vault)
        self.assertTrue(man.exists)
        entry = man.files["A&D/ad.md"]
        self.assertEqual(entry["module"], "core")
        self.assertEqual(entry["source"], "core/vault/{{course.folder}}/{{course.slug}}.md")
        self.assertEqual(entry["sha256"], paths.sha256_file(self.vault / "A&D" / "ad.md"))
        self.assertTrue(man.files["A&D/notes/ad-demo.html"].get("verbatim"))
        self.assertEqual(man.modules["progress"]["status"], "enabled")
        self.assertIn("progress/weeks", man.dirs)
        raw_text = (self.vault / "_agent" / "uni-os.toml").read_text(encoding="utf-8")
        self.assertEqual(raw_text, self.config.read_text(encoding="utf-8"))
        data = json.loads(self.read("_agent/uni-os.json"))
        self.assertEqual(data["_generated"], "do not edit; edit uni-os.toml")
        self.assertEqual(data["modules"]["enabled"], ["core", "progress", "study"])
        # no absolute paths in the manifest (safe for the public example vault)
        self.assertNotIn(str(self.tmp.as_posix()), man.to_json())

    def test_never_overwrites_without_force(self):
        self.init()
        self.write("AGENTS.md", "my own text\n")
        (self.vault / "README.md").unlink()
        _, out, _ = self.init()
        self.assertEqual(self.read("AGENTS.md"), "my own text\n")
        self.assertIn("= AGENTS.md", out)
        self.assertIn("files you edited", out)
        self.assertTrue((self.vault / "README.md").is_file(), "init restores deleted files")
        _, out, _ = self.init("--force")
        self.assertIn("Alex Example", self.read("AGENTS.md"))
        self.assertIn("overwritten", out)

    def test_existing_unrelated_file_is_skipped(self):
        self.write("AGENTS.md", "pre-existing vault file\n")
        _, out, _ = self.init()
        self.assertEqual(self.read("AGENTS.md"), "pre-existing vault file\n")
        self.assertIn("= AGENTS.md", out)
        self.assertNotIn("AGENTS.md", Manifest.load(self.vault).files)

    def test_dry_run_writes_nothing(self):
        _, out, _ = self.init("--dry-run")
        self.assertIn("would be created", out)
        self.assertFalse(self.vault.exists())

    def test_modules_override_adds_dependencies_and_updates_copy(self):
        _, out, _ = self.init("--modules", "study")
        self.assertIn("modules (2): core, study", out)
        self.assertFalse((self.vault / "_templates" / "week-page.md").exists())
        copy = tomllib.loads(self.read("_agent/uni-os.toml"))
        self.assertEqual(copy["modules"]["enabled"], ["core", "study"])
        self.assertIn("# Small fictional config", self.read("_agent/uni-os.toml"), "comments kept")

    def test_skills_copy_reminder(self):
        """Skills are copied (not linked) to agent.skills_dir, so init and render say when to copy."""
        _, out, _ = self.init()
        self.assertIn("skills written: course-facts. Copy them to agent.skills_dir (.claude/skills)", out)
        _, out, _ = self.in_vault("render")
        self.assertNotIn("skills changed", out, "nothing changed: nothing to copy")
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('short = "EIT"', 'short = "XIT"'), encoding="utf-8")
        _, out, _ = self.in_vault("render")
        self.assertIn("skills changed: course-facts. Copy them again to agent.skills_dir", out)

    def test_modules_override_with_dependency_chain(self):
        _, out, _ = self.init("--modules", "winaddon")
        self.assertIn("modules (3): core, progress, winaddon", out)

    def test_unknown_module_is_an_error(self):
        _, _, err = self.init("--modules", "nope", expect=1)
        self.assertIn("unknown module 'nope'", err)
        self.assertFalse(self.vault.exists())

    def test_init_requires_vault(self):
        _, _, err = self.cli("init", "--config", str(self.config), "--modules-dir", str(support.FIXTURE_MODULES), expect=1)
        self.assertIn("--vault", err)

    def test_config_conflict_with_existing_vault_copy(self):
        self.init()
        other = self.tmp / "other.toml"
        other.write_text(self.config.read_text(encoding="utf-8").replace("Alex Example", "Sam Sample"), encoding="utf-8")
        _, _, err = self.cli("init", "--config", str(other), "--vault", str(self.vault), "--modules-dir", str(support.FIXTURE_MODULES), expect=1)
        self.assertIn("already exists and differs", err)

    def test_invalid_config_writes_nothing(self):
        self.config.write_text(self.config.read_text(encoding="utf-8").replace("week0_monday = 2026-09-14", "week0_monday = 2026-09-15"), encoding="utf-8")
        _, _, err = self.init(expect=1)
        self.assertIn("Monday", err)
        self.assertFalse(self.vault.exists())

    def test_template_error_writes_nothing(self):
        mods = self.tmp / "mods"
        core = mods / "core"
        (core / "vault").mkdir(parents=True)
        (core / "module.toml").write_text('id = "core"\nname = "c"\nsummary = "s"\ntier = "core"\n', encoding="utf-8")
        (core / "vault" / "ok.md").write_text("{{student.name}}\n", encoding="utf-8")
        (core / "vault" / "bad.md").write_text("line\n{{student.nickname}}\n", encoding="utf-8")
        code, out, err = support.run_cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(mods), "--modules", "core")
        self.assertEqual(code, 1)
        self.assertIn("modules/core/vault/bad.md:2", err)
        self.assertIn("student.nickname", err)
        self.assertFalse((self.vault / "ok.md").exists())

    def test_refuses_framework_repo_as_vault(self):
        _, _, err = self.cli("init", "--config", str(self.config), "--vault", str(support.REPO), "--modules-dir", str(support.FIXTURE_MODULES), expect=1)
        self.assertIn("refusing", err)

    def test_collision_between_modules_is_an_error(self):
        mods = self.tmp / "mods"
        for mid, req in (("core", "[]"), ("other", '["core"]')):
            (mods / mid / "vault").mkdir(parents=True)
            (mods / mid / "module.toml").write_text(f'id = "{mid}"\nname = "x"\nsummary = "s"\nrequires = {req}\n', encoding="utf-8")
            (mods / mid / "vault" / "same.md").write_text("x\n", encoding="utf-8")
        _, _, err = self.cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(mods), "--modules", "other", expect=1)
        self.assertIn("also produces", err)

    def test_reproducible_output(self):
        self.init("--date", "2026-01-05")
        first = {rel: e["sha256"] for rel, e in Manifest.load(self.vault).files.items()}
        second_vault = self.tmp / "vault2"
        self.cli("init", "--config", str(self.config), "--vault", str(second_vault), "--modules-dir", str(support.FIXTURE_MODULES), "--date", "2026-01-05")
        second = {rel: e["sha256"] for rel, e in Manifest.load(second_vault).files.items()}
        self.assertEqual(first, second)
        self.assertIn("Generated 2026-01-05", self.read("README.md"))


class RenderTests(support.TempDirTestCase):
    def add_course(self):
        toml = self.vault / "_agent" / "uni-os.toml"
        text = toml.read_text(encoding="utf-8").replace(
            "[modules]",
            '[[courses]]\nid = "la"\nname = "Linear Algebra"\nshort = "LA"\nfolder = "LA"\nslug = "la"\ncolour = "#8839ef"\n\n[modules]',
        )
        toml.write_text(text, encoding="utf-8")

    def test_render_updates_untouched_and_keeps_edited_files(self):
        self.init()
        self.write("AGENTS.md", "edited by me\n")
        self.add_course()
        _, out, _ = self.in_vault("render")
        # new course: new files
        self.assertTrue((self.vault / "LA" / "la.md").is_file())
        self.assertTrue((self.vault / "LA" / "la-error-log.md").is_file())
        self.assertTrue((self.vault / "LA" / "notes").is_dir())
        # untouched generated file updated
        self.assertIn("Linear Algebra", self.read("README.md"))
        self.assertIn("~ README.md", out)
        # edited file kept and reported
        self.assertEqual(self.read("AGENTS.md"), "edited by me\n")
        self.assertIn("= AGENTS.md", out)
        # json regenerated
        data = json.loads(self.read("_agent/uni-os.json"))
        self.assertEqual([c["id"] for c in data["courses"]], ["algo", "prog", "la"])
        # manifest keeps the old hash for the edited file (still "modified")
        self.assertEqual(Manifest.load(self.vault).status(self.vault, "AGENTS.md"), "modified")

    def test_render_does_not_recreate_deleted_files(self):
        self.init()
        (self.vault / "AGENTS.md").unlink()
        _, out, _ = self.in_vault("render")
        self.assertFalse((self.vault / "AGENTS.md").exists())
        self.assertIn("- AGENTS.md", out)

    def test_render_force_replaces_edits(self):
        self.init()
        self.write("AGENTS.md", "edited\n")
        self.in_vault("render", "--force")
        self.assertIn("Alex Example", self.read("AGENTS.md"))

    def test_render_needs_manifest(self):
        self.vault.mkdir()
        (self.vault / "_agent").mkdir()
        (self.vault / "_agent" / "uni-os.toml").write_text(self.config.read_text(encoding="utf-8"), encoding="utf-8")
        _, _, err = self.in_vault("render", expect=1)
        self.assertIn("uni-os init", err)

    def test_render_discovers_vault_from_env(self):
        self.init()
        import os

        os.environ["UNI_OS_VAULT"] = str(self.vault)
        self.cli("render", "--modules-dir", str(support.FIXTURE_MODULES))

    def test_render_reports_orphans_after_course_removal(self):
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        text = toml.read_text(encoding="utf-8")
        start = text.index('[[courses]]\nid = "prog"')
        end = text.index("[modules]")
        toml.write_text(text[:start] + text[end:], encoding="utf-8")
        _, out, _ = self.in_vault("render")
        self.assertIn("orphaned", out)
        self.assertIn("PROG/prog.md", out)
        self.assertTrue((self.vault / "PROG" / "prog.md").is_file(), "never deleted")


class EnableDisableTests(support.TempDirTestCase):
    def enabled_in_copy(self):
        return tomllib.loads(self.read("_agent/uni-os.toml"))["modules"]["enabled"]

    def test_enable_installs_module_and_updates_config(self):
        self.init("--modules", "study")
        self.assertFalse((self.vault / "_agent" / "jobs" / "week-page").exists())
        _, out, _ = self.in_vault("enable", "winaddon")
        self.assertIn("enabling: progress, winaddon", out)
        self.assertEqual(self.enabled_in_copy(), ["core", "study", "winaddon"])
        self.assertTrue((self.vault / "_agent" / "jobs" / "week-page" / "job.conf").is_file())
        self.assertTrue((self.vault / "_agent" / "jobs" / "win-watch" / "job.conf").is_file())
        self.assertIn("Progress (fixture)", self.read("README.md"))
        _, out, _ = self.in_vault("enable", "progress")
        self.assertIn("already enabled", out)

    def test_enable_unknown_module(self):
        self.init()
        _, _, err = self.in_vault("enable", "nope", expect=1)
        self.assertIn("unknown module 'nope'", err)

    def test_disable_never_deletes_and_marks_jobs(self):
        self.init()
        _, out, _ = self.in_vault("disable", "progress")
        self.assertEqual(self.enabled_in_copy(), ["study"])
        self.assertTrue((self.vault / "_templates" / "week-page.md").is_file())
        marker = self.vault / "_agent" / "jobs" / "week-page" / "DISABLED"
        self.assertTrue(marker.is_file())
        self.assertIn("uni-os enable progress", marker.read_text(encoding="utf-8"))
        self.assertNotIn("Progress (fixture)", self.read("README.md"))
        self.assertIn("No progress module.", self.read("README.md"))
        self.assertEqual(Manifest.load(self.vault).modules["progress"]["status"], "disabled")
        self.assertIn("kept in the vault", out)
        # re-enable removes the marker
        self.in_vault("enable", "progress")
        self.assertFalse(marker.exists())
        self.assertEqual(Manifest.load(self.vault).modules["progress"]["status"], "enabled")

    def test_disable_blocked_by_dependents(self):
        self.init("--modules", "winaddon")
        _, _, err = self.in_vault("disable", "progress", expect=1)
        self.assertIn("progress is needed by winaddon", err)
        self.assertIn("uni-os disable progress winaddon", err)
        self.in_vault("disable", "progress", "winaddon")
        self.assertEqual(self.enabled_in_copy(), ["core"])

    def test_disable_core_refused(self):
        self.init()
        _, _, err = self.in_vault("disable", "core", expect=1)
        self.assertIn("cannot be disabled", err)

    def test_dry_run_enable_changes_nothing(self):
        self.init("--modules", "study")
        before = self.read("_agent/uni-os.toml")
        _, out, _ = self.in_vault("enable", "progress", "--dry-run")
        self.assertIn("would set modules.enabled", out)
        self.assertEqual(self.read("_agent/uni-os.toml"), before)
        self.assertFalse((self.vault / "_templates" / "week-page.md").exists())

    def test_modules_command_shows_status(self):
        self.init("--modules", "study")
        _, out, _ = self.in_vault("modules")
        self.assertRegex(out, r"core\s+enabled")
        self.assertRegex(out, r"study\s+enabled")
        self.assertRegex(out, r"progress\s+available")
        self.assertIn("[windows only]", out)


class WriteFailureTests(support.TempDirTestCase):
    """A file or folder that cannot be written is reported; everything else is written and recorded."""

    def test_unwritable_target_is_reported_and_the_rest_is_recorded(self):
        # A plain file named like a course folder: PROG/prog.md and the PROG folders cannot be created.
        self.vault.mkdir()
        (self.vault / "PROG").write_text("in the way\n", encoding="utf-8")
        code, out, err = self.init(expect=1)
        self.assertIn("PROG/prog.md: could not be written:", err)
        self.assertIn("PROG/notes/: could not be written:", err)
        self.assertIn("everything else was written and recorded in the manifest", err)
        self.assertNotIn("Traceback", err)
        # the rest of the vault was written ...
        self.assertTrue((self.vault / "A&D" / "ad.md").is_file())
        self.assertTrue((self.vault / "A&D" / "notes").is_dir())
        # ... and recorded: the manifest and uni-os.json were saved for what was written
        man = Manifest.load(self.vault)
        self.assertTrue(man.exists)
        self.assertIn("A&D/ad.md", man.files)
        self.assertIn("A&D/notes", man.dirs)
        self.assertNotIn("PROG/prog.md", man.files)
        self.assertNotIn("PROG/notes", man.dirs)
        self.assertTrue((self.vault / "_agent" / "uni-os.json").is_file())
        self.assertNotIn("+ PROG/prog.md", out, "a failed file is not reported as created")
        # fix the cause, run again: only the missing part is written
        (self.vault / "PROG").unlink()
        _, out, _ = self.init()
        self.assertTrue((self.vault / "PROG" / "prog.md").is_file())
        self.assertIn("PROG/prog.md", Manifest.load(self.vault).files)

    def test_render_reports_a_failed_update(self):
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('short = "EIT"', 'short = "XIT"'), encoding="utf-8")
        old_hash = Manifest.load(self.vault).files["AGENTS.md"]["sha256"]
        real_write = paths.atomic_write

        def locked(path, data):
            if path.name == "AGENTS.md" and path.parent == self.vault:
                raise PermissionError(13, "Permission denied", str(path))
            real_write(path, data)

        with mock.patch.object(paths, "atomic_write", side_effect=locked):
            _, out, err = self.in_vault("render", expect=1)
        self.assertIn("AGENTS.md: could not be written: Permission denied:", err)
        self.assertNotIn("~ AGENTS.md", out, "a failed update is not reported as updated")
        self.assertIn("~ _agent/skills/course-facts/SKILL.md", out, "the other updates went through")
        man = Manifest.load(self.vault)
        self.assertEqual(man.files["AGENTS.md"]["sha256"], old_hash, "old hash kept: the file still counts as untouched")
        self.assertIn("XIT", self.read("_agent/skills/course-facts/SKILL.md"))
        self.in_vault("render")
        self.assertIn("XIT", self.read("AGENTS.md"))

    def test_failed_json_write_is_reported_and_the_manifest_saved(self):
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('short = "EIT"', 'short = "XIT"'), encoding="utf-8")
        real_write = install.write_if_changed

        def locked(path, data, *, dry_run=False):
            if path.name == paths.JSON_NAME:
                raise PermissionError(13, "Permission denied", str(path))
            return real_write(path, data, dry_run=dry_run)

        with mock.patch.object(install, "write_if_changed", side_effect=locked):
            _, out, err = self.in_vault("render", expect=1)
        self.assertIn("_agent/uni-os.json: could not be written: Permission denied:", err)
        self.assertIn("1 file(s) after the module files could not be written", err)
        self.assertNotIn("Traceback", err)
        self.assertIn(f"_agent/{paths.MANIFEST_NAME} saved", out)
        # the template update went through and is recorded, so the next render has nothing left but the JSON
        self.assertIn("XIT", self.read("_agent/skills/course-facts/SKILL.md"))
        sha = Manifest.load(self.vault).files["_agent/skills/course-facts/SKILL.md"]["sha256"]
        self.assertEqual(sha, paths.sha256_file(self.vault / "_agent" / "skills" / "course-facts" / "SKILL.md"))
        self.assertNotIn('"XIT"', self.read("_agent/uni-os.json"))
        self.in_vault("render")
        self.assertIn('"XIT"', self.read("_agent/uni-os.json"))

    def test_failed_disabled_marker_is_reported(self):
        self.init()
        real_write = paths.write_text

        def locked(path, text, *args, **kwargs):
            if path.name == "DISABLED":
                raise PermissionError(13, "Permission denied", str(path))
            return real_write(path, text, *args, **kwargs)

        with mock.patch.object(paths, "write_text", side_effect=locked):
            _, out, err = self.in_vault("disable", "progress", expect=1)
        self.assertIn("_agent/jobs/week-page/DISABLED: could not be written: Permission denied:", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(Manifest.load(self.vault).modules["progress"]["status"], "disabled", "the manifest was still saved")
        self.assertTrue((self.vault / "_agent" / "uni-os.json").is_file())

    def test_os_error_outside_the_installer_is_one_clean_line(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("a file, not a folder\n", encoding="utf-8")
        code, out, err = self.cli(
            "init", "--config", str(self.config), "--vault", str(blocker / "vault"),
            "--modules-dir", str(support.FIXTURE_MODULES), expect=1,
        )
        self.assertTrue(err.startswith("uni-os: error: "), err)
        self.assertIn("blocker", err)
        self.assertNotIn("Traceback", err)

    def test_os_error_text(self):
        self.assertEqual(install.os_error_text(PermissionError(13, "Permission denied", "G:\\Uni\\x.md")), "Permission denied: G:/Uni/x.md")
        self.assertEqual(install.os_error_text(OSError("disk full")), "disk full")


class GlobTests(unittest.TestCase):
    def test_glob_to_regex(self):
        rx = install.glob_to_regex
        self.assertTrue(rx("vault/**/*.html").match("vault/a/b/c.html"))
        self.assertTrue(rx("vault/**/*.html").match("vault/c.html"))
        self.assertFalse(rx("vault/*.html").match("vault/a/c.html"))
        self.assertTrue(rx("**/private/**").match("Notes/PDF/private/x.pdf"))
        self.assertFalse(rx("**/private/**").match("Notes/privately.md"))
        self.assertTrue(rx("progress/weeks/week-??.md").match("progress/weeks/week-07.md"))


if __name__ == "__main__":
    unittest.main()
