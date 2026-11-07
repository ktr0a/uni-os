"""Render module templates into a vault (used by init, render, enable, disable).

Two phases, so nothing is written when any template fails:

1. :func:`build_plan` renders every file of every enabled module in memory.
   Sources and targets (``docs/file-formats.md``, section "Template language", "Paths"):

   ==========================================  =========================================
   ``modules/<id>/vault/<path>``               ``<vault>/<path>``
   ``modules/<id>/jobs/<job>/<file>``          ``<vault>/_agent/jobs/<job>/<file>``
   ``modules/<id>/roles/<role>.md``            ``<vault>/_agent/roles/<role>.md``
   ``modules/<id>/skills/<skill>/<file>``      ``<vault>/_agent/skills/<skill>/<file>``
   ==========================================  =========================================

   A path containing ``{{course.`` is produced once per course; a path containing
   ``{{error_log.`` once per course *and* error-log stream (``error_log`` binds
   ``stream``, ``file``, ``path``, ``title``). Files matching the module's
   ``verbatim`` globs, and binary files, are copied unchanged. A ``.gitkeep`` or
   ``.keep`` file only creates its folder; so does each ``[[folders]]`` entry of a
   ``module.toml`` (a path template, optionally expanded once per item of a list
   key named by ``each``, e.g. one folder per ``course.official_subfolders`` entry;
   see :func:`_plan_folders`). A leading ``_agent/`` or ``inbox/`` in a
   vault path follows ``paths.agent_dir`` / ``paths.inbox``. Template text is
   written with ``\\n`` line endings (except ``.bat .cmd .vbs .ps1 .psm1 .psd1``, which
   keep the CRLF that ``.gitattributes`` gives them in every checkout), so output is
   identical on every OS.

2. :func:`apply_plan` writes files according to the mode:

   - ``init``: create missing files; never overwrite an existing one (``--force`` does).
   - ``render``: create new files; update files whose hash still matches the
     manifest (untouched by you); keep files you edited, but refresh their
     generated regions (``<!-- uni-os:begin NAME -->`` ... ``<!-- uni-os:end NAME -->``,
     :mod:`uni_os.regions`) when the file and the fresh rendering have the same
     well-formed regions (otherwise the file is skipped and the reason reported);
     do not recreate files or folders you deleted (``init`` restores them).

   New folders are created in both modes; only ``init`` recreates deleted ones.
   Nothing is ever deleted. Files in the manifest that the plan no longer
   produces (module disabled, course removed) are reported as orphaned.

   A file or folder that cannot be written (``OSError``: no permission, a file
   where a folder should be, a full disk) does not stop the run: it is listed in
   ``Report.failed`` (and, with a closing hint, in ``Report.conflicts``, which the
   commands print and turn into exit code 1) and left out of the manifest, while
   everything else is written and recorded, so the manifest and ``uni-os.json``
   are still saved for what was written.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import frontmatter, jobs, paths, regions, template
from .errors import TemplateError, UniOsError
from .manifest import Manifest

JUNK_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_DIRS = {"__pycache__", ".git", "node_modules", ".pytest_cache"}
DIR_MARKERS = {".gitkeep", ".keep"}
#: Windows script types keep the line endings of the checkout (CRLF, see .gitattributes).
KEEP_LINE_ENDINGS = {".bat", ".cmd", ".vbs", ".ps1", ".psm1", ".psd1"}
AREAS = ("vault", "jobs", "roles", "skills")


def glob_to_regex(pattern: str) -> re.Pattern:
    """Translate a glob with ``**`` support to a regex over POSIX paths."""
    pattern = paths.posix(pattern) if pattern not in ("", "**") else pattern
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(rel: str, patterns: list[str]) -> bool:
    return any(glob_to_regex(p).match(rel) for p in patterns)


def is_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    try:
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


@dataclass
class Item:
    """One planned output: a file (``template``/``verbatim``) or a folder (``dir``)."""

    target: str
    module: str
    source: str
    kind: str
    data: bytes | None = None

    @property
    def sha256(self) -> str | None:
        return paths.sha256_bytes(self.data) if self.data is not None else None


@dataclass
class Plan:
    items: list[Item] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def files(self) -> list[Item]:
        return [i for i in self.items if i.kind != "dir"]

    @property
    def dirs(self) -> list[Item]:
        return [i for i in self.items if i.kind == "dir"]

    def targets(self) -> set[str]:
        return {i.target for i in self.files}


def module_sources(module) -> list[tuple[str, str, Path]]:
    """``(area, path_within_area, absolute_path)`` for every installable file of a module."""
    out = []
    for area in AREAS:
        base = Path(module.path) / area
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in JUNK_DIRS)
            for name in sorted(filenames):
                if name in JUNK_FILES or name.endswith((".pyc", ".uni-os-tmp")):
                    continue
                full = Path(dirpath) / name
                out.append((area, full.relative_to(base).as_posix(), full))
    return out


def _target_prefix(area: str, agent_dir: str) -> str:
    return "" if area == "vault" else f"{agent_dir}/{area}"


def _remap(rel: str, agent_dir: str, inbox: str) -> str:
    if agent_dir != paths.DEFAULT_AGENT_DIR and (rel == "_agent" or rel.startswith("_agent/")):
        rel = agent_dir + rel[len("_agent"):]
    if inbox != "inbox" and (rel == "inbox" or rel.startswith("inbox/")):
        rel = inbox + rel[len("inbox"):]
    return rel


def _bindings_for(path_text: str, cfg: dict) -> list[dict]:
    courses = [c for c in cfg.get("courses") or [] if isinstance(c, dict)]
    if template.expands_per_error_log(path_text):
        return [{"course": c, "error_log": log} for c in courses for log in c.get("error_logs") or []]
    if template.expands_per_course(path_text):
        return [{"course": c} for c in courses]
    return [{}]


def build_plan(catalog, enabled: list[str], cfg: dict, context: dict) -> Plan:
    """Render every installable file of the enabled modules in memory."""
    plan = Plan()
    agent_dir = (cfg.get("paths") or {}).get("agent_dir", paths.DEFAULT_AGENT_DIR)
    inbox = (cfg.get("paths") or {}).get("inbox", "inbox")
    known_modules = set(catalog.modules) | set(_catalogue_ids())
    owners: dict[str, str] = {}
    dir_seen: set[str] = set()

    for mid in enabled:
        module = catalog.modules[mid]
        for area, rel_area, full in module_sources(module):
            source_rel = f"{mid}/{area}/{rel_area}"
            display = f"modules/{source_rel}"
            name = full.name
            is_marker = name in DIR_MARKERS
            path_text = rel_area.rsplit("/", 1)[0] if is_marker and "/" in rel_area else ("" if is_marker else rel_area)
            try:
                raw = full.read_bytes()
            except OSError as exc:
                plan.errors.append(f"{display}: cannot read: {exc}")
                continue
            verbatim = matches_any(f"{area}/{rel_area}", module.verbatim) or is_binary(raw)
            try:
                path_tpl = template.compile(path_text, f"{display} (file path)") if path_text else None
                content_tpl = None
                if not verbatim and not is_marker:
                    text = raw.decode("utf-8")
                    if full.suffix.lower() not in KEEP_LINE_ENDINGS:
                        text = text.replace("\r\n", "\n")
                    content_tpl = template.compile(text, display)
            except TemplateError as exc:
                plan.errors.append(str(exc))
                continue

            for binding in _bindings_for(path_text, cfg):
                try:
                    rel_target = path_tpl.render(context, bindings=binding) if path_tpl else ""
                except TemplateError as exc:
                    plan.errors.append(str(exc))
                    break
                prefix = _target_prefix(area, agent_dir)
                target = paths.posix("/".join(p for p in (prefix, rel_target) if p))
                if area == "vault":
                    target = _remap(target, agent_dir, inbox)
                if not target:
                    if is_marker:
                        continue
                    plan.errors.append(f"{display}: renders to an empty path")
                    continue
                problem = paths.check_relpath(target)
                if problem:
                    plan.errors.append(f"{display}: target path '{target}' is not valid: {problem}")
                    continue
                if is_marker:
                    if target not in dir_seen:
                        dir_seen.add(target)
                        plan.items.append(Item(target, mid, source_rel, "dir"))
                    continue
                if target in owners:
                    plan.errors.append(
                        f"{display}: renders to '{target}', which {owners[target]} also produces (one owner per file)"
                    )
                    continue
                if verbatim:
                    data = raw
                    kind = "verbatim"
                else:
                    try:
                        data = content_tpl.render(
                            context, bindings=binding, known_modules=known_modules, warnings=plan.warnings
                        ).encode("utf-8")
                    except TemplateError as exc:
                        plan.errors.append(str(exc))
                        continue
                    kind = "template"
                owners[target] = f"modules/{source_rel}"
                plan.items.append(Item(target, mid, source_rel, kind, data))
        _plan_folders(plan, module, cfg, context, agent_dir, inbox, dir_seen, known_modules)
    # De-duplicate warnings, keep order.
    plan.warnings = list(dict.fromkeys(plan.warnings))
    return plan


def _plan_folders(plan: Plan, module, cfg: dict, context: dict, agent_dir: str, inbox: str, dir_seen: set, known_modules) -> None:
    """Add the module's ``[[folders]]`` to the plan (empty folders, created and recorded).

    ``path`` is a template. If it (or ``each``) refers to ``course.``, it is produced
    once per course (``error_log.``: per course and error-log stream). ``each`` names a
    list key; every item gives one folder, bound as ``item`` (with ``@index``,
    ``@first``, ``@last``). Empty items are skipped. Folders are shared: two modules
    may ask for the same folder (the first one records it).
    """
    for idx, spec in enumerate(module.folders):
        display = f"modules/{module.id}/module.toml [[folders]] #{idx + 1}"
        source = f"{module.id}/module.toml#folders/{idx + 1}"
        path_text = spec["path"]
        each = spec.get("each")
        try:
            tpl = template.compile(path_text, f"{display} (path)")
        except TemplateError as exc:
            plan.errors.append(str(exc))
            continue
        probe = path_text + (f"{{{{{each}}}}}" if each else "")
        for binding in _bindings_for(probe, cfg):
            items: list[dict] = [binding]
            if each:
                try:
                    values = template.lookup(each, context, bindings=binding, filename=f"{display} (each)")
                except TemplateError as exc:
                    plan.errors.append(str(exc))
                    break
                if not isinstance(values, (list, tuple)):
                    plan.errors.append(f"{display}: each = \"{each}\" must name a list, but it is {type(values).__name__}")
                    break
                values = [v for v in values if v not in (None, "")]
                last = len(values) - 1
                items = [dict(binding, item=v, **{"@index": i, "@first": i == 0, "@last": i == last}) for i, v in enumerate(values)]
            for bound in items:
                try:
                    rel = tpl.render(context, bindings=bound, known_modules=known_modules, warnings=plan.warnings)
                except TemplateError as exc:
                    plan.errors.append(str(exc))
                    break
                target = _remap(paths.posix(rel.strip()), agent_dir, inbox)
                problem = paths.check_relpath(target)
                if problem:
                    plan.errors.append(f"{display}: folder '{rel}' is not a valid vault path: {problem}")
                    continue
                if target not in dir_seen:
                    dir_seen.add(target)
                    plan.items.append(Item(target, module.id, source, "dir"))


def _catalogue_ids() -> list[str]:
    from .presets import CATALOGUE

    return list(CATALOGUE)


# --------------------------------------------------------------------------- generated.* info


def generated_info(catalog, enabled: list[str], context: dict) -> dict:
    """``generated.modules``, ``generated.roles``, ``generated.jobs``, ``generated.skills``.

    Lists of the enabled modules and of their roles, jobs and skills, so core
    templates can build registries and routing tables (system handbook, roles
    README, where-to-find-what) from what is actually installed.
    """
    agent_dir = (context.get("paths") or {}).get("agent_dir", paths.DEFAULT_AGENT_DIR)
    mods, roles, job_list, skills = [], [], [], []

    def _render_value(value, filename):
        if isinstance(value, str) and "{{" in value:
            try:
                return template.render(value, context, filename=filename)
            except TemplateError:
                return value
        return value

    for mid in enabled:
        module = catalog.modules[mid]
        mods.append(module.record())
        declared_roles = {r["id"]: r for r in module.roles if isinstance(r, dict) and "id" in r}
        roles_dir = Path(module.path) / "roles"
        role_files = sorted(roles_dir.glob("*.md")) if roles_dir.is_dir() else []
        for rf in role_files:
            rid = rf.stem
            try:
                fm = frontmatter.parse(rf.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                fm = {}
            decl = declared_roles.get(rid, {})
            roles.append(
                {
                    "id": rid,
                    "module": mid,
                    "title": _render_value(decl.get("title") or fm.get("title") or rid, str(rf)),
                    "runtime": decl.get("runtime") or fm.get("runtime") or "any",
                    "file": f"{agent_dir}/roles/{rid}.md",
                }
            )
        jobs_root = Path(module.path) / "jobs"
        if jobs_root.is_dir():
            for jd in sorted(p for p in jobs_root.iterdir() if p.is_dir() and (p / "job.conf").is_file()):
                try:
                    text = (jd / "job.conf").read_text(encoding="utf-8")
                    try:
                        text = template.render(text, context, filename=str(jd / "job.conf"))
                    except TemplateError:
                        pass
                    conf = dict(jobs.JOB_DEFAULTS)
                    conf.update(jobs.parse_conf_text(text)[0])
                except (OSError, UnicodeDecodeError, jobs.ConfParseError):
                    conf = dict(jobs.JOB_DEFAULTS)
                job_list.append(
                    {
                        "id": jd.name,
                        "module": mid,
                        "title": conf.get("TITLE") or jd.name,
                        "kind": conf.get("KIND"),
                        "slots": jobs.split_list(conf.get("SLOTS", "")),
                        "every_min": (conf.get("EVERY_MIN") or "").strip(),
                        "days": jobs.expand_days(conf.get("DAYS", "")),
                        "session": conf.get("SESSION"),
                        "runtime": conf.get("RUNTIME"),
                        "default_mode": conf.get("DEFAULT_MODE"),
                        "dir": f"{agent_dir}/jobs/{jd.name}",
                    }
                )
        skills_root = Path(module.path) / "skills"
        if skills_root.is_dir():
            for sd in sorted(p for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
                try:
                    fm = frontmatter.parse((sd / "SKILL.md").read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError):
                    fm = {}
                skills.append(
                    {
                        "id": sd.name,
                        "module": mid,
                        "name": _render_value(fm.get("name") or sd.name, str(sd)),
                        "description": _render_value(fm.get("description") or "", str(sd)),
                        "dir": f"{agent_dir}/skills/{sd.name}",
                    }
                )
    return {"modules": mods, "roles": roles, "jobs": job_list, "skills": skills}


# --------------------------------------------------------------------------- applying


@dataclass
class Report:
    created: list[Item] = field(default_factory=list)
    updated: list[Item] = field(default_factory=list)
    overwritten: list[Item] = field(default_factory=list)
    unchanged: list[Item] = field(default_factory=list)
    skipped_exists: list[Item] = field(default_factory=list)  # exists, not ours / differs (init)
    kept_modified: list[Item] = field(default_factory=list)  # ours, but you edited it
    missing: list[Item] = field(default_factory=list)  # ours, you deleted it (render does not restore)
    merged: list[tuple[Item, list[str]]] = field(default_factory=list)  # edited; generated regions refreshed
    regions_current: list[Item] = field(default_factory=list)  # edited; generated regions already current
    regions_skipped: list[tuple[Item, str]] = field(default_factory=list)  # edited; regions not refreshable (why)
    dirs_created: list[str] = field(default_factory=list)
    dirs_missing: list[str] = field(default_factory=list)  # ours, you deleted it (render does not restore)
    orphaned: list[tuple[str, str]] = field(default_factory=list)  # (path, module)
    conflicts: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (path, why): could not be written

    @property
    def written(self) -> list[Item]:
        return self.created + self.updated + self.overwritten + [i for i, _ in self.merged]

    def fail(self, path: str, exc: OSError) -> None:
        """Record a file or folder that could not be written.

        It also goes to ``conflicts``: those are printed and make the command exit 1.
        """
        why = os_error_text(exc)
        self.failed.append((path, why))
        self.conflicts.append(f"{path}: could not be written: {why}")


def os_error_text(exc: OSError) -> str:
    """One line for an ``OSError``: ``Permission denied: G:/My Drive/Uni/x.md``."""
    reason = exc.strerror or exc.__class__.__name__
    name = exc.filename
    if name is None:
        return str(exc) or reason
    where = Path(os.fsdecode(name)).as_posix() if isinstance(name, (str, bytes, os.PathLike)) else str(name)
    return f"{reason}: {where}"


def merge_regions(target: Path, item: Item) -> regions.MergeResult | None:
    """Region merge of an edited file with its fresh rendering.

    ``None`` when the fresh rendering has no generated regions (nothing to merge:
    the file is simply kept). Otherwise a :class:`~uni_os.regions.MergeResult`.
    """
    if item.kind != "template" or item.data is None:
        return None
    fresh = item.data.decode("utf-8")
    if not regions.has_regions(fresh):
        return None
    try:
        current = target.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return regions.MergeResult(problem="the file is not UTF-8 text")
    except OSError as exc:
        return regions.MergeResult(problem=f"cannot read it: {exc}")
    return regions.merge(current, fresh)


def apply_plan(
    vault: Path,
    plan: Plan,
    manifest: Manifest,
    *,
    mode: str,
    force: bool = False,
    dry_run: bool = False,
) -> Report:
    """Write the plan into the vault (see module docstring for the rules)."""
    if mode not in ("init", "render"):
        raise ValueError(mode)
    report = Report()
    vault = Path(vault)

    for item in plan.dirs:
        folder = paths.vault_file(vault, item.target)
        if folder.is_file():
            report.conflicts.append(f"{item.target}: a file exists where module '{item.module}' needs a folder")
            continue
        if not folder.is_dir():
            if mode == "render" and item.target in manifest.dirs and not force:
                report.dirs_missing.append(item.target)
                continue
            if not dry_run:
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    report.fail(f"{item.target}/", exc)
                    continue
            report.dirs_created.append(item.target)
        if not dry_run:
            manifest.record_dir(item.target, item.module)

    for item in plan.files:
        target = paths.vault_file(vault, item.target)
        if target.is_dir():
            report.conflicts.append(f"{item.target}: a folder exists where module '{item.module}' needs a file")
            continue
        new_sha = item.sha256
        exists = target.is_file()
        tracked = manifest.files.get(item.target)
        action = None  # "write" | "record" | "merge" | None
        merged = None
        # Where the item is reported once its write succeeded (a failed write goes to report.failed).
        bucket: list | None = None
        reported_as: object = item
        if not exists:
            if mode == "render" and tracked is not None and not force:
                report.missing.append(item)
            else:
                action = "write"
                bucket = report.created
        else:
            current = paths.sha256_file(target)
            if current == new_sha:
                report.unchanged.append(item)
                action = "record"
            elif mode == "render" and tracked is not None and current == tracked.get("sha256"):
                action = "write"
                bucket = report.updated
            elif force:
                action = "write"
                bucket = report.overwritten
            elif tracked is not None and current != tracked.get("sha256"):
                result = merge_regions(target, item) if mode == "render" else None
                if result is None:
                    report.kept_modified.append(item)
                elif result.problem:
                    report.regions_skipped.append((item, result.problem))
                elif not result.changed:
                    report.regions_current.append(item)
                else:
                    bucket, reported_as = report.merged, (item, result.changed)
                    merged = result.text.encode("utf-8")
                    action = "merge"
            else:
                report.skipped_exists.append(item)
        if dry_run:
            if bucket is not None:
                bucket.append(reported_as)
            continue
        if action in ("write", "merge"):
            try:
                paths.atomic_write(target, item.data if action == "write" else merged)
            except OSError as exc:
                report.fail(item.target, exc)
                continue
        if bucket is not None:
            bucket.append(reported_as)
        if action in ("write", "record") or (action == "merge" and paths.sha256_bytes(merged) == new_sha):
            # The file now equals a full rendering: it counts as untouched again.
            manifest.record(
                item.target, module=item.module, source=item.source, sha256=new_sha, verbatim=item.kind == "verbatim"
            )
        elif action == "merge":
            # Still edited outside its regions: keep the baseline hash (so the file stays
            # "edited" and the next render merges again instead of overwriting it).
            manifest.note_merge(item.target, paths.sha256_bytes(merged))

    produced = plan.targets()
    for rel, entry in sorted(manifest.files.items()):
        if rel not in produced:
            report.orphaned.append((rel, entry.get("module", "?")))
    if report.failed:
        report.conflicts.append(
            f"{len(report.failed)} file(s) or folder(s) above could not be written; everything else was written and "
            "recorded in the manifest. Fix the cause (permissions, a file where a folder belongs, disk space) and "
            "run the command again: it only writes what is still missing or out of date"
        )
    return report


def write_if_changed(path: Path, data: bytes, *, dry_run: bool = False) -> str:
    """Write ``data`` unless identical; returns ``created``, ``updated`` or ``unchanged``."""
    if path.is_file():
        if paths.sha256_file(path) == paths.sha256_bytes(data):
            return "unchanged"
        state = "updated"
    else:
        state = "created"
    if not dry_run:
        paths.atomic_write(path, data)
    return state


def ensure_safe_vault(vault: Path) -> None:
    """Refuse to scaffold into the framework repo itself (or a folder containing it)."""
    vault = Path(vault)
    if vault.exists() and not vault.is_dir():
        raise UniOsError(f"vault path {vault} exists and is not a folder")
    root = paths.FRAMEWORK_ROOT
    if paths.is_within(root, vault):
        raise UniOsError(
            f"refusing to use {vault} as the vault: it contains the framework repo",
            hint="pick a separate folder for your vault (e.g. your Google Drive folder)",
        )
    if paths.is_within(vault, root / "modules") or paths.is_within(vault, root / "tools"):
        raise UniOsError(f"refusing to use {vault} as the vault: it is inside the framework's modules/ or tools/")
