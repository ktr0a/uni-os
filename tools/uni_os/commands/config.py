"""``uni-os config``: read the resolved config (get, show, keys, validate, path)."""

from __future__ import annotations

import argparse
import json

from .. import config as cfgmod
from .. import template
from ..cli import common_options
from ..context import session_from_args
from ..errors import UniOsError

ORDER = 70

HELP = """\
Read the resolved config (your uni-os.toml merged over the module defaults).

  uni-os config get schedule.daily_prep      17:30, 19:30
  uni-os config get courses.algo.folder      AD          (list items by id or index)
  uni-os config get term --json              {...}
  uni-os config show                         the whole resolved config as JSON
  uni-os config keys                         every key, its value and where it comes from
  uni-os config validate                     config checks only (exit 1 on errors)
  uni-os config path                         the config file in use"""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "config",
        parents=[common_options()],
        help="read config values (get/show/keys/validate/path)",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="config_cmd", metavar="<action>")
    g = sub.add_parser("get", parents=[common_options()], help="print one value (lists joined by ', ', tables as JSON)", description="print one value (lists joined by ', ', tables as JSON)")
    g.add_argument("key", help="dotted key, e.g. term.week0_monday or courses.algo.name")
    g.add_argument("--json", action="store_true", help="always print JSON")
    g.set_defaults(func=run_get)
    s = sub.add_parser("show", parents=[common_options()], help="print the resolved config as JSON", description="print the resolved config as JSON")
    s.set_defaults(func=run_show)
    k = sub.add_parser("keys", parents=[common_options()], help="list every key with its value and source", description="list every key with its value and source")
    k.add_argument("--prefix", default="", help="only keys starting with this")
    k.set_defaults(func=run_keys)
    v = sub.add_parser("validate", parents=[common_options()], help="validate the config only", description="validate the config only")
    v.set_defaults(func=run_validate)
    pa = sub.add_parser("path", parents=[common_options()], help="print the config file path", description="print the config file path")
    pa.set_defaults(func=run_path)
    p.set_defaults(func=lambda args: (p.print_help(), 1)[1])


def run_get(args) -> int:
    session = session_from_args(args, strict_modules=False)
    try:
        value = cfgmod.get_path(session.cfg, args.key)
    except KeyError as exc:
        raise UniOsError(f"config get {args.key}: {exc.args[0]}") from None
    if args.json or isinstance(value, dict) or (isinstance(value, list) and any(isinstance(v, (dict, list)) for v in value)):
        print(json.dumps(cfgmod.to_jsonable(value), indent=2, ensure_ascii=False))
    else:
        print(template.to_text(value))
    return 0


def run_show(args) -> int:
    session = session_from_args(args, strict_modules=False)
    print(json.dumps(cfgmod.to_jsonable(session.cfg), indent=2, ensure_ascii=False))
    return 0


def run_keys(args) -> int:
    session = session_from_args(args, strict_modules=False)
    sources: dict[str, str] = {}
    for source, layer in cfgmod.layers_for(session.raw, session.catalog, session.enabled):
        for key, _ in cfgmod.flatten(layer):
            if not key.startswith("courses"):
                sources[key] = source
    for key, value in cfgmod.flatten(session.cfg):
        if args.prefix and not key.startswith(args.prefix):
            continue
        src = sources.get(key)
        if src is None:
            src = "user" if key.startswith("courses") else "derived"
        try:
            text = json.dumps(cfgmod.to_jsonable(value), ensure_ascii=False)
        except TypeError:
            text = str(value)
        print(f"{key} = {text}    # {src}")
    return 0


def run_validate(args) -> int:
    session = session_from_args(args, strict_modules=False)
    issues = session.validate() + list(session.module_problems)
    for i in issues:
        print(f"  {i.level.upper():7} {i.where}: {i.message}")
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    print(f"{session.config_path.as_posix()}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def run_path(args) -> int:
    session = session_from_args(args, strict_modules=False)
    print(session.config_path.as_posix())
    return 0
