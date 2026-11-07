"""``uni-os week`` and ``uni-os new-week``: term week number and week pages."""

from __future__ import annotations

import argparse
import json
import re

from .. import config, frontmatter, paths, semester, template
from ..cli import common_options
from ..context import session_from_args
from ..errors import UniOsError

ORDER = 60

WEEK_TEMPLATE = "_templates/week-page.md"
WEEKS_DIR = "progress/weeks"

WEEK_HELP = """\
Print the term week of today (or --date): week 0 is the Monday in
term.week0_monday, week n starts week0 + 7n days.

Examples:
  uni-os week                      Week 8 (Mon 9 Nov to Sun 15 Nov 2026), lectures
  uni-os week --number             8
  uni-os week --date 2026-12-24 --json"""

NEW_WEEK_HELP = f"""\
Create a week page from <vault>/{WEEK_TEMPLATE} at
<vault>/{WEEKS_DIR}/week-NN.md. Never overwrites: an existing page is
left alone (exit 0), so jobs can call it safely.

Which week: by default the NEXT week (the one after the week containing today
or --date), which is what a weekly job running at the end of a week wants.
--current takes the week containing the date; --week N picks one.

The template's {{{{week.number}}}}, {{{{week.nn}}}}, {{{{week.monday}}}},
{{{{week.sunday}}}}, {{{{week.label}}}} and {{{{week.status}}}} are filled in, plus
Obsidian-style {{{{date}}}}, {{{{date:FORMAT}}}}, {{{{time}}}} and {{{{title}}}}.
--close-previous sets status: done on the previous week's page if it is current."""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "week",
        parents=[common_options()],
        help="print the term week of today or a date",
        description=WEEK_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--date", metavar="YYYY-MM-DD", help="date to look up (default: today in term.timezone)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--number", action="store_true", help="print only the week number")
    g.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=run_week)

    p = subparsers.add_parser(
        "new-week",
        parents=[common_options()],
        help="create the next week page from the week-page template (never overwrites)",
        description=NEW_WEEK_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--date", metavar="YYYY-MM-DD", help="reference date (default: today in term.timezone)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--current", action="store_true", help="create the page of the week containing the date")
    g.add_argument("--week", type=int, metavar="N", help="create the page of week N")
    p.add_argument("--status", default="current", help="value for {{week.status}}: upcoming | current | done (default: current)")
    p.add_argument("--close-previous", action="store_true", help="set status: done on the previous week page if it is current")
    p.add_argument("--dry-run", action="store_true", help="print the page instead of writing it")
    p.set_defaults(func=run_new_week)


def _date(session, text: str | None):
    if text:
        day = config.as_date(text)
        if day is None:
            raise UniOsError(f"--date '{text}' is not a date (YYYY-MM-DD)")
        return day
    return semester.today(session.cfg)


def run_week(args) -> int:
    session = session_from_args(args, strict_modules=False)
    day = _date(session, args.date)
    info = semester.describe(day, session.cfg)
    if args.number:
        print(info["number"])
    elif args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Week {info['number']} ({info['label']}), {info['phase']}")
    return 0


_OBSIDIAN_RE = re.compile(r"\{\{\s*(date|time)(?::([^{}\n]+?))?\s*\}\}|\{\{\s*title\s*\}\}")


def fill_obsidian_placeholders(text: str, *, when, title: str) -> str:
    """Fill ``{{date}}``, ``{{date:FMT}}``, ``{{time}}``, ``{{time:FMT}}``, ``{{title}}``."""

    def sub(m: re.Match) -> str:
        if m.group(0).replace(" ", "").startswith("{{title"):
            return title
        kind, fmt = m.group(1), m.group(2)
        if fmt:
            return semester.moment_format(when, fmt.strip())
        return when.strftime("%Y-%m-%d") if kind == "date" else when.strftime("%H:%M")

    return _OBSIDIAN_RE.sub(sub, text)


def render_week_page(session, number: int, *, status: str = "current", when=None) -> tuple[str, str]:
    """Render the week page of ``number``; returns ``(vault-relative path, text)``."""
    vault = session.require_vault()
    tpl_path = vault / WEEK_TEMPLATE
    if not tpl_path.is_file():
        raise UniOsError(
            f"no week-page template at {WEEK_TEMPLATE}",
            hint="it is installed by the progress module: `uni-os enable progress`",
        )
    info = semester.week_info(number, session.cfg, status=status)
    rel = f"{WEEKS_DIR}/week-{info['nn']}.md"
    text = paths.read_text(tpl_path).replace("\r\n", "\n")
    when = when or semester.now(session.cfg)
    text = fill_obsidian_placeholders(text, when=when, title=f"week-{info['nn']}")
    ctx = session.context(with_generated_info=False)
    ctx["week"] = info
    roots = template.INSTALL_ROOTS | {"week"}
    text = template.render(text, ctx, filename=WEEK_TEMPLATE, roots=roots)
    return rel, text


def run_new_week(args) -> int:
    session = session_from_args(args, strict_modules=False)
    vault = session.require_vault()
    day = _date(session, args.date)
    if args.week is not None:
        number = args.week
    elif args.current:
        number = semester.week_of(day, session.cfg)
    else:
        number = semester.week_of(day, session.cfg) + 1
    if number < 0:
        raise UniOsError(f"week {number} is before week 0 ({semester.week0(session.cfg).isoformat()})")
    rel, text = render_week_page(session, number, status=args.status)
    target = paths.vault_file(vault, rel)
    if args.dry_run:
        print(f"--- {rel} (dry run, {'exists' if target.exists() else 'would be created'}) ---")
        print(text, end="" if text.endswith("\n") else "\n")
        return 0
    if target.exists():
        print(f"{rel} already exists; not overwritten")
    else:
        paths.write_text(target, text)
        print(f"created {rel} (week {number}, {semester.week_info(number, session.cfg)['label']})")
    if args.close_previous and number > 0:
        prev = paths.vault_file(vault, f"{WEEKS_DIR}/week-{semester.nn(number - 1)}.md")
        if prev.is_file():
            old = paths.read_text(prev)
            if frontmatter.parse(old).get("status") == "current":
                new, changed = frontmatter.set_value(old, "status", "done")
                if changed:
                    paths.write_text(prev, new)
                    print(f"set status: done on {prev.relative_to(vault).as_posix()}")
    return 0
