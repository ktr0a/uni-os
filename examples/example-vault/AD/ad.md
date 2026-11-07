---
type: course
course: algo
bonus_banked: "0 / 0 graded"
bonus_target: "80 % of all sheet points"
next_bonus: ""
updated: 2026-11-07
audience: both
tags: [uni/algo, course]
---
# AD: Algorithms and Data Structures (Autumn 2026)

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
- Course: Algorithms and Data Structures (AD) · 8 ECTS · language: English
- Lecturers: (not recorded yet)
- Moodle course page: https://lms.example.edu/course/algo
- Course website: https://algo.example.edu
- Other platforms: online judge with hidden tests (programming tasks)
- Lectures: Tue 10:15-12:00, Thu 10:15-12:00
- Recordings: recorded, usually online the next day
- Exercise session: Wed 14:15-16:00 · my group: group 3
  - (Add the room, the TA's role, the language and how the session runs: class, then supervised work; group work; peer grading; attendance rule. Other groups' regular slots are not extra sessions.)
- Exam format (logistics only: length, mode, language, allowed aids): written, 120 min, English, one handwritten A4 sheet allowed
- Exam session: 2027-01-25 to 2027-02-19 (dates only; the official exam timetable is binding)
- Course events that are not weekly (official mock or practice runs, timed bonus tasks, orals): (date, time, place, rules; one line each)

## Weekly rhythm and bonus
<!-- uni-os:begin assessments -->
<!-- Generated from the config (this course's assistance and [[courses.assessments]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Stream | Kind | Rhythm | Counts for | Points | Help allowed |
|---|---|---|---|---|---|
| Weekly exercise sheets | sheet | out Thu, due the next Thu 23:59 | bonus | not published | hints-only |
| In-class quizzes | quiz | weeks 4, 8 and 12, in the exercise session | bonus | 10 | hints-only |

- **Help allowed for this course:** `hints-only` by default; per-stream overrides are in the table above. Legend: `solo` = the agent gives no help at all on that work (no solving, no hints, no checks; it is never discussed, logged or linked); `hints-only` = smallest hint first, technique on a different example, checking your own steps, never your proof, answer or code; `coach` = hints plus review of your own work and worked explanations of similar tasks; `full` = worked solutions, only where the course allows it.
<!-- uni-os:end assessments -->

- Sheets: released Thu 12:00 · due Thu 23:59, one week later · hand-in: LMS upload, one PDF per person
- **Session rule (what the exercise session of week n covers):** The exercise session of week n discusses sheet n-1 and introduces sheet n.
- Week numbering: Sheet k is released in term week k.
- **Bonus** (scheme `threshold`): +0.25 grade bonus at 80 % of all sheet points
  - Rule: Sum of sheet points over the term; quizzes count double.
  - Maximum: 0.25
  - Full bonus at: 80 % of all sheet points
  - Valid for: (which exam session(s) the bonus counts for; whether it is added before or after rounding)
- Update `bonus_target` as soon as a sheet, the grade files or a TA gives real numbers. Bonus totals are often never published: keep an explicit estimate with its reasoning, labelled "(est.)".
- **Integrity (official rule):** Sheets are individual work; AI may explain concepts, never produce solutions.

## Conventions
- Written answers use the pseudocode conventions of the script.
- Notation used in this course: (e.g. "every plain log is log base 2", "indices start at 1", "vectors in round brackets")
- How the TAs grade: (fill in when the first corrections come back, e.g. "each 2-point task = 1 right idea + 1 formally correct exposition; most lost points were exposition")
- My routine for this course: (when sheets start, cold-attempt timers, when hints are allowed)
- Exercise help for this course follows the exercise-help role at the assistance level above (`hints-only` unless a stream says otherwise): smallest hint first, a time cap per task part, then the missing idea in one line; the sticking point goes into the error log.

## Real sources (cite pages)
- Ground truth for "what was lectured": the lecture script and the slides on the LMS
- Page offsets (printed page numbers are what you cite; the offset is what you need to open the right PDF page):

| Source | Rule |
|---|---|
| Script 2026 (PDF) | PDF page = printed page + 2 |

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
- `AD assignments/`
- `AD slides & script/`
- `AD handwritten/`: PDFs exported by the tablet note app (written only by the app; agents read and link, never write there)

Rules for the official subfolders (the handwritten folder belongs to the note app: agents never add anything there):
- Keep the official file name. An agent may add a newly downloaded official file to the matching subfolder, but never renames, moves or deletes an existing one. A superseded version moves, under its own name, to `z_archive/AD-outdated-YYYY-MM-DD/` at the vault root, only by the student or on the student's direct OK; it is never overwritten or deleted.
- Link files by relative path in angle brackets, with a page where useful, e.g. `[Sheet 3](<assignments/sheet03.pdf>)` or `[Script p. 41](<script and slides/script.pdf#page=49>)` (PDF page = printed page + 8). Several folders hold files with the same name, so never link by bare name.
- An agent-typed text copy of an official file (when a PDF can't be read) is named `<official name>-transcript.md` and says at the top: "If this copy and the PDF ever differ, the PDF wins."

## In this folder
Study pages come in this vault's formats (html, md): an interactive HTML original plus a Markdown copy with the same name that reads in Obsidian. All study pages of this course: [Study pages view](<../views/Study pages.base>). One row per file or folder, newest at the bottom of each group; each row says what it is, the date and who made it, e.g. `| [ad-<topic>-study-page](<notes/ad-<topic>-study-page.md>) · [interactive HTML](<notes/ad-<topic>-study-page.html>) | <topic>, script ch. 3 (Tue 13 Oct, lecture rundown) |`. File names follow the scheme in [notes/README.md](<notes/README.md>).

| Path | What |
|---|---|
| [backlog.md](<backlog.md>) | Parked tasks, with why and estimated minutes |
| [ad-error-log.md](<ad-error-log.md>) | Error log: one row per error or point of confusion, with recurring patterns |
| [notes/](<notes/README.md>) | Study pages, lecture notes, summaries, cheat sheets |
| `quiz-prep/` | Graded-quiz prep sheets, mock quizzes, review extracts and breakdowns |
| [reference/ad-topic-plan.md](<reference/ad-topic-plan.md>) | Predicted per-week content map (not authoritative) |
| [reference/ad-course-guide.md](<reference/ad-course-guide.md>) | One-page course guide: week, sessions, bonus, integrity, where to look |
| `AD handwritten/` | Handwritten notes exported by the tablet app (read only) |
