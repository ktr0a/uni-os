# `modules/vm/host/`: the code that runs on the always-on host

Shipped as is (never templated, never copied into the vault). Every script reads one settings file, `~/.config/uni-os/host.env`, written by `install-user.sh` from the vault config plus a few answers; nothing personal is in these files. Full documentation: [../README.md](../README.md); setup: [../INSTALL.md](../INSTALL.md).

| Path | Run by | Purpose |
|---|---|---|
| `bootstrap-root.sh` | root, once (re-runnable) | base system: packages, zram + swap, Node, rclone, Chrome, timezone, linger, upgrades; WSL-aware |
| `install-user.sh` | the user, at every install/update | settings, links, units, mount, agent config, jobs sync, services; never restarts a running service |
| `host.env.example` | (reference) | what the settings file looks like |
| `lib/common.sh` | sourced | settings, paths, vault check, pushes, transcript and tmux helpers |
| `lib/jobconf.sh` | sourced | job.conf defaults and loading, SLOTS/DAYS/DATES -> OnCalendar, the DATES guard, timer text |
| `lib/vaultconf.py` | install, uni-vm | vault config -> host.env, `@@KEY@@` rendering, the notes-history filter file |
| `bin/uni-vm` | everyone | the control tool (`uni-vm help`) |
| `bin/run-job` | `uni-job@<job>.service`, `uni-vm jobs run` | runs one job |
| `bin/rc-loop` | `uni-rc.service` | keeps the agent's remote-control server running in the vault |
| `bin/role-sessions` | `uni-roles.service`, health, `uni-vm roles` | persistent role sessions |
| `bin/vault-history` | job `vault-history` | hourly git snapshot of the vault's text notes |
| `bin/doctor` | `uni-vm doctor` | one read-only look at everything |
| `bin/outcome-checks` | health | did the jobs' work happen? pushes problems through the gate |
| `bin/brief-nudge` | the agent's prompt hook | one fixed sentence when the rules or a role brief changed |
| `bin/uni-browse` | sessions | headless Chrome for public JavaScript pages |
| `systemd/*.service` | install renders them | `uni-drive` (rclone mount), `uni-rc`, `uni-jobs`, `uni-roles` (tmux servers with OOM priorities), `uni-job@` (one job run) |
| `agent/` | install renders them | machine notes for every session (`AGENTS.md`; `CLAUDE.md` imports it), the job header, the role start prompt, slash commands |
| `roles/` | (reference) | the `role.conf` format |

Conventions: bash with `set -uo pipefail`, quoted paths everywhere (folder names may contain spaces and `&`), every push path (`uni_notify`, `uni_push_gate` in `lib/common.sh`) and every helper that writes job output (`outcome-checks`, `vault-history`) honours `UNI_DRY_RUN=1` (host management such as `uni-vm jobs on|off|sync` and the installer doesn't read it), every push path has a file-based fake (`UNI_PUSH_FAKE_SEND`) for tests, state in `~/.local/state/uni-os/`, nothing secret in logs.
