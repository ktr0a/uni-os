"""``uni-os modules``: list modules with status and dependencies; resolve presets."""

from __future__ import annotations

import argparse
import json

from .. import modules as modlib
from .. import presets
from ..cli import common_options
from ..context import session_from_args
from ..errors import ModuleError, UniOsError
from ..manifest import Manifest

ORDER = 40

HELP = """\
List the module catalogue. Inside a vault (or with --vault/--config) each
module shows its status: enabled (you asked for it), dep (added as a dependency),
disabled (installed earlier, now off) or available.

--preset minimal|standard|full prints the modules of a preset with their
dependencies resolved (use --no-obsidian to drop the Obsidian-only modules). The
preset is resolved for the laptop's system: --os, else runtime.laptop_os of the
config, else this computer's; modules that do not support it are left out, with
the reason (--os any keeps them)."""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "modules",
        parents=[common_options()],
        help="list modules (status, tier, dependencies) or resolve a preset",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--preset", choices=presets.PRESETS, help="print the resolved module list of a preset")
    p.add_argument("--no-obsidian", action="store_true", help="with --preset: without Obsidian-only modules")
    p.add_argument("--os", choices=presets.OS_NAMES + ("any",), dest="laptop_os",
                   help="with --preset: resolve for this laptop system (default: runtime.laptop_os, else this computer; any = keep all)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=run)


def _try_session(args):
    try:
        return session_from_args(args, strict_modules=False)
    except UniOsError:
        return None


def run(args) -> int:
    session = _try_session(args) if (getattr(args, "vault", None) or getattr(args, "config", None) or not args.preset) else None
    catalog = session.catalog if session else modlib.discover(getattr(args, "modules_dir", None))

    if args.preset:
        obsidian = not args.no_obsidian
        if session is not None and not args.no_obsidian:
            obsidian = bool((session.cfg.get("obsidian") or {}).get("enabled", True))
        ids = presets.preset_modules(args.preset, obsidian=obsidian)
        if args.laptop_os:
            laptop_os, source = (None, "") if args.laptop_os == "any" else (args.laptop_os, "--os")
        else:
            laptop_os, source = presets.laptop_os_for(session.raw if session is not None else {}, detect=True)
        ids, dropped = presets.filter_for_os(ids, catalog, laptop_os)
        missing = [m for m in ids if m not in catalog.modules]
        resolved = []
        problem = None
        try:
            resolved = modlib.resolve([m for m in ids if m in catalog.modules], catalog)
        except ModuleError as exc:
            problem = str(exc)
        extra_deps = [m for m in resolved if m not in ids]
        dropped = [m for m in dropped if m not in resolved]
        if args.json:
            print(json.dumps({"preset": args.preset, "obsidian": obsidian, "laptop_os": laptop_os, "modules": ids,
                              "resolved": resolved, "missing": missing, "dependencies_added": extra_deps,
                              "left_out_for_os": dropped, "problem": problem}, indent=2))
            return 0 if not problem else 1
        print(f"preset {args.preset} ({presets.DESCRIPTIONS[args.preset]}){'' if obsidian else ', without Obsidian'}:")
        print("  " + ", ".join(resolved or ids))
        if extra_deps:
            print(f"  dependencies added: {', '.join(extra_deps)}")
        for line in presets.left_out_note(dropped, catalog, laptop_os, source):
            print("  " + line)
        if missing:
            print(f"  not found in {catalog.dir.as_posix()}: {', '.join(missing)}")
        if problem:
            print(f"  problem: {problem}")
            return 1
        return 0

    status: dict[str, str] = {}
    if session is not None:
        man = Manifest.load(session.vault, session.agent_dir) if session.vault and session.vault.is_dir() else None
        for mid in catalog.modules:
            if mid in session.enabled and (mid in session.requested or mid == modlib.ALWAYS):
                status[mid] = "enabled"
            elif mid in session.enabled:
                status[mid] = "dep"
            elif man is not None and man.modules.get(mid, {}).get("status") == "disabled":
                status[mid] = "disabled"
            else:
                status[mid] = "available"
    rows = []
    for mid in catalog.ids():
        mod = catalog.modules[mid]
        rows.append(
            {
                "id": mid,
                "tier": mod.tier,
                "status": status.get(mid, "available"),
                "requires": mod.requires,
                "recommends": mod.recommends,
                "obsidian": mod.obsidian,
                "os": mod.os,
                "runtime": mod.runtime,
                "summary": mod.summary,
            }
        )
    if args.json:
        print(json.dumps({"modules_dir": catalog.dir.as_posix(), "modules": rows, "incomplete": catalog.incomplete, "problems": [str(p) for p in catalog.problems]}, indent=2))
        return 0
    if not rows:
        print(f"no modules found in {catalog.dir.as_posix()}")
    width = max((len(r["id"]) for r in rows), default=10)
    current_tier = None
    for row in rows:
        if row["tier"] != current_tier:
            current_tier = row["tier"]
            print(f"\n{current_tier}:")
        req = f" (requires {', '.join(row['requires'])})" if row["requires"] else ""
        osn = "" if "any" in row["os"] else f" [{'/'.join(row['os'])} only]"
        print(f"  {row['id']:<{width}}  {row['status']:<9}  {row['summary']}{req}{osn}")
    if catalog.incomplete:
        print(f"\nwithout module.toml (ignored): {', '.join(catalog.incomplete)}")
    if catalog.problems:
        print(f"\nproblems in module.toml files ({len(catalog.problems)}): run `uni-os doctor` for details")
    if session is not None and session.module_problems:
        for p in session.module_problems:
            print(f"\n{p.level}: {p.message}")
        return 1
    return 0
