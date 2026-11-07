#!/usr/bin/env python3
"""Inbox poll for the Uni OS inbox-sync module (stdlib only, Python 3.11+).

Starts the agent job `inbox-sync` soon after a create-only writer drops a NEW update note
into the vault inbox, instead of waiting for the next fixed run. No agent runs here.
Port of the original system's `inbox-poll` (a bash script run every 10 minutes by a
systemd timer), made portable and extended with the stale-note outcome check.

Subcommands
  poll    the job body: maybe start the sync; also report notes stuck too long
  check   exit 0 if an update note waits (or the inbox can't be read, or the sync's failure
          flag _agent/logs/flags/inbox-sync.md exists), else 1.
          A portable PRECHECK for the inbox-sync job on hosts without bash.
  stale   print one OUTCOME line per note older than the threshold; exit 1 if any

Stuck-note alerts use the id `inbox:stuck:<slug of the file name>` and the push text of the
outcome checks (`uni-os heartbeat outcomes`, tools/uni_os/heartbeat_rules.py) and of the vm host's
own check, word for word, and never the file name. Exactly ONE sender pushes them: with the vm
module on, the always-on host; else the notifications module's job outcome-checks (or, where no
command job can run, the heartbeat). `poll --push` therefore stands down whenever the vault config
enables the vm or the notifications module (it prints why) and only pushes in a setup that has
neither. The threshold is the one shared pair notify.inbox_stale_hours / _taps (job.conf passes
them as --stale-hours / --tap-stale-hours).

Rules of `poll` (same as the original):
  * update notes = files named *-update.md, minus Done taps (default pattern
    `_(cockpit|quickview)-(done|undo)-`): taps never start a sync, the dashboard already
    hides the item, so they wait for the next run;
  * no notes at all -> clear the "seen" list and stop;
  * "new" = notes not in the seen list. No new note -> stop. A note a sync was already
    started for (e.g. a parked one) never starts another: the fixed runs retry those;
  * at most one sync per --min-gap-min minutes, counting the fixed runs: if the newest
    run log of the job (or this script's own last start) is younger -> print "waiting";
  * otherwise record the current list as seen and start the job (detached).
  * outside --window nothing is started (the timer may fire around the clock).

Exit codes: poll always exits 0 (a poll that can't decide does nothing: the fixed runs and
health checks cover it). check: 0 = run the sync, 1 = nothing waits. stale: 0 = none stuck,
1 = at least one stuck note.

Environment (all optional; the host runner usually sets them):
  UNI_STATE_DIR  host-side state folder (default ~/.local/state/uni-os, on Windows
                 %LOCALAPPDATA%/uni-os); run logs are read from <state>/jobs/<job>/*.log
  UNI_JOB_START  command that starts a job; "{job}" is replaced by the job id
                 (default: systemctl --user start --no-block uni-job@{job}.service)
  UNI_PUSH_CMD   command used by --push; the script appends
                 --source inbox-sync --prefix "Outcome check: " --item <id>=<text> [...]
                 (default: <python> "$UNI_OS_HOME/tools/uni_os.py" push)
  UNI_DRY_RUN=1  same as --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_TAP_PATTERN = r"_(cockpit|quickview)-(done|undo)-"
DEFAULT_START = "systemctl --user start --no-block uni-job@{job}.service"
SEEN_FILE = "inbox-poll-seen"
LAST_START_FILE = "inbox-poll-last-start"
ALERTED_FILE = "inbox-stale-alerted"
ALERT_REPEAT_S = 24 * 3600
PUSH_PREFIX = "Outcome check: "          # heartbeat.outcome_prefix default: the same push as the outcome checks


# ---------------------------------------------------------------------------- helpers

def utf8_console() -> None:
    """Run as a scheduled command job, stdout is a pipe or NUL, and on Windows Python then
    encodes with the ANSI code page (cp1252): one note name with a character outside it would
    crash the poll before it records and starts anything. UTF-8, replacing what can't be written."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def say(text: str, err: bool = False) -> None:
    """Print without ever failing: the output is a report, never a reason to stop the poll."""
    stream = sys.stderr if err else sys.stdout
    if stream is None:
        return
    try:
        print(text, file=stream, flush=True)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        try:
            print(text.encode(enc, "replace").decode(enc, "replace"), file=stream, flush=True)
        except (OSError, ValueError, LookupError):
            pass
    except (OSError, ValueError):  # closed or broken pipe
        pass


def default_state_dir() -> Path:
    env = os.environ.get("UNI_STATE_DIR")
    if env:
        return Path(env).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "uni-os"
    return Path.home() / ".local" / "state" / "uni-os"


def parse_now(value: str | None) -> float:
    """Epoch seconds for --now (ISO 'YYYY-MM-DD HH:MM[:SS]' local time) or the real time."""
    if not value:
        return time.time()
    return datetime.fromisoformat(value).timestamp()


def parse_window(window: str) -> tuple[int, int] | None:
    """'07:00-22:00' -> (420, 1320) minutes; '', 'always', 'all' -> None (no limit)."""
    w = (window or "").strip().lower()
    if w in ("", "always", "all", "any"):
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", w)
    if not m:
        raise ValueError(f"bad --window {window!r}, expected HH:MM-HH:MM")
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


def in_window(now: float, window: tuple[int, int] | None) -> bool:
    if window is None:
        return True
    lt = time.localtime(now)
    t = lt.tm_hour * 60 + lt.tm_min
    start, end = window
    if start <= end:
        return start <= t <= end          # both ends inclusive, like 07..21:00/10 plus 22:00
    return t >= start or t <= end         # window across midnight


def list_inbox(inbox: Path) -> list[str] | None:
    """File names in the inbox, or None if it can't be read."""
    try:
        return sorted(p.name for p in inbox.iterdir() if p.is_file())
    except OSError:
        return None


def update_notes(names: list[str], tap_re: re.Pattern[str], include_taps: bool = False) -> list[str]:
    notes = [n for n in names if n.endswith("-update.md")]
    if not include_taps:
        notes = [n for n in notes if not tap_re.search(n)]
    return sorted(notes)


def read_lines(path: Path) -> list[str]:
    try:
        return [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def newest_run(runs_dir: Path, state_dir: Path) -> float | None:
    """mtime of the newest non-dry run log of the job, or of this script's last start."""
    best = None
    try:
        for p in runs_dir.glob("*.log"):
            if p.name.endswith("-dry.log"):
                continue
            m = p.stat().st_mtime
            best = m if best is None or m > best else best
    except OSError:
        pass
    stamp = read_lines(state_dir / LAST_START_FILE)
    if stamp:
        try:
            m = float(stamp[0])
            best = m if best is None or m > best else best
        except ValueError:
            pass
    return best


def start_job(cmd_template: str, job: str) -> int:
    cmd = cmd_template.replace("{job}", job)
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW. Not DETACHED_PROCESS: a detached cmd.exe
        # has no console, so a console program it starts would open a visible window.
        kwargs["creationflags"] = 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(cmd, shell=True, **kwargs)
        return 0
    except OSError as exc:
        say(f"could not start {job}: {exc}", err=True)
        return 1


# ---------------------------------------------------------------------------- stale check

def slug(s: str, n: int = 60) -> str:
    """Same slug as tools/uni_os/heartbeat_rules.py, so alert ids match across senders: lower
    case, runs of other characters -> "-", trimmed, at most n characters. A longer slug is cut
    and gets "-" plus the first 6 hex digits of the SHA-1 of the original text (two long names
    that share their start never share an id); a slug of at most n characters is unchanged."""
    full = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")
    if len(full) <= n:
        return full or "x"
    head = full[:max(0, n - 7)].rstrip("-")
    tail = hashlib.sha1(str(s).encode("utf-8")).hexdigest()[:6]
    return head + "-" + tail if head else tail


def stuck_push_text(is_tap: bool, limit_h: float) -> str:
    """Word for word heartbeat_rules.stuck_push_text(): every sender pushes the same text."""
    kind = "Done-tap note" if is_tap else "update note"
    return f"{kind} waiting in the inbox for over {limit_h:g} h, not applied by the inbox sync"


def stale_notes(inbox: Path, names: list[str], tap_re: re.Pattern[str], now: float,
                hours: float, tap_hours: float) -> list[tuple[str, str, str]]:
    """(id, local text, push text) per update note at least as old as its threshold (file mtime,
    like the original and the heartbeat rules). Only the local text names the file."""
    out = []
    for name in update_notes(names, tap_re, include_taps=True):
        is_tap = bool(tap_re.search(name))
        limit_h = tap_hours if is_tap else hours
        try:
            age = now - (inbox / name).stat().st_mtime
        except OSError:
            continue
        if age >= limit_h * 3600:
            push = stuck_push_text(is_tap, limit_h)
            out.append(("inbox:stuck:" + slug(name), f"{push}: {name}", push))
    return out


def push_owner(vault: Path) -> str:
    """Why another sender owns stuck-note pushes in this vault ('' = none, this poll may push).
    Reads the generated effective config (_agent/uni-os.json), else _agent/uni-os.toml."""
    agent = vault / "_agent"
    try:
        cfg = json.loads((agent / "uni-os.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        try:
            import tomllib
            cfg = tomllib.loads((agent / "uni-os.toml").read_text(encoding="utf-8"))
        except (OSError, ValueError, ImportError):
            return ""
    enabled = (cfg.get("modules") or {}).get("enabled") or []
    if "vm" in enabled or (cfg.get("runtime") or {}).get("use_vm") is True:
        return "the vm module is on: the always-on host pushes stuck notes"
    if "notifications" in enabled:
        return "the notifications module is on: its outcome checks (or the heartbeat) push stuck notes"
    return ""


def split_cmd(cmd: str) -> list[str]:
    """Split a command string for subprocess without a shell (Windows-safe)."""
    if os.name != "nt":
        return shlex.split(cmd)
    out = []
    for tok in shlex.split(cmd, posix=False):
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
            tok = tok[1:-1]
        out.append(tok)
    return out


def push_alerts(alerts: list[tuple], state_dir: Path, now: float, push_cmd: list[str], dry: bool) -> None:
    """One push for the stuck notes not pushed in the last 24 h (the push gate dedupes again per
    id). Same shape as the outcome checks: --item <id>=<push text>, --prefix "Outcome check: "."""
    path = state_dir / ALERTED_FILE
    seen: dict[str, float] = {}
    for line in read_lines(path):
        key, _, ts = line.partition("\t")
        try:
            seen[key] = float(ts)
        except ValueError:
            continue
    changed = False
    fresh = []
    for alert in alerts:
        key = alert[0]
        # No file names in pushes (they can carry course or personal details); the local
        # `stale` command and the poll log still name the file.
        text = alert[2] if len(alert) > 2 else alert[1].split(": ", 1)[0]
        if now - seen.get(key, 0) >= ALERT_REPEAT_S:
            fresh.append((key, text))
    if not fresh:
        return
    cmd = push_cmd + ["--source", "inbox-sync", "--prefix", PUSH_PREFIX]
    for key, text in fresh:
        cmd += ["--item", f"{key}={text}"]
    if dry:
        say("would push: " + " ".join(shlex.quote(c) for c in cmd))
        return
    try:
        r = subprocess.run(cmd, timeout=60, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # gate exit codes 10-13 (held, budget, dedupe, refused) are decisions, not failures
        if r.returncode not in (0, 10, 11, 12, 13):
            say(f"push exited {r.returncode}", err=True)
        for key, _ in fresh:
            seen[key] = now
        changed = True
    except (OSError, subprocess.SubprocessError) as exc:
        say(f"push failed: {exc}", err=True)
    if changed:
        keep = {k: v for k, v in seen.items() if now - v < 7 * 24 * 3600}
        write_text_atomic(path, "".join(f"{k}\t{v:.0f}\n" for k, v in sorted(keep.items())))


def push_command(override: str | None) -> list[str]:
    """--push-cmd, else UNI_PUSH_CMD, else `<python> <framework>/tools/uni_os.py push`."""
    s = override or os.environ.get("UNI_PUSH_CMD")
    if s:
        return split_cmd(s)
    py = os.environ.get("UNI_PYTHON") or sys.executable or "python3"
    home = os.environ.get("UNI_OS_HOME") or str(Path(__file__).resolve().parents[3])
    return [py, str(Path(home) / "tools" / "uni_os.py"), "push"]


# ---------------------------------------------------------------------------- commands

def cmd_poll(a: argparse.Namespace) -> int:
    inbox = Path(a.vault) / a.inbox
    state = Path(a.state_dir).expanduser() if a.state_dir else default_state_dir()
    runs = Path(a.runs_dir).expanduser() if a.runs_dir else state / "jobs" / a.job
    tap_re = re.compile(a.tap_pattern)
    now = parse_now(a.now)
    dry = a.dry_run or os.environ.get("UNI_DRY_RUN") == "1"

    names = list_inbox(inbox)
    if names is None:
        return 0  # inbox unreadable: the fixed runs and the health checks cover it

    # Outcome check first: it runs around the clock (quiet hours are the push gate's job).
    if a.stale_hours > 0:
        alerts = stale_notes(inbox, names, tap_re, now, a.stale_hours, a.tap_stale_hours)
        for key, text, _push in alerts:
            say(f"OUTCOME {key}: {text}")
        if alerts and a.push:
            owner = push_owner(Path(a.vault))
            if owner:
                say(f"push: left to the one stuck-note sender; {owner}")
            else:
                push_alerts(alerts, state, now, push_command(a.push_cmd), dry)

    if not in_window(now, parse_window(a.window)):
        return 0

    notes = update_notes(names, tap_re)
    seen_path = state / SEEN_FILE
    if not notes:
        if not dry and seen_path.exists():
            write_text_atomic(seen_path, "")
        return 0
    seen = set(read_lines(seen_path))
    new = [n for n in notes if n not in seen]
    if not new:
        return 0

    last = newest_run(runs, state)
    if last is not None and now - last < a.min_gap_min * 60:
        say("waiting: the last sync started or ended under "
            f"{a.min_gap_min:g} min ago; new: {' '.join(new)}")
        return 0

    if dry:
        say(f"starting the sync (dry run: nothing started); new: {' '.join(new)}")
        return 0
    write_text_atomic(seen_path, "".join(n + "\n" for n in notes))
    write_text_atomic(state / LAST_START_FILE, f"{now:.0f}\n")
    start_job(a.start_cmd or os.environ.get("UNI_JOB_START") or DEFAULT_START, a.job)
    say(f"starting the sync; new: {' '.join(new)}")  # after the start: the report can't stop it
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    names = list_inbox(Path(a.vault) / a.inbox)
    if names is None:
        return 0  # can't read the inbox: run the agent so it reports the problem
    notes = update_notes(names, re.compile(a.tap_pattern), include_taps=True)
    # an earlier run's failure flag: run, so that a successful run can clear it
    flag = Path(a.vault) / a.agent_dir / "logs" / "flags" / "inbox-sync.md"
    return 0 if notes or flag.is_file() else 1


def cmd_stale(a: argparse.Namespace) -> int:
    inbox = Path(a.vault) / a.inbox
    names = list_inbox(inbox)
    if names is None:
        say(f"OUTCOME inbox-unreadable: cannot list {inbox}")
        return 1
    alerts = stale_notes(inbox, names, re.compile(a.tap_pattern), parse_now(a.now),
                         a.stale_hours, a.tap_stale_hours)
    for key, text, _push in alerts:
        say(f"OUTCOME {key}: {text}")
    return 1 if alerts else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--vault", default=".", help="vault root (default: current folder)")
        sp.add_argument("--inbox", default="inbox", help="inbox folder relative to the vault")
        sp.add_argument("--tap-pattern", default=DEFAULT_TAP_PATTERN,
                        help="regex for Done-tap note names (default: %(default)s)")
        sp.add_argument("--now", help="pretend the time is this local ISO time (tests)")

    sp = sub.add_parser("poll", help="maybe start the sync job; report stuck notes")
    common(sp)
    sp.add_argument("--job", default="inbox-sync", help="job id to start (default: %(default)s)")
    sp.add_argument("--window", default="07:00-22:00", help="HH:MM-HH:MM local, or 'always'")
    sp.add_argument("--min-gap-min", type=float, default=60, help="minutes between syncs")
    sp.add_argument("--stale-hours", type=float, default=4, help="alert after this many hours (0 = off)")
    sp.add_argument("--tap-stale-hours", type=float, default=14, help="same for Done taps")
    sp.add_argument("--push", action="store_true",
                    help="push stuck-note alerts through the push command, only in a setup without the vm and "
                         "notifications modules (they own those pushes)")
    sp.add_argument("--push-cmd", help="override UNI_PUSH_CMD")
    sp.add_argument("--start-cmd", help="override UNI_JOB_START ({job} = job id)")
    sp.add_argument("--state-dir", help="override UNI_STATE_DIR")
    sp.add_argument("--runs-dir", help="folder with the job's run logs (default <state>/jobs/<job>)")
    sp.add_argument("--dry-run", action="store_true", help="decide and print, change nothing, start nothing")
    sp.set_defaults(func=cmd_poll)

    sp = sub.add_parser("check", help="exit 0 if an update note waits or the sync's failure flag exists (portable PRECHECK)")
    common(sp)
    sp.add_argument("--agent-dir", default="_agent", help="agent folder relative to the vault (paths.agent_dir)")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("stale", help="print notes stuck longer than the threshold")
    common(sp)
    sp.add_argument("--stale-hours", type=float, default=4)
    sp.add_argument("--tap-stale-hours", type=float, default=14)
    sp.set_defaults(func=cmd_stale)
    return p


def main(argv: list[str] | None = None) -> int:
    utf8_console()
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
