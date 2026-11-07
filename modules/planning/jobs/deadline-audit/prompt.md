# Deadline audit (job `deadline-audit`)

Purpose: one read-only pass that compares every dated obligation the vault documents with {{#if calendar.provider}}the calendars{{else}}the week plans (no calendar is connected){{/if}} and with the study blocks planned before it, and lists what is at risk, stale, duplicated or missing, ranked by consequence. You write the report{{#if modules.inbox-sync}}, at most one inbox note for Plan & progress{{/if}} and, if the run fails, your own failure flag, and change nothing else. This job runs headless{{#if term.last_lecture_day}} on {{term.last_lecture_day}} (the last lecture day, before the exam phase) at {{schedule.day_start}}{{/if}}, or when started by hand; nobody can answer questions during the run, so state what you could not check instead of asking. The same procedure runs in a Plan & progress session when {{student.name}} says "audit my deadlines". Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Everything you write is in {{student.language}} (headings, table columns and dates that tools parse stay exactly as given), UTF-8 without BOM, LF line ends.

## Read first
- `_agent/agent-start.md` and `_agent/rules.md` (precision over guessing; integrity rules; no calendar addresses in files).
- `semester/planning-system.md`, section "Deadline audit (docs vs calendar, read-only)": the report format. It wins over this prompt on format.

## 0. Should this run do anything?
{{#if modules.vm}}- **Failover marker.** Work out this run's nominal slot as `YYYY-MM-DD HH:MM`. If `_agent/vm/ran/deadline-audit.md` exists and its `slot:` line equals that slot, reply one line "Skipped: the host already ran the <slot> slot" and stop.
{{/if}}- **Date.** Get the real local time from the system ({{term.timezone}}): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Term week: week 0 starts Mon {{term.week0_monday}}, week n starts 7n days later.
- **Already done today?** If `semester/plans/deadline-audit-<today>.md` exists, delete this job's failure flag if there is one (see "Failure flag"), reply one line "Deadline audit for <today> already exists" and stop. Never overwrite a report.

## 1. Collect the documented obligations
Read, and list every dated item with its exact source (`file.md l.NN`):
- `semester/calendar-and-dates.md` (key dates, release rhythm, graded items, term end, exam logistics);
{{#if modules.progress}}- `progress/current-status.md` ("Next 10 days", "Later:"), the current week page in `progress/weeks/` ("Due this week") and next week's page if it exists;
{{/if}}- the newest `semester/plans/week-NN-plan.md` ("Deadlines this week", the "Blocks" day lines){{#if term.exam_session_start}} and `semester/plans/exam-phase-plan.md`{{/if}};
- the course cards ({{#each courses}}`{{course.folder}}/{{course.slug}}.md` {{/each}}): facts, `next_bonus`, graded streams;
- the graded items in `_agent/uni-os.toml` (`[[courses.assessments]]`: `schedule`, `dates`) and `term` (holidays, last lecture day, exam session).
Group the items into deadline families (weekly quizzes, sheets, hand-ins, graded sittings, registration, term end) and keep the horizon to the next 14 days for "at risk", the whole remaining term for consistency.

## 2. Read the other side
{{#if calendar.provider}}- With the calendar tool, find the calendars by name ("{{calendar.courses}}", "{{calendar.study_blocks}}", "{{calendar.events}}", "{{calendar.busy}}") and list their events from today to the end of term, in chunks of two to four weeks (calendar tools can't return very long ranges; save a large result to a temp file outside the vault and read it there). Only list and read calls: no create, update, delete, respond or message call. In Claude Code, load the deferred calendar tools with ToolSearch first.
- Judge an event by its **title**: a date that appears only in an event's description counts as "no event". "{{calendar.events}}" and "{{calendar.busy}}" are read for collisions and stale duplicates only; their titles never go into the report (write "a personal event").
- Times from the tool may be UTC: convert to {{term.timezone}} before comparing.{{else}}- No calendar is connected: the "Blocks" day lines of the week plans are the schedule. Category 3 below (calendar contradicts the docs) is "not applicable".{{/if}}

## 3. Compare and write the report
Write the new file `semester/plans/deadline-audit-<YYYY-MM-DD>.md` (today's date) with this frontmatter and the sections of `planning-system.md`:

```markdown
---
type: plan
audience: both
updated: <YYYY-MM-DD>
tags: [uni/plan]
---
# Deadline audit <Ddd D Mon YYYY> (term week N)
```

- The header paragraph: run time, term week, "Read-only: nothing was changed", the judging rule ("calendar coverage is judged by event **title**"), and the confidence legend: high = both sides read directly; medium = implied, or one side not verifiable from here; low = inference.
- `## 1. Due within 7 days and at risk`: most urgent first, each with evidence and a confidence level.
- `## 2. Findings`: table `| # | What | Docs say | Calendar says | Source | Sure |`; every cell cites `file.md l.NN` or the calendar, the event title and the date.
- `## 3. Results by category`: (1) a date in the docs with no event or a different time; (2) docs that disagree with each other; (3) a course-calendar event that contradicts the docs; (4) graded deadlines in the next 14 days with no study block before them.
- `## 4. Checked and consistent`: one line per deadline family that matched (proving coverage matters as much as listing problems), and a line "Known-intentional items, not reported" if there are any.
- `## 5. What I checked, and what I could not`: the files read, the calendars and date ranges read, the sentence "No create, update, delete, respond or message call was made", and an explicit "Could not check" list (for example states on the learning platform, unpublished exam dates, dates that are only inferred).

Doc-vs-doc disagreements are as common as doc-vs-calendar ones; stale duplicates usually sit in the personal calendar, not the course calendar. Mark every inference as one.

## 4. Afterwards
Fixes are not this job's work: Plan & progress applies them through the usual rules (proposed or applied, ledger in the week plan) once {{student.name}} has seen the report.{{#if modules.inbox-sync}} If the report has findings in "Due within 7 days and at risk", also write an inbox note `inbox/YYYY-MM-DD_HHMM_deadline-audit-update.md` containing only `# Update from deadline-audit, <Ddd D Mon YYYY>` and a section `## For Plan & progress` with one line: "Please read `semester/plans/deadline-audit-<date>.md` (n items at risk) and propose the fixes."{{/if}}

## Failure flag
{{#if modules.heartbeat}}The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"){{else}}The format is below (the heartbeat module, which normally reads flags, is not installed){{/if}}; create the folder if it is missing.
- **Write** `_agent/logs/flags/deadline-audit.md` when the report could not be written, or was written without one side of the comparison (the calendar tool was unavailable, a required file could not be read). Front matter `job: deadline-audit`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: amber`; the first line of the body says in one sentence what is missing and why, with no event titles or other personal details (e.g. `report written without the calendar side: the calendar tool was not available`). If the file exists, overwrite it with the newest text.
- **Delete** that file when the run ends with a complete report, or finds today's report already there.
{{#if modules.heartbeat}}
- The flag replaces any notification: the heartbeat decides whether {{student.name}} hears about it.
{{else}}
- No heartbeat is installed (module `heartbeat`), so nobody reads the flag between runs: it is the record for the next run and the next session. Whenever you write it, also put the failure on the first line of your final reply{{#if modules.notifications}} and send one push through the gate, from the vault root: `uni-os push "Deadline audit could not finish; ask any session what failed." --id job:deadline-audit:failed --source deadline-audit` (no file names or details in the text; if `uni-os` is not a command here, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"`; exit 10-13: don't retry, say so in the reply){{/if}}.
{{/if}}

## Never
- Never create, change, move or delete calendar events; never edit any vault file except the new report{{#if modules.inbox-sync}}, the one inbox note{{/if}} and this job's own failure flag (the only file it may delete).
- Never copy titles of personal events, calendar ids, private calendar addresses, emails or keys into any file.
- Never present an inferred date as confirmed; never guess a date that no source gives.
- Never send a notification.

## Final reply
One line: `Deadline audit <Ddd D Mon>: <file>; at risk n, findings m, consistent families k, could not check j; flag written|cleared|none`, or the one-line reason nothing was written.
