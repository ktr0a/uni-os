---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent, uni/jobs]
---
# Jobs: what runs on a schedule, and how

A **job** is a scheduled unit of work: an unattended agent prompt (`KIND="agent"`) or a plain command (`KIND="command"`). Each enabled module renders its jobs into a folder here, `_agent/jobs/<job-id>/`, with a `job.conf` (when and how) and, for agent jobs, a `prompt.md` (the complete unattended prompt). Hosts read the jobs from here: the laptop's scheduler (module scheduler-local){{#if modules.vm}} and the always-on host's job runner (module vm){{/if}}. Jobs act on their own; role sessions don't. A duty that must happen at a time needs a job.

The list of jobs with their schedules: run `python <framework>/modules/scheduler-local/scripts/list_jobs.py --vault "<vault>"` (or ask any agent to). Which host runs which job right now, kept by hand: {{#if modules.roles}}the "Scheduled jobs" table of [../coordinator-state.md](../coordinator-state.md){{else}}section 4b "Where each job is switched on now" of [../system-handbook.md](../system-handbook.md){{/if}} (the handbook's section 3 lists only where each job *can* run){{#if modules.vm}}; the always-on host's live on/off state is `uni-vm jobs`{{/if}}.

## job.conf in one table
Shell-style `KEY="value"` lines. Values in double braces were filled from `_agent/uni-os.toml` at install: to change a schedule, change the config and re-render the module's files with the framework, then update the host's scheduled task. Never hand-edit a schedule in two places: in the original, a later sync silently reverted a hand change made in one of them.

| Key | Meaning |
|---|---|
| `TITLE` | shown in logs and session titles ("job: TITLE · Ddd HH:MM") |
| `KIND` | `agent` (runs `prompt.md` with the host's agent CLI or app) or `command` (runs `COMMAND` with bash from the vault root) |
| `SLOTS`, `DAYS`, `DATES` | local start times "HH:MM, HH:MM", weekday subset, optional date ranges `YYYY-MM-DD..YYYY-MM-DD;...` |
| `EVERY_MIN` | fixed interval in minutes for polling jobs (laptop schedulers read it) |
| `SCHEDULE` | raw systemd OnCalendar strings for the always-on host; overrides SLOTS/DAYS/DATES there |
| `SESSION` | `print` = headless, asks the student nothing (default); `rc` = an interactive remote session the student can open from the phone (each new one notifies the phone: only for jobs that must talk to the student) |
| `MODEL`, `EFFORT`, `TIMEOUT_MIN` | agent model (empty = host default), effort, hard timeout |
| `NEEDS_VAULT` | `yes` = skip with exit 3 if the vault isn't reachable |
| `PRECHECK` | a bash test run from the vault root; non-zero = skip without starting the agent (the main cost saver) |
| `QUIET_OK`, `DRY_OK` | log only failures; a command that honours `--dry-run` |
| `NOTIFY_DONE`, `NOTIFY_GATE` | push after the first turn of an `rc` job / through the push gate |
| `AGENT_LOCK`, `LOCK_WAIT_MIN` | `shared` / `exclusive` / `none`: keeps heavy agent jobs from running side by side |
| `LAPTOP_TASK`, `FAILOVER_DELAY_MIN`, `MARKER` | failover between laptop and always-on host (below) |
| `RUNTIME`, `DEFAULT_MODE` | where the job is meant to run (`any`, `laptop`, `vm`); initial state when installed (`off`, `always`, `failover`) |

## How this vault's laptop runs jobs
Configured: `runtime.laptop_scheduler = "{{runtime.laptop_scheduler}}"` (`agent-app`, `os` or `none`).

**`agent-app`: the agent's desktop app runs agent jobs as scheduled tasks.** In Claude Code: the setup agent creates one desktop "Scheduled" task per agent job (task id = job id) from the output of `list_jobs.py prompt <job>` (this folder's `_header.md` + the job's `prompt.md`) and the cron line from `list_jobs.py cron <job>`, from a session in the highest permission mode the student allows. Know the quirks:
- Tasks run **only while the app is open**; a task due while the app was closed runs at the next launch, and missed slots are **caught up when the laptop wakes** (a 19:30 slot ran at 20:01). Every prompt therefore computes its nominal slot and checks "already done?" first.
- Recurring tasks start a few minutes after the nominal time (a fixed offset for load balancing; late starts of ~12 minutes were seen).
- One cron expression can't mix minute values: 07:50 and 13:05 need two tasks with the same prompt.
- A task created from a bypass-mode session is saved in bypass mode and runs unattended; "auto" mode blocked writes to the synced vault, and a task that stops at an approval prompt does nothing.
- A push sent by a task may be held back while the student is active at the computer.
- Messaging other sessions from a scheduled task: In Claude Code `SendMessage` was refused there (the older `send_message` tool worked). Prefer the vault or the inbox for hand-offs.
- Command jobs can't run as app tasks (an app task runs a prompt; wrapping a frequent command in an agent run wastes usage). They need an OS scheduler or the always-on host.

**`os`: an OS scheduler runs `run_job.py`** (experimental). Windows Task Scheduler (the documented default; `list_jobs.py windows <job>` prints the PowerShell that registers a task) starts `python <framework>/modules/scheduler-local/scripts/run_job.py --vault "<vault>" --job <job-id>`, which applies `PRECHECK`, the failover marker, locks and the timeout, then runs the agent CLI headless or the command, and logs on the laptop (never in the vault). cron and launchd work the same way; see the module's README for porting notes.

**`none`:** nothing runs on the laptop; jobs run on the always-on host or not at all.

## The anatomy of a good unattended prompt
Every `prompt.md` follows this order (extracted from the original's best prompts):
1. **Idempotency guard first:** compute the nominal slot (the latest scheduled time at or before now, without the scheduler's offset) and stop with one line if a marker, a state file or the target file says it already ran.
2. **Identity and scope in one paragraph:** who you are, which vault, which language, that you run unattended.
3. **Read the contract before acting:** point to the runbook, conventions and rules files instead of inlining them. Behaviour lives in versioned vault docs; the prompt stays short.
4. **Get the real time explicitly** with a command; compute the term week from week 0.
5. **Branch by slot** (e.g. first slot = full run, later slot = change check) and add a **catch-up rule** (if an earlier slot's work is missing, do it too).
6. **Spell out tool constraints:** which connector, which calendars are read-only, "if the connector refuses, don't work around it with keys or feeds", or "run exactly this command and nothing else".
7. **Write rules for shared files:** re-read right before editing, small local edits, keep the properties block and bump `updated:`, append-only logs, never edit files in fixed locations, new revisions as new files (`-rN`) instead of edits.
8. **Integrity rules repeated** where the job could touch graded work.
9. **Privacy rules:** no secrets, keys, emails or private calendar addresses in any file; private folders are never opened.
10. **Interactive jobs in two turns:** turn 1 reads everything and asks once (one line per course, answer options, never guess numbers), sends one push and ends the turn; turn 2 applies the answer and replies with a summary.
11. **Delegation with a fallback:** message the owning session; if that fails, do it yourself or leave the item and log `WAITING`.
12. **Notification discipline:** most jobs send nothing ("the log is the record"); never "all good"; one line that leads with the action when a push is needed.
13. **Output contract:** a fixed final line or "reply in at most N lines"; one log line per run that did something, even for a no-op where the job says so.

## Failover between laptop and always-on host
{{#if modules.vm}}
A job can run in one of two modes on the always-on host: `always` (only the host runs it; the laptop task is paused) or `failover` (the laptop runs it; the host runs a copy only if the laptop missed the slot). In failover mode the host writes a **ran marker** after each run it does in the laptop's place:

```
_agent/vm/ran/<job-id>.md
---
type: agent
audience: agent
updated: YYYY-MM-DD
tags: [uni/agent]
---
slot: YYYY-MM-DD HH:MM
ran_on_host: YYYY-MM-DD HH:MM
exit: N
```
Every laptop run starts with the failover check in [_header.md](_header.md): if the marker names this run's slot, it stops ("Skipped: another host already ran the <slot> slot"). That stops the desktop app's wake-up catch-up runs from repeating a slot. In mode `always` no markers are written, so a job must never be active on both machines: switch one off and the other on back to back, never around a scheduled time. The original settled on `always` for every recurring job: the always-on host runs them, the laptop keeps only what needs the laptop.
{{else}}
Only relevant with an always-on host (module vm): a ran marker `_agent/vm/ran/<job-id>.md` with `slot: YYYY-MM-DD HH:MM` lets the laptop skip a slot the host already ran.
{{/if}}

## Logs and outcomes
- Jobs that change the vault append one line per run that did something to their own log in `_agent/logs/` ([../logs/README.md](../logs/README.md)).
- Run logs (stdout, exit codes) stay on the host that ran the job, never in the synced vault.
- **Exit 0 is not success.** It says the job ended, not that its result exists. Outcome checks look for the result (a prep note exists by its deadline, no inbox note waits longer than its threshold) and push only on a problem.
