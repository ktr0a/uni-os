# Setup playbook

This is the procedure your agent follows when you open it in the framework folder and say **"set me up"**. It is written for the agent: numbered steps, exact commands, and a checkpoint at the end of each step. You can read along; nothing here happens without your answers and your yes.

Uni OS has only been tested with Claude Code (desktop app, CLI and Remote Control) and works best with it. The steps are agent-neutral; where a Claude Code feature is used, an "In Claude Code:" note says so and the step names the fallback for other agents ([docs/agents.md](../docs/agents.md)).

## Conventions in this file

| Term | Meaning |
|---|---|
| `<repo>` | the framework clone (the folder that contains `tools/`, `modules/` and this file) |
| `<vault>` | the folder that becomes the student's vault (often inside the synced drive, e.g. `G:/My Drive/Uni`) |
| `<py>` | the Python 3.11+ command found in check 0.1: usually `python` on Windows, `python3` on macOS and most Linux systems. Every `python` in a command on this page means `<py>` |
| `uni-os <cmd>` | shorthand for `<py> tools/uni_os.py <cmd>`, run from `<repo>` |
| batch | one message with several numbered questions (see step 2) |
| the student | the person you are setting up |

Quote every path: vault and course folders may contain spaces and `&` (`--vault "G:/My Drive/Uni & Co"`).

## Rules for the whole setup

1. **Nothing is deleted, nothing is overwritten.** `uni-os init` never overwrites an existing file. Never pass `--force` to a vault that holds the student's own files unless they asked for that exact file to be replaced and a backup exists.
2. **Secrets stay with the student.** Passwords, API keys, private calendar (iCal) addresses and the ntfy topic are typed by the student into the app or file that needs them, never by you, never into the chat, the config, the vault or the repo. The config may hold only *paths* to secret files outside the vault (`notify.ntfy_topic_file`).
3. **Ask before installing.** Do not install software, change system settings, register scheduled tasks or accept consent screens without the student's yes. Say what, where and why first. Sign-ins and OAuth consent screens are always the student's.
4. **Integrity first.** The default assistance level is `hints-only`. `solo` means the agent gives no help at all on that work. Never weaken a course's official rule because it would be convenient.
5. **No fixed days or times.** Every schedule is a config value the student chooses. The original system's values (the module defaults) may be offered as examples, never presented as the right answer.
6. **Ask in a few big batches**, propose a default for every question, and accept "default", "skip" or "don't know" as answers ([interview.md](interview.md)).
7. **Write down progress** after every step (see "The progress file"), so a broken session can be resumed.
8. **Stop on errors.** Show the error, look it up in "If something fails", fix the cause, repeat the step. Never work around a refusal (a permission prompt, a connector that refuses a write) with keys or private feed addresses.

## The progress file

Keep a short checklist at `<vault>/_agent/setup-progress.md` from the end of step 0 on. If the student does not want anything in the vault folder before the final yes, keep it (and the draft config, step 4) in a draft folder outside the repo instead, for example `~/uni-os-setup/`. Never put it inside the repo; if it must live in the clone, use a name `.gitignore` excludes (`config/uni-os.toml`, `*.local.toml`).

```markdown
# Uni OS setup progress
Framework: <repo> · Vault: <vault> · Agent: <agent> · Started: YYYY-MM-DD

## Steps
- [x] 0 Preflight (YYYY-MM-DD): Windows 11, Python 3.12, Claude Code desktop, Google Drive, new vault
- [x] 1 Explained
- [ ] 2 Interview: batches done 1, 2 (algo, dm); open: 3, 4, 5
- [ ] 3 Modules
- [ ] 4 Config written and validated; summary confirmed
- [ ] 5 init
- [ ] 6 doctor
- [ ] 7 Post-install: 7.1 [ ] 7.2 [ ] 7.3 [ ] ...
- [ ] 8 First week page, first prep note
- [ ] 9 Handed over

## Decisions (quote the student where it matters)
## Waiting on the student
```

No secrets, no grades, nothing that is not also in the config.

---

## Step 0: Preflight

Run these checks before you explain anything. Most are one command.

| # | Check | How | Good result | If not |
|---|---|---|---|---|
| 0.1 | Python command and version | `python --version` (Windows) or `python3 --version` (macOS, most Linux) | 3.11 or higher; record the command that worked as `<py>` | `command not found`: try the other name (macOS has no `python` command, and its built-in `python3` may be older than 3.11). Neither works, or older than 3.11: ask the student to install Python 3.11+ (python.org or their package manager); do not install it yourself without a yes |
| 0.2 | You are in the framework clone | `<py> tools/uni_os.py --version` in `<repo>` | `uni-os 0.1.0` | "can't open file" or "No such file": `cd` into the clone; ask the student where they cloned it. `command not found` means the wrong interpreter name (0.1), not the wrong folder |
| 0.3 | The module catalogue is complete | `<py> tools/uni_os.py modules` | 25 modules listed, no "problems" line | re-clone; report the problem |
| 0.4 | Operating system | `<py> -c "import platform; print(platform.system(), platform.release())"` | `Windows`, `Darwin` (macOS) or `Linux` | |
| 0.5 | git | `git --version` | any version | only needed for framework updates and the VM's clone option; note it and carry on |
| 0.6 | Which agent you are | your own knowledge of your runtime | Claude Code (desktop, CLI), Codex, Gemini CLI, Cursor, other | record it for `agent.primary` |
| 0.7 | Where the vault will live | ask (batch below) | a folder outside `<repo>` | see "Vault location" |
| 0.8 | How the vault syncs | ask | Google Drive for desktop (the documented default), OneDrive, Dropbox, iCloud, Syncthing, git, or none | [docs/storage.md](../docs/storage.md) |
| 0.9 | You can write to `<vault>` | create `<vault>/_agent/` | the folder exists | see "Access to the vault folder" below |

**What the operating system means for the setup.**

- **Windows:** everything in the catalogue can run on the laptop. The laptop automation (Task Scheduler, PowerShell, VBS launchers) is experimental.
- **macOS or Linux:** the vault, the study engine and the organisation layer work; the agent app's own scheduled tasks should work too, but that is untested (the original ran only on Windows). The Windows-only parts (the OS-scheduler path of `scheduler-local`, `vault-watch`, the pick-up task of `course-files-fetch`) need porting by the student's agent first, from the behaviour specs in their READMEs ([docs/porting-to-other-os.md](../docs/porting-to-other-os.md)). The presets already leave out `vault-watch` and `course-files-fetch` on these systems (step 3); add them back only if the student wants to port them.
- **Windows Python and time zones:** Windows Python ships no time-zone database; `uni-os` then uses the computer's own clock zone and prints an INFO line. Optional, with the student's yes: `python -m pip install tzdata`.

**Which agent.** Say once, plainly: "Uni OS was only tested with Claude Code; other agents should be able to follow the same files." For other agents note now what will differ later: no desktop scheduled tasks (jobs then need `runtime.laptop_scheduler = "os"` and `agent.headless_command`, step 7.8), maybe no skills folder (agents then read `_agent/skills/<id>/SKILL.md` directly), no cross-session messaging (single-agent mode or vault-based routing, step 7.9). The `os` path exists only for Windows Task Scheduler: on macOS or Linux it must be ported first (scheduler-local in [docs/porting-to-other-os.md](../docs/porting-to-other-os.md)). Until then such a student has no laptop job runner: recommend Minimal, or Standard with `runtime.laptop_scheduler = "none"` and the jobs run by hand ("run the week-page job"), or the always-on host for the jobs.

### Access to the vault folder

The vault lies outside the repo, so the session needs write access to it before check 0.9 writes there.

> In Claude Code: in the CLI, add it with `/add-dir "<vault>"`; otherwise approve the folder access when asked. Run the setup in a mode where the student sees each step (ask, or accept edits). Only step 7.8 may need a bypass-mode session, for unattended scheduled tasks, and only if the student chooses it there.

Other agents: make sure the vault folder is writable for this session before you write there. A sandboxed CLI agent usually may write only inside the folder it was started in. It may need the vault added as an extra writable folder when it starts, or an approval at the first write (see the agent's own documentation). If neither is possible, keep the draft config and the progress file in a folder the agent may write (outside `<repo>`, see "The progress file"), and let the student run the `init` command of step 5 in their own terminal.

### Vault location

Ask: "Where should your vault live? Usually a folder inside your synced drive, e.g. `G:/My Drive/Uni` on Windows. Is it a new folder, or a folder you already use?"

On macOS, Google Drive for desktop puts the drive under `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/`, and `<account>` is the student's account address. If that path is recorded as `paths.vault`, the address lands in `_agent/uni-os.toml`, `_agent/uni-os.json` and the rendered job prompts, which all sync. So on macOS the student makes a symbolic link in their home folder, outside the Drive folder (`ln -s "<Drive path>/Uni" ~/Uni`), and `paths.vault` records `~/Uni` (interview 5.7). Leaving `paths.vault` empty also keeps the address out, but then the job prompts name no vault path. Pass either path to `--vault`; the tools record no absolute path from it.

Then check the folder:

| Finding | What it means | What to do |
|---|---|---|
| It is `<repo>`, contains `<repo>`, or lies inside `<repo>/modules` or `<repo>/tools` | the tools refuse it | pick another folder; keep the vault out of the clone entirely |
| It doesn't exist or is empty | a fresh vault | good; until step 5 only `_agent/setup-progress.md` and the draft config are written there |
| It contains `_agent/uni-os.toml` | it is already a Uni OS vault | do not start over: go to "Resuming a half-finished setup" |
| It contains `.obsidian/` or other notes | an existing vault the student uses | ask: "Adopt this vault (Uni OS adds its files next to yours and never overwrites one) or start in a new folder?" Adopting is fine; step 5's dry run shows every file that already exists and would be skipped |
| It contains files with Uni OS names (`README.md`, `Home.md`, `AGENTS.md`, `CLAUDE.md`, `inbox/`, `me/`, `progress/`, `semester/`, `resources/`, `views/`, `_templates/`, a folder named like a course) | init skips those files, so the vault would miss the generated pages | recommend a new subfolder, or a backup plus a careful look at the dry run |
| The path has spaces or `&` | fine | quote it everywhere |

**Checkpoint 0.** You know: `<repo>` (absolute path), OS, the Python command, your agent, the sync provider, `<vault>` and whether it is new or adopted. Create `<vault>/_agent/` (or the draft folder) and the progress file with step 0 ticked.

## Step 1: Explain what will happen

Tell the student, in about this many words:

> Here is the plan. (1) I ask you questions in about five batches: you, your university and term, your courses, how they are graded and how much help you want, how you study, and your tools. You can answer "default" to anything; I propose a default every time. (2) You pick modules, from a preset or one by one. (3) I write your config file and show you a summary; nothing is created before your yes. (4) A script builds your vault from templates in a few seconds and checks it. (5) We set up the pieces you chose: Obsidian, your calendar, phone pushes, scheduled jobs, and so on. Sign-ins, passwords and keys are always yours to type; I never see them.
>
> Time (rough estimates): about 20-40 minutes of questions, plus 5-10 minutes per course if I can't read your course pages; the script takes seconds; the follow-up steps take 15-60 minutes depending on the modules. The optional always-on server adds about an hour. You can stop at any point; I keep a progress note and we continue later. Nothing you already have is deleted or overwritten.
>
> It helps to have at hand: your timetable, each course's page on your learning platform (a link, or the page pasted here), the grading and bonus rules, and your term dates.

If the student gives course page links, read the public ones yourself. Pages behind a login stay in the student's browser: they paste the text, or (with a browser tool, In Claude Code: the built-in browser or Claude in Chrome) they sign in themselves and you only read.

**Checkpoint 1.** The student agreed to start. Tick step 1.

## Step 2: Interview in batches

The full question bank, with the config key, default and reason for every question, is [interview.md](interview.md). Ask batches 1 to 5 now:

| Batch | Topic | Typical length |
|---|---|---|
| 1 | You, your university and your term | 12 short questions |
| 2 | Your courses and timetable (one message per course, or one for all if they paste a timetable) | 10-15 per course, most answered from the course page |
| 3 | Graded work, bonus schemes and the help policy per course and per graded item | 4-6 per course |
| 4 | How you study, whether you use Obsidian, and which study-material formats you want | 6-11 |
| 5 | Your tools: laptop OS, agent, storage, calendar, phone pushes, where things run | 10-15 |

How to ask:
1. One message per batch. Number the questions. Put the proposed default in brackets after each: `3. Which language should notes and replies be in? [English]`.
2. Fill what you can yourself (from course pages, the timetable, earlier answers) and show it as a proposal to confirm, not as a question. Mark anything inferred: "(inferred from the LMS page, please check)".
3. Accept short answers. "Defaults for the rest" means: take every proposed default in this batch.
4. Don't ask about modules the student will obviously not use (no tablet: skip the handwriting questions). Questions read by one module carry its id in brackets, such as "(scheduler-local)" in batch 5; skip them for a student who wants Minimal. Batches 6 to 9 come after the module menu.
5. After each batch, save the answers into the draft config (step 4's format, unfinished keys left out) and tick the batch in the progress file. A session that dies loses at most one batch.

> In Claude Code: a multiple-choice question tool is useful for choices like the preset or the study formats; plain numbered questions work in every agent.

**Checkpoint 2.** The required keys are known: `student.name`, `university.name`, `term.label`, `term.timezone`, `term.week0_monday` (a Monday), and for every course `id`, `name`, `short`, `folder`, `slug`, `colour`. Each course has its graded items and an assistance level (or the default).

## Step 3: The module menu

Show the three presets from [presets.md](presets.md) in a short table and recommend one:

| If the student ... | Recommend |
|---|---|
| wants to try Uni OS, or only wants study help (course folders, study pages, hints, error logs) | Minimal |
| wants the organisation layer too (week pages, planning in a calendar, check-ins, daily prep, quiz coaching, pushes) and has the agent's desktop app or an OS scheduler | Standard (most students) |
| wants everything to run while the laptop sleeps and is happy to run a small server | Full (or Standard plus `vm`) |

Then adjust:
- Without Obsidian (`obsidian.enabled = false`) the presets leave out `obsidian` and `cockpit` by themselves.
- On macOS or Linux, Full already leaves out `vault-watch` and `course-files-fetch` (the `modules --preset` and `init --preset` output says so). Add them back only if the student wants to port them; `uni-os doctor` then warns about both.
- Without an always-on host, take out `vm`. Without cloud agent sessions and without the cockpit, `inbox-sync` is not needed.
- Add single modules if asked (the example config of the fictional student is Standard plus `inbox-sync` and `experiments`).

Show the resolved list with the dependencies added:

```bash
python tools/uni_os.py modules --preset standard
python tools/uni_os.py modules --preset standard --no-obsidian
```

**Explain the dependencies in one line each when they matter**, e.g. "daily prep needs planning (it reads the week plan), and planning needs progress (it reads the week page)". The tools add every requirement automatically; the full graph is in [presets.md](presets.md#dependencies). Say which modules add scheduled jobs (they are installed switched off and only run after the student's yes, step 7.8).

Then ask the module questions for the chosen modules only: batch 6 (schedules), 7 (calendars and block notation), 8 (notifications and push rules) and 9 (add-ons) of [interview.md](interview.md).

**Checkpoint 3.** The module list is agreed (write it as an explicit `modules.enabled` list with the dependencies included, step 4), and batches 6 to 9 are answered or defaulted.

## Step 4: Write the config, validate it, get a yes

**Where.** Write the config to `<vault>/_agent/uni-os.toml`, its final home; `uni-os init` then finds it by itself. Alternative: the draft folder from step 0 (`init --config` copies the file into the vault). Never inside the repo under a tracked name.

**What.** Plain TOML, grouped by table, in the order of [config/uni-os.example.toml](../config/uni-os.example.toml):
- `[uni_os]` with `version = "0.1.0"` and `preset` (the preset you started from, or `"custom"`).
- Every key the student answered, also when the answer equals the default for schedules (so they see their times in one place). Keys left at their default may be left out: every key has a default in [config/schema.md](../config/schema.md) or in the module's `module.toml`.
- One `[[courses]]` table per course, with its `[[courses.assessments]]` and `[courses.bonus]`.
- `[modules]` with the explicit `enabled` list from step 3 (more predictable than relying on `uni_os.preset`). Write the **resolved** list, dependencies included, exactly as `uni-os modules --preset ...` printed it (that is also what `init --preset` writes). A module listed there stays when another module is disabled later; a module that is only pulled in as a dependency is disabled together with the last module that needed it ([changing-modules.md](changing-modules.md#removing-a-module-uni-os-disable)).
- Times quoted (`"07:30"`; a bare `07:30` is not valid TOML), dates bare (`2026-09-14`), days `"Mon"` ... `"Sun"`, colours `"#1e66f5"`.
- Short comments are welcome; secrets are not (`uni-os doctor` refuses keys named like `*_token`, `*_secret`, `*_api_key`, `*_password` and scans values for key-like strings).

**Validate.**

```bash
python tools/uni_os.py config validate --vault "<vault>"          # config at <vault>/_agent/uni-os.toml
python tools/uni_os.py config validate --config "<draft>.toml"    # or a draft elsewhere
```

Fix every error. Explain every warning; an "unknown key" warning is almost always a typo (it suggests the right name). Then check the values the student cares about with the merged defaults:

```bash
python tools/uni_os.py config keys --vault "<vault>" --prefix schedule
python tools/uni_os.py config get courses.algo --vault "<vault>"
python tools/uni_os.py config keys --config "<draft>.toml" --prefix schedule   # draft elsewhere
python tools/uni_os.py config get courses.algo --config "<draft>.toml"
```

Use `--config` while the config is still a draft outside the vault; never run `init` to make these commands work.

**Show a summary** and wait for an explicit yes:

```markdown
**Your Uni OS setup (please check)**
- You: Alex Example (alex), English. Example Institute of Technology, BSc Computer Science.
- Term: Autumn 2026, week 0 = Mon 14 Sep 2026, Europe/Zurich; last lecture Fri 18 Dec; exam session 25 Jan to 19 Feb 2027.
- Vault: G:/My Drive/Uni-EIT (new folder), synced with Google Drive. Obsidian: yes.

| Course | Folder | Lectures / exercises | Graded work | Assistance level | Bonus |
|---|---|---|---|---|---|
| AD | AD | Tue, Thu 10:15 / Wed 14:15 | weekly sheets (bonus), 3 in-class quizzes | hints-only | +0.25 at 80 % of sheet points |

- Modules (22): Standard + inbox-sync + experiments. Dependencies are added automatically.
- Scheduled jobs (nothing runs until you choose which, in step 7): daily prep 17:30 and 19:30, morning check 07:30, week page Sun 10:00, check-in Sat 19:45 weekly, heartbeat 07:50 / 13:05 / 18:05 on weekdays, inbox sync 07:15 / 13:15 / 18:15 (these are the original system's times; change any of them).
- Pushes: at most 3 a day, 2 h apart, quiet 21:00-07:30, during the exam session only urgent ones (a soft quiet window); never "all good"; no personal details.
- Afterwards you will: install the ntfy app and create your topic file, open the vault in Obsidian once, connect your calendar in your agent app.
Shall I create the vault?
```

**Checkpoint 4.** `config validate` reports 0 errors; the student said yes to the summary. Tick step 4.

## Step 5: Dry run, then init

1. **Dry run.** Nothing is written:

   ```bash
   python tools/uni_os.py init --vault "<vault>" --dry-run
   python tools/uni_os.py init --config "<draft>.toml" --vault "<vault>" --dry-run   # draft elsewhere
   ```

   Read the output: the module list (dependencies included), `would be created N files (per module)`, every file path, the folders that would be created (one per official subfolder per course, and the handwritten folders), and any `skipped ... files that already exist`. In an adopted vault, show the student the skipped list: each skipped file stays theirs and the Uni OS version is not installed. They can keep theirs, or rename theirs and run the dry run again.

2. **Init.**

   ```bash
   python tools/uni_os.py init --vault "<vault>"
   ```

   Expected: `created N files`, `created N folders`, `_agent/uni-os.toml created` (or `unchanged` when the config already sat there), `_agent/uni-os.json created`, `_agent/.uni-os-manifest.json saved`. Exit code 0. Do not pass `--date` (it only fixes `generated.date` for reproducible test renders) and do not pass `--force`.

3. If you used a draft folder: from now on the vault's copy `<vault>/_agent/uni-os.toml` is the single source of truth. Tell the student; the draft can be deleted (it holds no secrets) or kept as a backup.

**Checkpoint 5.** init exited 0. Tick step 5 with the file count.

## Step 6: Check the vault

```bash
python tools/uni_os.py doctor --vault "<vault>"
python tools/uni_os.py doctor --vault "<vault>" -v        # details, edited files
python tools/uni_os.py jobs --vault "<vault>"             # installed jobs: slots, days, runtime, default mode
```

`doctor` checks the config, the modules, every installed file and folder, `uni-os.json`, the skill copies in `agent.skills_dir`, every `job.conf`, the parsed-format contracts (week pages, course cards, the `course` property, generated-region markers) and scans the vault for secrets (matches are shown redacted). It must report **0 errors**. Explain any warning. Expected: a warning for each Windows-only module the student kept on macOS or Linux (step 3), on Windows possibly an INFO line about the missing time-zone database (step 0), and an INFO line "skill(s) not copied here" until step 7.3 copies the skills. Save the `jobs` table for step 7.8.

**Checkpoint 6.** 0 errors. Tick step 6.

## Step 7: Post-install steps per module

Do only the parts whose module is enabled, in this order. Each part says what you do, what the student does, and how you know it worked. Tick each part in the progress file. The module READMEs have the full detail; most headings link to theirs.

### 7.1 Record the setup (always)

- Add one row to section 5, "Components added in this vault", of `<vault>/_agent/system-handbook.md`: the framework clone and its path (`C:/Users/<you>/...` on Windows, `/Users/<you>/...` on macOS, `/home/<you>/...` on Linux), so later sessions know where `tools/uni_os.py` is. Section 5 lies outside the generated regions, so `uni-os render` keeps it.
- In section 6 of the same file, list the connectors in use (storage, calendar) as you set them up. Never a secret, only where it lives.
- Tell the student how daily work starts: open the agent **in the vault folder**, not in the repo. The vault's `AGENTS.md` (and `CLAUDE.md`, which imports it) send every session to `_agent/agent-start.md`.
- Gemini CLI reads `GEMINI.md`: if that is the agent, create `<vault>/GEMINI.md` with the line `Read AGENTS.md first.`

### 7.2 Fill what templates can't compute (courses, planning, student-model, resources)

- With `courses` in an adopted vault: check that the student's existing course folders and official subfolders match the configured names; a mismatch means a second, empty folder next to theirs (fix the name in the config, then `render`).
- With `planning`: the term-week table in `semester/calendar-and-dates.md` is generated (week 0 from `term.week0_monday` to the week of `term.last_lecture_day`, each with its Monday) and `uni-os render` keeps it current, so never fill it by hand. Check its first and last row against the university's academic calendar with the student; a wrong row means a wrong `term.week0_monday` or `term.last_lecture_day`: fix the config and render (`python tools/uni_os.py week --vault "<vault>" --date <YYYY-MM-DD>` checks a date). Fill in the daylight-saving switch date, and add every other numbering the student mentioned as a translation line.
- With `student-model`: offer the short interview (about ten minutes, one question at a time) that fills `me/profile.md` and `me/rhythm-and-habits.md`. Skipping it is fine; the pages fill over time.
- With `resources`: offer the first verification pass: "Shall we check every course fact against the course pages now? You sign in, I only read." Its results go into `resources/course-verification.md` (claims, checks, verdicts), and corrected facts into the course cards and the config.

### 7.3 Skills (courses, error-logs, study-pages, handwritten-notes)

The modules install skills in the open Agent Skills format to `<vault>/_agent/skills/<id>/SKILL.md` (`course-facts`, `log-error`, `study-page`, `read-handwritten-notes`, depending on the modules). Copy each skill folder, keeping its name, into the folder your agent reads skills from, `agent.skills_dir`:

| `agent.skills_dir` | Means |
|---|---|
| `.claude/skills` (default) | `<vault>/.claude/skills/`: project skills, loaded when a session opens in the vault (In Claude Code) |
| `~/.claude/skills` | the user's skills folder, for every project (In Claude Code) |
| another path | wherever your agent reads skills |

```bash
# bash (Git Bash, macOS, Linux)
mkdir -p "<vault>/.claude/skills" && cp -R "<vault>/_agent/skills/." "<vault>/.claude/skills/"
```

```powershell
# PowerShell
New-Item -ItemType Directory -Force "<vault>\.claude\skills" | Out-Null
Copy-Item -Recurse -Force "<vault>\_agent\skills\*" "<vault>\.claude\skills\"
```

The commands use the default `.claude/skills`; for another `agent.skills_dir` (for example `~/.claude/skills`) change the target folder.

- **Copy, don't link.** Google Drive for desktop allows no symbolic links inside its folder ([docs/storage.md](../docs/storage.md)), and a copy works with every provider.
- **Copy again after every render.** `uni-os render` (also run by `enable` and `disable`) updates only `_agent/skills/`, never the copies, and the skills contain the courses, the term and the assistance levels. Run the copy command again right after each render you run, here and later; when the student renders by hand, they say "re-copy the skills" ([docs/agents.md](../docs/agents.md#pointing-your-agent-at-the-skills)).
- **Don't edit the copies.** Change the config and render, or edit `_agent/skills/<id>/SKILL.md` itself, then copy again.
- **`doctor` checks the copies.** With a folder inside the vault (the default `.claude/skills`), `doctor` warns when a copy lacks a file of `_agent/skills/<id>/` or holds an older version of it, and prints the copy command; a skill that was never copied there is only an info line (a link or another skills folder is fine).
- Agents without a skills folder need nothing: `AGENTS.md`, the rules and the role briefs point to `_agent/skills/<id>/SKILL.md`.

### 7.4 Obsidian (module `obsidian`; [README](../modules/obsidian/README.md))

1. Student: install Obsidian 1.9 or newer (Bases views need it), "Open folder as vault" on `<vault>`, then close Obsidian again (it writes its settings back on close and would undo a merge made while it runs).
2. You: show the plan of the settings merge (dry run, changes nothing):
   `python modules/obsidian/scripts/merge_obsidian_config.py --vault "<vault>"`
3. Read the plan to the student in a few lines; after a yes, run it with `--apply`. Every changed file is backed up to `.obsidian/uni-os-backup-<timestamp>/` first. `--overwrite` only with a yes per setting.
4. Student: reopen Obsidian. Check together: `Home.md` shows the course table and the course tiles in colour; Settings > Appearance > CSS snippets lists `uni-os` switched on; the graph colours the course folders; new notes land in `inbox/`.
5. With `handwritten-notes`: add the note app's data folder and private folders to Settings > Files and links > Excluded files.

The step-by-step version for agents is installed as `_agent/obsidian/obsidian-setup.md`.

### 7.5 Cockpit (module `cockpit`; [README](../modules/cockpit/README.md))

1. Student: Obsidian 1.13.2 or newer. Settings > Community plugins > turn off Restricted mode (once) > enable "Uni OS cockpit" under Installed plugins. `init` already copied the plugin into `.obsidian/plugins/uni-os-cockpit/`; no module turns it on, because that needs restricted mode off.
2. Check: the dashboard icon in the left ribbon opens the cockpit; it shows the courses (it reads `_agent/uni-os.json`).
3. Optional, only if the student wants them, and done by the student:
   - **Assistant panel:** an Anthropic API key with a monthly spend limit, linked in Settings > Uni OS cockpit > Assistant > API key > Link... > Add secret... It lives in Obsidian's secret storage on each device, never in the vault. Billed separately from any chat subscription.
   - **Live calendars:** each calendar's private iCal address, linked the same way under Live calendar. Treat these addresses like passwords.

### 7.6 Calendar (planning, daily-prep; `calendar.provider` not `"none"`)

1. Student: connect the calendar to the agent. In Claude Code: the Google Calendar connector of the Claude app (Settings > Connectors); the student does the sign-in and consent. Other agents: their calendar tool. Without one, set `calendar.provider = "none"` (the week plan's day lines become the schedule) and `render`.
2. The calendars named in `[calendar]` must exist (defaults `Courses`, `Study blocks`, `Events`, `Busy`). The student creates or renames them in the calendar app, or tells you which existing calendars to use (then change the names in the config and render). Agents find calendars by name every run; ids and private addresses are never stored.
3. You: list the calendars and a few events, read-only, to prove access. The `Courses` calendar should hold lectures titled `L: <short>` and exercise classes `E: <short>` (`calendar.lecture_prefix`, `calendar.exercise_prefix`). If it is empty, the student imports the university's timetable, or you create the recurring events after an explicit yes.
4. `calendar.standing_approval` stays `false` unless the student chose otherwise: the planner proposes calendar changes and waits for a yes.

### 7.7 Phone pushes (module `notifications`, `notify.provider = "ntfy"`; [README](../modules/notifications/README.md))

1. Student: install the **ntfy** app (Android: Play Store or F-Droid; iOS: App Store).
2. Student, in their own terminal (not in this chat, so the topic never enters a transcript): create the random topic and the secret file outside the vault, and show the topic once to subscribe to it.

   ```powershell
   # Windows PowerShell
   $t = python -c "import secrets; print('uni-' + secrets.token_urlsafe(18))"
   New-Item -ItemType Directory -Force "$HOME\.config\uni-os" | Out-Null
   Set-Content -Encoding ascii "$HOME\.config\uni-os\ntfy-topic" $t
   $t
   ```

   ```bash
   # macOS, Linux
   mkdir -p ~/.config/uni-os
   python3 -c "import secrets; print('uni-' + secrets.token_urlsafe(18))" > ~/.config/uni-os/ntfy-topic
   chmod 600 ~/.config/uni-os/ntfy-topic && cat ~/.config/uni-os/ntfy-topic
   ```

3. Student: in the app, Subscribe to topic, paste the topic, keep the server `ntfy.sh` (or their own, `notify.ntfy_server`). Android: exempt ntfy from battery optimisation.
4. You: test the path. `python tools/uni_os.py push "Uni OS test push: pushes work" --direct --source setup --vault "<vault>"`. Exit 0 and a buzz within seconds. Exit 2 "no ntfy topic file" means step 2 was skipped on this machine.
5. Propose quiet windows for timed graded fixtures from the assessments' `dates` (and a soft window with `urgent_ok = true` for the exam session); add them to `notify.quiet_windows` after a yes and `render`.

### 7.8 Scheduled jobs (modules with jobs; runner: `scheduler-local` or `vm`; [README](../modules/scheduler-local/README.md))

Most jobs are installed **switched off** (`DEFAULT_MODE="off"`). Nothing runs on the laptop until a task exists for it, and you create tasks only for the jobs the student switches on.

1. List the jobs meant for a laptop and their schedules:

   ```bash
   python modules/scheduler-local/scripts/list_jobs.py --vault "<vault>" --laptop
   python modules/scheduler-local/scripts/list_jobs.py --vault "<vault>" cron <job>
   ```

2. Recommend which to switch on now and which later:

   | Job | Module | Recommendation |
   |---|---|---|
   | `week-page`, `check-in` | check-in | now: they run the weekly rhythm |
   | `daily-study-prep`, `study-prep-morning-check` | daily-prep | now, once a calendar is connected and a week plan exists (step 8) |
   | `inbox-sync` | inbox-sync | now, if create-only writers (cloud sessions, cockpit Done taps) exist |
   | `heartbeat`, `heartbeat-weekend` | heartbeat | after the first week, as a release: dry runs, review, switch on ([heartbeat README](../modules/heartbeat/README.md), "Switching it on") |
   | `lecture-skim`, `quiz-prep`, `deadline-audit`, `waiting-on-you` | lecture-rundowns, quiz-coaching, planning, roles | optional; later, each after a dry run |
   | `outcome-checks`, `inbox-poll` | notifications, inbox-sync | command jobs: they run on the always-on host or through the OS-scheduler path, never as agent-app tasks. Without either, the heartbeat pushes the outcome findings itself and `inbox-sync` runs at its fixed slots |
   | `heartbeat-watch`, `heartbeat-ask`, `vm-health`, `vault-history`, `vm-performance-verdict` | heartbeat, vm | host only (`RUNTIME="vm"`); the VM installer takes them |

3. **Dry run** each job before its task exists:
   - path 1: `python modules/scheduler-local/scripts/list_jobs.py --vault "<vault>" prompt <job> --session app --dry-run`, pasted into a fresh session in the jobs' permission mode;
   - path 2: `python modules/scheduler-local/scripts/run_job.py --vault "<vault>" --job <job> --dry-run`.

   A dry run is an instruction, not a sandbox: it reads for real and uses plan usage. Check that it would write the right files, the push gate refused nothing ("would not send (exit 13)" means wrong wording) and it ended with exit 0.

4. **Path 1, the agent's desktop app** (`runtime.laptop_scheduler = "agent-app"`, the default). For each job the student switches on: get the assembled prompt (`... prompt <job> --session app`) and its cron lines (`... cron <job>`), and create one scheduled task per cron line (local time). A job whose slots have different minutes gets several cron lines and therefore several tasks with the same prompt, named `<job>`, `<job>-2`, ... (the `cron` output says so). A desktop task runs no `PRECHECK` and ignores `DATES`: for a job limited by `DATES` the cron line alone fires on every matching day, so single dates (`deadline-audit`, the dates in `schedule.quiz_prep_dates`) become one-time tasks, and a date range (`lecture-skim`) relies on the prompt's own guard.

   > In Claude Code: the desktop app's scheduled-task tool (`create_scheduled_task` with `taskId` = the task name above, `title`, `description`, `prompt` = the assembled text, `cronExpression` = the cron line, `notifyOnCompletion: false`). A task keeps the permission mode of the session that created it, and a task in a lower mode stops at approval prompts and does nothing; unattended jobs therefore need tasks created from a session in **bypass** mode. That is the student's choice (`agent.permission_posture`, interview question 5.3): explain the trade-off; if they choose it, they switch the session's permission mode themselves (never you) and you create the tasks from that session. Tasks run only while the desktop app is open, may start a few minutes late, and catch up missed slots on wake; the prompts are written for that.

   Other agents rarely have desktop scheduled tasks: use path 2.

5. **Path 2, an OS scheduler** (`runtime.laptop_scheduler = "os"`, Windows Task Scheduler, experimental). `python modules/scheduler-local/scripts/list_jobs.py --vault "<vault>" windows <job>` prints the PowerShell that registers the task for the current user (no admin rights). Show it to the student; run it after a yes, or let the student run it. This path also runs command jobs (`EVERY_MIN`). Other agents set `agent.headless_command` (a command template with `{model}`, `{effort}`, `{permission}`, `{title}`, `{prompt_file}`; untested).

6. Cron lines and Task Scheduler triggers use the laptop's local time, so the laptop clock should be in `term.timezone`; if it is not, convert the times before you create the tasks. With `roles`, write each switched-on job and where it runs into the "Scheduled jobs" table of `_agent/coordinator-state.md`; without `roles`, into section 4b of `_agent/system-handbook.md` (outside the generated registry). Never run one job on two machines (the VM, 7.13, takes jobs over one at a time).

### 7.9 Roles and the coordinator (module `roles`; [README](../modules/roles/README.md))

Explain the choice: one agent session that reads the role briefs as needed (fine to start), or a coordinator session plus one session per role. To start the coordinator: open a session in the vault and say "you are the coordinator"; it reads its boot list, fills in its identity in `_agent/coordinator-state.md` and starts role sessions with the titles from `_agent/roles/README.md`.

> In Claude Code: the desktop app lets the coordinator start sessions itself, in the same permission mode, and sessions message each other by title. Other agents: the student opens one window per role; requests go through the coordinator state page or `## For <role>` sections in update notes.

The optional `waiting-on-you` job (one page of what waits on the student, at most one push a day) stays off until the student says yes after a dry run.

### 7.10 Handwritten notes (module `handwritten-notes`; [README](../modules/handwritten-notes/README.md))

`init` created one empty folder per course, `<course folder>/<course folder> handwritten/` (or `handwritten_folder`). The student points the note app's automatic PDF export at those folders; you never connect the app or approve its permission screens. The app's own data folder goes into `paths.handwriting_app_data`, private folders into `paths.never_open` (then `render`).

### 7.11 Inbox sync (module `inbox-sync`; [README](../modules/inbox-sync/README.md))

Only for create-only writers. For cloud sessions, copy the standing instructions from `_agent/inbox-sync/cloud-session-instructions.md` into the cloud workspace (In Claude Code cloud sessions: the workspace repo's `AGENTS.md`). Switch on `inbox-sync` (7.8); `inbox-poll` needs the OS-scheduler path or the always-on host.

### 7.12 Windows add-ons (vault-watch, course-files-fetch; experimental)

- **vault-watch** ([README](../modules/vault-watch/README.md)): register the watcher task, from Windows PowerShell:
  `powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\modules\vault-watch\scripts\register-task.ps1" -Vault "<vault>"`.
  Some agent apps refuse to register scheduled tasks; then run it with `-NoRegister` and give the student the one-line command to run themselves.
- **course-files-fetch** ([README](../modules/course-files-fetch/README.md)): install the pick-up task on the laptop whose browser downloads:
  `powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\modules\course-files-fetch\scripts\install-course-pickup.ps1" -Vault "<vault>"`.
  Then a route test: the student downloads one small official file, you run `python "<repo>/modules/course-files-fetch/scripts/request_pickup.py" --vault "<vault>" "<file>" "<course folder>/<subfolder>"` and expect `filed` and `verified here`. The fetch session drives the student's own logged-in browser (In Claude Code: Claude in Chrome); every password, one-time code and consent screen stays with the student.

### 7.13 Always-on host (module `vm`; [README](../modules/vm/README.md))

Set `runtime.use_vm = true` and the `[vm]` answers (batch 9), then follow [modules/vm/INSTALL.md](../modules/vm/INSTALL.md) (Ubuntu on Google Cloud) or [modules/vm/HOME-SERVER.md](../modules/vm/HOME-SERVER.md) (WSL2 on a spare laptop) with the student. The cloud console, the drive consent and the agent login are the student's. Move jobs one at a time: dry run on the host (`uni-vm jobs run <job> --dry-run`), pause the laptop task, then right after `uni-vm jobs on <job>`, away from the job's slot times. Never leave a job switched on on both sides.

**Checkpoint 7.** Every enabled module's part is ticked or marked "later, by the student" with what is left. `doctor` still reports 0 errors.

## Step 8: First week page and first daily prep

1. Check the term week: `python tools/uni_os.py week --vault "<vault>"` (e.g. `Week 7 (Mon 2 Nov to Sun 8 Nov 2026), lectures`).
2. With `progress`: create this week's page. During the lecture period:
   `python tools/uni_os.py new-week --vault "<vault>" --current`
   Before week 0, create week 0's page with `--week 0`. Then fill its "Due this week" table with the week's real items (sheet numbers, concrete deadlines, personal targets), the way `_agent/jobs/week-page/prompt.md` describes, or run the `week-page` job once by hand (dry run first). `new-week` never overwrites an existing page.
3. With `planning`: ask Plan & progress (a role session, or this session reading `_agent/roles/plan-and-progress.md`) to plan the rest of the week: it writes `semester/plans/week-NN-plan.md` and proposes the calendar blocks; they are applied after the student's yes.
4. With `daily-prep`: run `daily-study-prep` once by hand for tomorrow (dry run first; In Claude Code: run the new scheduled task by hand from the app, or paste the assembled prompt into a session). Check the note:
   `python modules/daily-prep/scripts/prep_note.py check "<vault>" --date <tomorrow YYYY-MM-DD>`
5. Run `python tools/uni_os.py doctor --vault "<vault>"` once more.

**Checkpoint 8.** A current week page exists (with `progress`); with `daily-prep`, tomorrow's prep note exists and passes the check.

## Step 9: Hand over

Tell the student, briefly:
- what was set up (modules, which jobs run where and when, what is still switched off);
- what is left for them (the "Waiting on the student" list of the progress file: sign-ins, the phone app, the plugin switch);
- how to work from now on: open the agent in the vault; the first week and the daily routine are in [after-setup.md](after-setup.md); adding or removing modules later is in [changing-modules.md](changing-modules.md);
- that every setting lives in `<vault>/_agent/uni-os.toml` and changes go through the agent ("move my check-in to Sunday evening");
- that Uni OS was only tested with Claude Code.

Then mark step 9 done in the progress file and leave the file in place as a record (or move it to `_agent/archive/`).

---

## If something fails

| Symptom | Cause | Fix |
|---|---|---|
| `uni-os needs Python 3.11 or newer (it uses tomllib)` | old Python | the student installs 3.11+; on macOS/Linux try `python3` |
| `uni-os: error: init needs --vault <folder>` | `--vault` missing | init never takes the vault from `paths.vault`; always pass `--vault` |
| `refusing to use ... as the vault: it contains the framework repo` (or "inside the framework's modules/ or tools/") | vault and repo overlap | choose a vault folder outside the clone |
| `init needs --config <file>: the vault has no _agent/uni-os.toml yet` | no config in the vault and no `--config` | write the config first (step 4) or pass `--config` |
| `... _agent/uni-os.toml already exists and differs from <file>` | a vault config exists and you passed another file | edit the vault's copy and run `uni-os render`; `--force` replaces it only on an explicit yes |
| `config errors (N) ... (nothing was written)` | invalid values | fix each line; common: a bare time `07:30` (quote it), `week0_monday` not a Monday, two course folders that differ only in case, an unknown module id (the message suggests the right one) |
| `template errors (N); nothing was written` | a key a template needs is missing or has the wrong type | the message names file, line and key; fix the config (or report a module bug) |
| `CONFLICT` lines | two modules produce the same file | report it: a catalogue bug, not the student's fault |
| `doctor` warning "'vault-watch' supports windows only" or "'course-files-fetch': its laptop part supports windows only" | a Windows-only module (or the Windows-only pick-up task of `course-files-fetch`) while `runtime.laptop_os` is another system | disable it or port its laptop scripts ([docs/porting-to-other-os.md](../docs/porting-to-other-os.md)) |
| `doctor` lists missing folders or files | deleted after init | `python tools/uni_os.py init --vault "<vault>"` restores them (it never overwrites) |
| Scheduled task runs but does nothing | it stopped at an approval prompt | In Claude Code: recreate it from a bypass-mode session (the student switches the mode, step 7.8) |
| The agent app refuses to register a Task Scheduler task | the app blocks persistence | use the script's `-NoRegister` option and give the student the command |
| Push exit 2 "no ntfy topic file" | secret file missing on this machine | step 7.7, point 2 |
| Push exit 13 | the text reads like "all good", or contains a link, a mail address or a long number | rephrase as a problem with an id; links go into `--click` |
| The Obsidian merge "did nothing" | Obsidian was open and wrote its settings back | close Obsidian, run `--apply` again, reopen |
| "Uni OS cockpit" is not listed in Obsidian | restricted mode on, or the files are missing | turn restricted mode off; `uni-os init --vault "<vault>"` restores missing plugin files |
| A calendar write is refused | connector or permission mode | do not work around it; the student approves in the app, or the planner proposes and the student applies |

## Resuming a half-finished setup

1. Read `<vault>/_agent/setup-progress.md` (or the draft folder's copy). If there is none, rebuild the picture from the state on disk below and ask the student what was decided.
2. Find where you are:

   | On disk | Where you are | Continue with |
   |---|---|---|
   | no config anywhere | the interview was not saved | step 2, reusing whatever the progress file recorded |
   | a config, but no `<vault>/_agent/.uni-os-manifest.json` | init has not run | step 4: validate, show the summary again, get a yes |
   | a manifest | init ran | `python tools/uni_os.py doctor --vault "<vault>"`; then the first unticked part of step 7 |
   | the progress file says step 9 is done | setup is complete | nothing; changes go through [changing-modules.md](changing-modules.md) |

3. If the config changed after init (new answers, another module list), apply it with `render`, not `init`:
   `python tools/uni_os.py render --vault "<vault>" --dry-run`, then without `--dry-run`. Use `python tools/uni_os.py init --vault "<vault>"` only to restore files or folders that were deleted.
4. Before creating any scheduled task, check what already exists (the agent app's task list, Task Scheduler, `uni-vm jobs`), so no job ends up with two tasks.
5. Re-confirm anything the student must do themselves (topic file, Obsidian plugin switch, calendar connector) instead of assuming it happened.
