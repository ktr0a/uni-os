"""Tests for ``uni-os enable`` / ``uni-os disable`` edge cases (the main flows: test_install.py)."""

import tomllib

import support
from uni_os.context import open_session


class DisableLastModuleTests(support.TempDirTestCase):
    """An empty modules.enabled means "use uni_os.preset": disable must never write one."""

    def enabled_in_copy(self):
        return tomllib.loads(self.read("_agent/uni-os.toml"))["modules"]["enabled"]

    def test_disabling_every_listed_module_keeps_core(self):
        self.init()  # the fixture lists progress and study
        _, out, _ = self.in_vault("disable", "progress", "study")
        self.assertEqual(self.enabled_in_copy(), ["core"])
        self.assertIn("disabled: progress, study", out)
        session = open_session(vault=self.vault, modules_dir=support.FIXTURE_MODULES)
        self.assertEqual(session.requested, ["core"])
        self.assertEqual(session.enabled, ["core"])
        self.assertIn("No progress module.", self.read("README.md"))

    def test_preset_does_not_come_back(self):
        """With a preset named in the config, an empty list would install the preset again."""
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('preset = "custom"', 'preset = "minimal"'), encoding="utf-8")
        self.in_vault("disable", "progress", "study")
        session = open_session(vault=self.vault, modules_dir=support.FIXTURE_MODULES)
        self.assertEqual(session.enabled, ["core"], "the minimal preset must not be resolved again")

    def test_dry_run_uses_core_too(self):
        self.init()
        before = self.read("_agent/uni-os.toml")
        _, out, _ = self.in_vault("disable", "progress", "study", "--dry-run")
        self.assertIn("would set modules.enabled", out)
        self.assertIn("to: core\n", out)
        self.assertIn("modules (1): core", out)
        self.assertIn("would disable: progress, study", out)
        self.assertEqual(self.read("_agent/uni-os.toml"), before)

    def test_enable_after_disabling_everything(self):
        self.init()
        self.in_vault("disable", "progress", "study")
        self.in_vault("enable", "study")
        self.assertEqual(self.enabled_in_copy(), ["core", "study"])


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
