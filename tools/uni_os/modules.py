"""Module discovery and dependency resolution.

A module is a folder ``modules/<id>/`` with a ``module.toml`` manifest (format:
``docs/file-formats.md``, section "module.toml"). Folders
without ``module.toml`` are ignored by discovery (they may be work in progress)
but asking for them explicitly is an error.

``discover(dir)`` returns a :class:`Catalog`; ``resolve(requested, catalog)``
returns the requested ids plus all hard dependencies (``requires``), each after
its dependencies, ``core`` always first. Unknown ids and dependency cycles raise
:class:`~uni_os.errors.ModuleError` with an explanation.
"""

from __future__ import annotations

import difflib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import paths
from .errors import Issue, ModuleError

TIERS = ("core", "standard", "advanced", "addon")
OBSIDIAN_LEVELS = ("required", "recommended", "optional", "irrelevant")
OS_VALUES = ("any", "windows", "macos", "linux")
RUNTIMES = ("laptop", "cloud", "vm", "any")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

#: Top-level keys a module.toml may contain.
KNOWN_KEYS = {
    "id",
    "name",
    "tier",
    "summary",
    "requires",
    "recommends",
    "obsidian",
    "os",
    "runtime",
    "config_keys",
    "verbatim",
    "jobs",
    "roles",
    "skills",
    "defaults",
    "contracts",
    "folders",
}

#: Keys of one ``[[folders]]`` table.
FOLDER_KEYS = {"path", "each"}
_EACH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*(?:\.(?:[A-Za-z_][A-Za-z0-9_-]*|\d+))*$")

#: The module that is always installed (if it exists in the catalogue).
ALWAYS = "core"


@dataclass
class Module:
    """One parsed ``module.toml``."""

    id: str
    path: Path
    name: str = ""
    tier: str = "standard"
    summary: str = ""
    requires: list[str] = field(default_factory=list)
    recommends: list[str] = field(default_factory=list)
    obsidian: str = "optional"
    os: list[str] = field(default_factory=lambda: ["any"])
    runtime: list[str] = field(default_factory=lambda: ["any"])
    config_keys: list[str] = field(default_factory=list)
    verbatim: list[str] = field(default_factory=list)
    jobs: list[dict] = field(default_factory=list)
    roles: list[dict] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    defaults: dict = field(default_factory=dict)
    contracts: list[dict] = field(default_factory=list)
    folders: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def supports_os(self, os_name: str | None) -> bool:
        return not os_name or "any" in self.os or os_name in self.os

    def os_note(self, os_name: str | None) -> str | None:
        """Why this module does not fully work on a laptop running ``os_name`` (None = it does).

        ``os`` in module.toml names the laptop systems its laptop scripts support. A module
        that also runs elsewhere (``runtime`` beyond ``laptop``, e.g. course-files-fetch:
        role anywhere, pick-up task Windows-only) only loses its laptop part."""
        if self.supports_os(os_name):
            return None
        only = "/".join(self.os)
        if self.runtime == ["laptop"]:
            return f"'{self.id}' supports {only} only"
        return f"'{self.id}': its laptop part supports {only} only (the rest works on any system)"

    @property
    def job_ids(self) -> list[str]:
        return [j["id"] for j in self.jobs if isinstance(j, dict) and "id" in j]

    @property
    def role_ids(self) -> list[str]:
        return [r["id"] for r in self.roles if isinstance(r, dict) and "id" in r]

    @property
    def skill_ids(self) -> list[str]:
        return [s["id"] for s in self.skills if isinstance(s, dict) and "id" in s]

    def record(self) -> dict:
        """A plain dict for templates (``generated.modules``) and JSON output."""
        return {
            "id": self.id,
            "name": self.name or self.id,
            "tier": self.tier,
            "summary": self.summary,
            "requires": list(self.requires),
            "recommends": list(self.recommends),
            "obsidian": self.obsidian,
            "os": list(self.os),
            "runtime": list(self.runtime),
            "jobs": self.job_ids,
            "roles": self.role_ids,
            "skills": self.skill_ids,
            "config_keys": list(self.config_keys),
            "readme": f"modules/{self.id}/README.md",
        }


@dataclass
class Catalog:
    """All modules found in a modules folder plus problems found while reading them."""

    dir: Path
    modules: dict[str, Module] = field(default_factory=dict)
    problems: list[Issue] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)  # folders without module.toml

    def __contains__(self, mid: str) -> bool:
        return mid in self.modules

    def get(self, mid: str) -> Module | None:
        return self.modules.get(mid)

    def ids(self) -> list[str]:
        return sorted(self.modules, key=lambda m: (TIERS.index(self.modules[m].tier) if self.modules[m].tier in TIERS else 9, m))


def _str_list(value: Any, where: str, problems: list[Issue]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    problems.append(Issue("error", where, "must be a list of text values"))
    return []


def _table_list(value: Any, where: str, problems: list[Issue]) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(v, dict) for v in value):
        for entry in value:
            if not isinstance(entry.get("id"), str):
                problems.append(Issue("error", where, "every entry needs an id = \"...\""))
        return list(value)
    problems.append(Issue("error", where, "must be [[...]] tables with an id"))
    return []


def _folder_list(value: Any, where: str, problems: list[Issue]) -> list[dict]:
    """Validate ``[[folders]]``: ``path`` (a template) and optional ``each`` (a list key)."""
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        problems.append(Issue("error", where, "[[folders]] must be tables with a path = \"...\""))
        return []
    out = []
    for idx, entry in enumerate(value):
        here = f"{where} [[folders]] #{idx + 1}"
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            problems.append(Issue("error", here, "needs path = \"...\" (a vault-relative folder, may use {{course.<key>}} and {{item}})"))
            continue
        if path.strip().startswith("/") or re.match(r"^[A-Za-z]:", path.strip()):
            problems.append(Issue("error", here, f"path '{path}' must be relative to the vault"))
            continue
        each = entry.get("each")
        if each is not None and (not isinstance(each, str) or not _EACH_RE.match(each)):
            problems.append(Issue("error", here, f"each = {each!r} must name a list key, e.g. \"course.official_subfolders\""))
            continue
        for key in entry:
            if key not in FOLDER_KEYS:
                problems.append(Issue("warning", here, f"unknown key '{key}' (ignored; known: path, each)"))
        out.append({"path": path, **({"each": each} if each else {})})
    return out


def load_module(folder: Path) -> tuple[Module | None, list[Issue]]:
    """Parse ``<folder>/module.toml``; returns the module (or None) and problems."""
    problems: list[Issue] = []
    manifest = folder / "module.toml"
    where = paths.display(manifest)
    try:
        with open(manifest, "rb") as fh:
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        return None, [Issue("error", where, f"invalid TOML: {exc}")]
    except OSError as exc:
        return None, [Issue("error", where, f"cannot read: {exc}")]

    mid = raw.get("id")
    if not isinstance(mid, str) or not mid:
        problems.append(Issue("error", where, "missing id"))
        mid = folder.name
    elif mid != folder.name:
        problems.append(Issue("error", where, f"id '{mid}' must equal the folder name '{folder.name}'"))
    if not ID_RE.match(mid):
        problems.append(Issue("error", where, f"id '{mid}' must be lowercase-kebab-case"))
    for key in ("name", "summary"):
        if not isinstance(raw.get(key), str) or not raw.get(key):
            problems.append(Issue("warning", where, f"missing {key}"))
    tier = raw.get("tier", "standard")
    if tier not in TIERS:
        problems.append(Issue("error", where, f"tier '{tier}' must be one of {', '.join(TIERS)}"))
    obsidian = raw.get("obsidian", "optional")
    if obsidian not in OBSIDIAN_LEVELS:
        problems.append(Issue("error", where, f"obsidian '{obsidian}' must be one of {', '.join(OBSIDIAN_LEVELS)}"))
    os_list = _str_list(raw.get("os", ["any"]), f"{where}: os", problems) or ["any"]
    for value in os_list:
        if value not in OS_VALUES:
            problems.append(Issue("error", where, f"os '{value}' must be one of {', '.join(OS_VALUES)}"))
    runtime = _str_list(raw.get("runtime", ["any"]), f"{where}: runtime", problems) or ["any"]
    for value in runtime:
        if value not in RUNTIMES:
            problems.append(Issue("error", where, f"runtime '{value}' must be one of {', '.join(RUNTIMES)}"))
    defaults = raw.get("defaults", {})
    if not isinstance(defaults, dict):
        problems.append(Issue("error", where, "[defaults] must be a table"))
        defaults = {}
    contracts = raw.get("contracts", [])
    if not isinstance(contracts, list) or any(not isinstance(cn, dict) for cn in contracts):
        problems.append(Issue("error", where, "[[contracts]] must be tables"))
        contracts = []
    for key in raw:
        if key not in KNOWN_KEYS:
            problems.append(Issue("warning", where, f"unknown key '{key}' (ignored)"))

    module = Module(
        id=mid,
        path=folder,
        name=raw.get("name", mid) if isinstance(raw.get("name"), str) else mid,
        tier=tier if tier in TIERS else "standard",
        summary=raw.get("summary", "") if isinstance(raw.get("summary"), str) else "",
        requires=_str_list(raw.get("requires"), f"{where}: requires", problems),
        recommends=_str_list(raw.get("recommends"), f"{where}: recommends", problems),
        obsidian=obsidian if obsidian in OBSIDIAN_LEVELS else "optional",
        os=os_list,
        runtime=runtime,
        config_keys=_str_list(raw.get("config_keys"), f"{where}: config_keys", problems),
        verbatim=_str_list(raw.get("verbatim"), f"{where}: verbatim", problems),
        jobs=_table_list(raw.get("jobs"), f"{where}: jobs", problems),
        roles=_table_list(raw.get("roles"), f"{where}: roles", problems),
        skills=_table_list(raw.get("skills"), f"{where}: skills", problems),
        defaults=defaults,
        contracts=contracts,
        folders=_folder_list(raw.get("folders"), where, problems),
        raw=raw,
    )
    if mid in module.requires:
        problems.append(Issue("error", where, "a module cannot require itself"))

    # Declared jobs/roles/skills vs files on disk (warnings only).
    for kind, ids, finder in (
        ("jobs", module.job_ids, lambda i: (folder / "jobs" / i / "job.conf").is_file()),
        ("roles", module.role_ids, lambda i: (folder / "roles" / f"{i}.md").is_file()),
        ("skills", module.skill_ids, lambda i: (folder / "skills" / i / "SKILL.md").is_file()),
    ):
        for item in ids:
            if not finder(item):
                problems.append(Issue("warning", where, f"declares {kind[:-1]} '{item}' but its file is missing"))
    for sub, ids, kind in (("jobs", module.job_ids, "job"), ("skills", module.skill_ids, "skill")):
        base = folder / sub
        if base.is_dir():
            for child in sorted(base.iterdir()):
                if child.is_dir() and child.name not in ids:
                    problems.append(Issue("warning", where, f"{sub}/{child.name}/ exists but is not declared as [[{sub}]] id = \"{child.name}\""))
    roles_dir = folder / "roles"
    if roles_dir.is_dir():
        for child in sorted(roles_dir.glob("*.md")):
            if child.stem not in module.role_ids and child.stem.lower() != "readme":
                problems.append(Issue("warning", where, f"roles/{child.name} exists but is not declared as [[roles]] id = \"{child.stem}\""))
    return module, problems


def discover(modules_dir: str | Path | None = None) -> Catalog:
    """Read every ``<modules_dir>/*/module.toml``. Never raises for broken modules."""
    folder = paths.modules_dir(modules_dir)
    catalog = Catalog(dir=folder)
    if not folder.is_dir():
        catalog.problems.append(Issue("warning", paths.display(folder), "modules folder not found"))
        return catalog
    for child in sorted(folder.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        if not (child / "module.toml").is_file():
            catalog.incomplete.append(child.name)
            continue
        module, problems = load_module(child)
        catalog.problems.extend(problems)
        if module is not None:
            catalog.modules[module.id] = module
    return catalog


def _unknown(mid: str, catalog: Catalog, required_by: str | None) -> ModuleError:
    msg = f"unknown module '{mid}'"
    if required_by:
        msg += f" (required by '{required_by}')"
    hint = None
    if mid in catalog.incomplete:
        hint = f"modules/{mid}/ has no module.toml yet"
    else:
        close = difflib.get_close_matches(mid, list(catalog.modules), n=2)
        if close:
            hint = "did you mean " + " or ".join(f"'{c}'" for c in close) + "?"
        else:
            hint = "run `uni-os modules` to list the available modules"
    return ModuleError(msg, hint=hint)


def resolve(requested: Iterable[str], catalog: Catalog, *, include_core: bool = True) -> list[str]:
    """Requested modules plus their dependencies, dependencies first.

    ``core`` comes first whenever it exists in the catalogue (everything builds
    on the vault skeleton). Raises :class:`ModuleError` for unknown ids or cycles.
    """
    order: list[str] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(mid: str, chain: list[str]) -> None:
        if mid not in catalog.modules:
            raise _unknown(mid, catalog, chain[-1] if chain else None)
        st = state.get(mid)
        if st == 2:
            return
        if st == 1:
            cycle = chain[chain.index(mid):] + [mid]
            raise ModuleError("dependency cycle: " + " -> ".join(cycle), hint="fix the requires lists in these module.toml files")
        state[mid] = 1
        for dep in catalog.modules[mid].requires:
            visit(dep, chain + [mid])
        state[mid] = 2
        order.append(mid)

    roots = list(requested)
    if include_core and ALWAYS in catalog.modules:
        roots = [ALWAYS] + [m for m in roots if m != ALWAYS]
    for mid in roots:
        visit(mid, [])
    return order


def dependents(targets: Iterable[str], enabled: Iterable[str], catalog: Catalog) -> dict[str, list[str]]:
    """For each target id: the enabled modules that need it (directly or transitively)."""
    enabled = [m for m in enabled if m in catalog.modules]
    result: dict[str, list[str]] = {}
    for target in targets:
        needers: list[str] = []
        frontier = [target]
        while frontier:
            current = frontier.pop()
            for mid in enabled:
                if mid in needers or mid == target:
                    continue
                if current in catalog.modules[mid].requires:
                    needers.append(mid)
                    frontier.append(mid)
        result[target] = sorted(needers)
    return result


def uses_config_preset(raw: dict) -> bool:
    """True when the config names no modules and ``uni_os.preset`` decides instead."""
    from . import presets

    mods = raw.get("modules") if isinstance(raw.get("modules"), dict) else {}
    enabled = mods.get("enabled") if isinstance(mods, dict) else None
    if isinstance(enabled, list) and enabled:
        return False
    preset = (raw.get("uni_os") or {}).get("preset", "standard") if isinstance(raw.get("uni_os"), dict) else "standard"
    return preset in presets.PRESETS


def requested_from_config(raw: dict, *, obsidian: bool | None = None) -> list[str]:
    """The module ids a config asks for: ``modules.enabled``, or the preset if that is empty."""
    from . import presets

    mods = raw.get("modules") if isinstance(raw.get("modules"), dict) else {}
    enabled = mods.get("enabled") if isinstance(mods, dict) else None
    if isinstance(enabled, list) and enabled:
        return [m for m in enabled if isinstance(m, str)]
    preset = (raw.get("uni_os") or {}).get("preset", "standard") if isinstance(raw.get("uni_os"), dict) else "standard"
    if obsidian is None:
        obs = raw.get("obsidian") if isinstance(raw.get("obsidian"), dict) else {}
        obsidian = bool(obs.get("enabled", True))
    if preset in presets.PRESETS:
        return presets.preset_modules(preset, obsidian=obsidian)
    return [ALWAYS]


def parse_id_list(text: str | Iterable[str]) -> list[str]:
    """``"a, b,c"`` or ``["a", "b,c"]`` -> ``["a", "b", "c"]`` (order kept, duplicates removed)."""
    items = [text] if isinstance(text, str) else list(text)
    out: list[str] = []
    for item in items:
        for part in str(item).replace(";", ",").split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out
