"""Tests for the CLI entry point: runs from any directory, command discovery, config command."""

import json
import os
import subprocess
import sys
import unittest

import support
from uni_os import cli


class EntryPointTests(unittest.TestCase):
    def run_script(self, *args, cwd):
        env = {k: v for k, v in os.environ.items() if not k.startswith("UNI_OS_")}
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(support.TOOLS / "uni_os.py"), *args],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=120,
        )

    def test_help_from_repo_root(self):
        proc = self.run_script("--help", cwd=support.REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for command in ("init", "render", "doctor", "enable", "disable", "modules", "week", "new-week", "config"):
            self.assertIn(command, proc.stdout)

    def test_help_from_another_directory(self):
        proc = self.run_script("--help", cwd=support.FIXTURES / "config")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage: uni-os", proc.stdout)

    def test_version(self):
        proc = self.run_script("--version", cwd=support.TESTS)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("uni-os 0.1.0", proc.stdout)

    def test_subcommand_help(self):
        for command in ("init", "render", "doctor", "new-week", "modules"):
            code, out, _ = support.run_cli(command, "--help")
            self.assertEqual(code, 0, command)
            self.assertIn("usage:", out)


class DiscoveryTests(unittest.TestCase):
    def test_commands_are_auto_discovered(self):
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        loaded = cli.load_commands(sub)
        for name in ("init", "render", "doctor", "enable", "modules", "week", "config", "jobs"):
            self.assertIn(name, loaded)
        self.assertNotIn("_shared", loaded)

    def test_no_command_prints_help(self):
        code, out, _ = support.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("usage: uni-os", out)

    def test_user_errors_have_no_traceback(self):
        code, _, err = support.run_cli("render", "--vault", str(support.TESTS / "nowhere"))
        self.assertEqual(code, 1)
        self.assertIn("uni-os: error:", err)
        self.assertNotIn("Traceback", err)


class ConfigCommandTests(support.TempDirTestCase):
    def test_get_show_keys_validate_path(self):
        self.init()
        _, out, _ = self.in_vault("config", "get", "schedule.week_page.time")
        self.assertEqual(out.strip(), "10:00")
        _, out, _ = self.in_vault("config", "get", "courses.algo.folder")
        self.assertEqual(out.strip(), "A&D")
        _, out, _ = self.in_vault("config", "get", "schedule.daily_prep")
        self.assertEqual(out.strip(), "17:30, 19:30")
        _, out, _ = self.in_vault("config", "get", "term", "--json")
        self.assertEqual(json.loads(out)["week0_monday"], "2026-09-14")
        _, _, err = self.in_vault("config", "get", "schedule.daily_perp", expect=1)
        self.assertIn("did you mean 'schedule.daily_prep'", err)
        _, out, _ = self.in_vault("config", "show")
        self.assertEqual(json.loads(out)["student"]["name"], "Alex Example")
        _, out, _ = self.in_vault("config", "keys", "--prefix", "schedule.week_page")
        self.assertIn("schedule.week_page.day", out)
        self.assertIn("# module:progress", out)
        _, out, _ = self.in_vault("config", "keys", "--prefix", "student.name")
        self.assertIn("# user", out)
        _, out, _ = self.in_vault("config", "validate")
        self.assertIn("0 error(s)", out)
        _, out, _ = self.in_vault("config", "path")
        self.assertTrue(out.strip().endswith("_agent/uni-os.toml"))

    def test_modules_preset_command(self):
        _, out, _ = self.cli("modules", "--preset", "standard", "--modules-dir", str(support.FIXTURE_MODULES))
        self.assertIn("preset standard", out)
        self.assertIn("not found in", out)  # the fixture catalogue lacks most modules
        _, out, _ = self.cli("modules", "--preset", "minimal", "--no-obsidian", "--json", "--modules-dir", str(support.FIXTURE_MODULES), expect=None)
        data = json.loads(out)
        self.assertEqual(data["modules"], ["core", "student-model", "courses", "error-logs", "study-pages", "exercise-help"])
        self.assertFalse(data["obsidian"])


if __name__ == "__main__":
    unittest.main()
