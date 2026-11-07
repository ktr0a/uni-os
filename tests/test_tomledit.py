"""Tests for the comment-preserving edit of [modules] enabled."""

import tomllib
import unittest

import support  # noqa: F401
from uni_os import tomledit
from uni_os.errors import ConfigError

SAMPLE = """\
# My config
[student]
name = "Alex"   # keep me

[modules]
# what I use
enabled = [
  "core",   # always
  "progress",
] # trailing comment

[schedule]
prep_check = "07:30"
"""


class TomlEditTests(unittest.TestCase):
    def test_replace_multiline_array_keeps_comments(self):
        out = tomledit.set_modules_enabled(SAMPLE, ["core", "progress", "daily-prep", "heartbeat"])
        self.assertIn("# My config", out)
        self.assertIn('name = "Alex"   # keep me', out)
        self.assertIn("# what I use", out)
        self.assertIn("] # trailing comment", out)
        data = tomllib.loads(out)
        self.assertEqual(data["modules"]["enabled"], ["core", "progress", "daily-prep", "heartbeat"])
        self.assertEqual(data["schedule"]["prep_check"], "07:30")

    def test_short_list_inline(self):
        out = tomledit.set_modules_enabled(SAMPLE, ["core"])
        self.assertIn('enabled = ["core"] # trailing comment', out)

    def test_inline_array(self):
        text = '[modules]\nenabled = ["a", "b"]\n[x]\ny = 1\n'
        out = tomledit.set_modules_enabled(text, ["a"])
        self.assertEqual(out, '[modules]\nenabled = ["a"]\n[x]\ny = 1\n')

    def test_missing_key_is_inserted(self):
        out = tomledit.set_modules_enabled("[modules]\n[x]\ny = 1\n", ["a", "b"])
        self.assertEqual(tomllib.loads(out)["modules"]["enabled"], ["a", "b"])
        self.assertEqual(tomllib.loads(out)["x"]["y"], 1)

    def test_missing_table_is_appended(self):
        out = tomledit.set_modules_enabled('[student]\nname = "A"', ["a"])
        self.assertEqual(tomllib.loads(out), {"student": {"name": "A"}, "modules": {"enabled": ["a"]}})

    def test_strings_with_brackets_and_hashes(self):
        text = '[modules]\nenabled = ["a]#", \'b[\']\nnote = "x"\n'
        out = tomledit.set_modules_enabled(text, ["c"])
        self.assertEqual(tomllib.loads(out)["modules"], {"enabled": ["c"], "note": "x"})

    def test_unsupported_layout_raises(self):
        with self.assertRaises(ConfigError):
            tomledit.set_modules_enabled('modules = { enabled = ["a"] }\n', ["b"])

    def test_array_of_tables_after_modules(self):
        text = '[modules]\nenabled = []\n\n[[courses]]\nid = "x"\n'
        out = tomledit.set_modules_enabled(text, ["a"])
        data = tomllib.loads(out)
        self.assertEqual(data["modules"]["enabled"], ["a"])
        self.assertEqual(data["courses"], [{"id": "x"}])


if __name__ == "__main__":
    unittest.main()
