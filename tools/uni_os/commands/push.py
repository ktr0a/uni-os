"""`uni-os push`: send one phone push through the push gate (module `notifications`).

  uni-os push "<message>" --id PROBLEM_ID [--id ...] [--priority 1-5] [--title T] [--click URL]
              (aliases kept for other scripts: --text for the message, --ids / --key for --id,
              --prio NAME, --flush-held)
              [--action LABEL=URL] [--source S] [--urgent] [--direct] [--dry-run] [--now "YYYY-MM-DD HH:MM"]
  uni-os push --item ID=TEXT [--item ...] [--prefix "Outcome check: "]   (deterministic senders:
              the text is built from the items that are still fresh, i.e. not pushed recently)
  uni-os push --check --id ID        what a send would do now; changes nothing
  uni-os push --status               budget left today, quiet time now, held queue (JSON)
  uni-os push --flush                release the direct pushes held during a quiet window, as one push

Exit codes: 0 sent (or would send / logged only), 1 send failed or "gate busy, try later"
(another sender held the gate's lock too long; nothing sent, nothing recorded), 2 usage or
setup error (an invalid vault config is not one: the gate then uses the last known notify
settings, else the defaults, and says so on stderr),
10 held (quiet hours or a quiet window: not sent, send again later; only --direct pushes
are queued and released by --flush; a soft window, urgent_ok = true, lets --urgent and
--direct through), 11 budget (day cap or minimum gap), 12 dedupe (all
ids pushed recently), 13 refused (no id, an "all good" text, or personal details).
See pushgate.py.
"""
from __future__ import annotations

import argparse
import json
import sys

from uni_os import pushgate


def _location_parents():
    """The framework CLI's shared --vault/--config/--modules-dir options, if available."""
    try:
        from uni_os.cli import common_options
        return [common_options()]
    except Exception:  # noqa: BLE001  standalone use or tests without the CLI module
        return []


def register(subparsers):
    parents = _location_parents()
    p = subparsers.add_parser(
        "push", parents=parents, help="send a phone push through the push gate (budget, dedupe, quiet hours)",
        description="Send one phone push through the push gate. Exit codes: 0 sent, 1 send failed or gate busy, "
                    "2 usage/setup error, 10 held (quiet time: send again later; --direct is queued), "
                    "11 budget, 12 dedupe, 13 refused.")
    p.add_argument("message", nargs="?", help="one line, plain words; no links (use --click), no personal details")
    p.add_argument("--text", dest="text_opt", default=None, help="the message as an option (same as the positional)")
    p.add_argument("--id", "--ids", "--key", dest="id", action="append", default=[], metavar="PROBLEM_ID",
                   help="stable id of the problem this push is about (repeatable or comma-separated); "
                        "the gate dedupes per id (--key: the spelling of the job runners and the inbox poll)")
    p.add_argument("--item", action="append", default=[], metavar="ID=TEXT",
                   help="deterministic senders: one problem per item; the text is built from fresh items only")
    p.add_argument("--prefix", default="", help="with --item: text put before the joined items")
    p.add_argument("--source", default="cli", help="who sends (heartbeat, outcome-checks, a job id ...)")
    p.add_argument("--priority", "--prio", dest="priority", default=None, metavar="1-5",
                   help="ntfy priority 1-5 or min|low|default|high|max (default 3; --direct: notify.direct_priority)")
    p.add_argument("--title", default=None, help="push title (default notify.title)")
    p.add_argument("--click", default=None, metavar="URL", help="URL opened when the push is tapped")
    p.add_argument("--action", action="append", default=[], metavar="LABEL=URL",
                   help="an ntfy action button (repeatable, at most 3)")
    p.add_argument("--urgent", action="store_true",
                   help="skip the minimum gap (never the day cap) and pass soft quiet windows (urgent_ok = true)")
    p.add_argument("--direct", action="store_true",
                   help="host health alerts and job failures: outside the budget and quiet hours, no id "
                        "needed; still no personal details; queued inside a hard quiet window")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="print what a send would do now; change nothing")
    g.add_argument("--status", action="store_true", help="print the gate's state as JSON")
    g.add_argument("--flush", "--flush-held", dest="flush", action="store_true",
                   help="release the queue of direct pushes held in a quiet window, as one push, if allowed now")
    p.add_argument("--dry-run", action="store_true", help="write nothing, print the decision (also UNI_DRY_RUN=1)")
    p.add_argument("--now", default=None, metavar='"YYYY-MM-DD HH:MM"', help="simulated now (tests)")
    if not parents:
        p.add_argument("--vault", default=argparse.SUPPRESS, help="vault folder (default: UNI_OS_VAULT or the cwd)")
    p.set_defaults(func=run, handler=run)
    return p


PRIORITY_NAMES = {"min": 1, "low": 2, "default": 3, "high": 4, "max": 5, "urgent": 5}


def _priority(v):
    if v is None or v == "":
        return None
    s = str(v).strip().lower()
    if s in PRIORITY_NAMES:
        return PRIORITY_NAMES[s]
    if s.isdigit() and 1 <= int(s) <= 5:
        return int(s)
    raise ValueError("--priority must be 1-5 or min|low|default|high|max, got %r" % v)


def _split_ids(values):
    out = []
    for v in values:
        out += [x.strip() for x in str(v).split(",") if x.strip()]
    return out


def run(args, out=print):
    try:
        return _run(args, out)
    except Exception as e:  # noqa: BLE001  never a traceback from a push: exit 2 (setup error)
        out("error: %s: %s" % (type(e).__name__, e))
        return pushgate.ERROR


def _run(args, out):
    try:
        settings, _cfg = pushgate.settings_for(getattr(args, "vault", None), getattr(args, "config", None),
                                               getattr(args, "modules_dir", None))
        now = pushgate.now_local(settings.tz, args.now)
    except (ValueError, OSError) as e:
        out("error: %s" % e)
        return pushgate.ERROR
    if args.status:
        out(json.dumps(pushgate.status(settings, now), indent=1, ensure_ascii=False))
        return 0
    if args.flush:
        return pushgate.flush(settings, now=now, dry_run=args.dry_run, out=out)
    items = {}
    for it in args.item:
        k, sep, v = it.partition("=")
        if not sep:
            out("error: --item needs ID=TEXT, got %r" % it)
            return pushgate.ERROR
        if k.strip() and v.strip():
            items[k.strip()] = v
    actions = []
    for a in args.action[:3]:
        lbl, sep, url = a.partition("=")
        if not sep or not url.strip():
            out("error: --action needs LABEL=URL, got %r" % a)
            return pushgate.ERROR
        actions.append((lbl.strip(), url.strip()))
    message = args.message if args.message is not None else args.text_opt
    if not args.check and not items and message is None:
        out("error: a message (or --item ID=TEXT) is required")
        return pushgate.ERROR
    try:
        priority = _priority(args.priority)
    except ValueError as e:
        out("error: %s" % e)
        return pushgate.ERROR
    return pushgate.push(settings, text=message, ids=_split_ids(args.id), items=items, prefix=args.prefix,
                         source=args.source, priority=priority, title=args.title, click=args.click,
                         actions=actions, urgent=args.urgent, direct=args.direct, check_only=args.check,
                         dry_run=args.dry_run, now=now, out=out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="uni-os")
    sub = ap.add_subparsers(dest="command", required=True)
    register(sub)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
