# Quiz prep page (job `quiz-prep`)

Purpose: the prep sheet for each graded quiz of the term that is coming up within the next {{study.quiz.prep_lead_days}} days, built before the student needs it, so the prep block has its material. This job runs headless at {{schedule.quiz_prep}} on the dates in `schedule.quiz_prep_dates`; nobody can answer questions during the run, so decide on sensible defaults and state them in your final reply. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Write vault files directly; everything you write is in {{student.language}} (headings, table columns and dates that tools parse stay exactly as given), UTF-8 without BOM, LF line ends.

## Read first
1. `_agent/agent-start.md` and `_agent/rules.md` (real sources only with section and page cited; never skip algebra steps; maths rendered; integrity rules: sheet and assignment tasks stay under their assistance level).
2. `_agent/roles/quiz-coach.md` (rules, quiz variants, output formats) and `_agent/skills/study-page/SKILL.md` (names, properties, checks, twin, card row).
3. For each course with graded quizzes (`[[courses.assessments]]` with `kind = "quiz"` in `_agent/uni-os.toml`): `<course folder>/quiz-prep/<slug>-quiz-prep.md` (quiz facts, the "Planned quizzes" table, the index of earlier prep sheets and reviews), the course card, the error log's "Patterns to watch" (`<course folder>/<slug>-error-log*.md`), `me/weak-spots.md`, and the breakdowns of the earlier quizzes in `quiz-prep/`.

## 0. Should this run do anything?
Whenever this run stops early because there is nothing to do, first delete this job's failure flag if there is one (see "Failure flag" below){{#if modules.vm}}; a failover skip leaves the flag to the machine that ran the slot{{/if}}.
{{#if modules.vm}}- **Failover marker.** Work out this run's nominal slot as `YYYY-MM-DD HH:MM`. If `_agent/vm/ran/quiz-prep.md` exists and its `slot:` line equals that slot, reply one line "Skipped: the host already ran the <slot> slot" and stop.
{{/if}}- **Date.** Get the real local time from the system ({{term.timezone}}): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Term week: week 0 starts on {{term.week0_monday}}.
- **Which quizzes.** Every graded quiz that takes place after now and within the next {{study.quiz.prep_lead_days}} days. Take it from the "Planned quizzes" table of the course's quiz-prep file (run date, quiz in the course's own numbering, quiz date and time, lectures up to, sheet in scope, file stem); if a quiz is missing there, work it out from the quiz facts and the assessment's `schedule`, and say that you inferred it. No quiz in the window: reply one line and stop.
- **Assistance level.** Resolve the quiz's level (the assessment's `assistance`, else the course's, else `study.assistance_default`). `solo` means the course forbids help on it: build nothing for that quiz and say so in one line.

## 1. Stop if it exists
If the prep sheet for that quiz is already there (`<course folder>/quiz-prep/<slug>-quiz-<quiz-id>-prep.html`, or `.md` in a Markdown-only vault, or the file stem in the "Planned quizzes" table), say so in one line and go to the next quiz. The course's quiz-coach session may have built it.

## 2. Scope
Quote the official scope rule from the quiz facts, then map it to this quiz: the lectures up to the cut-off (script sections and printed pages), and the sheet or assignment in scope ("the assignment released that week", "the previous two weeks of lectures"...). Label the mapping **inferred**. If the sheet in scope is not in the vault yet, use the one before and say so. Lecture material comes from the course's real sources (card: "Real sources", page offset); handouts that return empty text are read as page images. If a source for the scope is missing, say which and build from what exists: **never fill in from general knowledge**.

## 3. Content
Follow the prep-sheet format in the course's quiz-prep file (and the newest earlier prep sheet of the course as the model, if there is one): quiz facts box; scope in four lines; weighting; how this quiz asks (patterns from the earlier reviews); core material per topic with origin tags (`Plan W<n>`, `S<k> Ex <j>`, `plan only`, `sheet only`, `edge`) and "In practice" lines, with the course's exact qualifiers; cheat card; short drills on the student's error-log patterns; about ten quick checks with answers checked by code, each labelled with its pattern and origin (`invented`, `adapted from <this term's sheet or quiz>`, `official: <this term's sheet, quiz or practice quiz>`); sheet map, **hints only**; last-minutes do-list; sources and checks.

**Mock**: build the timed mock in the real format as well ({{#if study.quiz.auto_mocks}}`study.quiz.auto_mocks` is on, so for every quiz{{else}}only where the course's quiz facts say "Mock with the prep sheet: yes"; otherwise mention in the reply that a mock is available on request{{/if}}): written quizzes "train at 10, expect 15" (clock shorter than the real quiz), computed answers checked by code, proofs self-marked against a rubric the way the TA would mark them, every problem labelled. A mock's own questions may have worked answers (they are practice).

## 4. Never
- Never use practice material from outside this term's course material; never label a question "official" unless it is this term's official sheet, quiz or practice quiz.
- Never solve the sheet or assignment exercises themselves (hints-only rule, or the course's stricter level); nothing at all for `solo` work.
- Never present an inferred scope as the official one.
- Never edit `semester/prep/`; never rename, move or delete files (the only exception is this job's own failure flag, section 6); never touch the learning platform (no attempts, no submissions).
- No emails, quiz passwords, keys or private calendar addresses in any file. Never send a notification.

## 5. Save
HTML on `_templates/study-page.html` (quick checks = an `instant` quiz, the mock = a `final` quiz with the timer) when this vault's formats include html ({{study.formats}}), otherwise Markdown from `_templates/quiz-prep-sheet.md`. Write `\lt` instead of a bare `<` before a letter inside maths, run `python _agent/tools/check_study_page.py <page.html>` until it reports 0 errors, make the Markdown twin with `python _agent/tools/html2md.py <page.html>`, add one row to the index of `<slug>-quiz-prep.md` and one row to the "In this folder" table of the course card (re-read each file right before editing, keep its properties, bump `updated`).

## 6. Failure flag
{{#if modules.heartbeat}}The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"){{else}}The format is below (the heartbeat module, which normally reads flags, is not installed){{/if}}; create the folder if it is missing.
- **Write** `_agent/logs/flags/quiz-prep.md` when a prep sheet that was due is missing or incomplete after the run: no source for its scope could be opened, a file could not be saved, or the checker still reports errors. Front matter `job: quiz-prep`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: amber` (`red` if the quiz is within 24 hours and no sheet exists); the first line of the body says in one sentence which quiz has no complete sheet and why, with no scores or other personal details (e.g. `LA quiz week9: no prep sheet, the sheet in scope is not in the vault`). If the file exists, overwrite it with the newest text. A pending Markdown twin is not a failure.
- **Delete** that file when the run ends with every due sheet in place, including runs that found nothing to do (no quiz in the window, a `solo` quiz, the sheet already there).
{{#if modules.heartbeat}}
- The flag replaces any notification: the heartbeat decides whether {{student.name}} hears about it.
{{else}}
- No heartbeat is installed (module `heartbeat`), so nobody reads the flag between runs: it is the record for the next run and the next session. Whenever you write it, also put the failure on the first line of your final reply{{#if modules.notifications}} and send one push through the gate, from the vault root: `uni-os push "Quiz prep could not finish; ask any session what failed." --id job:quiz-prep:failed --source quiz-prep` (no file names or details in the text; if `uni-os` is not a command here, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"`; exit 10-13: don't retry, say so in the reply){{/if}}.
{{/if}}

## Final reply
At most 5 lines per quiz: `<COURSE SHORT> <quiz>: <file> | scope used | sheet used | inside: <parts, mock yes/no> | missing or inferred: <...>`, or the one-line reason nothing was built; then `flag written|cleared|none`. No notification: the daily prep picks the page up.
