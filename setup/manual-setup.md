# Setting up without an agent

> **Warning: this is very tedious, and you get only part of the system.** Uni OS is primarily an agent-based system. The setup agent normally interviews you, reads your course pages, writes a config of several hundred lines, runs the scripts, and walks you through the follow-up steps. After setup, agents do the daily work: they write the study pages, give the hints, keep the week pages and dashboards current, plan your calendar and run the scheduled jobs. Without an agent you do all of that by hand, and most scheduled jobs cannot run at all, because they are agent prompts. Use this page to look at the scaffold, to build a test vault, or if your agent cannot run commands. If you have an agent, say "set me up" instead ([PLAYBOOK.md](PLAYBOOK.md)).

Everything below is exact; nothing needs an agent until the "What you lose" section says so.

## What you need

- the framework clone (`git clone https://github.com/ktr0a/uni-os.git` once it is published, or a copy of the folder);
- Python 3.11 or newer (standard library only; `python --version`, on macOS and Linux possibly `python3`);
- a folder for the vault, **outside** the clone (the tools refuse a vault that contains the clone or lies inside its `modules/` or `tools/`), usually inside your synced drive, e.g. `G:/My Drive/Uni`;
- optionally Obsidian 1.9 or newer.

All commands run from the framework folder. Quote every path: folders may contain spaces and `&`.

## Step 1: Write the config

Create the vault folder and its agent folder, and put your config at its final place, `<vault>/_agent/uni-os.toml`. Two starting points:

- **Everything, commented:** copy [config/uni-os.example.toml](../config/uni-os.example.toml). It contains every key of every module, filled in for the fictional student Alex Example. Replace the values; delete the lines of modules you won't use (or leave them: keys of disabled modules are ignored).
- **The minimum:** the five required keys, one table per course, and a preset. This is a complete, valid config:

```toml
[uni_os]
version = "0.1.0"
preset = "minimal"            # "minimal" | "standard" | "full"; used because modules.enabled is empty

[student]
name = "Alex Example"
handle = "alex"

[university]
name = "Example Institute of Technology"
short = "EIT"
programme = "BSc Computer Science"

[term]
label = "Autumn 2026"
timezone = "Europe/Zurich"     # IANA time zone
week0_monday = 2026-09-14      # must be a Monday

[obsidian]
enabled = false                # true if you use Obsidian

[[courses]]
id = "algo"                    # stable lowercase id
name = "Algorithms and Data Structures"
short = "AD"
folder = "AD"                  # spaces and & are fine
slug = "ad"                    # file prefix
colour = "#1e66f5"

[modules]
enabled = []                   # empty = the preset above
```

Then add what you want, using these references:
- [interview.md](interview.md): every question the agent would ask, with the key it fills and its default. Work through it batch by batch.
- [config/schema.md](../config/schema.md): every key with type, default and the modules that use it.
- [presets.md](presets.md): which modules each preset contains. To pick modules yourself, list them in `modules.enabled` (requirements are added automatically).
- [examples/alex.toml](../examples/alex.toml): a complete config with four courses, graded work and bonus schemes.

Format rules: times are quoted (`"07:30"`; a bare `07:30` is not valid TOML), dates are bare (`2026-09-14`), days are `"Mon"` ... `"Sun"`, colours `"#1e66f5"`. **No secrets in the config** (no API keys, tokens, private calendar addresses or the ntfy topic); it may hold only the path of a secret file outside the vault, such as `notify.ntfy_topic_file`.

Keep the config out of the clone. If you must keep a copy there, use `config/uni-os.toml` or a `*.local.toml` name, which `.gitignore` excludes.

## Step 2: Validate

```bash
python tools/uni_os.py config validate --vault "<vault>"
```

Its last line must say `0 error(s)` (warnings are allowed but worth reading). Errors name the key and the problem; an "unknown key" warning is usually a typo and suggests the right name. To see every effective value with its source (your file, a module default, derived):

```bash
python tools/uni_os.py config keys --vault "<vault>"
python tools/uni_os.py config keys --vault "<vault>" --prefix schedule
```

To see which modules you will get:

```bash
python tools/uni_os.py modules --preset standard
python tools/uni_os.py modules --preset standard --no-obsidian
```

## Step 3: Dry run, then create the vault

```bash
python tools/uni_os.py init --vault "<vault>" --dry-run
python tools/uni_os.py init --vault "<vault>"
```

The dry run lists every file and folder that would be created and every existing file that would be skipped (init never overwrites a file). The real run creates the files, one empty folder per official subfolder of each course (plus one handwritten folder per course with `handwritten-notes`), `_agent/uni-os.json` (a machine copy of the config) and `_agent/.uni-os-manifest.json` (what was written, with hashes). If you kept the config elsewhere, add `--config "<file>"`: init copies it to `<vault>/_agent/uni-os.toml`, which is the only copy that counts from then on.

## Step 4: Check it

```bash
python tools/uni_os.py doctor --vault "<vault>"
python tools/uni_os.py jobs --vault "<vault>"
```

Doctor must report 0 errors. `jobs` lists the scheduled jobs the modules installed (with Minimal: none).

## Step 5: Install the pieces by hand

Do only what applies to your modules. Each module's README has the full detail.

| Piece | Module | By hand |
|---|---|---|
| Skills | courses, error-logs, study-pages, handwritten-notes | copy `<vault>/_agent/skills/*` to the folder your tool reads skills from (if any); otherwise read the `SKILL.md` files yourself |
| Term-week table | planning | nothing to fill: `render` generates the table in `semester/calendar-and-dates.md` from `term.week0_monday` and `term.last_lecture_day`; check it once. `python tools/uni_os.py week --vault "<vault>" --date <YYYY-MM-DD>` gives the week of any date |
| Obsidian settings | obsidian | open the vault in Obsidian once, close it, then `python modules/obsidian/scripts/merge_obsidian_config.py --vault "<vault>"` (dry run) and the same with `--apply`; reopen Obsidian |
| Cockpit plugin | cockpit | Obsidian: Settings > Community plugins > Restricted mode off > enable "Uni OS cockpit" |
| Phone pushes | notifications | install the ntfy app, create the secret topic file outside the vault and test: [modules/notifications/README.md](../modules/notifications/README.md), "Set up ntfy" |
| Week pages | progress | `python tools/uni_os.py new-week --vault "<vault>" --current` now, then `python tools/uni_os.py new-week --vault "<vault>" --close-previous` at the end of every week (it creates next week's page and closes the old one; it never overwrites) |
| Vault watcher | vault-watch (Windows) | `powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\modules\vault-watch\scripts\register-task.ps1" -Vault "<vault>"` |
| Course-file pick-up | course-files-fetch (Windows) | `powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\modules\course-files-fetch\scripts\install-course-pickup.ps1" -Vault "<vault>"`; you download the files yourself and file them with `request_pickup.py` |
| Always-on server | vm | [modules/vm/INSTALL.md](../modules/vm/INSTALL.md); its health check, notes history and outcome checks are plain commands, its other jobs need an agent CLI on the server |

## Step 6: Maintain it by hand

- **Change a setting:** edit `<vault>/_agent/uni-os.toml`, then `python tools/uni_os.py render --vault "<vault>" --dry-run` and `render`. Files you never edited are updated; in files you edited only the generated regions between `<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->` are refreshed.
- **Add or remove a module:** `python tools/uni_os.py enable <id> --vault "<vault>"` or `disable <id>` ([changing-modules.md](changing-modules.md)).
- **Restore a deleted file:** `python tools/uni_os.py init --vault "<vault>"`.
- **Check health:** `python tools/uni_os.py doctor --vault "<vault>"`.

## What you lose without an agent

| Part of Uni OS | With an agent | Without |
|---|---|---|
| Setup | an interview, course pages read for you, the config written and checked | you write the TOML yourself |
| Course cards | filled from the course pages, corrected as facts change, the session rule inferred and checked | you keep them current |
| Study pages, rundowns, skims, recaps | built from the real sources with cited pages | only the template (`_templates/study-page.html`) and the converters (`html2md.py`, `html2pdf.py`, `check_study_page.py`) |
| Exercise help, quiz coaching | hints by your policy, prep sheets, reviews | not available: the roles are agent briefs |
| Error logs, weak spots | logged the moment a mistake shows up, patterns updated | you write the rows |
| Week pages | filled with the week's real items, closed at the check-in | `uni-os new-week` makes the skeleton; you fill it |
| Planning, daily prep, check-in, heartbeat | scheduled agent jobs | do not run (they are agent prompts) |
| The write-back rule ("every new fact into the right file, same turn") | every session follows the routing table | you are the only writer |
| Dashboards (Bases views, Home, cockpit) | always current, because agents keep the notes in format | work only as long as you keep the notes in the documented formats ([docs/file-formats.md](../docs/file-formats.md)) |

What still works without any agent: the vault layout and templates, the generated maps, `uni-os` itself (`init`, `render`, `doctor`, `week`, `new-week`, `config`, `jobs`), the push gate (`uni-os push`) and the deterministic outcome checks, the Obsidian views and the cockpit, the Windows watcher and the pick-up task, and the server's health check and notes history.

A plain chat assistant without file access can still follow the rules if you paste `AGENTS.md` and `_agent/rules.md` into it, but it cannot write anything back. Agents that can create files but not edit them (some cloud sessions) write update notes instead (module `inbox-sync`).
