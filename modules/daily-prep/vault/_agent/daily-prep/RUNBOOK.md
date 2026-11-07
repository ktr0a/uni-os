---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Daily study prep: runbook

Purpose ({{student.name}}'s rule): every evening, prepare everything the NEXT day's study blocks need (sheets, scripts with sections, study pages, notes) and say where to find it: in an Obsidian note in `semester/prep/` and at the end of each calendar block's description. Log every run, also the ones that change nothing, so the routine's presence is visible. Several attempts a day, so one failure doesn't leave a gap.

The format contract is [semester/prep/README.md](../../semester/prep/README.md); it wins over this runbook on format. This runbook is owned by the Plan & progress role: changes to the routine go through it, with {{student.name}}'s yes.

## Schedule
- **`daily-study-prep`** at {{schedule.daily_prep}}. The **first** of these slots prepares TOMORROW in full (steps 0-5, 8). Every **later** slot runs the change check for TOMORROW (step 6).
- **`study-prep-morning-check`** at {{schedule.prep_check}}: MORNING VERIFICATION of TODAY (step 7).
- One marker per **target date** (the day being prepared) in `state.json`.
- **Catch-up rule:** jobs on a laptop run only while the machine (and, for agent-app scheduled tasks, the app) is running, and may start late. So every run first looks at today and tomorrow in `state.json` and does whatever is missing (no note yet = full prep; note but `status: open` = finish it; today's note not verified = verification), not only what its own slot suggests.

## State (this folder)
- `state.json` (valid JSON, edited in place, UTF-8 without BOM):
  ```json
  {
    "days": {
      "YYYY-MM-DD": {
        "status": "done",
        "attempts": 3,
        "prep_file_name": "prep-YYYY-MM-DD-r2.md",
        "blocks_sig": "09:00 <title> | 14:30 <title>",
        "gaps": ["<item> not in the vault yet (<why>)"],
        "done_by": "<slot> run on <host> <YYYY-MM-DD HH:MM> (<reason>)",
        "last_change_check": "YYYY-MM-DD HH:MM",
        "verified": "YYYY-MM-DD HH:MM",
        "calendar": "pending"
      }
    },
    "carry": { "YYYY-MM-DD": ["<item another session asked to include>"] }
  }
  ```
  `status` is `done` or `open`; `blocks_sig` = start time and title of each study block of the target day, joined by ` | `; `gaps` lists what is missing (dashboards and outcome checks read it; it must be empty when there are none); `calendar: "pending"` only while the MATERIAL lines could not be written.
- `daily-prep-log.md` (append-only, one line per attempt, local time):
  - full prep: `- YYYY-MM-DD HH:MM  <slot> run for <target>: blocks n, items m, gaps g (<names>), note <file>; MATERIAL n/n; day done|open`
  - change check: `- YYYY-MM-DD HH:MM  change check for <target>: blocks unchanged, gaps unchanged; no change` or `...: <what changed>; note <file>; MATERIAL updated`
  - morning check: `- YYYY-MM-DD HH:MM  morning check for <today>: note <file>, callouts n/n match, MATERIAL n/n, paths ok|<broken list>; ok|fixed with <file>`
  - corrections: `- YYYY-MM-DD HH:MM  correction to the HH:MM line: <what is right>`

## Steps of an attempt

**0. Time, state, targets.** Get the real local time from the system ({{term.timezone}}), never from memory: `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Compute the term week (week 0 = Mon {{term.week0_monday}}). Read `state.json`. Pick the target(s): daily-prep runs -> tomorrow; the morning check -> today; plus the catch-up rule. If the target is already `done` at a daily-prep slot, only step 6 runs (it catches the planner's changes of the day).

**1. Read the target day.**
{{#if calendar.provider}}- With the calendar tool, find the calendars by name ({{calendar.study_blocks}}, {{calendar.courses}}, {{calendar.events}}, {{calendar.busy}}) and read the target day 00:00-24:00 in {{term.timezone}}. Never store calendar ids.
- **Study blocks** = events in "{{calendar.study_blocks}}", except `OP` blocks and other non-study items (gym, meals, errands). **Classes** = events in "{{calendar.courses}}" (lectures `{{calendar.lecture_prefix}}`, exercise classes `{{calendar.exercise_prefix}}`, graded fixtures). "{{calendar.events}}" and "{{calendar.busy}}" are read only to mention collisions; their titles never go into a file (write "a personal event").
- Judge a block by its title, not its description. The `FOCUS:` lines in the descriptions are the planner's statement of what each block needs: use them first.{{else}}- No calendar is connected: the day's blocks are the target day's line under "Blocks" in the newest `semester/plans/week-NN-plan.md` (`- **Ddd:** HH:MM-HH:MM <title> · ...`).{{/if}}
- Then the vault: the week plan's "Material per block", the current week page (`progress/weeks/week-NN.md`, "Due this week"), the course cards, and the course folders.

**2. Work out the material per block.** First fold in `carry[<target date>]` from `state.json`. Then, from the block's title, its FOCUS lines and the week plan:
- **Sheets and assignments:** the PDF in the course's official subfolder (find it with a file listing; it is the source of truth). Name the tasks the block covers.
- **Scripts and slides:** the file plus the section, and the page offset if the course card or the config lists one ("PDF page = printed + 8"){{#each courses}}{{#each course.page_offsets}}; {{course.short}} {{item.source}}: {{item.rule}}{{/each}}{{/each}}.
- **Study pages:** the HTML page and its Markdown twin in `<course folder>/notes/` (and quiz-prep pages in `quiz-prep/`). **Check that each file exists on disk.** A page the block names that isn't there is a gap (step 3).
- **Classes:** the script chapter or slides of that lecture only. **Light slots:** the recap page or the short item they name.
- **Opening recap:** if the planning system says blocks start with a short open-notes recap, the first item names the pages to reread.
- **Cloud links for the phone:** PDFs get their vault path; for the MATERIAL lines a cloud-storage link is a useful phone fallback. Reuse a link that an earlier MATERIAL block or prep note already has for the same file; if none is known, give the vault path only (never guess or construct a link).
- **Integrity filters** (never overridden):
  - Never link a solution of a task that is graded now, or of an identical older task (old sheets with official solutions sometimes repeat a current graded task word for word: check before linking).
  - For graded `solo` work, link the task sheet only, and write "solo, no AI help" into the item.
  - Keep the warning in the item when a PDF contains both an allowed and a graded task ("task 6.1 only; the same PDF holds graded task 6.3: don't read it").
  - **Integrity windows:** material the student keeps closed before a graded sitting (for example their own model summary sheet in the week before an oral) is not linked inside that window. Windows are written in the course card or the course's `notes` in the config.
  - Per course (from the config; assessment-level overrides are in `_agent/uni-os.toml`):
{{#each courses}}    - {{course.short}}: assistance level `{{course.assistance}}`.{{#each course.assessments}}{{#if item.assistance == "solo"}} Solo: {{item.name}}.{{/if}}{{/each}}{{#if course.integrity}} Official rule: {{course.integrity}}{{/if}} {{course.notes}}
{{/each}}

**3. Gaps.** Material a block names that is not in the vault (a promised study page, a sheet not saved yet, a page that exists only in a chat app's own storage or an online library this job can't reach) is a gap. List each under `## Gaps` in the note and as a `PENDING:` line in the MATERIAL block, always with a fallback ("script §4.5", "the LMS course page", "open it in the chat app"). The owner learns about it through the log line{{#if modules.inbox-sync}} and, only when a session must act, a short inbox note `inbox/YYYY-MM-DD_HHMM_daily-prep-update.md` with a `## For <session title>` section{{/if}}. A gap is dropped as soon as the file exists. Sheets behind the university login reach the vault only when someone fetches them{{#if modules.course-files-fetch}} (the course-files-fetch role){{/if}}; until then they are gaps.

**4. Write the note.** A **new** file `semester/prep/prep-YYYY-MM-DD.md` (UTF-8 without BOM, LF). If a note for that date exists, the new one is `-r2`, `-r3`, ... (one more than the highest). Check with a file listing first. **Never overwrite, edit, move or delete an existing prep note.** Format: the contract. Set `run` to this run's nominal slot (or `manual`), `status` to `ready-with-gaps` when `## Gaps` is not `- none`.

**5. Calendar.**{{#if calendar.provider}} For each study block of the target day in "{{calendar.study_blocks}}": read the event right before changing it (the planner edits descriptions too), then update it **with notifications off**, keeping the full existing description and putting at its end the block
`MATERIAL (daily prep, <Ddd D Mon HH:MM>; all of it in {{#if obsidian.enabled}}Obsidian{{else}}the vault{{/if}}: semester/prep/<note name without .md>)` followed by one line per item (vault paths; cloud links for PDFs where known; `PENDING:` lines for gaps). If a MATERIAL block exists, replace only that block (it is always the last one). **Never touch the text above it** (tasks, FOCUS: the planner owns it). Never edit events in "{{calendar.courses}}". Read the event back: the start and end must be unchanged.{{else}} Skipped (no calendar connected).{{/if}}

**6. Change check** (later daily-prep slots, and any daily-prep run whose target is already `done`). Recompute `blocks_sig` for the target day, re-read the classes (a moved lecture changes a callout's times) and re-check every gap (does the file exist now?). If anything changed: write the next `-rN` note (its first paragraph says what changed), update the MATERIAL blocks, update `state.json`, log it. Otherwise append only `... change check for <target>: blocks unchanged, gaps unchanged; no change` and set `last_change_check`. **No new note when nothing changed.**

**7. Morning verification** (the morning check; target = today). Check all four and write each result into the log line:
1. **Note exists:** the newest `prep-<today>*.md` exists with the contract properties (`type: prep`, `date`, `generated`, `run`, `status`). Missing: do the full prep now (steps 1-5) with `run: "{{schedule.prep_check}}"`.
2. **Callouts match the calendar:** every callout's start and end equal its event's start and end (study blocks and classes, read now{{#unless calendar.provider}}; without a calendar: the day's line under "Blocks" in the newest week plan{{/unless}}), and the number of callouts equals the number of those events. A free day: no callouts and `- none`.
3. **MATERIAL blocks:** {{#if calendar.provider}}every study block of today ends with a MATERIAL block that names the newest note and lists the same items.{{else}}skipped (no calendar connected).{{/if}}
4. **Paths exist:** every backticked vault path and every relative `../../` link in the note, and every vault path in the MATERIAL lines, points to a file that exists on disk (check each with a file test, e.g. `test -e "<path>"` or `Test-Path -LiteralPath "<path>"`). Cloud links are not fetched; check only that they are well formed.
- Anything off: fix it with a NEW `-rN` note (never edit the old one) and updated MATERIAL blocks; say in the note's first paragraph and in the log what was wrong. All fine: change nothing.
- Set `days[today].verified` and append the log line either way.
- Catch-up: if tomorrow has no note or `status: open` (the evening runs were missed), do tomorrow's full prep too.

**8. Mark and log.** The day is `done` after steps 4 and 5 worked (gaps are allowed). Update `attempts`, `prep_file_name`, `blocks_sig`, `gaps`, `done_by`. Append the log line.

**9. Tell {{student.name}}** only in the run's own final reply (no push, no messages): one short summary. If step 7 could not fix something or the calendar was not writable, say so at the top, and leave the failure flag (see "Failures").

**10. Failure flag.** Last, write or delete this job's flag file as "Failures" says.

## Slot types (optional)
If the planning system defines special slots that the prep must recognise by title (for example a short weekly "error-log redo" slot that names three old error-log rows of that course, or a "lecture skim" slot that needs the skim page of the next lecture), describe each here: how to recognise it, what MATERIAL it gets, where its items come from, and what is never linked. None are defined by default. (The original had a 20-minute retest slot with the three oldest error-log rows per course; the student dropped retests after a week, "that doesn't really work", which is why slot types are opt-in.)

## Failures
- A calendar or file error: retry once, log it, leave the day `open` (the next run retries).
- One half works, the other doesn't (vault yes, calendar no, or the reverse): do the half that works, mark the day `open`, and log which half is missing.
- The calendar tool is read-only or refuses updates in this run: **do not work around it** (no API keys, no calendar feeds, no other accounts). Write the note, mark the day `open` with `"calendar": "pending"`, and log "MATERIAL lines not written: calendar update denied".
- **Failure flag:** a run that ends with its result incomplete writes one small file `_agent/logs/flags/<job>.md` (`<job>` = `daily-study-prep` or `study-prep-morning-check`; create the folder if needed): front matter `job: <job>`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: red` when a target day has no note at all, `amber` when the note exists but something is still off (MATERIAL blocks pending, a check that could not be repaired, a day left `open`); the first line of the body is one sentence on what is missing and why, without calendar titles or other personal details. An existing flag is overwritten with the newest text. The next run of the same job that ends complete (every day it handled `done`, no `"calendar": "pending"`, the morning checks `ok` or `fixed`) deletes its own flag; that is the only file these jobs ever delete. Gaps with a fallback are not failures. {{#if modules.heartbeat}}The heartbeat turns a flag into the finding `job:<job>:failed` and decides whether {{student.name}} hears about it (format: `_agent/heartbeat/README.md`).{{else}}Without the heartbeat module nobody reads the flag between runs: it stays as the record of the incomplete run until a complete run removes it, and the run that writes it also puts the failure on the first line of its final reply{{#if modules.notifications}} and sends one gated push `--id job:<job>:failed` (the job prompts give the exact line){{/if}}.{{/if}}
- Never send an "all good" message. Outside watchers (dashboards{{#if modules.vm}}, the host's outcome checks{{/if}}{{#if modules.heartbeat}}, the heartbeat{{/if}}) alert when a note is missing.

## Where {{student.name}} sees it
{{#if calendar.provider}}- The calendar: the MATERIAL block in each study block (phone, calendar app{{#if modules.cockpit}}, the cockpit's week view{{/if}}).
{{/if}}- Obsidian: `semester/prep/prep-YYYY-MM-DD[-rN].md` (the newest file for a date wins){{#if modules.cockpit}} and the cockpit's Prep card{{/if}}.
- This folder's `daily-prep-log.md`.

## Notes and gotchas
- Re-read the calendar on every run: the planner reshapes blocks in the evening and in the morning, so a note written at the first evening run can be stale by the morning.
- The MATERIAL header can name an older revision after a manual change; the morning check fixes that.
- Vault re-layouts silently break links; the morning check's path test is what catches it.
- Week labels: use the project numbering from `semester/calendar-and-dates.md`, not the LMS's (the original labelled a week wrongly for two days).
- Duplicate files from cloud sync (`name (1).md`): leave them, link the original, mention it in the log.
- No secrets, keys, private calendar addresses or feed URLs in any file. Course websites are read-only.
