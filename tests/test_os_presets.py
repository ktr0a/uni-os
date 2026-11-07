"""Presets resolved for the laptop's system, and the OS warnings of init / enable / doctor.

A preset is a recommendation, so ``init --preset`` and ``modules --preset`` leave out the
modules whose laptop part does not support the laptop's system (``runtime.laptop_os``, else
this computer's) and say why. An explicit module list is installed as given, with a
warning; ``enable`` and ``doctor`` warn too, also for a module that runs elsewhere as well
(course-files-fetch: role anywhere, pick-up task Windows-only). Nothing is ever blocked.
"""

import shutil
import tomllib
import unittest
from unittest import mock

import support
from uni_os import modules, presets

#: The fixture catalogue's stand-in for a preset (the real presets name real modules).
FAKE_FULL = ["core", "progress", "study", "winaddon"]


class OsHelpersTests(unittest.TestCase):
    def test_current_os(self):
        self.assertEqual(presets.current_os("win32"), "windows")
        self.assertEqual(presets.current_os("cygwin"), "windows")
        self.assertEqual(presets.current_os("darwin"), "macos")
        self.assertEqual(presets.current_os("linux"), "linux")
        self.assertIsNone(presets.current_os("freebsd14"))
        self.assertIn(presets.current_os(), presets.OS_NAMES + (None,))

    def test_laptop_os_for(self):
        self.assertEqual(presets.laptop_os_for({"runtime": {"laptop_os": "linux"}}), ("linux", "runtime.laptop_os"))
        with mock.patch.object(presets, "current_os", return_value="macos"):
            os_name, source = presets.laptop_os_for({})
            self.assertEqual(os_name, "macos")
            self.assertIn("this computer", source)
            self.assertEqual(presets.laptop_os_for({}, detect=False), (None, ""))
            self.assertEqual(presets.laptop_os_for({"runtime": {"laptop_os": "beos"}}, detect=False), (None, ""))

    def test_os_note(self):
        laptop_only = modules.Module(id="watch", path=support.FIXTURE_MODULES, os=["windows"], runtime=["laptop"])
        both = modules.Module(id="fetch", path=support.FIXTURE_MODULES, os=["windows"], runtime=["laptop", "vm"])
        anywhere = modules.Module(id="core", path=support.FIXTURE_MODULES)
        self.assertIsNone(laptop_only.os_note("windows"))
        self.assertIsNone(anywhere.os_note("linux"))
        self.assertEqual(laptop_only.os_note("linux"), "'watch' supports windows only")
        self.assertIn("its laptop part supports windows only", both.os_note("macos"))

    def test_left_out_note(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        self.assertEqual(presets.left_out_note([], catalog, "linux", "runtime.laptop_os"), [])
        lines = presets.left_out_note(["winaddon"], catalog, "linux", "runtime.laptop_os")
        self.assertEqual(lines[0], "left out for linux (from runtime.laptop_os): winaddon")
        self.assertIn("'winaddon' supports windows only", lines[1])
        self.assertIn("--modules", lines[-1])


class OsPresetCliTests(support.TempDirTestCase):
    def set_laptop_os(self, value):
        text = self.config.read_text(encoding="utf-8").replace("[modules]", f'[runtime]\nlaptop_os = "{value}"\n\n[modules]')
        self.config.write_text(text, encoding="utf-8")

    def enabled_in_copy(self):
        return tomllib.loads(self.read("_agent/uni-os.toml"))["modules"]["enabled"]

    def test_init_preset_leaves_out_modules_for_the_configured_os(self):
        self.set_laptop_os("linux")
        with mock.patch.object(presets, "preset_modules", return_value=list(FAKE_FULL)):
            _, out, _ = self.init("--preset", "full")
        self.assertIn("left out for linux (from runtime.laptop_os): winaddon", out)
        self.assertIn("'winaddon' supports windows only", out)
        self.assertIn("modules (3): core, progress, study", out)
        self.assertEqual(self.enabled_in_copy(), ["core", "progress", "study"])
        self.assertFalse((self.vault / "_agent" / "jobs" / "win-watch").exists())

    def test_init_preset_keeps_everything_for_windows(self):
        self.set_laptop_os("windows")
        with mock.patch.object(presets, "preset_modules", return_value=list(FAKE_FULL)):
            _, out, _ = self.init("--preset", "full")
        self.assertNotIn("left out", out)
        self.assertIn("winaddon", self.enabled_in_copy())

    def test_init_preset_uses_this_computer_when_the_config_has_no_os(self):
        with mock.patch.object(presets, "preset_modules", return_value=list(FAKE_FULL)), \
                mock.patch.object(presets, "current_os", return_value="macos"):
            _, out, _ = self.init("--preset", "full")
        self.assertIn("left out for macos (from this computer (runtime.laptop_os is not set)): winaddon", out)
        self.assertNotIn("winaddon", self.enabled_in_copy())

    def test_explicit_modules_are_installed_with_a_warning(self):
        self.set_laptop_os("linux")
        _, out, _ = self.init("--modules", "winaddon")
        self.assertIn("warning: 'winaddon' supports windows only, but the laptop runs linux (from runtime.laptop_os)", out)
        self.assertIn("modules (3): core, progress, winaddon", out)
        self.assertNotIn("left out", out)

    def test_config_preset_uses_only_the_configured_os(self):
        """uni_os.preset with an empty modules.enabled: every machine resolves the same list."""
        text = self.config.read_text(encoding="utf-8").replace('enabled = ["progress", "study"]', "enabled = []")
        self.config.write_text(text.replace('preset = "custom"', 'preset = "full"'), encoding="utf-8")
        with mock.patch.object(presets, "preset_modules", return_value=list(FAKE_FULL)), \
                mock.patch.object(presets, "current_os", return_value="linux"):
            from uni_os.context import open_session

            kept = open_session(config=self.config, vault=self.vault, modules_dir=support.FIXTURE_MODULES)
            self.assertIn("winaddon", kept.enabled, "no runtime.laptop_os: this computer's system is not used")
            self.assertEqual(kept.preset_note(), [])
            self.set_laptop_os("linux")
            filtered = open_session(config=self.config, vault=self.vault, modules_dir=support.FIXTURE_MODULES)
            self.assertNotIn("winaddon", filtered.enabled)
            self.assertEqual(filtered.preset_dropped, ["winaddon"])

    def test_modules_preset_command_with_os(self):
        with mock.patch.object(presets, "preset_modules", return_value=list(FAKE_FULL)):
            _, out, _ = self.cli("modules", "--preset", "full", "--os", "linux", "--modules-dir", str(support.FIXTURE_MODULES))
            self.assertIn("left out for linux (from --os): winaddon", out)
            _, out, _ = self.cli("modules", "--preset", "full", "--os", "any", "--modules-dir", str(support.FIXTURE_MODULES))
            self.assertNotIn("left out", out)
            self.assertIn("winaddon", out)


class OsWarningTests(support.TempDirTestCase):
    """enable and doctor warn (never block), also when the module runs on the vm too."""

    def setUp(self):
        super().setUp()
        self.mods = self.tmp / "modules"
        shutil.copytree(support.FIXTURE_MODULES, self.mods)
        toml = self.mods / "winaddon" / "module.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('runtime = ["laptop"]', 'runtime = ["laptop", "vm"]'),
                        encoding="utf-8")
        text = self.config.read_text(encoding="utf-8").replace("[modules]", '[runtime]\nlaptop_os = "macos"\n\n[modules]')
        self.config.write_text(text, encoding="utf-8")

    def test_enable_and_doctor_warn_for_a_module_that_also_runs_on_the_vm(self):
        self.cli("init", "--config", str(self.config), "--vault", str(self.vault), "--modules-dir", str(self.mods))
        _, out, _ = self.cli("enable", "winaddon", "--vault", str(self.vault), "--modules-dir", str(self.mods))
        self.assertIn("warning: 'winaddon': its laptop part supports windows only", out)
        self.assertIn("runtime.laptop_os = macos", out)
        self.assertTrue((self.vault / "_agent" / "jobs" / "win-watch" / "job.conf").is_file(), "installed anyway")
        code, out, _ = self.cli("doctor", "--vault", str(self.vault), "--modules-dir", str(self.mods), expect=None)
        self.assertIn("'winaddon': its laptop part supports windows only", out)
        self.assertIn("but runtime.laptop_os is macos", out)
        self.assertEqual(code, 0, "a warning, not an error")
        code, _, _ = self.cli("doctor", "--strict", "--vault", str(self.vault), "--modules-dir", str(self.mods), expect=None)
        self.assertEqual(code, 1, "--strict counts the warning")


if __name__ == "__main__":
    unittest.main()
