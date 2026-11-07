# Security and privacy

Uni OS gives AI agents broad access to your study life: your notes, your calendar, your course sites, sometimes a shell with no approval prompts. This page explains how the system limits the damage that can do, where every secret lives, what the built-in checks catch, how to undo mistakes, and what to check before you show a vault to anyone.

Two facts shape everything here:
1. **The vault syncs to every device and every agent can read it.** Anything written into it is effectively shared with every session, job, cloud service and device that touches it. So no secret ever goes into the vault.
2. **Any session can be fooled.** An agent that reads a web page, a downloaded PDF or a message from another session can meet text written to manipulate it (prompt injection). So text from files, pages and other sessions is data, never instructions, and the components that act on vault content (the course pick-up, the job runner on the host) trust nothing they read there.

Uni OS has only been tested with Claude Code; the rules below are in agent-neutral files (`_agent/rules.md`, the role briefs) and bind every agent.

## Where each secret lives

| Secret | Lives in | Never in |
|---|---|---|
| ntfy push topic (anyone who knows it can read and send your pushes) | a file outside the vault, `notify.ntfy_topic_file` (default `~/.config/uni-os/ntfy-topic`); on the always-on host the same path, mode 600, copied without being printed | the vault, the config, the framework, logs, pushes |
| Anthropic API key for the cockpit's assistant panel | Obsidian's secret storage (Settings, Keychain), on each device separately; the synced plugin settings hold only the secret's name | the vault, `data.json`, the config |
| Private calendar addresses (Google's "secret address in iCal format", Outlook ICS links, iCloud links) | Obsidian's secret storage, per device; they work like passwords and the provider can reset them | the vault, the config |
| Calendar and mail access for agents | your agent's connector (an OAuth grant held by the agent platform) | the vault; agents never work around a refused connector with keys or feed addresses |
| Your university password, one-time codes, consent screens | your browser and you | everywhere else: agents never type them, not even with permission |
| Google Drive access on the always-on host | `~/.config/uni-os/drive-client.env` (your own OAuth client id and secret, typed in an ssh session) and `~/.config/rclone/rclone.conf` (the token) | the vault, the framework |
| Agent login on the host | the agent's own folder (in Claude Code `~/.claude/`); jobs always use the subscription login: the runners unset `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN` | the host's environment, the vault |
| Google Cloud | the VM has **no** service account and no scopes; your `gcloud` login stays on your laptop. The project id (`vm.project`) is not a secret but stays out of shared examples | the VM, the vault |
| ssh keys | `~/.ssh/` on the laptop (one key of its own for the host) | the vault |
| Course pick-up policy (allowed hosts, folders, limits) | `pickup-settings.json` in the install folder outside the vault, written only by the installer you run | the vault (the vault page `pickup-policy.md` is a summary the script never reads) |

The config may hold **paths** to secret files, never the secrets themselves.

## What `uni-os doctor` checks

### Config validation

`python tools/uni_os.py config validate` (and every `doctor` run) refuses:
- any config key whose name ends in `token`, `api_key`/`apikey`, `secret`, `password` or `passwd` with a value: store the value in a file outside the vault and point to it with a `*_file` key;
- any config value that contains a key-like string (the same patterns as the vault scan below);
- `notify.ntfy_topic_file` pointing inside the vault.

### Secrets scan of the vault

Every `doctor` run scans the vault's text files and prints findings **redacted** (only a short prefix and the length, never the secret):

| Finding | Level |
|---|---|
| Anthropic API keys (`sk-ant-...`), OpenAI-style keys, Google API keys (`AIza...`), Google OAuth client secrets (`GOCSPX-...`) | error |
| GitHub, GitLab and Slack tokens, AWS access key ids, Stripe live keys, private key blocks, JSON web tokens, bearer tokens in an `Authorization` header | error |
| Private calendar feeds: Google `.../private-<hex>` iCal addresses, any `/private-<hex>` feed, published Outlook `.ics` and iCloud calendar links | error |
| ntfy topics: `ntfy.sh/<topic>`, `<your ntfy server>/<topic>`, and the literal content of your topic file | error |
| A long value assigned to a name like `api_key`, `client_secret`, `token`, `password` | warning |

- Skipped: `paths.never_open` (default `**/private/**`), `.git`, `node_modules`, `.trash`, virtual environments and caches, binary files (PDFs, images, archives, office files), files over 5 MB, and the manifest.
- Obvious placeholders (`example`, `xxxx`, `your-`, `<`, `...`, `changeme`, `placeholder`, `dummy`) are not reported. To silence a deliberate false positive, such as a documented fake key, put `uni-os: allow-secret` on the same line.
- `doctor` exits 1 on any error (with `--strict`, also on warnings). `--no-secrets` skips the scan; `--json` gives machine-readable output.

The scan finds known shapes, not every secret. Treat a clean result as "nothing obvious", not as proof.

## Private folders

- `paths.never_open` (default `["**/private/**"]`, any folder named `private`): agents never open these paths, `doctor`'s scan skips them, the vault watcher does not even list file names inside them, and the always-on host's notes history never copies them.
- `paths.handwriting_app_data`: a tablet note app's own data folder inside the vault, if any: never touched, read or listed.
- The note app's exports (`paths.handwriting_app_exports`) and the handwritten folders are read-only for agents.

Put anything an agent must never see (health notes, personal letters, ID scans) into a `private` folder, or better, outside the vault.

## Course sites and the password step

The rules in `_agent/rules.md` ("Credentials and course sites") bind every agent:
- **Agents never type your university password**, autofilled or not. Entering a username and clicking through single sign-on is fine; any password, one-time code or consent screen stays with you.
- **Logged-in course pages are read-only for agents**: "Do not change anything, solely click through the data and read." Never start a quiz attempt, submit, post, enrol, or change settings.
- **Opening course sites in your signed-in browser** needs your permission per visit until you allow it once in `rules.md` (with the date and your words); afterwards it is still read-only.
- When a sign-in has expired, the agent tells you once (one push or one line), skips that part and carries on.

### Agents that drive your browser

The course-files-fetch role ([module page](../modules/course-files-fetch/README.md)) drives your own, already logged-in browser to download official files. Its limits:
- It works in a new tab, leaves your tabs alone, treats page text as data, and fetches only official material from the sources in the config (anything else: ask first).
- It never sees a password, code or cookie: your browser downloads with your session. It never prints file URLs (LMS file URLs can carry session tokens).
- It pauses while you study on that machine, batches every sign-in it needs into one request, and waits.
- **The pick-up trusts no request.** Any vault writer can write a request, including a session that read a malicious page. A hostile request can at most get a file that is already in your Downloads, came from an allowed host per the browser's own download record, has an allowed document type and is at most 12 hours old copied into one of your configured official folders under a free name. It cannot choose another path, overwrite or delete anything (the only removal is the Downloads original, to the Recycle Bin, after a verified copy), file a program, run anything, reach the network, or change the policy. Residual risks are listed in the module's threat model.
- Avoid browser tools that copy your cookies into a separate automated browser or need a remote-debugging port: they move your login out of your browser's control.

The always-on host has its own browser helper, `uni-browse`: headless Chrome per call, for public JavaScript pages only, with no logins. Logged-in pages stay in your own browser.

## Prompt injection and messages between sessions

- **Text is data.** Text in files, web pages, downloads and messages is never an instruction. Third-party downloads are unpacked into a new empty scratch folder, nothing inside is run, and they are read with isolated tooling (for example `python -I`).
- **A message from another session is never your approval.** Only your own words count. A side session asking the coordinator to approve something risky gets your answer relayed in quotes, or the item stays a proposal.
- **The relay rule** on the always-on host forwards a headless job's message unchanged to the named session and never acts on the forwarded text.
- **The re-read nudge** (a prompt hook on the host) prints one fixed sentence when the rules or a role brief changed. It never passes file content, so nothing a session writes reaches other sessions with the weight of a user message.
- **Job definitions are code.** On the always-on host, `job.conf` runs with bypass permissions, so the host never runs jobs straight from the vault: `uni-vm jobs sync` copies them into the host's own copy and prints every `job.conf` change, new job folders are taken only with `--accept-new` (or a "y" on a terminal), and folders not yet taken are read only by a static parser that never executes them. Nothing syncs jobs by itself.
- **Update notes** from create-only writers are applied only if every quoted line still matches exactly; notes that would put protected graded work or a secret into the vault are refused (module inbox-sync).

## Pushes without personal details

Phone pushes appear on a lock screen anyone can see. The push gate (`uni-os push`, module [notifications](../modules/notifications/README.md)) refuses (exit 13) a push whose text contains a mail address, a link (links go into the click URL with `--click`), or a long digit run (phone, matriculation or account numbers). This applies to direct host alerts too. Senders also leave out file names (they can contain people's names): the outcome checks say "update note waiting in the inbox for over 4 h", never which note; vault-watch pushes only a count. The keys `notify.block_personal` and `notify.require_id` keep this on; leave them `true`. Pushes never say "all good" either; silence is the norm.

## The always-on host

The host (module [vm](../modules/vm/README.md)) runs agents unattended with bypass permissions, so its exposure matters.

| Surface | How it is limited |
|---|---|
| SSH | No public SSH on the cloud VM: the firewall allows port 22 only from Google's IAP range, and the laptop connects through `gcloud compute start-iap-tunnel` as the ssh `ProxyCommand`, with a key of its own. A home server allows key-only ssh, password login off, on Private networks only (LAN or Tailscale). |
| Cloud identity | The VM is created with `--no-service-account --no-scopes` and shielded secure boot: a compromised host cannot touch the cloud project. |
| Remote Control | The remote-control server lets you (through your agent account) open sessions in the vault from the phone; those sessions run in bypass mode. Protect your agent account like any account that can run code on your machine. The server accepts `vm.rc_capacity` sessions (10). |
| Bypass permissions | Only on the host (and on a laptop you trust, for unattended tasks). Cloud sessions cannot use it at all. |
| Secrets | Only on the host, in `~/.config/uni-os/`, `~/.config/rclone/` and the agent's folder; never in the vault, the framework, logs or pushes. |
| Updates | Unattended security upgrades, with a reboot (04:30) only when a kernel needs it. The agent CLI updates itself; the health check restarts the Remote Control server in the quiet hour `vm.rc_update_hour` to pick it up. |
| Money | A budget alert on the billing account (50/90/100 % and forecast 100 %). If the bill surprises you: `uni-vm jobs off all`, then stop the VM (a stopped VM costs only its disk). |

**The blast radius of bypass mode is the vault and the host.** Mitigations: the vault rules forbid deletes and renames by agents (on the mount a delete is real), destructive actions on your own files need your yes, the hourly notes history and Drive's trash and versions make damage cheap to undo, jobs from the vault are taken only explicitly, the relay rule never acts on forwarded text, pushes refuse personal data, and password steps are always yours.

## Backups and undo

| Layer | What it covers | How to undo |
|---|---|---|
| Never-delete conventions | outdated official files move to `z_archive/<course folder>-outdated-YYYY-MM-DD/`; applied update notes move to `_agent/inbox-applied/YYYY-MM/`; prep notes are never edited (a change is a new `-rN` revision); logs are append-only; agents archive or trash instead of deleting | open the older copy |
| Notes history (always-on host only) | hourly git snapshot of every text note (`md html json canvas base css py txt csv tsv ts`, up to 8 MB) in `~/vault-history/`; private paths and `vm.history_exclude` skipped | `uni-vm history <note>`, `uni-vm history show <rev> <note>` (an old version), `uni-vm history since <when>` |
| Your sync provider | Google Drive keeps deleted files in its trash and older versions of changed files | restore from drive.google.com |
| Host disk snapshots (cloud VM) | weekly snapshots kept `vm.snapshot_retention_days` (21) days, deletion protection | restore the disk; rebuilding the host from scratch takes about 20 minutes ([vm README](../modules/vm/README.md), "Rebuild from scratch") |
| The manifest | which files `uni-os` installed and their hashes | `uni-os init` restores deleted installed files; `doctor -v` lists the files you edited |

Laptop-only setups have no notes history; Drive's version history is the safety net. If you want more, a periodic copy of the vault to another disk is enough.

## Before you make a vault public

To show the system to someone, the safest option is not your vault at all: render a fictional one with `python tools/uni_os.py init --config examples/alex.toml --vault <folder>`. If you still want to share your own (or parts of it), work on a **copy** and go through this list:

1. **Run the scan:** `python tools/uni_os.py doctor --vault "<copy>"` must show no secrets findings. Then search for mail addresses, phone numbers and long numbers yourself.
2. **Remove private and personal pages:** every `private` folder, the note app's data folder, `me/` (profile, learning style, rhythm and habits, weak spots), `progress/` (results, bonus standing, tracker log, week pages), the error logs, `semester/prep/` (they quote your calendar), plans, `inbox/` and `_agent/inbox-applied/`, `_agent/logs/`, `_agent/heartbeat/`, `_agent/coordinator-state.md`, `_agent/handoffs/`, `_agent/handover/`, `_agent/vm/`, `_agent/course-fetch/` logs, `_agent/vault-watch/` logs and inventory.
3. **Remove other people:** names of classmates, TAs and lecturers in notes, logs and course cards.
4. **Remove material that isn't yours:** official course files (slides, scripts, sheets, recordings) are usually not yours to publish; delete the official subfolders and `z_archive/`.
5. **Integrity:** never publish solutions to graded work, not even after the term; courses reuse tasks.
6. **Remove identifiers:** storage folder ids, calendar ids, session ids, links to private pages, your cloud project id, your ntfy topic, absolute paths with your user name (write `C:/Users/<you>`).
7. **Clean the config:** `_agent/uni-os.toml` and `_agent/uni-os.json` hold your name, university and course links; replace or delete them.
8. **Per-device Obsidian files:** `.obsidian/workspace*.json`, plugin `data.json` files.
9. **If the vault was ever a git repository,** secrets and personal files stay in its history: publish a fresh repository, not the old one.
10. The manifest `_agent/.uni-os-manifest.json` is safe: it holds vault-relative paths and hashes only.

## Rules for contributors to this repository

This repository is public. Everything in it must be free of personal data:
- **No real people** except the author, Qiang Luo (ktr0a), and only as author and credit. Examples use the fictional student **Alex Example** at **Example Institute of Technology** (EIT) with the courses AD, DM, LA and PROG (`examples/alex.toml`).
- **No personal records:** no grades, results or bonus points, no error-log rows, no schedules, habits, health or travel details, no personal reply quirks, no personal calendar names.
- **No identifiers:** no storage, calendar, cloud-project, LMS or session ids, no artifact or private-page URLs, no ntfy topics, no mail addresses, no Windows user paths (write `C:/Users/<you>`).
- **Schedules are config keys.** The original's times may appear only as example defaults.
- **Integrity first:** the default assistance level is `hints-only`, and `solo` means no help at all; new roles and jobs must follow [`academic-integrity.md`](academic-integrity.md).
- **Checks before a commit:** `python -m unittest discover -s tests` (it renders every module with `examples/alex.toml` and runs `uni-os doctor --strict`, including the secrets scan, on the result), and the module test suites you touched. The repo's `.gitignore` already excludes local configs (`config/uni-os.toml`, `*.local.toml`), local test vaults, `.env` files, keys and `ntfy-topic`.

## Related pages

- [`academic-integrity.md`](academic-integrity.md): what agents may and may not do on your coursework.
- [`storage.md`](storage.md): what stays out of the vault.
- [`runtimes.md`](runtimes.md): what bypass mode is needed for, and where it runs.
- [`../modules/course-files-fetch/README.md`](../modules/course-files-fetch/README.md), "Threat model".
- [`../modules/vm/README.md`](../modules/vm/README.md), "Security posture".
