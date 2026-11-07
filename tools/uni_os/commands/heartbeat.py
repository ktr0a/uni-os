"""`uni-os heartbeat`: the deterministic side of the proactive watcher (module `heartbeat`).

  uni-os heartbeat precheck [--json] [--force] [--now "YYYY-MM-DD HH:MM"]
        the heartbeat job's PRECHECK: exit 0 = the agent should run (prints why),
        1 = nothing to do (prints why). It fails OPEN: the job runners read any non-zero
        exit as "skip", so an internal error (an invalid config, an unreadable file, a bug)
        prints "run: pre-check error: <msg>", writes the failure flag
        _agent/logs/flags/<job>.md (job = $UNI_JOB when it is a heartbeat job, else
        heartbeat; level red) and exits 0, so the agent runs and the dashboards show
        job:<job>:failed. A run that commits deletes the flag. (--report errors exit 2.)
  uni-os heartbeat report [--json]      what the agent reads first (also: precheck --report)
  uni-os heartbeat watch                event wake-up (job heartbeat-watch): start an extra run
                                        when something urgent fired (capped per day)
  uni-os heartbeat commit FILE          write flags.json + state.json (in place) and one log
                                        line from the run's decisions JSON
  uni-os heartbeat state [--json] [--init] [--ask-test]
                                        show the memory (last run, flags, snoozes, events);
                                        --init creates missing placeholder files;
                                        --ask-test makes the next asking run test the question path once
  uni-os heartbeat flags [--json]       show what the heartbeat flags now
  uni-os heartbeat log TEXT [--kind note|answer]
  uni-os heartbeat tracker TEXT         one tracker-log line tagged "heartbeat"
  uni-os heartbeat ask --ids A,B --text Q | --take | --has-pending | --gate-id
  uni-os heartbeat rerun JOB            start an allowed job now (heartbeat.rerun_allowed)
  uni-os heartbeat outcomes [--push]    deterministic outcome checks ("exit 0 is not success"); --push
                                        sends only from the one outcome sender (the host when vm is on)
All take --vault DIR (default: UNI_OS_VAULT, else the folder holding _agent/uni-os.toml
above the cwd), --now and --dry-run (also UNI_DRY_RUN=1: write only to the dry-run folder
in the heartbeat state dir, send and start nothing).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

from uni_os import heartbeat_rules as hr
from uni_os import pushgate


def _location_parents():
    """The framework CLI's shared --vault/--config/--modules-dir options, if available."""
    try:
        from uni_os.cli import common_options
        return [common_options()]
    except Exception:  # noqa: BLE001  standalone use or tests without the CLI module
        return []


def _common(p):
    if not any(a.dest == "vault" for a in p._actions):
        p.add_argument("--vault", default=argparse.SUPPRESS, help="vault folder (default: UNI_OS_VAULT or the cwd)")
    p.add_argument("--now", default=None, metavar='"YYYY-MM-DD HH:MM"', help="simulated now (tests, dry runs)")
    p.add_argument("--dry-run", action="store_true", help="write only to the dry-run folder; send and start nothing")
    return p


def register(subparsers):
    p = subparsers.add_parser("heartbeat", help="the proactive watcher: pre-check, report, memory files, outcome checks",
                              description="Deterministic side of the heartbeat. precheck exit codes: 0 run, 1 skip; "
                                          "an internal error fails open (exit 0, 'run: pre-check error: ...', failure flag).")
    sub = p.add_subparsers(dest="hb_cmd", required=True, metavar="SUBCOMMAND")
    parents = _location_parents()

    q = _common(sub.add_parser("precheck", parents=parents,
                               help="the job's PRECHECK: exit 0 run, 1 nothing to do; an error fails open (exit 0 + failure flag)"))
    q.add_argument("--json", action="store_true", help="print the decision and the full report as JSON")
    q.add_argument("--report", action="store_true", help="print the report instead of deciding (exit 0)")
    q.add_argument("--force", action="store_true", help="run regardless of triggers (hard quiet windows still skip; soft ones, urgent_ok = true, never do)")
    q.set_defaults(hb_func=cmd_precheck)

    q = _common(sub.add_parser("report", parents=parents, help="the Markdown report the agent reads first"))
    q.add_argument("--json", action="store_true")
    q.set_defaults(hb_func=cmd_report)

    q = _common(sub.add_parser("watch", parents=parents, help="event wake-up check (every few minutes, no agent)"))
    q.add_argument("--force", action="store_true")
    q.set_defaults(hb_func=cmd_watch)

    q = _common(sub.add_parser("commit", parents=parents, help="write flags.json, state.json and the log line from a decisions file"))
    q.add_argument("file", help="decisions JSON written by the agent (outside the vault)")
    q.set_defaults(hb_func=cmd_commit)

    q = _common(sub.add_parser("state", parents=parents, help="show the heartbeat's memory"))
    q.add_argument("--json", action="store_true")
    q.add_argument("--init", action="store_true", help="create missing placeholder flags.json/state.json")
    q.add_argument("--ask-test", action="store_true", help="the next run that may ask tests the question path once")
    q.set_defaults(hb_func=cmd_state)

    q = _common(sub.add_parser("flags", parents=parents, help="show what the heartbeat flags now"))
    q.add_argument("--json", action="store_true")
    q.set_defaults(hb_func=cmd_flags)

    q = _common(sub.add_parser("log", parents=parents, help="append one line to heartbeat-log.md"))
    q.add_argument("text")
    q.add_argument("--kind", default="note", choices=["note", "answer"])
    q.set_defaults(hb_func=cmd_log)

    q = _common(sub.add_parser("tracker", parents=parents, help='append one tracker-log line tagged "heartbeat"'))
    q.add_argument("text")
    q.set_defaults(hb_func=cmd_tracker)

    q = _common(sub.add_parser("ask", parents=parents, help="ask the one combined question (missing results)"))
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids", help="comma-separated flag ids the question is about")
    g.add_argument("--take", action="store_true", help="(question session) print the pending question, mark it taken")
    g.add_argument("--has-pending", action="store_true", help="exit 0 if a question is pending (job PRECHECK)")
    g.add_argument("--gate-id", action="store_true", help="print the pending question's gate id (NOTIFY_GATE)")
    q.add_argument("--text", help="the question, one line")
    q.set_defaults(hb_func=cmd_ask)

    q = _common(sub.add_parser("rerun", parents=parents, help="start an allowed job now (heartbeat.rerun_allowed)"))
    q.add_argument("job")
    q.set_defaults(hb_func=cmd_rerun)

    q = _common(sub.add_parser("outcomes", parents=parents, help='deterministic outcome checks ("exit 0 is not success")'))
    q.add_argument("--push", action="store_true",
                   help="send fresh problems through the push gate; with the vm module on, only on the always-on "
                        "host (UNI_HOST=vm): elsewhere it prints and sends nothing (one sender per problem)")
    q.set_defaults(hb_func=cmd_outcomes)

    p.set_defaults(func=run, handler=run)
    return p


def _ctx(args, force=False):
    vault = pushgate.find_vault(getattr(args, "vault", None))
    if vault is None or not vault.is_dir():
        raise SystemExit("error: no vault found (pass --vault, set UNI_OS_VAULT, or run inside the vault)")
    cfg_path, mdir = getattr(args, "config", None), getattr(args, "modules_dir", None)
    cfg = pushgate.load_config(vault, cfg_path, mdir) if (cfg_path or mdir) else pushgate.load_config(vault)
    tz = pushgate.deep_get(cfg, "term.timezone")
    now = pushgate.now_local(tz, getattr(args, "now", None))
    return hr.Context(vault, cfg, now=now, dry_run=getattr(args, "dry_run", False), force=force)


def run(args, out=print):
    """Exit codes: the subcommand's own, or 2 for any error, except in the pre-check's
    decision mode (`precheck` without --report), which fails OPEN: both job runners read
    every non-zero PRECHECK exit as "skip", so a pre-check that cannot judge says so loudly
    instead (the line "run: pre-check error: <msg>", the precheck.log line and the job's
    failure flag) and exits 0, so the agent runs."""
    try:
        return args.hb_func(args, out)
    except SystemExit as e:
        if isinstance(e.code, str):
            return _failed(args, e.code, out)
        raise
    except Exception as e:  # noqa: BLE001
        return _failed(args, "error: %s: %s" % (type(e).__name__, e), out)


def _failed(args, msg, out):
    _log_error(args, msg)
    if getattr(args, "hb_cmd", None) == "precheck" and not getattr(args, "report", False):
        return _precheck_fail_open(args, msg, out)
    out(msg)
    return 2


FLAG_JOB_RE = re.compile(r"^heartbeat(-[a-z0-9]+)*$")


def _precheck_fail_open(args, msg, out):
    """Print 'run: pre-check error: <msg>', write the failure flag, exit 0 (the agent runs)."""
    why = " ".join(re.sub(r"^error:\s*", "", str(msg)).split())
    line = "run: pre-check error: " + why
    flag = _write_precheck_flag(args, why)
    if getattr(args, "json", False):
        out(json.dumps({"decision": line, "run": True, "error": why, "flag": flag}, indent=1, ensure_ascii=False))
    else:
        out(line)
    return 0


def _write_precheck_flag(args, why):
    """The job's failure flag `<heartbeat.flags_dir>/<job>.md` in the format of every job's
    failure flag (front matter job, at, level; the first body line says what failed). Best
    effort, never raises: returns the flag's vault-relative path, or None (dry run, no vault,
    the write failed). The job is $UNI_JOB when it names a heartbeat job, else heartbeat."""
    if getattr(args, "dry_run", False) or pushgate.is_dry():
        return None
    try:
        vault = pushgate.find_vault(getattr(args, "vault", None))
        if vault is None or not vault.is_dir():
            return None
        cfg_path, mdir = getattr(args, "config", None), getattr(args, "modules_dir", None)
        try:
            cfg = pushgate.load_config(vault, cfg_path, mdir) if (cfg_path or mdir) else pushgate.load_config(vault)
        except Exception:  # noqa: BLE001  the config may be what failed: use the defaults
            cfg = {}
        agent = str(pushgate.deep_get(cfg, "paths.agent_dir", "_agent") or "_agent").strip("/\\")
        fdir = str(pushgate.deep_get(cfg, "heartbeat.flags_dir") or hr.DEFAULTS["flags_dir"]).strip("/\\")
        if fdir.startswith("_agent/"):
            fdir = agent + fdir[len("_agent"):]
        job = os.environ.get("UNI_JOB", "")
        job = job if FLAG_JOB_RE.match(job) else "heartbeat"
        try:
            now = pushgate.now_local(pushgate.deep_get(cfg, "term.timezone"), getattr(args, "now", None))
        except Exception:  # noqa: BLE001  a bad --now or UNI_OS_NOW: the real time
            now = dt.datetime.now().replace(second=0, microsecond=0)
        body = "pre-check error: %s; the agent ran without a pre-check decision" % pushgate.clip(why, 240)
        path = vault / fdir / (job + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\njob: %s\nat: %s\nlevel: red\n---\n%s\n" % (job, now.strftime("%Y-%m-%d %H:%M"), body),
                        encoding="utf-8")
        return fdir.replace("\\", "/") + "/" + job + ".md"
    except Exception:  # noqa: BLE001  the flag is a courtesy; the exit code is what matters
        return None


def _log_error(args, msg):
    if getattr(args, "dry_run", False) or pushgate.is_dry():
        return
    try:
        d = hr.hb_state_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "precheck.log", "a", encoding="utf-8") as f:
            f.write("%s | %s | %s\n" % (pushgate.now_local().strftime("%Y-%m-%d %H:%M"), args.hb_cmd, " ".join(msg.split())))
    except (OSError, ValueError):
        pass


def cmd_precheck(args, out):
    ctx = _ctx(args, force=args.force)
    r = hr.compute(ctx)
    if args.report:
        out(json.dumps(r, indent=1, ensure_ascii=False, default=str) if args.json else hr.render(r))
        return 0
    reason, code = hr.gate_decision(ctx, r)
    if args.json:
        out(json.dumps({"decision": reason, "run": code == 0, "report": r}, indent=1, ensure_ascii=False, default=str))
    else:
        out(reason)
    return code


def cmd_report(args, out):
    r = hr.compute(_ctx(args))
    out(json.dumps(r, indent=1, ensure_ascii=False, default=str) if args.json else hr.render(r))
    return 0


def cmd_watch(args, out):
    ctx = _ctx(args, force=args.force)
    return hr.watch(ctx, hr.compute(ctx), out)


def cmd_commit(args, out):
    ctx = _ctx(args)
    try:
        with open(args.file, encoding="utf-8") as f:
            dec = json.load(f)
    except (OSError, ValueError) as e:
        out("commit refused: cannot read %s: %s" % (args.file, e))
        return 2
    return hr.commit(ctx, dec, out)


def cmd_state(args, out):
    ctx = _ctx(args)
    if args.init:
        hr.init_files(ctx, out)
    if args.ask_test:
        if ctx.dry:
            out("dry run: would create the ask-test marker")
        else:
            ctx.state_dir.mkdir(parents=True, exist_ok=True)
            (ctx.state_dir / "ask-test-due").write_text("due\n", encoding="utf-8")
            out("ask test: due (the next run that may ask makes one test question)")
    s = hr.status(ctx)
    if args.json:
        out(json.dumps(s, indent=1, ensure_ascii=False, default=str))
    elif not (args.init or args.ask_test):
        lr = s["last_run"] or {}
        out("last run: %s (%s)" % (lr.get("at") or "never", lr.get("kind") or "-"))
        out("flags remembered: %d; snoozes: %s" % (s["flags"], ", ".join((s["snoozes"] or {}).keys()) or "none"))
        out("event runs today: %d; pending question: %s; ask mode: %s" % (s["event_runs_today"], s["pending_question"], s["ask_mode"]))
        for line in s["precheck_log_tail"]:
            out("  " + line)
    return 0


def cmd_flags(args, out):
    ctx = _ctx(args)
    doc = ctx.rjson("_agent/heartbeat/flags.json") or {}
    if args.json:
        out(json.dumps(doc, indent=1, ensure_ascii=False))
        return 0
    if doc.get("status") == "not-switched-on" or not doc.get("generated"):
        out("no flags yet (the heartbeat has not committed a run)")
        return 0
    out("flags from %s (%s run):" % (doc["generated"], (doc.get("run") or {}).get("kind", "?")))
    for f in doc.get("flags") or []:
        out("- [%s] %s: %s%s" % (f.get("level"), f.get("id"), f.get("text"),
                                 "  (snoozed until %s)" % f["snoozed_until"] if f.get("snoozed_until") else ""))
    if not doc.get("flags"):
        out("- none")
    return 0


def cmd_log(args, out):
    return hr.append_log(_ctx(args), args.text, args.kind, out)


def cmd_tracker(args, out):
    return hr.tracker(_ctx(args), args.text, out)


def cmd_ask(args, out):
    ctx = _ctx(args)
    if args.take:
        return hr.take_pending(ctx, out)
    if args.has_pending:
        return 0 if hr.has_pending(ctx) else 1
    if args.gate_id:
        out(hr.pending_gate_id(ctx))
        return 0
    if not args.text:
        out("refused: --text is required with --ids")
        return 2
    return hr.ask(ctx, args.ids.split(","), args.text, out)


def cmd_rerun(args, out):
    return hr.rerun(_ctx(args), args.job, out)


def cmd_outcomes(args, out):
    return hr.outcomes(_ctx(args), push=args.push, out=out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="uni-os")
    sub = ap.add_subparsers(dest="command", required=True)
    register(sub)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
