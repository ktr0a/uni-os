---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Conventions: how to keep this vault up to date

For every agent working on {{student.name}}'s studies, and for {{student.name}}. The short version: **this vault is the primary store. Whenever something new and even slightly useful comes up, put it in the right file in the same turn. Don't wait to be asked.**

## 1. Source of truth, in order
1. What {{student.name}} says now (except that the integrity rules in `rules.md` are never overridden in the moment).
1. **For course facts** (dates, rhythms, rooms, rules that decide points): the official course pages ({{university.lms}} course page and its announcements, course websites), then the course catalogue. They beat this vault's course{{#if modules.courses}} cards and the course{{/if}} notes: when they disagree, correct the vault file with the date and the source{{#if modules.resources}} (and a line in `resources/course-verification.md` when it came up in a verification pass){{/if}}.
1. **For everything else:** the live files in this vault (the newest `updated` date wins when two disagree).
{{#if modules.courses}}
1. The course-facts skill (`_agent/skills/course-facts/`). When an official page or {{student.name}} corrects it, the correction goes on the course card, and the card wins.
{{/if}}
1. `_agent/archive/` and{{#if modules.courses}} `z_archive/`{{/if}}: frozen snapshots and outdated copies, never the source for current status.

## 2. Two audiences, two areas
- **Human area** (everything outside `_agent/`): written for {{student.name}} to read{{#if obsidian.enabled}} in Obsidian{{/if}}. Short, clear, linked, tables over prose. Agents read it too.
- **Agent area** (`_agent/`): instructions, protocols, routing, tool notes, job definitions, operational state, logs, raw exports. {{student.name}} doesn't need to read it.
- Don't put agent instructions into human notes beyond a one-line pointer. Don't hide facts {{student.name}} needs inside `_agent/`.

## 3. Where things go
`<Course>` is a course folder at the vault root and `<c>` its file prefix:

<!-- uni-os:begin courses -->
| Course | `<Course>` | `<c>` |
|---|---|---|
{{#each courses}}
| {{course.name}} ({{course.short}}) | `{{course.folder}}` | `{{course.slug}}` |
{{/each}}
<!-- uni-os:end courses -->

<!-- uni-os:begin routing -->
<!-- Generated from the enabled modules. Add your own rows to section 3b, not here (see "Generated regions" below). -->
| You learned... | Put it in | How |
|---|---|---|
| A rule for how agents should help | `_agent/rules.md` | under the matching heading, date in brackets, {{student.name}}'s words quoted; never delete a replaced rule, add "(Since <date>: ...)" to it |
| A setting: a schedule time, a calendar name, a notification limit, a course's help policy, a new course | `_agent/uni-os.toml` (the config) | edit the value, then re-render (`python tools/uni_os.py render` from the framework) and say what changed; scheduled jobs and tasks may need re-installing (see `_agent/system-handbook.md`) |
| A tool or environment trick, a connector quirk | `_agent/tools-and-environment.md` | append a dated bullet under the right heading |
| A new component, job or role, or one changed where it runs | `_agent/system-handbook.md` | add or fix its row; append a line to the change log at the bottom |
| Something you can't place yet | `inbox/` | name it `YYYY-MM-DD_short-topic.ext`; whoever processes the inbox sorts it (rules in `inbox/inbox.md`) |
{{#if modules.student-model}}
| Something about {{student.name}}: identity, goals, tools, shorthand, course contacts | `me/profile.md` | edit in place, date the change, keep the previous value inline ("Before: ... (date)") |
| How {{student.name}} learns, what works per course, study-page preferences | `me/learning-style.md` | same |
| Energy curve, focus span, sleep or stop times, week shape, places that work | `me/rhythm-and-habits.md` | same; strike through retired advice instead of deleting it |
| A self-rating of understanding ("I'd say 60 % in LA") | `me/profile.md` "Self-rated understanding"{{#if modules.progress}} **and** `progress/current-status.md` **and** a dated line in `progress/tracker-log.md`{{/if}} | keep the earlier ratings in the Note cell; mark mid-week ratings "provisional" |
| A recurring mistake pattern (seen across several error-log rows or across courses) | `me/weak-spots.md` | one pattern line with its fix and source links; the dated rows stay in the error log |
{{/if}}
{{#if modules.experiments}}
| A habit experiment (sleep, evenings, phone; proposal, rule change, nightly measure, review) | `me/habits-experiments.md` | one change at a time, two weeks, one simple measure; rule changes dated with the reason; log rows appended |
| A study-method experiment (a new week layout or technique, tried for a fixed period) and its per-block log | `semester/experiments/` (plan + `...-block-log.md`, method in its `README.md`) | one block-log line per study block, written only by the session that owns the experiment; other sessions send it their block report |
{{/if}}
{{#if modules.progress}}
| A result, a score, bonus points, a sheet done or not done | the four places in `_agent/progress-tracking.md` section 1: `progress/current-status.md` (state), a dated line in `progress/tracker-log.md`{{#if modules.courses}}, the course card's properties `bonus_banked` / `bonus_target` / `next_bonus`{{/if}}, and the week page's Status cell plus a line under "Results this week" | all of them in the same turn; edit the status in place; append to the log; keep `x / y` numbers and dates like `Tue 3 Nov 23:59` in that shape (dashboards parse them) |
| What happens this week; the end-of-week check-in | `progress/weeks/week-NN.md` (NN two digits) | create it from `_templates/week-page.md`; set `status: current` on the new week and `status: done` on the old one; status cells cite their evidence and keep the previous value ("done (Tue 3 Nov, {{university.lms}} 'Submitted'). Before: open") |
{{/if}}
{{#if modules.courses}}
| A course fact: rhythm, deadline, room, assessment rule, bonus rule, help policy, source, page offset | `<Course>/<c>.md` (the course card) | edit in place; say when it corrects an older fact; mark estimates "(est.)". A fact that is also a config key (a graded stream, an assistance level, slots, the session rule, a page offset) changes in `_agent/uni-os.toml` too, then render: the card's graded-streams table and the per-course tables of `courses-overview.md` are generated from it |
| A lecture happened (what was covered) | `<Course>/<c>.md` "Lecture log"; optionally a lecture note from `_templates/lecture-note.md` in `<Course>/notes/` | one line per lecture; only {{student.name}}'s word or the slides actually reached say where it stopped |
| A lecture transcript (from a recorder or dictation app) | `<Course>/notes/<c>-lecture-<ddd><d><mon>-transcript.md` (day not zero-padded), e.g. `<c>-lecture-tue3nov-transcript.md` | wording unchanged, `[mm:ss]` timestamps; check coverage against the recording length (connectors can return partial text); one row in the card's file table and a Lecture log line |
| A parked task, a to-do for later | `<Course>/backlog.md` | append a row with why it was parked and an estimate; strike done rows, don't delete them |
| An official course file (sheet, script, slides, solution) | the course folder's official subfolders (listed on the course card) | keep the official file name; agents may add a newly downloaded file, never rename, move or delete existing ones; link it from the card |
| A newer version of an official file that is already in the vault | the official subfolder, after the old copy moved to `z_archive/<course folder>-outdated-YYYY-MM-DD/` (vault root) | only with {{student.name}}'s OK: move the old copy there under its own name (never delete it), then add the new one under the official name; one line on the card ("Replaced <date>: ...") |
| Reference material (course guide, topic plan, script index) | `<Course>/reference/` | one row in the card's file table |
{{/if}}
{{#if modules.error-logs}}
| A mistake, a point of confusion, "log this error" | `<Course>/<c>-error-log.md` (one file per stream if the course has several) | append a table row in the format at the top of that log (section 7); never edit old rows (corrections are new rows); at the second error of the same family add a pattern under "Patterns to watch"{{#if modules.student-model}} and mirror it as one line in `me/weak-spots.md`{{/if}}; never log `solo` work |
{{/if}}
{{#if modules.study-pages}}
| A study page, summary, rundown, cheat sheet | `<Course>/notes/` | formats per `study.formats` ({{study.formats}}); named `<c>-<what>-<kind>` (course slug first, kind word last, e.g. `<c>-<topic>-study-page`), lowercase kebab-case; one row in the course card's "In this folder" table |
{{/if}}
{{#if modules.quiz-coaching}}
| A mock quiz, a quiz checklist, a quiz review extract | `<Course>/quiz-prep/` (saved review pages in `quiz-prep/raw/`) | label official vs invented questions; one row in the card's file table |
{{/if}}
{{#if modules.handwritten-notes}}
| Handwritten notes (tablet app exports) | the course's handwritten folder (default `<Course>/<Course> handwritten/`) | written only by the app; agents read and link, never write, move or delete there |
{{/if}}
{{#if modules.planning}}
| A key date or deadline | `semester/calendar-and-dates.md`{{#if modules.progress}} (+ the "Next 10 days" section of `progress/current-status.md` if it falls within 10 days){{/if}} | edit the tables; prune past dates at the check-in |
| A week plan or a calendar restructure | `semester/plans/week-NN-plan.md`; principles and block notation in `semester/planning-system.md` | new file per week; the calendar wins over the plan file when they disagree |
| A study-approach decision | `semester/study-approach.md` | edit in place, dated, with the reason |
{{/if}}
{{#if modules.daily-prep}}
| Tomorrow's study material per block | `semester/prep/prep-YYYY-MM-DD.md` (revisions `-r2`, `-r3`: the highest wins) | written only by the prep jobs: a new file per run, never edited, moved or deleted by hand; to change it, ask for a re-run |
{{/if}}
{{#if modules.resources}}
| A useful website, an assistant's or TA's page, a third-party resource | `resources/ta-websites-log.md` (method and log) or `resources/sources-and-links.md` (the registry) | append; one language per resource where possible |
| A course fact checked against the official page | `resources/course-verification.md` | claim, check, result, date; then fix the course card |
{{/if}}
{{#if modules.roles}}
| A role, session or routine changed (new role, new owner of a file, new trigger) | the role's brief `_agent/roles/<role>.md`; for a role or route of your own also the "added in this vault" rows in `_agent/roles/README.md` | edit in place; every duty names its trigger; the generated routing and roles tables there follow the modules on render, so don't edit between their markers |
| A request for another role | that role (through the coordinator), not its files | say in your reply what should go where; don't do another role's work yourself |
{{/if}}
{{#if modules.inbox-sync}}
| A change to an existing file, made by a writer that can only create files | `inbox/YYYY-MM-DD_HHMM_<sender>-update.md` (an update note) | quote every line to replace exactly as it stands now; the inbox-sync job applies it or parks it (section 9) |
{{/if}}
{{#if modules.heartbeat}}
| "Stop telling me about X" | `_agent/heartbeat/requests.md` | append one dated line; the watcher reads it before every run |
{{/if}}
{{#if modules.cockpit}}
| Cockpit settings, feeds, layout | the cockpit plugin's settings in Obsidian (keys and feed URLs only in Obsidian's keychain) | never put feed URLs or keys into a vault file |
{{/if}}
{{#if modules.course-files-fetch}}
| A newly fetched official file | the course's official subfolder, through the pick-up bridge | add-only, never overwrite; a changed server copy is logged, not replaced |
{{/if}}
{{#if modules.vm}}
| State of the always-on host | `_agent/vm/status.md`, `_agent/vm/performance.md` | written by the host's own tools; read only |
{{/if}}
| A new kind of thing that has no row yet | the closest folder | section 10: create it there, index it, give it properties, add a row to section 3b |
<!-- uni-os:end routing -->

### 3b. Rows added in this vault
Rows that agents or {{student.name}} added for new kinds of things (section 10). Nothing generated goes here.

| You learned... | Put it in | How |
|---|---|---|

### Generated regions
Parts of this file (the course table and the routing table), `README.md`, `where-to-find-what.md`, `_agent/system-handbook.md` and `_agent/rules.md` (the per-course integrity table and the course-specific rules from the config){{#if modules.courses}}, the per-course tables of `courses-overview.md` and the graded-streams table of each course card{{/if}}{{#if modules.planning}}, the weekly grid, release rhythm and graded-items tables of `semester/calendar-and-dates.md`{{/if}}{{#if modules.roles}}, and the tables in `_agent/roles/README.md`{{/if}} sit between two marker lines, `<!-- uni-os:begin <name> -->` and `<!-- uni-os:end <name> -->`: they are generated from the config and the enabled modules. `uni-os render` (run from the framework: `python tools/uni_os.py render --vault "<vault>"`; `uni-os enable` and `disable` do the same) keeps them current:
- A file nobody edited since it was installed is re-rendered whole.
- A file you or an agent edited (a row in 3b, a change-log line) keeps every line outside the markers; render replaces only the text between each pair of markers with a fresh rendering and lists the file as "refreshed".
- If a marker is missing, renamed, duplicated or broken, render changes nothing in that file and lists it as "skipped" with the reason; `uni-os doctor` warns about it too. Fix the marker lines (copy them from a scratch render: `python tools/uni_os.py init --config "<vault>/_agent/uni-os.toml" --vault "<scratch folder>" --force`), then render again.
- `python tools/uni_os.py render --vault "<vault>" --dry-run` shows which regions would change, without writing.

Never edit inside a region (render overwrites it) and never delete or rename the marker lines; put your own rows in the sections meant for them, outside the markers.

## 4. Properties (frontmatter) and note types
Every new note starts with a properties block. Common keys:

| Key | Values | Notes |
|---|---|---|
| `type` | one value from the table below | views, dashboards and jobs filter on it, so never invent a near-duplicate |
| `course` | a course id: {{#each courses}}`{{course.id}}` {{/each}} | only on course notes |
| `audience` | `me`, `agent` or `both` | nothing else (no "user" or "claude") |
| `updated` | `YYYY-MM-DD` | bump it on every edit |
| `tags` | `uni/<course id>` or `uni/<area>`, plus a flat tag such as `study-page`, `error-log` | hierarchical `uni/...` tags, lowercase |

Note types in this vault (a module adds its own types to its page):

| `type` | Used for | From |
|---|---|---|
| `home` | `Home.md` | core |
| `overview` | `where-to-find-what.md`{{#if modules.courses}}, `courses-overview.md`{{/if}} | core{{#if modules.courses}}, courses{{/if}} |
| `agent` | files in `_agent/` | core |
| `inbox` | `inbox/inbox.md`, hand-made inbox notes | core |
| `lecture-note` | lecture notes from `_templates/lecture-note.md` | core |
| `study-page` | study pages and their Markdown twins (property `kind`: teaching-page, skim, rundown, recap, summary, cheat-sheet, walkthrough, ...; twins also carry `source_html` and `converted`) | core{{#if modules.study-pages}}, study-pages{{/if}} |
| `reference` | course guides, topic plans, script indexes | core{{#if modules.courses}}, courses{{/if}} |
{{#if modules.student-model}}
| `me` | the student model in `me/` | student-model |
{{/if}}
{{#if modules.courses}}
| `course` | course cards `<Course>/<c>.md` (properties `bonus_banked`, `bonus_target`, `next_bonus` are parsed) | courses |
| `backlog` | `<Course>/backlog.md` | courses |
{{/if}}
{{#if modules.error-logs}}
| `error-log` | `<Course>/<c>-error-log*.md` | error-logs |
{{/if}}
{{#if modules.quiz-coaching}}
| `quiz-prep` | files in `<Course>/quiz-prep/` | quiz-coaching |
{{/if}}
{{#if modules.progress}}
| `status`, `log`, `week` | `progress/current-status.md`, append-only logs, week pages (properties `week`, `start`, `end`, `status`: `upcoming`, `current` or `done`) | progress |
{{/if}}
{{#if modules.planning}}
| `plan` | `semester/plans/week-NN-plan.md` and other plans | planning |
{{/if}}
{{#if modules.daily-prep}}
| `prep` | `semester/prep/prep-YYYY-MM-DD[-rN].md` | daily-prep |
{{/if}}
{{#if modules.roles}}
| `role` | role briefs in `_agent/roles/` | roles |
| `digest` | `waiting-on-you.md` at the vault root (written by the optional job waiting-on-you) | roles |
{{/if}}
| `job` | job definitions in `_agent/jobs/` (when a job carries a Markdown note) | modules with jobs |

## 5. {{#if obsidian.enabled}}Obsidian rules (this vault is an Obsidian vault){{else}}Markdown rules{{/if}}
- **Links:** standard Markdown links with **relative paths** (`[text](../<Course>/<c>.md)`), so they work in Obsidian, on the synced drive, on GitHub and for agents. Wrap paths that contain spaces or `&` in angle brackets: `[Script, p. 12](<../A&D/A&D Plan & Script/script.pdf#page=14>)`.{{#if obsidian.enabled}} Embeds may use `![[note#Heading]]` or `![[View.base]]`.{{/if}}
- **Unique file names** across the vault's notes: don't create new notes called `README.md`, `log.md`, `notes.md` or `error-log.md` (the folder READMEs that Uni OS installs are the only exception). Prefix with the course or topic, lowercase-kebab-case: `<c>-lecture-mon26oct-<topic>-skim.md`. Source files keep their official names; several folders hold files with the same name (e.g. `week01.pdf`), so link those by relative path, never by bare name.
- **Source PDFs:** link with a relative path in angle brackets plus `#page=N` where useful. {{#if obsidian.enabled}}Embed a page with `![[file.pdf#page=2]]` only when the name is unique. {{/if}}On a streaming drive a PDF downloads on first open.
- **Templates** live in `_templates/`: copy their properties when creating notes by hand.{{#if obsidian.enabled}} In Obsidian: command "Templates: Insert template".{{/if}}
- **Maths:** `$...$` and `$$...$$`. Don't use `\(...\)` in Markdown.
{{#if obsidian.enabled}}
- **Callouts:** `> [!note]`, `> [!warning]`, `> [!tip]`, collapsible `> [!info]-`.{{#if modules.obsidian}} Custom ones styled by the vault's CSS snippet: one per course ({{#each courses}}`[!{{course.slug}}]` {{/each}}), `[!course]` (neutral), `[!me]`, `[!week]`, `[!semester]`, `[!deadline]`, `[!agent]`, and `[!grid]` (puts nested callouts side by side).{{/if}}
{{#if modules.obsidian}}
- **Colours:** each course has one colour (config `courses.colour`), used for its callout, its folder in the file list, its graph group and its node on the vault map. Other areas have their own clearly different colours. Never introduce a colour similar to an existing one.
{{/if}}
- **`Home.md`** is the dashboard. Most of it is computed from views and embeds, so keeping properties and the status page right keeps Home right. Edit `Home.md` itself only for new tiles or links.
- **Move or rename notes inside Obsidian** (or through its command line), so links update. A move on the drive, through a connector or with a shell command does not update links.
- Don't edit `.obsidian/` unless {{student.name}} asks.
{{/if}}
- **Parsed formats are contracts.**{{#if modules.cockpit}} The cockpit plugin and the jobs{{else}} Dashboards and jobs{{/if}} parse certain headings, table columns and value shapes{{#if modules.progress}} (the week page's "Due this week" table, `progress/current-status.md` sections such as "Next 10 days"){{/if}}{{#if modules.courses}} and the course-card properties{{/if}}{{#if modules.daily-prep}} and the prep notes{{/if}}. Keep headings, column names, `x / y` numbers and dates like `Tue 3 Nov 23:59` exactly as they are. Each module page names its contract.

## 6. How to write
- **{{student.language}}** in every file (local-language course terms in brackets are fine). No personal sign-off tokens inside files.
- **Absolute dates** with the weekday ("Mon 26 Oct 2026"), plus the term week where it helps. Never "yesterday" or "tomorrow" in a file.
- **Say where a fact comes from** and mark estimates "(est.)" and inferences "(inferred)".
- **{{student.name}}'s words, quoted:** decisions in state pages, rules and briefs carry the quote and the date. That settles later misreadings.
- **No secrets:** no email addresses, passwords, tokens, API keys, private calendar addresses or notification topics.
- **Integrity in files:** never store finished solutions or code for graded work, and never transcribe, summarise or store {{student.name}}'s own `solo` work (handwritten or typed). Coaching notes, error logs and technique explanations are fine. The policies are in `rules.md`.
- **One subject per file.** Update the existing file instead of creating a near-duplicate. Bump `updated` when you edit.
- **Status cells cite their evidence and keep the previous value:** `done 4/4 (Mon 2 Nov 10:05, screenshot). Before: open`.

## 7. Logs: append, don't rewrite
- Append-only files: {{#if modules.progress}}`progress/tracker-log.md`, {{/if}}{{#if modules.error-logs}}every error log, {{/if}}{{#if modules.resources}}`resources/ta-websites-log.md`, {{/if}}{{#if modules.experiments}}the block and experiment logs, {{/if}}{{#if modules.inbox-sync}}`_agent/logs/inbox-sync-log.md`, {{/if}}the change log in `_agent/system-handbook.md`, and every file under `_agent/logs/`.
- **Fix a wrong entry by adding a correction line** ("Correction to the row of Tue 3 Nov: ..."), never by editing the old one.
{{#if modules.error-logs}}
- **Error-log rows:** `| Date | Where | What went wrong | Correct idea | Source |`, with the column rules and source tags (`[script]`, `[slides]`, `[task]`, `[derived]`, `[user note]`, ...) written at the top of every log. The correct idea is the general rule, never the full solution of a current graded task. Note {{student.name}}'s state if they mention it (tired, rushed, frustrated): errors made under fatigue weigh differently. Steps: the `log-error` skill in `_agent/skills/`.
{{/if}}
- `_agent/archive/` is frozen. To retire a live file, move it there with the date in its name, put "FROZEN on <date>; live file: <path>" at its top, and fix the links.{{#if modules.courses}}
- `z_archive/` (vault root) holds official course files that a newer version replaced, one folder per replacement: `z_archive/<course folder>-outdated-YYYY-MM-DD/`, files under their official names. It is a source folder: never edit or delete anything there. This is the only place outdated official files go.{{/if}}
- When the folder layout changes, keep a path map (`_agent/old-path-map.md`: `| Old path | New path |`) instead of rewriting old logs, because append-only logs keep old paths forever.

## 8. Notes, sources and app-owned folders
Every folder in the vault is one of three kinds. Agents treat them differently:

| Kind | What | Agents may |
|---|---|---|
| **Notes** | `Home.md`, `README.md`, `where-to-find-what.md`, `inbox/`, `_agent/`, `_templates/`{{#if modules.student-model}}, `me/`{{/if}}{{#if modules.progress}}, `progress/`{{/if}}{{#if modules.planning}}, `semester/`{{/if}}{{#if modules.resources}}, `resources/`{{/if}}{{#if modules.obsidian}}, `views/`{{/if}}{{#if modules.courses}}; in each course folder the top-level `.md` files plus `notes/`, `reference/`{{#if modules.quiz-coaching}}, `quiz-prep/`{{/if}}{{/if}} | edit per this file (re-read first, small edits) |
| **Sources** | {{#if modules.courses}}the official subfolders in each course folder (listed on the course card){{#if modules.handwritten-notes}}, the handwritten folders{{/if}}, `z_archive/`, {{/if}}anything {{student.name}} marks as a source | read and link; **add** a new file (official files only); never rename, move, edit or delete |
| **App-owned or private** | folders written by another app (e.g. a note app's data folder), any private folder, `.obsidian/` | never open private folders; never write, move, rename or delete anything (deleting an app's file can delete the thing on the device) |

Record every app-owned or private folder of this vault here, with its rule, when it appears.{{#if modules.vault-watch}} The vault watch checks the notes for drift and the source folders for new arrivals; it reports, it never fixes.{{/if}}

## 9. How to reach the vault
The vault is a synced folder (storage: `{{storage.provider}}`). Changes made on one machine reach the others through sync, usually within a minute.

**On the laptop** (local agent app or CLI): read and write the synced folder directly. {{#if obsidian.enabled}}Obsidian opens the same folder. {{/if}}Quote paths: they may contain spaces and `&`.

{{#if runtime.use_cloud_sessions}}
**Cloud sessions** (hosted agent sessions with a storage connector) can read every file, but a typical storage connector (e.g. the Google Drive connector) **only creates new files and edits metadata: it cannot change an existing file's content.** So a cloud session:
1. creates genuinely new files (a new study page, a new note) straight in their target folder, only if no file of that name exists there, as plain files (with the Google Drive connector: `disableConversionToGoogleType: true`, MIME type `text/markdown` or `text/html`, otherwise a Google Doc appears that nothing can read);
{{#if modules.inbox-sync}}
1. sends every change to an existing file as **one update note per turn** into `inbox/`, named `YYYY-MM-DD_HHMM_<sender>-update.md` (local time), with the exact lines to add or replace. The inbox-sync job applies it. Format and rules: the inbox-sync module page and `inbox/inbox.md`.
1. **The vault wins:** read the vault file first and quote every line to replace exactly as it stands now. The sync applies a replacement only if the quoted line is still there; otherwise it leaves the note in `inbox/` as PARKED and the sender re-sends it against the current file.
{{else}}
1. never changes an existing file: it says in its reply exactly what should change (file, section, lines), and the next laptop session applies it. (The inbox-sync module automates this with update notes.)
{{/if}}
1. In Claude Code: cloud sessions need a git repository, run at most in "accept edits" mode (no bypass), can't read laptop files and can't message laptop sessions back. A cloud session that has the laptop connected through a remote shell tool may edit files directly, but then it backs each file up outside the vault first, re-reads it right before editing, keeps the properties block, and logs what it changed.

{{/if}}
{{#if modules.vm}}
**On the always-on host (VM):** the vault is a mounted folder (an rclone mount of the storage). **No deletes or renames on the mount**: they are real deletes on the storage. Wait for the mount before reading (jobs do this). Search the host's text mirror instead of grepping the mount (a recursive search over a mounted cloud folder takes minutes); read a hit in the real file before relying on it.

{{/if}}
**Concurrency.** Cloud storage is last-writer-wins per file: two machines editing one file within the sync window lose a write or create a conflict copy.
- Re-read a file right before editing it; keep edits small and local; one writer per task; never edit the same file from two machines at the same moment.
- Write a file directly **or** send an update note for it, never both (that produced duplicate `(1)` files in the original).
- New files are always safe.
- **Files where a second writer is risky:** `_agent/rules.md`, `_agent/system-handbook.md`{{#if modules.progress}}, `progress/current-status.md`, `progress/tracker-log.md`, the week pages{{/if}}{{#if modules.courses}}, the course cards{{/if}}{{#if modules.error-logs}}, the error logs{{/if}}{{#if modules.roles}}, `_agent/coordinator-state.md`, `_agent/roles/`{{/if}}{{#if modules.heartbeat}}, `_agent/heartbeat/state.json`{{/if}}.

**Time.** Local time ({{term.timezone}}) everywhere: file names, log lines, times inside notes.{{#if modules.planning}} The daylight-saving switch dates are in `semester/calendar-and-dates.md`.{{/if}} Convert UTC from tools first.

**If you can't reach the vault at all** (a hosted chat project with its own file store, a session without the storage connector): keep writing to your own store, say so in your reply, and list what must be copied in. The next session that can reach the vault runs the **catch-up recipe**:
1. Find the newest "full sync" line in the change log of `_agent/system-handbook.md` (that date is the watermark). Copy every file in the other store that is newer than it into the matching vault file, keeping each vault file's properties block and anything the vault has that the copy lacks (the vault wins). Old paths: `_agent/old-path-map.md`.
1. Apply the update notes waiting in `inbox/`{{#if modules.inbox-sync}} (or let the inbox-sync job do it){{/if}}.
1. Read the sessions or chats active since the watermark for facts no file captured (results, rules, dates, events) and route them through section 3.
{{#if modules.study-pages}}
1. Make Markdown twins of new HTML study pages with the converter (`python _agent/tools/html2md.py <page.html>`).
{{/if}}
1. Append a new "full sync" line to the change log: `- Ddd D Mon YYYY HH:MM: full sync from <store> (compared <what>)`.

## 10. When you add a new kind of thing
Create it in the closest folder, add it to that folder's index (the course card's "In this folder" table, or the map in `README.md`), give it properties (a `type` from section 4, or a new one recorded in section 4), and add a row to section 3b. If it is a new job, role or component, add it to `_agent/system-handbook.md` too.
{{#if modules.check-in}}

## 11. Weekly rhythm
The vault rolls over by itself through scheduled jobs, not because a session "notices" that a week ended. Times are from the config (`[schedule]`).
- **Check-in** (job `check-in`, {{schedule.check_in.day}} {{schedule.check_in.time}}, every {{schedule.check_in.every}}): asks {{student.name}} once for the period's results, then fills "End-of-week check-in" in the current week page and sets it `status: done`; refreshes `progress/current-status.md` (snapshot date, bonus standing, done vs to do, next 10 days, self-ratings) and the course cards' bonus properties; appends one line to `progress/tracker-log.md`; prunes key dates older than a week from `semester/calendar-and-dates.md`. Details: its prompt in `_agent/jobs/check-in/`.
- **Next week's page** (job `week-page`, {{schedule.week_page.day}} {{schedule.week_page.time}}): creates `progress/weeks/week-NN.md` from `_templates/week-page.md` with the week's real "Due this week" rows{{#if modules.planning}}, and asks the planning role for `semester/plans/week-NN-plan.md`{{/if}}.
{{#if modules.experiments}}
- **During a study-method experiment:** one block-log line per study block, written only by the session that owns the experiment; the check-in takes "Focused hours" from it.
{{/if}}
{{/if}}
