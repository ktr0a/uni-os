"""Shared logic for the commands that write into the vault (init, render, enable, disable)."""

from __future__ import annotations

import datetime as dt
import sys
from collections import Counter
from pathlib import Path

from .. import config, install, jobs, paths
from ..context import Session
from ..errors import UniOsError
from ..manifest import Manifest


def add_write_options(parser, *, init: bool = False) -> None:
    parser.add_argument("--force", action="store_true", help="overwrite existing files, including ones you edited (careful)")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen; write nothing")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="value of generated.date (default: today); for reproducible output")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every file")


def check_config(session: Session) -> bool:
    """Print config issues; return False if there are errors."""
    issues = session.validate()
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    if warnings:
        print(f"config warnings ({len(warnings)}):")
        for i in warnings:
            print(f"  warning  {i.where}: {i.message}")
    if errors:
        print(f"config errors ({len(errors)}) in {paths.display(session.config_path)}:", file=sys.stderr)
        for i in errors:
            print(f"  error    {i.where}: {i.message}", file=sys.stderr)
        print("fix them and run the command again (nothing was written).", file=sys.stderr)
        return False
    return True


def build(session: Session, date: dt.date):
    """Render the plan; print template errors and return None if there are any."""
    ctx = session.context(date=date)
    plan = install.build_plan(session.catalog, session.enabled, session.cfg, ctx)
    for w in plan.warnings:
        print(f"  warning  {w}")
    if plan.errors:
        print(f"template errors ({len(plan.errors)}); nothing was written:", file=sys.stderr)
        for err in plan.errors:
            print(f"  error    {err}", file=sys.stderr)
        return None
    return plan


def _job_dirs_of(manifest: Manifest, module: str, agent_dir: str) -> list[str]:
    prefix = f"{agent_dir}/jobs/"
    out = set()
    for rel, entry in manifest.files.items():
        if entry.get("module") == module and rel.startswith(prefix):
            out.add(rel[len(prefix):].split("/")[0])
    return sorted(out)


def marker_text(module: str, date: str) -> str:
    return (
        f"This job belongs to module '{module}', disabled on {date} with `uni-os disable {module}`.\n"
        "Hosts (laptop scheduler, VM runner) skip every job whose folder contains this file.\n"
        f"Re-enable with: uni-os enable {module}\n"
    )


def reconcile_modules(
    session: Session, manifest: Manifest, date: str, *, dry_run: bool, report: install.Report | None = None
) -> tuple[list[str], list[str]]:
    """Mark modules enabled/disabled in the manifest; add/remove job DISABLED markers.

    Returns ``(newly_enabled, newly_disabled)``. A marker that cannot be written or
    removed (``OSError``) goes to ``report.fail`` when a report is given, and is raised
    otherwise.
    """
    vault = session.require_vault()
    newly_enabled, newly_disabled = [], []

    def marker_op(job_id: str, op) -> None:
        try:
            op()
        except OSError as exc:
            if report is None:
                raise
            report.fail(f"{session.agent_dir}/jobs/{job_id}/{jobs.DISABLED_MARKER}", exc)

    for mid in session.enabled:
        if manifest.modules.get(mid, {}).get("status") != "enabled":
            newly_enabled.append(mid)
        if not dry_run:
            manifest.set_module(mid, "enabled", date)
            for job_id in _job_dirs_of(manifest, mid, session.agent_dir):
                marker = vault / session.agent_dir / "jobs" / job_id / jobs.DISABLED_MARKER
                if marker.is_file():
                    marker_op(job_id, marker.unlink)
    for mid, entry in sorted(manifest.modules.items()):
        if entry.get("status") == "enabled" and mid not in session.enabled:
            newly_disabled.append(mid)
            if not dry_run:
                manifest.set_module(mid, "disabled", date)
                for job_id in _job_dirs_of(manifest, mid, session.agent_dir):
                    folder = vault / session.agent_dir / "jobs" / job_id
                    if folder.is_dir():
                        marker_op(job_id, lambda f=folder, m=mid: paths.write_text(f / jobs.DISABLED_MARKER, marker_text(m, date)))
    return newly_enabled, newly_disabled


def _by_module(items) -> str:
    counts = Counter(i.module for i in items)
    return ", ".join(f"{m} {n}" for m, n in counts.items())


def print_report(report: install.Report, *, mode: str, dry_run: bool, verbose: bool) -> None:
    would = "would be " if dry_run else ""
    if report.created:
        print(f"  {would}created    {len(report.created):4} files ({_by_module(report.created)})")
        if verbose or dry_run:
            for i in report.created:
                print(f"      + {i.target}")
    if report.updated:
        print(f"  {would}updated    {len(report.updated):4} files you had not edited:")
        for i in report.updated:
            print(f"      ~ {i.target}")
    if report.overwritten:
        print(f"  {would}overwritten {len(report.overwritten):3} files (--force):")
        for i in report.overwritten:
            print(f"      ! {i.target}")
    if report.merged:
        print(f"  {would}refreshed  {len(report.merged):4} files you edited: only their generated regions (everything outside the markers kept):")
        for i, names in report.merged:
            print(f"      ~ {i.target}  [{', '.join(names)}]")
    if report.unchanged:
        print(f"  unchanged    {len(report.unchanged):4} files")
    if report.dirs_created:
        print(f"  {would}created    {len(report.dirs_created):4} folders:")
        for d in report.dirs_created:
            print(f"      + {d}/")
    if report.skipped_exists:
        print(f"  skipped      {len(report.skipped_exists):4} files that already exist (never overwritten; --force replaces them):")
        for i in report.skipped_exists:
            print(f"      = {i.target}  ({i.module})")
    if report.kept_modified:
        print(f"  kept         {len(report.kept_modified):4} files you edited (not overwritten; --force replaces them with a fresh rendering):")
        for i in report.kept_modified:
            print(f"      = {i.target}  ({i.module})")
    if report.regions_current:
        print(f"  kept         {len(report.regions_current):4} files you edited whose generated regions are already current:")
        for i in report.regions_current:
            print(f"      = {i.target}  ({i.module})")
    if report.regions_skipped:
        print(
            f"  skipped      {len(report.regions_skipped):4} files you edited whose generated regions cannot be refreshed "
            "(file kept; restore the markers, or --force replaces the whole file):"
        )
        for i, why in report.regions_skipped:
            print(f"      ! {i.target}: {why}")
    if report.missing:
        print(f"  missing      {len(report.missing):4} installed files you deleted (not recreated; `uni-os init` restores them):")
        for i in report.missing:
            print(f"      - {i.target}")
    if report.dirs_missing:
        print(f"  missing      {len(report.dirs_missing):4} installed folders you deleted (not recreated; `uni-os init` restores them):")
        for d in report.dirs_missing:
            print(f"      - {d}/")
    if report.orphaned and (verbose or mode == "render"):
        print(f"  orphaned     {len(report.orphaned):4} installed files no enabled module produces any more (kept, never deleted):")
        for rel, mod in report.orphaned[: (None if verbose else 15)]:
            print(f"      ? {rel}  ({mod})")
        if not verbose and len(report.orphaned) > 15:
            print(f"      ... {len(report.orphaned) - 15} more (-v lists all)")
    for c in report.conflicts:
        print(f"  CONFLICT     {c}", file=sys.stderr)


def run_install(
    session: Session,
    *,
    mode: str,
    force: bool,
    dry_run: bool,
    date: dt.date,
    verbose: bool,
    config_text: str | None = None,
) -> int:
    """Validate, render, write, reconcile modules, write uni-os.json (+ config copy for init)."""
    vault = session.require_vault()
    install.ensure_safe_vault(vault)
    if not check_config(session):
        return 1
    plan = build(session, date)
    if plan is None:
        return 1
    manifest = Manifest.load(vault, session.agent_dir)
    if mode == "render" and not manifest.exists:
        raise UniOsError(
            f"{vault} has no {session.agent_dir}/{paths.MANIFEST_NAME}",
            hint="create the vault first with `uni-os init --config <file> --vault <folder>`",
        )
    if not dry_run:
        vault.mkdir(parents=True, exist_ok=True)
    report = install.apply_plan(vault, plan, manifest, mode=mode, force=force, dry_run=dry_run)
    failed_in_plan = len(report.failed)
    newly_enabled, newly_disabled = reconcile_modules(session, manifest, date.isoformat(), dry_run=dry_run, report=report)

    agent = vault / session.agent_dir
    extra = []
    would = "would be " if dry_run else ""

    def write_extra(name: str, data: bytes) -> None:
        # A failure here is reported like a failed template file; the manifest is still saved.
        try:
            state = install.write_if_changed(agent / name, data, dry_run=dry_run)
        except OSError as exc:
            report.fail(f"{session.agent_dir}/{name}", exc)
            return
        extra.append(f"{session.agent_dir}/{name} {'' if state == 'unchanged' else would}{state}")

    if config_text is not None:
        write_extra(paths.CONFIG_NAME, config_text.encode("utf-8"))
    write_extra(paths.JSON_NAME, config.export_json(session.cfg).encode("utf-8"))
    if not dry_run:
        try:
            manifest.save(date.isoformat())
            extra.append(f"{session.agent_dir}/{paths.MANIFEST_NAME} saved")
        except OSError as exc:
            report.fail(f"{session.agent_dir}/{paths.MANIFEST_NAME}", exc)
    if len(report.failed) > failed_in_plan:
        report.conflicts.append(
            f"{len(report.failed) - failed_in_plan} file(s) after the module files could not be written (see above). "
            "Fix the cause and run the command again"
        )

    print(f"uni-os {mode}{' (dry run)' if dry_run else ''}: vault {vault.as_posix()}")
    print(f"  modules ({len(session.enabled)}): {', '.join(session.enabled)}")
    if newly_enabled and mode != "init":
        print(f"  {'would enable' if dry_run else 'enabled'}: {', '.join(newly_enabled)}")
    if newly_disabled:
        print(f"  {'would disable' if dry_run else 'disabled'}: {', '.join(newly_disabled)} (files kept; their jobs get a DISABLED marker)")
    print_report(report, mode=mode, dry_run=dry_run, verbose=verbose)
    for line in extra:
        print(f"  {line}")
    skills_prefix = f"{session.agent_dir}/skills/"
    changed_skills = sorted({i.target[len(skills_prefix):].split("/")[0] for i in report.written
                             if i.target.startswith(skills_prefix) and "/" in i.target[len(skills_prefix):]})
    if changed_skills:
        skills_dir = (session.cfg.get("agent") or {}).get("skills_dir") or ".claude/skills"
        verb = ("would be written" if dry_run else "written") if mode == "init" else ("would change" if dry_run else "changed")
        print(f"  skills {verb}: {', '.join(changed_skills)}. Copy them{'' if mode == 'init' else ' again'} to "
              f"agent.skills_dir ({skills_dir}): copies are not links and do not update themselves "
              "(docs/agents.md, \"Pointing your agent at the skills\")")
    if report.conflicts:
        return 1
    return 0


def read_config_text(path: Path) -> str:
    try:
        return paths.read_text(path)
    except OSError as exc:
        raise UniOsError(f"cannot read {path}: {exc}") from None
