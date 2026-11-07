# Agent instructions for the Uni OS framework

You are working in the **framework repository** of Uni OS. The repository builds a student's study system, the **vault**: a folder of plain Markdown, usually inside a synced cloud drive, that the student and their agents share. The framework and the vault are two different folders:

- **This repo** holds the module templates, the `uni-os` command line and the docs.
- **The vault** belongs to the student. It has its own `AGENTS.md`, which sends agents to `_agent/agent-start.md`. When you work inside a vault, follow that file, not this one.

Uni OS has only been tested with Claude Code. These instructions are agent-neutral. Where a step uses a Claude Code feature, the linked file says so ("In Claude Code: ...") and gives the fallback. Claude Code users also get [CLAUDE.md](CLAUDE.md), which imports this file.

## What the student asks, and what you do

| The student says | You do |
|---|---|
| "set me up", "install Uni OS", "build my study system", or similar | Follow [setup/PLAYBOOK.md](setup/PLAYBOOK.md) step by step: the interview ([setup/interview.md](setup/interview.md)), the module choice ([setup/presets.md](setup/presets.md)), the config, `init`, `doctor`, then optional automation. Do not skip or reorder steps. |
| "add the VM", "turn off daily prep", "add a course", "change the check-in to Sunday", "make DM solo", any change to an existing vault | Follow [setup/changing-modules.md](setup/changing-modules.md). |
| "what can this do?", "which modules should I pick?" | Answer from [README.md](README.md), [modules/README.md](modules/README.md) and [setup/presets.md](setup/presets.md). Install nothing. |
| Questions about daily use or the first week | [setup/after-setup.md](setup/after-setup.md). |
| "I want to set it up myself, without you" | Point to [setup/manual-setup.md](setup/manual-setup.md). Say plainly that it is very tedious, because Uni OS is an agent-based system. |
| "how does X work?" | The module's `README.md`, then [docs/](docs/): [architecture](docs/architecture.md), [runtimes](docs/runtimes.md), [file formats](docs/file-formats.md), [glossary](docs/glossary.md), [faq](docs/faq.md). |
| "make the laptop scripts work on my Mac / Linux" | [docs/porting-to-other-os.md](docs/porting-to-other-os.md) and the behaviour spec in the module's README. |
| Fix a bug, change a module, write a new module | The contribution rules below. |

## Rules

1. **The student's vault is theirs.** Write into it only through the steps of the playbook or of `changing-modules.md`, and only after the student agreed to that step. Show what will change first (`--dry-run`). Never delete, move or rename files in a vault unless the student asked for exactly that. `init` never overwrites. Use `--force` only after the student said yes for exactly those files, because it replaces files they edited.
2. **Never type secrets.** That covers passwords, API keys, tokens, ntfy topics and private calendar (iCal) addresses. The student enters them themselves: in the ntfy app, in a secret file outside the vault, in Obsidian's secret storage, or at a login prompt. Never write a secret into the config, the vault, this repo, a log, a push or a reply. The config may only hold the *path* to a secret file (for example `notify.ntfy_topic_file`).
3. **Never commit secrets or personal data.** The student's real config stays out of git: `config/uni-os.toml` and `*.local.toml` are ignored, and the vault's copy at `<vault>/_agent/uni-os.toml` is outside the repo anyway. Never commit or push without the student's explicit yes.
4. **Integrity first.** The default assistance level is `hints-only`. `solo` means no help at all on that work. Never lower a course's or an assessment's assistance level on your own. Change it only on the student's explicit words, and record them.
5. **The password step stays with the student.** Logged-in course sites are read-only. You may click through single sign-on, but you never type a password, even with permission.
6. **System changes need a yes.** Scheduled tasks, Task Scheduler entries, systemd units, a cloud VM, installed software, and changes to the agent's own settings or permission mode all wait for a yes. Explain each one first. If your agent may not register persistent tasks or edit its own permissions, hand the student the exact command to run.
7. **One place per value.** Schedules, courses and assistance levels live in the config. Change the config, then run `render`. Never hand-edit generated files: `_agent/uni-os.json`, the manifest, or a rendered `job.conf`.
8. **No fixed days or times.** Every schedule is a config key the student picks. The original system's times are examples, not defaults to push.
9. **Nothing beyond the request.** Ask before adding a module, a job, a recipient or a step the student did not ask for.

## Commands

Run from the repo root. Python is `python` on Windows and usually `python3` on Linux and macOS. The CLI needs Python 3.11+ and only the standard library.

```text
python tools/uni_os.py --help                       # every command; <command> --help for details
python tools/uni_os.py modules                      # the catalogue; --preset minimal|standard|full
python tools/uni_os.py config validate --config <file.toml>
python tools/uni_os.py init --config <file.toml> --vault "<folder>" [--modules a,b | --preset P] [--dry-run]
python tools/uni_os.py --vault "<folder>" render [--dry-run]
python tools/uni_os.py --vault "<folder>" enable <id> ...   /   disable <id> ...
python tools/uni_os.py doctor --vault "<folder>" [--strict] [-v]
```

`init` always needs an explicit `--vault`; it never takes `paths.vault` from the config as a write target. The full reference is [tools/README.md](tools/README.md), and every config key is in [config/schema.md](config/schema.md).

Checks before you finish a change to the framework:

```text
python -m unittest discover -s tests                         # tools and the real catalogue
python -m unittest discover -s modules/<id>/tests            # each module you touched that has Python tests
bash modules/vm/tests/run-tests.sh                           # vm host scripts (full set on Linux or WSL)
powershell -NoProfile -ExecutionPolicy Bypass -File modules/vault-watch/tests/test-vault-watch.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File modules/course-files-fetch/tests/test-course-pickup.ps1
cd modules/cockpit/plugin && npm test && npm run check       # cockpit plugin (npm install once first)
bash -n <script>                                             # any shell script you changed

# render everything into a scratch folder, then check it
python tools/uni_os.py init --config examples/alex.toml --vault <scratch> --modules <all ids, comma-separated> --date 2026-11-07 --force
python tools/uni_os.py doctor --vault <scratch> --strict
```

Render into a scratch folder outside any real vault. The repo-root names `test-vault*` and `scratch/` are git-ignored.

## Repo layout

| Path | What |
|---|---|
| `setup/` | the setup playbook, interview, presets, manual setup, after setup, changing modules |
| `config/` | `uni-os.example.toml` (every key, commented) and `schema.md` (type, default, used by) |
| `tools/` | the `uni-os` CLI (`tools/uni_os.py`) and its package `tools/uni_os/`; commands are auto-discovered from `tools/uni_os/commands/*.py` |
| `modules/<id>/` | one module: `README.md`, `module.toml`, `vault/` templates, `jobs/<job>/`, `roles/<role>.md`, `skills/<skill>/SKILL.md`, code in `scripts/`, `host/`, `laptop/`, `plugin/`, tests in `tests/` |
| `docs/` | architecture, runtimes, storage, agents, porting, security, integrity, file formats, glossary, FAQ |
| `examples/alex.toml` | the complete config of the fictional student Alex Example |
| `tests/` | unit tests for the tools; `test_repo.py` checks the real catalogue |

## Contributing

**Module structure.**

- `module.toml` declares `id` (= the folder name), `name`, `tier` (`core`, `standard`, `advanced` or `addon`), `summary`, `requires`, `recommends`, `obsidian`, `os`, `runtime`, `config_keys`, `verbatim`, `[[jobs]]`, `[[roles]]`, `[[skills]]`, optional `[[folders]]` and `[[contracts]]`, and `[defaults]`.
- `README.md` keeps this section order: title, one-paragraph summary, At a glance, Why it exists, How it works, What gets installed, Configuration, Daily use, Agents other than Claude Code, Failure modes and fixes, Lessons from the original system, Removing it. A module may add sections of its own between them (the `vm` README adds "Cost and sizing" and "Security posture").
- After a change to the cockpit's TypeScript, run `npm run build` in `modules/cockpit/plugin`: the built files in `modules/cockpit/dist/` and the module's vault copy are committed, so users need no Node toolchain.

**Config keys.** Every key a module reads goes into:

1. its `[defaults]`;
2. its README's Configuration section;
3. all three shared files: `config/uni-os.example.toml`, `examples/alex.toml` and `config/schema.md`, where the "Used by" column names the defining module first.

`tests/test_repo.py` fails when a module default is missing from one of the three shared files, or when `config/uni-os.example.toml` and `examples/alex.toml` differ in any key or value (only `uni_os.preset` and `modules.enabled` may differ). The test starts from each module's `[defaults]`: a key a module reads without a default, and the README's Configuration section, are not checked, so check them yourself.

**Templates.**

- Only the known roots are template keys (see [tools/README.md](tools/README.md)), and a missing key is an error.
- Guard optional parts with `{{#if modules.<id>}}`.
- A `{{course.` segment in a path renders the file once per course.
- Wrap text that `render` must keep current in edited files in `<!-- uni-os:begin NAME -->` / `<!-- uni-os:end NAME -->` marker lines. Each marker stands alone on its line; names are unique and not nested.

**Jobs.**

- `job.conf` uses the keys listed in [docs/file-formats.md](docs/file-formats.md), [modules/vm/README.md](modules/vm/README.md) ("The job runner") and [tools/README.md](tools/README.md); `doctor` reports any other key. Schedules come from `{{schedule.*}}` keys.
- `prompt.md` follows the 13-point anatomy in `modules/scheduler-local/vault/_agent/jobs/README.md`: idempotency guard first, real time from a command, slot branching with catch-up, never an "all good" push, a fixed output line.
- A job that can end without its result writes the failure flag `_agent/logs/flags/<job>.md`.
- Add a `PRECHECK` when an agent run is often unnecessary.
- New agent jobs that act on their own ship with `DEFAULT_MODE="off"` and go live through the staged rollout in [modules/scheduler-local/README.md](modules/scheduler-local/README.md). On the always-on host a `RUNTIME="any"` job in mode `always` arrives switched off, so a job never runs on two machines; only host-only jobs (`RUNTIME="vm"`) and jobs in failover mode switch themselves on there.

**Roles.** Front matter `type: role`, `id`, `title`, `runtime`, `model`, `effort`, `owns`, `reads`. Every duty names its trigger: a job, a calendar block or a message from the student.

**Content rules.**

- **No personal data.** No real people's names (students, TAs, lecturers). No grades, results, error-log rows, schedules, habits, health or travel of real people. No ids: drive, calendar, cloud project, LMS, session or artifact ids. No ntfy topics, no emails, no real Windows user paths (write `C:/Users/<you>`). Examples use **Alex Example** at the **Example Institute of Technology (EIT)**, with courses `algo` (AD), `dm` (DM), `la` (LA) and `prog` (PROG). The only real person named is the author, Qiang Luo (ktr0a), as author.
- **Integrity defaults.** `hints-only` by default; `solo` = no help at all. Encode both in roles, rules and job prompts.
- **Exam scope.** Exam-related content stays within exam-session dates, exam-phase scheduling, summary and cheat sheets, the final self-test of study pages and coaching for graded quizzes during the term.
- **Agent-neutral wording.** Write "your agent", with explicit "In Claude Code: ..." notes and a fallback for other agents. Say that it was only tested with Claude Code.
- **Schedules.** Never anchor on fixed days or times; every schedule is a config key.
- **Windows scripts.** Laptop scripts stay Windows-only and are marked experimental. Each comes with a precise behaviour spec in its module README (purpose, inputs, outputs, triggers, state files, safety checks).
- **Markdown style.** Sentence-case headings, tables where they help, short paragraphs, no emojis, Mermaid for diagrams. Write for a smart student who has never seen the system: concrete and exact, no filler.

**Before you finish.** Run the checks above and add a line to [CHANGELOG.md](CHANGELOG.md) under "Unreleased".
