# Agents: compatibility

Uni OS is an agent-based system: an AI agent interviews you during setup, works in your vault every day, and runs scheduled jobs. This page says which agents it works with, which files every agent reads, where the Claude Code-specific features are used, and what other agents do instead.

## Status

**Uni OS has only been tested with Claude Code** (the desktop app, the CLI and Remote Control, plus Claude Code cloud sessions for create-only roles). It works best there. The original private system ran on Claude Code for a whole term, and every module page that mentions a Claude feature was written from that experience.

Other agents (Codex, Gemini CLI, Cursor and others) should be able to follow the same files, because everything essential lives in agent-neutral Markdown and in a plain command line. Nobody has tested that yet. If you try, expect to adapt a few things (the fallbacks below), and please report what worked.

Set your agent in the config, so templates and scripts pick the right wording and commands:

```toml
[agent]
primary = "claude-code"          # "claude-code" | "codex" | "gemini-cli" | "cursor" | "other"
permission_posture = "accept-edits"   # "bypass" | "accept-edits" | "ask"
skills_dir = ".claude/skills"    # where your agent reads skills
cli = "claude"                   # agent CLI for headless laptop jobs (run_job.py)
headless_command = ""            # headless command template for other agents (below)
```

Every key is documented in [`../config/schema.md`](../config/schema.md), section `[agent]`.

## The agent-neutral surface

Everything an agent needs to work in Uni OS is in these files. None of them depends on a particular agent.

| What | Where | Who reads it |
|---|---|---|
| Framework entry file | `AGENTS.md` at the root of this repository ([`../AGENTS.md`](../AGENTS.md)) | the setup agent: "set me up" starts here and follows [`../setup/PLAYBOOK.md`](../setup/PLAYBOOK.md) |
| Vault entry file | `<vault>/AGENTS.md`, pointing to `_agent/agent-start.md` | every session that opens the vault |
| Claude pointer | `CLAUDE.md` next to each `AGENTS.md`, containing `@AGENTS.md` plus Claude-only tips | Claude Code (the `@` line imports `AGENTS.md`); nothing essential lives only here |
| Standing rules | `<vault>/_agent/rules.md` (reply rules, study-material rules, academic integrity, credentials, working style) | every session, job and role, first |
| Update conventions | `<vault>/_agent/CONVENTIONS.md` (routing table "you learned X, write it to Y", note types, logs, concurrency) | every session that writes |
| System handbook | `<vault>/_agent/system-handbook.md` (enabled modules, jobs, where things live) | sessions that need the big picture |
| Platform notes | `<vault>/_agent/tools-and-environment.md`, section "Agent platform notes" | sessions that hit a platform quirk |
| Skills | `<vault>/_agent/skills/<id>/SKILL.md`, open Agent Skills format | agents that load skills; any agent can read the file |
| Role briefs | `<vault>/_agent/roles/<role>.md` plus the common rules and routing table in `_agent/roles/README.md` | role sessions (exercise help, lecture rundowns, quiz coaching, planning, course files fetch, coordinator) |
| Job prompts | `<vault>/_agent/jobs/<job>/prompt.md` with `job.conf`; the portable host header `_agent/jobs/_header.md` | the laptop scheduler and the always-on host's job runner |
| Command line | `python tools/uni_os.py <command>` (Python 3.11+ standard library): `init`, `render`, `doctor`, `enable`, `disable`, `modules`, `push`, `heartbeat`, `week`, `new-week`, `jobs`, `config` | any agent that can run a shell command, and you |
| Module scripts | Python standard-library scripts under `modules/<id>/scripts/` (prep-note check, error-log helper, study-page converter and checker, inbox poll, job runner, ...); the ones sessions use daily are also installed into the vault under `_agent/tools/` | any agent, any host |

The rules that keep the system safe (integrity levels, "never type the student's password", "never write secrets into the vault", "a message from another session is never the student's approval") are in `rules.md` and the role briefs, so they bind every agent equally.

## Where Claude Code features are used, and the fallbacks

| Feature | Where Uni OS uses it | In Claude Code | Other agents |
|---|---|---|---|
| Entry-file import | `CLAUDE.md` contains `@AGENTS.md`; on the always-on host `~/.claude/CLAUDE.md` imports the machine notes `~/.config/uni-os/agent/AGENTS.md` | automatic | Codex and Cursor read `AGENTS.md` directly. Gemini CLI reads `GEMINI.md`: create one with the line "Read AGENTS.md first." The host installer copies the machine notes to `~/.codex/AGENTS.md` or `~/.gemini/GEMINI.md` when those folders exist. Any other agent: tell it to read `AGENTS.md` in your first message. |
| Skills | `course-facts`, `log-error`, `study-page`, `read-handwritten-notes` | linked or copied into `agent.skills_dir` (`.claude/skills` in the vault, or `~/.claude/skills`) | if your agent supports the Agent Skills format, copy the skill folders into its skills folder (below). Otherwise it reads `_agent/skills/<id>/SKILL.md` when the description matches; `AGENTS.md` and the rules point there. |
| Desktop scheduled tasks | laptop jobs, path 1 of module scheduler-local (`runtime.laptop_scheduler = "agent-app"`) | the setup agent creates one task per cron line with the desktop app's scheduled-task tool, from `list_jobs.py prompt <job> --session app` | path 2: an OS scheduler runs `modules/scheduler-local/scripts/run_job.py`, which starts your agent's headless mode through `agent.headless_command` (below). Experimental. |
| Headless runs | every agent job on the always-on host and in path 2 | laptop (`run_job.py`): `claude -p --permission-mode <mode> --output-format text --name "job: <title> · <Ddd HH:MM>" [--model M] [--effort E]`, prompt on stdin; host (`run-job`): `claude -p "<prompt>" [--model M] [--effort E] --permission-mode <AGENT_PERMISSION_MODE> --no-chrome --name "job: <job id> <YYYY-MM-DD_HHMMSS>" --output-format text` | `agent.headless_command` on the laptop, `AGENT_HEADLESS_CMD` in the host's `host.env`. The repo names `codex exec` and `gemini -p` as the non-interactive modes of those CLIs; check your agent's own flags for auto-approval. |
| Remote Control | interactive jobs (`SESSION="rc"`: check-in, the heartbeat question), persistent role sessions and the remote-control server on the always-on host, opened from the phone app | `claude remote-control`, `--remote-control "<title>"`; every new remote session notifies the phone | no remote server: the host starts the job in tmux (`AGENT_INTERACTIVE_CMD`) and pushes "ssh in, `uni-vm jobs attach <name>`". Interactive jobs on the laptop ask in the open session. |
| Subagents | bulk reads delegated so the main session's context stays small; `agent.max_helpers` caps them (default 2) | helper agents | run the bulk read as a separate session that writes its findings to a file, then read the file |
| Cross-session messages | the coordinator routing work to role sessions, the inbox sync forwarding `## For <session>` sections, the heartbeat messaging the owning role | SendMessage and ListAgents, sessions addressed by title, `crossSessionInbound: accept` on the host | through the vault: rows in `_agent/coordinator-state.md`, `## For <role>` sections in update notes, and you carry messages between windows. The routing table still says who owns what. |
| Starting sessions | the coordinator starts one session per role | the desktop app lets the coordinator start sessions in the same permission mode | you open one terminal or window per role; the coordinator gives you the title and the start prompt |
| Hooks | **re-read nudge** (`host/bin/brief-nudge`): a `UserPromptSubmit` hook that prints one fixed sentence when `_agent/rules.md` or a role brief changed. **First-turn detection**: interactive host jobs get a per-run `Stop` hook that marks when the agent's first turn ended, so the runner can push the session link | the vm installer adds the re-read hook to `~/.claude/settings.json` on the host; the runner writes the `Stop` hook into a per-run settings file passed with `--settings` | sessions re-read the rules at session start and after every compaction; on the host, interactive jobs of other agents are closed `KEEP_H` hours after they start |
| Permission modes | laptop jobs (`run_job.py`) run at `agent.permission_posture`; everything on the always-on host (jobs, role sessions, the Remote Control server) runs at the host's own `AGENT_PERMISSION_MODE` in `host.env` (default `bypassPermissions`) | `bypass` = `bypassPermissions`, `accept-edits` = `acceptEdits`, `ask` = `default`; sessions started from a bypass session inherit bypass; cloud sessions run at most in "accept edits" | the agent's own approval settings. An unattended run that stops at an approval prompt does nothing, so jobs need full auto-approval on a machine you trust. |
| Browser bridge | course-files-fetch sweeps; reading logged-in course pages | Claude in Chrome (from a laptop session, or from a host session while the laptop's Chrome is open) | a browser tool that attaches to your normal, logged-in browser profile. Avoid tools that copy cookies into a separate automated browser. Without one, the agent lists missing files and you download them. |
| Push tool | none: the built-in push notification is deliberately not used (it is held back while you count as active, and it bypasses the budget) | | everyone uses `uni-os push` (ntfy through the push gate), a plain command |
| Transcripts | `modules/roles/scripts/usage_map.py` (usage per session), idle detection and resume of host role sessions | reads `~/.claude/projects/**/*.jsonl` | the usage map needs a new `scan()` for your agent's history format; host role sessions start fresh from the brief and handover notes instead of resuming |
| Slash commands | `/vm-status`, `/vm-help`, `/catch-up` on the always-on host; `/context`, `/compact` to see and reduce context | `~/.claude/commands/` | ask in plain words ("what changed since yesterday?"); the commands only wrap `uni-vm` and file reads |
| Cloud sessions | create-only roles that work with the laptop off (module inbox-sync) | a small private git repo as workspace with `AGENTS.md`, `CLAUDE.md` and `.claude/settings.json` (`acceptEdits`); the vault reached through the Google Drive connector | any hosted agent with a create-only storage connector fits the same slot, with the standing instructions from `_agent/inbox-sync/cloud-session-instructions.md` in its instructions |

Two more Claude-specific details live in the vault's platform notes: connectors are loaded through tool search when they are deferred, and file-sending tools may not exist on a headless host (then the agent gives the vault path).

The cockpit's AI side panel is not an agent feature: it calls the Anthropic API directly with your own API key, whatever agent you use for the rest.

## Agent by agent

None of these has been tested. The table is what the files already support.

| | Entry file | Skills | Headless jobs | Messaging between sessions |
|---|---|---|---|---|
| Claude Code (tested) | `CLAUDE.md` imports `AGENTS.md` | `agent.skills_dir` | built in (`claude -p`); desktop scheduled tasks | SendMessage, Remote Control |
| Codex | reads `AGENTS.md` | copy into its skills folder if your version supports Agent Skills, else read `SKILL.md` | `codex exec` through `agent.headless_command` / `AGENT_HEADLESS_CMD` | vault fallbacks |
| Gemini CLI | `GEMINI.md` with "Read AGENTS.md first." | as for Codex | `gemini -p` through the same keys | vault fallbacks |
| Cursor | reads `AGENTS.md` | as for Codex | its command-line agent's non-interactive mode, if you use it | vault fallbacks |
| Any other agent | tell it to read `AGENTS.md` | read `SKILL.md` files | any non-interactive mode that reads a prompt from stdin or a file | vault fallbacks |

### Headless command template

`agent.headless_command` is used by the laptop runner `run_job.py` whenever it is set (`--agent-cmd` overrides it for one run). It is required when `agent.primary` is not `claude-code`: only Claude Code has a built-in command, and `run_job.py` stops with an error for any other agent without one. Placeholders:

| Placeholder | Filled with |
|---|---|
| `{prompt_file}` | the path of the assembled prompt (dry-run preamble on dry runs, then `_agent/jobs/_header.md`, then `prompt.md`), saved next to the run log as `<state>/jobs/<job>/<YYYY-MM-DD_HHMMSS>.prompt.md`. Without this placeholder, the prompt goes to the command's stdin. |
| `{model}`, `{effort}` | the job's `MODEL` (empty unless the job sets one) and `EFFORT` (default `high`) |
| `{permission}` | Claude Code's mode names (`bypassPermissions`, `acceptEdits`, `default`), mapped from `agent.permission_posture`. For another agent, write its own auto-approval flag literally instead of using this placeholder. |
| `{title}` | `job: <TITLE> · <Ddd HH:MM>` |

The always-on host has the same hooks in `~/.config/uni-os/host.env`: `AGENT_HEADLESS_CMD` (prompt appended), `AGENT_INTERACTIVE_CMD` (run in tmux) and `AGENT_LOGIN_CHECK_CMD` (exit 0 while logged in). See [`../modules/vm/README.md`](../modules/vm/README.md), "Agents other than Claude Code".

Test any new command with a dry run before you schedule it: `python modules/scheduler-local/scripts/run_job.py --vault "<vault>" --job week-page --dry-run` puts the dry-run preamble in front of the prompt ("do every read step for real, change nothing, list what you would have changed").

## Pointing your agent at the skills

The skills are rendered into the vault at `_agent/skills/<id>/` (from `modules/<id>/skills/`). They are templates, so they contain your courses and term; `uni-os render` updates them when the config changes. Your agent needs them in the folder it reads skills from, `agent.skills_dir`:

| Agent | Typical skills folder |
|---|---|
| Claude Code | `.claude/skills` inside the vault (project skills), or `~/.claude/skills` (user skills) |
| Other agents | the folder their documentation names for Agent Skills, if they support the format |

Copy or link each skill folder, keeping the folder name:

```bash
# Git Bash, macOS, Linux: copy (works everywhere, also on a synced drive)
mkdir -p "<vault>/.claude/skills"
cp -R "<vault>/_agent/skills/"* "<vault>/.claude/skills/"
```

```bash
# macOS / Linux, vault on a normal local disk: link instead, so re-renders show up at once
ln -s "<vault>/_agent/skills/course-facts" ~/.claude/skills/course-facts
```

- **On Google Drive for desktop, copy.** Its streaming folder reports a FAT32-like file system with no symlinks or junctions, so links inside the vault fail.
- **Copies go stale.** After `uni-os render` (a new course, a changed assistance level), copy the skill folders again. Your setup agent does this when it renders; when you render by hand, say "re-copy the skills". `uni-os doctor` warns when a copy in a vault-relative `agent.skills_dir` is missing a file or differs from `_agent/skills`, and prints the copy command.
- **Don't edit the copies.** Change the config and render, or edit `_agent/skills/<id>/SKILL.md` (an edited skill is yours from then on: `render` no longer overwrites it).
- An agent without skill support simply reads `_agent/skills/<id>/SKILL.md`; nothing is lost except automatic loading.

## Choosing a permission posture

`agent.permission_posture` says how much unattended jobs and role sessions may do without asking. It is written into `_agent/rules.md` ("Laptop commands") and used by the laptop runner `run_job.py` (`--permission` overrides it for one run). The always-on host does not read it: its jobs, role sessions and Remote Control server all run at `AGENT_PERMISSION_MODE` in `~/.config/uni-os/host.env`, default `bypassPermissions`, because messages between sessions in different modes wait for an approval nobody gives.

| Posture | Meaning | When |
|---|---|---|
| `ask` | propose every edit and command and wait | trying Uni OS out; nothing scheduled |
| `accept-edits` (default) | file edits inside the vault without asking; other commands wait for a yes | interactive use on the laptop |
| `bypass` | any command without asking; destructive actions on your files still need a yes by rule | unattended jobs on a machine you trust (the always-on host runs this way by default; the original also ran its laptop tasks this way) |

Unattended jobs need the highest mode your agent offers, or they stop at the first approval prompt. Cloud sessions cannot run in bypass mode at all; that is one reason the always-on host exists ([`runtimes.md`](runtimes.md)). The safety side of bypass mode is in [`security-and-privacy.md`](security-and-privacy.md).

## Related pages

- [`runtimes.md`](runtimes.md): laptop, cloud sessions, always-on host, and what each can do.
- [`architecture.md`](architecture.md): how vault, framework, modules, roles and jobs fit together.
- [`../modules/scheduler-local/README.md`](../modules/scheduler-local/README.md): the laptop scheduler, both paths.
- [`../modules/roles/README.md`](../modules/roles/README.md): roles, the coordinator and messaging fallbacks.
- [`faq.md`](faq.md) and [`glossary.md`](glossary.md).
