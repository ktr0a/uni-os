# FAQ

Short answers with links to the full story. `uni-os` is short for `python tools/uni_os.py`, run in this repository's folder.

**Getting started**
- [What is Uni OS, in two sentences?](#what-is-uni-os-in-two-sentences)
- [How do I set it up?](#how-do-i-set-it-up)
- [Can I set it up without an agent?](#can-i-set-it-up-without-an-agent)
- [Can I see an example first?](#can-i-see-an-example-first)
- [What do I need installed?](#what-do-i-need-installed)

**Cost and tools**
- [What does it cost?](#what-does-it-cost)
- [Which agent do I need?](#which-agent-do-i-need)
- [Does it work with Codex, Gemini CLI or Cursor?](#does-it-work-with-codex-gemini-cli-or-cursor)
- [Do I need Obsidian?](#do-i-need-obsidian)
- [Do I need Google Drive?](#do-i-need-google-drive)

**Platforms and devices**
- [I use macOS or Linux. Can I use it?](#i-use-macos-or-linux-can-i-use-it)
- [Can I use it from my phone?](#can-i-use-it-from-my-phone)
- [What about several devices?](#what-about-several-devices)
- [What happens when my laptop sleeps?](#what-happens-when-my-laptop-sleeps)
- [Do I need the VM?](#do-i-need-the-vm)
- [How do I remove the VM later?](#how-do-i-remove-the-vm-later)

**Privacy and integrity**
- [Is my data private?](#is-my-data-private)
- [Isn't this cheating?](#isnt-this-cheating)

**Changing things**
- [How do I change a schedule?](#how-do-i-change-a-schedule)
- [How do I add a course in the middle of the term?](#how-do-i-add-a-course-in-the-middle-of-the-term)
- [Can I turn a module off? Will it delete my files?](#can-i-turn-a-module-off-will-it-delete-my-files)
- [I edited a generated file. Will `uni-os render` overwrite it?](#i-edited-a-generated-file-will-uni-os-render-overwrite-it)
- [How do I update to a new version of the framework?](#how-do-i-update-to-a-new-version-of-the-framework)
- [Too many pushes, or too few. How do I tune them?](#too-many-pushes-or-too-few-how-do-i-tune-them)

**Fit**
- [I'm not a computer science student. Does it fit?](#im-not-a-computer-science-student-does-it-fit)
- [My university works in another language. Is that a problem?](#my-university-works-in-another-language-is-that-a-problem)
- [My platform isn't Moodle, my calendar isn't Google. Does it matter?](#my-platform-isnt-moodle-my-calendar-isnt-google-does-it-matter)
- [What happens if two agents edit the same file?](#what-happens-if-two-agents-edit-the-same-file)
- [Where is the handwriting app the original used?](#where-is-the-handwriting-app-the-original-used)
- [How can I contribute?](#how-can-i-contribute)

---

## Getting started

### What is Uni OS, in two sentences?

A framework that turns a folder of Markdown notes into a study system run by AI agent sessions: course folders, study pages, hints-only exercise help, error logs, week pages, planning, daily prep notes, check-ins, a proactive watcher and phone pushes. You clone it, open your agent and say "set me up". The agent interviews you, you pick modules, and a deterministic script builds your vault from templates. I built the original for my own first year of BSc Computer Science at ETH Zurich (HS26); this version is generalised for any student ([how-it-evolved.md](how-it-evolved.md)).

### How do I set it up?

Clone the repository, open your agent in the folder and say "set me up". The agent follows [setup/PLAYBOOK.md](../setup/PLAYBOOK.md): the interview ([setup/interview.md](../setup/interview.md)), a module menu with presets ([setup/presets.md](../setup/presets.md)), `uni-os init` to scaffold the vault, and then the optional automation, one piece at a time. [setup/after-setup.md](../setup/after-setup.md) covers the first week.

### Can I set it up without an agent?

Yes, but it is very tedious, because Uni OS is primarily an agent-based system. You fill in the config by hand from [`config/uni-os.example.toml`](../config/uni-os.example.toml) and [config/schema.md](../config/schema.md), run `uni-os init`, then create the scheduled tasks, the course facts and the calendar yourself. [setup/manual-setup.md](../setup/manual-setup.md) walks through it. Even then, the study engine needs an agent to do anything day to day.

### Can I see an example first?

Yes. [`examples/alex.toml`](../examples/alex.toml) is the complete config of a fictional student, Alex Example, at the Example Institute of Technology (EIT), with four first-year courses. Render it into an empty folder:

```text
python tools/uni_os.py init --config examples/alex.toml --vault "<an empty folder>" --date 2026-11-07
python tools/uni_os.py doctor --vault "<that folder>"
```

Then open the folder as a vault in Obsidian, or just browse it. Add `--modules <id>,<id>` (or `--preset minimal`) to see a smaller setup.

### What do I need installed?

- Python 3.11 or newer. The `uni-os` tools use only the standard library.
- Your agent (only Claude Code has been tested).
- Git, to clone the repository.
- Optional: Obsidian, the ntfy phone app, and a cloud drive client.

Node and npm are needed only to rebuild the cockpit plugin, which ships prebuilt. On Windows, `python -m pip install tzdata` makes the term time zone exact ([tools/README.md](../tools/README.md#windows-notes)).

## Cost and tools

### What does it cost?

| Part | Cost |
|---|---|
| The framework | free (MIT licence) |
| Your agent | your agent subscription. Long-lived sessions and scheduled jobs use it; recycling long sessions keeps the cost down ([roles](../modules/roles/README.md)) |
| Phone pushes (ntfy) | free on the public server |
| Obsidian (optional) | free |
| Cockpit assistant panel (optional) | your own Anthropic API key, billed separately; the original estimated about $1-5 a month at about 20 questions a day ([cockpit](../modules/cockpit/README.md)) |
| Always-on host (optional) | the original's 4 GB Google Cloud VM cost about $21 a month at list price; a home server costs electricity ([vm](../modules/vm/README.md#cost-and-sizing)) |

### Which agent do I need?

Uni OS has only been tested with Claude Code (desktop app, CLI and Remote Control) and works best with it. Everything essential is in agent-neutral files (`AGENTS.md`, `SKILL.md` skills, role briefs, job prompts), so other agents should be able to follow them ([agents.md](agents.md)).

### Does it work with Codex, Gemini CLI or Cursor?

They should be able to read the same files, but this is untested. What you lose depends on the agent:
- **Desktop scheduled tasks:** use an OS scheduler that runs your agent's CLI headless (`agent.headless_command`, [scheduler-local](../modules/scheduler-local/README.md)).
- **Starting sessions and messaging between them:** you open one window per role yourself, and messages go through the vault.
- **Remote Control from the phone:** on the always-on host, ssh plus tmux instead.
- **Hooks:** sessions re-read the rules at start-up and after compaction instead.

Every module README has a section "Agents other than Claude Code" with the details. Gemini CLI reads `GEMINI.md`; create one containing "Read AGENTS.md first."

### Do I need Obsidian?

No, it is recommended but optional. Everything is plain Markdown. Without Obsidian, the Bases views, the Home dashboard and the cockpit plugin are hard to get. Alternatives you could build: a dashboard inside your AI app (ask for the status summary each morning, or have a job write it to a note), your own HTML page that reads the same notes, or a small wrapper script ([cockpit](../modules/cockpit/README.md#not-using-obsidian)). Choose `obsidian.enabled = false` during setup and the templates use plain-Markdown variants.

### Do I need Google Drive?

No. Google Drive is the documented default: desktop sync on the laptop, and an rclone mount on the always-on host. OneDrive, Dropbox, iCloud, Syncthing or a git repository probably work, but they are untested, and their conflict-copy names and mount options differ. A purely local folder works if you only use one machine. See [storage.md](storage.md).

## Platforms and devices

### I use macOS or Linux. Can I use it?

Most of it, yes. The `uni-os` tools, the study engine, the organisation layer, the heartbeat, the push gate and the always-on host (Ubuntu) do not depend on the laptop's OS. If your agent's desktop app runs on your system, laptop scheduling through its scheduled tasks works too. Only the laptop automation scripts are Windows-only and experimental (PowerShell, Task Scheduler, VBS launchers):
- the vault watcher;
- the course-file pick-up;
- the OS-scheduler example;
- the laptop helpers for the VM.

Each one has a precise behaviour spec, so your agent can port it ([porting-to-other-os.md](porting-to-other-os.md)). Presets leave `vault-watch` and `course-files-fetch` out when the laptop's system (`runtime.laptop_os`, else the computer that runs the command) is not Windows. If you enable them anyway, `uni-os doctor` and `uni-os enable` warn about both while `runtime.laptop_os` names another system. For the course-files fetch the warning names only its laptop part: the role also runs on the always-on host, so only the pick-up task needs porting.

### Can I use it from my phone?

Partly:
- **Pushes** arrive in the ntfy app.
- **The calendar** carries each study block's `MATERIAL` links, so the material is one tap away.
- **With the always-on host**, you can open and answer sessions in the vault from the agent's phone app (Claude Code: Remote Control). The check-in arrives that way: a push with a link to its session.
- **Notes** can be read in Obsidian's mobile app if your drive syncs there. The cockpit plugin was never tried on a phone.

### What about several devices?

The vault syncs to every device through your drive, so you can read and write notes anywhere. Three rules:
- **A job runs on exactly one machine.** If a job is switched on on two machines, it runs twice.
- **Machine state stays on its machine.** The push gate and the heartbeat keep their state there, so let one machine run the heartbeat.
- **Each machine that pushes needs its own copy of the ntfy topic file**, outside the vault.

### What happens when my laptop sleeps?

Laptop sessions stop, and desktop-app scheduled tasks don't run. When the laptop wakes, the app catches up missed slots, often late. Every job prompt is idempotent: it works out which slot it belongs to and does nothing if that slot is already done. A prep note that never appeared is caught by the outcome checks or the heartbeat once something can run, and pushes don't leave a sleeping laptop at all. If this costs you prep notes or check-ins regularly, that is the case for the always-on host ([runtimes.md](runtimes.md)).

### Do I need the VM?

No. The always-on host is an optional add-on (module `vm`). The core works laptop-only. The trade-off:

| Option | Strengths | Limits |
|---|---|---|
| Laptop only | free, simple, direct edits | stops while the laptop sleeps |
| Cloud agent sessions | work with the laptop off | need a git repository, no bypass-permissions mode, can't read laptop files, write through update notes |
| Always-on host | always on, bypass mode possible, runs scheduled jobs and persistent role sessions, phone access | costs money (the original: about $21 a month) or a spare machine, and needs maintenance |

Ubuntu on Google Cloud is documented. Other providers, a Linux box or WSL2 on an old laptop at home also work ([vm](../modules/vm/README.md), [runtimes.md](runtimes.md)).

### How do I remove the VM later?

Move every job back first: re-enable the laptop copies, then `uni-vm jobs off <job>` for each, back to back, right after a slot. Move the role sessions you want to keep, using their handover notes. Then stop or delete the VM, its snapshots, the budget alert, the drive access and the agent login on it. On a Windows laptop, remove the helpers (`install-laptop.ps1 -Uninstall`) and the ssh `Host` entry. Finally run `uni-os disable vm`, which keeps your files. Details: [vm](../modules/vm/README.md#removing-it).

## Privacy and integrity

### Is my data private?

Your vault lives in your own storage. Uni OS sends nothing anywhere by itself. What leaves your machine:
- what your agent reads goes to your agent's provider, as with any agent use;
- pushes go to the ntfy server;
- the optional cockpit assistant sends questions to the API on your own key;
- your drive syncs the vault to its cloud.

Secrets (API keys, private calendar addresses, the ntfy topic, tokens) are never stored in the vault or the config, only paths to files outside it, and `uni-os doctor` scans the vault for them. Pushes refuse personal details. Folders matching `paths.never_open` (default `**/private/**`) are never read.

No agent ever types your university password. Logged-in course pages are opened only in your own browser, read-only. Agents stop at every password, one-time code and consent screen until you have signed in yourself, and they collect sign-ins into one request. The always-on host never uses your university login ([course-files-fetch](../modules/course-files-fetch/README.md), [security-and-privacy.md](security-and-privacy.md)).

### Isn't this cheating?

Uni OS is built to make that hard. The default assistance level on every course is `hints-only`: the smallest hint first, technique explained on a different example, your own steps checked, never your proof, final answer or code. For work that must be your own, the level is `solo`, and the agent gives no help at all on it. Levels are set per course and per graded assessment from your university's rules, the stricter level wins when in doubt, and course rules are never overridden in the moment, not even when you ask. Quiet windows hold pushes during timed graded work. You remain responsible for your university's rules. See [academic-integrity.md](academic-integrity.md).

Looser help on ungraded practice is a deliberate config choice, and only where your course allows it: `coach` adds full explanations on similar tasks and a line-by-line review of your complete draft, and only `full` gives worked solutions. Under `hints-only` the agent never gives the full solution, not even at the end. Asked for one, it gives the next hint (or, after the time cap, the missing idea in one line) and tells you that a looser level is a config change. The original student chose hints-only everywhere so that a tired "just tell me" would not end in a worked solution ([exercise-help](../modules/exercise-help/README.md)).

## Changing things

### How do I change a schedule?

Tell your agent, for example "move the check-in to Sunday 18:00". It edits `[schedule]` in `_agent/uni-os.toml` (here `check_in = { day = "Sun", time = "18:00", every = "week" }`), runs `uni-os render`, and reinstalls the job on its host: the desktop-app task, the OS scheduler task, or `uni-vm jobs sync` on the always-on host. A schedule lives in exactly one place, the config. For a one-off exception, start the job early by hand instead of editing a copy. All keys: [config/schema.md](../config/schema.md#schedule).

### How do I add a course in the middle of the term?

Add a `[[courses]]` entry to the config and run `uni-os render` (`--dry-run` first shows what would change). It creates the course folder, card, backlog, notes and reference folders, error log, official subfolders and handwritten folder, and refreshes the generated regions of the maps and tables. Files you edited that have no generated regions (often `courses-overview.md`) need the new rows by hand. The steps for collecting the course facts are in the course-facts skill's onboarding reference ([`course-onboarding.md`](../modules/courses/skills/course-facts/references/course-onboarding.md), section 5).

### Can I turn a module off? Will it delete my files?

`uni-os disable <id>` never deletes a file or folder. It removes the module from `modules.enabled`, writes a `DISABLED` marker into its job folders (both job runners skip them), and the generated maps stop listing it. Switch its scheduled tasks or timers off on their host too. A module that others need can't be disabled alone. See [setup/changing-modules.md](../setup/changing-modules.md).

### I edited a generated file. Will `uni-os render` overwrite it?

No. `render` replaces a file only while its hash still matches the manifest, that is, while nobody has edited it. In an edited file it refreshes only the text between the marker lines `<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->` and keeps every other byte. If a marker is missing or broken, the file is skipped and reported, never guessed. Only `--force` replaces whole files ([tools/README.md](../tools/README.md#how-installing-works)).

### How do I update to a new version of the framework?

There is no separate upgrade command; `render` does the work. Pull the new version of the repository, read [CHANGELOG.md](../CHANGELOG.md), then:

```text
python tools/uni_os.py render --vault "<vault>" --dry-run    # lists every change, including regions
python tools/uni_os.py render --vault "<vault>"
python tools/uni_os.py doctor --vault "<vault>"
```

Untouched files are updated, edited files get their generated regions refreshed, and new module files are created; your config stays as it is, and new keys arrive with their module defaults. Afterwards, reinstall any job whose `job.conf` changed on its host (on the always-on host: refresh its framework copy with `uni-vm update` or the laptop's `deploy.sh`, then run `uni-vm jobs sync`), and re-copy the skills if your agent reads copies of them.

### Too many pushes, or too few. How do I tune them?

Everything goes through one gate with a daily budget (`notify.max_per_day`, default 3), a minimum gap (`notify.min_gap_hours`, 2), quiet hours (`notify.quiet_hours`, `21:00-07:30`), dedupe and quiet windows. Lower or raise those. Tell any session "stop telling me about X until Friday" to snooze one heartbeat finding. `notify.provider = "none"` stops sending but keeps the logs. The system never sends "all good", so silence means nothing needs you ([notifications](../modules/notifications/README.md), [heartbeat](../modules/heartbeat/README.md#how-to-tune-it-and-how-to-silence-it)).

## Fit

### I'm not a computer science student. Does it fit?

Mostly. The framework leans towards engineering and computer science: study pages render maths with KaTeX, exercise help knows proofs and programming tasks, and quiz coaching assumes recurring graded quizzes. The mechanics are generic, though. Courses, assessments (`sheet`, `quiz`, `oral`, `project`, `midterm`, `other`), bonus schemes (`none`, `threshold`, `points`, `best-n`, `custom`), week pages, planning, daily prep and check-ins work for any subject. Skip the modules that don't fit, and tell the setup agent how your courses work.

### My university works in another language. Is that a problem?

No. `student.language` sets the language agents write notes and replies in, and `courses[].language` the language of each course's material. Calendar title prefixes are config keys (`calendar.lecture_prefix`, `calendar.exercise_prefix`; the original used German `V:` and `U:`). Add "all good" phrases in your language to `notify.extra_all_good_patterns` so the gate refuses them too. The framework's own docs and agent files are in English.

### My platform isn't Moodle, my calendar isn't Google. Does it matter?

Not much. `university.lms` is just a name agents use. `calendar.provider` can be `google`, `other` (whatever calendar connector your agent has) or `none`. The cockpit reads standard iCal feeds (Google, Outlook, iCloud). The daily prep works best with a calendar tool that can update event descriptions. With `calendar.provider = "none"` it reads the blocks from the week plan and writes only the prep note, with no `MATERIAL` blocks ([daily-prep](../modules/daily-prep/README.md), [config/schema.md](../config/schema.md)).

### What happens if two agents edit the same file?

Cloud drives keep the last writer's version, so one edit can vanish, or a conflict copy such as `name (1).md` appears. Uni OS keeps one owner per file (each role lists the files it owns), asks agents to re-read right before editing and to keep edits small, and lists the files where a second writer is risky. Writers that can only create files use update notes that apply only if the quoted line is still there. The Windows vault watcher alerts on conflict copies ([design-principles.md](design-principles.md#6-multi-writer-hygiene)).

### Where is the handwriting app the original used?

It's my own app, Quiet Notes, and not part of Uni OS; I may publish it separately later. The `handwritten-notes` module works with any app that exports PDFs into a folder per course ([handwritten-notes](../modules/handwritten-notes/README.md)).

### How can I contribute?

The repository has not been published yet. Version 0.1.0, the first public release, was prepared on 2026-11-07 and is planned for github.com/ktr0a/uni-os. Once it is public, issues and pull requests are welcome under the MIT licence ([LICENSE](../LICENSE)). Before sending a change:
- run `python -m unittest discover -s tests` and the module's own tests (`modules/<id>/tests/`);
- render [`examples/alex.toml`](../examples/alex.toml) into a scratch folder and run `uni-os doctor --strict` on it;
- give a new config key a module default, an entry in `config/uni-os.example.toml` and `examples/alex.toml`, and a row in `config/schema.md` (a test checks this, [tools/README.md](../tools/README.md#tests));
- keep each module README in the shared structure: summary, At a glance, Why it exists, How it works, What gets installed, Configuration, Daily use, Agents other than Claude Code, Failure modes and fixes, Lessons from the original system, Removing it;
- use only the fictional Alex Example in examples and fixtures, never real people's data;
- if you test with an agent other than Claude Code, say so: reports on what works elsewhere are especially welcome.
