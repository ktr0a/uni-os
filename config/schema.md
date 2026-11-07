# Config schema

Every key of `uni-os.toml`: type, default, meaning and which modules use it. The commented example is [`uni-os.example.toml`](uni-os.example.toml); a complete fictional config is [`../examples/alex.toml`](../examples/alex.toml).

## How the config works

- **One file, in the vault.** After setup the config lives at `<vault>/_agent/uni-os.toml`. It is the single source of truth for every parameter. `uni-os` also writes a machine copy, `<vault>/_agent/uni-os.json` (first key `"_generated": "do not edit; edit uni-os.toml"`), for consumers that cannot read TOML (the Obsidian cockpit plugin). Never edit the JSON.
- **Defaults are layered** (lowest priority first): the built-in defaults in this document, then the `[defaults]` of every module that is *not* enabled, then the `[defaults]` of every enabled module, then your file. Tables merge key by key; lists and values replace. `uni-os config keys` prints every key with its value and where the value comes from (`base`, `module:<id>`, `user`, `derived`).
- **Per-course defaults.** A module's `[defaults.course]` table is applied to every `[[courses]]` entry that lacks those keys.
- **Secrets never go in the config or the vault**: no API keys, tokens, private calendar (iCal) addresses or the ntfy topic. The config may only hold *paths* to secret files outside the vault (`notify.ntfy_topic_file`). `uni-os doctor` refuses keys named like `*_token`, `*_secret`, `*_api_key`, `*_password` and scans every value for key-like strings.
- **Formats.** Dates: `2026-09-14` (TOML date) or `"2026-09-14"`. Times: quoted 24-hour `"07:30"` (bare `07:30` is not valid TOML 1.0). Time ranges: `"21:00-07:30"`. Days: `"Mon"` ... `"Sun"`. Colours: `"#1e66f5"`.
- **No fixed days or times.** Every schedule is a value you choose during setup. The defaults are the original system's values, shown only as an example.
- **Validation.** `uni-os doctor` (or `uni-os config validate`) checks required keys, types, enum values, dates, times, unique course ids/slugs/folders (case-insensitive, because Windows and macOS file systems are), valid folder names, colours, module ids and every quiet-window shape, and warns about unknown keys (typos, also inside `[[courses.assessments]]` and quiet windows) with a "did you mean" suggestion, about a hard quiet window longer than a day, and about a module key you changed while none of the modules that read it is enabled (for example `schedule.vault_watch` without `vault-watch`: it has no effect). Not reported: values equal to the module's default (so keys copied from the example config are fine) and keys with a built-in default (not from a module's `[defaults]`), which the tools and any module's templates may read.
- **Templates** read these keys as `{{table.key}}` (see [docs/file-formats.md](../docs/file-formats.md#template-language) and `tools/uni_os/template.py`). Only the roots listed there are template keys; tables that modules add (`[heartbeat]`, `[course_fetch]`, `[vault_watch]`) are read by scripts and agents through `uni-os.json` / `uni-os config get`.
- **Module keys.** Besides the base keys, every module brings its own keys with defaults in the `[defaults]` of its `modules/<id>/module.toml` (the original system's values). They are all listed below, with the module that defines them first in "Used by"; set only what you want to change. A test (`tests/test_repo.py`) keeps this page, `uni-os.example.toml` and `examples/alex.toml` in step with the modules. The only module keys the two example files leave out are the four old stuck-note aliases (`heartbeat.inbox_stuck_hours`, `heartbeat.inbox_tap_stuck_hours`, `vm.inbox_stuck_h`, `vm.tap_stuck_h`): they default to `0` (= use `notify.inbox_stale_hours` / `notify.inbox_stale_hours_taps`), and a non-zero value gets an info note from `uni-os config validate`.

Legend for "used by": module ids from [`../modules/README.md`](../modules/README.md); `tools` = the `uni-os` command line; `all` = read by every agent through `_agent/agent-start.md` and the rules.

## `[uni_os]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `version` | text | `"0.1.0"` | Framework version the config was written for. A newer value than the tools produces a warning. | tools |
| `preset` | `"minimal"` \| `"standard"` \| `"full"` \| `"custom"` | `"standard"` | The preset you started from. Used only when `modules.enabled` is empty; then modules that do not support `runtime.laptop_os` (when set) are left out. Lists: `setup/presets.md`, `tools/uni_os/presets.py`. | tools, setup |

## `[student]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `name` | text | **required** | Your name as agents use it ("You are helping Alex ..."). | core, student-model, all |
| `handle` | text | `""` | Optional short id (letters, digits, `-_.`). Shown next to your name on the agents' start page (`_agent/agent-start.md`), in the system handbook and in `me/profile.md`; the cockpit uses it only when `name` is empty. Prose always uses `name`. | core, student-model, cockpit |
| `language` | text | `"English"` | Language agents write notes and replies in. Also the default of `courses.language`. | core, all, cockpit, courses |
| `dictates` | bool | `false` | You often dictate (speech to text): agents infer mangled words from context and ask only when a wrong guess would change something. | core (rules) |
| `pronouns` | text | `""` | Optional. | core, student-model |

## `[university]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `name` | text | **required** | Full name of your university. | core, courses |
| `short` | text | `""` | Abbreviation used in titles. | core, courses, cockpit, inbox-sync, obsidian, roles |
| `programme` | text | `""` | Degree programme, e.g. "BSc Computer Science". | core, student-model, cockpit, courses |
| `lms` | text | `"Moodle"` | Name of your learning platform. | courses, course-files-fetch, quiz-coaching, core, resources, student-model |
| `lms_url` | URL | `""` | Public start page of the platform (never a private link). | courses, course-files-fetch, resources |
| `website` | URL | `""` | University website. | resources |
| `catalogue` | URL | `""` | Course catalogue URL (official list of courses, rooms, exam modes). | courses, resources |
| `recordings` | URL | `""` | Lecture recording portal URL, if any. | courses, resources |

## `[term]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `label` | text | **required** (module fallback: `"this term"`) | Term name, e.g. "Autumn 2026". | core, all, error-logs, cockpit, courses, inbox-sync, obsidian, planning, resources, roles, student-model |
| `timezone` | IANA zone | **required** | E.g. "Europe/Zurich". "Today" and the term week are computed in this zone, also on a server running in UTC. | tools, all jobs |
| `week0_monday` | date (a Monday) | **required** | Monday of week 0. Week *n* starts `week0_monday + 7n` days. | tools (`week`, `new-week`), progress, planning, check-in, daily-prep, heartbeat, cockpit |
| `last_lecture_day` | date or `""` | `""` | Last day with lectures. Also where the derived `weeks` (the term-week table) ends; empty = weeks 0 to 13. | planning, progress, heartbeat, core, courses, lecture-rundowns, check-in |
| `lecture_free_from` | date or `""` | `""` | First lecture-free day. | planning, core, courses |
| `exam_session_start` | date or `""` | `""` | Start of the exam session (used for exam-phase scheduling). | planning, notifications, core, courses, student-model |
| `exam_session_end` | date or `""` | `""` | End of the exam session. | planning, notifications, core, courses, student-model |
| `holidays` | list of `{ name, from, to }` | `[]` | Breaks and public holidays inside the term (`from`/`to` dates, inclusive). | planning, progress, tools (`week` phase), courses |

### Derived term field (computed; do not set)

The tools add this to `[term]` in the resolved config (and in `uni-os.json`), so templates can list the term's weeks. `uni-os config validate` warns when your file sets it (the value would be ignored).

| Field | Example | Meaning | Used by |
|---|---|---|---|
| `weeks` | `[{ number = 0, nn = "00", start = "Mon 14 Sep 2026", start_iso = "2026-09-14" }, ...]` | One entry per teaching week, numbered like `uni-os week` and the week pages: week 0 starts on `week0_monday`, week *n* on `week0_monday + 7n` days. Runs through the week of `last_lecture_day`; while that is empty (or before week 0) it covers weeks 0 to 13 (14 teaching weeks); at most 60 weeks. `nn` is the two-digit number of the week files (`week-07.md`), `start` the Monday as the vault writes dates in text (English names on every system), `start_iso` the same day as `YYYY-MM-DD`. Empty when `week0_monday` is missing. | planning (the generated term-week table in `semester/calendar-and-dates.md`) |

## `[paths]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `vault` | text | `""` | Where the vault lives on the laptop, e.g. `"G:/My Drive/Uni"`. Informational for agents and laptop scripts. The CLI never writes to it implicitly: it takes the vault from `--vault`, `$UNI_OS_VAULT` or the folder you run it in. | core (tools-and-environment), scheduler-local, vault-watch, check-in, daily-prep, lecture-rundowns, quiz-coaching |
| `agent_dir` | folder name | `"_agent"` | The agent area. Changing it is not recommended: every document refers to `_agent/`. Templates under `vault/_agent/` follow it. | tools, all, cockpit, inbox-sync, roles, vm, heartbeat |
| `inbox` | vault-relative folder | `"inbox"` | Drop folder for unsorted files and update notes. Templates under `vault/inbox/` follow it. | core, inbox-sync, obsidian, cockpit, roles, vault-watch, vm, heartbeat |
| `never_open` | list of globs | `["**/private/**"]` | Vault-relative paths that tools and agents never read (doctor's secrets scan skips them). | tools (doctor), handwritten-notes, vault-watch, vm |
| `handwriting_app_data` | vault folder or `""` | `""` | The note app's own sync/data folder if it lives inside the vault: never touched, never read, never listed. | handwritten-notes, vault-watch, vm |
| `handwriting_app_exports` | vault folder or `""` | `""` | The note app's own export folder inside the vault (notebooks not mapped to a course, fallback exports); read-only. | handwritten-notes |

## `[storage]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `provider` | `"google-drive"` \| `"onedrive"` \| `"dropbox"` \| `"icloud"` \| `"syncthing"` \| `"git"` \| `"local"` | `"google-drive"` | How the vault syncs between devices. See `docs/storage.md`. | core, vm, inbox-sync, student-model |

## `[obsidian]`

`area_colours.*` is the `[obsidian.area_colours]` table: colours of the non-course areas. Keep them clearly different from each other and from every course colour.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `enabled` | bool | `true` | You use Obsidian. Presets add `obsidian` (and `cockpit` in Standard/Full) only when true; templates add Obsidian embeds only when true. | core, obsidian, cockpit, tools (presets), student-model, daily-prep, courses, study-pages, roles, inbox-sync |
| `area_colours.me` | hex colour | `"#F6BF26"` | Colour of the student-model area (`me/`): callout, graph group, canvas group. | obsidian |
| `area_colours.progress` | hex colour | `"#00BCD4"` | Colour of `progress/` and the week pages. | obsidian |
| `area_colours.semester` | hex colour | `"#795548"` | Colour of `semester/` (dates, planning). | obsidian |
| `area_colours.deadline` | hex colour | `"#EF6C00"` | Colour of deadline callouts. | obsidian |
| `area_colours.agent` | hex colour | `"#6E7681"` | Colour of the agent area (`_agent/`), muted. | obsidian |
| `area_colours.course` | hex colour | `"#607D8B"` | Colour of the neutral `[!course]` callout and the canvas Courses group. | obsidian |

## `[agent]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `primary` | `"claude-code"` \| `"codex"` \| `"gemini-cli"` \| `"cursor"` \| `"other"` | `"claude-code"` | Your agent. Only Claude Code has been tested. | core, roles, scheduler-local, setup, student-model, vm |
| `permission_posture` | `"bypass"` \| `"accept-edits"` \| `"ask"` | `"accept-edits"` | How much unattended jobs and role sessions may do without asking. `bypass` only on a machine you trust (the original ran its always-on host in bypass mode). | scheduler-local, roles, vm, core |
| `default_model` | text | `""` | Model for ordinary jobs; empty = the agent's default. | roles, scheduler-local, vm, core, inbox-sync, course-files-fetch |
| `heavy_model` | text | `""` | Model for long or hard jobs; empty = default. | roles, scheduler-local, vm, core, exercise-help, lecture-rundowns, quiz-coaching |
| `reply_rules` | list of text | `[]` | Your personal reply rules, written into `_agent/rules.md`. | core, cockpit |
| `skills_dir` | path | `".claude/skills"` | Where your agent reads skills (relative = inside the vault). Setup **copies** `_agent/skills/*` there: a copy, not a link, because Google Drive for desktop has no symbolic links. The copies do not update themselves: copy the skills again after every `render` (it lists changed files under `_agent/skills/`). In Claude Code: `.claude/skills` (project) or `~/.claude/skills` (user). | setup, courses |
| `coordinator_title` | text | `"Uni coordinator"` | Session title of the coordinator, your single entry point. Other sessions address it by this title, so keep it short. | roles |
| `context_refresh_tokens` | integer | `300000` | Recycle a long-lived session (coordinator, any role) once its context passes about this many tokens: it writes its handover and a fresh one boots from the state page. The original measured ~31k tokens for a fresh coordinator against ~550k re-read per turn by an old one. | roles |
| `usage_stop_weekly_pct` | integer | `90` | Unattended side sessions finish the current file, write their handover and stop at this percentage of the weekly usage limit. | roles |
| `usage_pause_5h_pct` | integer | `90` | Unattended side sessions pause at this percentage of the plan's 5-hour usage limit until it resets. | roles |
| `max_helpers` | integer | `2` | Helper agents (subagents) a session may run at the same time. | roles |
| `cli` | command name | `"claude"` | Agent command line used for headless job runs on the laptop (`run_job.py`). Claude Code: `claude`. | scheduler-local |
| `headless_command` | command template | `""` | Headless command for agents other than Claude Code. Placeholders `{model}` `{effort}` `{permission}` `{title}` `{prompt_file}`; without `{prompt_file}` the prompt goes to stdin. Empty = the built-in Claude Code command (`claude -p --permission-mode <mode> --output-format text --name <title> [--model M] [--effort E]`). | scheduler-local |

## `[study]`

Sub-tables (`[study.error_logs]`, `[study.exercise_help]`, `[study.quiz]`, `[study.rundowns]`) are written here as `table.key`.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `formats` | list, subset of `"html"`, `"md"`, `"pdf"` | `["html", "md"]` | Study material formats. The original: interactive HTML page + Markdown twin. | study-pages, lecture-rundowns, exercise-help, quiz-coaching, core, student-model |
| `math` | `"katex"` \| `"mathjax"` \| `"none"` | `"katex"` | Maths renderer in HTML pages. | study-pages, core |
| `chunk_words` | integer | `750` | Words per study-page section (700-800 worked well). | study-pages, lecture-rundowns, core |
| `assistance_default` | `"solo"` \| `"hints-only"` \| `"coach"` \| `"full"` | `"hints-only"` | Default assistance level for graded work; `solo` = the agent gives no help at all. Default of `courses.assistance`. | exercise-help, quiz-coaching, courses, core, error-logs |
| `personal_deadline_rule` | text | `""` | Your rule stricter than official deadlines, e.g. "Sheets released in a week are done by that Sunday". | planning, progress, daily-prep, check-in, core |
| `experiment_weeks` | integer | `2` | Default length of a study or habit experiment (weeks). | experiments |
| `handwriting_app` | text | `""` | Name of your handwriting app, shown in the rules (e.g. "GoodNotes", "Notability"). | handwritten-notes |
| `intuition_first` | bool | `true` | Study pages and rundowns lead with intuition and pictures, then the precise definitions. | study-pages, lecture-rundowns |
| `target_column` | text | `"Personal target"` | Header of the personal-target column of every "Due this week" table (readers find it by the word "target"; the original: "Sunday target"). | progress, planning |
| `pdf_browser` | `"auto"` \| `"chrome"` \| `"edge"` \| `"chromium"` \| path | `"auto"` | Browser `html2pdf.py` uses for PDF export. | study-pages |
| `error_logs.retests` | bool | `false` | Turn on the optional cold-redo retest bank (the original student dropped it). | error-logs, exercise-help |
| `error_logs.retest_items` | integer | `3` | Items per course per weekly retest slot. | error-logs |
| `error_logs.retest_minutes` | integer | `20` | Length of the weekly retest slot (minutes). | error-logs |
| `exercise_help.cold_minutes` | integer | `25` | Cold attempt before the first hint (minutes). | exercise-help |
| `exercise_help.part_cap_minutes` | integer | `45` | Cap per task part; then the missing idea in one line and move on (minutes). | exercise-help |
| `exercise_help.stuck_bug_minutes` | integer | `25` | Programming: stuck longer than this on one bug = ask for the next hint (minutes). | exercise-help |
| `exercise_help.official_solutions_after_attempt` | bool | `true` | Ungraded tasks only: point to the official solution on explicit request after your own attempt (`false` = never). Graded work: never. | exercise-help |
| `quiz.auto_mocks` | bool | `false` | Build a mock quiz with every prep sheet (`false` = mocks on request only). | quiz-coaching |
| `quiz.prep_lead_days` | integer | `4` | The quiz-prep job builds sheets for quizzes within this many days. | quiz-coaching |
| `rundowns.skim_lead_hours` | integer | `1` | A skim is ready at least this many hours before the lecture starts. | lecture-rundowns |
| `rundowns.recall_keys` | bool | `false` | Offer post-lecture recall-key pages (the original student dropped recall tests). | lecture-rundowns |
| `rundowns.skim_courses` | list of course ids | `[]` | Course ids the lecture-skim job writes skims for (the original: only its hardest course). | lecture-rundowns |

## `[[courses]]` (one table per course)

The first six keys are required. Every other key has a default (base defaults, then each enabled module's `[defaults.course]`), so a course needs only what differs. Folder names may contain spaces and `&`.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `id` | lowercase id | **required** | Stable id (`[a-z][a-z0-9_-]*`), unique. Used in the `course:` property and the `uni/<id>` tag of course notes, in the cockpit registry, in `courses.<id>` lookups and in lists of course ids such as `study.rundowns.skim_courses`. (The callout type is the `slug`.) | all course modules |
| `name` | text | **required** | Full course name. | courses, all |
| `short` | text | **required** | Short label for tables and calendar titles. | courses, planning, cockpit |
| `folder` | folder name | **required** | Vault folder of the course (spaces and `&` allowed; unique; not a system folder). | courses, error-logs, handwritten-notes, quiz-coaching |
| `slug` | kebab-case | **required** | File prefix: `<slug>.md`, `<slug>-error-log.md`. Unique. Also the course's callout type, `> [!<slug>]`, coloured by the CSS snippet. | courses, error-logs, study-pages, obsidian |
| `colour` | hex colour | **required** | Lecture colour; CSS snippet, graph groups, canvas, cockpit. | obsidian, cockpit, courses |
| `colour_light` | hex colour or `""` | `""` (computed) | Exercise colour; if empty, a 40 % tint of `colour` is used. | obsidian, cockpit, courses |
| `lecturers` | list of text | `[]` | Optional. Never put real names in shared examples. | courses |
| `lecture_slots` | list of `"Ddd HH:MM-HH:MM"` | `[]` | Weekly lecture times (other text after the time is allowed). | planning, daily-prep, courses, resources, lecture-rundowns |
| `exercise_slots` | list of `"Ddd HH:MM-HH:MM"` | `[]` | Weekly exercise session(s). | planning, daily-prep, courses, resources |
| `sheet_release` | text | `""` | When sheets come out, e.g. `"Thu 12:00"`. | progress, check-in, planning, courses, resources |
| `sheet_due` | text | `""` | When sheets are due, e.g. `"Thu 23:59, one week later"`. | progress, check-in, planning, courses, resources |
| `official_subfolders` | list of folder paths inside the course folder | `["assignments", "assignments/solutions", "script and slides"]` (courses module; base: `[]`) | Folders for official course files (kept under their official names; add-only). `uni-os init` creates one empty folder per entry (the courses module's `[[folders]]`); `render` adds new ones; nothing is ever deleted. | courses, course-files-fetch, vault-watch, resources |
| `error_log_streams` | list of kebab-case | `["main"]` | One error log per stream: one stream gives `<slug>-error-log.md`, several give `<slug>-error-log-<stream>.md`. | error-logs, exercise-help, courses, cockpit |
| `notes` | list of text | `[]` | Course-specific rules agents must follow (page offsets, integrity details). | courses, all course roles, core, daily-prep |
| `assessments` | list of `[[courses.assessments]]` tables | `[]` | The course's graded work, one `[[courses.assessments]]` table each (keys in the next table). Feeds the progress tracker, integrity rules and the bonus engine. | courses, handwritten-notes, quiz-coaching, resources, cockpit, core, daily-prep, exercise-help, planning, progress |
| `aliases` | list of text | `[]` | Extra names the cockpit recognises the course by in titles and table rows (e.g. a platform name); short all-caps codes match case-sensitively. | cockpit |
| `detect` | regular expression or `""` | `""` | Optional raw regular expression that also identifies the course (e.g. `\bE\d+\b` for exercise numbers); `""` = none. | cockpit |
| `assistance` | `"solo"` \| `"hints-only"` \| `"coach"` \| `"full"` | `study.assistance_default` | Assistance level for this course. | exercise-help, quiz-coaching, core, cockpit, courses, daily-prep, handwritten-notes, inbox-sync, planning, roles, error-logs |
| `fetch_sources` | list of URLs | `[]` | Extra official pages of the course beyond `lms_url` and `website` (e.g. a slides server); their hosts become allowed for course-file pick-up. | course-files-fetch |
| `ects` | text or number | `""` | Credits, for the course card. | courses |
| `exercise_group` | text | `""` | Your own exercise group or tutorial, e.g. "group 3". | courses, resources |
| `lms_url` | URL | `""` | This course's page on the LMS (a public course page, never a private link). | courses, resources, course-files-fetch |
| `website` | URL | `""` | Course website outside the LMS, if any. | courses, resources, course-files-fetch |
| `platforms` | list of text | `[]` | Other platforms the course uses, e.g. an online judge or a git server for hand-ins. | courses, resources |
| `recordings` | text | `""` | Whether and when lectures are recorded, e.g. "recorded, usually online the next day". | courses, resources |
| `hand_in` | text | `""` | How work is handed in, e.g. "LMS upload, one per group", "git push", "not handed in". | courses, resources |
| `session_rule` | text | `""` | The key fact for planning: what the exercise session of term week *n* covers (e.g. "discusses sheet n-1, introduces sheet n"). | courses, resources |
| `week_numbering` | text | `""` | How the course numbers its weeks or sheets relative to term weeks, e.g. "LMS 'Week k' = term week k-1". | courses, resources, planning |
| `real_source` | text | `""` | Which documents are ground truth for "what was lectured" (lecture rundowns cite only real sources). | courses, resources |
| `page_offsets` | list of `{ source, rule }` | `[]` | Page-number offsets between printed and PDF pages, e.g. `{ source = "Script (PDF)", rule = "PDF page = printed page + 8" }`. | courses, daily-prep |
| `exam_format` | text | `""` | Exam logistics (length, mode, language, allowed aids), for exam-phase scheduling. | courses, resources, planning |
| `integrity` | text | `""` | The course's official integrity / AI-use rule in one or two sentences; agents follow it on top of `assistance`. | courses, resources, daily-prep |
| `handwritten_folder` | folder path inside the course folder, or `""` | `""` | Folder for handwritten-note PDFs; `""` = `<folder> handwritten`. The name actually used is the derived `handwritten_dir`; `uni-os init` creates that folder when handwritten-notes is enabled. | courses, handwritten-notes, resources, vault-watch |
| `watch_note_subfolders` | list of folder names | `[]` | Extra note subfolders of this course for the vault watcher, e.g. `["code"]`. | vault-watch |
| `language` | text | `student.language` | Language of the course material. | lecture-rundowns, study-pages |

### `[[courses.assessments]]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | text | **required** | E.g. "Weekly exercise sheets". |
| `kind` | `"sheet"` \| `"quiz"` \| `"oral"` \| `"project"` \| `"midterm"` \| `"other"` | `"other"` | Type of graded work. |
| `schedule` | text | `""` | When it happens, free text ("weekly, due Thu 23:59"). |
| `counts_for` | `"bonus"` \| `"grade"` \| `"admission"` \| `"none"` | `"none"` | What it counts towards. |
| `assistance` | `"solo"` \| `"hints-only"` \| `"coach"` \| `"full"` | the course's `assistance` | Overrides the course level for this work (solo-graded work: `"solo"`). |
| `points_max` | number | `0` | Points per instance; `0` = unknown or varies. |
| `dates` | list of `"YYYY-MM-DD"` or `"YYYY-MM-DD HH:MM"` | `[]` | Dated sittings (quizzes, orals) for "N left" counts; a timed one is over once it starts, a date-only one at the end of its day. Optional (list items carry no module defaults). |
| `scope` | text | not set | Optional: what the work covers, in the official wording (e.g. "chapters 1-3 of the script, as announced on the course page"). Shown on the course card, in the course-facts skill and in `resources/course-verification.md`; leave it out when unknown. |

Used by: progress (tracker), check-in, exercise-help and quiz-coaching (integrity: an assessment's `assistance` overrides the course's), courses (course card and course-facts skill, `scope`), resources (`scope`), heartbeat (graded fixtures), cockpit (`dates`, bonus engine). Any other key gets an "unknown assessment key" warning from `uni-os config validate` and `doctor`.


### `[courses.bonus]`

`scheme`, `description`, `max_bonus` and `rule` describe the bonus for humans and agents; the other keys feed the cockpit's bonus rule engine (`modules/cockpit/README.md`) and the progress tracker.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `scheme` | `"none"` \| `"threshold"` \| `"points"` \| `"best-n"` \| `"custom"` | `"none"` | How extra credit works. | courses, resources, cockpit, progress |
| `description` | text | `""` | One line for humans. | courses, cockpit, progress |
| `max_bonus` | number | `0` | Maximum bonus (grade units or percent, as your university counts it). | cockpit, courses, progress |
| `rule` | text | `""` | The exact rule in words; agents and the cockpit read it. | courses, resources, cockpit, progress |
| `threshold` | number (share, `0.8` or `80`) | `0.8` | `threshold` scheme: share of all points that gives the full bonus (`80` also means 80 %). | cockpit, progress |
| `total` | number | `0` | Total points if published; `0` = unknown. | cockpit, progress |
| `total_estimated` | bool | `false` | `true` when `total` is your own estimate. | cockpit, progress |
| `proportional` | bool | `true` | `threshold` / `best-n`: a proportional share below the mark (`false` = all or nothing). | cockpit, progress |
| `full_at` | number | `0` | `points` scheme: points that give the full bonus (`0` = the total). | cockpit, progress |
| `required` | integer | `0` | `best-n` scheme: how many assessments must be passed (`0` = all). | cockpit, progress |
| `unit` | text | `"points"` | Label of the points, e.g. "quiz points". | cockpit, progress |
| `counts` | list of assessment names | `[]` | Names of the assessments whose `dates` count as sittings (`[]` = all that count for the bonus). | cockpit, progress |
| `target` | text | `""` | Short display string for the course card, e.g. "80 % of all points" or "5 / 7". | courses, resources, cockpit, progress |

### Derived course fields (computed; do not set)

The tools add these to every course in the resolved config (and in `uni-os.json`) because templates cannot compute them:

| Field | Example | Meaning |
|---|---|---|
| `colour_rgb` / `colour_light_rgb` | `"30, 102, 245"` | For CSS `--c: r, g, b` callout rules. |
| `colour_int` / `colour_light_int` | `1992437` | For Obsidian `graph.json` colour groups (`rgb: <int>`). |
| `card` | `"AD/ad.md"` | Vault path of the course card. |
| `error_logs` | `[{stream, file, path, title}]` | The course's error-log files (see `error_log_streams`). |
| `error_log_files` | `["ad-error-log.md"]` | Just the file names. |
| `handwritten_dir` | `"AD handwritten"` | The handwritten folder inside the course folder: `handwritten_folder`, or `<folder> handwritten` when that is empty. |

## `[schedule]`

All times are local (`term.timezone`), `"HH:MM"`. Choose your own; the defaults are only the original system's values. Generic checks apply to every key, also module keys: keys named `day` take a day, keys ending in `days` a list of days, values that look like a time must be `"HH:MM"`, values that look like a range must be `"HH:MM-HH:MM"`.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `daily_prep` | list of times | `["17:30", "19:30"]` | Build tomorrow's prep note; later runs check for changes. | daily-prep, cockpit, core, planning, vault-watch, vm, heartbeat |
| `prep_check` | time | `"07:30"` | Morning check of today's prep note against the calendar. | daily-prep, cockpit, core, heartbeat |
| `week_page` | `{ day, time }` | `{ day = "Sun", time = "10:00" }` | Create next week's page (`uni-os new-week`). | check-in, core, planning, progress, heartbeat |
| `check_in` | `{ day, time, every }` | `{ day = "Sat", time = "19:45", every = "week" }` | The end-of-week check-in with you. | check-in, core, planning, progress, heartbeat |
| `heartbeat` | list of times | `["07:50", "13:05", "18:05"]` | Proactive watcher runs (silent unless something matters). | heartbeat, core |
| `heartbeat_days` | list of days | `["Mon", "Tue", "Wed", "Thu", "Fri"]` | Days the heartbeat runs. | heartbeat, core |
| `inbox_sync` | list of times | `["07:15", "13:15", "18:15"]` | Apply update notes waiting in the inbox. | inbox-sync, cockpit, core |
| `study_cutoff` | time | `"19:00"` | No study blocks are planned after this time. | planning, daily-prep, heartbeat, cockpit, student-model |
| `heartbeat_weekend` | list of times | `["09:00", "17:40"]` | Heartbeat runs at the weekend (`[]` = none). | heartbeat, core |
| `heartbeat_weekend_days` | list of days | `["Sun"]` | Weekend days of those runs (the original skipped Saturday because the check-in covered it). | heartbeat, core |
| `inbox_poll_window` | `"HH:MM-HH:MM"` or `"always"` | `"07:00-22:00"` | The poll starts syncs only inside this window (`"always"` = all day). | inbox-sync, core |
| `inbox_poll_every_min` | integer | `10` | How often the inbox poll looks for waiting update notes (minutes). | inbox-sync, core |
| `inbox_poll_min_gap_min` | integer | `60` | At most one inbox sync per this many minutes, fixed runs included. | inbox-sync |
| `lecture_skim` | list of times | `["10:30"]` | Run times of the lecture-skim job (off when installed); pick a time that ends `study.rundowns.skim_lead_hours` before the earliest skimmed lecture. | lecture-rundowns |
| `lecture_skim_days` | list of days | `["Mon", "Wed"]` | Run days of the lecture-skim job (the days of the lectures you skim, or the day before for morning lectures). | lecture-rundowns |
| `day_start` | time | `"08:00"` | Earliest start of a study block. | planning, student-model |
| `weekday_stop` | time | `"18:15"` | Weekday study ends by this time (the original: a hard stop at 18:15). | planning, student-model |
| `focus_minutes` | integer | `70` | Focus span before a break when planning blocks. | planning, student-model |
| `break_minutes` | integer | `10` | Fixed break inside long blocks. | planning, student-model |
| `quiz_prep` | list of times | `["09:00"]` | Run time of the quiz-prep job (off when installed). | quiz-coaching |
| `quiz_prep_dates` | `"YYYY-MM-DD[..YYYY-MM-DD]"` items, `;`-separated | `""` | Run dates of the quiz-prep job, e.g. `"2026-11-15; 2026-11-29"`; `""` = never runs. | quiz-coaching |
| `waiting_on_you` | list of times | `["19:00"]` | When the optional job waiting-on-you writes the student's "what's waiting on you" page (and pushes once if something is due soon); off when installed. | roles |
| `waiting_on_you_days` | list of days | `["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]` | The days that job runs. | roles |
| `vault_watch` | list of times | `["08:17", "13:17", "18:17", "22:17"]` | Daily run times of the vault watcher (Windows); it also runs at logon. | vault-watch, heartbeat |
| `vm_verdict` | `{ day, time }` | `{ day = "Sun", time = "19:30" }` | When the always-on host's weekly performance verdict runs. | vm |

## `[notify]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `provider` | `"ntfy"` \| `"none"` | `"ntfy"` | Phone pushes via ntfy, or none. | notifications, heartbeat, core, vm |
| `ntfy_server` | URL | `"https://ntfy.sh"` | ntfy server (self-hosted works too). | notifications, vm |
| `ntfy_topic_file` | path outside the vault | `"~/.config/uni-os/ntfy-topic"` | File containing only your secret topic. Doctor errors if it points inside the vault, and scans the vault for the topic itself. | notifications, heartbeat, vm, core |
| `max_per_day` | integer | `3` | Push budget per day. | notifications |
| `min_gap_hours` | number | `2` | Minimum hours between pushes. | notifications |
| `quiet_hours` | `"HH:MM-HH:MM"` or `""` | `"21:00-07:30"` | No pushes in this window. | notifications |
| `dedupe_hours` | number | `24` | The same message is not repeated within this time. | notifications |
| `never_all_good` | bool | `true` | Never push "all good" messages; silence is the norm. | notifications, heartbeat |
| `quiet_windows` | list of `{ from, to, reason }` or weekly `{ day, from, to, since, until, reason }`, each with optional `urgent_ok` | `[]` | Extra quiet periods. Dated: `from`/`to` as a date (whole days) or `"YYYY-MM-DD HH:MM"` (`to` may be just `"HH:MM"` on the `from` day). Weekly: `day` (or `days`), `from`/`to` as `"HH:MM"` on the same day, optional `since`/`until` dates. A **hard** window (the default) holds every push, `--urgent` ones too, and the heartbeat's pre-check skips its runs (each skip is still logged): for a short graded fixture such as a timed quiz. `urgent_ok = true` makes it **soft**: ordinary pushes stay held, `--urgent` and `--direct` pushes pass, and the heartbeat keeps running: for a long period such as the exam session. Validation warns about a hard dated window longer than 24 hours and about unknown keys. | notifications, heartbeat |
| `inbox_stale_hours` | integer | `4` | An update note waiting at least this long counts as stuck. The one stuck-note threshold for every sender (inbox poll, heartbeat rules, outcome checks, vm host check). | inbox-sync, heartbeat, notifications, vm |
| `inbox_stale_hours_taps` | integer | `14` | The same for cockpit Done taps (they wait for fixed runs by design). | inbox-sync |
| `title` | text | `"Uni OS"` | Title of every push. | notifications |
| `default_click` | URL or `""` | `""` | Link opened when a push is tapped; `""` = none (Claude Code users: `https://claude.ai/code`). | notifications |
| `require_id` | bool | `true` | Every push must name the problem it is about (`--id`); keep it on. | notifications |
| `block_personal` | bool | `true` | Refuse pushes with mail addresses, links or long numbers in the text; keep it on. | notifications |
| `extra_all_good_patterns` | list of regular expressions | `[]` | More regular expressions for "all good" messages in your language (refused by the gate). | notifications |
| `max_length` | integer | `300` | Longer push texts are cut. | notifications |
| `hold_max_hours` | integer | `24` | Direct host alerts queued during a quiet window and older than this are dropped at release. | notifications |
| `direct_priority` | integer 1-5 | `4` | ntfy priority of direct host alerts. | notifications |

## `[calendar]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `provider` | `"google"` \| `"other"` \| `"none"` | `"google"` | Calendar the agents read/write through your agent's connector. `"other"` = whatever connector you have. | planning, daily-prep, heartbeat, core |
| `courses` | text | `"Courses"` | Calendar with lectures, exercise sessions and graded fixtures. | planning, daily-prep, cockpit, courses, core, student-model |
| `study_blocks` | text | `"Study blocks"` | Calendar for self-study blocks. | planning, daily-prep, cockpit, courses, roles, core, student-model |
| `events` | text | `"Events"` | Non-study events. | planning, cockpit, core, daily-prep, student-model |
| `busy` | text | `"Busy"` | Busy time only (no details read). | planning, cockpit, core, daily-prep, student-model |
| `notation` | text | `"default"` | Block-title notation (`X_`, `(X)`, `[X]`, `OP` ...); `"default"` = the one documented in the planning module. You can define your own. | planning, daily-prep, cockpit |
| `lecture_prefix` | text | `"L:"` | Title prefix of lectures in the Courses calendar (the original used German `V:`). The cockpit always recognises it, on top of `cockpit.lecture_pattern`. | planning, cockpit, core, daily-prep |
| `exercise_prefix` | text | `"E:"` | Title prefix of exercise classes in the Courses calendar (the original used German `U:`). The cockpit always recognises it, on top of `cockpit.exercise_pattern`. | planning, cockpit, core, daily-prep |
| `standing_approval` | bool | `false` | `true`: the planner changes study blocks without asking first and lists every change in the plan's ledger; `false`: it proposes and waits for your yes. | planning, check-in, core |
| `default_location` | text | `""` | Location written into every study block until you name real places (e.g. "Library"). | planning |

## `[runtime]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `laptop_os` | `"windows"` \| `"macos"` \| `"linux"` | `"windows"` | Laptop OS. Laptop scripts are Windows-only (experimental). Presets are resolved for it: `init --preset` and `modules --preset` leave out modules whose laptop part does not support it (vault-watch, course-files-fetch on macOS and Linux) and say so; when this key is not set they use the system of the computer they run on. An explicit module list is installed as given; `enable` and `doctor` then warn about each such module (course-files-fetch included: its pick-up task is Windows-only even though its role runs anywhere). | scheduler-local, vault-watch, course-files-fetch, tools, core |
| `use_vm` | bool | `false` | You run the optional always-on host. | vm, scheduler-local, roles |
| `use_cloud_sessions` | bool | `false` | You use hosted agent sessions (they cannot read laptop files; they write through the inbox). | inbox-sync, roles, core |
| `laptop_scheduler` | `"agent-app"` \| `"os"` \| `"none"` | `"agent-app"` | How agent jobs run on the laptop: `agent-app` (scheduled tasks of the agent's desktop app; Claude Code desktop "Scheduled"), `os` (an OS scheduler runs `run_job.py` with the agent CLI headless; experimental), `none` (nothing runs on the laptop). | scheduler-local |

## `[vm]` (only with the `vm` module)

Only used with the `vm` module (`runtime.use_vm = true`). Host-only values (vault path on the host, agent binary) live in the host's `host.env`, not here.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `provider` | `"gcp"` \| `"home-server"` \| `"other"` | `"gcp"` | Where the host runs. | vm |
| `host_alias` | text | `"uni-vm"` | ssh alias of the host. | vm |
| `project` | text | `""` | Cloud project id (keep it out of shared examples). | vm |
| `zone` | text | `"us-central1-a"` (vm module; base: `""`) | Cloud zone, e.g. `"europe-west6-a"`. | vm |
| `machine_type` | text | `"e2-custom-small-4096"` | Machine size. | vm |
| `linux_user` | text | `""` | User on the host. | vm |
| `remote_control_name` | text | `"Uni (VM)"` | Name shown for the host's remote sessions. | roles, scheduler-local, vm |
| `budget_month` | number | `13` | Monthly budget alert threshold. | vm |
| `budget_currency` | text | `"EUR"` | Currency of the budget. | vm |
| `disk_gb` | integer | `30` | Boot disk size (used in the install commands). | vm |
| `mount_path` | path on the host | `"~/Uni"` | Where the vault appears on the host. | vm |
| `drive_remote` | text | `"uni-drive"` | rclone remote whose root is the vault folder. | vm |
| `repo_url` | URL or `""` | `""` | Public git URL of the framework for `git clone` / `uni-vm update`; `""` = deploy from the laptop. | vm |
| `rc_prefix` | text | `"uni-vm"` | Automatic names of the remote sessions the server spawns. | vm |
| `rc_capacity` | integer | `10` | Remote sessions the server accepts; finished ones count until archived in the app. | vm |
| `rc_chrome` | bool | `true` | Browser bridge for app-started and role sessions (In Claude Code: Claude in Chrome). | vm |
| `rc_update_hour` | hour (0-23) | `4` | Quiet hour in which a self-updated agent binary is picked up. | vm |
| `default_model` | text | `"sonnet"` | Host default model for jobs and roles without their own `MODEL`. | vm |
| `default_effort` | `"low"` \| `"medium"` \| `"high"` \| ... | `"high"` | Host default effort for jobs and roles without their own `EFFORT`. | vm |
| `monthly_credit` | number | `0` | A monthly cloud credit some subscriptions include (counted in the budget view). | vm |
| `snapshot_retention_days` | integer | `21` | Days weekly disk snapshots are kept (install commands). | vm |
| `health_every_min` | integer | `15` | Period of the host self-check (minutes). | vm |
| `history_minute` | minute (0-59) | `40` | Minute of the hourly notes-history snapshot. | vm |
| `history_exclude` | list of globs | `[".obsidian/plugins/**", "**/node_modules/**", "_agent/vm/snapshot.json"]` | More paths the notes history skips (private paths from `paths.never_open` are always skipped). | vm |
| `mem_alert_mb` | integer | `500` | Push when available memory is below this on two checks in a row. | vm |
| `mem_close_jobs_mb` | integer | `700` | Below this, idle job sessions close after 20 minutes. | vm |
| `swapin_alert_rate` | integer | `250` | Swap-in pages per second between two checks that count as thrashing. | vm |
| `disk_alert_pct` | integer | `90` | Disk usage that counts as a problem (percent). | vm |
| `alert_repeat_h` | integer | `3` | One alert (and one "recovered") per problem per this many hours. | vm |
| `big_context_k` | integer | `300` | Doctor flags role sessions above this many thousand tokens of context. | vm |
| `outcome_prep_grace_min` | integer | `60` | Tomorrow's prep note is due this many minutes after the first prep slot. | vm |
| `inbox_stuck_h` | integer | `0` | Alias kept for old configs: 0 = use `notify.inbox_stale_hours`; a non-zero value overrides it for the host's check only. | vm |
| `tap_stuck_h` | integer | `0` | Alias kept for old configs: 0 = use `notify.inbox_stale_hours_taps`; a non-zero value overrides it for the host's check only. | vm |

## `[cockpit]` (only with the `cockpit` module)

The plugin reads the merged config through `_agent/uni-os.json`. The layout and display keys are first-run defaults: afterwards the plugin's own settings win (Settings -> Uni OS cockpit; "Reset" reads these again). Secrets (the assistant's API key, private iCal addresses) live in Obsidian's secret storage on each device, never here. `headings.*` is the `[cockpit.headings]` table.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `enabled` | bool | `true` | Use the Obsidian cockpit plugin. Further keys are defined by the cockpit module (`modules/cockpit/README.md`). | cockpit |
| `layout` | `"focus"` \| `"dashboard"` \| `"agenda"` | `"focus"` | First-run layout of the plugin (later: Settings -> Uni OS cockpit; "Reset" reads these defaults again). | cockpit |
| `default_tab` | `"home"` \| `"week"` \| `"courses"` | `"home"` | First-run start page. | cockpit |
| `open_on_startup` | bool | `false` | Open the cockpit when Obsidian starts (first-run setting). | cockpit |
| `color_mode` | `"accent"` \| `"mono"` \| `"vivid"` | `"accent"` | First-run colour mode of course blocks. | cockpit |
| `prep_switch_hour` | hour (0-23) | `18` | Before this hour the prep card shows today's prep note, from it tomorrow's. | cockpit |
| `prep_warn_after` | time | `"19:30"` | Tomorrow's prep note still missing after this time: orange alert. | cockpit |
| `feed_minutes` | integer | `10` | Live iCal feeds are fetched this often while Obsidian is open. | cockpit |
| `write_snapshot` | bool | `true` | Rewrite the vault's calendar snapshot from the live feeds when they change (one device should do this). | cockpit |
| `stale_days` | integer | `2` | Warn when the calendar snapshot is older than this many days. | cockpit |
| `urgent_hours` | integer | `24` | A deadline closer than this many hours is urgent. | cockpit |
| `day_start` | hour (0-23) | `7` | Start of the timeline and week grid (hour). | cockpit |
| `day_end` | hour (0-24) | `21` | End of the timeline and week grid (hour). | cockpit |
| `status_path` | vault path | `"progress/current-status.md"` | Progress dashboard the cockpit reads. | cockpit |
| `weeks_folder` | vault folder | `"progress/weeks"` | Folder of the week pages. | cockpit |
| `prep_folder` | vault folder | `"semester/prep"` | Folder of the daily prep notes. | cockpit |
| `plans_folder` | vault folder | `"semester/plans"` | Folder of the week plans. | cockpit |
| `overview_path` | vault path | `"courses-overview.md"` | Courses overview page. | cockpit |
| `study_folders` | list of folder names | `["notes", "quiz-prep"]` | Per course, the newest notes from these subfolders are listed. | cockpit |
| `snapshot_path` | vault path or `""` | `""` | Calendar snapshot file; `""` = `<agent_dir>/cockpit/calendar-snapshot.json`. | cockpit |
| `rules_path` | vault path or `""` | `""` | Rules the assistant panel reads first; `""` = `<agent_dir>/rules.md`. | cockpit |
| `prompt_note` | vault path or `""` | `""` | Prompt template of the assistant panel; `""` = `<agent_dir>/cockpit/assistant-prompt.md`. | cockpit |
| `lecture_pattern` | regular expression | `"^(?:V\|L):"` | Courses-calendar titles that are lectures (`"/pattern/flags"` works; `""` switches it off). The default accepts the framework's `L:` and the original's `V:`. | cockpit |
| `exercise_pattern` | regular expression | `"^(?:U\|Ü\|E):"` | Courses-calendar titles that are exercise classes; anything else there is a graded fixture. The default accepts `E:` and the original's `U:`/`Ü:`. | cockpit |
| `optional_pattern` | regular expression | `'^\(\|^OP\b'` | Study blocks that are optional (`(X)` or `OP ...` in the default block notation). | cockpit |
| `deep_pattern` | regular expression | `'\bdeep\b'` | A title matching this marks a deep-work block (case-insensitive). | cockpit |
| `focus_marker` | text | `"FOCUS:"` | In an event description, the lines after this marker are the block's focus. | cockpit |
| `main_marker` | text | `"_"` | In a block title like `LA_ mock A`, the segment with this marker is the block's main subject. | cockpit |
| `done_words` | list of text | `["✓", "done", "submitted", "closed", "handed in", "uploaded", "dropped", "skipped"]` | Due-table Status cells starting with one of these are done (a score `x / y` always counts as done). | cockpit |
| `pending_words` | list of text | `["not reported", "pending", "not recorded"]` | Status cells containing one of these wait for a result: never overdue. | cockpit |
| `no_bonus_words` | list of text | `["none", "no", "feedback only"]` | Bonus cells starting with one of these (or empty) mean no bonus: the row drops off once its date is over. | cockpit |
| `soft_prefixes` | list of text | `["tutorial"]` | Deadline cells starting with one of these are soft dates (never overdue or urgent). | cockpit |
| `soft_markers` | list of text | `["(tentative)"]` | Deadline cells containing one of these are soft dates too. | cockpit |
| `not_released_words` | list of text | `["not released"]` | Rows whose status contains one of these get no Done button. | cockpit |
| `fast_model` | text | `"claude-haiku-5-5"` | First-run model of the assistant panel for quick questions (your own API key, stored in Obsidian's secret storage, never in the vault). | cockpit |
| `strong_model` | text | `"claude-sonnet-5-5"` | First-run model of the assistant panel for harder questions. | cockpit |
| `headings.due` | text | `"Due this week"` | Week-page heading of the due table (headings match by prefix). | cockpit |
| `headings.results` | text | `"Results this week"` | Week-page heading of the results table. | cockpit |
| `headings.notes` | text | `"Notes"` | Week-page notes heading. | cockpit |
| `headings.check_in` | text | `"End-of-week check-in"` | Week-page check-in heading ("End-of-week check-in (Sat)" matches too). | cockpit |
| `headings.next` | text | `"Next 10 days"` | Progress-page heading of the upcoming items (any "Next <n> days" matches). | cockpit |
| `headings.exercises` | text | `"Exercises"` | Progress-page heading "Exercises: done vs. to do" (one `###` per course). | cockpit |
| `headings.self_rating` | text | `"Self-rated"` | Progress-page heading "Self-rated understanding". | cockpit |
| `headings.snapshot` | text | `"Snapshot:"` | The bold `**Snapshot: ...**` line of the progress page. | cockpit |

## `[heartbeat]` (only with the `heartbeat` module)

Tuning knobs of the proactive watcher; the defaults are the original's values. The interview asks about `act_mode` and `ask_mode`; its run times are `schedule.heartbeat*`.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `act_mode` | `"safe"` \| `"full"` | `"safe"` | `safe`: the heartbeat only asks the owning role for moves; `full`: it may act itself. Start with safe. | heartbeat |
| `safe_windows` | list of `{ from, to, reason }` | `[]` | Periods that force safe mode (e.g. a plan freeze). | heartbeat |
| `event_hours` | `"HH:MM-HH:MM"` | `"07:30-20:45"` | When event wake-ups may start an extra heartbeat run. | heartbeat |
| `event_cap` | integer | `2` | Extra event runs per day. | heartbeat |
| `event_near_slot_min` | integer | `45` | No event run when the next regular slot is this close (minutes). | heartbeat |
| `event_min_gap_min` | integer | `30` | No event run this soon after the last run (minutes). | heartbeat |
| `min_memory_mb` | integer | `600` | Skip the run when the host has less free memory (Linux). | heartbeat |
| `grace_min` | integer | `20` | Grace after a job's slot before its missing result counts (minutes). | heartbeat |
| `inbox_stuck_hours` | integer | `0` | Alias kept for old configs: 0 = use `notify.inbox_stale_hours`; a non-zero value overrides it for the heartbeat rules only. | heartbeat |
| `inbox_tap_stuck_hours` | integer | `0` | Alias kept for old configs: 0 = use `notify.inbox_stale_hours_taps`; a non-zero value overrides it for the heartbeat rules only. | heartbeat |
| `checkin_grace_hours` | integer | `16` | Hours after the check-in slot before an empty check-in is flagged. | heartbeat |
| `gap_open_hours` | integer | `24` | A prep gap older than this becomes an outcome push. | heartbeat |
| `result_window_days` | integer | `7` | How long after a graded fixture a missing result stays a question candidate. | heartbeat |
| `snapshot_file` | vault path | `"_agent/vm/snapshot.json"` | The always-on host's machine-readable status (vm module). | heartbeat |
| `snapshot_stale_min` | integer | `40` | The host snapshot is written every 15 min; older than this = red. | heartbeat |
| `jobs_log` | path (`{state}` = state folder) | `"{state}/jobs.log"` | The job runners' run log; `{state}` = the uni-os state folder outside the vault (the laptop scheduler and the VM runner both write it). | heartbeat |
| `flags_dir` | vault folder | `"_agent/logs/flags"` | Where jobs write failure flags. | heartbeat |
| `block_log_glob` | vault glob or `""` | `""` | Optional study-block log tables (e.g. from an experiment), to annotate ended blocks; `""` = none. | heartbeat |
| `non_study_block_prefixes` | list of text | `["L:", "E:", "V:", "U:", "OP", "("]` | Block titles that are not study blocks (lectures, exercise classes, optional blocks); match your block notation. | heartbeat |
| `done_words` | list of text | `["✓", "done", "submitted", "closed", "handed in", "uploaded", "dropped", "skipped"]` | Status words that close a due row (a score `x/y` always does); the done-status vocabulary of module progress, the same list as `cockpit.done_words`. | heartbeat |
| `event_words` | list of text | `["quiz", "timed", "oral", "exam", "midterm", "tutorial", "rehearsal", "test"]` | Due rows that are events: past their time they are "result not recorded", never "overdue". | heartbeat |
| `on_demand_roles` | list of role ids | `["course-files-fetch"]` | Role sessions that are normally off (not flagged as down). | heartbeat |
| `ask_mode` | `"auto"` \| `"session"` \| `"inline"` | `"auto"` | How it asks you a question: `session` (a question session on the always-on host), `inline` (the question is the push), `auto` (session on the always-on host, else inline). | heartbeat |
| `start_job_command` | command template (`{job}`) or `""` | `""` | How this host starts a job now (`{job}` = job id). Empty = the runner's `UNI_JOB_START`, else on the always-on host its systemd unit; with none: no event wake-ups, no re-runs, inline questions only. | heartbeat |
| `rerun_allowed` | list of job ids | `["study-prep-morning-check"]` | Jobs the heartbeat may re-run itself. | heartbeat |
| `outcome_prefix` | text | `"Outcome check: "` | Text in front of outcome-check pushes. | heartbeat |

## `[course_fetch]` (only with the `course-files-fetch` module)

Windows (experimental). The pick-up bridge files official course files from your browser's Downloads into the vault with provenance checks. Re-run its installer after changing `task_name`, `install_dir` or `interval_minutes`.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `task_name` | text | `"Uni OS course pick-up"` | Task Scheduler task name of the pick-up bridge. | course-files-fetch |
| `install_dir` | path outside the vault | `'%USERPROFILE%\Documents\uni-os\course-pickup'` | Scripts, policy and log of the pick-up task, outside the vault so a vault writer cannot change the policy (Documents, not AppData: app-packaged agents may see a redirected AppData). | course-files-fetch |
| `downloads_dir` | path or `""` | `""` | The browser's download folder; `""` = your Downloads known folder. | course-files-fetch |
| `interval_minutes` | integer | `1` | How often the pick-up task looks into the request queue (it exits at once when the queue is empty). | course-files-fetch |
| `extra_hosts` | list of host names (`*.domain` allowed) | `[]` | Allowed download hosts besides the LMS and the course URLs, e.g. the LMS's file host. | course-files-fetch |
| `check_referrer` | bool | `false` | Also accept a download whose referrer host is allowed (weaker than the download host). | course-files-fetch |
| `allowed_types` | list of file extensions | `["pdf", "zip", "txt", "md", "java", "html", ...]` (documents, archives, code; see `modules/course-files-fetch/module.toml`) | File extensions the pick-up accepts; executables are always refused. | course-files-fetch |
| `max_mb` | integer | `50` | Larger files need your OK (`--approved-large`). | course-files-fetch |
| `max_age_hours` | integer | `12` | A file in Downloads older than this is refused (it may be an old version). | course-files-fetch |
| `wait_minutes` | integer | `30` | A request waits this long for its download (or for a half-synced request). | course-files-fetch |
| `date_guards` | list of `{ course or folder, pattern, not_before, reason }` | `[]` | Integrity gates: a file matching `pattern` (regular expression on the file name, case-insensitive) stays out of the vault before `not_before`, checked by the requester and the pick-up. Example: a quiz's solution only after the quiz. | course-files-fetch |
| `request_timeout_min` | integer | `15` | `request_pickup.py`: how long to wait for the laptop's answer. | course-files-fetch |
| `verify_timeout_min` | integer | `5` | `request_pickup.py`: how long to wait for the filed copy to sync to this machine. | course-files-fetch |
| `preferred_language` | text | `"English"` | When a file exists in several languages, take this one. | course-files-fetch |
| `browser_hint` | text | `""` | Which connected browser the agent drives (e.g. a device id) when several are connected. | course-files-fetch |

## `[vault_watch]` (only with the `vault-watch` module)

Windows (experimental). Re-run `register-task.ps1` after changing `schedule.vault_watch`, `task_name`, `install_dir`, `at_logon` or `logon_delay_min`; the script reads the rest on its next run.

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `task_name` | text | `"Uni OS vault watch"` | Task Scheduler task name. | vault-watch |
| `install_dir` | path outside the vault | `'%USERPROFILE%\Documents\uni-os\vault-watch'` | Scripts and state of the watcher, outside the vault. | vault-watch |
| `at_logon` | bool | `true` | Also run at logon. | vault-watch |
| `logon_delay_min` | integer | `5` | Delay of the logon run (minutes). | vault-watch |
| `scopes` | list, subset of `"notes"`, `"sources"` | `["notes", "sources"]` | Which scopes run: `notes` (drift in your notes) and `sources` (new or changed official files). | vault-watch |
| `toast_title` | text | `"Uni OS vault watch"` | Title of the Windows toasts. | vault-watch |
| `toast_summary_over` | integer | `3` | More alerts than this in one run = one summary toast. | vault-watch |
| `push` | bool | `false` | One generic phone push per run with new alerts (needs `notifications`; no file names in pushes). | vault-watch |
| `push_command` | list (command and arguments, `{message}`) | `[]` | Custom push command with `{message}`; `[]` = `uni-os push` through the push gate. | vault-watch |
| `note_root_files` | list of text | `["*.md", "*.canvas", "*.base"]` | Root files that belong to the notes scope. | vault-watch |
| `note_folders` | list of vault folders | `["me", "progress", "semester", "resources", "views", "inbox", "_agent", "_templates"]` | Note folders (recursive) of the notes scope. | vault-watch |
| `course_note_subfolders` | list of folder names | `["notes", "reference", "quiz-prep"]` | Note subfolders inside every course folder. | vault-watch |
| `churn` | list of globs | job logs, applied inbox notes, the watcher's own files, pick-up queue, heartbeat state, VM status, `uni-os.json`, the manifest (see `modules/vault-watch/module.toml`) | Paths that change all the time and are ignored by the notes scope (logs, applied inbox notes, state files). | vault-watch |
| `never_list` | list of globs | `["private", "*/private"]` | Never enumerated, not even file names (privacy); `paths.never_open` and `paths.handwriting_app_data` are added. | vault-watch |
| `source_top_dirs` | list of vault folders | `[]` | Extra top-level folders with official material. | vault-watch |
| `quiet_dirs` | list of vault folders | `[]` | App-output areas: changes are logged only, never alerted. | vault-watch, handwritten-notes |
| `quiet_patterns` | list of globs | `["*handwritten*"]` | First-level course subfolders that are app-output areas (also `course.handwritten_folder`). | vault-watch |
| `frozen_dirs` | list of vault folders | `["z_archive", "archive"]` | Archives (vault-relative, e.g. `"AD/z_archive"`): any change alerts. | vault-watch |
| `ignore_top_dirs` | list of folder names | `[]` | Top-level folders that may exist without a "not watched" alert. | vault-watch |
| `conflict_patterns` | list of globs | `["* (1)*", "*conflicted copy*", "*.sync-conflict-*", "Copy of *"]` | File names of sync conflict copies. | vault-watch |
| `half_mount_ratio` | number (0-1) | `0.2` | Half-mount guard: fewer files than this share of the last snapshot = the drive is only half there; the run stops quietly. | vault-watch |
| `half_mount_min_files` | integer | `50` | The half-mount guard applies only when the last snapshot had at least this many files. | vault-watch |
| `alert_prune_days` | integer | `120` | Forget once-only alert keys after this many days. | vault-watch |
| `group_new_over` | integer | `3` | More new files than this in one folder become one alert. | vault-watch |
| `log_max_paths` | integer | `20` | At most this many paths per log line. | vault-watch |
| `write_inventory` | bool | `true` | Write `_agent/vault-watch/sources-inventory.tsv`. | vault-watch |
| `stale_update_hours` | integer | `24` | An update note left in the inbox longer than this alerts (with `inbox-sync`). | vault-watch |
| `update_note_patterns` | list of globs | `["*-update.md"]` | Names of update notes in the inbox. | vault-watch |
| `prep_watchdog` | bool | `true` | Alert when today's or tomorrow's prep note is missing (with `daily-prep`). | vault-watch |
| `prep_folder` | vault folder | `"semester/prep"` | Folder of the prep notes. | vault-watch |
| `prep_pattern` | file pattern (`{date}`) | `"prep-{date}*.md"` | Prep note names (`{date}` = the day). | vault-watch |
| `prep_morning` | `"HH:MM-HH:MM"` | `"08:00-12:00"` | Window in which a missing prep note for today alerts. | vault-watch |
| `prep_evening_from` | time | `"21:00"` | From this time a missing prep note for tomorrow alerts. | vault-watch |

## `[modules]`

| Key | Type | Default | Meaning | Used by |
|---|---|---|---|---|
| `enabled` | list of module ids | `[]` | Modules to install; dependencies are added automatically and `core` is always included. Empty = the preset in `uni_os.preset`. `uni-os enable` / `disable` edit this list (comments are kept). | tools |

## `job.conf` schedule keys (not config keys)

Every job of a module is `_agent/jobs/<job>/job.conf` in the vault (shell-style `KEY="value"` lines; [docs/file-formats.md](../docs/file-formats.md#jobconf) has every key). Its schedule is rendered from the `[schedule]` keys above. Both host runners (the laptop scheduler of `scheduler-local` and the always-on host of `vm`) and `uni-os jobs` / `doctor` read these keys the same way:

| Key | Format | Default | Meaning |
|---|---|---|---|
| `SLOTS` | `"HH:MM, HH:MM"` (local times) | `""` | Fixed run times. |
| `EVERY_MIN` | whole minutes: `1`-`59`, or a multiple of 60 up to `1440` | `""` | Fixed polling interval for cheap check jobs (e.g. `inbox-poll`, `heartbeat-watch`). The always-on host uses it only when `SLOTS` and `SCHEDULE` are empty; the laptop scheduler adds one repeating trigger for it. |
| `DAYS` | comma list of `Mon` ... `Sun`; ranges `Mon..Fri` or `Mon-Fri` (both runners accept both, and a range may wrap: `Sat..Mon`) | every day | Days on which `SLOTS` and `EVERY_MIN` apply. Empty means every day. `doctor` reports unknown day names as errors; ranges are fine. |
| `DATES` | `YYYY-MM-DD` or `YYYY-MM-DD..YYYY-MM-DD`, `;`-separated | `""` | Optional date limits or one-off dates. |
| `SCHEDULE` | raw systemd `OnCalendar` strings, `;`-separated | `""` | Overrides `SLOTS`/`DAYS`/`DATES` on the always-on host. |

Change a time in `uni-os.toml`, run `uni-os render`, then re-install the job on its host (the module README says how).

## Template-only values (not config keys)

Available in every template besides the config:

| Value | Meaning |
|---|---|
| `generated.date`, `generated.version` | Render date (ISO; `--date`, `$UNI_OS_TODAY` or `$SOURCE_DATE_EPOCH` make it reproducible) and framework version. |
| `generated.date_long` | The render date as the vault writes dates in text, `Ddd D Mon YYYY` (`Sat 7 Nov 2026`), with English day and month names on every system. For seeded log lines such as the first change-log entry of the system handbook. |
| `generated.modules` | Enabled modules: `{id, name, tier, summary, requires, recommends, obsidian, os, runtime, jobs, roles, skills, config_keys, readme}`. |
| `generated.roles` | Installed roles: `{id, module, title, runtime, file}`. |
| `generated.jobs` | Installed jobs: `{id, module, title, kind, slots, every_min, days, session, runtime, default_mode, dir}`. |
| `generated.skills` | Installed skills: `{id, module, name, description, dir}`. |
| `modules.<id>` | `true` when module `<id>` is enabled (never an error). |
| `course`, `item`, `error_log` | Bound inside `{{#each courses}}`, other `{{#each}}` loops, per-course / per-error-log file paths, and module `[[folders]]` paths (`item` = one entry of the list named by `each`). |
| `week.*` | Reserved for `uni-os new-week`: `number`, `nn`, `monday`, `sunday`, `label`, `status`, `previous_nn`, `next_nn`. |

## Environment variables

| Variable | Meaning |
|---|---|
| `UNI_OS_VAULT` | Default vault for every command. |
| `UNI_OS_MODULES_DIR` | Alternative module catalogue (tests, module development). |
| `UNI_OS_TODAY` | Pretend today is this date (`YYYY-MM-DD`): tests and reproducible runs. |
| `SOURCE_DATE_EPOCH` | Standard reproducible-build timestamp; sets `generated.date` if `UNI_OS_TODAY` is not set. |
