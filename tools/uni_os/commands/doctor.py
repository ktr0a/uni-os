"""``uni-os doctor``: check config, modules, installed files, jobs, contracts and secrets."""

from __future__ import annotations

import argparse
import json

from .. import doctor
from ..cli import common_options
from ..context import session_from_args

ORDER = 25

HELP = """\
Health check. Sections: config, modules, install, jobs, contracts, secrets.

- config: required keys, types, enums, dates ("YYYY-MM-DD"), times ("HH:MM"),
  unique course ids/slugs/folders, colours, no secrets in the config.
- install: missing installed files, files you edited (-v lists them), template
  files not rendered yet, _agent/uni-os.json up to date, skill copies in
  agent.skills_dir that are missing a file or older than _agent/skills.
- contracts: parsed formats, e.g. week pages keep "## Due this week",
  "## Results this week", "## Notes", "## End-of-week check-in".
- secrets: scans the vault's text files for API keys, tokens, private calendar
  (iCal) addresses and ntfy topics (matches are shown redacted). Folders in
  paths.never_open (default: any 'private' folder) are never opened.

Exit code 1 if anything is an error (or a warning, with --strict)."""

ICONS = {"error": "ERROR", "warning": "WARN", "info": "ok"}


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "doctor",
        parents=[common_options()],
        help="check the vault: config, modules, files, jobs, contracts, secrets",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--strict", action="store_true", help="treat warnings as errors (exit 1)")
    p.add_argument("--no-secrets", action="store_true", help="skip the secrets scan")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("-v", "--verbose", action="store_true", help="also list edited files and other details")
    p.set_defaults(func=run)


def run(args) -> int:
    session = session_from_args(args, strict_modules=False)
    result = doctor.run(session, verbose=args.verbose, secrets_scan=not args.no_secrets)
    code = result.exit_code(args.strict)
    if args.json:
        print(
            json.dumps(
                {
                    "vault": session.vault.as_posix() if session.vault else None,
                    "config": session.config_path.as_posix(),
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
                    "exit_code": code,
                    "findings": [f.__dict__ for f in result.findings],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return code
    print(f"uni-os doctor: {session.vault.as_posix() if session.vault else '(no vault)'}")
    print(f"  config: {session.config_path.as_posix()}")
    sections = ["config", "modules", "install", "jobs", "contracts", "secrets"]
    vault_ok = session.vault is not None and session.vault.is_dir()
    for section in sections:
        items = [f for f in result.findings if f.section == section]
        if not items:
            if section == "secrets" and args.no_secrets:
                print(f"\n[{section}] skipped (--no-secrets)")
            elif section in ("jobs", "contracts", "secrets") and not vault_ok:
                print(f"\n[{section}] skipped (no vault)")
            else:
                print(f"\n[{section}] ok")
            continue
        problems = [f for f in items if f.level != "info"]
        print(f"\n[{section}] " + ("ok" if not problems else f"{len(problems)} problem(s)"))
        for f in items:
            where = f"{f.path}: " if f.path else ""
            print(f"  {ICONS.get(f.level, f.level):5} {where}{f.message}")
    print(f"\n{len(result.errors)} error(s), {len(result.warnings)} warning(s)" + (" (strict)" if args.strict else ""))
    return code
