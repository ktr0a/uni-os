---
type: overview
audience: both
updated: {{generated.date}}
tags: [uni/overview]
---
# Courses ({{university.short}} {{term.label}}, {{university.programme}})

All courses at a glance. The facts here are a summary: each course card is the source of truth for its course.

The tables between the marker lines (`<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->`, visible in the file's source) are generated from the config, `[[courses]]` in `_agent/uni-os.toml`, and the enabled modules. `uni-os render` refreshes them whenever the config changes, also after this page was edited elsewhere (everything outside the markers is kept). So when a card corrects a fact that appears in one of them, change the config too and render; text typed between the markers is overwritten. The per-week content map at the bottom is not generated: it is yours and the agents' to fill.

<!-- uni-os:begin courses -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Card | Lectures | Exercise session | Bonus scheme | Full bonus at |
|---|---|---|---|---|---|
{{#each courses}}| {{course.short}} {{course.name}} | [{{course.slug}}.md](<{{course.folder}}/{{course.slug}}.md>) | {{#if course.lecture_slots}}{{course.lecture_slots}}{{else}}?{{/if}} | {{#if course.exercise_slots}}{{course.exercise_slots}}{{else}}?{{/if}}{{#if course.exercise_group}} ({{course.exercise_group}}){{/if}} | {{#if course.bonus.scheme}}{{course.bonus.scheme}}{{#if course.bonus.description}}: {{course.bonus.description}}{{/if}}{{else}}none{{/if}} | {{#if course.bonus.target}}{{course.bonus.target}}{{else}}{{#if course.bonus.scheme}}not known yet{{else}}-{{/if}}{{/if}}{{#if course.bonus.max_bonus}} (max {{course.bonus.max_bonus}}){{/if}} |
{{/each}}
<!-- uni-os:end courses -->

Term: week 0 starts Mon {{term.week0_monday}}; week n starts week 0 + 7n days.{{#if term.last_lecture_day}} Last lecture day {{term.last_lecture_day}}.{{/if}}{{#if term.exam_session_start}} Exam session {{term.exam_session_start}} to {{term.exam_session_end}}.{{/if}}{{#if modules.progress}} Current standing: [progress/current-status.md](<progress/current-status.md>).{{/if}}

## Weekly rhythm and session offsets
An exercise session almost never covers the material of that same day's or week's lectures: it lags, and the lag differs per course. Getting this wrong is the main failure mode when answering "what does today's session cover?".

<!-- uni-os:begin rhythm -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Sheets out | Due | Session rule (what the exercise session of week n covers) | Week numbering |
|---|---|---|---|---|
{{#each courses}}| {{course.short}} | {{#if course.sheet_release}}{{course.sheet_release}}{{else}}?{{/if}} | {{#if course.sheet_due}}{{course.sheet_due}}{{else}}?{{/if}} | {{#if course.session_rule}}{{course.session_rule}}{{else}}(not set yet){{/if}} | {{#if course.week_numbering}}{{course.week_numbering}}{{else}}same as term weeks?{{/if}} |
{{/each}}
<!-- uni-os:end rhythm -->

## Help allowed per course
Default assistance level and the official rule. Per-stream overrides are on each course card. `solo` means the agent gives no help at all on that work.

<!-- uni-os:begin help -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Default | Official rule |
|---|---|---|
{{#each courses}}| {{course.short}} | `{{course.assistance}}` | {{#if course.integrity}}{{course.integrity}}{{else}}(add from the course page){{/if}} |
{{/each}}
<!-- uni-os:end help -->

## Same layout in every course folder
<!-- uni-os:begin layout -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current. -->
| Item | What goes there |
|---|---|
| `<slug>.md` (e.g. `{{#each courses}}{{#if @first}}{{course.slug}}.md{{/if}}{{/each}}`) | Course card: facts, weekly rhythm, assessments, bonus, help policy, real sources with page offsets, lecture log, known gaps, official files, file index |
| `backlog.md` | Parked tasks with why and estimated minutes |
{{#if modules.error-logs}}| `<slug>-error-log*.md` | Error log(s): date, where, what went wrong, the correct idea, source; recurring patterns |
{{/if}}| `notes/` | Study pages, lecture notes, summaries, cheat sheets. **New study material lands here.** |
{{#if modules.quiz-coaching}}| `quiz-prep/` | Graded-quiz checklists, mock quizzes, review extracts, breakdowns |
{{/if}}| `reference/` | Predicted topic plan (`<slug>-topic-plan.md`), course guide (`<slug>-course-guide.md`), script indexes, text copies of scripts too big to read |
| Official subfolders | The university's files under their official names (sheets, solutions, script, slides, handouts). Add-only |
{{#if modules.handwritten-notes}}| `<folder> handwritten/` (default name; `handwritten_folder` in the config overrides it) | PDFs exported by the tablet note app. Written only by the app |
{{/if}}
<!-- uni-os:end layout -->

Official subfolders per course:

<!-- uni-os:begin official-subfolders -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Folder | Official subfolders |
|---|---|---|
{{#each courses}}| {{course.short}} | `{{course.folder}}/` | {{#each course.official_subfolders}}`{{item}}/`{{#unless @last}}, {{/unless}}{{else}}(none configured yet){{/each}}{{#if modules.handwritten-notes}}, `{{course.handwritten_dir}}/` (tablet app){{/if}} |
{{/each}}
<!-- uni-os:end official-subfolders -->

## Filing rules (all course folders)
1. **Sources are add-only.** Official files keep their official names. An agent may add a newly downloaded official file to the matching subfolder and link it from the course card; it never renames, moves or deletes an existing one. A newer version of an official file replaces the old one only on the student's direct OK, and the old copy moves, under its own name, to `z_archive/<course folder>-outdated-YYYY-MM-DD/` at the vault root, never deleted.
2. **Notes and sources never mix.** Agent-made files go into `notes/`, `reference/`{{#if modules.quiz-coaching}}, `quiz-prep/`{{/if}} or the course folder's top level (card, backlog{{#if modules.error-logs}}, error logs{{/if}}). Nothing agent-made goes into an official subfolder{{#if modules.handwritten-notes}} or the handwritten folder{{/if}}.
3. **Unique names.** Notes are lowercase-kebab-case, start with the course slug and end with the kind of note (`<slug>-<what>-<kind>.md`, e.g. `<slug>-heaps-study-page.md`, `<slug>-weeks3-4-recap.md`; the list is in each course's `notes/README.md`). Official files can share names across folders (`lecture01.pdf`, `solution01.pdf`), so always link by relative path, never by bare name.
4. **Text copies are marked.** When a PDF can't be read and an agent types a copy, it is `<official name>-transcript.md` and says "If this copy and the PDF ever differ, the PDF wins."
5. **Every new file is indexed.** One row in the course card's "In this folder" table, with what it is, the date and who made it.
6. **Graded solo work stays out.** Nothing that solves, hints at or summarises work marked `solo` is stored anywhere in the vault{{#if modules.handwritten-notes}}, including the student's handwritten work on it{{/if}}.

## Colour convention
Each course has one colour, used in the calendar, the Obsidian graph and folders, dashboards and course guides. Darker shade = lectures, lighter shade = exercise sessions. Other areas (`me/`, `progress/`, `semester/`, deadlines, agent notes) get clearly different colours: never give two areas similar colours. A calendar may instead use one colour per event type (all lectures one colour, all exercise sessions another); say which convention you use.

<!-- uni-os:begin colours -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Main colour | Lighter (exercise) |
|---|---|---|
{{#each courses}}| {{course.short}} | `{{course.colour}}` | {{#if course.colour_light}}`{{course.colour_light}}`{{else}}(lighter shade of the main colour){{/if}} |
{{/each}}
<!-- uni-os:end colours -->

## Page offsets (printed vs PDF)
Cite printed page numbers; use the offset to open the right PDF page. Offsets differ per script and even per file, and can change with a new script version.

<!-- uni-os:begin page-offsets -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Source | Rule |
|---|---|---|
{{#each courses}}{{#each course.page_offsets}}| {{course.short}} | {{item.source}} | {{item.rule}} |
{{/each}}{{/each}}
<!-- uni-os:end page-offsets -->

Whenever you meet a new script, deck or handout with an offset, add it to the course card's offset table and to the course's `page_offsets` in the config; the next `uni-os render` adds the row here. Typical rules: "PDF page = printed page + 8", "printed = PDF - 1", "part II: printed = PDF, may renumber". Previous years' scripts have their own offsets.

## Per-week content map (predicted)
One line per term week and course: lecture numbers · topic · sheet number · **graded fixtures in bold**. Derived from the per-course topic plans (`<folder>/reference/<slug>-topic-plan.md`); verify on the official pages when it matters.

| W | Starts (Mon) |{{#each courses}} {{course.short}} |{{/each}}
|---|---|{{#each courses}}---|{{/each}}
| 0 | {{term.week0_monday}} |{{#each courses}} |{{/each}}

(Setup or the first planning session adds one row per term week up to the last lecture week. A course added later gets its column here by hand.)
