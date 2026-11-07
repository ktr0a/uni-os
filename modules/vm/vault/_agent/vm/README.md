---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# `_agent/vm/`: files the always-on host writes

Everything in this folder is written by the always-on host `{{vm.host_alias}}` (module `vm`), and only by it. Nobody else edits these files: the next health run overwrites them. When two hosts exist for a while (a move), exactly one of them writes here (`VAULT_WRITES=yes` in its host settings). About the host: [../vm.md](../vm.md).

| File | Written by | When | Read by |
|---|---|---|---|
| `status.md` | `uni-vm health` | when the overall state or the list of switched-on jobs changes, and once a day | agents, the coordinator, the student |
| `performance.md` | `uni-vm health` | once a day (yesterday's row), and after a new verdict | agents, the verdict job |
| `snapshot.json` | `uni-vm health` | every health run (every {{vm.health_every_min}} min), rewritten **in place** (same file id in the cloud drive) | dashboards, the heartbeat's pre-check |
| `ran/<task>.md` | `run-job` | after each failover run | the laptop copy of that task (skip a catch-up run) |

## Reading them honestly
- Every status names the time it was checked. A file older than its cadence is **old**, not fine: `status.md` older than ~26 hours or `snapshot.json` older than ~40 minutes means the host (or its health job) is not running.
- What no file can see is unknown, never green.
- `status.md` shows a problem only after it persisted 20+ minutes (no flapping rewrites); the live view is `uni-vm status`.

## `snapshot.json` (schema 1)
```json
{"schema": 1, "generated": "<ISO>", "writer": "uni-vm health", "host_name": "<name>",
 "host": {"uptime_s": 0, "mount_ok": true, "remote_control_ok": true, "agent_login_ok": true,
          "mem_total_mb": 0, "mem_available_mb": 0, "swap_used_mb": 0, "swap_total_mb": 0,
          "disk_used_pct": 0, "load_1m": 0.0, "load_5m": 0.0, "load_15m": 0.0},
 "laptop": {"online": true, "app_open": true, "seen": "<ISO or null>"},
 "jobs": [{"name": "<job>", "on": true, "mode": "always|failover", "schedule": "<human>",
           "last_run": "<ISO|null>", "exit": 0, "duration_s": 0, "next_run": "<ISO|null>", "last_skipped": "<ISO|null>"}],
 "job_sessions": [{"name": "<session>", "state": "idle|working", "idle_min": 0, "closes_after_h": 8, "started": "<ISO>"}],
 "roles": [{"role": "<id>", "title": "<title>", "state": "running|down|off", "model": "<model>"}],
 "sessions_total": 0, "alerts": ["<this run's problems>"]}
```
Rules: no links, no push topic, no emails, no paths outside the vault. `laptop.online` is `null` when the laptop's ping is stale (off and "app closed" look the same). `last_run`, `exit` and `duration_s` describe the last **finished** run (the job log's `# exit N after Ss` footer). The placeholder before the first write has `"generated": null`.

## `ran/<task>.md` (failover markers)
```
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
`slot` is the nominal scheduled minute (host timers start within ~21 s of it). A laptop task in failover mode starts with: "if `_agent/vm/ran/<task>.md` names the slot this run is for, reply that the host already ran it, and stop."
