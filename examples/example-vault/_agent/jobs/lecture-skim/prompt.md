# Lecture skim (job `lecture-skim`)

Purpose: a short skim page for the next lecture of each chosen course, read in about 10 minutes just before the lecture, so the lecture is not the first time Alex Example sees the material. Courses: `study.rundowns.skim_courses` = dm (course ids in `_agent/uni-os.toml`). The page must be ready at least 1 h before the lecture starts. This job runs headless at 19:00 on Sun, Tue; nobody can answer questions during the run, so decide sensibly and say what you decided. Paths below are relative to the vault root (named in the host header; in an interactive session, the folder that holds `_agent/`). Write vault files directly; everything you write is in English (headings, table columns and dates that tools parse stay exactly as given), UTF-8 without BOM, LF line ends.

## Read first
1. `_agent/agent-start.md` and `_agent/rules.md` (real sources only with section and page cited; never skip algebra steps; maths rendered, never plain text; integrity rules).
2. `_agent/roles/lecture-rundown.md` (rules and the skim format) and `_agent/skills/study-page/SKILL.md` (names, properties, checks, twin, card row).
3. For each chosen course: its course card (`<course folder>/<slug>.md`: "Real sources" with the page offset, "Conventions", "Lecture log" and any "where it stopped" line), the course's lecture schedule or topic plan in `<course folder>/reference/` if there is one, and the newest `<course folder>/notes/<slug>-lecture-*` page.

## 0. Should this run do anything?
Whenever this run stops early because there is nothing to do, first delete this job's failure flag if there is one (see "Failure flag" below).
- **Date and time.** Get the real local time from the system (Europe/Zurich): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Term week: week 0 starts on 2026-09-14, week n starts 7n days later.
- **Teaching time?** After 2026-12-18 (the last lecture day) there are no lectures: reply one line and stop. Holidays and lecture-free days in `term.holidays` have no lectures either.

## 1. Which lectures
For each course in `study.rundowns.skim_courses`: find its **next lecture that has not started yet and starts within the next 24 hours** (a morning run covers an afternoon lecture; an evening run covers the next morning's lecture). Lecture times come from `courses[].lecture_slots` in `_agent/uni-os.toml`, corrected by the course card and the course calendar if they say a lecture moved or is cancelled. If a course has no such lecture, write nothing for it. If no course has one, reply one line ("No lecture to skim before <Ddd D Mon HH:MM>") and stop.

Then work out **which sections** that lecture will cover: start where the last lecture stopped (the card's Lecture log, which comes from the student's word or the slides actually reached; a deck is the whole chapter, not what was lectured), and take the expected end from the course's plan. The plan is a **prediction**: say so on the page, and say that the official roadmap wins when they differ. If the previous lecture's end is unconfirmed, the page opens with a warning card "Where today may start".

## 2. Stop if it exists
If a skim for that course and lecture date is already there (`<course folder>/notes/<slug>-lecture-<ddd><d><mon>-*-skim.html`, or `.md` if this vault writes Markdown only), write nothing for that course and say so in one line. The course's lecture-rundown session may have written it on request.

## 3. Source
Open the real source: the script (and the slides or official handout for that lecture, if the course publishes them before the lecture) listed in the card's "Real sources". Apply the page offset from the card and cite **printed** page numbers. For scanned or handwritten PDFs, and handouts that return empty text, read the page images. **If the source can't be opened, write nothing for that course and say so: never fill in from general knowledge or from the plan alone.**

## 4. Format
Like the newest existing skim page of that course if there is one; otherwise the skim format of the rundown brief (`_templates/lecture-skim.md` for the structure; HTML on `_templates/study-page.html` without quizzes when this vault's formats include html: html, md):
- opening paragraph: the lecture (date, time), the sections the plan predicts and which plan, "the official roadmap wins", script pages (printed and PDF);
- "Where today may start" warning card if needed; a "Big picture" card (the question this chapter answers, how it connects to the last one);
- one block per expected section with a source chip: **intuition first** (with a picture or diagram when structure is involved), then the exact definitions and results with their numbers, one small example each (say whether it is from the source or your own);
- sections the course marks optional or non-examinable, marked the way the course marks them; course-language terms in brackets if the course uses another language (the `language:` line under the card's "Facts", set by `courses[].language` in `_agent/uni-os.toml`);
- **no quiz**; short enough to read in about 10 minutes; closing section "What I checked, what I inferred";
- HTML: KaTeX, dark mode, phone width, and `\lt` instead of a bare `<` before a letter inside maths.

## 5. Integrity
Nothing from any current or graded sheet task, no link to any solution file, nothing that touches work under the `solo` assistance level (resolve it as in the exercise-help brief: assessment, then course, then `study.assistance_default`). If the course card lists a blackout window (for example a week around an oral bonus problem during which a model sheet must not be linked), respect it.

## 6. Save
Follow the study-page skill: save `<course folder>/notes/<slug>-lecture-<ddd><d><mon>-<topic>-skim.html` (or `.md` for Markdown-only vaults), run `python _agent/tools/check_study_page.py <page.html>` until it reports 0 errors, make the Markdown twin with `python _agent/tools/html2md.py <page.html>`, and add one row to the "In this folder" table of the course card (re-read the card right before editing, keep its properties, bump `updated`). If you cannot run Python, say that the twin is pending.

## Failure flag
The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"); create the folder if it is missing.
- **Write** `_agent/logs/flags/lecture-skim.md` when a skim that was due could not be written: its source could not be opened, a file could not be saved, or the checker still reports errors. Front matter `job: lecture-skim`, `at: <YYYY-MM-DD HH:MM>` (local time), `level: amber`; the first line of the body says in one sentence which course and lecture have no skim and why (e.g. `DM Mon 16 Nov 08:15: no skim, the script PDF could not be opened`). If the file exists, overwrite it with the newest text. A pending Markdown twin (no Python on this host) is not a failure.
- **Delete** that file when the run ends with every due skim in place, including runs that found nothing to do (no lecture within 24 hours, teaching over, the skim already there).
- The flag replaces any notification: the heartbeat decides whether Alex Example hears about it.

## Never
- Never invent content, page numbers or "what the lecture will say"; never present the plan's prediction as fact.
- Never edit `semester/prep/` (the daily prep picks the page up; a missing page shows as a prep gap there).
- Never rename, move or delete files (the only exception is this job's own failure flag); never touch official course folders except to read.
- Never send a notification.

## Final reply
At most 3 lines per course: `<COURSE SHORT> <Ddd D Mon HH:MM>: <file> | sections <...> | uncertain: <...>`, or the one-line reason nothing was written; then `flag written|cleared|none`.
