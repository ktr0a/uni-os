"""``uni-os enable`` / ``uni-os disable``: add or remove modules later."""

from __future__ import annotations

import argparse

from .. import modules, paths, tomledit
from ..cli import common_options
from ..context import generation_date, open_session, session_from_args
from ..errors import UniOsError
from ._shared import add_write_options, read_config_text, run_install

ORDER = 30

ENABLE_HELP = """\
Enable modules: add them to modules.enabled in <vault>/_agent/uni-os.toml
(comments are kept), add their dependencies, install their files and folders
and update the generated maps and tables (also the generated regions of files
you edited, as `uni-os render` does). Host-side steps (scheduled tasks, VM timers, phone app)
are listed in each module's README under "How it works" / setup.

Example: python tools/uni_os.py enable daily-prep heartbeat"""

DISABLE_HELP = """\
Disable modules: remove them from modules.enabled. Nothing is deleted: their
files and folders stay in the vault, their jobs get a DISABLED marker (hosts
skip them) and the generated routing tables/maps stop listing them (generated
regions are refreshed in files you edited, as `uni-os render` does). A module that other
enabled modules need cannot be disabled alone (disable them together). Disabling
the last listed module leaves modules.enabled = ["core"] (an empty list would mean
"use uni_os.preset" and bring the preset's modules back).

Remove the module's scheduled tasks / VM timers yourself afterwards (see the
module README, section "Removing it").

Example: python tools/uni_os.py disable daily-prep"""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "enable",
        parents=[common_options()],
        help="enable modules (adds dependencies, installs their files)",
        description=ENABLE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("ids", nargs="+", metavar="MODULE", help="module id(s)")
    add_write_options(p)
    p.set_defaults(func=run_enable)

    p = subparsers.add_parser(
        "disable",
        parents=[common_options()],
        help="disable modules (never deletes files)",
        description=DISABLE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("ids", nargs="+", metavar="MODULE", help="module id(s)")
    add_write_options(p)
    p.set_defaults(func=run_disable)


def _write_and_render(args, session, new_requested: list[str]) -> int:
    # An empty modules.enabled means "use uni_os.preset", so disabling the last listed
    # module would bring the whole preset back. Keep core listed instead.
    new_requested = list(new_requested) or [modules.ALWAYS]
    text = read_config_text(session.config_path)
    new_text = tomledit.set_modules_enabled(text, new_requested)
    if args.dry_run:
        print(f"would set modules.enabled in {session.config_path.as_posix()} to: {', '.join(new_requested)}")
        new_session = open_session(
            vault=session.vault,
            config=session.config_path,
            modules_dir=getattr(args, "modules_dir", None),
            modules_override=new_requested,
        )
    else:
        paths.write_text(session.config_path, new_text)
        print(f"updated modules.enabled in {session.config_path.as_posix()}")
        new_session = open_session(vault=session.vault, config=session.config_path, modules_dir=getattr(args, "modules_dir", None))
    date = generation_date(new_session.cfg, args.date)
    return run_install(new_session, mode="render", force=args.force, dry_run=args.dry_run, date=date, verbose=args.verbose)


def run_enable(args) -> int:
    session = session_from_args(args)
    session.require_vault()
    ids = modules.parse_id_list(args.ids)
    new_requested = list(session.requested)
    for mid in ids:
        if mid not in new_requested:
            new_requested.append(mid)
    resolved = modules.resolve(new_requested, session.catalog)  # raises on unknown ids / cycles
    added = [m for m in resolved if m not in session.enabled]
    if not added:
        print(f"already enabled: {', '.join(ids)}")
        return 0
    print(f"enabling: {', '.join(added)}" + (f" (dependencies of {', '.join(ids)})" if set(added) - set(ids) else ""))
    laptop_os = (session.cfg.get("runtime") or {}).get("laptop_os")
    obsidian = bool((session.cfg.get("obsidian") or {}).get("enabled", True))
    for mid in added:
        mod = session.catalog.modules[mid]
        note = mod.os_note(laptop_os)
        if note:
            print(f"  warning: {note} (runtime.laptop_os = {laptop_os}); its laptop scripts need porting "
                  f"(docs/porting-to-other-os.md)")
        if mod.obsidian == "required" and not obsidian:
            print(f"  warning: {mid} needs Obsidian (obsidian.enabled = false)")
    rc = _write_and_render(args, session, new_requested)
    if rc == 0:
        for mid in added:
            mod = session.catalog.modules[mid]
            recs = [r for r in mod.recommends if r not in resolved]
            print(f"  next for {mid}: read {mod.record()['readme']}" + (f"; it recommends {', '.join(recs)}" if recs else ""))
            if mod.config_keys:
                print(f"    config keys: {', '.join(mod.config_keys)}")
    return rc


def run_disable(args) -> int:
    session = session_from_args(args)
    session.require_vault()
    ids = modules.parse_id_list(args.ids)
    if modules.ALWAYS in ids:
        raise UniOsError("'core' cannot be disabled: every other module builds on it")
    for mid in ids:
        if mid not in session.catalog.modules:
            raise modules._unknown(mid, session.catalog, None)
    not_enabled = [m for m in ids if m not in session.enabled]
    if not_enabled:
        print(f"not enabled (nothing to do): {', '.join(not_enabled)}")
    targets = [m for m in ids if m in session.enabled]
    if not targets:
        return 0
    needers = modules.dependents(targets, session.enabled, session.catalog)
    blocking = sorted({n for t in targets for n in needers[t] if n not in targets})
    if blocking:
        detail = "; ".join(f"{t} is needed by {', '.join(n for n in needers[t] if n not in targets)}" for t in targets if any(n not in targets for n in needers[t]))
        raise UniOsError(
            f"cannot disable: {detail}",
            hint=f"disable them together: uni-os disable {' '.join(targets + blocking)}",
        )
    new_requested = [m for m in session.requested if m not in targets]
    resolved = modules.resolve(new_requested, session.catalog)
    still = [m for m in targets if m in resolved]
    if still:  # pragma: no cover - guarded by the dependents check
        raise UniOsError(f"{', '.join(still)} would still be pulled in as dependencies")
    rc = _write_and_render(args, session, new_requested)
    if rc == 0 and not args.dry_run:
        from ..manifest import Manifest

        man = Manifest.load(session.vault, session.agent_dir)
        for mid in targets:
            files = man.files_of(mid)
            print(f"  {mid}: {len(files)} installed file(s) kept in the vault (delete them yourself if you want).")
            print(f"    remove its scheduled tasks / VM timers by hand: see modules/{mid}/README.md, 'Removing it'")
    return rc
