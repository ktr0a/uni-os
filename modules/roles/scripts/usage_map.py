#!/usr/bin/env python3
"""Usage map: where the week's agent usage went, per session. Claude Code only. Read-only.

Why it exists: long-lived sessions re-read their whole context on every turn, so a coordinator
or infrastructure session that has grown to hundreds of thousands of tokens costs more per turn
than a dozen scheduled jobs together. This script ranks sessions by an estimated cost from
Claude Code's local transcripts, so you can see which session to recycle (fresh session from
its state page or a handoff; module roles, `agent.context_refresh_tokens`). In the original
system it showed the coordinator at about a fifth of a week's usage while all jobs together were
under 2 %, which is what made session recycling the rule.

It reads Claude Code's transcripts (`<config dir>/projects/**/*.jsonl`; the config dir is
$CLAUDE_CONFIG_DIR or ~/.claude) and nothing else. It writes nothing. Other agents keep their
history elsewhere: adapt scan() to their format.

    python usage_map.py [--since 2026-11-04T09:00] [--reset-day Wed --reset-time 09:00]
                        [--top 25] [--json] [--host laptop]
                        [--remote "ssh my-host python3 ~/uni-os/modules/roles/scripts/usage_map.py --json --host vm --since {since}"]

Units are relative API-style price weights, good for ranking sessions, not the plan's real
accounting: (input + 1.25 x cache write + 0.1 x cache read + 5 x output) x model factor / 1000,
with model factors top tier (opus) 5/3, mid tier (sonnet) 1, small tier (haiku) 1/3
(`--factor name=x` adds or changes one). "Re-read per turn" is the context a session carries into
each turn on average, "Now" its size at its last turn: a big "Now" costs on every turn.

Sessions are named by their title (Claude Code's custom title). Untitled sessions are grouped by
their first message: scheduled job prompts (the job runners' headers, or a title starting
"job: ") count as "scheduled jobs", relayed messages as "relayed messages"; anything else is
labelled with the first 48 characters, mail addresses masked as <mail>. Subagent transcripts
count under their parent's label plus " (its agents)". Cloud sessions keep no local transcript
and never show up.

Exit codes: 0 ok, 1 no transcript folder, 2 usage error.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

DEFAULT_FACTORS = {"opus": 5 / 3, "sonnet": 1.0, "haiku": 1 / 3}
# How unattended job prompts start in this framework (laptop header, always-on host header, dry-run
# preamble). Keep job prompts recognisable so tools can group them; add your own with --job-prefix.
JOB_PREFIXES = ("You are running the scheduled job", "You are running as a scheduled job", "DRY RUN",
                "<!-- Uni OS laptop host header")
RELAY_PREFIXES = ("Another Claude session sent a message", "Relay request:")
MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def config_dir() -> str:
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def last_reset(now: dt.datetime, day: str = "Wed", time: str = "09:00") -> str:
    """The most recent weekly reset at or before now, as 'YYYY-MM-DDTHH:MM' (UTC). The reset
    weekday and time (UTC) depend on your plan: look them up on its usage page."""
    wd = DAYS.index(day[:3].title())
    h, m = (int(x) for x in time.split(":"))
    now = now.astimezone(dt.timezone.utc)
    d = (now - dt.timedelta(days=(now.weekday() - wd) % 7)).replace(hour=h, minute=m, second=0, microsecond=0)
    if d > now:
        d -= dt.timedelta(days=7)
    return d.strftime("%Y-%m-%dT%H:%M")


def parse_ts(s: str) -> dt.datetime | None:
    """A transcript or --since timestamp as an aware UTC datetime (naive input counts as UTC)."""
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d.astimezone(dt.timezone.utc)


def group_of(first: str | None, title: str | None, job_prefixes=JOB_PREFIXES) -> str:
    if title:
        return "scheduled jobs" if title.startswith("job: ") else MAIL.sub("<mail>", title)
    f = (first or "").replace("\n", " ").strip()
    if f.startswith(tuple(job_prefixes)):
        return "scheduled jobs"
    if f.startswith(RELAY_PREFIXES):
        return "relayed messages"
    # mask first, then cut: a cut through an address would leave a partial one unmasked
    return MAIL.sub("<mail>", f)[:48].strip() or "(no text)"


def factor_of(model: str, factors: dict) -> float:
    name = (model or "").lower()
    return next((v for k, v in factors.items() if k in name), 1.0)


def first_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return str(part.get("text") or "")
    return json.dumps(content)


def scan(root: str, since: str, host: str, factors: dict | None = None, job_prefixes=JOB_PREFIXES) -> list[dict]:
    """One row per session label: cost units, turns, output tokens, cache reads, last context."""
    factors = factors or DEFAULT_FACTORS
    since_dt = parse_ts(since)
    since_epoch = since_dt.timestamp() if since_dt else 0
    seen, rows, titles = set(), {}, {}
    paths = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    # main transcripts first, so a subagent finds its parent's label
    paths.sort(key=lambda p: ("/subagents/" in p.replace(os.sep, "/"), p))
    for path in paths:
        try:
            if os.path.getmtime(path) < since_epoch:
                continue
        except OSError:
            continue
        norm = path.replace(os.sep, "/")
        is_agent = "/subagents/" in norm
        sid = norm.split("/subagents/")[0].rsplit("/", 1)[-1] if is_agent else os.path.basename(norm)[:-6]
        first = title = None
        u = collections.Counter()
        cost, last_ctx, last_ts = 0.0, 0, None
        days, models = collections.Counter(), collections.Counter()
        try:
            fh = open(path, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                kind = d.get("type")
                if kind == "custom-title":
                    title = d.get("customTitle") or title
                elif kind == "user" and first is None:
                    first = first_text((d.get("message") or {}).get("content"))
                elif kind == "assistant":
                    m = d.get("message") or {}
                    us, ts = m.get("usage"), parse_ts(d.get("timestamp", ""))
                    if not us or ts is None or (since_dt and ts < since_dt):
                        continue
                    mid = m.get("id")
                    if mid:
                        if mid in seen:      # the same message can be written to several files
                            continue
                        seen.add(mid)
                    name = (m.get("model") or "").lower()
                    i, o = int(us.get("input_tokens") or 0), int(us.get("output_tokens") or 0)
                    cw, cr = int(us.get("cache_creation_input_tokens") or 0), int(us.get("cache_read_input_tokens") or 0)
                    c = (i + 1.25 * cw + 0.1 * cr + 5 * o) * factor_of(name, factors) / 1000
                    cost += c
                    u.update(turns=1, out=o, cr=cr)
                    days[ts.strftime("%Y-%m-%d")] += c
                    models[name.replace("claude-", "")] += 1
                    last_ctx, last_ts = i + cw + cr, ts
        if not u["turns"]:
            continue
        if not is_agent:
            titles[sid] = group_of(first, title, job_prefixes)
        label = titles.get(sid, group_of(first, title, job_prefixes)) if is_agent else titles[sid]
        key = label + (" (its agents)" if is_agent else "")
        r = rows.setdefault(key, {"label": key, "host": host, "cost": 0.0, "turns": 0, "out": 0, "cr": 0,
                                  "now": 0, "last": "", "days": collections.Counter(), "models": collections.Counter()})
        r["cost"] += cost
        r["turns"] += u["turns"]
        r["out"] += u["out"]
        r["cr"] += u["cr"]
        r["days"].update(days)
        r["models"].update(models)
        stamp = last_ts.isoformat() if last_ts else ""
        if stamp > r["last"] and label != "scheduled jobs":
            r["last"], r["now"] = stamp, last_ctx
    return list(rows.values())


def remote_rows(cmd: str, since: str, out=print) -> list[dict]:
    """Rows from another machine: CMD runs this script there with --json (e.g. over ssh).
    "{since}" in CMD is replaced by the start time; without it, " --since <time>" is appended."""
    full = cmd.replace("{since}", since) if "{since}" in cmd else "%s --since %s" % (cmd, since)
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=280)
        data = json.loads(r.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        out("Remote not reached (%s): local only.\n" % (cmd.split()[0] if cmd.split() else "empty command"))
        return []
    rows = []
    for x in data if isinstance(data, list) else []:
        if isinstance(x, dict) and "label" in x:
            x.setdefault("host", "remote")
            x["days"] = collections.Counter(x.get("days") or {})
            x["models"] = collections.Counter(x.get("models") or {})
            rows.append(x)
    return rows


def render(rows: list[dict], since: str, hosts: str, top: int) -> str:
    rows = sorted(rows, key=lambda r: -r["cost"])
    total = sum(r["cost"] for r in rows) or 1
    L = ["Since %s UTC, %s; cloud sessions are not visible. Total %s units." % (since, hosts, format(round(total), ",")), "",
         "| Session | Where | Units | Share | Turns | Output | Re-read per turn | Now | Model |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    rest = 0.0
    for i, r in enumerate(rows):
        if i >= top:
            rest += r["cost"]
            continue
        model = r["models"].most_common(1)[0][0] if r["models"] else ""
        now = "%dk" % (r["now"] // 1000) if r["now"] else ""
        L.append("| %s | %s | %s | %.1f %% | %d | %dk | %dk | %s | %s |" % (
            r["label"].replace("|", "/"), r["host"], format(round(r["cost"]), ","), r["cost"] / total * 100, r["turns"],
            r["out"] // 1000, r["cr"] // max(r["turns"], 1) // 1000, now, model))
    if rest:
        L.append("| %d others | | %s | %.1f %% | | | | | |" % (len(rows) - top, format(round(rest), ","), rest / total * 100))
    days = collections.Counter()
    for r in rows:
        days.update(r["days"])
    L += ["", "Per day: " + (", ".join("%s %s" % (d[5:], format(round(v), ",")) for d, v in sorted(days.items())) or "none")]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Where the week's agent usage went, per session (Claude Code transcripts; read-only).")
    p.add_argument("--since", help="start, ISO 'YYYY-MM-DDTHH:MM' in UTC (default: the last weekly reset)")
    p.add_argument("--reset-day", default="Wed", help="weekday of your plan's weekly reset, UTC (default: %(default)s)")
    p.add_argument("--reset-time", default="09:00", help="time of the weekly reset, UTC HH:MM (default: %(default)s)")
    p.add_argument("--top", type=int, default=25, help="rows to show before 'others' (default: %(default)s)")
    p.add_argument("--json", action="store_true", help="print the rows as JSON (what --remote reads)")
    p.add_argument("--host", default="local", help="label for this machine in the Where column (default: %(default)s)")
    p.add_argument("--remote", action="append", default=[], metavar="CMD",
                   help="a shell command that runs this script on another machine with --json, e.g. over ssh; "
                        "'{since}' is replaced by the start time (else '--since <time>' is appended); repeatable")
    p.add_argument("--projects", help="transcript folder (default: $CLAUDE_CONFIG_DIR/projects or ~/.claude/projects)")
    p.add_argument("--factor", action="append", default=[], metavar="NAME=X",
                   help="model cost factor by name part, e.g. opus=1.67 (repeatable)")
    p.add_argument("--job-prefix", action="append", default=[], metavar="TEXT",
                   help="another first-message prefix that marks a scheduled job prompt (repeatable)")
    p.add_argument("--now", help=argparse.SUPPRESS)  # tests: pretend the time is this (ISO, UTC)
    a = p.parse_args(argv)
    if a.reset_day[:3].title() not in DAYS or not re.fullmatch(r"\d{1,2}:\d{2}", a.reset_time):
        p.error("--reset-day takes Mon..Sun and --reset-time HH:MM")
    factors = dict(DEFAULT_FACTORS)
    for f in a.factor:
        name, _, val = f.partition("=")
        try:
            factors[name.strip().lower()] = float(val)
        except ValueError:
            p.error("--factor takes NAME=NUMBER, got %r" % f)
    now = parse_ts(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    since = a.since or last_reset(now, a.reset_day, a.reset_time)
    if parse_ts(since) is None:
        p.error("--since takes an ISO time like 2026-11-04T09:00")
    root = a.projects or os.path.join(config_dir(), "projects")
    if not os.path.isdir(root):
        print("no Claude Code transcripts under %s (this script reads Claude Code's history only)" % root,
              file=sys.stderr)
        return 1
    rows = scan(root, since, a.host, factors, JOB_PREFIXES + tuple(a.job_prefix))
    if a.json:
        for r in rows:
            r["days"], r["models"] = dict(r["days"]), dict(r["models"])
        print(json.dumps(rows))
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for cmd in a.remote:
        rows += remote_rows(cmd, since)
    hosts = ", ".join(sorted({r["host"] for r in rows})) or a.host
    print(render(rows, since, hosts, a.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
