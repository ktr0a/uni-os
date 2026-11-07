---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent, uni/jobs]
---
# Logs

Agent-written logs of jobs and agents live here, one file per job or tool: `_agent/logs/<name>-log.md` (for example `inbox-sync-log.md`, a prep log, a fetch log). Host-side run logs (full output, exit codes, timings) stay on the machine that ran the job, never in the synced vault: two machines appending to one file inside the sync window lose lines.

## Rules for every log here
- **Append only.** Never rewrite or delete a line. Fix a wrong line by appending a dated correction line.
- **One line per run that did something** (a job that found nothing to do logs nothing, unless its prompt says otherwise). One line per attempt for jobs whose prompt asks for it, even no-ops.
- **Local time** in Europe/Zurich, always with the date: `YYYY-MM-DD HH:MM`. Convert UTC from tools first.
- Say **where and as what** it ran: `(job <id>, <host>, slot YYYY-MM-DD HH:MM)`, or `(not a job run)` / `(<session title>, not a job run)` for an interactive session doing a job's work.
- Say what changed (paths, and what in them), what was skipped and why, what waits on someone. Use the job's fixed vocabulary for problems (for example `PARKED`, `WAITING`, `REFUSED`, `skipped`).
- No secrets, no personal details beyond what the vault already holds, no full private URLs (name the host, not the address).
- Keep the properties block (`type: log`, `audience: agent`) at the top; no `updated:` property is needed on a log.

## Line shape
```
- YYYY-MM-DD HH:MM (job <job-id>, <host>, slot YYYY-MM-DD HH:MM): <what was done>. Files changed: `<path>` (<what>). <Skipped/parked/waiting: ... | Nothing skipped.>
```
