# Deadline audit (job `deadline-audit`)

Purpose: one read-only pass that compares every dated obligation the vault documents with the calendars and with the study blocks planned before it, and lists what is at risk, stale, duplicated or missing, ranked by consequence. You write the report, at most one inbox note for Plan & progress and, if the run fails, your own failure flag, and change nothing else. This job runs headless on 2026-12-18 (the last lecture day, before the exam phase) at 08:00, or when started by hand; nobody can answer questions during the run, so state what you could not check instead of asking. The same procedure runs in a Plan & progress session when Alex Example says "audit my deadlines". Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Everything you write is in English (headings, table columns and dates that tools parse stay exactly as given), UTF-8 without BOM, LF line ends.

## Read first
- `_agent/agent-start.md` and `_agent/rules.md` (precision over guessing; integrity rules; no calendar addresses in files).
- `semester/planning-system.md`, section "Deadline audit (docs vs calendar, read-only)": the report format. It wins over this prompt on format.

## 0. Should this run do anything?
- **Date.** Get the real local time from the system (Europe/Zurich): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Term week: week 0 starts Mon 2026-09-14, week n starts 7n days later.
- **Already done today?** If `semester/plans/deadline-audit-<today>.md` exists, delete this job's failure flag if there is one (see "Failure flag"), reply one line "Deadline audit for <today> already exists" and stop. Never overwrite a report.

## 1. Collect the documented obligations
Read, and list every dated item with its exact source (`file.md l.NN`):
- `semester/calendar-and-dates.md` (key dates, release rhythm, graded items, term end, exam logistics);
- `progress/current-status.md` ("Next 10 days", "Later:"), the current week page in `progress/weeks/` ("Due this week") and next week's page if it exists;
- the newest `semester/plans/week-NN-plan.md` ("Deadlines this week", the "Blocks" day lines) and `semester/plans/exam-phase-plan.md`;
- the course cards (`AD/ad.md` `DM/dm.md` `LA/la.md` `PROG/prog.md` ): facts, `next_bonus`, graded streams;
- the graded items in `_agent/uni-os.toml` (`[[courses.assessments]]`: `schedule`, `dates`) and `term` (holidays, last lecture day, exam session).
Group the items into deadline families (weekly quizzes, sheets, hand-ins, graded sittings, registration, term end) and keep the horizon to the next 14 days for "at risk", the whole remaining term for consistency.

## 2. Read the other side
- With the calendar tool, find the calendars by name ("Courses", "Study blocks", "Events", "Busy") and list their events from today to the end of term, in chunks of two to four weeks (calendar tools can't return very long ranges; save a large result to a temp file outside the vault and read it there). Only list and read calls: no create, update, delete, respond or message call. In Claude Code, load the deferred calendar tools with ToolSearch first.
- Judge an event by its **title**: a date that appears only in an event's description counts as "no event". "Events" and "Busy" are read for collisions and stale duplicates only; their titles never go into the report (write "a personal event").
- Times from the tool may be UTC: convert to Europe/Zurich before comparing.

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
Fixes are not this job's work: Plan & progress applies them through the usual rules (proposed or applied, ledger in the week plan) once Alex Example has seen the report. If the report has findings in "Due within 7 days and at risk", also write an inbox note `inbox/YYYY-MM-DD_HHMM_deadline-audit-update.md` containing only `# Update from deadline-audit, <Ddd D Mon YYYY>` and a section `## For Plan & progress` with one line: "Please read `semester/plans/deadline-audit-<date>.md` (n items at risk) and propose the fixes."

## Failure flag
The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"); create the folder if it is missing.
- **Write** `_agent/logs/flags/deadline-audit.md` when the report could not be written, or was written without one side of the comparison (the calendar tool was unavailable, a required file could not be read). Front matter `job: deadline-audit`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: amber`; the first line of the body says in one sentence what is missing and why, with no event titles or other personal details (e.g. `report written without the calendar side: the calendar tool was not available`). If the file exists, overwrite it with the newest text.
- **Delete** that file when the run ends with a complete report, or finds today's report already there.
- The flag replaces any notification: the heartbeat decides whether Alex Example hears about it.

## Never
- Never create, change, move or delete calendar events; never edit any vault file except the new report, the one inbox note and this job's own failure flag (the only file it may delete).
- Never copy titles of personal events, calendar ids, private calendar addresses, emails or keys into any file.
- Never present an inferred date as confirmed; never guess a date that no source gives.
- Never send a notification.

## Final reply
One line: `Deadline audit <Ddd D Mon>: <file>; at risk n, findings m, consistent families k, could not check j; flag written|cleared|none`, or the one-line reason nothing was written.
