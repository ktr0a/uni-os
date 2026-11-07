"""Module folders (``[[folders]]``), region-aware re-render and the course property check.

Uses the fixture modules: ``study`` declares one folder per ``official_subfolders``
entry and the derived handwritten folder; the core fixture's README has two
generated regions (``modules`` and ``progress``).
"""

import json

import support
from uni_os import config, modules, paths
from uni_os.manifest import Manifest

FOLDERS = [
    "A&D/sheets",
    "A&D/sheets/solutions",
    "A&D/script & slides",
    "A&D/A&D handwritten",
    "PROG/PROG tablet",
]


class FolderTests(support.TempDirTestCase):
    def test_init_creates_and_records_module_folders(self):
        _, out, _ = self.init()
        for rel in FOLDERS:
            self.assertTrue((self.vault / rel).is_dir(), rel)
            self.assertIn(f"+ {rel}/", out)  # listed without -v
        self.assertEqual([p for p in (self.vault / "A&D").rglob("*") if p.is_file() and "sheets" in p.parts], [], "no placeholder files")
        man = Manifest.load(self.vault)
        for rel in FOLDERS:
            self.assertEqual(man.dirs[rel], "study")

    def test_dry_run_lists_folders(self):
        _, out, _ = self.init("--dry-run")
        self.assertIn("would be created", out)
        self.assertIn("+ A&D/script & slides/", out)
        self.assertFalse(self.vault.exists())

    def test_only_when_the_module_is_enabled_and_never_deleted(self):
        self.init("--modules", "progress")
        self.assertFalse((self.vault / "A&D" / "sheets").exists())
        _, out, _ = self.in_vault("enable", "study")
        self.assertIn("+ A&D/sheets/", out)
        self.assertTrue((self.vault / "A&D" / "sheets").is_dir())
        self.in_vault("disable", "study")
        for rel in FOLDERS:
            self.assertTrue((self.vault / rel).is_dir(), f"{rel} kept after disable")

    def test_render_adds_new_folders_but_does_not_recreate_deleted_ones(self):
        self.init()
        (self.vault / "A&D" / "sheets" / "solutions").rmdir()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(
            toml.read_text(encoding="utf-8").replace('"script & slides"]', '"script & slides", "handouts"]'),
            encoding="utf-8",
        )
        _, out, _ = self.in_vault("render")
        self.assertTrue((self.vault / "A&D" / "handouts").is_dir())
        self.assertIn("+ A&D/handouts/", out)
        self.assertFalse((self.vault / "A&D" / "sheets" / "solutions").exists())
        self.assertIn("- A&D/sheets/solutions/", out)
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertIn("installed folder is missing", out)
        self.cli("init", "--vault", str(self.vault), "--modules-dir", str(support.FIXTURE_MODULES))  # init restores it
        self.assertTrue((self.vault / "A&D" / "sheets" / "solutions").is_dir())

    def test_doctor_reports_folders_not_created_yet(self):
        self.init()
        man = Manifest.load(self.vault)
        del man.dirs["A&D/script & slides"]
        man.save("2026-11-07")
        (self.vault / "A&D" / "script & slides").rmdir()
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertIn("folder(s) not created yet (A&D/script & slides/)", out)

    def test_file_in_the_way_is_a_conflict(self):
        self.vault.mkdir()
        (self.vault / "PROG").mkdir()
        (self.vault / "PROG" / "PROG tablet").write_text("a file\n", encoding="utf-8")
        _, _, err = self.init(expect=1)
        self.assertIn("a file exists where module 'study' needs a folder", err)

    def test_handwritten_dir_is_derived(self):
        cfg = config.resolve({"courses": [{"id": "a", "folder": "A&D", "slug": "ad"}, {"id": "b", "folder": "B", "slug": "b", "handwritten_folder": "tablet/"}]})
        self.assertEqual(cfg["courses"][0]["handwritten_dir"], "A&D handwritten")
        self.assertEqual(cfg["courses"][1]["handwritten_dir"], "tablet")

    def test_bad_handwritten_folder_is_a_config_error(self):
        self.config.write_text(
            self.config.read_text(encoding="utf-8").replace('handwritten_folder = "PROG tablet"', 'handwritten_folder = "../outside"'),
            encoding="utf-8",
        )
        _, _, err = self.init(expect=1)
        self.assertIn("handwritten_folder", err)


class FolderSpecTests(support.TempDirTestCase):
    def make_module(self, body: str):
        mods = self.tmp / "mods"
        core = mods / "core"
        core.mkdir(parents=True, exist_ok=True)
        (core / "module.toml").write_text('id = "core"\nname = "c"\nsummary = "s"\ntier = "core"\n' + body, encoding="utf-8")
        return mods

    def test_validation(self):
        mods = self.make_module('[[folders]]\neach = "course.x"\n\n[[folders]]\npath = "a"\neach = "not a key!"\n\n[[folders]]\npath = "b"\nmode = 1\n')
        mod, problems = modules.load_module(mods / "core")
        text = "\n".join(p.message for p in problems)
        self.assertIn("needs path", text)
        self.assertIn("must name a list key", text)
        self.assertIn("unknown key 'mode'", text)
        self.assertEqual([f["path"] for f in mod.folders], ["b"])

    def test_each_must_be_a_list_and_paths_must_stay_in_the_vault(self):
        mods = self.make_module('[[folders]]\npath = "{{course.folder}}/{{item}}"\neach = "course.name"\n')
        _, _, err = support.run_cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(mods), "--modules", "core")
        self.assertIn("must name a list", err)
        mods = self.make_module('[[folders]]\npath = "../{{student.handle}}"\n')
        code, _, err = support.run_cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(mods), "--modules", "core")
        self.assertEqual(code, 1)
        self.assertIn("not a valid vault path", err)

    def test_plain_and_agent_dir_paths(self):
        mods = self.make_module('[[folders]]\npath = "_agent/drop/{{student.handle}}"\n\n[[folders]]\npath = "{{course.slug}}-extra"\n')
        support.run_cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(mods), "--modules", "core")
        self.assertTrue((self.vault / "_agent" / "drop" / "alex").is_dir())
        self.assertTrue((self.vault / "ad-extra").is_dir())
        self.assertTrue((self.vault / "prog-extra").is_dir())


class RegionRenderTests(support.TempDirTestCase):
    def write(self, rel: str, text: str) -> None:
        """Write with LF line endings on every OS (write_text would give CRLF on Windows)."""
        (self.vault / rel).write_bytes(text.encode("utf-8"))

    def edit_readme(self):
        text = self.read("README.md")
        text = text.replace("## Courses", "My own intro line.\n\n## Courses")
        self.write("README.md", text + "\nMy own closing note.\n")

    def test_render_refreshes_regions_of_an_edited_file(self):
        self.init("--modules", "study")
        self.edit_readme()
        baseline = Manifest.load(self.vault).files["README.md"]["sha256"]
        _, out, _ = self.in_vault("enable", "progress")
        readme = self.read("README.md")
        self.assertIn("| Progress (fixture) | standard |", readme)  # region "modules" refreshed
        self.assertIn("Progress lives in progress/.", readme)  # region "progress" refreshed
        self.assertNotIn("No progress module.", readme)
        self.assertIn("My own intro line.", readme)
        self.assertIn("My own closing note.", readme)
        self.assertIn("~ README.md  [modules, progress]", out)
        entry = Manifest.load(self.vault).files["README.md"]
        self.assertEqual(entry["sha256"], baseline, "the baseline hash is kept")
        self.assertEqual(entry["merged_sha256"], paths.sha256_file(self.vault / "README.md"))
        self.assertEqual(Manifest.load(self.vault).status(self.vault, "README.md"), "modified")
        # disable re-renders too
        _, out, _ = self.in_vault("disable", "progress")
        readme = self.read("README.md")
        self.assertNotIn("| Progress (fixture) |", readme)
        self.assertIn("No progress module.", readme)
        self.assertIn("My own closing note.", readme)
        # nothing left to do: reported as current, file untouched
        before = self.read("README.md")
        _, out, _ = self.in_vault("render")
        self.assertIn("generated regions are already current", out)
        self.assertEqual(self.read("README.md"), before)
        _, out, _ = self.in_vault("doctor", "-v", expect=None)
        self.assertIn("edited outside its generated regions", out)

    def test_dry_run_reports_regions_and_writes_nothing(self):
        self.init("--modules", "study")
        self.edit_readme()
        before = self.read("README.md")
        _, out, _ = self.in_vault("enable", "progress", "--dry-run")
        self.assertIn("would be refreshed", out)
        self.assertIn("~ README.md  [modules, progress]", out)
        self.assertEqual(self.read("README.md"), before)

    def test_broken_markers_skip_the_file(self):
        self.init("--modules", "study")
        self.edit_readme()
        self.write("README.md", self.read("README.md").replace("<!-- uni-os:end progress -->\n", ""))
        before = self.read("README.md")
        _, out, _ = self.in_vault("enable", "progress")
        self.assertEqual(self.read("README.md"), before, "never guessed")
        self.assertIn("! README.md: markers in the file are missing or malformed", out)
        self.assertIn("never closed", out)
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertIn("generated regions cannot be refreshed", out)
        # --force still replaces the whole file
        self.in_vault("render", "--force")
        self.assertNotIn("My own closing note.", self.read("README.md"))
        self.assertEqual(Manifest.load(self.vault).status(self.vault, "README.md"), "unmodified")

    def test_edits_only_inside_regions_make_the_file_untouched_again(self):
        self.init()
        self.write("README.md", self.read("README.md").replace("Progress lives in progress/.", "I scribbled here."))
        _, out, _ = self.in_vault("render")
        self.assertIn("~ README.md  [progress]", out)
        self.assertIn("Progress lives in progress/.", self.read("README.md"))
        entry = Manifest.load(self.vault).files["README.md"]
        self.assertNotIn("merged_sha256", entry)
        self.assertEqual(Manifest.load(self.vault).status(self.vault, "README.md"), "unmodified")

    def test_files_without_regions_are_kept_as_before(self):
        self.init()
        self.write("AGENTS.md", "edited\n")
        _, out, _ = self.in_vault("render")
        self.assertEqual(self.read("AGENTS.md"), "edited\n")
        self.assertIn("files you edited (not overwritten", out)

    def test_init_never_merges(self):
        self.init("--modules", "study")
        self.edit_readme()
        before = self.read("README.md")
        toml = self.vault / "_agent" / "uni-os.toml"
        self.cli("init", "--vault", str(self.vault), "--modules-dir", str(support.FIXTURE_MODULES))
        self.assertEqual(self.read("README.md"), before)
        self.assertTrue(toml.is_file())


class CoursePropertyTests(support.TempDirTestCase):
    def test_course_property_must_be_the_id(self):
        self.init()
        self.write("A&D/notes/ad-heaps.md", "---\ntype: study-page\ncourse: ad\n---\n# Heaps\n")
        self.write("A&D/notes/ad-ok.md", "---\ntype: study-page\ncourse: algo\n---\n# OK\n")
        self.write("PROG/notes/prog-draft.md", "---\ncourse: <course id>\n---\n")
        self.write("_templates/x.md", "---\ncourse: whatever\n---\n")
        _, out, _ = self.in_vault("doctor", expect=None)
        self.assertIn("A&D/notes/ad-heaps.md: course: ad is not a course id (algo, prog); use course: algo", out)
        self.assertNotIn("ad-ok.md", out)
        self.assertNotIn("prog-draft.md", out)
        self.assertNotIn("_templates/x.md", out)

    def test_course_card_needs_the_id(self):
        from uni_os import doctor

        self.init()
        self.write("A&D/ad.md", self.read("A&D/ad.md").replace("course: algo", "course: ad"))
        cfg = config.load(self.vault, modules_dir=support.FIXTURE_MODULES)
        ctx = doctor.DoctorContext(self.vault, cfg, ["core", "courses"], modules.discover(support.FIXTURE_MODULES))
        found = [f.message for f in doctor.check_course_cards(ctx)]
        self.assertEqual(found, ["course card frontmatter should have course: algo (the course id)"])

    def test_json_has_handwritten_dir(self):
        self.init()
        data = json.loads(self.read("_agent/uni-os.json"))
        self.assertEqual([c["handwritten_dir"] for c in data["courses"]], ["A&D handwritten", "PROG tablet"])


if __name__ == "__main__":
    import unittest

    unittest.main()
