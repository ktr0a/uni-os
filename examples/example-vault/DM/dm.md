---
type: course
course: dm
bonus_banked: "0 / 0 graded"
bonus_target: "8 points"
next_bonus: ""
updated: 2026-11-07
audience: both
tags: [uni/dm, course]
---
# DM: Discrete Mathematics (Autumn 2026)

Course card. Last reviewed: 2026-11-07 (written by the Uni OS setup from the config; re-check the facts below against the official course pages in the first week). Current points and to-dos: [progress/current-status.md](<../progress/current-status.md>).

> [!info]- How this card is kept up to date
> - This card is the single source of truth for this course's facts: rhythm, deadlines, rooms, assessment rules, bonus rule, help policy, sources, page offsets. Any agent that learns a course fact edits it here, in place, in the same turn.
> - Exception: the graded-streams table and the assistance level under "Weekly rhythm and bonus" sit between `uni-os:begin` / `uni-os:end` marker lines and are generated from the config (`assistance` and `[[courses.assessments]]` of this course in `_agent/uni-os.toml`). To change a stream or the assistance level, change the config and run `uni-os render`: it refreshes that part even after this card was edited and keeps everything else. Text typed between the markers is overwritten.
> - When a new fact corrects an older one, keep the trace in the line: "(Corrected Thu 22 Oct 2026: sheets come out Thursday; older notes said Friday because of corrected re-uploads.)" Settled questions get "Settled <date> (<who>): ...".
> - Mark estimates "(est.)" and inferences "(inferred)", and say what would replace them with a real number.
> - Keep the properties at the top in their shape: `bonus_banked` starts with an `x / y` pair, `bonus_target` may say `~N pts (est.)`, `next_bonus` starts with a date like `Tue 3 Nov 23:59`. Dashboards parse them.
> - Results and scores go to the bonus properties above and to `progress/current-status.md` plus `progress/tracker-log.md`, not into long narratives here. Progress stories belong on the week pages.
> - Every new file in this folder gets one row in "In this folder" below. Every lecture gets one line in "Lecture log".

## Facts
- Course: Discrete Mathematics (DM) · language: English
- Lecturers: (not recorded yet)
- Moodle course page: (add the link)
- Lectures: Mon 08:15-10:00, Wed 08:15-10:00
- Recordings: (say whether lectures are recorded or streamed, and where)
- Exercise session: Tue 16:15-18:00
  - (Add the room, the TA's role, the language and how the session runs: class, then supervised work; group work; peer grading; attendance rule. Other groups' regular slots are not extra sessions.)
- Exam format (logistics only: length, mode, language, allowed aids): (add once the course catalogue or the course page states it; note it if the two disagree)
- Exam session: 2027-01-25 to 2027-02-19 (dates only; the official exam timetable is binding)
- Course events that are not weekly (official mock or practice runs, timed bonus tasks, orals): (date, time, place, rules; one line each)

## Weekly rhythm and bonus
<!-- uni-os:begin assessments -->
<!-- Generated from the config (this course's assistance and [[courses.assessments]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Stream | Kind | Rhythm | Counts for | Points | Help allowed |
|---|---|---|---|---|---|
| Graded sheets | sheet | every second week | bonus | 2 | **solo** |
| Practice sheets | sheet | weekly | none | - | hints-only |

- **Help allowed for this course:** `hints-only` by default; per-stream overrides are in the table above. Legend: `solo` = the agent gives no help at all on that work (no solving, no hints, no checks; it is never discussed, logged or linked); `hints-only` = smallest hint first, technique on a different example, checking your own steps, never your proof, answer or code; `coach` = hints plus review of your own work and worked explanations of similar tasks; `full` = worked solutions, only where the course allows it.
<!-- uni-os:end assessments -->

- Sheets: released Mon 12:00 · due Mon 12:00, one week later · hand-in: (channel: LMS upload, git push, paper, not handed in; who submits in a group)
- **Session rule (what the exercise session of week n covers):** (not set yet. Write it as "In the <day> session of week n: <which sheet is discussed>, <what happens in the room>, <which sheet comes out>." This is the most important line on the card: an exercise session almost never covers that same day's material; it lags the lectures, and the lag differs per course.)
- Week numbering: (say how the course numbers its weeks and sheets compared with term weeks, e.g. "LMS 'Week k' = term week k-1", "sheet number = term week + 1"; week 0 starts Mon 2026-09-14)
- **Bonus** (scheme `points`): Up to 2 points per graded sheet; 8 points give +0.25
  - Rule: Bonus = 0.25 * min(points, 8) / 8.
  - Maximum: 0.25
  - Full bonus at: 8 points
  - Valid for: (which exam session(s) the bonus counts for; whether it is added before or after rounding)
- Update `bonus_target` as soon as a sheet, the grade files or a TA gives real numbers. Bonus totals are often never published: keep an explicit estimate with its reasoning, labelled "(est.)".
- **Integrity (official rule):** (copy the course's own rule here: what is allowed, what is not, what happens on copying, what it says about AI)

## Conventions
- Notation used in this course: (e.g. "every plain log is log base 2", "indices start at 1", "vectors in round brackets")
- How the TAs grade: (fill in when the first corrections come back, e.g. "each 2-point task = 1 right idea + 1 formally correct exposition; most lost points were exposition")
- My routine for this course: (when sheets start, cold-attempt timers, when hints are allowed)
- Exercise help for this course follows the exercise-help role at the assistance level above (`hints-only` unless a stream says otherwise): smallest hint first, a time cap per task part, then the missing idea in one line; the sticking point goes into the error log.

## Real sources (cite pages)
- Ground truth for "what was lectured": (say which documents count, in order, e.g. "the LMS roadmap says what was lectured, then the script sections"; "the official weekly handout first, then the script pages")
- Page offsets (printed page numbers are what you cite; the offset is what you need to open the right PDF page):

| Source | Rule |
|---|---|
| (script or deck) | (e.g. PDF page = printed page + 8) |

- A lecture deck is the whole chapter, not what was covered: only the student's word (or a transcript matched to the slides) says where a lecture stopped.
- Content comes only from real sources (script, slides, official handouts, the LMS roadmap), with section and page cited. If a source can't be opened, say so instead of filling in.
- Previous years' material (older scripts, sheets, recordings) helps to predict, never to decide: last year's lecture on the same weekday is about 364 days earlier. Note here where such material lives, how its numbering differs, and what changed this year (new script version, changed bonus scheme). Old sheets with official solutions: only after the student's own attempt.
- Script versions: say which version (date) you cite. A new version can shift page offsets and numbering; re-check the offset table when one arrives.
- PDFs that read badly: handwritten lecture slides and scans have little or no text layer, so read page images; a script too large to read in one go gets a text copy in `reference/` (for searching only; the PDF wins).

## Lecture log
One line per lecture: what was covered, from the student's word or the slides actually reached. Mark inferred stop points as inferred.

| # | Date | Covered (source) |
|---|---|---|

## Known gaps and open questions
- (What cannot be obtained, e.g. "old sheets are behind a login: not obtainable, never enter the password")
- (What is not published, e.g. "semester maximum points not published; the estimate above is ours")
- (What is still open, with who can answer it: the TA, the course page, the student)

## Official files
The university's files live in these subfolders, under their official names:
- `DM assignments/`
- `DM script/`
- `DM handwritten/`: PDFs exported by the tablet note app (written only by the app; agents read and link, never write there)

Rules for the official subfolders (the handwritten folder belongs to the note app: agents never add anything there):
- Keep the official file name. An agent may add a newly downloaded official file to the matching subfolder, but never renames, moves or deletes an existing one. A superseded version moves, under its own name, to `z_archive/DM-outdated-YYYY-MM-DD/` at the vault root, only by the student or on the student's direct OK; it is never overwritten or deleted.
- Link files by relative path in angle brackets, with a page where useful, e.g. `[Sheet 3](<assignments/sheet03.pdf>)` or `[Script p. 41](<script and slides/script.pdf#page=49>)` (PDF page = printed page + 8). Several folders hold files with the same name, so never link by bare name.
- An agent-typed text copy of an official file (when a PDF can't be read) is named `<official name>-transcript.md` and says at the top: "If this copy and the PDF ever differ, the PDF wins."

## In this folder
Study pages come in this vault's formats (html, md): an interactive HTML original plus a Markdown copy with the same name that reads in Obsidian. All study pages of this course: [Study pages view](<../views/Study pages.base>). One row per file or folder, newest at the bottom of each group; each row says what it is, the date and who made it, e.g. `| [dm-<topic>-study-page](<notes/dm-<topic>-study-page.md>) · [interactive HTML](<notes/dm-<topic>-study-page.html>) | <topic>, script ch. 3 (Tue 13 Oct, lecture rundown) |`. File names follow the scheme in [notes/README.md](<notes/README.md>).

| Path | What |
|---|---|
| [backlog.md](<backlog.md>) | Parked tasks, with why and estimated minutes |
| [dm-error-log.md](<dm-error-log.md>) | Error log: one row per error or point of confusion, with recurring patterns |
| [notes/](<notes/README.md>) | Study pages, lecture notes, summaries, cheat sheets |
| `quiz-prep/` | Graded-quiz prep sheets, mock quizzes, review extracts and breakdowns |
| [reference/dm-topic-plan.md](<reference/dm-topic-plan.md>) | Predicted per-week content map (not authoritative) |
| [reference/dm-course-guide.md](<reference/dm-course-guide.md>) | One-page course guide: week, sessions, bonus, integrity, where to look |
| `DM handwritten/` | Handwritten notes exported by the tablet app (read only) |
