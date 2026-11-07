# Changing modules and settings later

You can add a module, remove one, or change any setting at any time, usually by saying it to your agent: "add the VM", "turn off daily prep", "move my check-in to Sunday evening". This page says exactly what happens underneath, so you (and your agent) know what to expect, and lists what the agent must check after each change.

Three commands do the work. They run from the framework folder against your vault, and **none of them ever deletes a file or a folder**:

| Command | What it does |
|---|---|
| `uni-os enable <id>...` | adds the named modules to `modules.enabled` in `<vault>/_agent/uni-os.toml` (comments kept), resolves their requirements (installed, but not written into the list), then renders |
| `uni-os disable <id>...` | removes modules from `modules.enabled`, then renders; their files stay, their jobs get a `DISABLED` marker |
| `uni-os render` | applies whatever is in the config now: a changed setting, a new course, a module list you edited by hand |

`uni-os <cmd>` is short for `python tools/uni_os.py <cmd>` (on macOS and Linux possibly `python3`). Every command takes `--vault "<vault>"` (or finds the vault you are standing in) and `--dry-run`, which prints every change and writes nothing. Uni OS has only been tested with Claude Code.

## How rendering treats your files

`render` (and therefore `enable` and `disable`) compares every file a module produces with the manifest `<vault>/_agent/.uni-os-manifest.json`, which records the hash of what was last written:

| The file is ... | render ... | Output line |
|---|---|---|
| new (a new module, a new course) | creates it | `created` |
| unchanged since it was written (hash matches) | updates it to the fresh rendering | `updated N files you had not edited` (or `unchanged N files` when the fresh rendering is the same) |
| edited, and it has generated regions whose markers are intact and match the fresh rendering | replaces only the text between each pair of markers; every other byte is kept (a CRLF file keeps CRLF) | `refreshed N files you edited: only their generated regions`, with the region names |
| edited, regions already current | leaves it alone | `kept N files you edited whose generated regions are already current` |
| edited, no generated regions | leaves it alone | `kept N files you edited (not overwritten; --force replaces them with a fresh rendering)` |
| edited, markers missing, renamed, duplicated, nested or malformed | leaves it alone and says why; nothing is guessed | `skipped N files you edited whose generated regions cannot be refreshed` |
| deleted by you | does **not** recreate it | `missing N installed files you deleted (not recreated; uni-os init restores them)` |
| no longer produced (module disabled, course removed) | leaves it in place | `orphaned N installed files no enabled module produces any more (kept, never deleted)` |

**Generated regions** are the parts of a file that the tools keep current, between two marker lines that must each stand alone on their line:

```markdown
<!-- uni-os:begin routing -->
... generated table ...
<!-- uni-os:end routing -->
```

Region names are lowercase letters, digits and `-`, unique in their file, never nested. The regions in use:

| File | Module | Regions |
|---|---|---|
| `README.md` | core | `map` |
| `where-to-find-what.md` | core | `lookup` |
| `_agent/CONVENTIONS.md` | core | `courses`, `routing` |
| `_agent/rules.md` | core | `integrity` |
| `_agent/system-handbook.md` | core | `setup`, `registry` |
| `courses-overview.md` | courses | `courses`, `rhythm`, `help`, `layout`, `official-subfolders`, `colours`, `page-offsets` |
| `<course folder>/<slug>.md` (each course card) | courses | `assessments` |
| `semester/calendar-and-dates.md` | planning | `term-weeks`, `grid`, `rhythm`, `graded` |
| `_agent/roles/README.md` | roles | `integrity`, `routing`, `roles`, `session-titles` |

So you and your agents may add your own rows and sections to these files (outside the markers), and later renders still keep the generated tables right. A file with broken markers is skipped: restore the two marker lines (copy them from a fresh render into a scratch folder) and render again. In the manifest a merged file keeps the hash of its last full rendering (so it still counts as edited and the next render merges again) plus `merged_sha256`; `doctor -v` reports it as "edited outside its generated regions; `uni-os render` refreshed the regions".

**Folders** declared by modules (one per official subfolder of each course, the handwritten folders) are created when their module is enabled, listed in the output (also with `--dry-run`), recorded in the manifest, and never deleted. Like files, a folder you deleted is not recreated by `render`; `uni-os init --vault "<vault>"` restores missing files and folders without overwriting anything.

**`--force`** replaces whole files, including ones you edited. Use it only for a specific file you want reset, with a backup.

Every render also regenerates `_agent/uni-os.json` (the machine copy of the config that the cockpit reads).

## Adding a module: `uni-os enable`

```bash
python tools/uni_os.py enable daily-prep --vault "<vault>" --dry-run
python tools/uni_os.py enable daily-prep --vault "<vault>"
```

What happens, in order:
1. The module and every module it requires are resolved. The output names what is added, for example in a vault that started from Minimal: `enabling: progress, planning, daily-prep (dependencies of daily-prep)`. Only the module you named is written into `modules.enabled`; its requirements are resolved again at every run and show as `dep` in `uni-os modules`. (A list written by the setup agent or by `init --preset` already names every module, dependencies included; those stay `enabled`.)
2. Warnings, if they apply: a module whose laptop scripts support only Windows (`vault-watch`, the pick-up task of `course-files-fetch`) while `runtime.laptop_os` is another system (its laptop part needs porting first, [docs/porting-to-other-os.md](../docs/porting-to-other-os.md)), or a module that needs Obsidian while `obsidian.enabled = false`. `enable` installs the module anyway; unlike a preset, an explicit module list is never filtered.
3. `modules.enabled` is updated (comments in the config are kept), then everything is rendered as in the table above: the module's files, roles, skills and job folders are created, and the generated maps and tables start listing it.
4. If the module was enabled before, the `DISABLED` markers in its job folders are removed.
5. The output ends with `next for <id>: read modules/<id>/README.md` (plus what it recommends) and the config keys it reads.

What `enable` does **not** do: create scheduled tasks or server timers, sign in anywhere, install apps, or set up secrets. Those host-side steps are in the module's README and in [PLAYBOOK.md](PLAYBOOK.md) step 7. New jobs mostly arrive switched off.

`enable` on a module that is already active (also as a dependency) prints `already enabled` and changes nothing.

## Removing a module: `uni-os disable`

```bash
python tools/uni_os.py disable daily-prep --vault "<vault>" --dry-run
python tools/uni_os.py disable daily-prep --vault "<vault>"
```

What happens:
1. `core` can never be disabled. An unknown id is an error; a module that isn't enabled is reported as "nothing to do".
2. If another enabled module still needs it, nothing changes: `cannot disable: planning is needed by daily-prep`, with the hint `disable them together: uni-os disable planning daily-prep`.
3. `modules.enabled` is updated and the vault rendered. Disabling the last listed module leaves `enabled = ["core"]`, never an empty list: an empty list means "use `uni_os.preset`" and would bring the whole preset back. The module is marked disabled in the manifest, each of its job folders gets a `DISABLED` file, and the generated maps, the routing table and the handbook stop listing it. Its files stay where they are (reported as orphaned).
4. **Requirements that only this module needed are disabled with it.** This only affects modules that are not in `modules.enabled` themselves (status `dep`). Disabling `daily-prep` in a vault where `planning` and `progress` came in only as its dependencies prints `disabled: daily-prep, planning, progress` (`would disable: ...` with `--dry-run`). In a vault set up from Standard they are listed themselves and stay. Read the dry run. To keep such a module, add its id to `modules.enabled` in the config first (by hand, or ask the agent; `enable` would say "already enabled"), then disable.
5. The output ends with how many files were kept and a reminder to remove the module's scheduled tasks or server timers by hand ("Removing it" in its README).

**The `DISABLED` marker** is read by the job runners: the laptop's OS-scheduler runner (`run_job.py`) and the server's runner skip a job whose folder contains it (the server sees it after `uni-vm jobs sync`). **Desktop app scheduled tasks do not read it**: pause or delete those tasks yourself (In Claude Code: in the desktop app's task list). On the server, also switch the timer off with `uni-vm jobs off <job>`.

Disabling never removes notes, course folders, week pages, prep notes, logs or anything else you or the agents wrote. Delete them yourself if you really want them gone.

## Changing a setting: edit the config, then `render`

1. Check that the module that reads the key is enabled. The "Used by" column of [config/schema.md](../config/schema.md) names it (the module that defines a key comes first), and `python tools/uni_os.py config keys --vault "<vault>" --prefix <key>` shows `# module:<id>` while the key still has that module's default. `python tools/uni_os.py modules --vault "<vault>"` must show that module as `enabled` or `dep`. If it is `available` or `disabled`, the setting has no effect: tell the student so and offer `uni-os enable <id>` instead (a check-in time does nothing without `check-in`).
2. Edit `<vault>/_agent/uni-os.toml` (the agent does this when you ask). Keys and formats: [config/schema.md](../config/schema.md).
3. Check: `python tools/uni_os.py config validate --vault "<vault>"`.
4. Preview: `python tools/uni_os.py render --vault "<vault>" --dry-run`.
5. Apply: `python tools/uni_os.py render --vault "<vault>"`.
6. Do the host-side step the change needs:

| You changed | Host-side step |
|---|---|
| a job's time or days (`schedule.*`) | update that job's task. Desktop app task: change its schedule (In Claude Code: the desktop app's scheduled-task tool), or recreate it with the new cron line from `python modules/scheduler-local/scripts/list_jobs.py --vault "<vault>" cron <job>`. OS scheduler: run the PowerShell from `... list_jobs.py --vault "<vault>" windows <job>` again. A ported launchd, systemd or cron entry (macOS, Linux): regenerate it from the new `... cron <job>` line. With `runtime.laptop_scheduler = "none"` no laptop task exists: nothing to update there. Server: `uni-vm jobs sync` (it prints the `job.conf` diff and regenerates the timer) |
| a course (added, renamed, new official subfolder) | render creates the new folder, card, backlog, notes and official folders (old folders stay) and refreshes the generated tables; add the course's rows to the hand-kept pages as `_agent/skills/course-facts/references/course-onboarding.md` says (section 5, "Adding a course mid-term", step 3: "Add by hand what is not generated"); copy the skills again; re-run the Obsidian settings merge; re-run the course-files-fetch installer if you use it |
| `schedule.vault_watch` or `vault_watch.task_name`, `install_dir`, `at_logon`, `logon_delay_min` | re-run `register-task.ps1` (other `vault_watch.*` keys are read on the next run) |
| any `course_fetch.*` key, course URLs or official folders | re-run `install-course-pickup.ps1` (its policy is baked into the install folder on purpose) |
| colours, course names, cockpit keys | nothing: the cockpit reloads `uni-os.json` by itself; re-run the Obsidian merge for new graph groups |
| a skill's source (after a framework update) | copy `_agent/skills/` to your agent's skills folder again |

## Example conversations

### "Add the VM"

> **You:** Add the always-on server.
>
> **Agent:** Before I do: a cloud VM costs money and needs some maintenance (the original ran a 4 GB Google Cloud machine at roughly $21 a month; a spare computer at home costs only electricity). In return, jobs run on time while your laptop sleeps, role sessions stay alive and you can open sessions in the vault from your phone. A few questions: cloud or home server? budget and currency? which jobs should move to it, and which roles should run there? [defaults ...]
>
> **You:** Google Cloud, 15 EUR, move daily prep and the check-in, keep everything else on the laptop for now.

What the agent then does:
1. Sets `runtime.use_vm = true` and the `[vm]` answers in the config, validates.
2. `uni-os enable vm --dry-run`, shows the new files (`_agent/vm.md`, `_agent/vm/`, the jobs `vm-health`, `vault-history`, `vm-performance-verdict`), then `uni-os enable vm`.
3. Walks through [modules/vm/INSTALL.md](../modules/vm/INSTALL.md) with you. The cloud console, the drive consent and the agent login on the server are yours.
4. Moves each chosen job: `uni-vm jobs run daily-study-prep --dry-run` on the server and reads the log; then, away from the job's slot times, pauses the laptop task and right after that `uni-vm jobs on daily-study-prep`. One job at a time, never on both machines.
5. Updates the "Scheduled jobs" table in `_agent/coordinator-state.md` and adds a line to the handbook's change log.

### "Turn off daily prep"

> **You:** Turn off the daily prep, I don't use it.
>
> **Agent:** You started from Minimal and added daily prep later, so planning and progress are only its dependencies: `uni-os disable daily-prep --dry-run` says it would disable them too. Do you want to keep planning (week plans, calendar blocks) and progress (week pages, dashboard)?
>
> **You:** Keep both.

What the agent then does:
1. Adds `planning` and `progress` to `modules.enabled`, then `uni-os disable daily-prep`.
2. Deletes or pauses the desktop tasks of `daily-study-prep` and `study-prep-morning-check` (or `uni-vm jobs off daily-study-prep` and `uni-vm jobs off study-prep-morning-check` on the server).
3. Tells you what stays: old prep notes as history, the MATERIAL text in past calendar events, the job folders with their `DISABLED` marker. With the cockpit: the prep card, its presence line and the prep warnings disappear by themselves once `_agent/uni-os.json` no longer lists `daily-prep`; nothing to switch off.

### "Move my check-in to Sunday evening"

> **You:** Move my check-in to Sunday evening.
>
> **Agent:** What time on Sunday? [18:00] A Sunday check-in covers the current week, as before.
>
> **You:** 18:30.

What the agent then does:
1. Checks that `check-in` shows as `enabled` or `dep` in `uni-os modules`. In a Minimal vault it does not: the agent says the setting alone would change nothing and offers `uni-os enable check-in` first.
2. Sets `check_in = { day = "Sun", time = "18:30", every = "week" }` under `[schedule]`, validates.
3. `uni-os render --dry-run` shows `_agent/jobs/check-in/job.conf` updated (and the jobs table in the handbook's generated region); then `uni-os render`.
4. Updates the check-in task: the desktop app task's schedule, or `uni-vm jobs sync` on the server, then `uni-vm jobs next` to confirm the new time.
5. Checks that the week-page job still runs before or after it in the order you want (`schedule.week_page`).

### Other common requests

| Request | Commands | Watch out for |
|---|---|---|
| "Switch on the heartbeat" | `uni-os enable heartbeat` if it is not enabled yet (it is part of Standard); its jobs follow the release pattern: dry runs at two representative times, review, then the task or `uni-vm jobs on heartbeat` | only one machine runs the heartbeat |
| "I stopped using Obsidian" | set `obsidian.enabled = false`; `uni-os disable cockpit obsidian`; `render` | files you edited (for example `Home.md`) keep their Obsidian embeds; the agent can rewrite them as plain Markdown |
| "Add quiz coaching" | `uni-os enable quiz-coaching` | it brings `error-logs`, `study-pages` and `student-model` if missing; the `quiz-prep` job runs only on dates in `schedule.quiz_prep_dates` |
| "Start over with a preset" | `python tools/uni_os.py modules --preset full --vault "<vault>"` to compare, then set `modules.enabled` to the new list and `render` | removing modules disables them (files kept); new modules arrive with their jobs switched off |

## What the agent checks after every change

1. **The command ended with exit 0**, and its output has no `CONFLICT` line, no `template errors` and no `config errors`.
2. **Nothing was skipped unexpectedly.** Every `skipped ... generated regions cannot be refreshed` line is either fixed (markers restored, render again) or explained to you.
3. **`python tools/uni_os.py doctor --vault "<vault>"` reports 0 errors**; new warnings are explained.
4. **`python tools/uni_os.py modules --vault "<vault>"` shows the statuses you expect** (`enabled`, `dep`, `disabled`, `available`): no module disabled by accident through the dependency rule.
5. **Jobs and tasks agree.** `python tools/uni_os.py jobs --vault "<vault>" --all` against the desktop app's task list, Task Scheduler or `uni-vm jobs`: every switched-on job has exactly one task on exactly one machine, no task runs a job with a `DISABLED` marker, and a changed schedule shows its new time.
6. **Skills are current** in the agent's skills folder if any file under `_agent/skills/` changed.
7. **No secret entered the config** (doctor's secrets scan) and nothing personal entered a push text.
8. **The records are updated:** the "Scheduled jobs" table in `_agent/coordinator-state.md` (with `roles`), section 5 of `_agent/system-handbook.md` for anything added outside the modules, and one line in its change log (section 8), with your words if it was your decision.
9. **You are told** what changed, what stayed, and anything left for you (a sign-in, an app setting, a task only you can register).
