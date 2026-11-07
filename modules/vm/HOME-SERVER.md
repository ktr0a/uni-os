# Home server variant: WSL2 on a spare Windows laptop

The same host code, running inside WSL2 Ubuntu on an old laptop that stays on at home. The original system moved its whole host (jobs, role sessions, Remote Control server) from a 4 GB cloud VM onto an 8 GB laptop this way, in one day, with the conversations and app links of the moved roles intact. This page is the generalised record of how, including what went wrong. Windows parts are **experimental**; tested only with Claude Code.

## Why (and why not)
- **Cost:** electricity instead of ~$20/month.
- **More memory** than a small VM, if the laptop has 8 GB or more (but Windows takes its share; see "RAM honesty").
- **A logged-in browser on the box:** Chrome on the home server, signed in to the course sites by the student, reachable through the Claude in Chrome bridge even while the main laptop is off. Password steps stay with the student; sites may log the browser out after a while (one sign-in per browser session). On its last day the original started measuring whether regular page loads keep those sign-ins alive: an hourly read-only probe job (a short headless run with a small model and the browser bridge, one new tab, loads the course platform's dashboard, logs "signed in: yes/no", clicks and pushes nothing). Not shipped here; an idea if logouts bother you.
- **Optional computer use:** the Windows desktop agent app on the box can be started on demand from WSL (below).

Against it: your home network and power, Windows Update reboots, hardware quirks (see "Gotchas"), and more maintenance than a cloud VM.

## Design decision: WSL2, not native Windows

| | Native Windows | WSL2 Ubuntu inside Windows (chosen) | Native Ubuntu Server (wipe) |
|---|---|---|---|
| What changes | rewrite the ~1,400 lines of bash, units -> Task Scheduler, rclone via WinFsp; **no tmux**, so session hosting (role, job and Remote Control sessions read with `capture-pane`) needs a new design | the host code deploys unchanged: systemd works in WSL (`[boot] systemd=true`), so do tmux, jq, FUSE and the rclone mount | unchanged, and the most RAM |
| RAM | Windows only | Windows + ~0.3-0.5 GB WSL overhead | all of it |
| Keeps a Windows Chrome / desktop app on the box | yes | yes | no (a desktop or virtual display: fiddly) |
| Risks | weeks of rewriting, two code bases | keeping WSL running with nobody signed in; WSL holding page cache; Windows Update reboots | losing Windows |

## RAM honesty
Measure before you move. In the original: Windows idled at ~1.75 GB free of 5.9 GB usable with auto sign-in, the agent desktop app and Chrome open (an iGPU took 2 GB of the 8 GB), WSL itself (`vmmemWSL`) took ~0.5 GB, and with six agent sessions Linux had ~2 GB available while Windows had only 0.65 GB free: "tight", like the 4 GB VM. Not autostarting the Windows desktop app saves ~1 GB.

## Setup

### 1. Windows
1. Keep Windows lean: startup apps off, search indexing off, transparency and animations off. Keep Windows Update, the Store/App Installer, Defender and the WSL components. A restore point first.
2. Optional, for reaching it from outside your home: Tailscale (sign in on the box yourself).
3. Optional, if you want Chrome or the desktop app on the box after every reboot: Windows auto sign-in (the password step is yours; Sysinternals Autologon is one way).
4. Copy `modules/vm/home-server/` to the box with your main laptop's **public** key as `uni-home.pub` next to it (`ssh-keygen -t ed25519 -f ~/.ssh/uni-home` on the main laptop), then double-click `setup-home-server.cmd` (or run `setup-home-server.ps1 -PublicKey <file>` as administrator). It:
   - installs and starts OpenSSH Server (falling back to Microsoft's Win32-OpenSSH MSI on trimmed Windows images), firewall rule for **Private** networks only, sets the network profile to Private;
   - allows key-only login for that key (`administrators_authorized_keys`, readable only by Administrators and SYSTEM, or sshd ignores it), turns password login off, sets PowerShell as the ssh shell;
   - power: never sleep or hibernate (also on battery), the lid does nothing, hibernation off (which also turns Fast Startup off);
   - Windows Update active hours 06:00-24:00, so restarts happen at night;
   - prints the IP, computer name and user for your `~/.ssh/config`. Nothing is saved.
5. On the main laptop, `~/.ssh/config`:
   ```
   Host uni-home
     HostName <LAN address or Tailscale name>
     User <windows-user>
     IdentityFile ~/.ssh/uni-home
   ```
   `ssh uni-home` must land in PowerShell without a password.

### 2. WSL
1. On the box, as administrator: `wsl --install -d Ubuntu-24.04`, restart, create the Linux user when asked (or let the bootstrap create one).
2. Copy `wslconfig.example.ini` to `%USERPROFILE%\.wslconfig` and size `memory=` (leave Windows ~2-2.5 GB). Key settings: `vmIdleTimeout=-1` (never shut the WSL VM down when idle), `autoMemoryReclaim=gradual` (give page cache back to Windows), `instanceIdleTimeout=-1`, `swap=4GB`.
3. Optional: Defender exclusions for the WSL virtual disk (`ext4.vhdx` under `%LOCALAPPDATA%\wsl\`) and the swap file folder, to keep Defender from scanning every write. Only those paths.
4. Inside WSL, as root: `sudo bash bootstrap-root.sh --user <linux-user> --tz <tz> --hostname uni-home`. It detects WSL: password-less sudo (you never need a Linux password), `/etc/wsl.conf` with systemd on, default user, hostname, Windows PATH not appended; no zram (swap comes from `.wslconfig`); never an automatic reboot (a reboot inside WSL just stops the distro).
5. In Windows: `wsl --terminate Ubuntu-24.04`, start it again, and run the bootstrap once more: linger needs systemd, which runs only after that restart.
6. As administrator: `register-wsl-keepalive.ps1`. The task "Uni OS WSL keepalive" starts 30 s after boot with nobody signed in (S4U logon, no stored password), restarts up to 999 times every minute, and keeps one `wsl.exe --exec /bin/sleep infinity` attached, so systemd and everything in it keeps running.

### 3. The host inside WSL
Follow [INSTALL.md](INSTALL.md) steps 8-16, with these differences:
- **rclone login:** do the consent in a browser on the box itself (the token never travels), or use the port forward of step 8 through `ssh uni-home` + `wsl`.
- **Let Windows see the vault** (for a pick-up task on the box, or to look at files): `uni-vm hostenv set RCLONE_ALLOW_OTHER yes` and re-run the installer; Windows then reads `~/Uni` through `\\wsl.localhost\Ubuntu-24.04\home\<linux-user>\Uni`.
- **Laptop settings:** a laptop.env for the box with `HOST_ALIAS="uni-home"`, `HOST_TRANSPORT="wsl"`, `WSL_DISTRO="Ubuntu-24.04"`, `WSL_USER="<linux-user>"`. `vm.sh` then base64-encodes each command and runs it through `wsl.exe` from the box's PowerShell, so quoting survives and stdin and exit codes pass through. `deploy.sh` and `uni-vm.cmd` use the same settings.
- **If another host is live, install in trial mode first:** `install-user.sh --trial`. A trial host mounts the vault read-only, keeps every job timer off, never writes `_agent/vm/*`, and gets its own Remote Control name ("... (trial)"). Don't copy the push topic yet.

### 4. Trial checklist
Run these before moving anything; record the numbers.

| Test | Pass when |
|---|---|
| SSH (LAN and Tailscale) | key only, no password prompt |
| Windows idle RAM (sign-in, desktop app, Chrome; WSL off) | your number, for sizing `.wslconfig` |
| WSL idle (mount, tmux holders) | Linux available memory; `vmmemWSL` size |
| `claude -p` and the account's connectors | a calendar read matches the laptop |
| Drive write / read / remove, outside the notes | a test file both ways within the expected times; back to read-only afterwards |
| Remote Control | the trial server appears in the app; a test session answers `hostname` and `pwd` |
| Reboot with nobody signed in | Linux starts ~30-60 s after Windows (the keep-alive task, not your ssh), all units active, mount up, nothing else started |
| Tests, probes, dry runs | `bash ~/uni-os/modules/vm/tests/run-tests.sh` all ok; `uni-vm doctor` only expected `!!`; dry runs exit 0 |
| Browser bridge to the box's own Chrome | a session sees the box's Chrome and opens a public page |
| Six test sessions | memory stays above ~1.5 GB in Linux and ~0.5 GB in Windows |
| Windows Update | restarts only outside the active hours, and everything comes back |

### 5. Going live: moving jobs and roles
From the laptop, with one laptop.env per host:
```bash
bash modules/vm/home-server/move-state.sh --from ~/.config/uni-os/vm.env --to ~/.config/uni-os/home.env check
bash modules/vm/home-server/move-state.sh --from ~/.config/uni-os/vm.env --to ~/.config/uni-os/home.env go
bash modules/vm/home-server/move-role.sh  --from ~/.config/uni-os/vm.env --to ~/.config/uni-os/home.env <role>
```
- `move-state.sh go`: every job off on the source and `VAULT_WRITES=no` there; job logs, modes, performance data, alert markers, outcome-check state, the push gate's budget (`~/.local/state/uni-os/push-gate/`) and the laptop-ping files copied; on the target `JOBS_LIVE=yes`, `VAULT_WRITES=yes`, jobs synced and the same jobs switched on. Other modules' host state (e.g. a watcher's memory outside the vault) goes along with `--extra "<path relative to home> ..."`.
- `move-role.sh`: refuses a busy role; stops it on the source (conversation kept); copies its id, link, role.conf, transcript (into the target's project folder, which depends on the vault path there) and handoff folder; compares checksums; resumes it on the target. In the original all five moved roles kept their app link and session reference.
- Don't forget the trial flags on the new host (`uni-vm hostenv set DRIVE_READ_ONLY no`, re-run the installer), the push topic, and pointing the laptop ping and `uni-vm.cmd` at the new host.

**Rules (from a real move):**
- Switch right after a :x0 or :x5 minute and never around a job's slot: a slot must run on exactly one host. `check` lists the next timers.
- One step at a time, with time to settle; avoid the quiet windows of timed tests.
- Some pieces are tied to one machine and must move together: a poll job that starts another job starts it on its own machine; a watcher that re-runs a check does so locally; the push budget lives on one machine.
- Exactly one host writes `_agent/vm/*` (the snapshot is found by readers by its file id).
- A role conversation exists on one host at a time. Rehearse once with a throwaway role. Fallback when a transcript is lost: `uni-vm roles start <role>` with a handover note and the old transcript in `~/handoff/<role>/`.
- Rollback = the same commands with `--from` and `--to` swapped.
- The performance verdict judges a cloud machine against a budget; on a home server it names what would help instead (it says so itself).

## Optional: start the Windows desktop app from WSL
For computer use (Windows desktop app only) without autostarting the app: create a Windows scheduled task "Uni OS start agent app" (run only while the user is signed in, no trigger) whose action is `explorer.exe shell:AppsFolder\<the app's AppUserModelId>` (find it with `Get-StartApps` in PowerShell). From WSL, `/mnt/c/Windows/System32/schtasks.exe /run /tn "Uni OS start agent app"` starts it on the signed-in desktop; `tasklist.exe /fi "imagename eq claude.exe"` shows whether it runs. Needs someone signed in to Windows (auto sign-in).

## Gotchas (all from the original move)
- **The hypervisor never started** on one laptop until the BIOS iGPU "UMA frame buffer" size was set to Auto (black-screen boots with the fan at full speed, two Startup Repair passes). Vendor-specific; search for your model.
- **Windows Update rolled back** features (including the WSL components) after failed boots. After any boot trouble check that WSL and the hypervisor are still there.
- **Account lockout:** Chrome's "verify it's you" box fell back to the Windows password; typed PINs locked the account. A vendor background service also contributed. Fix: NumLock on at sign-in, vendor services off, and know your Windows password.
- `Checkpoint-Computer` (restore point) hangs over ssh (VSS); make restore points at the console.
- A clock 9 hours off during the install corrupted timestamps; check `date` in WSL before installing.
- Chrome plus the desktop app cost ~2 GB in Windows; `.wslconfig` memory must leave room for them.
- An `.wslconfig` change needs `wsl --shutdown`, which ends every session in WSL (ask first).
- The Claude in Chrome extension names browsers only "Browser 1/2"; with two Chromes connected (main laptop and box), sessions must pick the right one by its device id, which can change on reinstall.
- Start the trial read-only; a delete on a read-write mount is a real delete in the cloud drive.

## Going back
Reverse the move (`move-state.sh` and `move-role.sh` with `--from`/`--to` swapped), then on the box `uni-vm jobs off all`, `systemctl --user disable --now uni-rc uni-roles`, and unregister the keep-alive task (`Unregister-ScheduledTask 'Uni OS WSL keepalive'`). WSL itself: `wsl --unregister Ubuntu-24.04` deletes the distro and everything in it (the vault is in the cloud drive and unaffected).
