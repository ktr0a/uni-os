# Onboarding a course (start of term, or a course added later)

How the original system got each course right in the first week: read the official sources once, write every number that decides points exactly as stated, separate facts from predictions, and put each fact in one place.

## 1. Read, in this order
1. **Course catalogue entry**: lecturers, credits, lecture and exercise slots with rooms, exam mode and length, allowed aids, bonus rules if stated there, integrity notes.
2. **LMS course page and every announcement so far**: release and due rhythm, hand-in channel, quiz rules and scope, bonus formula, integrity and AI rules, group lists, special pages (bonus system, exam info).
3. **Course website** (if separate): agenda with dates, slides, sheets, exam information, group table. Some sites need HTTP credentials that only the student's own browser has.
4. **The student's timetable**: which exercise group and slot they are actually in.
5. **First lecture slides and the first sheet**: notation conventions, numbering, what "week 1" means.

Logged-in pages are read-only and read through the student's signed-in browser. The student signs in; never type a password. Nothing is submitted, started or changed.

## 2. Ask the student (only what the sources can't answer)
- Which exercise group they are in, if the LMS doesn't show it (the mobile app may hide groups).
- How strict they want the assistance level per graded stream, if stricter than the course rule (some students want graded work fully solo even where hints would be allowed).
- Their routine for the course: when they start sheets, how long they try cold before a hint.
- Anything they already know about how the course runs from the first session.

## 3. Write it down
1. **Config entry** in `_agent/uni-os.toml` (`[[courses]]`): identity (id, name, short, folder, slug, colour), slots, release and due, hand-in, `session_rule`, `week_numbering`, `official_subfolders`, `real_source`, `page_offsets`, `exam_format` (logistics only), `integrity`, `assistance`, `assessments` (one entry per graded stream: name, kind, schedule, counts_for, optional points_max, assistance, scope), `bonus` (scheme, description, max_bonus, rule, target). Then run `python tools/uni_os.py render --vault "<vault>"` in the framework folder: it refreshes every generated table that shows these keys (below).
2. **Course card** `<folder>/<slug>.md`: the same facts in readable form, plus sources with page offsets, known gaps and the official file folders. Quote official wording for anything that decides points. Its graded-streams table and assistance level are a generated region: they come from the config, so fix a stream or an assistance level in the config (then render), not in the card.
3. **Course guide** `<folder>/reference/<slug>-course-guide.md`: the five-minute "how this course works" page.
4. **Topic plan** `<folder>/reference/<slug>-topic-plan.md`: one row and one block per term week, marked predicted.
5. **Courses overview** (`courses-overview.md`): its per-course tables (courses, rhythm, help, official subfolders, colours, page offsets) are generated regions that `render` fills from the config; by hand you only fill the course's column in the per-week content map.
6. **Calendar** (if the planning module is on): lectures and sessions in the courses calendar, with the course colour.

## 4. Separate certain from predicted
- Certain: dates, rooms, deadlines, graded-work rules, formulas, as stated officially. Write the date you checked them.
- Predicted: which topic falls in which week, scopes inferred from a pattern, totals that are not published. Label them every time.
- Unknown: write it in the card's "Known gaps" with who can answer it.

## 5. Adding a course mid-term
1. Add the `[[courses]]` entry to the config (`_agent/uni-os.toml`).
2. Run `python tools/uni_os.py render --vault "<vault>"` in the framework folder (or ask the agent to; `--dry-run` first shows what would change). It creates the new course's files (card, backlog, notes, reference), its official subfolders and, with handwritten notes on, its handwritten folder, and re-renders the generated files nobody has edited, including this skill. In files you or an agent edited, it refreshes only the generated regions (the text between the `uni-os:begin NAME` and `uni-os:end NAME` marker lines) and keeps everything else, so the new course appears in the per-course tables of `courses-overview.md`, in the course table of `_agent/CONVENTIONS.md`, in the integrity table and the course-specific rules of `_agent/rules.md`, in the weekly grid, release rhythm and graded-items tables of `semester/calendar-and-dates.md` and in the tables of `_agent/roles/README.md`, without hand edits. A file that render lists as "skipped" has a broken or missing marker line: fix the markers (`_agent/CONVENTIONS.md`, "Generated regions") and render again.
3. **Add by hand what is not generated.** Render never overwrites a page someone edited, and the pages below are edited all term, so the new course is missing from them until you add it. Check every page render lists under "kept ... files you edited" and add the course's rows in the page's own style (to see the rows, render the config into a scratch folder: `python tools/uni_os.py init --config "<vault>/_agent/uni-os.toml" --vault "<scratch folder>" --force`, and copy only the new course's lines):
   - `courses-overview.md`: the course's column in the per-week content map.
   - `Home.md`: the course's tile or row (Home is installed once, then kept by hand).
   - `progress/current-status.md`: its row in "Bonus standing", its "<short> detail" table (one row per graded stream) and its section under "Exercises: done vs. to do".
   - `semester/calendar-and-dates.md`: its row in "Exam logistics" (and a bullet under the weekly grid for any extra fact); `semester/plans/exam-phase-plan.md`: its exam row.
   - `me/profile.md` (course list, self-rating row, shorthand row), `me/learning-style.md` (its row) and `me/weak-spots.md` (its section).
   - `resources/course-verification.md` (its starter claims) and `resources/sources-and-links.md` (its links).
   - Any other page in the "kept" list that names every course.
4. If the skills are copied into your agent's skills folder (`agent.skills_dir`), copy them again: this skill now lists the new course.
5. Work through sections 1-4 of this file for the new course.

## 6. Dropping a course
Remove (or comment out) its `[[courses]]` entry and run `render`: the course leaves this skill and every generated table. Its folder and notes stay in the vault untouched; move them to an archive folder only if the student asks. Copy the skills into `agent.skills_dir` again if your agent reads copies.
