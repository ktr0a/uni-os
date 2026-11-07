# Study prep morning check (job `study-prep-morning-check`)

Purpose: before the day starts, make sure **today's** prep note is still right: it exists, its blocks match the calendar as it is now, every study block carries the MATERIAL block, and every link points to a real file. Repair anything that is off with a new revision. You are the worker for Alex Example's daily study prep. This job runs headless at 07:30; nobody can answer questions during the run. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Write vault files directly; everything you write is in English (headings, table columns and dates that tools parse stay exactly as given).

## Read first
1. `_agent/daily-prep/RUNBOOK.md`, completely. **Follow it exactly**; this job is its step 7.
2. `semester/prep/README.md` (the format contract), `_agent/CONVENTIONS.md`, `_agent/rules.md` (integrity: never link a solution of a graded task or of an identical older task; graded `solo` work gets the task sheet only).

## 0. Already done?
- Otherwise always run the checks: a second run on the same day (the planner reruns this job after changing today's blocks) must check again. It writes a new revision only when something is off.

## 1. Time
Get the real local time from the system (Europe/Zurich): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Compute the term week (week 0 = Mon 2026-09-14).

## 2. The four checks (runbook step 7), each result written into the log line
a. **Note exists:** the newest `semester/prep/prep-<today>*.md` (highest `-rN`, then latest `generated`) has the contract properties (`type: prep`, `date`, `generated`, `run`, `status`). If there is none, do the full prep for today now (runbook steps 1-5) with `run: "07:30"`.
b. **Callouts match the calendar:** read "Study blocks" and "Courses" for today now; every callout's `HH:MM-HH:MM` equals the start and end of its event, and the number of callouts equals the number of study blocks plus classes. A free day has no callouts and `## Gaps` with `- none`.
c. **MATERIAL blocks:** every study block of today ends its description with a MATERIAL block that names the newest note and lists the same items.
d. **Paths exist:** every backticked vault path and every relative `../../` link in the note, and every vault path in the MATERIAL lines, exists on disk (test each, e.g. `test -e "<path>"` or `Test-Path -LiteralPath "<path>"`; paths contain spaces and `&`, so quote them). Cloud links are only checked for being well formed. Also re-check each gap: a file that has arrived closes it.

If anything is off: write a NEW `-rN` note (never edit the old one) whose first paragraph says what was wrong, and update the MATERIAL blocks. If everything is fine, change nothing. Either way set `days[<today>].verified` in `_agent/daily-prep/state.json` and append the log line:
`- YYYY-MM-DD HH:MM  morning check for <today>: note <file>, callouts n/n match, MATERIAL n/n, paths ok|<broken list>; ok|fixed with <file>`.

**Catch-up:** if tomorrow has no note or `status: open` in `state.json` (the evening runs were missed), do tomorrow's full prep as well (runbook steps 1-5, 8).

## 3. Calendar and file rules
- Calendars only through the calendar tool, found by name; never write ids. "Courses" is read-only. Update study blocks with notifications off; replace only the MATERIAL block (always the last block); never touch titles, times or the planner's text above it. In Claude Code, load the deferred calendar tools with ToolSearch first.
- If the tool refuses updates, do not work around it (no API keys, no feeds): follow the runbook's "Failures" section.
- Prep notes are new files only (UTF-8 without BOM, LF); never edit, move, rename or delete anything in `semester/prep/`. `state.json` stays valid JSON.
- No secrets, keys, emails or private calendar addresses in any file. Course websites are read-only. Don't delete any vault file except this job's own failure flag (section 4).

## 4. Failure flag
The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job") and in the runbook's "Failures" section; create the folder if it is missing.
- **Write** `_agent/logs/flags/study-prep-morning-check.md` when the run ends with something still off: `level: red` when today has no prep note after the run, `level: amber` when a check failed and could not be repaired (calendar not writable, a broken path with no file to point to, a catch-up for tomorrow left `open`). Front matter `job: study-prep-morning-check`, `at: <YYYY-MM-DD HH:MM>` (local time), `level`; the first line of the body says in one sentence what is off and why, with no calendar titles or other personal details (e.g. `MATERIAL 1/2: calendar update denied; prep-2026-11-12-r2.md written`). If the file exists, overwrite it with the newest text.
- **Delete** that file when all four checks end `ok` or `fixed` and any catch-up day is `done`.
- Gaps with a fallback are not failures.

## Final reply
A short summary, problems first: `Morning check <Ddd D Mon>: note <file>; callouts n/n, MATERIAL n/n, paths ok|<broken>; ok|fixed with <file>; flag written|cleared|none`, plus one line if tomorrow was caught up. No notifications: the flag (if any) is the job's only signal.
