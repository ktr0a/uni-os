# Maintaining the always-on host

Day-2 operations: logins, updates, resizing, backups, budget, moving work, the developer rules, troubleshooting and removal. Commands run on the host (`ssh uni-vm`, or `bash modules/vm/laptop/vm.sh '<cmd>'` from Git Bash, or `uni-vm ...` from any Windows terminal) unless marked "laptop".

## Logins

### Drive (rclone)
Needed only when the token is revoked: a password change, "remove access" in your Google account, 6 months unused, or an OAuth app still in "Testing" (7-day tokens: publish it "In production").
1. laptop: `ssh -N -L 53682:127.0.0.1:53682 uni-vm` (leave it running).
2. host (`<drive-remote>` is `vm.drive_remote`, default `uni-drive`; `uni-vm hostenv get DRIVE_REMOTE` shows it):
   ```bash
   source ~/.config/uni-os/drive-client.env
   rclone config create <drive-remote> drive client_id="$RCLONE_CLIENT_ID" client_secret="$RCLONE_CLIENT_SECRET" \
     scope=drive root_folder_id=<vault-folder-id> config_is_local=true
   ```
3. Open the printed `http://127.0.0.1:53682/auth?state=...` link on the laptop, pick the account, "Advanced" -> "Go to <app> (unsafe)" -> Continue.
4. `uni-vm restart drive` (this also restarts Remote Control: it ends open sessions).

### Agent (Claude Code)
1. `claude auth login`: it prints a URL; open it on the laptop, sign in, authorise, paste the code into the host terminal.
2. `uni-vm restart rc` (ends open sessions; ask first).
`uni-vm status` shows "Agent login OK" with the plan. Never set an API key on the host.

### Push topic
To change it: write the new topic into `~/.config/uni-os/ntfy-topic` on the host (and the laptop) without printing it, subscribe the phone, `uni-vm notify "test"`. Anyone who knows the topic can read the pushes: it is a password.

## Updating
- **The framework copy:** git clone -> `uni-vm update` (pull, then the installer). Laptop copy -> laptop: `bash modules/vm/laptop/deploy.sh` (drift stop, then install). Both are safe to re-run and restart no service.
- **What needs a restart:** changes to `rc-loop` or the systemd units take effect only after `uni-vm restart rc` / `systemctl --user restart <unit>` (ends sessions: only with the student's go; `deploy.sh --restart-rc` does it right after the deploy). Job files take effect at the next run after `uni-vm jobs sync`. Role.conf changes at the next start or resume.
- **Job changes in the vault:** `uni-vm jobs sync` (prints what changed; new jobs need `--accept-new`). `uni-vm doctor` flags drift.
- **The agent CLI** updates itself (Claude Code: the stable channel). The running Remote Control server keeps the old binary: the health check restarts it in the quiet hour (`vm.rc_update_hour`) when the binary changed. Role sessions pick up the new version at their next resume.
- **Ubuntu** installs security updates every night and reboots at 04:30 only when a kernel needs it (never on WSL). After a reboot everything comes back by itself within about a minute: mount, Remote Control, the tmux holders, and every switched-on role (resumed from its transcript).

## Resizing (Google Cloud)
About 2 minutes of downtime; Remote Control and the roles come back by themselves. laptop:
```bash
gcloud compute instances stop <vm-name> --zone <zone>
gcloud compute instances set-machine-type <vm-name> --zone <zone> --machine-type e2-custom-small-6144
gcloud compute instances start <vm-name> --zone <zone>
```
Then set `vm.machine_type` in the config (the verdict prices the next step from it). Options and prices: README "Cost and sizing"; the weekly verdict re-prices them.

## Pausing
laptop: `gcloud compute instances stop <vm-name> --zone <zone>`. A stopped VM costs only its disk and snapshots (about $1/month for 30 GB standard). Before stopping, move the jobs back to the laptop (below), or they simply don't run. `... start ...` brings everything back.

## Backups and restore
- **Disk:** weekly snapshots (Sunday ~02:00 UTC, 21 days). Restore: Compute Engine -> Snapshots -> create a disk from one -> stop the VM -> detach the boot disk -> attach the new one as boot disk -> start. Or create a new VM from the snapshot.
- **Notes:** the cloud drive keeps file versions and a trash; the host's hourly notes history has every text note: `uni-vm history <note>`, `uni-vm history show <rev> <note> > /tmp/old.md`, then restore by hand (re-read the live file first).
- **Host state worth keeping** (not in the vault): `~/.local/state/uni-os/` (logs, perf data, verdicts), `~/.config/uni-os/` (settings, role confs, secrets), `~/.claude/projects/` (role transcripts). The snapshot covers them.

## Budget
- The billing budget mails at 50/90/100 % and forecast 100 %. If it fires: check Billing -> Reports for what grew (a bigger machine, egress, a forgotten disk or IP).
- Cheaper: a 1-year committed-use discount for the machine part (~37 % off; billed even while stopped; only after a month of real use), a smaller machine if the verdict says "enough" with room, deleting unrelated old resources in the same billing account, checking that a subscription's monthly cloud credit is applied.
- Emergency: `uni-vm jobs off all` (stops agent usage) or stop the VM.

## Moving work between the laptop and the host
- **A job runs on exactly one machine.** To move one: pause it at one side and switch it on at the other, back to back, never around one of its slot times (in mode `always` nothing stops a double run).
- Laptop -> host: `uni-vm jobs on <job>` right after pausing the laptop copy. Host -> laptop: re-enable the laptop copy, then `uni-vm jobs off <job>`.
- **Failover mode** (`uni-vm jobs mode <job> failover`) keeps both copies on, with the host running only missed slots. It needs the laptop ping (`install-laptop.ps1 -LaptopPing`) and the "skip if the host's ran-marker names this slot" first step in the laptop copy of the prompt.
- **Roles:** `uni-vm roles stop <role>` keeps the conversation; to move a role to another host use `home-server/move-role.sh`; to move it back to the laptop, stop it here and start a laptop session with a handover note (the brief is the same).
- After a change, update `_agent/vm.md` if it describes something that changed, and tell the coordinator session.

## Releasing a new recurring job (the original's staged pattern)
A new recurring job is the student's yes, and the original released its biggest one (the heartbeat watcher) in stages, a pattern worth reusing for any job that pushes or writes shared files (the short version is in [README.md](README.md), "Releasing a new agent job"):
0. **Build report:** the builder writes what it built, how it was checked, which tools it probed on this host, open questions with proposed defaults, and the changes it needs in files it doesn't own (listed, not made).
1. **Staged:** the job folder exists in the vault (module installed), but its timer stays off (`DEFAULT_MODE="off"`, or `uni-vm jobs off <job>` right after `jobs sync`).
2. **Dry runs at representative times:** `uni-vm jobs run <job> --dry-run`, at least once when there is something to do and once when there isn't. Read the log (what it WOULD have changed) and watch memory meanwhile (`free -m` every few seconds, or the process tree's RSS): the original measured ~4 minutes and ~300 MB for one agent dry run, which decided whether it fit next to the role sessions.
3. **Guard dry run shortly before the agreed switch-on time,** judged by fixed checks, not by eye: run-job exited 0, the run's log ends `# exit 0 after Ns`, no Python traceback in it, the job's state files parse (e.g. `jq -e '.schema == 1'`), it wrote its log line, and the push gate refused nothing (a refused push is a bug in the job's wording). If any check fails, the switch-on doesn't happen and the student gets one line; either way a short summary goes into the vault.
4. **Switch on at an agreed time,** right after a slot rather than just before one: by hand, or with a one-off timer, e.g. `systemd-run --user --on-calendar="2026-11-16 07:40" --timer-property=Persistent=true "$HOME/.local/bin/uni-vm" jobs on <job>` (Persistent: it still fires if the host was down at that minute).
5. **Rollback** = `uni-vm jobs off <job>`; the job's own state stays for the next attempt.

## Changing the host's settings
- Vault-wide values (`[vm]` in the config): edit the config, then re-run the installer (`uni-vm update`, or deploy).
- Host-only values: `uni-vm hostenv set KEY VALUE` (written below the "local overrides" marker of `host.env`; later lines win), then re-run the installer if it touches units or agent files (`RCLONE_*`, `DRIVE_READ_ONLY`, `AGENT_*`, `RC_*`).
- `uni-vm hostenv show` prints the file (no secrets in it).

## Developer rules (for the student and for agents changing the host)
**Change flow:** edit in the framework (laptop clone or the repo), never the copy on the host (a deploy refuses to overwrite hand fixes: the drift stop); deploy or update; re-run `bash modules/vm/tests/run-tests.sh`; dry-run the job you touched (`uni-vm jobs run <job> --dry-run`).

**Testing:**
| Want | Do |
|---|---|
| Look at everything (read-only) | `uni-vm doctor` (no agent, a few seconds), `uni-vm status` |
| Tool logic | `bash ~/uni-os/modules/vm/tests/run-tests.sh` (fake HOME, fake agent, fake systemctl; every push into a file) |
| A job without effects | `uni-vm jobs run <job> --dry-run`: agent jobs read for real and change nothing (an instruction, not a sandbox: it uses plan usage); command jobs honour `DRY_OK` |
| Read-only probes | `outcome-checks --dry-run`, `uni-vm snapshot`, `uni-vm roles`, `uni-vm jobs sync --check`, `vault-history --dry-run` |
| Every new push path | give it an env override that appends to a file (`UNI_PUSH_FAKE_SEND`), and test with that |

Not checks: `uni-vm health` (repairs, restarts, pushes, writes vault files), `uni-vm jobs run <job>` without `--dry-run` (real work), `uni-vm notify`.

**Never without a clear go from the student:**
- restarting `uni-rc` or `uni-roles` (`uni-vm restart ...`, `deploy.sh --restart-rc`), `uni-vm roles restart|stop`, `uni-vm jobs close`, killing tmux sessions: all of them end conversations. (The health check itself restarts Remote Control only on a dead mount, after two failing checks, and in the quiet hour after an update.)
- deleting, renaming or overwriting anything under the vault mount (a real cloud delete);
- keys, tokens, emails, calendar feed addresses or the push topic in the vault, the framework, docs, logs or pushes;
- running a job on two machines;
- a push that says "all good" or carries personal details.

**Who decides:**
| Change | Who |
|---|---|
| A new recurring job, a schedule change, moving a job between machines, a new kind of push | the student's yes first |
| A job's prompt | through the module that owns it (or the coordinator), then `uni-vm jobs sync` |
| `_agent/vm/status.md`, `performance.md`, `snapshot.json`, `ran/` | written by the host only: never edited by anyone |

**Gotchas while working on the host:** before any `tmux send-keys`, `capture-pane -p` that exact target and look; a hook or settings change reaches running sessions; a `/model` switch must also go into the role.conf; every edit of the rules or role briefs makes every session re-read them (no cosmetic edits); `uni-vm grep` reads the hourly copy (open the hit before relying on it); `status.md` changes only on a state change and once a day.

## When something is wrong
| Question | Look |
|---|---|
| Anything | `uni-vm doctor`, then `uni-vm status` |
| A job failed or didn't run | `uni-vm jobs` (last run), `uni-vm jobs log <job>` (ends `# exit N after Ss`), `~/.local/state/uni-os/jobs/<job>/` (last 40 logs), `uni-vm logs jobs` |
| Exit 0 but no result | `outcome-checks --dry-run`; the job log; the module's state files in the vault |
| When does it run next | `uni-vm jobs next` |
| A job session is open or stuck | `uni-vm jobs sessions`; screen: `tmux -L uni-jobs capture-pane -p -t <name>` |
| A role session is down | `uni-vm roles`, `uni-vm logs roles`; screen: `tmux -L uni-roles capture-pane -p -t <role>` |
| Remote Control, drive, health | `uni-vm logs rc`, `uni-vm logs drive`, `uni-vm logs health`; `~/.local/state/uni-os/alerts/` |
| Which pushes went out | `uni-vm logs notify` (also failed sends), `~/.local/state/uni-os/outcomes/log` |
| Memory | `uni-vm perf 24h` or `7d`, `_agent/vm/performance.md` |
| An old version of a note | `uni-vm history <note>`, `uni-vm history show <rev> <note>` |
| The vault-side view | `_agent/vm/status.md`, `_agent/vm/performance.md` (may lag hours) |
| Logins, resize, rebuild | this page; README "Rebuild from scratch" |

## Remove things
Each step is independent; pick what you want gone.
| Remove | How |
|---|---|
| Just the scheduled jobs | first re-enable the laptop copies of the jobs you moved, then `uni-vm jobs off <job>` for each (back to back). `uni-vm jobs off all` also stops `vm-health` and `vault-history` |
| Interactive job sessions (back to headless) | set `SESSION="print"` in the job's module (or its `job.conf` in the vault), `uni-vm jobs sync` |
| A role session | `uni-vm roles stop <role>` (keeps the conversation); `rm ~/.config/uni-os/roles/<role>.conf` to forget it |
| The laptop ping / `uni-vm.cmd` | laptop: `install-laptop.ps1 -Uninstall` |
| The re-read hook | `jq 'del(.hooks.UserPromptSubmit)' ~/.claude/settings.json` (and it comes back with the next install unless you remove it from `install-user.sh`) |
| The whole VM | Cloud console -> Compute Engine -> the VM -> turn off deletion protection -> Delete; Snapshots: delete `<vm-name>-weekly` ones; the snapshot schedule |
| The cloud project | IAM & Admin -> Settings -> Shut down (removes the VM, the OAuth app, the budget link) |
| The budget alert | Billing -> Budgets & alerts -> delete |
| The host's drive access | your Google account -> Security -> Third-party connections -> the app -> Remove access |
| The host's agent login | `claude auth logout` on the host, or in the account's device list |
| Laptop ssh setup | remove the `Host uni-vm` block from `~/.ssh/config` and the `~/.ssh/uni-vm*` key files |
| The tunnel speed-up | remove the `CLOUDSDK_PYTHON_SITEPACKAGES` user environment variable |
| Vault traces | `uni-os disable vm`; then archive `_agent/vm.md` and `_agent/vm/` by hand if you like |
