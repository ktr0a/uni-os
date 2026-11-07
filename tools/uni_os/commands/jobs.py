"""``uni-os jobs``: list the jobs installed in the vault (for setting up schedulers)."""

from __future__ import annotations

import argparse
import json

from .. import jobs as joblib
from ..cli import common_options
from ..context import session_from_args

ORDER = 80

HELP = """\
List <vault>/_agent/jobs/*: id, kind, slots (or the EVERY_MIN polling
interval, or a raw SCHEDULE), days, runtime and default mode.
The setup agent uses this to create the laptop's scheduled tasks or the VM
timers (see the scheduler-local and vm modules). Jobs of disabled modules carry
a DISABLED marker and are hidden unless --all."""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "jobs",
        parents=[common_options()],
        help="list installed jobs (slots, days, runtime)",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--all", action="store_true", help="include jobs of disabled modules")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=run)


def run(args) -> int:
    session = session_from_args(args, strict_modules=False)
    vault = session.require_vault()
    found = joblib.list_jobs(vault, include_disabled=args.all, agent_dir=session.agent_dir)
    if args.json:
        rows = []
        for job in found:
            row = job.to_dict()
            row["dir"] = job.dir.relative_to(vault).as_posix()
            rows.append(row)
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    if not found:
        print("no jobs installed")
        return 0
    width = max(len(j.id) for j in found)
    for job in found:
        slots = ", ".join(job.slots) or (f"every {job.every_min} min" if job.every_min else "") or (job.conf.get("SCHEDULE") or "-")
        days = ",".join(job.days) if (job.slots or job.every_min) else ""
        flags = []
        if job.disabled:
            flags.append("DISABLED")
        if job.conf.get("SESSION") == "rc":
            flags.append("interactive")
        print(f"  {job.id:<{width}}  {job.kind:<7}  {slots}  {days}  runtime={job.conf.get('RUNTIME')} mode={job.conf.get('DEFAULT_MODE')}  {' '.join(flags)}  {job.title}")
    return 0
