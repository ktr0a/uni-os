---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/overview]
---
# Courses (EIT Autumn 2026, BSc Computer Science)

All courses at a glance. The facts here are a summary: each course card is the source of truth for its course.

The tables between the marker lines (`<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->`, visible in the file's source) are generated from the config, `[[courses]]` in `_agent/uni-os.toml`, and the enabled modules. `uni-os render` refreshes them whenever the config changes, also after this page was edited elsewhere (everything outside the markers is kept). So when a card corrects a fact that appears in one of them, change the config too and render; text typed between the markers is overwritten. The per-week content map at the bottom is not generated: it is yours and the agents' to fill.

<!-- uni-os:begin courses -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Card | Lectures | Exercise session | Bonus scheme | Full bonus at |
|---|---|---|---|---|---|
| AD Algorithms and Data Structures | [ad.md](<AD/ad.md>) | Tue 10:15-12:00, Thu 10:15-12:00 | Wed 14:15-16:00 (group 3) | threshold: +0.25 grade bonus at 80 % of all sheet points | 80 % of all sheet points (max 0.25) |
| DM Discrete Mathematics | [dm.md](<DM/dm.md>) | Mon 08:15-10:00, Wed 08:15-10:00 | Tue 16:15-18:00 | points: Up to 2 points per graded sheet; 8 points give +0.25 | 8 points (max 0.25) |
| LA Linear Algebra | [la.md](<LA/la.md>) | Mon 13:15-15:00, Fri 10:15-12:00 | Thu 16:15-18:00 | best-n: Pass 10 of the 12 online quizzes (70 % each) for +0.25 | 10 / 12 (max 0.25) |
| PROG Introduction to Programming | [prog.md](<PROG/prog.md>) | Tue 13:15-15:00, Fri 13:15-15:00 | Wed 10:15-12:00 | none | - |
<!-- uni-os:end courses -->

Term: week 0 starts Mon 2026-09-14; week n starts week 0 + 7n days. Last lecture day 2026-12-18. Exam session 2027-01-25 to 2027-02-19. Current standing: [progress/current-status.md](<progress/current-status.md>).

## Weekly rhythm and session offsets
An exercise session almost never covers the material of that same day's or week's lectures: it lags, and the lag differs per course. Getting this wrong is the main failure mode when answering "what does today's session cover?".

<!-- uni-os:begin rhythm -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Sheets out | Due | Session rule (what the exercise session of week n covers) | Week numbering |
|---|---|---|---|---|
| AD | Thu 12:00 | Thu 23:59, one week later | The exercise session of week n discusses sheet n-1 and introduces sheet n. | Sheet k is released in term week k. |
| DM | Mon 12:00 | Mon 12:00, one week later | (not set yet) | same as term weeks? |
| LA | Fri 18:00 | Mon 09:00 | (not set yet) | same as term weeks? |
| PROG | Tue 18:00 | Tue 18:00, one week later | (not set yet) | same as term weeks? |
<!-- uni-os:end rhythm -->

## Help allowed per course
Default assistance level and the official rule. Per-stream overrides are on each course card. `solo` means the agent gives no help at all on that work.

<!-- uni-os:begin help -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Default | Official rule |
|---|---|---|
| AD | `hints-only` | Sheets are individual work; AI may explain concepts, never produce solutions. |
| DM | `hints-only` | (add from the course page) |
| LA | `hints-only` | (add from the course page) |
| PROG | `coach` | (add from the course page) |
<!-- uni-os:end help -->

## Same layout in every course folder
<!-- uni-os:begin layout -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current. -->
| Item | What goes there |
|---|---|
| `<slug>.md` (e.g. `ad.md`) | Course card: facts, weekly rhythm, assessments, bonus, help policy, real sources with page offsets, lecture log, known gaps, official files, file index |
| `backlog.md` | Parked tasks with why and estimated minutes |
| `<slug>-error-log*.md` | Error log(s): date, where, what went wrong, the correct idea, source; recurring patterns |
| `notes/` | Study pages, lecture notes, summaries, cheat sheets. **New study material lands here.** |
| `quiz-prep/` | Graded-quiz checklists, mock quizzes, review extracts, breakdowns |
| `reference/` | Predicted topic plan (`<slug>-topic-plan.md`), course guide (`<slug>-course-guide.md`), script indexes, text copies of scripts too big to read |
| Official subfolders | The university's files under their official names (sheets, solutions, script, slides, handouts). Add-only |
| `<folder> handwritten/` (default name; `handwritten_folder` in the config overrides it) | PDFs exported by the tablet note app. Written only by the app |
<!-- uni-os:end layout -->

Official subfolders per course:

<!-- uni-os:begin official-subfolders -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Folder | Official subfolders |
|---|---|---|
| AD | `AD/` | `AD assignments/`, `AD slides & script/`, `AD handwritten/` (tablet app) |
| DM | `DM/` | `DM assignments/`, `DM script/`, `DM handwritten/` (tablet app) |
| LA | `LA/` | `LA assignments/`, `LA plan & notes/`, `LA handwritten/` (tablet app) |
| PROG | `PROG/` | `PROG assignments/`, `PROG slides/`, `PROG handwritten/` (tablet app) |
<!-- uni-os:end official-subfolders -->

## Filing rules (all course folders)
1. **Sources are add-only.** Official files keep their official names. An agent may add a newly downloaded official file to the matching subfolder and link it from the course card; it never renames, moves or deletes an existing one. A newer version of an official file replaces the old one only on the student's direct OK, and the old copy moves, under its own name, to `z_archive/<course folder>-outdated-YYYY-MM-DD/` at the vault root, never deleted.
2. **Notes and sources never mix.** Agent-made files go into `notes/`, `reference/`, `quiz-prep/` or the course folder's top level (card, backlog, error logs). Nothing agent-made goes into an official subfolder or the handwritten folder.
3. **Unique names.** Notes are lowercase-kebab-case, start with the course slug and end with the kind of note (`<slug>-<what>-<kind>.md`, e.g. `<slug>-heaps-study-page.md`, `<slug>-weeks3-4-recap.md`; the list is in each course's `notes/README.md`). Official files can share names across folders (`lecture01.pdf`, `solution01.pdf`), so always link by relative path, never by bare name.
4. **Text copies are marked.** When a PDF can't be read and an agent types a copy, it is `<official name>-transcript.md` and says "If this copy and the PDF ever differ, the PDF wins."
5. **Every new file is indexed.** One row in the course card's "In this folder" table, with what it is, the date and who made it.
6. **Graded solo work stays out.** Nothing that solves, hints at or summarises work marked `solo` is stored anywhere in the vault, including the student's handwritten work on it.

## Colour convention
Each course has one colour, used in the calendar, the Obsidian graph and folders, dashboards and course guides. Darker shade = lectures, lighter shade = exercise sessions. Other areas (`me/`, `progress/`, `semester/`, deadlines, agent notes) get clearly different colours: never give two areas similar colours. A calendar may instead use one colour per event type (all lectures one colour, all exercise sessions another); say which convention you use.

<!-- uni-os:begin colours -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Main colour | Lighter (exercise) |
|---|---|---|
| AD | `#1e66f5` | `#7aa2f7` |
| DM | `#40a02b` | `#7ccf6b` |
| LA | `#8839ef` | `#b58af5` |
| PROG | `#d20f39` | `#f2788f` |
<!-- uni-os:end colours -->

## Page offsets (printed vs PDF)
Cite printed page numbers; use the offset to open the right PDF page. Offsets differ per script and even per file, and can change with a new script version.

<!-- uni-os:begin page-offsets -->
<!-- Generated from the config ([[courses]] in _agent/uni-os.toml); `uni-os render` keeps it current. Change the config, not this table. -->
| Course | Source | Rule |
|---|---|---|
| AD | Script 2026 (PDF) | PDF page = printed page + 2 |

<!-- uni-os:end page-offsets -->

Whenever you meet a new script, deck or handout with an offset, add it to the course card's offset table and to the course's `page_offsets` in the config; the next `uni-os render` adds the row here. Typical rules: "PDF page = printed page + 8", "printed = PDF - 1", "part II: printed = PDF, may renumber". Previous years' scripts have their own offsets.

## Per-week content map (predicted)
One line per term week and course: lecture numbers · topic · sheet number · **graded fixtures in bold**. Derived from the per-course topic plans (`<folder>/reference/<slug>-topic-plan.md`); verify on the official pages when it matters.

| W | Starts (Mon) | AD | DM | LA | PROG |
|---|---|---|---|---|---|
| 0 | 2026-09-14 | | | | |

(Setup or the first planning session adds one row per term week up to the last lecture week. A course added later gets its column here by hand.)
