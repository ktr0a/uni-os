---
type: course
course: {{course.id}}
bonus_banked: "{{#if course.bonus.scheme}}0 / 0 graded{{else}}none{{/if}}"
bonus_target: "{{#if course.bonus.target}}{{course.bonus.target}}{{else}}{{#if course.bonus.scheme}}not known yet{{else}}no bonus{{/if}}{{/if}}"
next_bonus: ""
updated: {{generated.date}}
audience: both
tags: [uni/{{course.id}}, course]
---
# {{course.short}}: {{course.name}} ({{term.label}})

Course card. Last reviewed: {{generated.date}} (written by the Uni OS setup from the config; re-check the facts below against the official course pages in the first week).{{#if modules.progress}} Current points and to-dos: [progress/current-status.md](<../progress/current-status.md>).{{/if}}

> [!info]- How this card is kept up to date
> - This card is the single source of truth for this course's facts: rhythm, deadlines, rooms, assessment rules, bonus rule, help policy, sources, page offsets. Any agent that learns a course fact edits it here, in place, in the same turn.
> - Exception: the graded-streams table and the assistance level under "Weekly rhythm and bonus" sit between `uni-os:begin` / `uni-os:end` marker lines and are generated from the config (`assistance` and `[[courses.assessments]]` of this course in `_agent/uni-os.toml`). To change a stream or the assistance level, change the config and run `uni-os render`: it refreshes that part even after this card was edited and keeps everything else. Text typed between the markers is overwritten.
> - When a new fact corrects an older one, keep the trace in the line: "(Corrected Thu 22 Oct 2026: sheets come out Thursday; older notes said Friday because of corrected re-uploads.)" Settled questions get "Settled <date> (<who>): ...".
> - Mark estimates "(est.)" and inferences "(inferred)", and say what would replace them with a real number.
> - Keep the properties at the top in their shape: `bonus_banked` starts with an `x / y` pair, `bonus_target` may say `~N pts (est.)`, `next_bonus` starts with a date like `Tue 3 Nov 23:59`. Dashboards parse them.
> - Results and scores go to the bonus properties above{{#if modules.progress}} and to `progress/current-status.md` plus `progress/tracker-log.md`{{/if}}, not into long narratives here. Progress stories belong on the week pages.
> - Every new file in this folder gets one row in "In this folder" below. Every lecture gets one line in "Lecture log".

## Facts
- Course: {{course.name}} ({{course.short}}){{#if course.ects}} · {{course.ects}} ECTS{{/if}} · language: {{course.language}}
- Lecturers: {{#if course.lecturers}}{{course.lecturers}}{{else}}(not recorded yet){{/if}}
- {{university.lms}} course page: {{#if course.lms_url}}{{course.lms_url}}{{else}}(add the link){{/if}}
{{#if course.website}}
- Course website: {{course.website}}
{{/if}}
{{#if course.platforms}}
- Other platforms: {{course.platforms}}
{{/if}}
- Lectures: {{#if course.lecture_slots}}{{course.lecture_slots}}{{else}}(add day, time and room){{/if}}
- Recordings: {{#if course.recordings}}{{course.recordings}}{{else}}(say whether lectures are recorded or streamed, and where){{/if}}
- Exercise session: {{#if course.exercise_slots}}{{course.exercise_slots}}{{else}}(add day, time and room){{/if}}{{#if course.exercise_group}} · my group: {{course.exercise_group}}{{/if}}
  - (Add the room, the TA's role, the language and how the session runs: class, then supervised work; group work; peer grading; attendance rule. Other groups' regular slots are not extra sessions.)
- Exam format (logistics only: length, mode, language, allowed aids): {{#if course.exam_format}}{{course.exam_format}}{{else}}(add once the course catalogue or the course page states it; note it if the two disagree){{/if}}
{{#if term.exam_session_start}}
- Exam session: {{term.exam_session_start}} to {{term.exam_session_end}} (dates only; the official exam timetable is binding)
{{/if}}
- Course events that are not weekly (official mock or practice runs, timed bonus tasks, orals): (date, time, place, rules; one line each)

## Weekly rhythm and bonus
<!-- uni-os:begin assessments -->
<!-- Generated from the config (this course's assistance and [[courses.assessments]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Stream | Kind | Rhythm | Counts for | Points | Help allowed |
|---|---|---|---|---|---|
{{#each course.assessments}}| {{item.name}} | {{item.kind}} | {{#if item.schedule}}{{item.schedule}}{{else}}(when, window, timer){{/if}} | {{item.counts_for}} | {{#if item.points_max}}{{item.points_max}}{{else}}{{#if item.counts_for}}not published{{else}}-{{/if}}{{/if}} | {{#if item.assistance == "solo"}}**solo**{{else}}{{item.assistance}}{{/if}} |
{{else}}| (no graded streams configured yet) | | | | | |
{{/each}}

- **Help allowed for this course:** `{{course.assistance}}` by default; per-stream overrides are in the table above. Legend: `solo` = the agent gives no help at all on that work (no solving, no hints, no checks; it is never discussed, logged or linked); `hints-only` = smallest hint first, technique on a different example, checking your own steps, never your proof, answer or code; `coach` = hints plus review of your own work and worked explanations of similar tasks; `full` = worked solutions, only where the course allows it.
<!-- uni-os:end assessments -->

- Sheets: released {{#if course.sheet_release}}{{course.sheet_release}}{{else}}(day and time){{/if}} · due {{#if course.sheet_due}}{{course.sheet_due}}{{else}}(day and time){{/if}} · hand-in: {{#if course.hand_in}}{{course.hand_in}}{{else}}(channel: LMS upload, git push, paper, not handed in; who submits in a group){{/if}}
- **Session rule (what the exercise session of week n covers):** {{#if course.session_rule}}{{course.session_rule}}{{else}}(not set yet. Write it as "In the <day> session of week n: <which sheet is discussed>, <what happens in the room>, <which sheet comes out>." This is the most important line on the card: an exercise session almost never covers that same day's material; it lags the lectures, and the lag differs per course.){{/if}}
- Week numbering: {{#if course.week_numbering}}{{course.week_numbering}}{{else}}(say how the course numbers its weeks and sheets compared with term weeks, e.g. "LMS 'Week k' = term week k-1", "sheet number = term week + 1"; week 0 starts Mon {{term.week0_monday}}){{/if}}
{{#each course.assessments}}
{{#if item contains "scope"}}
- Scope of "{{item.name}}" (quote the official wording, mark inferred parts): {{item.scope}}
{{/if}}
{{/each}}
{{#if course.bonus.scheme}}
- **Bonus** (scheme `{{course.bonus.scheme}}`): {{#if course.bonus.description}}{{course.bonus.description}}{{else}}(how it is earned){{/if}}
  - Rule: {{#if course.bonus.rule}}{{course.bonus.rule}}{{else}}(the official formula, verbatim){{/if}}
  - Maximum: {{#if course.bonus.max_bonus}}{{course.bonus.max_bonus}}{{else}}(cap, e.g. +0.25 grade){{/if}}
  - Full bonus at: {{#if course.bonus.target}}{{course.bonus.target}}{{else}}(not known yet){{/if}}
  - Valid for: (which exam session(s) the bonus counts for; whether it is added before or after rounding)
{{else}}
- **Bonus:** this course has no bonus scheme (configured as `none`).
{{/if}}
- Update `bonus_target` as soon as a sheet, the grade files or a TA gives real numbers. Bonus totals are often never published: keep an explicit estimate with its reasoning, labelled "(est.)".
- **Integrity (official rule):** {{#if course.integrity}}{{course.integrity}}{{else}}(copy the course's own rule here: what is allowed, what is not, what happens on copying, what it says about AI){{/if}}

## Conventions
{{#each course.notes}}- {{item}}
{{/each}}- Notation used in this course: (e.g. "every plain log is log base 2", "indices start at 1", "vectors in round brackets")
- How the TAs grade: (fill in when the first corrections come back, e.g. "each 2-point task = 1 right idea + 1 formally correct exposition; most lost points were exposition")
- My routine for this course: (when sheets start, cold-attempt timers, when hints are allowed)
{{#if modules.exercise-help}}- Exercise help for this course follows the exercise-help role at the assistance level above (`{{course.assistance}}` unless a stream says otherwise): smallest hint first, a time cap per task part, then the missing idea in one line{{#if modules.error-logs}}; the sticking point goes into the error log{{/if}}.
{{/if}}

## Real sources (cite pages)
- Ground truth for "what was lectured": {{#if course.real_source}}{{course.real_source}}{{else}}(say which documents count, in order, e.g. "the LMS roadmap says what was lectured, then the script sections"; "the official weekly handout first, then the script pages"){{/if}}
- Page offsets (printed page numbers are what you cite; the offset is what you need to open the right PDF page):

| Source | Rule |
|---|---|
{{#each course.page_offsets}}| {{item.source}} | {{item.rule}} |
{{/each}}{{#unless course.page_offsets}}| (script or deck) | (e.g. PDF page = printed page + 8) |
{{/unless}}

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
{{#each course.official_subfolders}}- `{{item}}/`
{{else}}- (none configured yet: one folder per kind of file the course publishes, e.g. `assignments/`, `assignments/solutions/`, `script and slides/`)
{{/each}}{{#if modules.handwritten-notes}}- `{{course.handwritten_dir}}/`: PDFs exported by the tablet note app (written only by the app; agents read and link, never write there)
{{/if}}

Rules for the official subfolders{{#if modules.handwritten-notes}} (the handwritten folder belongs to the note app: agents never add anything there){{/if}}:
- Keep the official file name. An agent may add a newly downloaded official file to the matching subfolder, but never renames, moves or deletes an existing one. A superseded version moves, under its own name, to `z_archive/{{course.folder}}-outdated-YYYY-MM-DD/` at the vault root, only by the student or on the student's direct OK; it is never overwritten or deleted.
- Link files by relative path in angle brackets, with a page where useful, e.g. `[Sheet 3](<assignments/sheet03.pdf>)` or `[Script p. 41](<script and slides/script.pdf#page=49>)` (PDF page = printed page + 8). Several folders hold files with the same name, so never link by bare name.
- An agent-typed text copy of an official file (when a PDF can't be read) is named `<official name>-transcript.md` and says at the top: "If this copy and the PDF ever differ, the PDF wins."

## In this folder
{{#if modules.study-pages}}Study pages come in this vault's formats ({{study.formats}}): {{#if study.formats contains "html"}}{{#if study.formats contains "md"}}an interactive HTML original plus a Markdown copy with the same name{{#if obsidian.enabled}} that reads in Obsidian{{/if}}{{else}}an interactive HTML page that opens in the browser{{/if}}{{else}}Markdown pages{{#if obsidian.enabled}} that read in Obsidian{{/if}}{{/if}}. {{/if}}{{#if modules.obsidian}}All study pages of this course: [Study pages view](<../views/Study pages.base>). {{/if}}One row per file or folder, newest at the bottom of each group; each row says what it is, the date and who made it, e.g. {{#if study.formats contains "md"}}`| [{{course.slug}}-<topic>-study-page](<notes/{{course.slug}}-<topic>-study-page.md>){{#if study.formats contains "html"}} · [interactive HTML](<notes/{{course.slug}}-<topic>-study-page.html>){{/if}} | <topic>, script ch. 3 (Tue 13 Oct, lecture rundown) |`{{else}}`| [{{course.slug}}-<topic>-study-page](<notes/{{course.slug}}-<topic>-study-page.html>) | <topic>, script ch. 3 (Tue 13 Oct, lecture rundown) |`{{/if}}. File names follow the scheme in [notes/README.md](<notes/README.md>).

| Path | What |
|---|---|
| [backlog.md](<backlog.md>) | Parked tasks, with why and estimated minutes |
{{#if modules.error-logs}}
{{#each course.error_logs}}
| [{{item.file}}](<{{item.file}}>) | {{item.title}}: one row per error or point of confusion, with recurring patterns |
{{/each}}
{{/if}}
| [notes/](<notes/README.md>) | Study pages, lecture notes, summaries, cheat sheets |
{{#if modules.quiz-coaching}}| `quiz-prep/` | Graded-quiz prep sheets, mock quizzes, review extracts and breakdowns |
{{/if}}| [reference/{{course.slug}}-topic-plan.md](<reference/{{course.slug}}-topic-plan.md>) | Predicted per-week content map (not authoritative) |
| [reference/{{course.slug}}-course-guide.md](<reference/{{course.slug}}-course-guide.md>) | One-page course guide: week, sessions, bonus, integrity, where to look |
{{#if modules.handwritten-notes}}| `{{course.handwritten_dir}}/` | Handwritten notes exported by the tablet app (read only) |
{{/if}}
