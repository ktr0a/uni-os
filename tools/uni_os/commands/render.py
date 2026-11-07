"""``uni-os render``: apply config/module changes to an existing vault."""

from __future__ import annotations

import argparse

from ..cli import common_options
from ..context import generation_date, session_from_args
from ._shared import add_write_options, run_install

ORDER = 20

HELP = """\
Re-render the vault from its config (<vault>/_agent/uni-os.toml).

- Files you never edited (hash still matches the manifest) are updated, e.g.
  the README map, where-to-find-what, the system handbook and routing tables
  after you add a course or a module.
- Files you (or an agent) edited are kept. Their generated regions (between
  <!-- uni-os:begin NAME --> and <!-- uni-os:end NAME --> lines) are still
  refreshed when the file and the fresh rendering have the same well-formed
  regions; everything outside the markers stays yours. Missing or broken
  markers: the file is skipped and listed (never guessed). --force replaces
  whole files.
- New template files and module folders (new course, newly enabled module) are
  created.
- Files and folders you deleted are not recreated (`uni-os init` restores them).
- --dry-run lists what would change, including which regions.
- Modules removed from modules.enabled are marked disabled: their files stay,
  their jobs get a DISABLED marker so hosts skip them.
- _agent/uni-os.json is regenerated."""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "render",
        parents=[common_options()],
        help="re-render untouched files and generated regions after config or module changes",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_write_options(p)
    p.set_defaults(func=run)


def run(args) -> int:
    session = session_from_args(args)
    session.require_vault()
    date = generation_date(session.cfg, args.date)
    return run_install(session, mode="render", force=args.force, dry_run=args.dry_run, date=date, verbose=args.verbose)
