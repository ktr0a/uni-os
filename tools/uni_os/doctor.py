"""``uni-os doctor``: health checks for a vault (or just a config file).

Sections, in order:

1. **config**: the TOML parses and validates (required keys, types, enums, dates,
   times, unique course ids/slugs/folders, colours, no secrets in the config).
2. **modules**: enabled modules exist, dependencies resolve, broken module.toml
   files, OS and Obsidian requirements.
3. **install**: the manifest exists; installed files and folders that are missing;
   files you edited (normal for notes, listed with ``-v``); new template files and
   module folders not yet created; ``uni-os.json`` up to date; the skill copies in a
   vault-relative ``agent.skills_dir`` match ``_agent/skills/`` (:func:`skill_copy_findings`).
4. **jobs**: every ``_agent/jobs/*/job.conf`` parses and uses valid values.
5. **contracts**: parsed-format checks (e.g. week pages keep the headings the
   cockpit and the check-in job parse; the ``course`` property is a course id;
   edited files keep well-formed generated regions). Checks come from a small
   registry (:func:`contract`) and from ``[[contracts]]`` tables in module.toml files.
6. **secrets**: the vault's text files are scanned for API keys, tokens, private
   calendar (iCal) addresses and ntfy topics. Matches are shown redacted.

Exit code: 1 if there is any error (or any warning with ``--strict``), else 0.

Adding a check
--------------
Python::

    from uni_os.doctor import contract, Finding

    @contract("my-check", modules=("progress",))
    def my_check(ctx):
        yield Finding("warning", "contracts", "something is off", "progress/x.md")

Declarative (in a module's ``module.toml``; runs when that module is enabled)::

    [[contracts]]
    name = "week pages keep the parsed headings"
    files = ["progress/weeks/week-*.md"]        # vault-relative globs
    headings = ["## Due this week", "## Notes"] # each must start some heading line
    frontmatter = { type = "week" }             # key = value ("" = key must exist)
    level = "warning"                           # or "error"
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from . import config, frontmatter, jobs, modules, paths, secrets, template
from .errors import Issue

MAX_SCAN_BYTES = 5 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", ".trash", ".venv", "__pycache__", ".pytest_cache"}
BINARY_EXT = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svgz", ".zip", ".gz", ".7z", ".rar",
    ".docx", ".xlsx", ".pptx", ".odt", ".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".mov", ".webm", ".woff",
    ".woff2", ".ttf", ".otf", ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".pyc", ".sqlite", ".db",
}

WEEK_HEADINGS = ("## Due this week", "## Results this week", "## Notes", "## End-of-week check-in")
WEEK_STATUSES = ("upcoming", "current", "done")   # the progress contract (module progress)
PREP_NAME_RE = re.compile(r"^prep-(\d{4}-\d{2}-\d{2})(-r\d+)?\.md$")


@dataclass(frozen=True)
class Finding:
    level: str  # error | warning | info
    section: str
    message: str
    path: str = ""

    def as_issue(self) -> Issue:
        where = f"{self.section}: {self.path}" if self.path else self.section
        return Issue(self.level, where, self.message)


@dataclass
class DoctorContext:
    """What a contract check gets: vault, resolved config, enabled modules, catalogue."""

    vault: Path | None
    cfg: dict
    enabled: list[str]
    catalog: modules.Catalog
    agent_dir: str = paths.DEFAULT_AGENT_DIR
    verbose: bool = False
    extra: dict = field(default_factory=dict)

    def glob(self, pattern: str) -> list[Path]:
        """Vault files matching a vault-relative glob (``**`` allowed)."""
        if self.vault is None or not self.vault.is_dir():
            return []
        from .install import glob_to_regex

        rx = glob_to_regex(pattern)
        root_part = pattern.split("*", 1)[0].rsplit("/", 1)[0] if "/" in pattern.split("*", 1)[0] else ""
        base = self.vault / root_part if root_part else self.vault
        if not base.is_dir():
            return []
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                full = Path(dirpath) / name
                rel = full.relative_to(self.vault).as_posix()
                if rx.match(rel):
                    out.append(full)
        return out

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.vault).as_posix()
        except (ValueError, TypeError):
            return str(path)


CheckFn = Callable[[DoctorContext], Iterable[Finding]]


@dataclass(frozen=True)
class Check:
    name: str
    fn: CheckFn
    modules: tuple[str, ...]  # run only if all of these are enabled (empty = always)


#: The contract-check registry. Use :func:`contract` to add to it.
REGISTRY: list[Check] = []


def contract(name: str, *, modules: Iterable[str] = ()) -> Callable[[CheckFn], CheckFn]:
    """Decorator: register a contract check that runs when ``modules`` are enabled."""

    def wrap(fn: CheckFn) -> CheckFn:
        REGISTRY[:] = [c for c in REGISTRY if c.name != name]
        REGISTRY.append(Check(name, fn, tuple(modules)))
        return fn

    return wrap


# --------------------------------------------------------------------------- built-in contracts


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _has_heading(heads: list[str], wanted: str) -> bool:
    return any(h.startswith(wanted) for h in heads)


@contract("week-pages", modules=("progress",))
def check_week_pages(ctx: DoctorContext) -> Iterable[Finding]:
    """Week pages (and their template) keep the headings other tools parse."""
    tpl = ctx.vault / "_templates" / "week-page.md" if ctx.vault else None
    files = ctx.glob("progress/weeks/week-*.md")
    if tpl is not None:
        if tpl.is_file():
            files = [tpl] + files
        else:
            yield Finding("warning", "contracts", "week-page template is missing (uni-os new-week needs it)", "_templates/week-page.md")
    current = []
    for path in files:
        text = _read(path)
        rel = ctx.rel(path)
        if text is None:
            yield Finding("warning", "contracts", "cannot read file", rel)
            continue
        heads = frontmatter.headings(text)
        for wanted in WEEK_HEADINGS:
            if not _has_heading(heads, wanted):
                yield Finding("error", "contracts", f"missing heading '{wanted}' (the check-in job and the cockpit parse it)", rel)
        if _has_heading(heads, "## Due this week"):
            section = text.split("## Due this week", 1)[1]
            nxt = re.search(r"^#{1,2} ", section, re.M)
            section = section[: nxt.start()] if nxt else section
            header = next((ln for ln in section.split("\n") if ln.strip().startswith("|")), "")
            low = header.lower()
            for col, rx in (("Item", "item"), ("deadline", "deadline|official"), ("Status", "status")):
                if not re.search(rx, low):
                    yield Finding("warning", "contracts", f"'Due this week' table has no {col} column", rel)
        if path == tpl:
            continue
        fm = frontmatter.parse(text)
        if fm.get("type") != "week":
            yield Finding("warning", "contracts", "frontmatter should have type: week", rel)
        status = fm.get("status")
        if status not in WEEK_STATUSES:
            yield Finding("warning", "contracts", f"status '{status}' should be one of {', '.join(WEEK_STATUSES)}", rel)
        if status == "current":
            current.append(rel)
        m = re.match(r"^week-(-?\d+)\.md$", path.name)
        if m and isinstance(fm.get("week"), int) and fm["week"] != int(m.group(1)):
            yield Finding("warning", "contracts", f"frontmatter week: {fm['week']} does not match the file name", rel)
    if len(current) > 1:
        yield Finding("warning", "contracts", f"{len(current)} week pages have status: current ({', '.join(current)}); only the newest should")


@contract("course-cards", modules=("courses",))
def check_course_cards(ctx: DoctorContext) -> Iterable[Finding]:
    """Every course has a card ``<folder>/<slug>.md`` with ``type: course`` and its id."""
    for course in ctx.cfg.get("courses") or []:
        if not isinstance(course, dict) or not course.get("card"):
            continue
        path = paths.vault_file(ctx.vault, course["card"]) if ctx.vault else None
        if path is None or not path.is_file():
            yield Finding("warning", "contracts", f"course card for '{course.get('id')}' is missing (run uni-os render)", course["card"])
            continue
        fm = frontmatter.parse(_read(path) or "")
        if fm.get("type") != "course":
            yield Finding("warning", "contracts", "course card frontmatter should have type: course", course["card"])
        if fm.get("course") != course.get("id"):
            yield Finding("warning", "contracts", f"course card frontmatter should have course: {course.get('id')} (the course id)", course["card"])


@contract("course-property")
def check_course_property(ctx: DoctorContext) -> Iterable[Finding]:
    """The ``course`` property of every note is a course id (``algo``), never a slug or name.

    Dashboards, views and the cockpit filter notes by it. Empty values and
    placeholders (``<course id>``) are fine; ``_templates/`` and ``paths.never_open``
    are skipped.
    """
    courses = [c for c in ctx.cfg.get("courses") or [] if isinstance(c, dict) and c.get("id")]
    if ctx.vault is None or not courses:
        return
    ids = {str(c["id"]) for c in courses}
    aliases: dict[str, str] = {}
    for c in courses:
        for key in ("slug", "short", "folder", "name"):
            if isinstance(c.get(key), str) and c[key]:
                aliases.setdefault(c[key].lower(), str(c["id"]))
    skip = _never_open(ctx.cfg)
    for dirpath, dirnames, filenames in os.walk(ctx.vault):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(ctx.vault).as_posix()
            if rel.startswith("_templates/") or any(rx.match(rel) for rx in skip):
                continue
            text = _read(full)
            if not text or not text.startswith("---"):
                continue
            value = frontmatter.parse(text).get("course")
            values = value if isinstance(value, list) else [value]
            for v in values:
                if v in (None, "") or not isinstance(v, (str, int)) or "<" in str(v) or "{{" in str(v):
                    continue
                if str(v) in ids:
                    continue
                hint = aliases.get(str(v).lower())
                msg = f"course: {v} is not a course id ({', '.join(sorted(ids))})"
                if hint:
                    msg += f"; use course: {hint}"
                yield Finding("warning", "contracts", msg, rel)


@contract("generated-regions")
def check_generated_regions(ctx: DoctorContext) -> Iterable[Finding]:
    """Edited installed files keep well-formed generated regions, so render can refresh them."""
    man = ctx.extra.get("manifest")
    fresh_by_target = ctx.extra.get("plan_by_target") or {}
    if man is None or ctx.vault is None:
        return
    from .install import merge_regions

    for rel, entry in sorted(man.files.items()):
        item = fresh_by_target.get(rel)
        if item is None or item.kind != "template":
            continue
        path = ctx.vault.joinpath(*rel.split("/"))
        if not path.is_file() or paths.sha256_file(path) == entry.get("sha256"):
            continue
        result = merge_regions(path, item)
        if result is None:
            continue
        if result.problem:
            yield Finding("warning", "contracts", f"generated regions cannot be refreshed by `uni-os render`: {result.problem}", rel)
        elif result.changed and ctx.verbose:
            yield Finding("info", "contracts", f"generated region(s) out of date: {', '.join(result.changed)}; `uni-os render` refreshes them", rel)


@contract("prep-notes", modules=("daily-prep",))
def check_prep_notes(ctx: DoctorContext) -> Iterable[Finding]:
    """Prep notes follow ``semester/prep/prep-YYYY-MM-DD[-rN].md`` with ``type: prep``."""
    folder = ctx.vault / "semester" / "prep" if ctx.vault else None
    if folder is None or not folder.is_dir():
        return
    man = ctx.extra.get("manifest")
    installed = set(man.files) if man is not None else set()
    for path in sorted(folder.glob("*.md")):
        rel = ctx.rel(path)
        if path.name.lower() == "readme.md" or rel in installed:
            continue  # documentation installed by a module, not a prep note
        m = PREP_NAME_RE.match(path.name)
        if not m:
            yield Finding("warning", "contracts", "prep notes must be named prep-YYYY-MM-DD.md or prep-YYYY-MM-DD-rN.md", rel)
            continue
        fm = frontmatter.parse(_read(path) or "")
        if fm.get("type") != "prep":
            yield Finding("warning", "contracts", "frontmatter should have type: prep", rel)
        if str(fm.get("date", "")) not in ("", m.group(1)):
            yield Finding("warning", "contracts", f"frontmatter date {fm.get('date')} does not match the file name", rel)


@contract("unrendered-placeholders")
def check_unrendered(ctx: DoctorContext) -> Iterable[Finding]:
    """Edited files must not have gained config placeholders that nothing renders.

    Typical cause: an agent copied template text (``{{course.name}}``) into a note.
    Only placeholders beyond those in a fresh render of the same file count, so
    escaped examples (``\\{{...}}`` in docs) and verbatim files are not reported.
    """
    man = ctx.extra.get("manifest")
    fresh_by_target = ctx.extra.get("plan_by_target") or {}
    if man is None or ctx.vault is None:
        return
    for rel, entry in sorted(man.files.items()):
        if entry.get("verbatim"):
            continue
        path = ctx.vault.joinpath(*rel.split("/"))
        if not path.is_file() or path.suffix.lower() in BINARY_EXT:
            continue
        if paths.sha256_file(path) == entry.get("sha256"):
            continue  # untouched since install: whatever is in it was rendered on purpose
        text = _read(path)
        if text is None:
            continue
        tags = template.find_tags(text, template.KNOWN_ROOTS)
        if not tags:
            continue
        fresh = fresh_by_target.get(rel)
        allowed: dict[str, int] = {}
        if fresh is not None and fresh.data is not None:
            for _line, tag in template.find_tags(fresh.data.decode("utf-8", "replace"), template.KNOWN_ROOTS):
                allowed[tag] = allowed.get(tag, 0) + 1
        extra = []
        for line, tag in tags:
            if allowed.get(tag, 0) > 0:
                allowed[tag] -= 1
            else:
                extra.append((line, tag))
        if extra:
            line, tag = extra[0]
            more = f" (+{len(extra) - 1} more)" if len(extra) > 1 else ""
            yield Finding("warning", "contracts", f"unrendered placeholder {tag} on line {line}{more}", rel)


def _declarative_checks(ctx: DoctorContext) -> Iterable[Finding]:
    for mid in ctx.enabled:
        mod = ctx.catalog.modules.get(mid)
        if mod is None:
            continue
        for idx, spec in enumerate(mod.contracts):
            name = spec.get("name") or f"{mid} contract {idx + 1}"
            level = spec.get("level", "warning")
            if level not in ("error", "warning", "info"):
                level = "warning"
            globs = spec.get("files") or []
            if isinstance(globs, str):
                globs = [globs]
            wanted = spec.get("headings") or []
            fm_req = spec.get("frontmatter") or {}
            for pattern in globs:
                for path in ctx.glob(pattern):
                    text = _read(path)
                    rel = ctx.rel(path)
                    if text is None:
                        continue
                    heads = frontmatter.headings(text)
                    for head in wanted:
                        if not _has_heading(heads, head):
                            yield Finding(level, "contracts", f"missing heading '{head}' ({name})", rel)
                    if fm_req:
                        fm = frontmatter.parse(text)
                        for key, value in fm_req.items():
                            if key not in fm:
                                yield Finding(level, "contracts", f"frontmatter lacks '{key}' ({name})", rel)
                            elif value not in ("", None) and str(fm[key]) != str(value):
                                yield Finding(level, "contracts", f"frontmatter {key}: {fm[key]} should be {value} ({name})", rel)


# --------------------------------------------------------------------------- skill copies


def _vault_relative_skills_dir(cfg: dict) -> str | None:
    """``agent.skills_dir`` as a vault-relative POSIX path, or ``None`` if it lies outside the vault."""
    value = (cfg.get("agent") or {}).get("skills_dir", ".claude/skills")
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith(("~", "/", "\\", "$", "%")) or re.match(r"^[A-Za-z]:", text):
        return None
    rel = paths.posix(text)
    if not rel or ".." in rel.split("/") or paths.check_relpath(rel):
        return None
    return rel


def skill_copy_findings(vault: Path, cfg: dict, agent_dir: str, skill_ids: Iterable[str] | None = None) -> list[Finding]:
    """Compare the copies in ``agent.skills_dir`` with the installed skills in ``<agent_dir>/skills``.

    Only for a vault-relative ``agent.skills_dir`` (default ``.claude/skills``). A copy that
    lacks a file of ``<agent_dir>/skills/<id>/`` or holds a different version of it is a
    warning: setup copies the skills (no links, for synced drives), and copies do not update
    themselves after ``uni-os render``. A skill without a copy is only info (the agent may
    read it through a link or from another folder). Extra files in a copy are ignored (the
    copy command never deletes them). ``skill_ids``: the skills of the enabled modules
    (default: every folder in ``<agent_dir>/skills``).
    """
    rel = _vault_relative_skills_dir(cfg)
    source_root = vault / agent_dir / "skills"
    if rel is None or not source_root.is_dir():
        return []
    copy_root = vault.joinpath(*rel.split("/"))
    try:
        if copy_root.resolve() == source_root.resolve():
            return []  # the agent reads the installed skills directly
    except OSError:
        return []
    ids = sorted(skill_ids) if skill_ids is not None else sorted(p.name for p in source_root.iterdir() if p.is_dir())
    findings: list[Finding] = []
    not_copied: list[str] = []
    stale: list[str] = []
    for sid in ids:
        source = source_root / sid
        if not (source / "SKILL.md").is_file():
            continue
        copy = copy_root / sid
        if not copy.is_dir():
            not_copied.append(sid)
            continue
        try:
            if copy.resolve() == source.resolve():
                continue  # a link or junction: always current
        except OSError:
            pass
        differences: list[str] = []
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                src = Path(dirpath) / name
                file_rel = src.relative_to(source).as_posix()
                dst = copy.joinpath(*file_rel.split("/"))
                if not dst.is_file():
                    differences.append(f"{file_rel} missing")
                elif paths.sha256_file(dst) != paths.sha256_file(src):
                    differences.append(f"{file_rel} differs")
        if differences:
            more = f" +{len(differences) - 3} more" if len(differences) > 3 else ""
            stale.append(f"{sid} ({', '.join(differences[:3])}{more})")
    if stale:
        src_text = source_root.as_posix()
        dst_text = copy_root.as_posix()
        findings.append(Finding(
            "warning", "install",
            f"skill copies are out of date with {agent_dir}/skills/: {'; '.join(stale)}. Copy the skills again "
            f"(setup/PLAYBOOK.md, step 7.3): bash: mkdir -p \"{dst_text}\" && cp -R \"{src_text}/.\" \"{dst_text}/\"   "
            f"PowerShell: Copy-Item -Recurse -Force \"{src_text}/*\" \"{dst_text}/\"",
            rel,
        ))
    if not_copied:
        findings.append(Finding(
            "info", "install",
            f"{len(not_copied)} skill(s) not copied here: {', '.join(not_copied)} (fine if your agent reads them "
            "through a link or from another folder; otherwise copy them, setup/PLAYBOOK.md step 7.3)",
            rel,
        ))
    return findings


# --------------------------------------------------------------------------- secrets scan


def _never_open(cfg: dict) -> list[re.Pattern]:
    from .install import glob_to_regex

    globs = (cfg.get("paths") or {}).get("never_open") or []
    return [glob_to_regex(g) for g in globs if isinstance(g, str)]


def _topic_literal(cfg: dict, vault: Path | None) -> list[tuple[str, str]]:
    topic_file = (cfg.get("notify") or {}).get("ntfy_topic_file")
    if not isinstance(topic_file, str) or not topic_file:
        return []
    path = paths.expand(topic_file)
    if vault is not None and not path.is_absolute():
        return []
    if vault is not None and paths.is_within(path, vault):
        return []  # reported by config validation; never read secrets from inside the vault
    try:
        topic = path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, IndexError, UnicodeDecodeError):
        return []
    return [("your ntfy topic (from notify.ntfy_topic_file)", topic)] if len(topic) >= 6 else []


def scan_vault_secrets(vault: Path, cfg: dict) -> list[Finding]:
    """Scan every text file of the vault (except ``paths.never_open`` and junk folders)."""
    findings: list[Finding] = []
    skip = _never_open(cfg)
    literals = _topic_literal(cfg, vault)
    server = (cfg.get("notify") or {}).get("ntfy_server", "")
    extra = []
    host = re.sub(r"^https?://", "", server or "").strip("/")
    if host and host != "ntfy.sh":
        extra.append(
            secrets.Pattern(
                "ntfy-topic-url-custom",
                re.compile(re.escape(host) + r"/([A-Za-z0-9_\-]{6,})"),
                "error",
                "ntfy topic on your ntfy server",
            )
        )
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(vault).as_posix()
            if any(rx.match(rel) for rx in skip):
                continue
            if full.suffix.lower() in BINARY_EXT or name == paths.MANIFEST_NAME:
                continue
            try:
                if full.stat().st_size > MAX_SCAN_BYTES:
                    continue
                data = full.read_bytes()
            except OSError:
                continue
            if b"\x00" in data[:8192]:
                continue
            text = data.decode("utf-8", errors="replace")
            for hit in secrets.scan_text(text, literals=literals, extra_patterns=extra):
                findings.append(
                    Finding(hit.level, "secrets", f"line {hit.line}: {hit.description} {hit.redacted}", rel)
                )
    return findings


# --------------------------------------------------------------------------- the run


@dataclass
class DoctorResult:
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, section: str, message: str, path: str = "") -> None:
        self.findings.append(Finding(level, section, message, path))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    def exit_code(self, strict: bool = False) -> int:
        if self.errors or (strict and self.warnings):
            return 1
        return 0


def run(session, *, verbose: bool = False, secrets_scan: bool = True) -> DoctorResult:
    """Run every section for an open :class:`~uni_os.context.Session`."""
    from .context import Session  # noqa: F401 - type reference
    from .install import build_plan
    from .manifest import Manifest

    res = DoctorResult()
    cfg = session.cfg
    vault = session.vault

    # 1. config
    for issue in session.validate():
        res.add(issue.level, "config", f"{issue.where}: {issue.message}")

    # 2. modules
    for issue in session.module_problems:
        res.add(issue.level, "modules", issue.message)
    for issue in session.catalog.problems:
        res.add(issue.level, "modules", f"{issue.where}: {issue.message}")
    laptop_os = (cfg.get("runtime") or {}).get("laptop_os")
    obsidian = bool((cfg.get("obsidian") or {}).get("enabled", True))
    for mid in session.enabled:
        mod = session.catalog.modules.get(mid)
        if mod is None:
            continue
        note = mod.os_note(laptop_os)
        if note:
            res.add("warning", "modules", f"{note}, but runtime.laptop_os is {laptop_os}: port its laptop scripts "
                                          f"(docs/porting-to-other-os.md, modules/{mid}/README.md) or disable it")
        if mod.obsidian == "required" and not obsidian:
            res.add("warning", "modules", f"'{mid}' needs Obsidian, but obsidian.enabled is false")
        missing_recs = [r for r in mod.recommends if r not in session.enabled]
        if missing_recs and verbose:
            res.add("info", "modules", f"'{mid}' recommends {', '.join(missing_recs)} (not enabled)")

    manifest = None
    if vault is None:
        res.add("info", "install", "no vault given: only the config and modules were checked")
    elif not vault.is_dir():
        res.add("error", "install", f"vault folder {vault} does not exist")
    else:
        # 3. install state
        manifest = Manifest.load(vault, session.agent_dir)
        if not manifest.exists:
            res.add("error", "install", f"no {session.agent_dir}/{paths.MANIFEST_NAME}: this folder was not set up with `uni-os init`")
        else:
            modified, missing = [], []
            for rel, entry in sorted(manifest.files.items()):
                state = manifest.status(vault, rel)
                if state == "missing":
                    missing.append(rel)
                    res.add("warning", "install", f"installed file is missing (module {entry.get('module')}); `uni-os init` restores it", rel)
                elif state == "modified":
                    modified.append(rel)
                    if verbose:
                        if entry.get("merged_sha256") and paths.sha256_file(vault.joinpath(*rel.split("/"))) == entry["merged_sha256"]:
                            res.add("info", "install", "edited outside its generated regions; `uni-os render` refreshed the regions", rel)
                        else:
                            res.add("info", "install", "edited since install (kept by `uni-os render`)", rel)
            res.add("info", "install", f"{len(manifest.files)} installed files: {len(manifest.files) - len(modified) - len(missing)} untouched, {len(modified)} edited, {len(missing)} missing")
            for mid, entry in sorted(manifest.modules.items()):
                if entry.get("status") == "enabled" and mid not in session.enabled:
                    res.add("warning", "install", f"module '{mid}' is installed but no longer enabled in the config; run `uni-os disable {mid}` or `uni-os render`")
            for mid in session.enabled:
                if mid not in manifest.modules or manifest.modules[mid].get("status") != "enabled":
                    res.add("warning", "install", f"module '{mid}' is enabled in the config but not installed; run `uni-os render`")
        # plan: new files not rendered yet, template errors
        plan = None
        try:
            plan = build_plan(session.catalog, session.enabled, cfg, session.context())
            for err in plan.errors:
                res.add("error", "install", f"template error: {err}")
            if manifest.exists:
                pending = [i.target for i in plan.files if i.target not in manifest.files and not paths.vault_file(vault, i.target).exists()]
                if pending:
                    sample = ", ".join(pending[:5]) + (" ..." if len(pending) > 5 else "")
                    res.add("warning", "install", f"{len(pending)} template file(s) not installed yet ({sample}); run `uni-os render`")
                absent = [i for i in plan.dirs if not paths.vault_file(vault, i.target).is_dir()]
                new_dirs = [i.target for i in absent if i.target not in manifest.dirs]
                gone_dirs = [i for i in absent if i.target in manifest.dirs]
                if new_dirs:
                    sample = ", ".join(f"{d}/" for d in new_dirs[:5]) + (" ..." if len(new_dirs) > 5 else "")
                    res.add("warning", "install", f"{len(new_dirs)} folder(s) not created yet ({sample}); run `uni-os render`")
                for i in gone_dirs:
                    res.add("warning", "install", f"installed folder is missing (module {i.module}); `uni-os init` recreates it, or remove it from the config", f"{i.target}/")
        except Exception as exc:  # noqa: BLE001 - report, do not crash doctor
            res.add("error", "install", f"could not render the module templates: {exc}")
        json_path = vault / session.agent_dir / paths.JSON_NAME
        expected = config.export_json(cfg)
        if not json_path.is_file():
            res.add("warning", "install", f"{session.agent_dir}/{paths.JSON_NAME} is missing; run `uni-os render`")
        elif paths.read_text(json_path) != expected:
            res.add("warning", "install", f"{session.agent_dir}/{paths.JSON_NAME} is out of date; run `uni-os render`")
        # copies of the skills in agent.skills_dir (only the skills of the enabled modules)
        skill_ids = None
        if plan is not None:
            prefix = f"{session.agent_dir}/skills/"
            skill_ids = sorted({i.target[len(prefix):].split("/")[0] for i in plan.files
                                if i.target.startswith(prefix) and "/" in i.target[len(prefix):]})
        res.findings.extend(skill_copy_findings(vault, cfg, session.agent_dir, skill_ids))

        # 4. jobs
        for job in jobs.list_jobs(vault, include_disabled=True, agent_dir=session.agent_dir):
            rel = f"{session.agent_dir}/jobs/{job.id}/job.conf"
            for level, msg in jobs.validate_job(job):
                if level == "info" and not verbose:
                    continue
                res.add(level, "jobs", msg, rel)
        jd = jobs.jobs_dir(vault, session.agent_dir)
        if jd.is_dir():
            for child in sorted(jd.iterdir()):
                if child.is_dir() and (child / "job.conf").is_file():
                    try:
                        jobs.parse_conf(child / "job.conf")
                    except jobs.ConfParseError as exc:
                        res.add("error", "jobs", f"cannot parse: {exc}", f"{session.agent_dir}/jobs/{child.name}/job.conf")

        # 5. contracts
        plan_by_target = {i.target: i for i in plan.files} if plan is not None else {}
        dctx = DoctorContext(
            vault,
            cfg,
            session.enabled,
            session.catalog,
            session.agent_dir,
            verbose,
            {"manifest": manifest, "plan_by_target": plan_by_target},
        )
        for check in REGISTRY:
            if all(m in session.enabled for m in check.modules):
                try:
                    res.findings.extend(check.fn(dctx))
                except Exception as exc:  # noqa: BLE001
                    res.add("warning", "contracts", f"check '{check.name}' crashed: {exc}")
        res.findings.extend(_declarative_checks(dctx))

        # 6. secrets
        if secrets_scan:
            hits = scan_vault_secrets(vault, cfg)
            res.findings.extend(hits)
            if not hits:
                res.add("info", "secrets", "no API keys, tokens, private calendar addresses or ntfy topics found")
    return res
