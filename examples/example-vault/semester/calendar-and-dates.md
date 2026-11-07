---
type: semester
audience: both
updated: 2026-11-07
tags: [uni/semester]
---
# Term calendar, weekly grid and key dates (Autumn 2026)

Last reviewed: 2026-11-07 (set up). The live calendar "Courses" is the source of truth for class times; this page is the overview. Every fact carries "checked <date>" and its source. Unverified dates are marked "(inferred)", "(unconfirmed)" or "[CHECK]".

## Term weeks (project numbering)
Week 0 starts Mon 2026-09-14; week n starts week 0 + 7n days. Every file in this vault uses this numbering (week pages, plans, prep notes). Daylight-saving switch in Europe/Zurich: _fill in the date_.

The table runs from week 0 to the week of the last lecture day (2026-12-18). It is generated from `term.week0_monday` and `term.last_lecture_day` in `_agent/uni-os.toml` and sits between `uni-os:begin` / `uni-os:end` marker lines: `uni-os render` keeps it current, so change those keys, not the rows. Holidays and other numberings go in the lines around it.

<!-- uni-os:begin term-weeks -->
| Week | Starts (Monday) |
|---|---|
| 0 | Mon 14 Sep 2026 |
| 1 | Mon 21 Sep 2026 |
| 2 | Mon 28 Sep 2026 |
| 3 | Mon 5 Oct 2026 |
| 4 | Mon 12 Oct 2026 |
| 5 | Mon 19 Oct 2026 |
| 6 | Mon 26 Oct 2026 |
| 7 | Mon 2 Nov 2026 |
| 8 | Mon 9 Nov 2026 |
| 9 | Mon 16 Nov 2026 |
| 10 | Mon 23 Nov 2026 |
| 11 | Mon 30 Nov 2026 |
| 12 | Mon 7 Dec 2026 |
| 13 | Mon 14 Dec 2026 |
<!-- uni-os:end term-weeks -->

Other numberings you will meet: the LMS may count "week 1" from the first lecture or name quizzes one week ahead, lecture schedules often start at 1, course websites may use the local language. Write each one down as a translation, e.g. "LMS 'Quiz week k' = term week k-1". In the original, a prep note was labelled with the wrong week until the translation was written here.
- AD: Sheet k is released in term week k.


The three tables below (weekly grid, release rhythm, graded and bonus items) sit between `uni-os:begin` / `uni-os:end` marker lines: they are generated from `[[courses]]` in `_agent/uni-os.toml`, and `uni-os render` refreshes them even after this page was edited (everything outside the markers is kept). To change a slot, a rhythm or a graded item, change the config and render; text typed between the markers is overwritten. Notes and corrections go in the bullet lists under the tables.

## Fixed weekly grid
<!-- uni-os:begin grid -->
| Course | Lectures (L:) | Exercise classes (E:) |
|---|---|---|
| AD (Algorithms and Data Structures) | Tue 10:15-12:00, Thu 10:15-12:00 | Wed 14:15-16:00 |
| DM (Discrete Mathematics) | Mon 08:15-10:00, Wed 08:15-10:00 | Tue 16:15-18:00 |
| LA (Linear Algebra) | Mon 13:15-15:00, Fri 10:15-12:00 | Thu 16:15-18:00 |
| PROG (Introduction to Programming) | Tue 13:15-15:00, Fri 13:15-15:00 | Wed 10:15-12:00 |
<!-- uni-os:end grid -->

- Add one bullet per extra fact, starting with the course short name: recordings (where, how soon), unofficial extra sessions, other groups' slots you may join, room changes. Each with "checked <date>".

## Release and deadline rhythm
<!-- uni-os:begin rhythm -->
| Course | Released | Official deadline |
|---|---|---|
| AD | Thu 12:00 | Thu 23:59, one week later |
| DM | Mon 12:00 | Mon 12:00, one week later |
| LA | Fri 18:00 | Mon 09:00 |
| PROG | Tue 18:00 | Tue 18:00, one week later |

Personal deadline rule: Sheets released in a week are done by that Sunday. The week pages show each item's personal target next to its official deadline.
<!-- uni-os:end rhythm -->

- Exceptions to the rhythm (a moved deadline, a skipped week): one bullet each, with the course, the week and "checked <date>".

### Graded and bonus items
<!-- uni-os:begin graded -->
| Course | Item | Kind | Schedule | Counts for |
|---|---|---|---|---|
| AD | Weekly exercise sheets | sheet | out Thu, due the next Thu 23:59 | bonus |
| AD | In-class quizzes | quiz | weeks 4, 8 and 12, in the exercise session | bonus |
| DM | Graded sheets | sheet | every second week | bonus |
| DM | Practice sheets | sheet | weekly | none |
| LA | Online quizzes | quiz | weekly on the LMS, open Fri 18:00 to Mon 09:00 | bonus |
| LA | Exercise sheets | sheet | weekly, discussed in the exercise session | none |
| PROG | Programming exercises | sheet | weekly, autograded | admission |
| PROG | Team project | project | weeks 10 to 13, in pairs | grade |
<!-- uni-os:end graded -->

## Key dates from now on
| Date | Course | What |
|---|---|---|
|  |  |  |

Rules for this table: dates as `Ddd D Mon HH:MM` (e.g. `Tue 3 Nov 23:59`), sorted; **bold** for graded or bonus fixtures; a cancelled item stays, struck through, with "**DROPPED (<who>, <date>)**"; the check-in prunes rows older than one week. Dates within the next 10 days also go into the "Next 10 days" table of the progress dashboard.

## Term end, lecture-free period and exam session
- Last lectures: 2026-12-18.
- Lecture-free from: 2026-12-19.
- Exam session: 2027-01-25 to 2027-02-19.
- Holiday: Reading day, 2026-11-20 to 2026-11-20.
- Last in-person must (the last fixture you have to attend): _fill in_.
- Items due online after teaching ends (sheets, peer grading): _fill in_; they constrain travel.
- Sources: the university's academic calendar (link), checked _date_.

## Exam logistics
Logistics only: when, how long, what you may bring, how to register. This is the input for [the exam-phase plan](plans/exam-phase-plan.md).

| Course | Date | Format and length | Allowed aids |
|---|---|---|---|
| AD | TBD | written, 120 min, English, one handwritten A4 sheet allowed |  |
| DM | TBD |  |  |
| LA | TBD |  |  |
| PROG | TBD |  |  |

This table is filled by hand (dates arrive during the term): a course added later gets its row here when it is onboarded (`_agent/skills/course-facts/references/course-onboarding.md`, section 5).

- Registration window and deregistration deadline: _fill in, with source and date checked_.
- Bonus validity (does the bonus count for a retake?): _fill in per course_.
