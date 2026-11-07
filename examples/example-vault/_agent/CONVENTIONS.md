---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent]
---
# Conventions: how to keep this vault up to date

For every agent working on Alex Example's studies, and for Alex Example. The short version: **this vault is the primary store. Whenever something new and even slightly useful comes up, put it in the right file in the same turn. Don't wait to be asked.**

## 1. Source of truth, in order
1. What Alex Example says now (except that the integrity rules in `rules.md` are never overridden in the moment).
1. **For course facts** (dates, rhythms, rooms, rules that decide points): the official course pages (Moodle course page and its announcements, course websites), then the course catalogue. They beat this vault's course cards and the course notes: when they disagree, correct the vault file with the date and the source (and a line in `resources/course-verification.md` when it came up in a verification pass).
1. **For everything else:** the live files in this vault (the newest `updated` date wins when two disagree).
1. The course-facts skill (`_agent/skills/course-facts/`). When an official page or Alex Example corrects it, the correction goes on the course card, and the card wins.
1. `_agent/archive/` and `z_archive/`: frozen snapshots and outdated copies, never the source for current status.

## 2. Two audiences, two areas
- **Human area** (everything outside `_agent/`): written for Alex Example to read in Obsidian. Short, clear, linked, tables over prose. Agents read it too.
- **Agent area** (`_agent/`): instructions, protocols, routing, tool notes, job definitions, operational state, logs, raw exports. Alex Example doesn't need to read it.
- Don't put agent instructions into human notes beyond a one-line pointer. Don't hide facts Alex Example needs inside `_agent/`.

## 3. Where things go
`<Course>` is a course folder at the vault root and `<c>` its file prefix:

<!-- uni-os:begin courses -->
| Course | `<Course>` | `<c>` |
|---|---|---|
| Algorithms and Data Structures (AD) | `AD` | `ad` |
| Discrete Mathematics (DM) | `DM` | `dm` |
| Linear Algebra (LA) | `LA` | `la` |
| Introduction to Programming (PROG) | `PROG` | `prog` |
<!-- uni-os:end courses -->

<!-- uni-os:begin routing -->
<!-- Generated from the enabled modules. Add your own rows to section 3b, not here (see "Generated regions" below). -->
| You learned... | Put it in | How |
|---|---|---|
| A rule for how agents should help | `_agent/rules.md` | under the matching heading, date in brackets, Alex Example's words quoted; never delete a replaced rule, add "(Since <date>: ...)" to it |
| A setting: a schedule time, a calendar name, a notification limit, a course's help policy, a new course | `_agent/uni-os.toml` (the config) | edit the value, then re-render (`python tools/uni_os.py render` from the framework) and say what changed; scheduled jobs and tasks may need re-installing (see `_agent/system-handbook.md`) |
| A tool or environment trick, a connector quirk | `_agent/tools-and-environment.md` | append a dated bullet under the right heading |
| A new component, job or role, or one changed where it runs | `_agent/system-handbook.md` | add or fix its row; append a line to the change log at the bottom |
| Something you can't place yet | `inbox/` | name it `YYYY-MM-DD_short-topic.ext`; whoever processes the inbox sorts it (rules in `inbox/inbox.md`) |
| Something about Alex Example: identity, goals, tools, shorthand, course contacts | `me/profile.md` | edit in place, date the change, keep the previous value inline ("Before: ... (date)") |
| How Alex Example learns, what works per course, study-page preferences | `me/learning-style.md` | same |
| Energy curve, focus span, sleep or stop times, week shape, places that work | `me/rhythm-and-habits.md` | same; strike through retired advice instead of deleting it |
| A self-rating of understanding ("I'd say 60 % in LA") | `me/profile.md` "Self-rated understanding" **and** `progress/current-status.md` **and** a dated line in `progress/tracker-log.md` | keep the earlier ratings in the Note cell; mark mid-week ratings "provisional" |
| A recurring mistake pattern (seen across several error-log rows or across courses) | `me/weak-spots.md` | one pattern line with its fix and source links; the dated rows stay in the error log |
| A habit experiment (sleep, evenings, phone; proposal, rule change, nightly measure, review) | `me/habits-experiments.md` | one change at a time, two weeks, one simple measure; rule changes dated with the reason; log rows appended |
| A study-method experiment (a new week layout or technique, tried for a fixed period) and its per-block log | `semester/experiments/` (plan + `...-block-log.md`, method in its `README.md`) | one block-log line per study block, written only by the session that owns the experiment; other sessions send it their block report |
| A result, a score, bonus points, a sheet done or not done | the four places in `_agent/progress-tracking.md` section 1: `progress/current-status.md` (state), a dated line in `progress/tracker-log.md`, the course card's properties `bonus_banked` / `bonus_target` / `next_bonus`, and the week page's Status cell plus a line under "Results this week" | all of them in the same turn; edit the status in place; append to the log; keep `x / y` numbers and dates like `Tue 3 Nov 23:59` in that shape (dashboards parse them) |
| What happens this week; the end-of-week check-in | `progress/weeks/week-NN.md` (NN two digits) | create it from `_templates/week-page.md`; set `status: current` on the new week and `status: done` on the old one; status cells cite their evidence and keep the previous value ("done (Tue 3 Nov, Moodle 'Submitted'). Before: open") |
| A course fact: rhythm, deadline, room, assessment rule, bonus rule, help policy, source, page offset | `<Course>/<c>.md` (the course card) | edit in place; say when it corrects an older fact; mark estimates "(est.)". A fact that is also a config key (a graded stream, an assistance level, slots, the session rule, a page offset) changes in `_agent/uni-os.toml` too, then render: the card's graded-streams table and the per-course tables of `courses-overview.md` are generated from it |
| A lecture happened (what was covered) | `<Course>/<c>.md` "Lecture log"; optionally a lecture note from `_templates/lecture-note.md` in `<Course>/notes/` | one line per lecture; only Alex Example's word or the slides actually reached say where it stopped |
| A lecture transcript (from a recorder or dictation app) | `<Course>/notes/<c>-lecture-<ddd><d><mon>-transcript.md` (day not zero-padded), e.g. `<c>-lecture-tue3nov-transcript.md` | wording unchanged, `[mm:ss]` timestamps; check coverage against the recording length (connectors can return partial text); one row in the card's file table and a Lecture log line |
| A parked task, a to-do for later | `<Course>/backlog.md` | append a row with why it was parked and an estimate; strike done rows, don't delete them |
| An official course file (sheet, script, slides, solution) | the course folder's official subfolders (listed on the course card) | keep the official file name; agents may add a newly downloaded file, never rename, move or delete existing ones; link it from the card |
| A newer version of an official file that is already in the vault | the official subfolder, after the old copy moved to `z_archive/<course folder>-outdated-YYYY-MM-DD/` (vault root) | only with Alex Example's OK: move the old copy there under its own name (never delete it), then add the new one under the official name; one line on the card ("Replaced <date>: ...") |
| Reference material (course guide, topic plan, script index) | `<Course>/reference/` | one row in the card's file table |
| A mistake, a point of confusion, "log this error" | `<Course>/<c>-error-log.md` (one file per stream if the course has several) | append a table row in the format at the top of that log (section 7); never edit old rows (corrections are new rows); at the second error of the same family add a pattern under "Patterns to watch" and mirror it as one line in `me/weak-spots.md`; never log `solo` work |
| A study page, summary, rundown, cheat sheet | `<Course>/notes/` | formats per `study.formats` (html, md); named `<c>-<what>-<kind>` (course slug first, kind word last, e.g. `<c>-<topic>-study-page`), lowercase kebab-case; one row in the course card's "In this folder" table |
| A mock quiz, a quiz checklist, a quiz review extract | `<Course>/quiz-prep/` (saved review pages in `quiz-prep/raw/`) | label official vs invented questions; one row in the card's file table |
| Handwritten notes (tablet app exports) | the course's handwritten folder (default `<Course>/<Course> handwritten/`) | written only by the app; agents read and link, never write, move or delete there |
| A key date or deadline | `semester/calendar-and-dates.md` (+ the "Next 10 days" section of `progress/current-status.md` if it falls within 10 days) | edit the tables; prune past dates at the check-in |
| A week plan or a calendar restructure | `semester/plans/week-NN-plan.md`; principles and block notation in `semester/planning-system.md` | new file per week; the calendar wins over the plan file when they disagree |
| A study-approach decision | `semester/study-approach.md` | edit in place, dated, with the reason |
| Tomorrow's study material per block | `semester/prep/prep-YYYY-MM-DD.md` (revisions `-r2`, `-r3`: the highest wins) | written only by the prep jobs: a new file per run, never edited, moved or deleted by hand; to change it, ask for a re-run |
| A useful website, an assistant's or TA's page, a third-party resource | `resources/ta-websites-log.md` (method and log) or `resources/sources-and-links.md` (the registry) | append; one language per resource where possible |
| A course fact checked against the official page | `resources/course-verification.md` | claim, check, result, date; then fix the course card |
| A role, session or routine changed (new role, new owner of a file, new trigger) | the role's brief `_agent/roles/<role>.md`; for a role or route of your own also the "added in this vault" rows in `_agent/roles/README.md` | edit in place; every duty names its trigger; the generated routing and roles tables there follow the modules on render, so don't edit between their markers |
| A request for another role | that role (through the coordinator), not its files | say in your reply what should go where; don't do another role's work yourself |
| A change to an existing file, made by a writer that can only create files | `inbox/YYYY-MM-DD_HHMM_<sender>-update.md` (an update note) | quote every line to replace exactly as it stands now; the inbox-sync job applies it or parks it (section 9) |
| "Stop telling me about X" | `_agent/heartbeat/requests.md` | append one dated line; the watcher reads it before every run |
| Cockpit settings, feeds, layout | the cockpit plugin's settings in Obsidian (keys and feed URLs only in Obsidian's keychain) | never put feed URLs or keys into a vault file |
| A new kind of thing that has no row yet | the closest folder | section 10: create it there, index it, give it properties, add a row to section 3b |
<!-- uni-os:end routing -->

### 3b. Rows added in this vault
Rows that agents or Alex Example added for new kinds of things (section 10). Nothing generated goes here.

| You learned... | Put it in | How |
|---|---|---|

### Generated regions
Parts of this file (the course table and the routing table), `README.md`, `where-to-find-what.md`, `_agent/system-handbook.md` and `_agent/rules.md` (the per-course integrity table and the course-specific rules from the config), the per-course tables of `courses-overview.md` and the graded-streams table of each course card, the weekly grid, release rhythm and graded-items tables of `semester/calendar-and-dates.md`, and the tables in `_agent/roles/README.md` sit between two marker lines, `<!-- uni-os:begin <name> -->` and `<!-- uni-os:end <name> -->`: they are generated from the config and the enabled modules. `uni-os render` (run from the framework: `python tools/uni_os.py render --vault "<vault>"`; `uni-os enable` and `disable` do the same) keeps them current:
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
| `course` | a course id: `algo` `dm` `la` `prog`  | only on course notes |
| `audience` | `me`, `agent` or `both` | nothing else (no "user" or "claude") |
| `updated` | `YYYY-MM-DD` | bump it on every edit |
| `tags` | `uni/<course id>` or `uni/<area>`, plus a flat tag such as `study-page`, `error-log` | hierarchical `uni/...` tags, lowercase |

Note types in this vault (a module adds its own types to its page):

| `type` | Used for | From |
|---|---|---|
| `home` | `Home.md` | core |
| `overview` | `where-to-find-what.md`, `courses-overview.md` | core, courses |
| `agent` | files in `_agent/` | core |
| `inbox` | `inbox/inbox.md`, hand-made inbox notes | core |
| `lecture-note` | lecture notes from `_templates/lecture-note.md` | core |
| `study-page` | study pages and their Markdown twins (property `kind`: teaching-page, skim, rundown, recap, summary, cheat-sheet, walkthrough, ...; twins also carry `source_html` and `converted`) | core, study-pages |
| `reference` | course guides, topic plans, script indexes | core, courses |
| `me` | the student model in `me/` | student-model |
| `course` | course cards `<Course>/<c>.md` (properties `bonus_banked`, `bonus_target`, `next_bonus` are parsed) | courses |
| `backlog` | `<Course>/backlog.md` | courses |
| `error-log` | `<Course>/<c>-error-log*.md` | error-logs |
| `quiz-prep` | files in `<Course>/quiz-prep/` | quiz-coaching |
| `status`, `log`, `week` | `progress/current-status.md`, append-only logs, week pages (properties `week`, `start`, `end`, `status`: `upcoming`, `current` or `done`) | progress |
| `plan` | `semester/plans/week-NN-plan.md` and other plans | planning |
| `prep` | `semester/prep/prep-YYYY-MM-DD[-rN].md` | daily-prep |
| `role` | role briefs in `_agent/roles/` | roles |
| `digest` | `waiting-on-you.md` at the vault root (written by the optional job waiting-on-you) | roles |
| `job` | job definitions in `_agent/jobs/` (when a job carries a Markdown note) | modules with jobs |

## 5. Obsidian rules (this vault is an Obsidian vault)
- **Links:** standard Markdown links with **relative paths** (`[text](../<Course>/<c>.md)`), so they work in Obsidian, on the synced drive, on GitHub and for agents. Wrap paths that contain spaces or `&` in angle brackets: `[Script, p. 12](<../A&D/A&D Plan & Script/script.pdf#page=14>)`. Embeds may use `![[note#Heading]]` or `![[View.base]]`.
- **Unique file names** across the vault's notes: don't create new notes called `README.md`, `log.md`, `notes.md` or `error-log.md` (the folder READMEs that Uni OS installs are the only exception). Prefix with the course or topic, lowercase-kebab-case: `<c>-lecture-mon26oct-<topic>-skim.md`. Source files keep their official names; several folders hold files with the same name (e.g. `week01.pdf`), so link those by relative path, never by bare name.
- **Source PDFs:** link with a relative path in angle brackets plus `#page=N` where useful. Embed a page with `![[file.pdf#page=2]]` only when the name is unique. On a streaming drive a PDF downloads on first open.
- **Templates** live in `_templates/`: copy their properties when creating notes by hand. In Obsidian: command "Templates: Insert template".
- **Maths:** `$...$` and `$$...$$`. Don't use `\(...\)` in Markdown.
- **Callouts:** `> [!note]`, `> [!warning]`, `> [!tip]`, collapsible `> [!info]-`. Custom ones styled by the vault's CSS snippet: one per course (`[!ad]` `[!dm]` `[!la]` `[!prog]` ), `[!course]` (neutral), `[!me]`, `[!week]`, `[!semester]`, `[!deadline]`, `[!agent]`, and `[!grid]` (puts nested callouts side by side).
- **Colours:** each course has one colour (config `courses.colour`), used for its callout, its folder in the file list, its graph group and its node on the vault map. Other areas have their own clearly different colours. Never introduce a colour similar to an existing one.
- **`Home.md`** is the dashboard. Most of it is computed from views and embeds, so keeping properties and the status page right keeps Home right. Edit `Home.md` itself only for new tiles or links.
- **Move or rename notes inside Obsidian** (or through its command line), so links update. A move on the drive, through a connector or with a shell command does not update links.
- Don't edit `.obsidian/` unless Alex Example asks.
- **Parsed formats are contracts.** The cockpit plugin and the jobs parse certain headings, table columns and value shapes (the week page's "Due this week" table, `progress/current-status.md` sections such as "Next 10 days") and the course-card properties and the prep notes. Keep headings, column names, `x / y` numbers and dates like `Tue 3 Nov 23:59` exactly as they are. Each module page names its contract.

## 6. How to write
- **English** in every file (local-language course terms in brackets are fine). No personal sign-off tokens inside files.
- **Absolute dates** with the weekday ("Mon 26 Oct 2026"), plus the term week where it helps. Never "yesterday" or "tomorrow" in a file.
- **Say where a fact comes from** and mark estimates "(est.)" and inferences "(inferred)".
- **Alex Example's words, quoted:** decisions in state pages, rules and briefs carry the quote and the date. That settles later misreadings.
- **No secrets:** no email addresses, passwords, tokens, API keys, private calendar addresses or notification topics.
- **Integrity in files:** never store finished solutions or code for graded work, and never transcribe, summarise or store Alex Example's own `solo` work (handwritten or typed). Coaching notes, error logs and technique explanations are fine. The policies are in `rules.md`.
- **One subject per file.** Update the existing file instead of creating a near-duplicate. Bump `updated` when you edit.
- **Status cells cite their evidence and keep the previous value:** `done 4/4 (Mon 2 Nov 10:05, screenshot). Before: open`.

## 7. Logs: append, don't rewrite
- Append-only files: `progress/tracker-log.md`, every error log, `resources/ta-websites-log.md`, the block and experiment logs, `_agent/logs/inbox-sync-log.md`, the change log in `_agent/system-handbook.md`, and every file under `_agent/logs/`.
- **Fix a wrong entry by adding a correction line** ("Correction to the row of Tue 3 Nov: ..."), never by editing the old one.
- **Error-log rows:** `| Date | Where | What went wrong | Correct idea | Source |`, with the column rules and source tags (`[script]`, `[slides]`, `[task]`, `[derived]`, `[user note]`, ...) written at the top of every log. The correct idea is the general rule, never the full solution of a current graded task. Note Alex Example's state if they mention it (tired, rushed, frustrated): errors made under fatigue weigh differently. Steps: the `log-error` skill in `_agent/skills/`.
- `_agent/archive/` is frozen. To retire a live file, move it there with the date in its name, put "FROZEN on <date>; live file: <path>" at its top, and fix the links.
- `z_archive/` (vault root) holds official course files that a newer version replaced, one folder per replacement: `z_archive/<course folder>-outdated-YYYY-MM-DD/`, files under their official names. It is a source folder: never edit or delete anything there. This is the only place outdated official files go.
- When the folder layout changes, keep a path map (`_agent/old-path-map.md`: `| Old path | New path |`) instead of rewriting old logs, because append-only logs keep old paths forever.

## 8. Notes, sources and app-owned folders
Every folder in the vault is one of three kinds. Agents treat them differently:

| Kind | What | Agents may |
|---|---|---|
| **Notes** | `Home.md`, `README.md`, `where-to-find-what.md`, `inbox/`, `_agent/`, `_templates/`, `me/`, `progress/`, `semester/`, `resources/`, `views/`; in each course folder the top-level `.md` files plus `notes/`, `reference/`, `quiz-prep/` | edit per this file (re-read first, small edits) |
| **Sources** | the official subfolders in each course folder (listed on the course card), the handwritten folders, `z_archive/`, anything Alex Example marks as a source | read and link; **add** a new file (official files only); never rename, move, edit or delete |
| **App-owned or private** | folders written by another app (e.g. a note app's data folder), any private folder, `.obsidian/` | never open private folders; never write, move, rename or delete anything (deleting an app's file can delete the thing on the device) |

Record every app-owned or private folder of this vault here, with its rule, when it appears.

## 9. How to reach the vault
The vault is a synced folder (storage: `google-drive`). Changes made on one machine reach the others through sync, usually within a minute.

**On the laptop** (local agent app or CLI): read and write the synced folder directly. Obsidian opens the same folder. Quote paths: they may contain spaces and `&`.

**Concurrency.** Cloud storage is last-writer-wins per file: two machines editing one file within the sync window lose a write or create a conflict copy.
- Re-read a file right before editing it; keep edits small and local; one writer per task; never edit the same file from two machines at the same moment.
- Write a file directly **or** send an update note for it, never both (that produced duplicate `(1)` files in the original).
- New files are always safe.
- **Files where a second writer is risky:** `_agent/rules.md`, `_agent/system-handbook.md`, `progress/current-status.md`, `progress/tracker-log.md`, the week pages, the course cards, the error logs, `_agent/coordinator-state.md`, `_agent/roles/`, `_agent/heartbeat/state.json`.

**Time.** Local time (Europe/Zurich) everywhere: file names, log lines, times inside notes. The daylight-saving switch dates are in `semester/calendar-and-dates.md`. Convert UTC from tools first.

**If you can't reach the vault at all** (a hosted chat project with its own file store, a session without the storage connector): keep writing to your own store, say so in your reply, and list what must be copied in. The next session that can reach the vault runs the **catch-up recipe**:
1. Find the newest "full sync" line in the change log of `_agent/system-handbook.md` (that date is the watermark). Copy every file in the other store that is newer than it into the matching vault file, keeping each vault file's properties block and anything the vault has that the copy lacks (the vault wins). Old paths: `_agent/old-path-map.md`.
1. Apply the update notes waiting in `inbox/` (or let the inbox-sync job do it).
1. Read the sessions or chats active since the watermark for facts no file captured (results, rules, dates, events) and route them through section 3.
1. Make Markdown twins of new HTML study pages with the converter (`python _agent/tools/html2md.py <page.html>`).
1. Append a new "full sync" line to the change log: `- Ddd D Mon YYYY HH:MM: full sync from <store> (compared <what>)`.

## 10. When you add a new kind of thing
Create it in the closest folder, add it to that folder's index (the course card's "In this folder" table, or the map in `README.md`), give it properties (a `type` from section 4, or a new one recorded in section 4), and add a row to section 3b. If it is a new job, role or component, add it to `_agent/system-handbook.md` too.

## 11. Weekly rhythm
The vault rolls over by itself through scheduled jobs, not because a session "notices" that a week ended. Times are from the config (`[schedule]`).
- **Check-in** (job `check-in`, Sat 19:45, every week): asks Alex Example once for the period's results, then fills "End-of-week check-in" in the current week page and sets it `status: done`; refreshes `progress/current-status.md` (snapshot date, bonus standing, done vs to do, next 10 days, self-ratings) and the course cards' bonus properties; appends one line to `progress/tracker-log.md`; prunes key dates older than a week from `semester/calendar-and-dates.md`. Details: its prompt in `_agent/jobs/check-in/`.
- **Next week's page** (job `week-page`, Sun 10:00): creates `progress/weeks/week-NN.md` from `_templates/week-page.md` with the week's real "Due this week" rows, and asks the planning role for `semester/plans/week-NN-plan.md`.
- **During a study-method experiment:** one block-log line per study block, written only by the session that owns the experiment; the check-in takes "Focused hours" from it.
