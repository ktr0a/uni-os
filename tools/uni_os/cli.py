"""The ``uni-os`` command line (``python tools/uni_os.py <command>``).

Commands are discovered automatically: every module in ``uni_os/commands/``
(except names starting with ``_``) that defines ``register(subparsers)`` adds its
sub-command(s). A command sets ``func`` with ``parser.set_defaults(func=handler)``;
the handler receives the parsed ``argparse.Namespace`` and returns an exit code
(``None`` means 0). An optional module-level ``ORDER = <int>`` sorts commands in
``--help``.

Shared options: ``--vault``, ``--config`` and ``--modules-dir`` work both before
and after the command name (``uni-os --vault X doctor`` and ``uni-os doctor
--vault X``). Command modules add the per-command copies with
``parents=[common_options()]``.

Errors meant for the user are raised as :class:`~uni_os.errors.UniOsError`; this
module prints them as ``uni-os: error: ...`` and exits 1 (no traceback). An
uncaught ``OSError`` (a folder that cannot be created, a file that cannot be
written) is printed the same way, as one line.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from typing import Sequence

from . import __version__
from .errors import UniOsError

DESCRIPTION = """\
Uni OS: scaffold and maintain a study vault from a config file and modules.

Typical flow:
  uni-os init --config my.toml --vault "G:/My Drive/Uni"   create the vault
  uni-os doctor                                              check it
  uni-os enable daily-prep                                   add a module later
  uni-os render                                              apply config changes
Run a command with --help for details. Inside the vault, --vault is optional."""


def _utf8_console() -> None:
    """Make stdout/stderr UTF-8 (the Windows console defaults to a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def common_options() -> argparse.ArgumentParser:
    """Parent parser with ``--vault``, ``--config`` and ``--modules-dir`` for sub-commands."""
    parent = argparse.ArgumentParser(add_help=False)
    group = parent.add_argument_group("location options")
    group.add_argument("--vault", default=argparse.SUPPRESS, metavar="DIR", help="the vault folder (default: $UNI_OS_VAULT or the vault you are in)")
    group.add_argument("--config", default=argparse.SUPPRESS, metavar="FILE", help="config file (default: <vault>/_agent/uni-os.toml)")
    group.add_argument("--modules-dir", default=argparse.SUPPRESS, metavar="DIR", help="module catalogue (default: <repo>/modules; for tests)")
    return parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uni-os",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"uni-os {__version__}")
    parser.add_argument("--vault", default=None, metavar="DIR", help="the vault folder")
    parser.add_argument("--config", default=None, metavar="FILE", help="config file")
    parser.add_argument("--modules-dir", default=None, metavar="DIR", help="module catalogue folder")
    sub = parser.add_subparsers(dest="command", metavar="<command>", title="commands")
    load_commands(sub)
    return parser


def load_commands(subparsers) -> list[str]:
    """Import ``uni_os.commands.*`` and call each ``register``; returns the module names."""
    from . import commands

    found = []
    for info in pkgutil.iter_modules(commands.__path__):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{commands.__name__}.{info.name}")
        except Exception as exc:  # noqa: BLE001 - one broken command must not break the CLI
            print(f"uni-os: warning: cannot load command module '{info.name}': {exc}", file=sys.stderr)
            continue
        register = getattr(mod, "register", None)
        if callable(register):
            found.append((getattr(mod, "ORDER", 50), info.name, register))
    loaded = []
    for _order, name, register in sorted(found):
        try:
            register(subparsers)
            loaded.append(name)
        except Exception as exc:  # noqa: BLE001
            print(f"uni-os: warning: command module '{name}' failed to register: {exc}", file=sys.stderr)
    return loaded


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI; returns the exit code."""
    _utf8_console()
    if sys.version_info < (3, 11):  # pragma: no cover
        print("uni-os needs Python 3.11 or newer (for tomllib).", file=sys.stderr)
        return 1
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    try:
        result = func(args)
    except UniOsError as exc:
        print(f"uni-os: error: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"  hint: {exc.hint}", file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        # A file system problem outside the per-file handling of the installer (the vault
        # folder itself, the config copy, the manifest): one clean line, no traceback.
        from .install import os_error_text

        print(f"uni-os: error: {os_error_text(exc)}", file=sys.stderr)
        print("  hint: check that the folder exists, is writable and is not open in another program; then run the command again", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        print("uni-os: interrupted", file=sys.stderr)
        return 130
    return 0 if result is None else int(result)


# Small output helpers shared by the commands -------------------------------------------


def say(text: str = "") -> None:
    print(text)


def warn(text: str) -> None:
    print(f"warning: {text}", file=sys.stderr)


def print_issues(issues, *, stream=None) -> None:
    stream = stream or sys.stdout
    for issue in issues:
        print(f"  {issue.level.upper():7} {issue.where}: {issue.message}", file=stream)
