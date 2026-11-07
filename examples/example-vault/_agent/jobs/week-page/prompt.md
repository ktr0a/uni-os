# Week page (job `week-page`)

Purpose: create the coming term week's page `progress/weeks/week-NN.md` with a "Due this week" table that lists the week's real items, close the previous page, and ask Plan & progress for the week plan. Runs headless (Sun 10:00); it asks Alex Example nothing. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Edit vault files directly. Everything you write is in English (headings, table columns and dates that tools parse stay exactly as given), UTF-8 without BOM, LF line ends.

## Read first
- `_agent/rules.md` (integrity rules), `_agent/CONVENTIONS.md`, and `_agent/progress-tracking.md` sections 3 and 4 (week-page lifecycle, the "Due this week" cell formats and the done-status vocabulary).

## 0. Should this run do anything?
- **Date.** Get the real local time from the system: `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell); the zone should be Europe/Zurich.
- **Target week.** If today is Friday, Saturday or Sunday, the target is next Monday's week; otherwise (a late run) it is the current week. N = (days from Mon 2026-09-14 to the target Monday) / 7; NN = N with two digits.
- **End of teaching.** If the target Monday is after 2026-12-18 (the last lecture day), do nothing: delete this job's failure flag if there is one (see "Failure flag"), reply one line "No week page: teaching has ended (exam-phase plan takes over)" and stop.
- **Already there?** If `progress/weeks/week-NN.md` already exists, skip section 1 and go to section 2.

## 1. Create the page
1. **Skeleton.** Preferred: run, from the Uni OS framework folder (on an always-on host usually `$UNI_OS_HOME`, e.g. `~/uni-os`; on the laptop the folder where you cloned the framework):
   `python tools/uni_os.py new-week --vault "<vault>" --week N --status current --close-previous`
   It renders `_templates/week-page.md` deterministically, never overwrites, and sets the previous page `done` if it was `current`. Check the result: file name `week-NN.md`, frontmatter `type: week`, `week: N`, `start` = target Monday, `end` = its Sunday, `status`, and the four headings. If the command is missing or failed, render the template yourself: copy `_templates/week-page.md` and replace `{{week.number}}` (N), `{{week.nn}}` (NN), `{{week.monday}}` and `{{week.sunday}}` (ISO dates), `{{week.label}}` ("Mon D Mon to Sun D Mon YYYY"), `{{week.status}}` (`current`) and `{{date:YYYY-MM-DD}}` (today). If the command created a page for another week, leave that file alone and report it. (Its default without `--week` is the week after today's, which is wrong for a late Monday run; always pass `--week N`.)
2. **Read** to know the week's items: `progress/current-status.md` (open items, "Next 10 days"), the previous week page (copy its style; collect rows that are not done), `semester/calendar-and-dates.md` (key dates, release rhythm, graded items), the course cards `AD/ad.md` `DM/dm.md` `LA/la.md` `PROG/prog.md` , the graded items in `_agent/uni-os.toml` (`[[courses.assessments]]`: name, kind, schedule, counts_for, dates), the newest `semester/plans/week-NN-plan.md` if it already exists, and `_agent/skills/course-facts/` if present (weekly rhythm, session offsets, numbering quirks).
3. **Fill "Due this week".** Replace the template's placeholder rows (one per graded item, "open (from the course rhythm; replace ...)") with the week's real rows, one per item due, held or released in the target week:
   - Item: starts with the course short name; says what and which number ("AD exercise sheet 8 (out Thu 12 Nov)"); unique in the table.
   - Official deadline: `Ddd D Mon HH:MM` (`Tue 10 Nov 23:59`), ranges for sittings (`Wed 11 Nov 14:15-14:45`), `tutorial <Ddd D Mon HH:MM>` for items without a hand-in, `(tentative)` or `(inferred)` where not confirmed.
   - Personal target: from the rule "Sheets released in a week are done by that Sunday.".
   - Bonus: points as the course gives them (`4 pts`), `(est.)` when inferred, or `none` / `feedback only`.
   - Status: `not released yet` for items that come out later in the week; `open` otherwise; items already done (recorded elsewhere) get their verdict.
   - **Carry-over:** every row of the previous page that is not done and still relevant goes in again with "(carried over from week M)" in the Item cell; its result belongs to week M until week M's check-in is done (say so in Notes).
   - Mark everything inferred from the weekly rhythm as inferred ("items marked 'not released yet' and estimates come from the course rhythm until the sheets are out").
4. **Notes:** first line `- Created <Ddd D Mon YYYY HH:MM> by the week-page job on <host>. Carried over from week M: <items>. Their results belong in week M until its check-in.` Add collisions or special dates you noticed (a holiday, a moved class).
5. Set `updated:` to today.

## 2. Status of the pages
- The target page: `status: current` (if it was `upcoming`, change only that line and `updated`).
- The previous page (week N-1): if it is `current`, set it `done` (re-read it first, change only that line and `updated`). Its check-in may still be open (its `_To fill_` markers stay): that is fine, the check-in job finds it by the marker.
- Never touch older pages.
## 3. Ask Plan & progress for the week plan
Skip this if `semester/plans/week-NN-plan.md` already exists. Otherwise send this request, choosing the first route your setup supports:
- An inbox note (the inbox sync forwards it): a new file `inbox/YYYY-MM-DD_HHMM_week-page-update.md` (local time) containing only a heading `# Update from week-page, <Ddd D Mon YYYY>` and this section, filled in:
  ```
  ## For Plan & progress
  Request from the week-page job: please write `semester/plans/week-NN-plan.md` for week N (Mon D Mon to Sun D Mon) as your role brief describes. The new week page is `progress/weeks/week-NN.md`. Calendar changes wait for Alex Example's yes.
  ```
  Write nothing else into the note.
- A direct message to the session titled "Plan & progress", if your host can message sessions (in Claude Code: `SendMessage`, loaded with ToolSearch; the session must be listed by ListAgents). Same text.
- Otherwise: add a line to the new page's Notes: `- Week plan not written yet: open Plan & progress and say "plan next week".`

## Failure flag
The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"); create the folder if it is missing.
- **Write** `_agent/logs/flags/week-page.md` when the run ends without its result: the target week's page could not be created or written, the previous page could not be closed, or the plan request could not be sent by any route. Front matter `job: week-page`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: red` when the page is missing, `amber` when only the closing or the plan request failed; the first line of the body says in one sentence what is missing and why, with no personal details (e.g. `week-09.md not created: new-week failed and the template could not be read`). If the file exists, overwrite it with the newest text.
- **Delete** that file (only that one: it is the single file this job may delete) when the run ends with the page in place and `current`, the previous page closed and the plan request sent or not needed, including a run that found everything already done, and at "End of teaching".
- The flag replaces any push of your own: the heartbeat decides whether Alex Example hears about it.

## Never
- Never delete or rename a week page; never rewrite past weeks beyond the one `status` line. The only file this job ever deletes is its own failure flag.
- Never edit anything in `semester/prep/`; never change calendar events.
- Never write results or scores nobody reported; never store solutions.
- No emails, passwords, keys or calendar addresses in any file.

## Final reply
One line: `Week page week-NN (Mon D Mon to Sun D Mon): created|already there; <k> items, <c> carried over; previous page closed|already closed; plan request sent|skipped (<route>); flag written|cleared|none`.
