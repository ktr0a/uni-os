# File formats

Uni OS is held together by plain files with fixed shapes. Scripts, the `uni-os` command, the cockpit plugin, the heartbeat and the job runners parse them, and agents write them. This page is the reference for every parsed contract: its exact syntax, an example, and who reads it. When this page and a module README differ, the module README and the code win; please report the difference.

| Format | File(s) | Read by | Section |
|---|---|---|---|
| Config | `<vault>/_agent/uni-os.toml` | everything | [Config](#config-uni-ostoml) |
| Generated config copy | `<vault>/_agent/uni-os.json` | cockpit, Windows scripts, job runners | [uni-os.json](#uni-osjson) |
| Module manifest | `modules/<id>/module.toml` | `uni-os` | [module.toml](#moduletoml) |
| Templates | every text file under `modules/<id>/vault/`, `jobs/`, `roles/`, `skills/` | `uni-os init` / `render` | [Template language](#template-language) |
| Generated regions | marker lines in installed files | `uni-os render`, `doctor` | [Generated regions](#generated-regions) |
| Job definition | `<vault>/_agent/jobs/<job>/job.conf` + `prompt.md` | laptop scheduler, host runner, `uni-os jobs`, `doctor` | [job.conf](#jobconf) |
| Role brief | `<vault>/_agent/roles/<role>.md` | role sessions, the routing table | [Role brief](#role-brief) |
| Skill | `<vault>/_agent/skills/<skill>/SKILL.md` | agents | [SKILL.md](#skillmd) |
| Note properties and names | every note | views, cockpit, `doctor` | [Notes](#note-properties-and-file-names) |
| Week page | `progress/weeks/week-NN.md` | cockpit, heartbeat, check-in job, `doctor` | [Week page](#week-page) |
| Prep note | `semester/prep/prep-YYYY-MM-DD[-rN].md` | cockpit, heartbeat, outcome checks, morning check | [Prep note](#prep-note) |
| Course card | `<course folder>/<slug>.md` | cockpit, agents, `doctor` | [Course card](#course-card) |
| Error log | `<course folder>/<slug>-error-log[-<stream>].md` | agents, `error_log.py` | [Error-log row](#error-log-row) |
| Update note | `inbox/YYYY-MM-DD_HHMM_<sender>-update.md` | the `inbox-sync` job, `inbox_poll.py` | [Update notes](#update-notes-and-the-inbox) |
| Failure flag | `_agent/logs/flags/<job>.md` | heartbeat pre-check, waiting-on-you | [Failure flags](#failure-flags) |
| Heartbeat output | `_agent/heartbeat/flags.json`, `state.json`, logs | dashboards, the heartbeat | [Heartbeat files](#heartbeat-files) |
| Push gate state | outside the vault: `push-gate/state.json` | `uni-os push` | [Push gate state](#push-gate-state) |
| Run logs | outside the vault: `jobs.log`, per-run logs | heartbeat, outcome checks, people | [Run logs](#run-logs) |
| Failover marker | `_agent/vm/ran/<task>.md` | laptop job runs | [Failover marker](#failover-marker) |
| Install manifest | `_agent/.uni-os-manifest.json` | `uni-os render`, `doctor` | [Manifest](#the-install-manifest) |
| Smaller contracts | course-fetch queue, waiting-on-you page, vault-watch logs, experiment files | their modules | [Other contracts](#other-contracts) |

General rules for every file Uni OS writes or parses: UTF-8 without BOM; rendered templates use `\n` line endings (except `.bat .cmd .vbs .ps1`); local time in `term.timezone` everywhere (file names, log lines, times inside notes); dates written for people as `Ddd D Mon YYYY` (`Thu 12 Nov 2026`), dates for machines as ISO `YYYY-MM-DD`.

## Config (`uni-os.toml`)

The single source of truth for every parameter, kept in the vault at `<vault>/_agent/uni-os.toml` (setup copies it there). Every key, its type, default and the modules that use it are documented in [`../config/schema.md`](../config/schema.md); a commented example is [`../config/uni-os.example.toml`](../config/uni-os.example.toml), a complete fictional config [`../examples/alex.toml`](../examples/alex.toml).

The essentials:
- **Layering**, lowest priority first: built-in defaults, the `[defaults]` of modules that are not enabled, the `[defaults]` of enabled modules, your file. Tables merge key by key; lists and values replace. `python tools/uni_os.py config keys` shows every key with its value and source (`base`, `module:<id>`, `user`, `derived`).
- **Per-course defaults:** a module's `[defaults.course]` is applied to every `[[courses]]` entry that lacks those keys.
- **Formats:** dates `2026-09-14`; times quoted 24-hour `"07:30"` (bare `07:30` is not valid TOML 1.0); ranges `"21:00-07:30"`; days `"Mon"` ... `"Sun"`; colours `"#1e66f5"`.
- **No secrets.** Only paths to secret files outside the vault ([`security-and-privacy.md`](security-and-privacy.md)).
- **Derived course fields** the tools add (never set them): `colour_rgb`, `colour_int`, `colour_light` (computed if empty), `colour_light_rgb`, `colour_light_int`, `card` (`"AD/ad.md"`), `error_logs` (`[{stream, file, path, title}]`), `error_log_files`, `handwritten_dir` (`handwritten_folder`, or `<folder> handwritten` when that is empty).
- **Validation:** `python tools/uni_os.py config validate` or `doctor`: required keys, types, enums, dates, times, unique course ids, slugs and folders (case-insensitive), folder names, colours, module ids, unknown keys with a "did you mean".
- **Editing:** `uni-os enable` / `disable` edit `modules.enabled` with comments kept. After any change, `python tools/uni_os.py render`.

## `uni-os.json`

`<vault>/_agent/uni-os.json` is the resolved config (all defaults merged, derived fields added) as JSON, for consumers that cannot read TOML: the cockpit plugin, the Windows scripts, the job runners. `uni-os init` and `render` rewrite it; never edit it.

```json
{
  "_generated": "do not edit; edit uni-os.toml",
  "_framework_version": "0.1.0",
  "uni_os": { "version": "0.1.0", "preset": "custom" },
  "student": { "name": "Alex Example", "handle": "alex", "language": "English", "dictates": false, "pronouns": "" },
  "courses": [ { "id": "algo", "short": "AD", "folder": "AD", "slug": "ad", "card": "AD/ad.md", "handwritten_dir": "AD handwritten", "...": "..." } ],
  "...": "one key per config table: university, term, paths, storage, obsidian, agent, study, schedule, notify, calendar, runtime, vm, cockpit, modules, and module tables such as heartbeat, course_fetch, vault_watch"
}
```

`doctor` compares the file with a fresh export of the resolved config and warns when it is missing or out of date ("run `uni-os render`").

## `module.toml`

Every module folder `modules/<id>/` has a `module.toml`. Folders without one are ignored by discovery. The example below is a composite that shows every kind of entry at once; real modules use only what they need (see [`../modules/daily-prep/module.toml`](../modules/daily-prep/module.toml) for a real one). No shipped module declares `[[contracts]]` yet: the built-in Python checks below cover their formats.

```toml
id = "daily-prep"                       # must equal the folder name; lowercase-kebab-case
name = "Daily study prep"
tier = "standard"                       # core | standard | advanced | addon
summary = "One or two sentences."
requires = ["core", "courses", "planning"]   # hard dependencies, installed automatically
recommends = ["progress", "heartbeat"]       # shown to the student, never installed automatically
obsidian = "recommended"                # required | recommended | optional | irrelevant
os = ["any"]                            # any | windows | macos | linux (laptop scripts)
runtime = ["laptop", "vm"]              # laptop | cloud | vm | any
config_keys = ["schedule.daily_prep", "schedule.prep_check"]   # documentation: keys it reads
verbatim = ["vault/_agent/daily-prep/state.json"]               # globs copied without templating

[[jobs]]
id = "daily-study-prep"                 # jobs/<id>/ in the module folder

[[roles]]
id = "plan-and-progress"                # roles/<id>.md

[[skills]]
id = "course-facts"                     # skills/<id>/SKILL.md

[[folders]]                             # folders created at init (below)
path = "{{course.folder}}/{{item}}"
each = "course.official_subfolders"

[[contracts]]                           # declarative doctor checks (below)
name = "tracker log keeps its heading"
files = ["progress/tracker-log.md"]
headings = ["## Entries"]
frontmatter = { type = "log" }
level = "warning"

[defaults.schedule]                     # this module's config defaults, merged UNDER the user's config
daily_prep = ["17:30", "19:30"]
prep_check = "07:30"

[defaults.course]                       # applied to every [[courses]] entry that lacks the key
handwritten_folder = ""
```

| Key | Type | Default | Notes |
|---|---|---|---|
| `id` | text | (required) | equals the folder name; lowercase-kebab-case |
| `name`, `summary` | text | | a warning if missing |
| `tier` | `core` \| `standard` \| `advanced` \| `addon` | `standard` | |
| `requires`, `recommends` | lists of module ids | `[]` | `requires` is resolved transitively, each module after its dependencies, `core` first; cycles are an error |
| `obsidian` | `required` \| `recommended` \| `optional` \| `irrelevant` | `optional` | |
| `os` | list of `any`, `windows`, `macos`, `linux` | `["any"]` | the laptop systems the module's laptop scripts support. A preset leaves out a module that does not support the laptop's system (`runtime.laptop_os`, else the computer running the command); `doctor` and `enable` warn when an enabled module does not support `runtime.laptop_os` (for a module whose `runtime` goes beyond `laptop`, the warning names only its laptop part) |
| `runtime` | list of `laptop`, `cloud`, `vm`, `any` | `["any"]` | |
| `config_keys` | list of key paths | `[]` | documentation for the schema and the README |
| `verbatim` | list of globs relative to the module folder | `[]` | matched files are copied byte for byte (scripts, HTML templates, JSON state) |
| `[[jobs]]`, `[[roles]]`, `[[skills]]` | tables with `id` | | |
| `[defaults]` | table | `{}` | every key the module's templates need must have a default here; `tests/test_repo.py` checks that every default also appears in the example config, Alex's config and `schema.md` |
| `[[folders]]` | tables with `path`, optional `each` | | |
| `[[contracts]]` | tables | | |

Unknown top-level keys produce a warning and are ignored.

**Module folders (`[[folders]]`).** For folders whose names come from the config. `path` is a template and may use every template key. A `path` (or `each`) that uses `{{course.*}}` expands once per course, `{{error_log.*}}` once per course and error-log stream. `each` names a list key; one folder is created per non-empty item, bound as `{{item}}` (with `{{@index}}`, `{{@first}}`, `{{@last}}`). A leading `_agent/` or `inbox/` follows `paths.agent_dir` / `paths.inbox`. The result must be a safe vault-relative path; an absolute path, a missing `path` or a bad `each` is an error; other keys warn. Folders are created empty, only while their module is enabled, recorded in the manifest under `dirs`, listed in the `init`, `render` and `enable` output (also with `--dry-run`), and never deleted. Two modules may ask for the same folder. `render` does not recreate a folder you deleted; `init` does. In use: the courses module creates `<course folder>/<entry>/` for every `official_subfolders` entry; handwritten-notes creates `<course folder>/<handwritten_dir>/`. A `.gitkeep` or `.keep` file in a module's `vault/` tree also creates its folder and is not copied.

**Doctor contracts (`[[contracts]]`).** Run by `uni-os doctor` when the module is enabled:

| Key | Meaning |
|---|---|
| `name` | shown in findings |
| `files` | vault-relative globs (`**` allowed) |
| `headings` | each must start some heading line of every matching file |
| `frontmatter` | `key = value` pairs the properties must have; value `""` = the key must exist |
| `level` | `warning` (default) or `error` |

Python checks register with the `@contract("name", modules=(...))` decorator in `tools/uni_os/doctor.py`. Built-in checks: `week-pages`, `course-cards`, `prep-notes`, `course-property` (any note's `course:` must be a course id), `generated-regions`, `unrendered-placeholders`.

## Template language

Every text file under `modules/<id>/vault/`, `jobs/`, `roles/` and `skills/` is a template unless its module lists it in `verbatim`. The language is a small, strict, Handlebars-like subset (reference: the docstring of [`../tools/uni_os/template.py`](../tools/uni_os/template.py)).

### Values

```text
{{student.name}}                 the config value
{{courses.algo.name}}            a list item by id (lists of tables with an id key)
{{courses.0.name}}               a list item by index
{{course.lecture_slots}}         lists render joined by ", "
{{term.week0_monday}}            dates render ISO: 2026-09-14
{{obsidian.enabled}}             booleans render true / false
```

- **Known roots** (substituted at install): `student university term paths storage obsidian agent study courses course schedule notify calendar runtime vm cockpit modules uni_os generated`, plus the bound roots `item` and `error_log`.
- **Anything else is left untouched**, byte for byte: Obsidian's `{{date}}`, `{{date:YYYY-MM-DD}}`, `{{title}}`, and the reserved root `{{week.*}}` that `uni-os new-week` fills later (`number`, `nn`, `monday`, `sunday`, `label`, `status`, `previous_nn`, `next_nn`). The job header's run-time placeholders (`{{job.*}}`, `{{host.*}}`) are also left for the runners.
- **A missing key under a known root is an error** naming the file, line and key, also inside `{{#if}}`. Only `modules.<id>` is never an error: it is true when that module is enabled and false otherwise.
- **Always available:** `generated.date` (render date; `--date`, `$UNI_OS_TODAY` or `$SOURCE_DATE_EPOCH` make it reproducible), `generated.date_long` (the same day as text, `Sat 7 Nov 2026`, English names on every system), `generated.version`, and the lists `generated.modules`, `generated.roles` (`{id, module, title, runtime, file}`), `generated.jobs` (`{id, module, title, kind, slots, every_min, days, session, runtime, default_mode, dir}`), `generated.skills` (`{id, module, name, description, dir}`). The derived `term.weeks` is always there too: one `{number, nn, start, start_iso}` per teaching week, from `term.week0_monday` through the week of `term.last_lecture_day` (weeks 0 to 13 when that is empty).

### Blocks

```text
{{#each courses}}{{course.short}}{{#unless @last}}, {{/unless}}{{/each}}
{{#each course.assessments}}{{item.name}}: {{item.assistance}}{{else}}none listed{{/each}}
{{#if modules.daily-prep}} ... {{else}} ... {{/if}}
{{#unless obsidian.enabled}} ... {{/unless}}
{{#if agent.primary == "claude-code"}} ... {{/if}}
{{#if error_log.title != "Error log"}} ... {{/if}}
{{#if study.formats contains "html"}} ... {{/if}}
```

- `{{#each courses}}` binds `course` to each item; `{{#each <any other list>}}` binds `item`. Inside a loop: `{{@index}}` (0-based), `{{@first}}`, `{{@last}}`. An `{{else}}` branch renders when the list is empty.
- `{{#if cond}}` / `{{#unless cond}}` with optional `{{else}}`. `cond` is a key path (truthiness), `path == "literal"`, `path != "literal"`, or `path contains "literal"` (list membership or substring). Literals: quoted strings, numbers, `true`, `false`.
- **Truthiness:** `false`, `""`, `0`, empty lists and tables, and the string `"none"` are false.
- **Standalone lines:** a block tag (`{{#each}}`, `{{#if}}`, `{{#unless}}`, `{{else}}`, a closing tag) that stands alone on its line removes the whole line, so loops build Markdown tables without blank lines.
- **Escaping:** `\{{course.name}}` renders the literal text `{{course.name}}` (the backslash is dropped). Use it in documentation inside templates.
- Unbalanced blocks and unknown block syntax under a known root are errors. Rendering is all or nothing: if any template fails, nothing is written and every error is listed.

### Paths

- A path segment containing `{{course.` is produced once per course: `vault/{{course.folder}}/{{course.slug}}.md` gives `AD/ad.md`, `DM/dm.md`, ...
- A path containing `{{error_log.` is produced once per course and error-log stream: `vault/{{course.folder}}/{{error_log.file}}` gives `PROG/prog-error-log-theory.md` and `PROG/prog-error-log-programming.md`. Inside, `error_log` has `stream`, `file`, `path`, `title`.
- Source to target: `modules/<id>/vault/<path>` to `<vault>/<path>`; `jobs/<job>/<file>` to `<vault>/_agent/jobs/<job>/<file>`; `roles/<role>.md` to `<vault>/_agent/roles/<role>.md`; `skills/<skill>/<file>` to `<vault>/_agent/skills/<skill>/<file>`. A leading `_agent/` or `inbox/` follows `paths.agent_dir` / `paths.inbox`. Two modules producing the same vault path is an error.
- Install never overwrites an existing file unless `--force`; skipped files are listed.

## Generated regions

Parts of installed files that `uni-os render` keeps current even after you edited the rest of the file.

```markdown
## Vault map
Your own introduction stays as you wrote it.

<!-- uni-os:begin map -->
| Folder | What |
|---|---|
| me/ | the student model |
<!-- uni-os:end map -->

Your own notes below the region stay too.
```

- Each marker stands alone on its line (leading and trailing spaces allowed). `NAME` is `[a-z0-9][a-z0-9-]*`, unique within the file. Regions do not nest.
- A line that starts with `<!-- uni-os:` but is not a valid marker counts as malformed. A marker quoted inside a sentence (not alone on its line) is plain text.
- **Render behaviour** (`render`, `enable`, `disable`): a file nobody edited is re-rendered whole. An edited file whose current text and fresh rendering contain exactly the same set of well-formed regions gets only the region bodies replaced; every other byte is kept, including region order and CRLF line endings. If a marker is missing, renamed, duplicated, nested or malformed, the file is left alone and listed as skipped with the reason; nothing is guessed.
- `init` never merges (it only creates missing files); `--force` replaces whole files. `render --dry-run` lists each file that would be refreshed with the names of the regions that would change.
- `doctor` warns when an edited file's markers are broken; with `-v` it says which regions are out of date.
- Regions in use:

  | File | Module | Regions |
  |---|---|---|
  | `README.md` | core | `map` |
  | `where-to-find-what.md` | core | `lookup` |
  | `_agent/CONVENTIONS.md` | core | `courses`, `routing` |
  | `_agent/rules.md` | core | `integrity` |
  | `_agent/system-handbook.md` | core | `setup`, `registry` |
  | `courses-overview.md` | courses | `courses`, `rhythm`, `help`, `layout`, `official-subfolders`, `colours`, `page-offsets` |
  | `<course folder>/<slug>.md` (each course card) | courses | `assessments` |
  | `_agent/roles/README.md` | roles | `integrity`, `routing`, `roles`, `session-titles` |

Never edit inside a region (render overwrites it) and never delete or rename marker lines; put your own rows in the sections meant for them, outside the markers. The manifest bookkeeping of a merge is described under [Manifest](#the-install-manifest).

## `job.conf`

A job is a folder `<vault>/_agent/jobs/<job>/` with a `job.conf` and, for agent jobs, a `prompt.md`. `job.conf` is shell-style `KEY="value"` lines, sourced by bash on the always-on host and parsed by `uni_os.jobs.parse_conf` with bash quoting rules (`"double"` with `\" \\ \$ \`` escapes, `'single'` literal, bare words, concatenations, values spanning lines inside quotes, `#` comments; `$VAR` and `$(...)` are kept literally). Schedules are rendered from config keys; edit the config, not the rendered file.

```bash
# Job "daily-study-prep" (module daily-prep). Rendered from the config; edit the config, not this file.
TITLE="Daily study prep"
KIND="agent"
SLOTS="17:30, 19:30"
DAYS="Mon,Tue,Wed,Thu,Fri,Sat,Sun"
DATES=""
SESSION="print"
PRECHECK=""
AGENT_LOCK="shared"
LAPTOP_TASK="daily-study-prep"
RUNTIME="any"
DEFAULT_MODE="off"
export MY_SWITCH="1"      # an extra variable: doctor accepts it because of "export"
```

The always-on host sources `job.conf` in bash, so an exported variable reaches the job's environment there. The laptop runner `run_job.py` only reads the keys in the table below; it does not pass extra variables on.

| Key | Default | Values and meaning |
|---|---|---|
| `TITLE` | the job id | shown in logs and session titles: `job: <TITLE> · <Ddd HH:MM>` for laptop runs and host Remote Control sessions (headless host runs are named `job: <job id> <YYYY-MM-DD_HHMMSS>`) |
| `KIND` | `agent` | `agent` runs `prompt.md` with the host's agent CLI; `command` runs `COMMAND` with bash |
| `COMMAND` | | the command of a command job (cwd = the vault, or `$HOME` on the host with `NEEDS_VAULT="no"`) |
| `SLOTS` | | local times `"HH:MM, HH:MM"` |
| `EVERY_MIN` | | fixed polling interval: whole minutes `1`-`59`, or a multiple of 60 up to `1440`. The host uses it only when `SLOTS` and `SCHEDULE` are empty (`10` becomes `*-*-* *:00/10:00`); the laptop scheduler adds a repeating trigger |
| `DAYS` | `Mon,Tue,Wed,Thu,Fri,Sat,Sun` | comma list of `Mon` ... `Sun`; ranges `Mon..Fri` or `Mon-Fri`, which may wrap (`Sat..Mon`); empty = every day. `doctor` reports unknown day names only |
| `DATES` | | `YYYY-MM-DD` or `YYYY-MM-DD..YYYY-MM-DD`, `;`-separated: date limits or one-off dates; scheduled runs outside them are skipped |
| `SCHEDULE` | | raw systemd `OnCalendar` strings, `;`-separated; overrides `SLOTS`/`DAYS`/`DATES` on the host |
| `SESSION` | `print` | `print` = headless, asks nobody; `rc` = an interactive remote session you open from the phone (each new one notifies the phone: only for jobs that must talk to you) |
| `KEEP_H` | `8` | `rc` only: idle hours before the host's health check closes the session |
| `MODEL`, `EFFORT` | `""`, `high` | empty = the default: on the laptop the agent's own model; on the host `vm.default_model` / `vm.default_effort` (`AGENT_DEFAULT_MODEL` / `AGENT_DEFAULT_EFFORT` in `host.env`) |
| `TIMEOUT_MIN` | `45` | hard time limit |
| `NEEDS_VAULT` | `yes` | wait for the vault (mount plus sentinel on the host), else skip with exit 3; `no` for jobs that don't need it |
| `PRECHECK` | | shell test run first from the vault root; non-zero = "nothing to do", exit 0, no agent started |
| `QUIET_OK` | `no` | `yes` = only failures go to `jobs.log` |
| `DRY_OK` | `no` | command jobs: `yes` appends ` --dry-run` to `COMMAND` on a dry run (only for commands that honour it); `no` = a dry run only prints the command |
| `NOTIFY_DONE`, `NOTIFY_GATE` | | `rc` jobs: push this text with the session link after the first turn, through the push gate with these ids |
| `AGENT_LOCK` | `shared` | `shared` waits only for an exclusive holder; `exclusive` waits until no other agent job runs (skips after `LOCK_WAIT_MIN`); `none` |
| `LOCK_WAIT_MIN` | `20` | minutes to wait for the lock |
| `LAPTOP_TASK`, `FAILOVER_DELAY_MIN`, `MARKER` | job id, `25`, `yes` | failover between laptop and host ([`runtimes.md`](runtimes.md#failover-between-laptop-and-host)) |
| `RUNTIME` | `any` | `any`, `laptop` (never taken onto the host), `vm` (host only) |
| `DEFAULT_MODE` | `off` | state when first installed: `off`, `always`, `failover` |

Validation (`doctor`, `uni-os jobs`): enum values, whole numbers for `KEEP_H`, `TIMEOUT_MIN`, `LOCK_WAIT_MIN`, `FAILOVER_DELAY_MIN`; `SLOTS` entries are `HH:MM`; `EVERY_MIN` in range; `DATES` entries well-formed; `KIND=agent` needs `prompt.md`, `KIND=command` needs `COMMAND`; `SESSION=rc` only for agent jobs; any other key is reported as unknown unless it is passed with `export KEY=...`. A job without `SLOTS`, `EVERY_MIN`, `SCHEDULE` or `DATES` is only started by other tools.

A file named `DISABLED` in a job folder (written by `uni-os disable <module>`) makes both runners skip the job, and `uni_os.jobs.list_jobs` hides it.

**`prompt.md`** is the complete unattended prompt. Its anatomy (module scheduler-local, `_agent/jobs/README.md`): an "already done?" guard for the nominal slot first; identity and scope; a "read first" list (`_agent/agent-start.md`, `_agent/rules.md`, the contract files) instead of inlined rules; the real time from a command; branches per slot with a catch-up rule; tool constraints; write rules for shared files; integrity and privacy rules; interactive jobs in two turns; notification discipline (never "all good"); a failure flag when the result is incomplete; a fixed final-reply line. The runners put a host header in front (`_agent/jobs/_header.md` on the laptop, `modules/vm/host/agent/job-header.md` on the host), and a dry-run preamble on dry runs.

## Role brief

`<vault>/_agent/roles/<role>.md`, rendered from `modules/<id>/roles/<role>.md`. Common rules for every role live in `_agent/roles/README.md` (module roles), which also holds the generated routing table.

```markdown
---
type: role
id: exercise-help
title: "Exercise help"             # session title; per-course sessions are "<SHORT> · Exercise help"
runtime: any                        # preferred runtime: laptop | cloud | vm | any
model: ""                           # empty = the agent's default
effort: high
owns:                               # vault paths this role writes (one writer per file)
  - "<course>/<slug>-error-log.md"
  - "<course>/backlog.md"
reads:
  - "_agent/agent-start.md"
  - "_agent/rules.md"
  - "_agent/roles/exercise-help.md"
---
# Exercise help

## Purpose
## Start-up
## Duties          (each duty names its trigger: a job, a kind of student message, or a message from a named role)
## Rules           (integrity first)
## Output formats
## Handoffs and routing
## Never
```

Briefs may add sections (the exercise-help brief has "Assistance levels", the quiz coach "The quiz variants"). A duty written as "do it when you notice it is due" never fires: every duty names its trigger.

## SKILL.md

Skills use the open Agent Skills format: a folder `<vault>/_agent/skills/<skill>/` with a `SKILL.md`, optionally `references/` (more Markdown the skill links to) and `scripts/` (helpers).

```markdown
---
name: log-error
description: Append a row to a course's error log when the student says "log this error", or the moment an error shows up. Use it unasked, in the same turn.
---
# Log an error

Steps, rules and examples in plain Markdown.
```

`name` equals the folder name; `description` says what the skill does and when to use it, because agents decide from it whether to load the skill. Skills are templates (they contain your courses and term); `render` updates them. Setup copies or links them into `agent.skills_dir` ([`agents.md`](agents.md#pointing-your-agent-at-the-skills)).

## Note properties and file names

Every note starts with a properties block:

| Key | Values |
|---|---|
| `type` | one value from the note-type table in `_agent/CONVENTIONS.md`: `home`, `overview`, `agent`, `inbox`, `lecture-note`, `study-page`, `reference`, `me`, `course`, `backlog`, `error-log`, `quiz-prep`, `status`, `log`, `week`, `plan`, `prep`, `role`, `digest`, `job` (the table lists only the types of enabled modules; update notes use `inbox-update`, defined by the inbox-sync module). Views and jobs filter on it, so never invent a near-duplicate. |
| `course` | **a course id** from the config (`algo`), never the slug or short name; only on course notes. `doctor` (check `course-property`) warns about any other value and suggests the id; empty values, `<placeholders>`, `_templates/` and `paths.never_open` are skipped. |
| `audience` | `me`, `agent` or `both` |
| `updated` | `YYYY-MM-DD`, bumped on every edit |
| `tags` | `uni/<course id>` or `uni/<area>`, plus a flat tag such as `study-page` or `error-log` |

Study pages also carry `kind` (teaching-page, skim, rundown, recap, summary, cheat-sheet, walkthrough, ...); Markdown twins add `source_html` and `converted`.

**Course note names:** lowercase kebab-case, `<slug>-<what>-<kind>`, the kind word last (the HTML-to-Markdown converter reads the kind from it). Pages tied to one lecture put `lecture-<ddd><d><mon>` after the slug, with the day unpadded (`mon2nov`).

| Kind | File name (without extension) | Folder |
|---|---|---|
| teaching page | `<slug>-<topic>-study-page` | `<course folder>/notes/` |
| skim / rundown | `<slug>-lecture-<ddd><d><mon>-<topic>-skim` / `-rundown` | `notes/` |
| recall key, transcript | `<slug>-lecture-<ddd><d><mon>-recall-key`, `...-transcript` | `notes/` |
| recap | `<slug>-<what>-recap` (e.g. `ad-sheet6-recap`) | `notes/` |
| summary | `<slug>-<topic>-summary`; the running summary sheet `<slug>-running-summary` | `notes/` |
| cheat sheet, walkthrough | `<slug>-<topic>-cheatsheet`, `<slug>-<topic>-walkthrough` | `notes/` |
| definitions deck | `<slug>-definitions-deck` | `notes/` |
| hint page, mistake map | `<slug>-sheet<N>-<task>-hints`, `<slug>-sheet<N>-mistake-map` | `notes/` |
| quiz prep | `<slug>-quiz-<quiz-id>-prep`, `-mock[-<n>]`, `-selfstudy` | `<course folder>/quiz-prep/` |
| own lecture note | `<slug>-lecture-<ddd><d><mon>` | `notes/` |

HTML pages get a Markdown twin with the same base name when `study.formats` holds both `html` and `md`. Official course files keep their official names.

## Week page

`progress/weeks/week-NN.md`, NN = the two-digit term week (week 0 starts `term.week0_monday`; week n starts 7n days later). Created by the `week-page` job or `python tools/uni_os.py new-week` from `_templates/week-page.md` (never overwrites; `--status`, `--current`, `--week N`, `--close-previous`, `--dry-run`).

```markdown
---
type: week
week: 7
start: 2026-11-02
end: 2026-11-08
status: current
audience: me
updated: 2026-11-06
tags: [uni/week]
---
# Week 7: Mon 2 Nov to Sun 8 Nov 2026

Plan: [week-07-plan.md](../../semester/plans/week-07-plan.md)

## Due this week
| Item | Official deadline | Personal target | Bonus | Status |
|---|---|---|---|---|
| AD exercise sheet 6 (out Thu 29 Oct) | Thu 5 Nov 23:59 | Sun 1 Nov | 10 pts | open: tasks 1-3 done, 4 open |
| DM graded sheet 4 (out Mon 2 Nov) | Mon 9 Nov 12:00 | Sun 8 Nov | 2 pts (solo) | done 1.5 / 2 (Fri 6 Nov ~16:10, LMS feedback) |

## Results this week
- Fri 6 Nov ~16:10: DM graded sheet 4 = **1.5 / 2** (LMS feedback).

## Notes
- Created Sun 1 Nov 10:00 by the week-page job.

## End-of-week check-in
- Done: _To fill_
- Focused hours: _To fill_
- What worked: _To fill_
- What didn't: _To fill_
- Missed: _To fill_
- Self-rating: _To fill_
- Rolls over: _To fill_
```

- **Headings** are exact and in this order: `## Due this week`, `## Results this week`, `## Notes`, `## End-of-week check-in` (readers match by prefix; `doctor` reports a missing one as an error).
- **`status`**: `upcoming` (only for pages made more than three days ahead), `current` (exactly one page), `done`. `doctor` warns about other values and about more than one `current` page; `week:` must match the file name.
- **Check-in done** = no `_To fill_` marker left in the check-in section, independent of `status`. The check-in job's `PRECHECK` looks for that marker.
- **Columns** are found by header words: `item`, `official|deadline`, `target|sunday` (header from `study.target_column`), `bonus`, `status`.
- **Item** starts with the course short name and is unique within the week (Done taps match it exactly).
- **Official deadline**: `Ddd D Mon HH:MM`, 24 h; ranges `Wed 11 Nov 14:15-14:45`; a soft date starts with `tutorial` or contains `(tentative)` and is never overdue.
- **Bonus**: points (`4 pts`) or `none` / `no` / `feedback only`.
- **Status vocabulary**, checked in this order after leading emphasis is stripped: a Done-tap mark `done (<Ddd D Mon HH:MM>, tapped). Before: <old cell>` = done; `not reported`, `pending` or `not recorded` anywhere = pending (took place, result unknown); a cell that **starts with** `✓`, `done`, `submitted`, `closed`, `handed in`, `uploaded`, `dropped`, `skipped` (whole words) or a score `x / y` = done; `not released` = a future item; anything else = open, overdue once the deadline has passed. `heartbeat.done_words` and `cockpit.done_words` hold the same list.

Related progress shapes (module [progress](../modules/progress/README.md)): the dashboard `progress/current-status.md` (a `**Snapshot: ...**` line, `## Bonus standing`, `## Exercises: done vs. to do`, `## Self-rated understanding`, `## Next 10 days` with a `When / What` table) and the tracker log `progress/tracker-log.md` (append-only lines `- <Ddd D Mon YYYY> ~HH:MM (<source>): **<key fact>** <details>; <consequence>; <unknowns>.` under `## Entries`).

## Prep note

`semester/prep/prep-YYYY-MM-DD.md`, revisions `-r2`, `-r3`, ...; the highest revision wins, then the latest `generated`. Prep notes are never edited, moved, renamed or deleted: a change is a new revision. Reference implementation and checker: `python modules/daily-prep/scripts/prep_note.py check <vault> --date YYYY-MM-DD`.

```markdown
---
type: prep
audience: me
date: 2026-11-12
generated: 2026-11-11T17:31+01:00
run: "17:30"
status: ready
tags: [uni/prep]
---
# Prep for Thu 12 Nov 2026 (week 8)

Full prep from the 17:30 run: two study blocks and two classes.

> [!dm] 08:15-10:00 DM_ practice sheet 8
> - Sheet: `DM/DM assignments/sheet08.pdf` (practice sheet, hints only)

> [!ad] 10:15-12:00 L: AD
> - Script chapter 6 (predicted by the topic plan): `AD/AD slides & script/script.pdf`

> [!ad] 13:15-16:00 AD_ Sheet 7 rest (deep)
> - Sheet: `AD/AD assignments/sheet07.pdf` (tasks 7.3-7.5, due today 23:59; hints only)
> - Study page: [ad-dynamic-programming-study-page](../../AD/notes/ad-dynamic-programming-study-page.md)

> [!la] 16:15-18:00 E: LA
> - Exercise class: sheet 8 is discussed: `LA/LA assignments/sheet08.pdf`

## Gaps
- none
```

- Properties: `date` = the day prepared; `generated` ISO with offset; `run` = the nominal slot, quoted, or `manual`; `status` `ready` or `ready-with-gaps` (exactly when gaps exist).
- Title `# Prep for <Ddd D Mon YYYY> (week N)`.
- One callout per study block and per class, in time order: `> [!<course>] HH:MM-HH:MM <title>`, where `<course>` is the course's **slug** (the callout type the CSS snippet colours; readers also accept the course id) and start and end equal the calendar event's. Items are `> - ` lines; vault notes as relative links from `semester/prep/` (angle brackets around paths with spaces or `&`), HTML pages and PDFs as backticked vault paths, integrity warnings inside the item.
- `## Gaps` is the last section: `- none`, or one bullet per gap with its fallback.
- `doctor` checks the file name and `type: prep`, and that `date` matches the name.

The **MATERIAL block** is the last block of each study block's calendar description; later runs replace only this block:

```text
MATERIAL (daily prep, Wed 11 Nov 17:31; all of it in Obsidian: semester/prep/prep-2026-11-12)
- Sheet: AD/AD assignments/sheet07.pdf (tasks 7.3-7.5, due today 23:59; hints only)
- Obsidian AD/notes/ad-dynamic-programming-study-page.md
- PENDING: <gap> (fallback: <fallback>)
```

("Obsidian" becomes "the vault" when `obsidian.enabled = false`.) The job's state is `_agent/daily-prep/state.json`: `{"days": {"YYYY-MM-DD": {"status": "done|open", "attempts", "prep_file_name", "blocks_sig", "gaps": [...], "done_by", "last_change_check", "verified", "calendar"?}}, "carry": {"YYYY-MM-DD": ["<item>"]}}`; the outcome checks read `days[<date>].gaps`.

## Course card

`<course folder>/<slug>.md`, one per course, rendered at setup and then maintained by agents (the single source of truth for that course's facts).

```markdown
---
type: course
course: algo
bonus_banked: "0 / 0 graded"
bonus_target: "80 % of all sheet points"
next_bonus: ""
updated: 2026-11-07
audience: both
tags: [uni/algo, course]
---
# AD: Algorithms and Data Structures (Autumn 2026)
```

- `course` is the course **id**; `doctor` (check `course-cards`) warns when `type` is not `course` or `course` is not the id, and when a card is missing.
- `bonus_banked`: the first `x / y` pair = banked / graded so far (or banked / total), e.g. `"7 / 9 graded (78 %)"`.
- `bonus_target`: e.g. `"80 % of ~156 pts (est.)"` (threshold courses: `NN % of ~M` is parsed for the pace check) or `"8 points"`.
- `next_bonus`: starts with a date, `"<Ddd D Mon HH:MM> <what> (<solo|group>)"`.

The cockpit reads only these three properties from the card; the bonus maths comes from `[courses.bonus]` in the config.

## Error-log row

`<course folder>/<slug>-error-log.md` for a course with one stream, `<slug>-error-log-<stream>.md` per stream otherwise (`courses[].error_log_streams`). Properties: `type: error-log`, `course: <course id>`, `stream`, `audience: both`, `updated`, `tags: [uni/<course id>, error-log]`. Sections: the table under `## Errors and misconceptions`, then `## Patterns to watch`, then `## Open points`.

```markdown
| Date | Where | What went wrong | Correct idea | Source |
|---|---|---|---|---|
| Mon 26 Oct | Sheet 3, 3.2 b) recurrence | Used case 2 of the master theorem although f(n) grows polynomially faster than n^(log_b a) | Compare f(n) with n^(log_b a) first; check the regularity condition; try n = 16 by hand | [script] p. 42 |
```

- **Date** `Ddd D Mon`. **Where**: `Sheet 3, 3.2 b) <short task name>`, `Quiz W5 Q3`, `Lecture Mon 26 Oct, clicker 2`, `Study page <name>, quiz B Q4`, `Sheet 4 corrections p. 2`, `retest of <date> row (R3)`. **What went wrong**: concretely, TA quotes in quotes, your state if you mentioned it. **Correct idea**: the general rule, a small-case check and the habit, never the full solution of a current graded task. **Source**: a tag plus the place: `[script]`, `[slides]`, `[handout]`, `[task]`, `[lecture]`, `[TA correction]`, `[quiz review]`, `[derived]`, `[user note]`, `[other AI]`, `[retest]`.
- Append-only: a correction is a new row ("Correction to the row of <date>: ..."). The one exception: a row about `solo` work is deleted.
- Patterns: `1. **<pattern name>** (<dates and where>): <what goes wrong>. Fix: <habit, technique or page>.`, mirrored as one line in `me/weak-spots.md`.
- Session notes go into a dated `## Session note (<Ddd D Mon>)` section below the table, not into rows.
- Helper: `python _agent/tools/error_log.py add --course <course id> --where ... --what ... --idea ... --source ... [--stream S] [--date YYYY-MM-DD]` (escapes pipes, turns line breaks into `<br>`, bumps `updated`); `check` validates five cells per row.

## Update notes and the inbox

Writers that can only **create** files (cloud sessions through a storage connector, the cockpit's Done taps) change existing files by dropping an update note into the inbox; the `inbox-sync` job applies it only if every quoted line still matches exactly ("the vault wins"). Full protocol: `_agent/inbox-sync/README.md` (module [inbox-sync](../modules/inbox-sync/README.md)).

**File name:** `<paths.inbox>/YYYY-MM-DD_HHMM_<sender>-update.md`, local time, `<sender>` the lowercase kebab-case role and course (`ad-exercise-help`); a second note in the same minute adds a letter (`..._0935b_...`). Only names ending in `-update.md` are update notes; everything else in the inbox is yours and never touched.

```markdown
---
type: inbox-update
from: "AD · Exercise help (cloud)"
created: 2026-11-10 21:04 (Europe/Zurich)
tags: [inbox, uni/algo]
---
# AD · Exercise help: update, Tue 10 Nov 2026 21:04

All "replace" lines below are quoted exactly as they stand in the vault now (read 21:02). Apply a replacement only if the quoted line is still there.

## AD/ad-error-log.md

**1. Append this row at the end of the "Errors and misconceptions" table** (after the row starting with `| Mon 26 Oct | Sheet 3, 3.2 b)`):

| Tue 10 Nov | Sheet 7, 7.2 a) | ... | ... | [derived] |

**2. Replace the line**
`next_bonus: ""`
**with**
`next_bonus: "Thu 12 Nov 23:59 sheet 7 (solo)"`

Also set `updated:` to 2026-11-10.

## For Plan & progress
- Sheet 7 task 7.4 took twice the planned time; your call how this fits tomorrow's blocks.

## Not changed
- The backlog: nothing new.
```

Operations: append row, append bullet, replace line, insert after line; each numbered and anchored, anchors quoted in backticks, complete and unchanged. One `## <path>` section per target file. `## For <session title>` sections are forwarded unchanged; `## Not changed` is read, never applied. An optional line "Apply after <note>." orders notes.

**Done-tap notes** (cockpit): `YYYY-MM-DD_HHMM_cockpit-done-<item-slug>-update.md` (undo: `cockpit-undo-`), properties `type: inbox-update`, `from`, `created`, `tapped_at` (ISO UTC) and `done_item: "<item text exactly as in the week page>"` (`undo_item:` for an undo). The rule: change only that row's Status cell on the current week page to `done (<Ddd D Mon HH:MM>, tapped). Before: <old cell>`; an undo restores the text after `Before: `.

**Applier log:** one line per run that did something in `_agent/logs/inbox-sync-log.md`:

```text
- YYYY-MM-DD HH:MM (job inbox-sync, <host>, slot YYYY-MM-DD HH:MM): applied N notes from "<sender>": `<file>`. Files changed: `<path>` (<what>; `updated:` YYYY-MM-DD). Anchors matched. Forwarded: ... Notes moved to `_agent/inbox-applied/YYYY-MM/`. Parked: none. Refused: none.
```

Vocabulary: `PARKED` (anchor not found, or waiting for an earlier note), `WAITING` (a `## For` section could not be forwarded), `REFUSED` (unclear, contradicts the vault, or forbidden content), `ALREADY APPLIED`, `LEFT` (a converted stub that can't be read). Applied notes move to `_agent/inbox-applied/YYYY-MM/`, never deleted. A note still in the inbox after `notify.inbox_stale_hours` (4; Done taps `notify.inbox_stale_hours_taps`, 14) counts as stuck; its outcome id is `inbox:stuck:<slug of the file name>`; a slug over 60 characters is cut to 53 and ends in `-` plus the first 6 hex digits of the file name's SHA-1.

## Failure flags

Exit code 0 says a job ended, not that its result is there. A job that ends without its full result writes one small file, `_agent/logs/flags/<job id>.md` (folder `heartbeat.flags_dir`), instead of pushing:

```markdown
---
job: daily-study-prep
at: 2026-11-10 17:31
level: red
---
calendar write denied; prep note written without MATERIAL blocks
```

- `at` is local time; `level` is `red` (the main output is missing) or `amber` (it is incomplete); the first body line is one plain sentence saying what failed and what is left undone, with no personal details. A newer flag overwrites an older one.
- The next run of the same job that ends complete, or finds nothing left to do, deletes the flag; it is the only file those jobs may delete. Jobs whose `PRECHECK` could skip the agent also start while their flag exists (`inbox-sync`, `lecture-skim`, `quiz-prep`, `deadline-audit`), so a stale flag gets cleared.
- The heartbeat's pre-check turns a flag into the finding `job:<job id>:failed` (level from the file, default red). The flag replaces any push.

| Job | Writes a flag when |
|---|---|
| `daily-study-prep`, `study-prep-morning-check` | red: a target day has no note; amber: the note lacks MATERIAL blocks or a repair failed (gaps with a fallback are not failures) |
| `check-in` | red: the check-in could not be completed |
| `week-page` | red: the page is missing; amber: closing the old week or the plan request failed |
| `lecture-skim` | amber: a due skim could not be written |
| `quiz-prep` | amber: a due sheet could not be built (red within 24 h of the quiz) |
| `deadline-audit` | amber: the report is incomplete |
| `inbox-sync` | red: the inbox can't be read; amber: a step was skipped |
| `heartbeat`, `heartbeat-weekend` | red: the run could not commit its decisions (the report failed, or commit was refused twice), or the pre-check hit an internal error and failed open (written by `uni-os heartbeat precheck`); amber: it committed only part of what it judged |
| `vm-performance-verdict`, `waiting-on-you` | amber: the verdict or the page could not be written |

## Heartbeat files

In `_agent/heartbeat/` (module [heartbeat](../modules/heartbeat/README.md); full contract in the installed `_agent/heartbeat/README.md`):

- `flags.json` (schema 1): `{schema, generated, writer, run: {at, kind, act_mode, dry_run}, flags: [{id, level: red|amber|grey, text (at most 300 characters), since, last_seen, pushed_at, snoozed_until, source, action, where}]}`. Ids are stable across runs (`due:<item>:overdue|behind`, `prep:gap:<date>`, `prep:tomorrow-missing:<date>`, `week:missing:<file>`, `job:<name>:failed|missed`, `inbox:stuck:<slug>`, `judgment:<topic>`, `duty:<row>`, `result:<item>`, `waiting:<item>`). Before the first run: `"generated": null`, `"status": "not-switched-on"`. Rewritten **in place** (no temp file and rename), so a synced file keeps its id.
- `state.json` (schema 1): `{schema, updated, last_run, inputs, outcome_keys, flagged, snoozes, actions, asks}`.
- `heartbeat-log.md`: `- YYYY-MM-DD HH:MM | slot|event|note|answer[ DRY-RUN] | <what fired, flagged, pushed, asked or done>`.
- `requests.md`: `- YYYY-MM-DD HH:MM | snooze | <what; `flag-id` if known> | until <YYYY-MM-DD or "further notice"> | <who>`; `resume` instead of `snooze` lifts it. A line naming an id or a prefix ending in `*` works at the next pre-check.

Outcome-check ids and push texts are word for word the same in every sender (the heartbeat rules, the host's `outcome-checks`, `inbox_poll.py`): `prep:today-missing:<date>`, `prep:tomorrow-missing:<date>`, `inbox:stuck:<slug>`, `prep:gap-open:<date>`, pushed with the prefix `Outcome check: ` (`heartbeat.outcome_prefix`). Exactly one machine sends them ([`../modules/notifications/README.md`](../modules/notifications/README.md), "One sender per problem").

## Push gate state

Outside the vault, per user and machine: `~/.local/state/uni-os/push-gate/` on Linux and macOS (`$XDG_STATE_HOME` respected), `%LOCALAPPDATA%\uni-os\push-gate\` on Windows (overrides: `UNI_OS_PUSH_STATE`, or `UNI_OS_STATE` / `UNI_STATE_DIR` for the state root).

| File | Content |
|---|---|
| `state.json` | `{"schema": 1, "pushes": [{"at", "source", "ids", "text", "direct"}], "ids": {"<id>": "<ISO time last pushed>"}, "held": [{"at", "source", "ids", "text", "priority", "title", "click", "direct", "reason"}]}`; pruned to 14 days; written under a lock with a temp file and an atomic rename |
| `notify.log` | one line per attempt: the time (`YYYY-MM-DD HH:MM`), the outcome (`sent`, `deferred`, `held`, `refused`, `dedupe`, `budget`, `failed`), the source, the ids and the text, separated by ` \| `; trimmed |
| `notify-settings.json` | the last known `[notify]` settings, so a direct alert still goes out when the vault is unreachable, or when the vault config can't be used (invalid TOML or `[notify]` value) |
| `.lock` | held while a call reads, decides, sends and records; a call that waits over 45 s exits 1 "gate busy, try later" |

`uni-os push` exit codes: `0` sent, `1` the HTTP request failed, `2` usage or setup error, `10` held (quiet hours or window), `11` budget, `12` dedupe, `13` refused (no id, "all good", personal details). Senders treat 10-13 as normal outcomes, not failures.

## Run logs

Both job runners keep their logs **outside the vault**: `<state>` = `UNI_STATE_DIR`, else `%LOCALAPPDATA%\uni-os` (Windows laptop) or `~/.local/state/uni-os` (macOS, Linux, the host).

- Per run: `<state>/jobs/<job>/<YYYY-MM-DD_HHMMSS>[-dry].log`, ending with the footer `# exit N after Ss` (the host's snapshot and the heartbeat read it). 40 logs are kept per job.
- `<state>/jobs.log`, one line per run:

```text
2026-11-11 17:30 | daily-study-prep | exit 0 | 412s | <log file>
2026-11-11 19:30 | daily-study-prep | dry run | exit 0 | 236s | <log file>
2026-11-11 07:15 | inbox-sync | skipped | nothing to do (precheck)
```

Skips are logged with a reason: on the host `skipped | <reason>` (`nothing to do (precheck)`, `outside DATES`, `laptop ran this slot`, `module disabled (DISABLED marker): ...`), on the laptop `skipped | <reason> | Ss | <log file>` (`precheck`, `host ran this slot`, `vault not reachable`, `module disabled`, `agent lock`). The laptop runner writes the log's full path, the host its file name. With `QUIET_OK="yes"` only failures are listed. The heartbeat reads this file through `heartbeat.jobs_log` (default `{state}/jobs.log`).

Agent-written logs inside the vault (`_agent/logs/`, the inbox-sync log, the daily-prep log, the course-fetch log) are append-only Markdown with one line per event; their rules are in `_agent/logs/README.md`.

## Failover marker

`_agent/vm/ran/<task>.md`, written by the always-on host after it ran a job in failover mode in the laptop's place (`<task>` = `LAPTOP_TASK`):

```markdown
---
type: agent
audience: agent
updated: 2026-11-11
tags: [uni/agent]
---
slot: 2026-11-11 17:30
ran_on_host: 2026-11-11 18:02
exit: 0
```

A blank line and one plain sentence follow (which host ran the laptop task for that slot, and that a laptop catch-up for the same slot can stop). `slot` is the nominal scheduled minute. A laptop run whose nominal slot equals it stops at once. The marker is overwritten by the next failover run of the same task. See [`runtimes.md`](runtimes.md#failover-between-laptop-and-host).

## The install manifest

`<vault>/_agent/.uni-os-manifest.json` records what `uni-os` installed. It holds vault-relative paths and hashes only (no absolute paths, no personal data).

```json
{
  "_generated": "do not edit; maintained by uni-os (what it installed, to detect your edits)",
  "schema": 1,
  "framework_version": "0.1.0",
  "updated": "2026-11-07",
  "modules": { "daily-prep": { "status": "enabled", "since": "2026-11-07" } },
  "dirs": { "AD/AD assignments": "courses", "AD/AD handwritten": "handwritten-notes" },
  "files": {
    "semester/prep/README.md": { "module": "daily-prep", "source": "daily-prep/vault/semester/prep/README.md", "sha256": "<hex>" },
    "_agent/daily-prep/state.json": { "module": "daily-prep", "source": "daily-prep/vault/_agent/daily-prep/state.json", "sha256": "<hex>", "verbatim": true },
    "README.md": { "module": "core", "source": "core/vault/README.md", "sha256": "<hex of the last full rendering>", "merged_sha256": "<hex right after the region merge>" }
  }
}
```

- A file whose hash still matches `sha256` is **unmodified**: `render` may update it. A different hash means **modified**: yours, never overwritten without `--force`, apart from its generated regions. A recorded file that is gone is **missing**: `init` restores it, `render` does not.
- **Region merges:** `sha256` stays the hash of the last *full* rendering, so the file keeps counting as edited and the next render merges again instead of overwriting your text. `merged_sha256` is the hash right after the merge, so `doctor -v` can say "edited outside its generated regions; render refreshed the regions". If a merge makes the file equal to a full rendering, the entry is recorded like a normal write and the file counts as untouched again.
- `dirs` maps each created folder to the module that asked for it. Folders are never deleted; `render` does not recreate a deleted one, `init` does. `doctor` warns about module folders not created yet ("run uni-os render") and recorded folders that are missing.
- If the manifest is corrupted, rename it; `init` then treats existing files as not installed by `uni-os` (and skips them).

## Other contracts

| Contract | Format | Reference |
|---|---|---|
| Course pick-up request | `_agent/course-fetch/pending/<id>.json`: `{"file", "target", "requested_at", "approved_large", "machine"?}`; `<id>` = `YYYYMMDD-HHMMSS-<sanitised file name>`; written as `.<id>.json.part`, then renamed | [course-files-fetch](../modules/course-files-fetch/README.md) |
| Course pick-up result | `_agent/course-fetch/done/<id>.result.json`: `{"id", "file", "target", "status", "reason", "size", "host", "sha256", "vault_sha256"?, "at"}`; status `filed`, `already-there`, `changed-on-server`, `rejected`, `not-found`, `failed` | same |
| What's waiting on you | `waiting-on-you.md` at the vault root, `type: digest`, `audience: me`, sections `## Today`, `## When you're back at the laptop`, `## Before <Ddd D Mon>`, `## Still open, no deadline`; each item an H3 with **State**, numbered **Steps**, **Time**, **Details** link, "(new)" when it wasn't on the previous page; rewritten at every run | [roles](../modules/roles/README.md) |
| Vault watcher output | `_agent/vault-watch/log.md` (one line per run and scope), `alerts.md` (`- YYYY-MM-DD HH:MM - <text>`), `sources-inventory.tsv` (`path`, `size_bytes`, `modified_utc`, `area`), `sources-expected.json` (expected-files table) | [vault-watch](../modules/vault-watch/README.md), "Behaviour specification" |
| Host status | `_agent/vm/status.md`, `performance.md`, `snapshot.json` (schema 1, rewritten in place every health run) | `_agent/vm/README.md` in the vault, [vm](../modules/vm/README.md) |
| Experiments | in `semester/experiments/`: `YYYY-MM-<slug>-plan.md` (`type: plan`), `YYYY-MM-<slug>-block-log.md` (append-only `\| Date \| Block \| Subject \| Focused min (focus 1-5) \| Done \|`, "Done" starting with DONE, PARTIAL, FAILED, MISSED or SKIPPED), and the coverage list `YYYY-MM-<slug>-coverage.md` (`type: log`, per-day `\| Block \| Logged outcome \| Note \|` tables) | [experiments](../modules/experiments/README.md) |
| Deadline audit | `semester/plans/deadline-audit-YYYY-MM-DD.md` (`type: plan`) | [planning](../modules/planning/README.md) |
| Coordinator state | `_agent/coordinator-state.md`: live roster, open items (a row that waits on the student starts its next-step cell with `Waiting on <student name>:`), scheduled jobs per host, decisions log | [roles](../modules/roles/README.md) |

## Related pages

- [`../tools/README.md`](../tools/README.md): the command line, installing, the library helpers.
- [`../config/schema.md`](../config/schema.md): every config key.
- [`architecture.md`](architecture.md): how the pieces use these files.
- [`glossary.md`](glossary.md): the vocabulary (module, role, session, job, runtime).
