# Porting the laptop scripts to macOS or Linux

Most of Uni OS is operating-system neutral: Markdown templates, agent prompts, and Python 3.11+ standard-library scripts that run on Windows, macOS and Linux. The always-on host is Linux (Ubuntu 24.04). Only a few **laptop** pieces are Windows-specific, and they are **experimental**: PowerShell 5.1 scripts, Windows Task Scheduler tasks, VBS launchers, toasts and the Recycle Bin. They were kept Windows-only on purpose, as in the original system; instead of shipping untested macOS and Linux versions, each piece has a precise behaviour specification so that your own agent can port it.

This page lists every Windows piece, what it does, what it touches, and the macOS and Linux equivalents, followed by a porting checklist and how to test a port. Uni OS has only been tested with Claude Code on Windows 11; ports are untested by definition.

## What is Windows-specific

| Piece | Module | Files | Needed for |
|---|---|---|---|
| Vault watcher | [vault-watch](../modules/vault-watch/README.md) | `scripts/vault-watch.ps1`, `scripts/vault-watch-launcher.vbs`, `scripts/register-task.ps1` | drift and official-file alerts on the laptop |
| Course file pick-up | [course-files-fetch](../modules/course-files-fetch/README.md) | `scripts/course-pickup.ps1`, `scripts/course-pickup-launcher.vbs`, `scripts/install-course-pickup.ps1` | filing browser downloads into the vault |
| OS-scheduler path for jobs | [scheduler-local](../modules/scheduler-local/README.md) | `scripts/run_job.py` (portable Python with Windows branches), the Task Scheduler snippet printed by `scripts/list_jobs.py windows <job>` | running jobs with the agent app closed (`runtime.laptop_scheduler = "os"`) |
| Laptop helpers for the host | [vm](../modules/vm/README.md) | `laptop/laptop-ping.ps1` (+ `laptop-ping-launcher.vbs`), `laptop/install-laptop.ps1`, `laptop/uni-vm.cmd` | failover mode, and `uni-vm` from a Windows terminal |
| Home-server setup | vm | `home-server/setup-home-server.ps1` (+ `.cmd`), `home-server/register-wsl-keepalive.ps1`, `home-server/wslconfig.example.ini` | WSL2 on a spare Windows laptop; Windows by nature: on a Linux box, install Ubuntu natively and follow `INSTALL.md` instead |

Already portable, no work needed: `request_pickup.py` (course-files-fetch), `run_job.py` and `list_jobs.py` themselves (scheduler-local), `laptop/vm.sh` and `laptop/deploy.sh` (bash; on macOS and Linux they use the system ssh), every `uni-os` command, every other module script.

## Cross-cutting equivalents

The same handful of Windows mechanisms appear in several scripts:

| Windows mechanism | Used by | macOS | Linux |
|---|---|---|---|
| Task Scheduler: daily triggers, "at logon" with a delay, "start when available", "ignore new instance", execution time limit | all scheduled scripts | a LaunchAgent plist in `~/Library/LaunchAgents/`: `StartCalendarInterval` (one dict per time, `Weekday` 1 = Monday ... 0 or 7 = Sunday), `StartInterval` (seconds) for "every N minutes", `RunAtLoad` for "at login"; launchd runs a calendar slot missed during sleep once after wake | a systemd **user** timer: `OnCalendar=` one line per time, `Persistent=true` (runs a missed slot at the next start), `OnStartupSec=` for "after login", `OnUnitActiveSec=` for "every N minutes"; the service `Type=oneshot` with `TimeoutStartSec=`. Or cron (no catch-up; use anacron) |
| VBS launcher (`wscript.exe //B`, window style 0) so no console flashes | vault-watch, course pick-up, laptop ping | not needed | not needed |
| `pythonw.exe` and `CREATE_NO_WINDOW` (no console window) | `run_job.py`, `list_jobs.py windows` | plain `python3` | plain `python3` |
| Named mutex (`UniOS-VaultWatch`, `UniOS-CoursePickup`) | vault-watch, course pick-up | `fcntl.flock` on a lock file in the state folder | `fcntl.flock`, or `flock -n` in the unit |
| WinRT toast (`Windows.UI.Notifications.ToastNotificationManager`) | vault-watch | `osascript -e 'display notification "<text>" with title "<title>"'`, or `terminal-notifier` | `notify-send "<title>" "<text>"` (libnotify; a systemd user unit has the user's D-Bus session) |
| Recycle Bin (`Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile(..., SendToRecycleBin)`) | course pick-up | `/usr/bin/trash` (macOS 14+), the `trash` tool, or Finder via `osascript` | `gio trash <file>`, or the freedesktop trash folder `~/.local/share/Trash` |
| NTFS `Zone.Identifier` stream (`HostUrl=`, `ReferrerUrl=`), the browser's "mark of the web" | course pick-up | extended attribute `com.apple.metadata:kMDItemWhereFroms`, a binary property list usually `[download URL, referrer]` (`xattr -px` plus `plistlib`, or `mdls -name kMDItemWhereFroms`) | Chrome/Chromium write `user.xdg.origin.url` and `user.xdg.referrer.url` where the file system supports user xattrs (`os.getxattr`; check with `getfattr -d <file>`) |
| `LastWriteTimeUtc.Ticks` (modified time, 100 ns ticks) | vault-watch snapshots | `st_mtime_ns` | `st_mtime_ns` |
| `GetCreationTime` | vault-watch (stale inbox notes) | `st_birthtime` | `st_ctime` is not creation time: use the script's own first-seen time only |
| `Get-FileHash -Algorithm SHA256` | course pick-up | `hashlib.sha256`, `shasum -a 256` | `hashlib.sha256`, `sha256sum` |
| `FileMode.CreateNew` (copy can never overwrite) | course pick-up | `open(dest, "xb")` | `open(dest, "xb")` |
| Downloads known folder | course pick-up | `~/Downloads` | `xdg-user-dir DOWNLOAD` |
| Install and state under `%USERPROFILE%\Documents\uni-os\...` | vault-watch, course pick-up | `~/Library/Application Support/uni-os/...` | `~/.local/state/uni-os/...` (state) or `~/.local/share/uni-os/...` (scripts) |
| `%LOCALAPPDATA%\uni-os` (runner state, job logs, push gate) | `run_job.py`, `uni-os push`, heartbeat | `~/.local/state/uni-os` (already the default off Windows) | `~/.local/state/uni-os` (already the default) |
| Git Bash for `PRECHECK` and `COMMAND` (never the WSL launcher in System32; override `UNI_BASH`) | `run_job.py` | `/bin/bash` | `/bin/bash` |
| `taskkill /T /F` (kill the process tree on timeout) | `run_job.py` | `os.killpg` (already used off Windows) | `os.killpg` (already used) |
| Google Drive for desktop at `G:\My Drive\...` | everything that reads the vault | `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/...` | no official client: an rclone mount (keep the half-mount guard) or `rclone bisync` |

Two more rules carry over unchanged: text files the tools parse are UTF-8 **without** BOM (PowerShell 5.1 writes ANSI or BOM by default; a BOM once broke a JSON loader), and the machine's clock must be in the term's time zone (`term.timezone`), because schedulers use local time.

## Script by script

### Vault watcher (`modules/vault-watch/scripts/vault-watch.ps1`)

The full contract (11 numbered sections: inputs, triggers, outputs, state files, algorithm, scope rules, every alert key and text, the expected-files table, safety checks, exit codes, switches) is in the module README, "Behaviour specification". That README section, not the PowerShell, is what a port must match. Summary:

| | |
|---|---|
| Purpose | Diff the vault's file **metadata** a few times a day in two scopes (notes; official sources), log every change for agents, alert only on what needs action: stale or unsorted inbox items, sync conflict copies, deleted agent files, missing prep notes, new, deleted, moved or overdue official files, changes in frozen archives, new top-level folders. |
| Inputs | vault root (`-Root`, else `vault` in `vault-watch.local.json`); `<vault>/_agent/uni-os.json` (read every run); `<vault>/_agent/vault-watch/sources-expected.json` (optional); file names, sizes and modified times. Never file contents. |
| Outputs | `<vault>/_agent/vault-watch/log.md` (one line per run and scope), `alerts.md` (one line per alert), `sources-inventory.tsv`; toasts (one per alert, or one summary toast above `toast_summary_over`); optionally one push per run through `uni-os push` (no file names; `stale:` and `prep-` alerts not counted). |
| Triggers | daily at each time in `schedule.vault_watch`, plus at logon after `vault_watch.logon_delay_min` minutes; missed slots run on wake; never two runs at once; 10-minute limit; only while the user is logged on; allowed on battery. |
| State | in the install folder, which must be outside the vault (else exit 2): `snapshot.json`, `snapshot-sources.json`, `state.json`, `state-sources.json` (atomic writes: temp file then rename; state before snapshot), `local-log.txt`. |
| Safety checks | metadata only (a streaming drive downloads every opened file); private folders checked **before** they are opened (`vault_watch.never_list` + `paths.never_open` + `paths.handwriting_app_data`); half-mount guard per scope (fewer than `half_mount_ratio` of the last snapshot's files, with at least `half_mount_min_files`: stop quietly); sources state saved only after a complete pass; once-only alert keys; links not followed; exit 0 for every normal condition. |
| Windows APIs | Task Scheduler, VBS launcher, named mutex `UniOS-VaultWatch`, WinRT toasts with PowerShell's AppUserModelID, `.Ticks`, `GetCreationTime`, `[IO.Path]::Combine` (`Join-Path` throws when a drive letter is missing). |
| macOS | one Python 3 script (`os.scandir`, `json`, `re`, `fcntl`), a LaunchAgent with a `StartCalendarInterval` array and `RunAtLoad`, `osascript` notifications, state in `~/Library/Application Support/uni-os/vault-watch`. |
| Linux | the same script, a systemd user timer (one `OnCalendar=` per time, `Persistent=true`, `OnStartupSec=5min`, `Type=oneshot`, `TimeoutStartSec=10min`), `notify-send`, state in `~/.local/state/uni-os/vault-watch`. |
| Installer | `register-task.ps1 -Vault "<vault>"` copies the scripts to `vault_watch.install_dir`, writes `vault-watch.local.json` and registers the task; `-NoRegister` copies and prints the one-line registration command instead; `-Uninstall` removes the task; also `-InstallDir`, `-TaskName`, `-Times`, `-NoLogon`, `-Python`. A port needs an equivalent installer that writes the plist or unit files. |
| Acceptance test | `modules/vault-watch/tests/test-vault-watch.ps1`: 39 checks against a fake vault. Port the cases. |

Port notes from the README: delete the snapshots after porting (the first run is a silent baseline); keep the formats of `log.md` and `alerts.md` identical, because agents and other modules read them; add a conflict pattern for your sync tool.

### Course file pick-up (`modules/course-files-fetch/scripts/course-pickup.ps1`)

Full contract: the module README, "The pick-up bridge: behaviour specification" and "Threat model". Summary:

| | |
|---|---|
| Purpose | File browser downloads into the vault for a fetch session that cannot see the laptop's Downloads folder, while trusting no request: any vault writer (including a prompt-injected session) can write requests. |
| Inputs | requests `<vault>/_agent/course-fetch/pending/<id>.json` (`file`, `target`, `requested_at`, `approved_large`, optional `machine`); the policy `pickup-settings.json` in the install folder (`vault`, `downloads`, `log_file`, `allowed_hosts`, `check_referrer`, `folders`, `types`, `max_mb`, `max_age_hours`, `wait_minutes`, `date_guards`, `mutex`, `machine`, `installed_at`), never read from the vault; files in Downloads and their download marks. |
| Outputs | the file copied into `<vault>/<target>/<file>`; `done/<id>.result.json` (status `filed`, `already-there`, `changed-on-server`, `rejected`, `not-found` or `failed`, with reason, size, host, SHA-256); the request moved to `done/<id>.request.json`; `pickup.log` in the install folder. |
| Triggers | every `course_fetch.interval_minutes` (1) minutes, hidden, on battery too, start when available, never two at once, 30-minute limit; an empty or missing `pending/` exits at once. |
| State | none besides the log; requests and results are the queue. |
| Safety checks, in order | valid JSON (waits while younger than `wait_minutes`); `machine` matches; plain file name; extension in `types` (executables refused by the installer); target exactly one of the configured folders; no date guard matches; target folder exists; source in Downloads (exact name or the browser's `name (N).ext`, at most `max_age_hours` old); download mark names an allowed host (hosts recorded, never URLs); size at most `max_mb` unless `approved_large`; destination exists: same hash = `already-there`, different = `changed-on-server` (both kept); copy with create-new, verify SHA-256, original to the Recycle Bin. |
| Windows APIs | Task Scheduler, VBS launcher, named mutex `UniOS-CoursePickup`, NTFS `Zone.Identifier` stream, `Get-FileHash`, `FileMode.CreateNew`, Recycle Bin through `Microsoft.VisualBasic`, the Downloads known folder. |
| macOS | origin from `com.apple.metadata:kMDItemWhereFroms`; trash with `/usr/bin/trash` or `osascript`; LaunchAgent with `StartInterval` 60; `fcntl.flock`; `open(dest, "xb")`; `hashlib`. |
| Linux | origin from `user.xdg.origin.url` / `user.xdg.referrer.url` (check your browser and file system write them); `gio trash`; systemd user timer `OnUnitActiveSec=1min` plus `OnStartupSec=1min`, or cron `* * * * *`; `xdg-user-dir DOWNLOAD`. |
| Installer | `install-course-pickup.ps1 -Vault "<vault>"` writes the policy from the config (hosts from `university.lms_url`, each course's `lms_url`, `website`, `fetch_sources`, plus `course_fetch.extra_hosts`; folders from `official_subfolders`), the vault summary `_agent/course-fetch/pickup-policy.md`, and the task; `-NoRegister`, `-NoCreateFolders`, `-Uninstall`, `-InstallDir`, `-TaskName`, `-Downloads`. Re-run it after every change to courses or `[course_fetch]`. |
| Acceptance tests | `modules/course-files-fetch/tests/test-course-pickup.ps1` (41 checks) and `modules/course-files-fetch/tests/test_request_pickup.py`. |

**Never silently weaken the origin check.** If your browser or file system writes no origin record, every request must be rejected. A fallback to "a recent file in Downloads" drops the main protection; offer it only as an explicit opt-in the student chooses, and say so in the policy summary.

### The OS-scheduler job runner (`modules/scheduler-local/scripts/run_job.py`)

`run_job.py` is already cross-platform Python; on macOS and Linux it uses `/bin/bash`, `~/.local/state/uni-os` and process groups automatically. What is Windows-specific is how it gets **scheduled**: `list_jobs.py --vault "<vault>" windows <job>` prints PowerShell that registers one Task Scheduler task per job ("Uni OS - <job>"): one trigger per slot (`-Daily`, or `-Weekly -DaysOfWeek ...` from `DAYS`), a repeating trigger for `EVERY_MIN`, `-StartWhenAvailable`, `-MultipleInstances IgnoreNew`, an execution limit of `TIMEOUT_MIN` + 10 minutes, the battery flags, and `pythonw.exe` as the program.

| | |
|---|---|
| Purpose | Run one job headless with the always-on host runner's semantics: per-job lock, `DISABLED` marker, vault check, failover marker, agent lock, `PRECHECK`, agent CLI or command, hard timeout, logs, optional failure push. |
| Inputs | `<vault>/_agent/jobs/<job>/job.conf` and `prompt.md`; `_agent/jobs/_header.md`; `agent.*` from `_agent/uni-os.json` (else `uni-os.toml`); switches `--dry-run`, `--print-only`, `--force`, `--host-name`, `--permission`, `--agent-cmd`, `--keep-api-env`, `--push-failures`. |
| Outputs | the job's own effects; `<state>/jobs/<job>/<YYYY-MM-DD_HHMMSS>[-dry].log` ending `# exit N after Ss`; one line in `<state>/jobs.log`; 40 logs kept per job. |
| Triggers | the OS scheduler, at the job's `SLOTS` on `DAYS` (within `DATES`), or every `EVERY_MIN` minutes. |
| State | `<state>/running/<job>.pid` lock files (`<pid> <mode>`), the logs. `<state>` = `UNI_STATE_DIR`, else `%LOCALAPPDATA%\uni-os` on Windows, `~/.local/state/uni-os` elsewhere. |
| Safety checks | exit 0 if already running; skip jobs with a `DISABLED` file; exit 3 when the vault is unreachable; skip a slot the host already ran; API-key variables removed so the CLI uses the plan login; process tree killed at `TIMEOUT_MIN`. |
| Windows specifics | `pythonw.exe`; `CREATE_NO_WINDOW`; `OpenProcess`/`GetExitCodeProcess` to test whether a pid lives (`os.kill(pid, 0)` would terminate it on Windows); `taskkill /T /F`; Git Bash lookup. |
| macOS | a LaunchAgent per job (`StartCalendarInterval` dicts per slot and weekday, or `StartInterval` for `EVERY_MIN`), `ProgramArguments` = `python3 run_job.py --vault <vault> --job <id>`. |
| Linux | a systemd user service plus timer per job (`OnCalendar=Mon..Fri *-*-* 07:50:00` per slot, `OnCalendar=*:00/10` for `EVERY_MIN`, `Persistent=true`), or cron lines (`list_jobs.py cron <job>` already prints them, in local time). |

The mapping table "Porting path 2 to cron, launchd or systemd" in the scheduler-local README has the details. A natural port adds a `launchd` or `systemd` subcommand to `list_jobs.py` next to `windows` that prints the files instead of PowerShell; keep it print-only, like the Windows one.

### Laptop ping (`modules/vm/laptop/laptop-ping.ps1`)

Only needed for **failover mode** on the always-on host, which the original stopped using (mode `always` needs no ping). Port it only if you run failover with a desktop app that keeps a last-run record per scheduled task.

| | |
|---|---|
| Purpose | Tell the host that the laptop and its agent desktop app are up, and when each app task last ran. |
| Inputs | `%USERPROFILE%\.config\uni-os\laptop.env` (`HOST_ALIAS`, `HOST_TRANSPORT` `ssh` or `wsl`, `WSL_DISTRO`, `WSL_USER`, `APP_PROCESS_LIKE`, `APP_TASKS_GLOB`); the running app process; the app's `scheduled-tasks.json` files (per task: `id`, `lastRunAt`, `lastScheduledFor`, `enabled`). |
| Outputs | `uni-vm laptop-ping <base64 of {seen, tasks}>` over ssh (through `wsl.exe` on a home server); the host stores `laptop-tasks.json` and touches `laptop-seen` in its state folder. |
| Triggers | Task Scheduler "Uni OS laptop ping" every 10 minutes and 2 minutes after logon, hidden (VBS launcher), on battery too, single instance, 5-minute limit. |
| State | none on the laptop. |
| Safety checks | exits quietly when the app is not running; if a task file can't be read (the app may be writing it), skips the whole ping rather than send wrong data. |
| Windows APIs | `Get-Process` path match, `%LOCALAPPDATA%` task files, Windows OpenSSH. |
| macOS / Linux | a LaunchAgent with `StartInterval` 600 / a systemd user timer `OnUnitActiveSec=10min`, the system ssh, and the location of your app's own task records (find it; it is app- and version-specific). |
| Test | `laptop-ping.ps1 -DryRun` prints "app running" and the JSON it would send. |

`install-laptop.ps1` installs the pieces (`-EnvFile` creates `laptop.env`, `-UniVmCmd` puts `uni-vm.cmd` on the user PATH, `-LaptopPing` registers the ping task, `-Uninstall` removes them). `uni-vm.cmd` becomes a three-line shell script on macOS or Linux:

```bash
#!/usr/bin/env bash
# ~/.local/bin/uni-vm: run uni-vm on the always-on host
ssh -o BatchMode=yes uni-vm 'export PATH=$HOME/.local/bin:$PATH; uni-vm '"$*"
```

### Home-server scripts (`modules/vm/home-server/`)

These set up **Windows** as a host for WSL2 (OpenSSH Server with key-only login on Private networks, power settings, Windows Update active hours, a keep-alive task that runs `wsl.exe --exec /bin/sleep infinity` with nobody signed in). There is nothing to port: on a spare Mac use a Linux VM or a cloud host instead; on a spare Linux machine run Ubuntu 24.04 natively and follow the "other providers" notes in [`../modules/vm/INSTALL.md`](../modules/vm/INSTALL.md). The host code inside (`modules/vm/host/`) is the same everywhere.

## Asking your agent to port a piece

Give your agent the module README and one clear instruction. Examples:

- "Port modules/vault-watch to macOS following the behaviour specification in its README. One Python 3 standard-library script plus a LaunchAgent and an installer. Keep every file format, alert key and alert text. Port the 39 test cases of tests/test-vault-watch.ps1 to Python."
- "Port the course pick-up to Linux following the behaviour specification and threat model in modules/course-files-fetch/README.md. Keep the request and result formats and statuses. Port tests/test-course-pickup.ps1. If my browser writes no origin attribute, reject every request."
- "Add a `systemd` subcommand to modules/scheduler-local/scripts/list_jobs.py that prints a user service and timer for a job, mirroring the `windows` subcommand."

Keep ports outside the framework's Windows files (a new file such as `vault_watch.py`), so updates to the framework don't overwrite your work, and tell your agent to record in the vault's `_agent/tools-and-environment.md` where the port lives.

## Porting checklist

1. **Read the spec, not only the script.** The README specification is the contract; where the PowerShell and the spec disagree, ask before choosing.
2. **Keep the outputs byte-compatible:** file names, Markdown line formats, JSON keys, alert keys and texts, statuses, exit codes. Agents, the heartbeat and other modules parse them.
3. **Keep every safety check**, in the same order: metadata only, private folders never opened, half-mount guard, state outside the vault, atomic JSON writes, single instance, never overwrite, origin check, no file names in pushes.
4. **State and install folders outside the vault**, and refuse to run (exit 2) if they are inside it.
5. **Text files UTF-8 without BOM.** LF line ends are fine everywhere in a port.
6. **Local time in `term.timezone`.** Check the machine's clock zone.
7. **Scheduler semantics:** catch up missed slots after sleep where the original did (`Persistent=true`, launchd's wake behaviour), never two instances at once, a time limit.
8. **Notifications** through the same text and the same once-only keys; phone pushes only through `uni-os push` (the push gate).
9. **An installer with a print-only or no-register mode** (the equivalent of `-NoRegister`), because some agent apps refuse to register scheduled tasks themselves; then the agent hands you one command to run.
10. **Port the tests** and run them against a fake vault before pointing the port at your real vault.
11. **Take a fresh baseline** (vault-watch: delete the snapshots; the first run is silent).
12. **Set `runtime.laptop_os`** to `macos` or `linux` and run `python tools/uni_os.py doctor`. It warns that `vault-watch` supports Windows only and that the laptop part of `course-files-fetch` does, because their `module.toml` files say so; with your own port running, those warnings are expected and harmless. Presets leave both modules out on these systems, so add a ported one with `uni-os enable <id>` (or list it in `modules.enabled`).

## Testing a port

Every Windows script has switches that let you test without side effects. A port should offer the same:

| Windows switch | What it does | Port equivalent |
|---|---|---|
| `vault-watch.ps1 -DryRun` | prints log lines, alerts, toasts and a per-folder scope summary; writes no file, no state, no toast, no push | `--dry-run` |
| `vault-watch.ps1 -Now '<date time>'` | simulates a run time (with `-DryRun`), e.g. to test the 21:00 prep watchdog in the morning | `--now "YYYY-MM-DD HH:MM"` |
| `vault-watch.ps1 -NoToast`, `-NoPush`, `-TestToast` | no toasts / never call the push command / show one test toast and exit | `--no-notify`, `--no-push`, `--test-notify` |
| `vault-watch.ps1 -Root`, `-StateDir` | point at a fake vault and a scratch state folder | `--root`, `--state-dir` |
| `course-pickup.ps1 -SettingsFile`, `-TrashDir` | use a test policy; move originals to a folder instead of the Recycle Bin | `--settings`, `--trash-dir` |
| `register-task.ps1 -NoRegister`, `install-course-pickup.ps1 -NoRegister` | copy files and write settings, print the registration command instead of running it | `--no-register` (print the plist or unit files) |
| `run_job.py --dry-run` | agent jobs get the dry-run preamble and `UNI_DRY_RUN=1`; command jobs get ` --dry-run` only with `DRY_OK="yes"`, else the command is only printed | unchanged (already portable) |
| `run_job.py --print-only` | prints what it would run, runs nothing | unchanged |
| `list_jobs.py windows <job>` | prints the registration, never runs it | a print-only `launchd` / `systemd` subcommand |
| `laptop-ping.ps1 -DryRun` | prints the payload instead of sending it | `--dry-run` |
| `deploy.sh --dry-run` | shows what a deploy to the host would change | unchanged (bash) |

A good order: run the ported tests; run the port with `--dry-run` against a copy of your vault (any folder with the same structure, for example one rendered by `python tools/uni_os.py init --config examples/alex.toml --vault <scratch folder>`); simulate edge cases with `--now`; then a dry run on the real vault; then install the schedule with your yes. Dry runs are instructions, not sandboxes, for agent jobs (the agent reads for real and is told not to write); command jobs must honour `--dry-run` themselves.

## Related pages

- [`runtimes.md`](runtimes.md): what runs where, and why the laptop scheduler is optional.
- [`storage.md`](storage.md): sync clients per OS.
- [`security-and-privacy.md`](security-and-privacy.md): why the pick-up trusts no request.
- The module pages: [vault-watch](../modules/vault-watch/README.md), [course-files-fetch](../modules/course-files-fetch/README.md), [scheduler-local](../modules/scheduler-local/README.md), [vm](../modules/vm/README.md).
