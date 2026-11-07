"""Tests for modules/obsidian/scripts/merge_obsidian_config.py (stdlib unittest).

Run from the repo root:  python -m unittest discover -s modules/obsidian/tests
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_obsidian_config.py"
spec = importlib.util.spec_from_file_location("merge_obsidian_config", SCRIPT)
moc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(moc)

GRAPH_SPEC = {
    "search": "-path:_agent -path:_templates -path:reference",
    "groups": [
        {"folder": "A&D", "colour": "#1e66f5", "label": "AD"},
        {"folder": "My Course", "colour": "#40a02b", "label": "MC"},
        {"folder": "me", "colour": "#F6BF26", "label": "me"},
        {"end": True},
    ],
}
BOOKMARK_SPEC = {
    "items": [
        {"type": "file", "path": "Home.md", "title": "Home"},
        {"type": "file", "path": "missing.md", "title": "Missing"},
        {"type": "group", "title": "Courses", "items": [
            {"type": "file", "path": "A&D/ad.md", "title": "AD"},
            {"type": "file", "path": "courses-overview.md", "title": "All courses"},
        ]},
    ]
}
APP_SPEC = {
    "app": {"useMarkdownLinks": True, "newFileLocation": "folder", "newFileFolderPath": "inbox"},
    "ignore_filters": ["_agent/archive/", "/desktop\\.ini$/"],
    "templates": {"folder": "_templates"},
    "core_plugins": ["bases", "canvas"],
    "css_snippet": "uni-os",
}


def make_vault(root: Path) -> Path:
    vault = root / "vault"
    (vault / "_agent" / "obsidian").mkdir(parents=True)
    (vault / "A&D").mkdir()
    for rel in ("Home.md", "A&D/ad.md", "courses-overview.md"):
        (vault / rel).write_text("# x\n", encoding="utf-8")
    for name, data in (("graph-groups.json", GRAPH_SPEC), ("bookmarks.json", BOOKMARK_SPEC),
                       ("app-settings.json", APP_SPEC)):
        (vault / "_agent" / "obsidian" / name).write_text(json.dumps(data), encoding="utf-8")
    (vault / ".obsidian" / "snippets").mkdir(parents=True)
    (vault / ".obsidian" / "snippets" / "uni-os.css").write_text("/* */", encoding="utf-8")
    return vault


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = moc.main(list(args))
    return code, out.getvalue() + err.getvalue()


def read(vault: Path, name: str):
    return json.loads((vault / ".obsidian" / name).read_text(encoding="utf-8"))


class QueryTests(unittest.TestCase):
    def test_anchored_query_escapes(self):
        self.assertEqual(moc.folder_query("me"), "path:/^me\\//")
        self.assertEqual(moc.folder_query("A&D"), "path:/^A&D\\//")
        self.assertEqual(moc.folder_query("My Course (2)"), "path:/^My\\sCourse\\s\\(2\\)\\//")

    def test_hex_to_int(self):
        self.assertEqual(moc.hex_to_int("#3F51B5"), 4149685)
        with self.assertRaises(ValueError):
            moc.hex_to_int("blue")


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = make_vault(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_writes_nothing(self):
        code, out = run("--vault", str(self.vault))
        self.assertEqual(code, 0, out)
        self.assertIn("DRY RUN", out)
        self.assertFalse((self.vault / ".obsidian" / "graph.json").exists())
        self.assertFalse((self.vault / ".obsidian" / "app.json").exists())

    def test_apply_on_empty_config(self):
        code, out = run("--vault", str(self.vault), "--apply")
        self.assertEqual(code, 0, out)
        graph = read(self.vault, "graph.json")
        queries = [g["query"] for g in graph["colorGroups"]]
        self.assertEqual(queries, ["path:/^A&D\\//", "path:/^My\\sCourse\\//", "path:/^me\\//"])
        self.assertEqual(graph["colorGroups"][0]["color"], {"a": 1, "rgb": 0x1E66F5})
        self.assertEqual(graph["search"], GRAPH_SPEC["search"])
        marks = read(self.vault, "bookmarks.json")["items"]
        self.assertEqual(marks[0]["path"], "Home.md")
        self.assertEqual(marks[1]["type"], "group")
        self.assertEqual([i["path"] for i in marks[1]["items"]], ["A&D/ad.md", "courses-overview.md"])
        self.assertNotIn("missing.md", json.dumps(marks))
        app = read(self.vault, "app.json")
        self.assertEqual(app["newFileFolderPath"], "inbox")
        self.assertEqual(app["userIgnoreFilters"], ["_agent/archive/", "/desktop\\.ini$/"])
        self.assertEqual(read(self.vault, "templates.json")["folder"], "_templates")
        self.assertEqual(read(self.vault, "core-plugins.json"), {"bases": True, "canvas": True})
        self.assertEqual(read(self.vault, "appearance.json")["enabledCssSnippets"], ["uni-os"])

    def test_idempotent(self):
        run("--vault", str(self.vault), "--apply")
        code, out = run("--vault", str(self.vault), "--apply")
        self.assertEqual(code, 0, out)
        self.assertIn("0 change(s)", out)

    def test_keeps_user_choices_and_backs_up(self):
        obs = self.vault / ".obsidian"
        (obs / "app.json").write_text(json.dumps({"newFileLocation": "root", "userIgnoreFilters": ["mine/"]}),
                                      encoding="utf-8")
        (obs / "graph.json").write_text(json.dumps({"search": "mine", "colorGroups": [
            {"query": "path:/^me\\//", "color": {"a": 1, "rgb": 1}}]}), encoding="utf-8")
        (obs / "core-plugins.json").write_text(json.dumps({"bases": False}), encoding="utf-8")
        (obs / "bookmarks.json").write_text(json.dumps({"items": [{"type": "file", "path": "Home.md"}]}),
                                            encoding="utf-8")
        code, out = run("--vault", str(self.vault), "--apply")
        self.assertEqual(code, 0, out)
        app = read(self.vault, "app.json")
        self.assertEqual(app["newFileLocation"], "root")              # kept
        self.assertEqual(app["userIgnoreFilters"][0], "mine/")         # nothing removed
        self.assertIn("_agent/archive/", app["userIgnoreFilters"])     # added
        graph = read(self.vault, "graph.json")
        self.assertEqual(graph["search"], "mine")
        me = [g for g in graph["colorGroups"] if g["query"] == "path:/^me\\//"]
        self.assertEqual(me[0]["color"]["rgb"], 1)                     # kept
        self.assertFalse(read(self.vault, "core-plugins.json")["bases"])
        marks = read(self.vault, "bookmarks.json")["items"]
        self.assertEqual(sum(1 for m in marks if m.get("path") == "Home.md"), 1)  # no duplicate
        backups = list(obs.glob("uni-os-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "app.json").exists())
        self.assertIn("kept", out)

    def test_overwrite(self):
        obs = self.vault / ".obsidian"
        (obs / "app.json").write_text(json.dumps({"newFileLocation": "root"}), encoding="utf-8")
        run("--vault", str(self.vault), "--apply", "--overwrite")
        self.assertEqual(read(self.vault, "app.json")["newFileLocation"], "folder")

    def test_only_and_bad_args(self):
        code, _ = run("--vault", str(self.vault), "--apply", "--only", "graph")
        self.assertEqual(code, 0)
        self.assertTrue((self.vault / ".obsidian" / "graph.json").exists())
        self.assertFalse((self.vault / ".obsidian" / "app.json").exists())
        code, _ = run("--vault", str(self.vault), "--only", "nonsense")
        self.assertEqual(code, 2)
        code, _ = run("--vault", str(Path(self.tmp.name) / "nowhere"))
        self.assertEqual(code, 2)

    def test_unreadable_target_is_left_alone(self):
        obs = self.vault / ".obsidian"
        (obs / "graph.json").write_text("{not json", encoding="utf-8")
        code, out = run("--vault", str(self.vault), "--apply", "--only", "graph")
        self.assertEqual(code, 1)
        self.assertEqual((obs / "graph.json").read_text(encoding="utf-8"), "{not json")


if __name__ == "__main__":
    unittest.main()
