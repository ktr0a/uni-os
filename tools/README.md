# uni-os tools

The `uni-os` command line scaffolds a vault from a config file and the module templates, keeps it in sync when the config or the modules change, and checks its health. It is pure Python standard library (3.11+, uses `tomllib`) and runs on Windows, macOS and Linux (tested on Windows 11 with Python 3.11 and 3.14).

```text
python tools/uni_os.py --help            # works from any folder
python tools/uni_os.py <command> --help
```

You rarely need it by hand: the setup agent runs it for you (`setup/PLAYBOOK.md`). This page is the reference for module builders and anyone curious how the scaffolding works.

## Commands

| Command | What it does |
|---|---|
| `init --config FILE --vault DIR [--modules a,b] [--preset P] [--force] [--dry-run] [--date D]` | Create (or complete) a vault. Renders every enabled module and creates its folders, never overwrites an existing file (lists what it skipped), copies the config to `<vault>/_agent/uni-os.toml`, writes `_agent/uni-os.json` and the manifest. Run it again to restore files and folders you deleted. `--modules`/`--preset` override `modules.enabled` (dependencies are added). A preset is resolved for the laptop's system (`runtime.laptop_os`, else this computer's): modules that do not support it are left out with a note saying which and why; an explicit `--modules` list is installed as given, with a warning per such module. Lists the skills it wrote: copy them to `agent.skills_dir`. |
| `render [--force] [--dry-run]` | Apply config or module changes: updates files you never edited, refreshes the generated regions of files you edited (everything outside the markers is kept), creates new files and folders (a new course, a newly enabled module), never recreates deleted ones, marks modules removed from the config as disabled. `--dry-run` lists every change, including which regions. When a skill changed it says so: copy the skills to `agent.skills_dir` again (they are copies, not links). |
| `enable ID...` / `disable ID...` | Edit `modules.enabled` in the vault's config (comments kept) and render (generated regions included). `disable` never deletes files or folders: the module's jobs get a `DISABLED` marker and generated maps stop listing it. A module that others need cannot be disabled alone. Disabling the last listed module writes `enabled = ["core"]`, never an empty list (empty means "use `uni_os.preset`" and would bring the preset back). |
| `modules [--preset P [--os windows\|macos\|linux\|any]] [--json]` | The catalogue with status (`enabled`, `dep`, `disabled`, `available`), or the resolved module list of a preset for a laptop system (default `runtime.laptop_os`, else this computer's; `any` keeps every module), with what was left out and why. |
| `doctor [--strict] [--json] [-v] [--no-secrets]` | Config validation, module problems (including enabled modules whose laptop part does not support `runtime.laptop_os`: a warning, never a block), missing/edited installed files and folders, stale `uni-os.json`, skill copies in a vault-relative `agent.skills_dir` that differ from `_agent/skills/` (a warning with the copy command; a skill without a copy is only an info line), job.conf checks, parsed-format contracts (week pages, course cards, the `course` property is a course id, generated-region markers of edited files), and a secrets scan of the vault (redacted output). Exit 1 on errors. |
| `week [--date D] [--number\|--json]` | The term week (week 0 = `term.week0_monday`, week n starts week0 + 7n) and phase (lectures, holiday, lecture-free, exam session). |
| `new-week [--date D] [--current\|--week N] [--status S] [--close-previous] [--dry-run]` | Create `progress/weeks/week-NN.md` from `_templates/week-page.md` (default: next week). Never overwrites. |
| `config get KEY` / `show` / `keys` / `validate` / `path` | Read the resolved config. `get courses.algo.folder` looks list items up by id. `keys` shows where each value comes from. `validate` also notes (level info, so `--strict` passes) a value you changed that only modules which are not enabled read ("`schedule.vault_watch`: is set, but its module vault-watch is not enabled"; values equal to the module default are left alone; `disable` keeps such settings on purpose), and warns about the computed `term.weeks` set by hand. |
| `jobs [--all] [--json]` | Installed jobs with slots (or the `EVERY_MIN` polling interval, or a raw `SCHEDULE`), days, runtime and default mode (for setting up schedulers). |
| `push`, `heartbeat` | Push gate and proactive watcher (owned by the notifications/heartbeat modules). |

### Which vault and config

- `--vault DIR` (or `$UNI_OS_VAULT`), else the vault you are standing in (the tools walk up looking for `_agent/uni-os.toml`).
- `--config FILE`, else `<vault>/_agent/uni-os.toml`. A config inside a vault (`<vault>/_agent/uni-os.toml`) also identifies the vault.
- `paths.vault` in a config file is **never** used as a write target. `init` always needs an explicit `--vault`.
- Modules come from `<repo>/modules` (override with `--modules-dir` or `$UNI_OS_MODULES_DIR`, used by the tests).

## How installing works

| Module source | Vault target |
|---|---|
| `modules/<id>/vault/<path>` | `<vault>/<path>` |
| `modules/<id>/jobs/<job>/<file>` | `<vault>/_agent/jobs/<job>/<file>` |
| `modules/<id>/roles/<role>.md` | `<vault>/_agent/roles/<role>.md` |
| `modules/<id>/skills/<skill>/<file>` | `<vault>/_agent/skills/<skill>/<file>` |

- **Templates.** Every text file is a template unless it matches the module's `verbatim` globs. Binary files are copied as they are. Template output always uses `\n` line endings (except `.bat .cmd .vbs .ps1 .psm1 .psd1`, which keep the CRLF that the repository's `.gitattributes` gives them in every checkout), so the same config produces byte-identical files on every OS.
- **Path expansion.** A path containing `{{course.` is produced once per course (`vault/{{course.folder}}/{{course.slug}}.md` gives `AD/ad.md`, `DM/dm.md` ...). A path containing `{{error_log.` is produced once per course *and* error-log stream (`vault/{{course.folder}}/{{error_log.file}}` gives `PROG/prog-error-log-theory.md` and `PROG/prog-error-log-programming.md`); inside, `error_log` has `stream`, `file`, `path`, `title`.
- **Folders.** A `.gitkeep` or `.keep` file only creates its folder; it is not copied. A module can also declare folders in its `module.toml` (see "Module folders" below), for folders whose names come from the config, such as one folder per official subfolder of each course. Folders are created only while their module is enabled, listed in the `init`/`render` output (also with `--dry-run`), recorded in the manifest under `dirs`, and never deleted. Like files, a folder you deleted is not recreated by `render` (`init` restores it).
- **Agent dir and inbox.** A leading `_agent/` or `inbox/` in a vault path follows `paths.agent_dir` / `paths.inbox`.
- **All or nothing.** Everything is rendered in memory first. If any template fails, nothing is written and every error is listed with file, line and key.
- **Write failures.** A file or folder that cannot be written (no permission, a file where a folder belongs, a full disk) does not stop the run: it is listed as `CONFLICT <path>: could not be written: <reason>`, left out of the manifest, and the command exits 1, while everything else is written and the manifest and `uni-os.json` are saved for it. The same holds for the files written after the module files: a job's `DISABLED` marker, the config copy, `uni-os.json` and the manifest itself. Fix the cause and run the command again. Any other file-system error (the vault folder itself cannot be created, say) ends the command with one `uni-os: error:` line, no traceback.
- **One owner per file.** Two modules producing the same vault path is an error.
- **Manifest.** `<vault>/_agent/.uni-os-manifest.json` records every written file with its module, source template and SHA-256 (no absolute paths, no personal data), and every created folder. A file whose hash still matches is "untouched" and `render` may update it; anything else is yours, apart from its generated regions.
- **Generated regions.** A template can mark generated parts with two marker lines, `<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->` (each alone on its line; `NAME` is lowercase letters, digits and `-`, unique in the file; no nesting). When a file was edited, `render` (and `enable`/`disable`) compares it with its fresh rendering: if both contain exactly the same set of well-formed regions, only the text between each pair of markers is replaced and every other byte is kept (a CRLF file keeps CRLF). If a marker is missing, renamed, duplicated, nested or malformed, the file is left alone and listed as skipped with the reason; nothing is guessed. `--force` still replaces whole files. Core uses regions for the vault map, the lookup table, the routing table in `CONVENTIONS.md`, and the setup summary and registry in `system-handbook.md`; the roles module for the tables in `_agent/roles/README.md`; the planning module for the term-week table, the weekly grid, the release rhythm and the graded items in `semester/calendar-and-dates.md`. Code: [`uni_os/regions.py`](uni_os/regions.py).
- **Bookkeeping of a region merge.** The manifest's `sha256` stays the hash of the last *full* rendering, so the file keeps counting as edited (`doctor -v` lists it) and the next render merges again instead of overwriting your text. The entry gains `merged_sha256`, the hash right after the merge, so `doctor -v` can say "edited outside its generated regions; render refreshed the regions". If a merge makes the file equal to a full rendering (you had only touched the regions), it is recorded like a normal write and counts as untouched again. `doctor` warns when an edited file's markers are broken.

## Template language

The full reference is the docstring of [`uni_os/template.py`](uni_os/template.py); a summary is in [docs/file-formats.md](../docs/file-formats.md#template-language).

```text
{{student.name}}                       value; lists render "a, b"; dates ISO; booleans true/false
{{courses.algo.name}} {{courses.0.id}} list items by id or index
{{#each courses}}{{course.short}}{{#unless @last}}, {{/unless}}{{/each}}
{{#each course.assessments}}{{item.name}}{{else}}none{{/each}}
{{#if modules.daily-prep}} ... {{else}} ... {{/if}}
{{#unless obsidian.enabled}} ... {{/unless}}
{{#if agent.primary == "claude-code"}} ... {{/if}}      also != and contains
{{#if study.formats contains "html"}} ... {{/if}}
\{{course.name}}                        literal text "{{course.name}}" (for docs)
```

- Known roots: `student university term paths storage obsidian agent study courses course schedule notify calendar runtime vm cockpit modules uni_os generated`, plus the loop roots `item` and `error_log`. Anything else is left untouched: `{{date}}`, `{{date:YYYY-MM-DD}}`, `{{title}}` (Obsidian) and `{{week.*}}` (filled later by `new-week`).
- A missing key under a known root is an error, also inside `{{#if}}` (only `modules.<id>` is never an error). Put every key your module needs into its `module.toml` `[defaults]`.
- A block tag alone on its line removes the whole line, so loops build Markdown tables cleanly.
- Truthiness: `false`, `""`, `0`, `[]`, `{}` and `"none"` are false.
- Always available: `generated.date` (ISO, `2026-11-07`), `generated.date_long` (the same day as the vault writes dates in text, `Sat 7 Nov 2026`; English day and month names on every system), `generated.version`, and the lists `generated.modules`, `generated.roles`, `generated.jobs`, `generated.skills` (what is enabled/installed, for registries and routing tables). `term.weeks` is derived too: one `{number, nn, start, start_iso}` per teaching week (`0`, `"00"`, `"Mon 14 Sep 2026"`, `"2026-09-14"`) from `term.week0_monday` through the week of `term.last_lecture_day` (weeks 0 to 13 when that is empty), for loops like `{{#each term.weeks}}| {{item.number}} | {{item.start}} |{{/each}}`. Each course also carries derived fields: `colour_rgb`, `colour_int`, `colour_light` (computed if empty), `colour_light_rgb`, `colour_light_int`, `card`, `error_logs`, `error_log_files`, `handwritten_dir` (`handwritten_folder`, or `<folder> handwritten`). Details: [`../config/schema.md`](../config/schema.md).

## Extending

**A new command.** Add `uni_os/commands/<name>.py` with `register(subparsers)`; it is discovered automatically:

```python
from uni_os.cli import common_options
from uni_os.context import session_from_args

def register(subparsers):
    p = subparsers.add_parser("hello", parents=[common_options()], help="say hello")
    p.set_defaults(func=run)

def run(args):
    session = session_from_args(args)          # vault, config, catalogue, resolved config
    print("Hello", session.cfg["student"]["name"])
    return 0                                   # exit code; raise UniOsError for user errors
```

**Module folders.** Folders whose names come from the config are declared in `module.toml`. They are created empty: never put placeholder files into folders that belong to the university or to another app.

```toml
[[folders]]
path = "{{course.folder}}/{{item}}"       # a template; {{course.*}} makes it one folder per course
each = "course.official_subfolders"       # optional: one folder per item of this list, bound as {{item}}

[[folders]]
path = "{{course.folder}}/{{course.handwritten_dir}}"
```

`path` may use every template key; `{{course.*}}` and `{{error_log.*}}` expand per course / per error-log stream, also when only `each` names them. `each` names a list key; `{{item}}` (plus `{{@index}}`, `{{@first}}`, `{{@last}}`) is bound per item, and empty items are skipped. A leading `_agent/` or `inbox/` follows `paths.agent_dir` / `paths.inbox`. The result must be a safe vault-relative path. Two modules may ask for the same folder.

**A doctor contract check.** Declarative, in a module's `module.toml` (runs when the module is enabled):

```toml
[[contracts]]
name = "tracker log keeps its heading"
files = ["progress/tracker-log.md"]          # vault-relative globs, ** allowed
headings = ["## Entries"]                    # each must start some heading line
frontmatter = { type = "log" }               # value "" = the key must exist
level = "warning"                            # or "error"
```

Or in Python with the registry in [`uni_os/doctor.py`](uni_os/doctor.py): decorate a function with `@contract("name", modules=("progress",))` and yield `Finding`s.

**Library helpers** other code may import (stable):

| Helper | Returns |
|---|---|
| `uni_os.config.load(vault)` | the resolved config dict of a vault |
| `uni_os.semester.week_of(date, cfg)` / `week_info(n, cfg)` / `today(cfg)` | term week number / week dict / today in the term time zone |
| `uni_os.jobs.parse_conf(path)` | job.conf as a dict (bash quoting rules, `export` handled) |
| `uni_os.jobs.list_jobs(vault)` | installed jobs (skips `DISABLED` ones unless asked) |
| `uni_os.jobs.expand_days(text)` | `"Mon..Wed,Fri"` -> `["Mon", "Tue", "Wed", "Fri"]` (empty = every day, as the host runners read `DAYS`) |
| `uni_os.template.render(text, context)` / `lookup(path, context)` | rendered text / the value of a key path |
| `uni_os.regions.parse(text)` / `merge(current, fresh)` | the generated regions of a text / the region merge `render` uses |
| `uni_os.secrets.scan_text(text)` | secret findings (redacted) |

## Tests

```text
python -m unittest discover -s tests -v
```

The tools tests use a tiny fixture module set (`tests/fixtures/modules`) and temporary folders; they never read any real vault. One file, `tests/test_repo.py`, checks the real catalogue (read-only, output only in temporary folders):

- every key a module defaults in its `[defaults]` appears in `config/uni-os.example.toml` and `examples/alex.toml` and has a row in `config/schema.md`;
- the example config and Alex's config hold the same keys and values (apart from the preset and the module list) and validate with no errors or warnings; the only module keys they leave out are the four old stuck-note aliases (`config.STUCK_ALIASES`), which stay documented in the schema;
- rendering **every** module with `examples/alex.toml` works, leaves no install-time placeholder behind, and `uni-os doctor --strict` passes.

So when a module gets a new config key: put it in the module's `[defaults]` and README, then add it to the three shared files (the schema row names the module first in "Used by"). Module tests live next to their modules (`modules/<id>/tests/`).

## Windows notes

- Quote every path: vault folders like `G:/My Drive/Uni & Co (A&D)` work in Git Bash and PowerShell as long as they are in quotes (`--vault "G:/My Drive/Uni"`). Course folders may contain spaces and `&` too; rendered `job.conf` files stay valid for bash `source`.
- Output is UTF-8 on the console and in pipes (the tools reconfigure stdout), and every rendered file uses `\n` line endings except `.bat .cmd .vbs .ps1 .psm1 .psd1` (CRLF from the checkout, see `.gitattributes`).
- Python on Windows ships no time-zone database. Then "today" uses the computer's own clock zone (fine on a laptop in the term's zone), and `doctor` / `config validate` print an INFO line; `python -m pip install tzdata` makes `term.timezone` exact. Linux has the database built in.
- Tested with Python 3.11 and 3.14 on Windows 11.

## job.conf keys

`uni_os.jobs` knows every key in [docs/file-formats.md](../docs/file-formats.md#jobconf), including `EVERY_MIN` (a fixed polling interval in minutes, 1-59 or whole hours up to 1440; the always-on host uses it when a job has no `SLOTS`/`SCHEDULE`, the laptop scheduler adds a repeating trigger for it). `DAYS` is a comma list of days; empty means every day. Ranges may be written `Mon..Fri` or `Mon-Fri` (and may wrap, `Sat..Mon`): both host runners accept both forms, and `doctor` only reports unknown day names. Any other key is reported by `doctor` as unknown unless it is passed with `export KEY=...`. The schedule keys are also listed in [`../config/schema.md`](../config/schema.md).

## Environment variables

| Variable | Meaning |
|---|---|
| `UNI_OS_VAULT` | Default vault. |
| `UNI_OS_MODULES_DIR` | Alternative module catalogue. |
| `UNI_OS_TODAY` | Pretend today is `YYYY-MM-DD` (tests, reproducible runs). |
| `SOURCE_DATE_EPOCH` | Reproducible-build timestamp for `generated.date`. |
