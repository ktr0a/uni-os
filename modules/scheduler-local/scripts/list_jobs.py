#!/usr/bin/env python3
"""List the vault's jobs and turn them into laptop schedules (Uni OS, module scheduler-local).

Used by the setup agent (and by you) to create laptop scheduled tasks from the rendered jobs
in <vault>/_agent/jobs/. Stdlib only, Python 3.11+. Changes nothing anywhere.

  python list_jobs.py --vault "<vault>"                    table of all jobs
  python list_jobs.py --vault "<vault>" --json             the same as JSON
  python list_jobs.py --vault "<vault>" --laptop           only jobs meant to run on a laptop
  python list_jobs.py --vault "<vault>" cron [JOB ...]     cron lines (local time) per job
  python list_jobs.py --vault "<vault>" prompt JOB [--session app|print|rc] [--dry-run]
                                                           header + prompt, ready to paste as a
                                                           desktop scheduled task or to pipe into a CLI
  python list_jobs.py --vault "<vault>" windows JOB        PowerShell that registers a Windows
                                                           Task Scheduler task running run_job.py
                                                           (experimental; printed, not run)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobconf as jc  # noqa: E402


def default_host(vault: str, session: str) -> jc.Host:
    if os.name == "nt":
        date_cmd = "powershell -NoProfile -Command \"Get-Date -Format 'ddd yyyy-MM-dd HH:mm K'\""
        py = "python"
    else:
        tz = os.environ.get("TZ", "")
        date_cmd = (f"TZ={tz} " if tz else "") + "date '+%a %Y-%m-%d %H:%M %Z'"
        py = "python3"
    return jc.Host(name=os.environ.get("UNI_HOST_NAME", "laptop"), kind="laptop",
                   vault=str(Path(vault).resolve()), date_cmd=date_cmd, python=py, session=session)


def cmd_list(a: argparse.Namespace) -> int:
    jobs = jc.load_jobs(a.vault)
    if a.laptop:
        jobs = [j for j in jobs if j.get("RUNTIME") in ("any", "laptop")]
    rows = []
    for j in jobs:
        try:
            lines, notes = jc.cron_lines(j)
        except ValueError as exc:
            lines, notes = [], [f"ERROR: {exc}"]
        rows.append({
            "job": j.id, "title": j.title, "kind": j.get("KIND"), "runtime": j.get("RUNTIME"),
            "default_mode": j.get("DEFAULT_MODE"), "when": jc.describe_when(j),
            "slots": j.get("SLOTS"), "days": j.get("DAYS"), "dates": j.get("DATES"),
            "every_min": j.get("EVERY_MIN"), "session": j.get("SESSION"),
            "model": j.get("MODEL"), "effort": j.get("EFFORT"), "timeout_min": j.get("TIMEOUT_MIN"),
            "precheck": bool(j.get("PRECHECK")), "cron": lines, "notes": notes,
        })
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"no jobs in {jc.jobs_dir(a.vault)}")
        return 0
    cols = [("job", 22), ("kind", 7), ("runtime", 7), ("default_mode", 8), ("session", 7), ("when", 40)]
    print("  ".join(name.upper().ljust(w) for name, w in cols) + "  TITLE")
    for r in rows:
        print("  ".join(str(r[name])[:w].ljust(w) for name, w in cols) + "  " + r["title"])
    return 0


def cmd_cron(a: argparse.Namespace) -> int:
    jobs = jc.load_jobs(a.vault)
    if a.jobs:
        jobs = [j for j in jobs if j.id in a.jobs]
        missing = set(a.jobs) - {j.id for j in jobs}
        if missing:
            print(f"unknown job(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    for j in jobs:
        lines, notes = jc.cron_lines(j)
        print(f"{j.id}  ({j.get('KIND')}, runtime {j.get('RUNTIME')})")
        for line in lines:
            print(f"  cron: {line}")
        if j.get("KIND") == "command" and lines:
            print("  note: a command job; a desktop-app task runs prompts, not commands. Use an OS "
                  "scheduler with run_job.py, or the always-on host.")
        for n in notes:
            print(f"  note: {n}")
    return 0


def cmd_prompt(a: argparse.Namespace) -> int:
    job = jc.load_job(a.vault, a.job)
    if job.get("KIND") != "agent":
        print(f"{a.job} is a {job.get('KIND')} job: no prompt. COMMAND={job.get('COMMAND')}", file=sys.stderr)
        return 2
    host = default_host(a.vault, a.session)
    if a.host_name:
        host.name = a.host_name
    if a.host_vault:
        host.vault = a.host_vault
    text = jc.assemble_prompt(a.vault, job, host, dry_run=a.dry_run)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out} ({len(text)} chars)")
    else:
        sys.stdout.write(text)
    return 0


PS_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def cmd_windows(a: argparse.Namespace) -> int:
    job = jc.load_job(a.vault, a.job)
    vault = str(Path(a.vault).resolve())
    run_job = str(Path(__file__).resolve().parent / "run_job.py")
    py = a.python or shutil.which("pythonw") or shutil.which("python") or "pythonw.exe"
    task = f"Uni OS - {job.id}"
    days = jc.parse_days(job.get("DAYS"))
    triggers = []
    every = job.get("EVERY_MIN").strip()
    if every:
        triggers.append(f"New-ScheduledTaskTrigger -Once -At 00:00 -RepetitionInterval "
                        f"(New-TimeSpan -Minutes {int(every)})")
    for h, m in jc.parse_slots(job.get("SLOTS")):
        if len(days) == 7:
            triggers.append(f"New-ScheduledTaskTrigger -Daily -At {h:02d}:{m:02d}")
        else:
            dl = ",".join(PS_DAYS[d] for d in days)
            triggers.append(f"New-ScheduledTaskTrigger -Weekly -DaysOfWeek {dl} -At {h:02d}:{m:02d}")
    if not triggers:
        print(f"# {job.id} has no SLOTS or EVERY_MIN: nothing to schedule", file=sys.stderr)
        return 2
    limit = int(job.get("TIMEOUT_MIN") or 45) + 10
    arg = f'"{run_job}" --vault "{vault}" --job {job.id}'
    ps_arg = arg.replace("'", "''")
    print(f"# Experimental. Registers \"{task}\" for the current user (no admin rights needed).")
    print("# Review before running it in PowerShell. Remove with:")
    print(f"#   Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false")
    print(f"$action = New-ScheduledTaskAction -Execute '{py}' -Argument '{ps_arg}'")
    print("$triggers = @(")
    print(",\n".join(f"  ({t})" for t in triggers))
    print(")")
    print("# StartWhenAvailable = run a missed slot when the laptop wakes (prompts must be idempotent);")
    print("# IgnoreNew = never two runs at once.")
    print(f"$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew "
          f"-ExecutionTimeLimit (New-TimeSpan -Minutes {limit}) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries")
    print(f"Register-ScheduledTask -TaskName '{task}' -Action $action -Trigger $triggers "
          f"-Settings $settings -Description 'Uni OS job {job.id}: {job.title.replace(chr(39), chr(39) * 2)}'")
    if every:
        print("# On older Windows versions add -RepetitionDuration (New-TimeSpan -Days 3650) to the "
              "repeating trigger.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vault", default=".", help="vault root (default: current folder)")
    p.add_argument("--json", action="store_true", help="list as JSON")
    p.add_argument("--laptop", action="store_true", help="only jobs with RUNTIME any or laptop")
    p.set_defaults(func=cmd_list)
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("list", help="table of jobs (default)")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("cron", help="cron lines per job")
    sp.add_argument("jobs", nargs="*")
    sp.set_defaults(func=cmd_cron)

    sp = sub.add_parser("prompt", help="assembled prompt of an agent job")
    sp.add_argument("job")
    sp.add_argument("--session", default="app", choices=["app", "print", "rc"],
                    help="how the run talks to the user (default: app = desktop scheduled task)")
    sp.add_argument("--host-name", help="name used in logs (default: laptop or $UNI_HOST_NAME)")
    sp.add_argument("--host-vault", help="vault path as seen by the runner (default: --vault resolved)")
    sp.add_argument("--dry-run", action="store_true", help="prepend the dry-run preamble")
    sp.add_argument("--out", help="write to this file instead of stdout")
    sp.set_defaults(func=cmd_prompt)

    sp = sub.add_parser("windows", help="PowerShell to register a Task Scheduler task (experimental)")
    sp.add_argument("job")
    sp.add_argument("--python", help="interpreter for the task (default: pythonw on PATH)")
    sp.set_defaults(func=cmd_windows)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    for attr, default in (("laptop", False), ("json", False)):
        if not hasattr(a, attr):
            setattr(a, attr, default)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
