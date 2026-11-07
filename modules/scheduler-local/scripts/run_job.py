#!/usr/bin/env python3
"""Run one Uni OS job on the laptop, headless (module scheduler-local). EXPERIMENTAL.

For OS schedulers (Windows Task Scheduler, cron, launchd) that start the agent CLI without
the agent's desktop app. The always-on host has its own runner (module vm); this is the
small laptop equivalent. Stdlib only, Python 3.11+.

  python run_job.py --vault "<vault>" --job <job-id> [--dry-run] [--print-only]

What it does, in order (the original host runner's semantics, trimmed for a laptop):
 1. read <vault>/_agent/jobs/<job>/job.conf (and agent.* from the vault's config: the generated
    _agent/uni-os.json, which has the module defaults merged in, else _agent/uni-os.toml);
 2. per-job lock: if the job is already running, exit 0; a job whose folder holds a DISABLED
    file (its module was disabled with `uni-os disable`) is skipped;
 3. NEEDS_VAULT=yes: the vault folder (and its _agent/) must be readable, else log
    "skipped: vault not reachable" and exit 3 (a synced drive that isn't mounted yet);
 4. failover marker: if _agent/vm/ran/<task>.md names this run's nominal slot, the always-on
    host already ran it: log "skipped" and exit 0 (guards catch-up runs after a wake-up);
 5. AGENT_LOCK (agent jobs): "exclusive" waits until no other agent job of this runner runs
    (skips after LOCK_WAIT_MIN), "shared" waits only for an exclusive holder (then runs anyway);
 6. PRECHECK: run with bash from the vault root; non-zero = "skipped (precheck)", exit 0.
    No bash found: the check is skipped and the job runs (it decides itself);
 7. KIND=command: COMMAND with bash -c from the vault root (DRY_OK=yes appends --dry-run on a
    dry run, otherwise a dry run only prints the command);
    KIND=agent: prompt = [dry-run preamble] + _agent/jobs/_header.md + prompt.md, piped into
    the agent CLI headless (default for Claude Code:
    claude -p --permission-mode <mode> --output-format text [--model M] [--effort E] --name "job: ...");
 8. hard timeout TIMEOUT_MIN (the process tree is killed, exit 124); a CLI that can't be started
    (not on the task's PATH, a wrong agent.cli or headless_command) is exit 127, a config with no
    usable headless command exit 2: both still get a run log, a jobs.log line and the push;
 9. log to <state>/jobs/<job>/<YYYY-MM-DD_HHMMSS>[-dry].log ending "# exit N after Ss", one
    line in <state>/jobs.log ("YYYY-MM-DD HH:MM | <job> | exit N | Ss | <log>"), keep 40 logs.
    The record is written before the job's output is echoed, and the console is UTF-8 with
    replacement, so output the console can't show never loses the record;
10. non-zero exit and --push-failures: one direct push "laptop job <id> failed (exit N)" through
    the push gate (`uni-os push --direct --id job-failed:<id>`, like the host runner's failure push).

State lives on the laptop, never in the synced vault (two machines writing one file lose
writes): <state> = $UNI_STATE_DIR, else %LOCALAPPDATA%/uni-os (Windows) or ~/.local/state/uni-os.
Environment given to command jobs: UNI_VAULT, UNI_OS_HOME, UNI_PYTHON, UNI_STATE_DIR,
UNI_JOB_START (starts another job through this script; "{job}" = id), UNI_DRY_RUN=1 on dry runs.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobconf as jc  # noqa: E402

KEEP_LOGS = 40
PERMISSION_MODES = {"bypass": "bypassPermissions", "accept-edits": "acceptEdits", "ask": "default"}
API_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")


class SetupError(Exception):
    """The job can't start as configured (e.g. no headless command for this agent): logged, exit 2."""


# ---------------------------------------------------------------------------- environment

def utf8_console() -> None:
    """Started by a scheduler or through UNI_JOB_START, stdout is a pipe, a file or NUL, and on
    Windows Python then encodes with the ANSI code page (cp1252): one check mark or arrow in a
    job's output would raise UnicodeEncodeError after the job ran. Use UTF-8 and replace what
    can't be written. pythonw has no streams at all (None): nothing to do."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def echo(text: str, end: str = "\n") -> None:
    """Print without ever failing: console output is a convenience, the run log is the record."""
    if sys.stdout is None:
        return
    try:
        print(text, end=end, flush=True)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        try:
            print(text.encode(enc, "replace").decode(enc, "replace"), end=end, flush=True)
        except (OSError, ValueError, LookupError):
            pass
    except (OSError, ValueError):  # closed or broken pipe
        pass

def state_dir() -> Path:
    env = os.environ.get("UNI_STATE_DIR")
    if env:
        return Path(env).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "uni-os"
    return Path.home() / ".local" / "state" / "uni-os"


def load_config(vault: Path) -> dict:
    """The vault's config. Prefer the generated uni-os.json (module defaults merged in, e.g.
    agent.cli and agent.permission_posture); fall back to the hand-edited uni-os.toml."""
    j = vault / "_agent" / "uni-os.json"
    try:
        data = json.loads(j.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    p = vault / "_agent" / "uni-os.toml"
    try:
        with p.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def find_bash() -> str | None:
    """Git Bash on Windows (never the WSL launcher in System32), /bin/bash elsewhere."""
    if os.environ.get("UNI_BASH"):
        return os.environ["UNI_BASH"]
    if os.name != "nt":
        return shutil.which("bash") or ("/bin/bash" if Path("/bin/bash").exists() else None)
    cands = []
    git = shutil.which("git")
    if git:
        g = Path(git).resolve()
        cands += [g.parent.parent / "bin" / "bash.exe", g.parent / "bash.exe"]
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        cands.append(Path(base) / "Git" / "bin" / "bash.exe")
    for c in cands:
        if c.exists() and "system32" not in str(c).lower():
            return str(c)
    return None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":  # os.kill(pid, 0) would TERMINATE the process on Windows
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(proc.pid, 9)
        except OSError:
            proc.kill()


def split_cmd(cmd: str) -> list[str]:
    """Split a command string for subprocess without a shell. On Windows shlex's non-POSIX
    mode keeps the quotes around a token; strip them so quoted paths with spaces work."""
    if os.name != "nt":
        return shlex.split(cmd)
    out = []
    for tok in shlex.split(cmd, posix=False):
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
            tok = tok[1:-1]
        out.append(tok)
    return out


# ---------------------------------------------------------------------------- locks

class Locks:
    """pid files in <state>/running/: '<pid> <mode>' per running job of this runner."""

    def __init__(self, state: Path, job: str):
        self.dir = state / "running"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{job}.pid"

    def others(self) -> list[tuple[str, str]]:
        out = []
        for p in self.dir.glob("*.pid"):
            if p == self.path:
                continue
            try:
                pid_s, _, mode = p.read_text().strip().partition(" ")
                if pid_alive(int(pid_s)):
                    out.append((p.stem, mode or "shared"))
                else:
                    p.unlink(missing_ok=True)
            except (OSError, ValueError):
                continue
        return out

    def acquire_job(self) -> bool:
        try:
            pid_s = self.path.read_text().split()[0]
            if pid_alive(int(pid_s)):
                return False
        except (OSError, ValueError, IndexError):
            pass
        self.path.write_text(f"{os.getpid()} none")
        return True

    def set_mode(self, mode: str) -> None:
        self.path.write_text(f"{os.getpid()} {mode}")

    def release(self) -> None:
        self.path.unlink(missing_ok=True)


def wait_agent_lock(locks: Locks, mode: str, wait_min: float, log) -> bool:
    """True = go. exclusive: no other agent job may run; shared: no exclusive holder."""
    if mode == "none":
        return True
    deadline = time.time() + wait_min * 60
    while True:
        others = [(j, m) for j, m in locks.others() if m in ("shared", "exclusive")]
        blocking = others if mode == "exclusive" else [o for o in others if o[1] == "exclusive"]
        if not blocking:
            locks.set_mode(mode)
            return True
        if time.time() >= deadline:
            if mode == "exclusive":
                log(f"skipped: other agent jobs still running after {wait_min:g} min: {blocking}")
                return False
            log(f"waited {wait_min:g} min for {blocking}; running anyway")
            locks.set_mode(mode)
            return True
        time.sleep(15)


# ---------------------------------------------------------------------------- agent command

def agent_command(cfg: dict, job: jc.Job, title: str, prompt_file: Path, args) -> tuple[list[str], bool]:
    """(argv, prompt_on_stdin)."""
    agent = cfg.get("agent", {})
    # Default = the config default ("accept-edits"). Unattended runs need "bypass": a run that
    # stops at an approval prompt does nothing (the log line below says so).
    perm = PERMISSION_MODES.get(args.permission or agent.get("permission_posture", "accept-edits"), "acceptEdits")
    model = job.get("MODEL")
    effort = job.get("EFFORT")
    template = args.agent_cmd or agent.get("headless_command", "")
    if template:
        filled = (template.replace("{model}", model).replace("{effort}", effort)
                  .replace("{permission}", perm).replace("{title}", title)
                  .replace("{prompt_file}", str(prompt_file)))
        argv = split_cmd(filled)
        return argv, "{prompt_file}" not in template
    primary = agent.get("primary", "claude-code")
    if primary != "claude-code":
        raise SetupError(f"agent.primary = {primary!r}: set agent.headless_command in the config "
                         "(placeholders {model} {effort} {permission} {title} {prompt_file}); "
                         "only Claude Code has a built-in default, and only it was tested.")
    cli = shutil.which(agent.get("cli", "claude")) or agent.get("cli", "claude")
    argv = [cli, "-p", "--permission-mode", perm, "--output-format", "text", "--name", title]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    return argv, True


# ---------------------------------------------------------------------------- run

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vault", required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--print-only", action="store_true", help="show what would run, run nothing")
    p.add_argument("--force", action="store_true", help="ignore PRECHECK and the failover marker")
    p.add_argument("--host-name", default=os.environ.get("UNI_HOST_NAME", "laptop"))
    p.add_argument("--permission", choices=sorted(PERMISSION_MODES), help="override agent.permission_posture")
    p.add_argument("--agent-cmd", help="override agent.headless_command")
    p.add_argument("--keep-api-env", action="store_true",
                   help="keep API-key variables (default: removed, so the CLI uses the plan login)")
    p.add_argument("--push-failures", action="store_true", help="push one line when the job fails")
    a = p.parse_args(argv)
    utf8_console()

    vault = Path(a.vault).expanduser().resolve()
    state = state_dir()
    job = jc.load_job(vault, a.job)
    cfg = load_config(vault)
    started = time.time()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_dir = state / "jobs" / job.id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{stamp}{'-dry' if a.dry_run else ''}.log"
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        echo(msg)

    def finish(code: int, summary: str | None = None) -> int:
        secs = int(time.time() - started)
        if not a.print_only:
            quiet = job.get("QUIET_OK") == "yes" and code == 0
            lines.append(f"# exit {code} after {secs}s")
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            if not quiet or summary:
                with (state / "jobs.log").open("a", encoding="utf-8") as fh:
                    when = datetime.now().strftime("%Y-%m-%d %H:%M")
                    what = summary or f"{'dry run | ' if a.dry_run else ''}exit {code}"
                    fh.write(f"{when} | {job.id} | {what} | {secs}s | {log_path}\n")
            for pattern in ("*.log", "*.prompt.md"):
                for old in sorted(log_dir.glob(pattern))[:-KEEP_LOGS]:
                    old.unlink(missing_ok=True)
            if code not in (0, 3) and a.push_failures and not a.dry_run:
                push = os.environ.get("UNI_PUSH_CMD")
                base = split_cmd(push) if push else \
                    [sys.executable, str(jc.framework_root() / "tools" / "uni_os.py"), "push"]
                try:
                    subprocess.run(base + ["--source", f"job:{job.id}", "--direct", "--id", f"job-failed:{job.id}",
                                           f"Laptop job {job.id} failed (exit {code}). Log: {log_path.name}"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                except OSError as exc:  # the record above is written; a broken push command can't undo it
                    echo(f"failure push not sent: {exc}")
        return code

    log(f"# job {job.id} ({job.title}) on {a.host_name}, {datetime.now():%a %Y-%m-%d %H:%M}"
        f"{' [dry run]' if a.dry_run else ''}")

    locks = Locks(state, job.id)
    if not a.print_only and not locks.acquire_job():
        echo(f"{job.id} is already running")
        return 0
    try:
        if jc.is_disabled(job):
            log("skipped: the job's module is disabled (DISABLED marker); remove the laptop task")
            return finish(0, "skipped | module disabled")
        if job.get("NEEDS_VAULT") == "yes" and not (vault / "_agent").is_dir():
            log(f"skipped: vault not reachable ({vault})")
            return finish(3, "skipped | vault not reachable")

        now = datetime.now()
        slot = jc.nominal_slot(job, now)
        slot_s = slot.strftime("%Y-%m-%d %H:%M") if slot else ""
        if slot_s and not a.force and jc.ran_marker_slot(vault, job) == slot_s:
            log(f"skipped: the always-on host already ran the {slot_s} slot")
            return finish(0, "skipped | host ran this slot")

        env = dict(os.environ)
        here = Path(__file__).resolve().parent
        env.update({
            "UNI_VAULT": str(vault), "UNI_OS_HOME": str(jc.framework_root()),
            "UNI_PYTHON": sys.executable, "UNI_STATE_DIR": str(state),
            "UNI_JOB_START": f'"{sys.executable}" "{here / "run_job.py"}" --vault "{vault}" --job {{job}}',
        })
        if a.dry_run:
            env["UNI_DRY_RUN"] = "1"
        bash = find_bash()

        if job.get("KIND") == "agent" and not a.print_only:
            if not wait_agent_lock(locks, job.get("AGENT_LOCK"), float(job.get("LOCK_WAIT_MIN") or 20), log):
                return finish(0, "skipped | agent lock")

        pre = job.get("PRECHECK").strip()
        if pre and not a.force:
            if bash is None:
                log("precheck not run: no bash found (set UNI_BASH); running the job")
            elif a.print_only:
                log(f"would run precheck: {pre}")
            else:
                r = subprocess.run([bash, "-c", pre], cwd=vault, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r.returncode != 0:
                    log("skipped / nothing to do (precheck)")
                    return finish(0, "skipped | precheck")

        timeout = float(job.get("TIMEOUT_MIN") or 45) * 60
        flags = {}
        if os.name == "nt":
            flags["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: no console flash
        else:
            flags["start_new_session"] = True

        if job.get("KIND") == "command":
            cmd = job.get("COMMAND")
            if a.dry_run:
                if job.get("DRY_OK") == "yes":
                    cmd += " --dry-run"
                else:
                    log(f"dry run: would run: {cmd}")
                    return finish(0)
            if bash is None:
                log("no bash found for a command job (install Git for Windows or set UNI_BASH)")
                return finish(2)
            if a.print_only:
                log(f"would run (bash, cwd vault): {cmd}")
                return 0
            argv_, stdin_text = [bash, "-c", cmd], None
        else:
            title = f"job: {job.title} · {now:%a %H:%M}"
            host = jc.Host(name=a.host_name, kind="laptop", vault=str(vault),
                           date_cmd=("powershell -NoProfile -Command \"Get-Date -Format 'ddd yyyy-MM-dd HH:mm K'\""
                                     if os.name == "nt" else "date '+%a %Y-%m-%d %H:%M %Z'"),
                           python=sys.executable, session="print")
            prompt = jc.assemble_prompt(vault, job, host, dry_run=a.dry_run)
            prompt_file = log_dir / f"{stamp}.prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            try:
                argv_, on_stdin = agent_command(cfg, job, title, prompt_file, a)
            except SetupError as exc:
                log(f"not started: {exc}")
                return finish(2)
            if not argv_:
                log("not started: the headless command is empty (agent.headless_command / --agent-cmd)")
                return finish(2)
            stdin_text = prompt if on_stdin else None
            if "bypassPermissions" not in argv_ and not (a.agent_cmd or cfg.get("agent", {}).get("headless_command")):
                log("note: not in bypass mode; a step that needs an approval will stop this unattended run")
            if not a.keep_api_env and not a.agent_cmd and not cfg.get("agent", {}).get("headless_command"):
                for k in API_ENV:
                    env.pop(k, None)
            if a.print_only:
                log("would run: " + " ".join(shlex.quote(x) for x in argv_))
                log(f"prompt: {prompt_file} ({len(prompt)} chars)")
                return 0

        log("$ " + " ".join(shlex.quote(x) for x in argv_))
        try:
            proc = subprocess.Popen(argv_, cwd=vault, env=env, text=True, encoding="utf-8", errors="replace",
                                    stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **flags)
        except OSError as exc:  # not on this task's PATH, a wrong agent.cli or headless_command
            log(f"could not start {argv_[0]}: {exc}")
            return finish(127)
        try:
            out, _ = proc.communicate(stdin_text, timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            out, _ = proc.communicate()
            lines.append(out or "")
            lines.append(f"timeout after {timeout / 60:g} min: killed")
            code = finish(124)  # the record first: echoing the output can never lose it
            echo(out or "")
            echo(f"timeout after {timeout / 60:g} min: killed")
            return code
        lines.append(out or "")
        code = finish(code)  # the record first: echoing the output can never lose it
        echo(out or "", end="")
        return code
    finally:
        if not a.print_only:
            locks.release()


if __name__ == "__main__":
    sys.exit(main())
