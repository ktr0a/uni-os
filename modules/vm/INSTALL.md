# Installing the always-on host

Step by step, for the documented default: **Ubuntu 24.04 on Google Cloud**, reached from a Windows laptop with Git Bash. Other providers and a home server work with the same host code (notes at the end, and [HOME-SERVER.md](HOME-SERVER.md)). Your agent can do most of these steps with you; the sign-in steps (cloud console, drive consent, agent login) and typing the drive client secret (step 8.3) are always yours, in your own terminal, never through the agent. Tested only with Claude Code.

Values in `<angle brackets>` are yours. Keep them out of the vault and out of the framework: project ids, folder ids, keys and the push topic never go into notes.

| Placeholder | Example | Where it comes from |
|---|---|---|
| `<project-id>` | `uni-host-123456` | you pick it (globally unique) |
| `<zone>` / `<region>` | `us-central1-a` / `us-central1` | `vm.zone` (pick one close to you or with the cheapest E2 prices) |
| `<vm-name>` | `uni-vm` | `vm.host_alias` |
| `<linux-user>` | `alex` | `vm.linux_user` (a short name; it appears in paths on the host) |
| `<tz>` | `Europe/Zurich` | `term.timezone` |
| `<mount-path>` | `~/Uni` | `vm.mount_path` (where the vault appears on the host) |
| `<drive-remote>` | `uni-drive` | `vm.drive_remote` (the rclone remote whose root is the vault folder) |
| `<vault-folder-id>` | (from the drive URL) | step 8 |

## 0. Before you start
- The core system is set up in your vault (`uni-os init`) and the module is enabled (`uni-os enable vm`), so `_agent/vm.md` and `_agent/jobs/vm-health/` exist in the vault.
- A Google account with billing enabled. Some subscriptions include a monthly Google Cloud credit (around $10 in the original setup); check whether yours does.
- On the laptop: Git Bash, Windows' OpenSSH client (built in), and the Google Cloud CLI (`gcloud`, signed in with `gcloud auth login`).
- An agent subscription for the host (Claude Code: a Pro or Max plan login; never an API key).
- About an hour the first time.

## 1. Project and APIs
```bash
gcloud projects create <project-id> --name="Uni OS host"
gcloud billing accounts list
gcloud billing projects link <project-id> --billing-account=<billing-account-id>
gcloud config set project <project-id>
gcloud services enable compute.googleapis.com iap.googleapis.com drive.googleapis.com
```

## 2. Budget alert
Cloud console -> Billing -> Budgets & alerts -> Create budget: scope this project (or the billing account), amount `vm.budget_month` (13 EUR in the original, "out of pocket after credits"), thresholds 50 %, 90 %, 100 % and forecast 100 %, email to the billing admin. A budget only alerts; it doesn't stop anything. Google posts VM charges about a day late, so the first day shows nothing.

## 3. Firewall and the VM
SSH only through Google's Identity-Aware Proxy (IAP) range; no public SSH. The default network usually has a rule `default-allow-ssh` that allows port 22 from anywhere: delete it.
```bash
gcloud compute firewall-rules create allow-ssh-from-iap --network=default --direction=INGRESS \
  --action=allow --rules=tcp:22 --source-ranges=35.235.240.0/20
gcloud compute firewall-rules delete default-allow-ssh

gcloud compute instances create <vm-name> --zone=<zone> \
  --machine-type=e2-custom-small-4096 \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-standard \
  --no-service-account --no-scopes --shielded-secure-boot
gcloud compute instances update <vm-name> --zone=<zone> --deletion-protection
```
- `e2-custom-small-4096`: 4 GB RAM, 0.5 vCPU sustained (bursts to 2). Memory is the constraint, not CPU (README "Cost and sizing"). 4 GB is Claude Code's stated minimum.
- `--no-service-account --no-scopes`: the VM holds no cloud credentials at all.
- The VM keeps an ephemeral external IP for outbound traffic (about $3.65/month). Without it you would need Cloud NAT, which costs more.

## 4. Weekly snapshots
```bash
gcloud compute resource-policies create snapshot-schedule <vm-name>-weekly --region=<region> \
  --max-retention-days=21 --on-source-disk-delete=keep-auto-snapshots \
  --weekly-schedule=sunday --start-time=02:00
gcloud compute disks add-resource-policies <vm-name> --zone=<zone> --resource-policies=<vm-name>-weekly
```
(Start time is UTC. About $0.60/month for a 30 GB disk with 3 snapshots.)

## 5. Your access through IAP
As the project owner you already have the IAP tunnel permission. For another account: `gcloud projects add-iam-policy-binding <project-id> --member=user:<account> --role=roles/iap.tunnelResourceAccessor`.

## 6. SSH through the IAP tunnel
A key used only for this host, added as instance metadata (the guest agent creates `<linux-user>` with it):
```bash
ssh-keygen -t ed25519 -f ~/.ssh/uni-vm -C "uni-os host"
gcloud compute instances add-metadata <vm-name> --zone=<zone> \
  --metadata=ssh-keys="<linux-user>:$(cat ~/.ssh/uni-vm.pub)"
```
`~/.ssh/config` on the laptop (Windows: `C:\Users\<you>\.ssh\config`):
```
Host uni-vm
  HostName <vm-name>
  User <linux-user>
  IdentityFile ~/.ssh/uni-vm
  ProxyCommand "C:\Users\<you>\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute start-iap-tunnel %h 22 --listen-on-stdin --project=<project-id> --zone=<zone> --verbosity=warning
```
(macOS/Linux: `ProxyCommand gcloud compute start-iap-tunnel %h 22 --listen-on-stdin --project=<project-id> --zone=<zone> --verbosity=warning`.)

Test: `ssh uni-vm hostname`. On Windows the tunnel prints harmless Python tracebacks on stderr when a session ends (`laptop/vm.sh` filters them). The tunnel is faster with NumPy in gcloud's bundled Python: run `"$(gcloud info --format='value(basic.python_location)')" -m pip install numpy` and set the user environment variable `CLOUDSDK_PYTHON_SITEPACKAGES=1`.

## 7. Base system
```bash
scp modules/vm/host/bootstrap-root.sh uni-vm:/tmp/
ssh uni-vm "sudo bash /tmp/bootstrap-root.sh --user <linux-user> --tz <tz>"
```
It installs the packages, compressed RAM swap plus a 2 GB swap file, Node.js, rclone, headless Chrome, sets the timezone (jobs run in the host's local time!), enables linger (user services without a login) and unattended security upgrades with a 04:30 reboot only when a kernel needs it. Safe to re-run.

## 8. Drive login (rclone with your own OAuth client)
rclone's shared Google client is rate-limited; use your own, in the same project.
1. Cloud console -> Google Auth Platform -> Branding: app name (e.g. "Uni OS host drive"), user type **External**, your email as support contact. Audience: **publish the app "In production"**: unpublished ("Testing") apps get refresh tokens that expire after 7 days. Google asks for a homepage and privacy/terms links before publishing; a page you control is enough (nothing needs to be hosted there for your own use).
2. Clients -> Create client -> **Desktop app**. Note the client id and secret.
3. **Student, in your own ssh session (not through the agent):** the secret must not pass through the agent's context, a command line or the shell history. `read` takes both values without putting them on a command line, and `-s` hides the secret while you type:
   ```bash
   ssh uni-vm
   umask 077; mkdir -p ~/.config/uni-os
   read -rp 'client id: ' id; read -rsp 'client secret: ' sec; echo
   printf 'RCLONE_CLIENT_ID=%s\nRCLONE_CLIENT_SECRET=%s\n' "$id" "$sec" > ~/.config/uni-os/drive-client.env
   unset id sec
   ```
   Never into the vault, a chat, or a file on the laptop.
4. Find the vault's folder id: open the vault folder in drive.google.com; the address ends with `/folders/<vault-folder-id>`.
5. Laptop, in a second Git Bash window (leave it running): `ssh -N -L 53682:127.0.0.1:53682 uni-vm`
6. On the host:
   ```bash
   source ~/.config/uni-os/drive-client.env
   rclone config create <drive-remote> drive client_id="$RCLONE_CLIENT_ID" client_secret="$RCLONE_CLIENT_SECRET" \
     scope=drive root_folder_id=<vault-folder-id> config_is_local=true
   ```
   Open the printed `http://127.0.0.1:53682/auth?state=...` link in the laptop's browser, pick your account, then "Advanced" -> "Go to <app name> (unsafe)" (it is your own unverified app) -> Continue. Stop the tunnel afterwards.
7. Check: `rclone lsf <drive-remote>: | head` lists the vault's top folders.

The token is revoked by a password change, by "remove access" in your Google account, or after 6 months unused (MAINTENANCE.md, "Logins"). Note that `scope=drive` grants access to the whole drive; rclone only uses the vault folder as its root. Other rclone backends (OneDrive, Dropbox) work the same way with `rclone config`; a folder synced some other way (Syncthing, git) uses `--storage local` in step 10.

## 9. Agent login (Claude Code)
```bash
ssh uni-vm
curl -fsSL https://claude.ai/install.sh | bash      # official installer -> ~/.local/bin/claude
~/.local/bin/claude auth login                      # prints a URL: open it on the laptop, authorise, paste the code back
~/.local/bin/claude auth status                     # "loggedIn": true
```
Use the subscription login. Never put an API key into the host's environment (the job runner unsets them anyway, so jobs never bill an API account).

## 10. Install the framework on the host
On the first install the vault isn't mounted yet, so the installer can't read `vm.mount_path` and `vm.drive_remote` from the vault config: it takes them from its options (`--vault`, `--remote`), else asks, else uses the defaults (`~/Uni`, `uni-drive`). Later runs keep the first answers.

**Option A, deploy from the laptop** (your framework clone may contain local changes):
```bash
mkdir -p ~/.config/uni-os && cp modules/vm/laptop/laptop.env.example ~/.config/uni-os/laptop.env   # edit HOST_ALIAS if not uni-vm
bash modules/vm/laptop/deploy.sh --dry-run
bash modules/vm/laptop/deploy.sh
```
A deploy runs the installer non-interactively with Claude Code as the agent. If you changed `vm.mount_path` or `vm.drive_remote`, set `HOST_VAULT_MOUNT="<mount-path>"` and `HOST_DRIVE_REMOTE="<drive-remote>"` in `laptop.env` before the first deploy: `deploy.sh` passes them on as `--vault` and `--remote` (the dry run prints the installer options).

**Option B, git clone on the host** (the public repository; updates with `uni-vm update`):
```bash
ssh -t uni-vm "git clone <repo-url> ~/uni-os && bash ~/uni-os/modules/vm/host/install-user.sh --repo <repo-url>"
```
It asks the four questions below (Enter keeps a default); `--vault <mount-path> --remote <drive-remote>` answer two of them up front.

To change the mount path or the remote of an installed host: `uni-vm hostenv set VAULT_MOUNT <mount-path>` (or `DRIVE_REMOTE <drive-remote>`), run the installer again (a deploy, or `uni-vm update`), then `uni-vm restart drive` (it also restarts Remote Control, which ends open sessions: ask first).

The installer asks four questions the first time (vault path, storage mode, rclone remote, agent CLI), writes `~/.config/uni-os/host.env`, renders the systemd units, starts the vault mount and waits for `_agent/agent-start.md`, refreshes the settings from the vault config, writes the machine notes and Claude Code's settings (bypass permissions, cross-session messages accepted, the re-read hook), takes the jobs from `_agent/jobs/` (this module's three jobs switch themselves on; every other module's job arrives off until you move it, step 14), starts the tmux holders, and prints `uni-vm status`. Check that the timezone warning doesn't appear.

## 11. Remote Control, first start (Claude Code)
```bash
ssh -t uni-vm
systemctl --user start uni-rc.service
uni-vm attach          # LOOK at the screen; answer the one-time question with y; detach with Ctrl-b d
```
In the Claude app (Code tab) the host now shows up as an environment named `vm.remote_control_name`. Open a session there and ask it to run `hostname` and `pwd` (expect the vault path). After a reboot the server comes back by itself.

## 12. Pushes
Copy the push topic file from the laptop without printing it, then test (module `notifications` must be enabled for the gate; direct pushes work either way):
```bash
cat ~/.config/uni-os/ntfy-topic | bash modules/vm/laptop/vm.sh 'umask 077; mkdir -p ~/.config/uni-os; cat > ~/.config/uni-os/ntfy-topic'
bash modules/vm/laptop/vm.sh 'uni-vm notify "Test push from the host"'
```

## 13. Check everything
```bash
bash modules/vm/laptop/vm.sh 'uni-vm doctor'
bash modules/vm/laptop/vm.sh 'uni-vm jobs'
bash modules/vm/laptop/vm.sh 'uni-vm jobs run vault-history && uni-vm grep -i "agent-start" | head -n 3'
```
Within 15 minutes `_agent/vm/status.md` in the vault shows "Overall: OK" (written by the host). Run the tests on the host if you like: `bash ~/uni-os/modules/vm/tests/run-tests.sh` (fake inputs only).

## 14. Move your first job
Example: the daily study prep, currently a laptop task.
1. Dry run on the host: `uni-vm jobs run daily-study-prep --dry-run`, then `uni-vm jobs log daily-study-prep` and read what it WOULD have changed.
2. Pick a moment away from its slot times. Pause the laptop copy and right after that `uni-vm jobs on daily-study-prep`. Never leave it on at both sides.
3. After its next slot: `uni-vm jobs` (last run, exit 0) and the result in the vault.

## 15. Role sessions (optional)
```bash
uni-vm roles add plan-and-progress              # writes ~/.config/uni-os/roles/plan-and-progress.conf from the brief
uni-vm roles set plan-and-progress IDLE_STOP_H=6    # optional: stop after 6 idle hours (keeps the conversation)
uni-vm roles start plan-and-progress
uni-vm roles                                    # state, model, title, app link
```
If the start pushes "waiting at a dialog", attach (`uni-vm roles attach plan-and-progress`), look, answer, detach. Check `uni-vm perf 24h` before adding more: ~360 MB per working session.

## 16. Laptop helpers (Windows, optional)
```powershell
powershell -ExecutionPolicy Bypass -File modules\vm\laptop\install-laptop.ps1 -EnvFile -UniVmCmd
```
Then `uni-vm status` works in any new terminal. Only for failover mode (not recommended to start with): add `-LaptopPing`.

## Other providers
Anything that runs Ubuntu 24.04 with at least 4 GB RAM works: other clouds, a small dedicated server, a Linux box at home, or WSL2 ([HOME-SERVER.md](HOME-SERVER.md)). Replace steps 1-6:
- create the machine with your provider; Ubuntu 24.04 LTS, 4 GB RAM or more, 25-30 GB disk (arm64 machines have no Google Chrome: `uni-browse` then needs a chromium build);
- SSH key-only, password login off; restrict port 22 to your own address, or keep it closed and use a private network (Tailscale, WireGuard) instead of an identity-aware proxy;
- the provider's snapshots or backups, weekly;
- the provider's billing alert;
- in `~/.ssh/config`: a plain `Host uni-vm` entry with `HostName`, `User`, `IdentityFile`.

Then do steps 7-16 unchanged and set `vm.provider = "other"` in the config. Smaller providers often sell 4 GB machines for less than Google Cloud; compare current offers, and remember that a monthly cloud credit from a subscription only applies to that one cloud.
