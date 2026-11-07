---
type: resource
audience: both
updated: 2026-11-07
tags: [uni/resources, verification]
---
# Course verification: claims, checks, verdicts

A read-only fact-check of every course fact the system relies on, against the real course pages. It turns "we think the sheets come out on Friday" into "WRONG: the course page says 'every Thursday', checked Sat 24 Oct", and pushes the corrections into the course cards, the overview, the plans and the config. In the original system one full pass in week 5 found a wrong release day, two "extra sessions" that were other groups' regular slots, a quiz scope broader than believed, an exam-language disagreement between catalogue and course page, and a week-numbering offset, all of which had been steering plans and answers.

## When to run it
- **Week 0 or 1**, as soon as the course pages are up: the first full pass, right after setup.
- **After any announcement that changes a date, a rule or a scope.** Check just the affected claims.
- **Around the middle of the term** (week 5 or 6): a full pass; rhythms and rules drift.
- **Before relying on a fact for points** (a quiz scope the evening before, a deadline that looks odd).
- **When two sources disagree**, or the student says "are you sure?".

Each run gets its own dated folder: `resources/course-verification-YYYY-MM-DD/` with `course-verification-claims.md` (written first) and `course-verification-results.md` (written during the pass). Add one line per run to the run log at the bottom of this page.

## The method
1. **Collect the claims before browsing.** Gather every course fact the system believes from the course cards, the course-facts skill, the courses overview, the topic plans and the status page. Write each as a precise, testable statement with an ID per course (`AD1`, `AD2`, ..., `G1` for general claims). Include open questions as claims ("Total number of quizzes and the last date?").
2. **Open a session that can see the pages.** Logged-in pages need the student's signed-in browser (in Claude Code: a laptop session with the desktop app's built-in browser, or Claude in Chrome for sites that need HTTP credentials; other agents: their browser tool, or the student pastes the pages). The student signs in first; the agent never types a password and asks for all sign-ins in one request.
3. **Walk each course strictly read-only:** the course page, **every** announcement thread since the start of term, the graded-items overview, special pages (bonus system, exam information), the course website, the course catalogue entry. "Do not change anything: solely click through the data and read." No quiz attempts, no submissions, no downloads of graded content.
4. **Give every claim a verdict** with the official wording in double quotes and a source abbreviation: `OK` · `PARTLY` (say which part) · `WRONG` (give the correction) · `NOT FOUND` (nothing official says it; it stays an estimate or an inference, labelled).
5. **Write down new facts** you met on the way, per course, and a "Still open after the full pass" list with who can answer each item.
6. **Propagate.** Correct each course card in place with the date and source ("Corrected <date> (verification run): ..."), then the courses overview, the topic plans, the week page if this week is affected, and the config entries (`_agent/uni-os.toml`) so the course-facts skill re-renders right. Tell the student in a few lines what changed and what it means this week.

## Claims file template
```markdown
# Course verification: claims to check (<Ddd D Mon YYYY>, week <n>)

Built from the course cards, the course-facts skill, the courses overview and the topic plans.
Each claim gets a verdict from the real course pages: OK / PARTLY / WRONG / NOT FOUND, with source.
Results go into course-verification-results.md in this folder.

## <COURSE> (<LMS course page>, <other platforms>)
- <C>1 Lecturers; lecture days, times, rooms; extra or swapped lectures.
- <C>2 Own exercise group, slot, room.
- <C>3 Release and due rhythm; hand-in channel; group rules.
- <C>4 Each graded stream: window, timer, number of questions, points, attempts; scope. Total number and last date?
- <C>5 Bonus formula and what full bonus needs; official semester maximum?
- <C>6 Integrity and AI rules.
- <C>7 Exam format (length, mode, language, aids): logistics only.

## General
- G1 Course catalogue entries for this term (times, rooms, exam mode).
- G2 Last lecture days.
- G3 Every announcement since the start of term that changes a date, a rule or a scope.
```

## Results file template
```markdown
# Course verification: results (<Ddd D Mon YYYY>, week <n>)

Read-only pass through the real course pages (<which browser/session>). Claim IDs refer to the claims file in this folder. Nothing was submitted or changed on any site.

## <COURSE>
Sources: CP = course page <url> · ANN = announcements (all <N> threads) · GB = graded items overview · SITE = course website · CAT = course catalogue

| ID | Verdict | Official wording / correction | Source |
|---|---|---|---|
| <C>1 | OK | "<verbatim quote>" | CP |

New facts (<COURSE>):
- ...

## Catalogue cross-check
- ...

## Still open after the full pass
- <item> (who can answer: TA / course page later / the student)
```

## Starter claims from your config
Copy these into the first claims file (they use the claim IDs of the template above; give several graded streams of one course letters when you copy them: 4a, 4b, ...), then add what the cards say beyond them. Every value here comes from `_agent/uni-os.toml`; "(not configured)" items are open questions to answer during the pass.

### AD: Algorithms and Data Structures
- AD1 Lectures: Tue 10:15-12:00, Thu 10:15-12:00 · lecturers, rooms, extra or swapped lectures?
- AD2 Exercise session: Wed 14:15-16:00 · group 3 · room?
- AD3 Sheets out Thu 12:00 · due Thu 23:59, one week later · hand-in: LMS upload, one PDF per person
- AD3s Session rule: The exercise session of week n discusses sheet n-1 and introduces sheet n. · week numbering: Sheet k is released in term week k.
- AD4 Graded stream "Weekly exercise sheets" (sheet): out Thu, due the next Thu 23:59 · counts for: bonus · total number and last date?
- AD4 Graded stream "In-class quizzes" (quiz): weeks 4, 8 and 12, in the exercise session · counts for: bonus · 10 points · total number and last date?
- AD5 Bonus: scheme `threshold` · rule: Sum of sheet points over the term; quizzes count double. · full bonus at: 80 % of all sheet points · official semester maximum?
- AD6 Integrity and AI rules: Sheets are individual work; AI may explain concepts, never produce solutions.
- AD7 Exam format (logistics only): written, 120 min, English, one handwritten A4 sheet allowed

### DM: Discrete Mathematics
- DM1 Lectures: Mon 08:15-10:00, Wed 08:15-10:00 · lecturers, rooms, extra or swapped lectures?
- DM2 Exercise session: Tue 16:15-18:00 · room?
- DM3 Sheets out Mon 12:00 · due Mon 12:00, one week later · hand-in: (not configured)
- DM3s Session rule: (not configured: what does the exercise session of week n cover?)
- DM4 Graded stream "Graded sheets" (sheet): every second week · counts for: bonus · 2 points · total number and last date?
- DM4 Graded stream "Practice sheets" (sheet): weekly · counts for: none · total number and last date?
- DM5 Bonus: scheme `points` · rule: Bonus = 0.25 * min(points, 8) / 8. · full bonus at: 8 points · official semester maximum?
- DM6 Integrity and AI rules: (not configured)
- DM7 Exam format (logistics only): (not configured)

### LA: Linear Algebra
- LA1 Lectures: Mon 13:15-15:00, Fri 10:15-12:00 · lecturers, rooms, extra or swapped lectures?
- LA2 Exercise session: Thu 16:15-18:00 · room?
- LA3 Sheets out Fri 18:00 · due Mon 09:00 · hand-in: (not configured)
- LA3s Session rule: (not configured: what does the exercise session of week n cover?)
- LA4 Graded stream "Online quizzes" (quiz): weekly on the LMS, open Fri 18:00 to Mon 09:00 · counts for: bonus · 4 points · total number and last date?
- LA4 Graded stream "Exercise sheets" (sheet): weekly, discussed in the exercise session · counts for: none · total number and last date?
- LA5 Bonus: scheme `best-n` · rule: At least 10 of the 12 weekly quizzes passed with >= 70 %; fewer passes give a proportional share. · full bonus at: 10 / 12 · official semester maximum?
- LA6 Integrity and AI rules: (not configured)
- LA7 Exam format (logistics only): (not configured)

### PROG: Introduction to Programming
- PROG1 Lectures: Tue 13:15-15:00, Fri 13:15-15:00 · lecturers, rooms, extra or swapped lectures?
- PROG2 Exercise session: Wed 10:15-12:00 · room?
- PROG3 Sheets out Tue 18:00 · due Tue 18:00, one week later · hand-in: (not configured)
- PROG3s Session rule: (not configured: what does the exercise session of week n cover?)
- PROG4 Graded stream "Programming exercises" (sheet): weekly, autograded · counts for: admission · total number and last date?
- PROG4 Graded stream "Team project" (project): weeks 10 to 13, in pairs · counts for: grade · total number and last date?
- PROG5 Bonus: none configured: confirm that the course has no bonus
- PROG6 Integrity and AI rules: (not configured)
- PROG7 Exam format (logistics only): (not configured)

## Lessons from past runs
- Facts inferred from file timestamps can be wrong: re-uploads on Friday made a Thursday release look like Friday. Announcements win.
- "Extra sessions" were other groups' regular slots. Check the group list.
- A quiz's time limit was not written anywhere official; only the student's experience confirmed it. Record such facts as "confirmed by the student on <date>".
- Week numbers on the LMS ran one ahead of the term weeks.
- The course catalogue and the course page disagreed about the exam language: record both and which is binding.
- A bonus formula depended on a semester maximum that was never published: keep the estimate, labelled.
- The mobile LMS app did not show groups; a browser did.
- Only one language version of a sheet was binding; "the last push before the deadline is binding" (a commit before but a push after counts as late).

## Run log
| Date | Week | Scope | Folder | Corrections propagated to |
|---|---|---|---|---|
