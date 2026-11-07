# Check-in (job `check-in`)

Purpose: once per period (Sat 19:45, every week) collect the period's results from Alex Example with **one** question, then close the week page(s) and bring every progress record up to date. This job talks to Alex Example: turn 1 reads and asks, then waits in this session; turn 2 applies the answer. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Edit vault files directly. Everything you write is in English (headings, table columns and dates that tools parse stay exactly as given).

When Alex Example types "check-in" in any session, that session follows this same prompt (an unscheduled check-in).

## Read first
- `_agent/agent-start.md` and `_agent/rules.md` (non-negotiable: integrity rules, reply rules, precision over guessing).
- `_agent/CONVENTIONS.md` (where things go) and `_agent/progress-tracking.md` (the formats: four-place write, tracker line, done-status vocabulary, dashboard sections, bonus logic). Follow them exactly; dashboards parse these files.

## 0. Should this run do anything? (in this order; stop at the first "stop")
- **Date and week.** Get the real local time from the system, never from memory: `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). The machine's time zone should be Europe/Zurich; if the offset says otherwise, convert. Term week: week 0 starts Mon 2026-09-14, week n starts week 0 + 7n days (cross-check: `python tools/uni_os.py week` in the framework folder, if available).
- **Frequency.** Every week: nothing to check.
- **Which weeks.** The target week is the current week if today is Thursday to Sunday, the previous week if today is Monday to Wednesday. The pages to fill are `progress/weeks/week-NN.md` of the target week, but only those whose section `## End-of-week check-in` still contains `_To fill_`. If none is left, delete this job's failure flag if there is one (see "Failures"), reply one line "Check-in for week N is already done" and stop: don't ask again.
- **Older open pages.** A page older than the period that still shows `_To fill_` belongs to a check-in nobody answered. Don't fill it from guesses; add one line to the question ("Anything to add for week K? Otherwise I mark it 'not checked in'.").
- **Can this run ask?** This job needs Alex Example's answer in this session. If the host header above says session type `print` (headless: nobody can open or answer this run, e.g. the laptop's OS scheduler), don't ask and change nothing: send one line through the push gate as step 5 describes, with the text "Check-in is due: open a session and type check-in." and the same `--id ask:check-in --source check-in`, then reply one line "Check-in is due, but this run can't ask; push <sent or the gate's answer>" and stop. Session types `rc` and `app`, and an interactive session without a header, can ask: go on.

## Turn 1: read, then ask once
1. Read:
   - `progress/current-status.md` and the last ~40 lines of `progress/tracker-log.md`;
   - the target week page(s) (Due this week, Results, Notes) and, if it exists, next week's page;
   - the course cards' properties (`bonus_banked`, `bonus_target`, `next_bonus`): `AD/ad.md` `DM/dm.md` `LA/la.md` `PROG/prog.md` ;
   - the course backlogs: `AD/backlog.md` `DM/backlog.md` `LA/backlog.md` `PROG/backlog.md` ;
   - `semester/calendar-and-dates.md` (key dates, rhythm) and the target week's plan `semester/plans/week-NN-plan.md` (planned blocks vs what happened);
   - the running experiment's block log in `semester/experiments/` (focused minutes per block);
   - the course rhythm and graded items in `_agent/uni-os.toml` (`[[courses.assessments]]`, `[courses.bonus]`).
2. Collect what is already known. Course sessions, Done taps and earlier messages may have recorded results this week: never ask again for something that is recorded.
3. List what is missing, per course: Status cells that are still open, pending or not reported for items whose deadline or sitting has passed; graded fixtures of the period without a score; items you can't tell are done or rolling over.
4. **Ask once**, in one short message (at most about 15 lines):
   - one line per course naming the open items and offering short answers ("done / partly (which tasks) / not done / dropped"), and asking for each missing score ("AD quiz 2: score out of 10?");
   - which items roll over to next week (or get parked in the backlog);
   - focused study hours this period (rough is fine), what worked, what didn't;
   - self-rating per course in % (optional; say so);
   - anything new for next week (events, changed dates);
   - **exam-date watcher:** only if `semester/plans/exam-phase-plan.md` still contains `[EXAM` placeholders marked TBD and fewer than about five weeks of teaching are left (last lectures 2026-12-18), one line: "Are your exam dates out yet? Paste or screenshot them." (Personal exam plans sit behind the university login: don't try to fetch them from this job.)
   Offer answer formats so a phone reply is enough ("AD: sheet done 4/4, quiz 3/4; DM: 6.1-6.3 done, rest parked; ~18 h; AD 80, DM 60"). **Never guess a number.**
5. **Announce the question once.** If this run is hosted by the always-on host's job runner, the runner pushes the session link after this turn: send nothing yourself. Otherwise send one line through the push gate (the only way pushes leave this system, `_agent/notifications.md`), from the vault root: `uni-os push "Check-in is waiting for your results." --id ask:check-in --source check-in`. If `uni-os` is not a command here, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"` (the job runners export both; without them, as in a desktop-app task or an interactive session: the Python named in the header and the framework folder, plus `--vault "<vault>"`). No `--direct`: that is only for host health alerts and job failures. If the gate holds (exit 10), has no budget (11), dedupes (12) or refuses (13), don't retry and don't use another channel (no app notification either): say so in the reply; the question waits in this session anyway. No personal details in the push.
6. End the turn and wait for the answer in this session.

## Turn 2: apply the answer
Re-read each file right before editing it, keep the properties block, bump `updated`, keep edits small. Mark anything unclear "to be confirmed" and tick nothing for it. Results of items carried over from an earlier week go to that earlier page if its check-in is part of this run.

Apply the answer to each of the following. They are bullets, not numbered steps, because the list depends on the modules you have; refer to a step by its bold name.

- **Week page(s).** For each page being filled:
  - Status cells: verdict first, evidence after, old value kept (`done 4 / 4 (check-in Sat 7 Nov, Alex Example). Before: open`). Use the done-status vocabulary exactly.
  - "Results this week": one line per new result, `- <Ddd D Mon> ~HH:MM: <item> = **<score>** (check-in, Alex Example)`.
  - "End-of-week check-in": first the line `Filled <Ddd D Mon> with Alex Example (check-in job).`, then replace every `_To fill_` line: `- **Done:**`, `- **Focused hours:**` (from the block log where it has data, else the student's estimate, labelled), `- **What worked:**`, `- **What didn't:**`, `- **Missed:**`, `- **Self-rating:**`, `- **Rolls over:**`. Quote Alex Example where it helps. Nothing to say = "none".
  - Set `status: done` if it was `current`. An older unanswered page gets "not checked in (no answer by <date>)" on each `_To fill_` line, unless the student answered for it now.
- **Dashboard** (`progress/current-status.md`): re-date the snapshot line (`**Snapshot: <Ddd D Mon YYYY>, <time of day> (end of term week N).**`); recompute every "Bonus standing" row with the arithmetic (section 6 of `_agent/progress-tracking.md`); update the detail tables; "Exercises: done vs. to do (as of <date>)" per course; "Self-rated understanding" (first line in the parsed shape, earlier values after it); "Next 10 days": drop passed rows, add the items of the next 10 days from `calendar-and-dates.md`, the course rhythm and next week's page, then the "Later:" line. Keep headings, columns, `x / y` numbers and dates like `Tue 3 Nov 23:59` exactly in that style.
- **Course cards:** `bonus_banked`, `bonus_target`, `next_bonus` in the parsed shapes.
- **Key dates** (`semester/calendar-and-dates.md`): remove key-date rows older than one week (struck-through dropped rows go too).
- **Tracker log** (`progress/tracker-log.md`): append one line, `- <Ddd D Mon YYYY> ~HH:MM (check-in job, answers by Alex Example): **Week N check-in**: <done>; <rolls over>; <bonus changes>; <focused hours>; <open questions (?)>.`
- **Backlogs:** strike through rows that are now done; add tasks the student parked ("for later").
- **Profile** (`me/profile.md`): the self-ratings in "Self-rated understanding" (earlier values kept in the Note cell).
- **Exam dates**, if they arrived: fill the `[EXAM ...: TBD]` placeholders in `semester/plans/exam-phase-plan.md` and the exam-logistics table of `calendar-and-dates.md`, add them to "Next 10 days" if close, and tell Plan & progress that the countdowns need booking (a message to that session, or an inbox note with a `## For Plan & progress` section).
- **Block log:** append the block outcomes the student reported; blocks still unknown get "not reported" (never invented).
- **Next week:** if next week's page exists with `status: upcoming`, set it `current`. If it already exists, add the rolled-over items as rows marked "(carried over from week N)"; otherwise the week-page job picks them up.
- **Plan & progress:** if the answer changes next week (a new event, a dropped item, a self-rating that triggers the rebalance rule), tell that session in one message (or an inbox note `## For Plan & progress`); never edit the calendar from this job.
- **Failure flag:** last, write or delete it as "Failures" below says.

Then reply with a short summary: done this period, still open, the next deadlines (next 10 days), the bonus standing per course (one line each, with numbers), the files you changed, and `flag written|cleared|none`.

## Failures
- A file you can't read or write: say so at the top of the reply, change nothing in it, carry on with the rest.
- No answer: the session stays open; don't push again. The next check-in folds the unanswered weeks into its question. A missing answer is not a failure of the job: write no flag for it.
- Never send an "all good" push; the one announcement in turn 1 (or, in a run that can't ask, the one "Check-in is due" line) is the only push of this job.
- **Failure flag** (the contract in `_agent/heartbeat/README.md`, "Writing a flag from a job"; create the folder if it is missing):
  - **Write** `_agent/logs/flags/check-in.md` when turn 2 could not write one of the files above, or when turn 1 had to stop because a file it needs (a week page, the dashboard) could not be read. Front matter `job: check-in`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: red`; the first line of the body says in one sentence what was not written and why, with no scores, names or other personal details (e.g. `week-09.md not writable; the answer stays in this session, nothing applied to that page`). If the file exists, overwrite it with the newest text.
  - **Delete** that file (only that one: it is the single file this job may delete) at the end of a turn 2 that wrote everything, and at step 0 when the check-in for the target week is already done.
  - The flag replaces any push of your own: the heartbeat decides whether Alex Example hears about it.

## Never
- Never invent or estimate a score, a submission or a self-rating; never tick an item without the student's word or platform evidence.
- Never store solutions to graded `solo` work or finished code for graded tasks; record only scores and status.
- Never edit, move or delete anything in `semester/prep/`; never change calendar events from this job.
- Never delete week pages, tracker lines or backlog rows (strike through instead); the only file this job ever deletes is its own failure flag.
- No emails, passwords, keys or calendar addresses in any file.

## Final reply
The summary above, after turn 2. Even when every result is already recorded, turn 1 still asks the short reflection lines (focused hours, what worked, what didn't, self-ratings, what rolls over): the check-in section can't be filled without the student.
