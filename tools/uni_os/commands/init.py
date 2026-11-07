"""``uni-os init``: scaffold a vault from a config file and the enabled modules."""

from __future__ import annotations

import argparse

from .. import install, modules, paths, presets, tomledit
from ..cli import common_options
from ..context import generation_date, open_session
from ..errors import UniOsError
from ._shared import add_write_options, read_config_text, run_install

ORDER = 10

HELP = """\
Create (or complete) a vault: render every enabled module's templates into it.

- Existing files are never overwritten (use --force to replace them); skipped
  files are listed. Run it again any time to restore files you deleted.
- --modules a,b,c (or --preset) overrides modules.enabled; dependencies are
  added automatically. The vault's copy of the config then lists the result.
- A preset is resolved for the laptop's system (runtime.laptop_os, else this
  computer's): modules that do not support it (e.g. the Windows-only
  vault-watch and course-files-fetch on macOS or Linux) are left out, with a
  note. An explicit --modules list is installed as given, with a warning.
- The config file is copied to <vault>/_agent/uni-os.toml (the single source of
  truth from now on); a machine copy goes to _agent/uni-os.json and every
  installed file is recorded with its hash in _agent/.uni-os-manifest.json.

Examples:
  python tools/uni_os.py init --config my.toml --vault "G:/My Drive/Uni"
  python tools/uni_os.py init --config my.toml --vault ./test-vault --dry-run
  python tools/uni_os.py init --vault "G:/My Drive/Uni"          (restore missing files)"""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "init",
        parents=[common_options()],
        help="create a vault from the config and the enabled modules",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--modules", metavar="ID,ID", help="install these modules instead of modules.enabled (dependencies added)")
    p.add_argument("--preset", choices=presets.PRESETS, help="install a preset instead of modules.enabled")
    add_write_options(p, init=True)
    p.set_defaults(func=run)


def run(args) -> int:
    vault_arg = getattr(args, "vault", None)
    config_arg = getattr(args, "config", None)
    if args.modules and args.preset:
        raise UniOsError("use either --modules or --preset, not both")
    if not vault_arg:
        raise UniOsError(
            "init needs --vault <folder> (where the vault should be created)",
            hint='e.g. --vault "G:/My Drive/Uni"; it is never taken implicitly from paths.vault',
        )
    vault = paths.expand(vault_arg)
    install.ensure_safe_vault(vault)
    existing = paths.config_in_vault(vault) if vault.is_dir() else None
    if not config_arg:
        if existing is None:
            raise UniOsError(
                "init needs --config <file>: the vault has no _agent/uni-os.toml yet",
                hint="start from config/uni-os.example.toml",
            )
        config_arg = existing

    session = open_session(
        vault=vault,
        config=config_arg,
        modules_dir=getattr(args, "modules_dir", None),
        modules_override=modules.parse_id_list(args.modules) if args.modules else None,
        preset_override=args.preset,
    )
    for line in session.preset_note():
        print(line)
    if args.modules:
        laptop_os, source = presets.laptop_os_for(session.raw, detect=True)
        for mid in session.enabled:
            mod = session.catalog.modules.get(mid)
            note = mod.os_note(laptop_os) if mod is not None else None
            if note:
                print(f"warning: {note}, but the laptop runs {laptop_os} (from {source}); installed as asked: "
                      "port its laptop scripts (docs/porting-to-other-os.md) or disable it")
    text = read_config_text(session.config_path)
    if args.modules or args.preset:
        text = tomledit.set_modules_enabled(text, session.enabled)

    dest = vault / session.agent_dir / paths.CONFIG_NAME
    same_file = dest.exists() and dest.resolve() == session.config_path.resolve()
    if dest.is_file() and not same_file and not args.force:
        if read_config_text(dest) != text:
            raise UniOsError(
                f"{dest.as_posix()} already exists and differs from {paths.display(session.config_path)}",
                hint="edit the vault's copy and run `uni-os render`, or pass --force to replace it",
            )
    date = generation_date(session.cfg, args.date)
    return run_install(
        session,
        mode="init",
        force=args.force,
        dry_run=args.dry_run,
        date=date,
        verbose=args.verbose,
        config_text=text,
    )
