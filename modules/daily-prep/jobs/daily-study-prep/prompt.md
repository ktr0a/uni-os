# Daily study prep (job `daily-study-prep`)

Purpose: tomorrow's study material in one fixed place: a prep note in `semester/prep/` and a MATERIAL block at the end of each study block in the calendar. You are the worker for {{student.name}}'s daily study prep. This job runs headless at {{schedule.daily_prep}}: the **first** slot prepares TOMORROW in full; every **later** slot runs the change check for TOMORROW. Nobody can answer questions during the run. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Write vault files directly; everything you write is in {{student.language}} (headings, table columns and dates that tools parse stay exactly as given).

## Read first
1. `_agent/daily-prep/RUNBOOK.md`, completely. **Follow it exactly.**
2. `semester/prep/README.md` (the format contract; it wins over the runbook on format), `_agent/CONVENTIONS.md`, and `_agent/rules.md` (integrity: never link a solution of a graded task or of an identical older task; for graded `solo` work link the task sheet only).

## 0. Already done?
{{#if modules.vm}}- **Failover marker.** This job may run on the laptop and, when the laptop is off, on the always-on host. Work out this run's nominal slot (the latest of {{schedule.daily_prep}} at or before now, without the scheduler's few-minute offset) as `YYYY-MM-DD HH:MM`. If `_agent/vm/ran/daily-study-prep.md` exists and its `slot:` line equals that slot, the host already ran it: reply one line "Skipped: the host already ran the <slot> slot" and stop.
{{/if}}- Otherwise `_agent/daily-prep/state.json` decides: a target that is already `done` gets only the change check (runbook step 6). There is never a second note for an unchanged day.

## 1. Time, slot, target
- Get the real local time from the system ({{term.timezone}}): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date.
- The nominal slot is the latest of {{schedule.daily_prep}} at or before now. **First slot: full prep for TOMORROW** (runbook steps 0-5 and 8). **Any later slot: change check for TOMORROW** (step 6). Earlier than the first slot (a manual run): full prep for tomorrow with `run: manual`.
- **Catch-up rule:** if today or tomorrow has no prep note, or `status: open` in `state.json` (for example because the machine was off at an earlier slot), do that missing work too.

## 2. Calendar
{{#if calendar.provider}}- Read and update the calendar "{{calendar.study_blocks}}" (study blocks: read them, append or replace the MATERIAL block) and read "{{calendar.courses}}" (classes and fixtures: **read-only**), through the calendar tool only. Find both by name with the tool's list function; never write calendar ids into any file. "{{calendar.events}}" and "{{calendar.busy}}" may be read for collisions only.
- In Claude Code, the calendar connector's tools are deferred: load them with ToolSearch before the first call.
- Update events with notifications off; read each event right before changing it and read it back afterwards; never change titles, times or the planner's text above the MATERIAL block.
- If the tool refuses updates, **do not work around it** (no API keys, no calendar feeds, no other accounts): follow the runbook's "Failures" section.{{else}}- No calendar is connected: read the target day's line under "Blocks" in the newest week plan; skip the calendar step.{{/if}}

## 3. Files
- Write prep notes as **new files** in `semester/prep/` in the exact contract format (UTF-8 without BOM, LF). Never edit, move, rename or delete an existing file there; a change is the next `-rN` revision.
- Update `_agent/daily-prep/state.json` in place (keep it valid JSON) and append one line per attempt to `_agent/daily-prep/daily-prep-log.md`, also for runs that change nothing.

## 4. Rules
- No secrets, keys, emails or private calendar addresses in any file; never copy titles from personal calendars.
- Course websites are read-only; don't fetch files behind a login (a missing sheet is a gap with a fallback).
- Don't delete any vault file except this job's own failure flag (section 5). Don't edit the week plan, the week page or study pages (other owners); report what is missing.

## 5. Failure flag
{{#if modules.heartbeat}}The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"){{else}}The format is below (the heartbeat module, which normally reads flags, is not installed){{/if}} and in the runbook's "Failures" section; create the folder if it is missing.
- **Write** `_agent/logs/flags/daily-study-prep.md` when the run ends with a target day still `open` in `state.json`: `level: red` when that day has no prep note at all, `level: amber` when the note exists but the MATERIAL blocks are missing (`"calendar": "pending"`) or another half failed. Front matter `job: daily-study-prep`, `at: <YYYY-MM-DD HH:MM>` (local time), `level`; the first line of the body says in one sentence what is missing and why, with no calendar titles or other personal details (e.g. `calendar write denied; prep note for 2026-11-12 written without MATERIAL blocks`). If the file exists, overwrite it with the newest text.
- **Delete** that file when the run ends with every target day it handled `done` and no `"calendar": "pending"` left, including a change check that found nothing to change.
- Gaps (missing material with a fallback) are not failures: they live in the note and in `state.json`, not in a flag.
{{#unless modules.heartbeat}}
- No heartbeat is installed (module `heartbeat`), so nobody reads the flag between runs: it is the record for the next run and the next session. Whenever you write it, also put the failure on the first line of your final reply{{#if modules.notifications}} and send one push through the gate, from the vault root: `uni-os push "Daily study prep could not finish; ask any session what failed." --id job:daily-study-prep:failed --source daily-study-prep` (no file names or details in the text; if `uni-os` is not a command here, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"`; exit 10-13: don't retry, say so in the reply){{/if}}.
{{/unless}}

## Final reply
A short summary, problems first: `Prep for <Ddd D Mon> (<slot> run): <new note prep-...md | no change>; blocks n, items m, gaps g (<names>); MATERIAL n/n; day done|open; flag written|cleared|none.` {{#if modules.heartbeat}}No notifications: the flag (if any) is the job's only signal.{{else}}No other notifications: a failure is the first line of this reply{{#if modules.notifications}} plus its one push{{/if}}.{{/if}}
