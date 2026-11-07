"""Integration checks against the REAL module catalogue (``modules/``).

The other tool tests use the small fixture catalogue in ``tests/fixtures``. These read
the real ``modules/*/module.toml``, ``config/`` and ``examples/alex.toml`` (read-only)
and write only into temporary folders. They catch drift between the modules and the
shared config documents, and template errors in any module:

- every key a module defaults in ``[defaults]`` is shown in ``config/uni-os.example.toml``
  and ``examples/alex.toml`` and documented in ``config/schema.md``;
- the example config and Alex's config hold the same keys and validate cleanly;
- the "Module facts" table of ``modules/README.md`` has one row per module and matches
  each ``module.toml`` (requires without ``core``, recommends, obsidian, os, runtime, and
  the job, role and skill ids);
- rendering every module with Alex's config works and ``uni-os doctor --strict`` passes.

When a module adds a config key, add it to the three shared files (the schema row names
the module in "Used by").
"""

from __future__ import annotations

import os
import re
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import support

MODULES_DIR = support.REPO / "modules"
EXAMPLE = support.REPO / "config" / "uni-os.example.toml"
SCHEMA = support.REPO / "config" / "schema.md"
ALEX = support.REPO / "examples" / "alex.toml"


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and v:
            out.update(flat(v, key + "."))
        else:
            out[key] = v
    return out


def module_manifests() -> dict[str, dict]:
    out = {}
    for mt in sorted(MODULES_DIR.glob("*/module.toml")):
        data = tomllib.loads(mt.read_text(encoding="utf-8"))
        out[data["id"]] = data
    return out


def module_default_keys() -> dict[str, set[str]]:
    """``table.key`` (course keys as ``course.key``) -> ids of the modules defaulting it."""
    out: dict[str, set[str]] = {}
    for mid, data in module_manifests().items():
        for key in flat(data.get("defaults", {})):
            out.setdefault(key, set()).add(mid)
    return out


def schema_rows() -> dict[str, set[str]]:
    """Section ("agent", "course", "course.bonus", ...) -> documented relative keys."""
    rows: dict[str, set[str]] = {}
    section = None
    for line in SCHEMA.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,3} `(\[\[?)([a-z_.]+)(\]\]?)`", line)
        if m:
            name = m.group(2)
            section = {"courses": "course", "courses.bonus": "course.bonus", "courses.assessments": "course.assessments"}.get(name, name)
            continue
        if line.startswith("#"):
            section = None
            continue
        if section and line.startswith("| `"):
            rows.setdefault(section, set()).add(line.split("`")[1])
    return rows


def split_key(key: str) -> tuple[str, str]:
    if key.startswith("course.bonus."):
        return "course.bonus", key[len("course.bonus."):]
    table, rel = key.split(".", 1)
    return table, rel


def present_in_config(cfg: dict, key: str) -> bool:
    if key.startswith("course."):
        rel = key[len("course."):].split(".")
        for course in cfg.get("courses", []):
            cur = course
            ok = True
            for seg in rel:
                if not isinstance(cur, dict) or seg not in cur:
                    ok = False
                    break
                cur = cur[seg]
            if ok:
                return True
        return False
    cur = cfg
    for seg in key.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return False
        cur = cur[seg]
    return True


class ConfigDocsTests(unittest.TestCase):
    """The shared config documents list every module key."""

    @classmethod
    def setUpClass(cls):
        cls.keys = module_default_keys()
        cls.example = tomllib.loads(EXAMPLE.read_text(encoding="utf-8"))
        cls.alex = tomllib.loads(ALEX.read_text(encoding="utf-8"))
        cls.rows = schema_rows()

    def test_every_module_key_is_in_the_example_configs(self):
        from uni_os import config

        aliases = set(config.STUCK_ALIASES)
        for name, cfg in (("config/uni-os.example.toml", self.example), ("examples/alex.toml", self.alex)):
            missing = sorted(f"{k} ({', '.join(sorted(m))})" for k, m in self.keys.items()
                             if k not in aliases and not present_in_config(cfg, k))
            self.assertEqual(missing, [], f"keys missing from {name}")

    def test_old_aliases_are_documented_but_not_in_the_examples(self):
        """The four stuck-note aliases default to 0 (= notify.inbox_stale_hours[_taps]); the
        examples leave them out so there is one threshold to set."""
        from uni_os import config

        for alias in config.STUCK_ALIASES:
            self.assertIn(alias, self.keys, f"{alias} is no longer a module default: drop it from STUCK_ALIASES")
            table, rel = split_key(alias)
            self.assertIn(rel, self.rows.get(table, set()), f"{alias} must stay documented in config/schema.md")
            for name, cfg in (("config/uni-os.example.toml", self.example), ("examples/alex.toml", self.alex)):
                self.assertFalse(present_in_config(cfg, alias), f"{name} sets the old alias {alias}")

    def test_every_module_key_is_documented_in_the_schema(self):
        missing = []
        for key, mods in sorted(self.keys.items()):
            table, rel = split_key(key)
            parts = rel.split(".")
            documented = self.rows.get(table, set())
            if not any(".".join(parts[:i]) in documented for i in range(1, len(parts) + 1)):
                missing.append(f"{key} ({', '.join(sorted(mods))})")
        self.assertEqual(missing, [], "keys missing from config/schema.md")

    def test_example_and_alex_hold_the_same_keys(self):
        ignore = {"uni_os.preset", "modules.enabled"}
        a = {k: v for k, v in flat(self.example).items() if k not in ignore}
        b = {k: v for k, v in flat(self.alex).items() if k not in ignore}
        self.assertEqual(sorted(set(a) ^ set(b)), [])
        self.assertEqual(a, b, "config/uni-os.example.toml and examples/alex.toml should hold the same values")

    def test_example_configs_validate_cleanly(self):
        for path in (EXAMPLE, ALEX):
            code, out, err = support.run_cli("config", "validate", "--config", str(path), "--modules-dir", str(MODULES_DIR))
            self.assertEqual(code, 0, out + err)
            self.assertIn("0 error(s), 0 warning(s)", out, out + err)

    def test_example_configs_validate_cleanly_with_fewer_modules(self):
        # The module keys of the example configs hold their module defaults, so a student who
        # copies the example and enables fewer modules gets no "is set, but its module ... is
        # not enabled" warnings (and every preset renders to doctor --strict = 0 warnings).
        for path in (EXAMPLE, ALEX):
            text = path.read_text(encoding="utf-8")
            trimmed, n = re.subn(r"(?ms)^enabled = \[.*?^\]", 'enabled = ["core"]', text, count=1)
            self.assertEqual(n, 1, f"{path.name}: no [modules] enabled list found")
            with tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp) / "core-only.toml"
                cfg.write_text(trimmed, encoding="utf-8")
                code, out, err = support.run_cli("config", "validate", "--config", str(cfg), "--modules-dir", str(MODULES_DIR))
            self.assertEqual(code, 0, out + err)
            self.assertIn("0 error(s), 0 warning(s)", out, f"{path.name} with only core enabled:\n{out}{err}")


def facts_table_rows() -> list[list[str]]:
    """The module rows of the "Module facts" table in ``modules/README.md``, as cell lists."""
    text = (MODULES_DIR / "README.md").read_text(encoding="utf-8")
    if "\n## Module facts" not in text:
        raise AssertionError('modules/README.md has no "## Module facts" section')
    section = text.split("\n## Module facts", 1)[1].split("\n## ", 1)[0]
    return [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in section.splitlines() if line.startswith("| [`")]


def cell_list(cell: str) -> list[str]:
    """A facts-table cell such as ``| `a`, `b` |`` or ``| laptop, vm |`` -> ``["a", "b"]``; ``-`` -> ``[]``."""
    cell = cell.strip()
    if cell in ("", "-"):
        return []
    return [x.strip().strip("`") for x in cell.split(",")]


class ModuleFactsTableTests(unittest.TestCase):
    """The "Module facts" table of modules/README.md matches every module.toml."""

    COLUMNS = ("requires", "recommends", "obsidian", "os", "runtime", "jobs", "roles", "skills")

    @classmethod
    def setUpClass(cls):
        cls.manifests = module_manifests()
        cls.rows = facts_table_rows()

    def test_every_module_has_exactly_one_row(self):
        ids = []
        for cells in self.rows:
            m = re.match(r"\[`([^`]+)`\]\(([^)]+)\)$", cells[0])
            self.assertIsNotNone(m, f"first cell is not [`id`](id/README.md): {cells[0]}")
            ids.append(m.group(1))
            self.assertEqual(m.group(2), f"{m.group(1)}/README.md", f"row {m.group(1)} links elsewhere")
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(dupes, [], "modules with more than one row")
        self.assertEqual(sorted(set(self.manifests) - set(ids)), [], "modules missing from the table")
        self.assertEqual(sorted(set(ids) - set(self.manifests)), [], "rows for modules that don't exist")

    def test_rows_match_module_toml(self):
        bad = []
        for cells in self.rows:
            mid = re.match(r"\[`([^`]+)`\]", cells[0]).group(1)
            data = self.manifests.get(mid)
            if data is None:
                continue  # reported by test_every_module_has_exactly_one_row
            if len(cells) != 1 + len(self.COLUMNS):
                bad.append(f"{mid}: {len(cells)} cells, expected {1 + len(self.COLUMNS)}")
                continue
            got = dict(zip(self.COLUMNS, cells[1:]))
            want = {
                "requires": [r for r in data.get("requires", []) if r != "core"],
                "recommends": data.get("recommends", []),
                "obsidian": data.get("obsidian", ""),
                "os": data.get("os", []),
                "runtime": data.get("runtime", []),
                "jobs": [j["id"] for j in data.get("jobs", [])],
                "roles": [r["id"] for r in data.get("roles", [])],
                "skills": [s["id"] for s in data.get("skills", [])],
            }
            for col in self.COLUMNS:
                if isinstance(want[col], list):
                    have, need = sorted(cell_list(got[col])), sorted(want[col])
                else:
                    have, need = got[col], want[col]
                if have != need:
                    bad.append(f"{mid}.{col}: table {have} vs module.toml {need}")
        self.assertEqual(bad, [], "modules/README.md 'Module facts' disagrees with module.toml")

    def test_cell_list_parses_table_cells(self):
        self.assertEqual(cell_list("-"), [])
        self.assertEqual(cell_list(" "), [])
        self.assertEqual(cell_list("`courses`, `progress`"), ["courses", "progress"])
        self.assertEqual(cell_list("laptop, cloud, vm"), ["laptop", "cloud", "vm"])


class FullRenderTests(support.TempDirTestCase):
    """Every real module renders with Alex's config, and the result passes doctor."""

    def test_render_all_modules_and_doctor(self):
        home = self.tmp / "home"
        home.mkdir()
        env = {"HOME": str(home), "USERPROFILE": str(home)}
        with mock.patch.dict(os.environ, env):
            all_ids = ",".join(sorted(module_manifests()))
            self.cli("init", "--config", str(ALEX), "--vault", str(self.vault), "--modules-dir", str(MODULES_DIR),
                     "--modules", all_ids, "--date", "2026-11-07")
            code, out, err = self.cli("doctor", "--vault", str(self.vault), "--modules-dir", str(MODULES_DIR), "--strict", expect=None)
            self.assertEqual(code, 0, out + err)
            code, out, err = self.cli("jobs", "--vault", str(self.vault), "--modules-dir", str(MODULES_DIR))
            self.assertIn("daily-study-prep", out)
            # nothing rendered as a Python value or left as an install-time placeholder
            roots = r"(student|university|term|paths|storage|obsidian|agent|study|courses|course|schedule|notify|calendar|runtime|vm|cockpit|modules|uni_os|generated|item|error_log)"
            leftover = re.compile(r"\{\{\s*[#/]?" + roots + r"\b")
            bad = []
            for path in sorted(Path(self.vault).rglob("*")):
                if not path.is_file() or path.suffix.lower() not in (".md", ".conf", ".css", ".base", ".canvas", ".json"):
                    continue
                if path.name in (".uni-os-manifest.json",):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if leftover.search(text):
                    bad.append(path.relative_to(self.vault).as_posix())
            self.assertEqual(bad, [], "unrendered install-time placeholders")


class LineEndingTests(unittest.TestCase):
    """.gitattributes and the installer agree on which files keep CRLF."""

    def test_gitattributes_matches_the_installer(self):
        from uni_os import install

        rules = {}
        for line in (support.REPO / ".gitattributes").read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                pattern, *attrs = line.split()
                rules[pattern] = attrs
        self.assertEqual(rules.get("*"), ["text=auto", "eol=lf"])
        for ext in sorted(install.KEEP_LINE_ENDINGS):
            self.assertEqual(rules.get("*" + ext), ["text", "eol=crlf"], f"*{ext} must be checked out with CRLF")
        crlf = {p[1:] for p, attrs in rules.items() if "eol=crlf" in attrs}
        self.assertEqual(crlf, set(install.KEEP_LINE_ENDINGS), "every CRLF type keeps its line endings when rendered")
        self.assertIn("binary", rules.get("*.png", []))


if __name__ == "__main__":
    unittest.main()
