"""Tests for module discovery, module.toml validation, dependency resolution and presets."""

import unittest
from pathlib import Path

import support
from uni_os import modules, presets
from uni_os.errors import ModuleError


def write_module(root: Path, mid: str, body: str) -> Path:
    folder = root / mid
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "module.toml").write_text(body, encoding="utf-8")
    return folder


class DiscoveryTests(unittest.TestCase):
    def test_fixture_catalog(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        self.assertEqual(set(catalog.modules), {"core", "progress", "study", "winaddon"})
        self.assertEqual([p for p in catalog.problems if p.level == "error"], [])
        progress = catalog.modules["progress"]
        self.assertEqual(progress.requires, ["core"])
        self.assertEqual(progress.job_ids, ["week-page"])
        self.assertEqual(progress.role_ids, ["plan-and-progress"])
        self.assertEqual(catalog.modules["study"].skill_ids, ["course-facts"])
        self.assertEqual(catalog.modules["winaddon"].os, ["windows"])
        self.assertTrue(catalog.modules["winaddon"].supports_os("windows"))
        self.assertFalse(catalog.modules["winaddon"].supports_os("linux"))
        self.assertTrue(catalog.modules["core"].supports_os("macos"))
        self.assertEqual(catalog.ids()[0], "core")

    def test_missing_folder(self):
        catalog = modules.discover(support.TESTS / "does-not-exist")
        self.assertEqual(catalog.modules, {})
        self.assertTrue(catalog.problems)


class ManifestValidationTests(support.TempDirTestCase):
    def test_bad_manifests_are_reported_not_raised(self):
        root = self.tmp / "mods"
        write_module(root, "core", 'id = "core"\nname = "Core"\nsummary = "s"\ntier = "core"\n')
        write_module(root, "wrong", 'id = "other"\nname = "W"\nsummary = "s"\n')
        write_module(root, "badtier", 'id = "badtier"\nname = "B"\nsummary = "s"\ntier = "gold"\nos = ["plan9"]\n')
        write_module(root, "broken", 'id = "broken\n')
        write_module(root, "extra", 'id = "extra"\nname = "E"\nsummary = "s"\nfoo = 1\n[[jobs]]\nid = "ghost"\n')
        (root / "wip").mkdir()
        catalog = modules.discover(root)
        text = "\n".join(str(p) for p in catalog.problems)
        self.assertIn("must equal the folder name", text)
        self.assertIn("tier 'gold'", text)
        self.assertIn("os 'plan9'", text)
        self.assertIn("invalid TOML", text)
        self.assertIn("unknown key 'foo'", text)
        self.assertIn("declares job 'ghost'", text)
        self.assertIn("wip", catalog.incomplete)
        self.assertNotIn("broken", catalog.modules)


class ResolveTests(support.TempDirTestCase):
    def catalog(self):
        root = self.tmp / "mods"
        write_module(root, "core", 'id = "core"\nname = "c"\nsummary = "s"\ntier = "core"\n')
        write_module(root, "a", 'id = "a"\nname = "a"\nsummary = "s"\nrequires = ["b"]\n')
        write_module(root, "b", 'id = "b"\nname = "b"\nsummary = "s"\nrequires = ["core"]\n')
        write_module(root, "c", 'id = "c"\nname = "c"\nsummary = "s"\nrequires = ["a", "b"]\n')
        write_module(root, "x", 'id = "x"\nname = "x"\nsummary = "s"\nrequires = ["y"]\n')
        write_module(root, "y", 'id = "y"\nname = "y"\nsummary = "s"\nrequires = ["z"]\n')
        write_module(root, "z", 'id = "z"\nname = "z"\nsummary = "s"\nrequires = ["x"]\n')
        write_module(root, "needs-ghost", 'id = "needs-ghost"\nname = "n"\nsummary = "s"\nrequires = ["ghost"]\n')
        (root / "wip").mkdir()
        return modules.discover(root)

    def test_dependencies_first_core_always(self):
        order = modules.resolve(["c"], self.catalog())
        self.assertEqual(order, ["core", "b", "a", "c"])

    def test_no_duplicates_and_requested_order(self):
        order = modules.resolve(["b", "a", "b"], self.catalog())
        self.assertEqual(order, ["core", "b", "a"])

    def test_unknown_module_with_suggestion(self):
        with self.assertRaises(ModuleError) as cm:
            modules.resolve(["bb"], self.catalog())
        self.assertIn("unknown module 'bb'", str(cm.exception))
        self.assertIn("'b'", cm.exception.hint)

    def test_unknown_dependency_names_requirer(self):
        with self.assertRaises(ModuleError) as cm:
            modules.resolve(["needs-ghost"], self.catalog())
        self.assertIn("required by 'needs-ghost'", str(cm.exception))

    def test_folder_without_manifest(self):
        with self.assertRaises(ModuleError) as cm:
            modules.resolve(["wip"], self.catalog())
        self.assertIn("no module.toml", cm.exception.hint)

    def test_cycle(self):
        with self.assertRaises(ModuleError) as cm:
            modules.resolve(["x"], self.catalog())
        self.assertIn("dependency cycle: x -> y -> z -> x", str(cm.exception))

    def test_dependents_are_transitive(self):
        cat = self.catalog()
        enabled = modules.resolve(["c"], cat)
        self.assertEqual(modules.dependents(["b"], enabled, cat), {"b": ["a", "c"]})
        self.assertEqual(modules.dependents(["c"], enabled, cat), {"c": []})

    def test_parse_id_list(self):
        self.assertEqual(modules.parse_id_list("a, b,,c;a"), ["a", "b", "c"])
        self.assertEqual(modules.parse_id_list(["a,b", "c"]), ["a", "b", "c"])

    def test_requested_from_config(self):
        self.assertEqual(modules.requested_from_config({"modules": {"enabled": ["a"]}}), ["a"])
        self.assertEqual(
            modules.requested_from_config({"uni_os": {"preset": "minimal"}, "obsidian": {"enabled": False}}),
            list(presets.MINIMAL),
        )
        self.assertIn("cockpit", modules.requested_from_config({}))  # standard + obsidian by default


class PresetTests(unittest.TestCase):
    def test_minimal(self):
        self.assertEqual(
            presets.preset_modules("minimal", obsidian=False),
            ["core", "student-model", "courses", "error-logs", "study-pages", "exercise-help"],
        )
        self.assertEqual(presets.preset_modules("minimal")[-1], "obsidian")

    def test_standard_and_full_build_on_each_other(self):
        minimal = presets.preset_modules("minimal")
        standard = presets.preset_modules("standard")
        full = presets.preset_modules("full")
        self.assertEqual(standard[: len(minimal)], minimal)
        self.assertEqual(full[: len(standard)], standard)
        for mid in ("progress", "planning", "check-in", "daily-prep", "lecture-rundowns", "quiz-coaching", "roles",
                    "scheduler-local", "heartbeat", "notifications", "resources", "handwritten-notes", "cockpit"):
            self.assertIn(mid, standard)
        for mid in ("inbox-sync", "experiments", "vault-watch", "course-files-fetch", "vm"):
            self.assertIn(mid, full)
            self.assertNotIn(mid, standard)

    def test_without_obsidian(self):
        ids = presets.preset_modules("full", obsidian=False)
        self.assertNotIn("obsidian", ids)
        self.assertNotIn("cockpit", ids)

    def test_every_preset_module_is_in_the_catalogue(self):
        for name in presets.PRESETS:
            for mid in presets.preset_modules(name):
                self.assertIn(mid, presets.CATALOGUE)
        self.assertEqual(len(presets.CATALOGUE), 25)

    def test_unknown_preset(self):
        with self.assertRaises(ValueError):
            presets.preset_modules("huge")

    def test_filter_for_os(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        keep, dropped = presets.filter_for_os(["core", "winaddon"], catalog, "linux")
        self.assertEqual((keep, dropped), (["core"], ["winaddon"]))
        self.assertEqual(presets.filter_for_os(["core", "winaddon"], catalog, "windows"), (["core", "winaddon"], []))


if __name__ == "__main__":
    unittest.main()
