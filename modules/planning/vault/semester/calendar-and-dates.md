---
type: semester
audience: both
updated: {{generated.date}}
tags: [uni/semester]
---
# Term calendar, weekly grid and key dates ({{term.label}})

Last reviewed: {{generated.date}} (set up). {{#if calendar.provider}}The live calendar "{{calendar.courses}}" is the source of truth for class times; this page is the overview. {{/if}}Every fact carries "checked <date>" and its source. Unverified dates are marked "(inferred)", "(unconfirmed)" or "[CHECK]".

## Term weeks (project numbering)
Week 0 starts Mon {{term.week0_monday}}; week n starts week 0 + 7n days. Every file in this vault uses this numbering (week pages, plans, prep notes). Daylight-saving switch in {{term.timezone}}: _fill in the date_.

The table runs from week 0 to the week of the last lecture day ({{#if term.last_lecture_day}}{{term.last_lecture_day}}{{else}}not set yet, so it shows a default term of weeks 0 to 13 until `term.last_lecture_day` is set{{/if}}). It is generated from `term.week0_monday` and `term.last_lecture_day` in `_agent/uni-os.toml` and sits between `uni-os:begin` / `uni-os:end` marker lines: `uni-os render` keeps it current, so change those keys, not the rows. Holidays and other numberings go in the lines around it.

<!-- uni-os:begin term-weeks -->
| Week | Starts (Monday) |
|---|---|
{{#each term.weeks}}| {{item.number}} | {{item.start}} |
{{/each}}
<!-- uni-os:end term-weeks -->

Other numberings you will meet: the LMS may count "week 1" from the first lecture or name quizzes one week ahead, lecture schedules often start at 1, course websites may use the local language. Write each one down as a translation, e.g. "LMS 'Quiz week k' = term week k-1". In the original, a prep note was labelled with the wrong week until the translation was written here.
{{#each courses}}{{#if course.week_numbering}}- {{course.short}}: {{course.week_numbering}}
{{/if}}{{/each}}

The three tables below (weekly grid, release rhythm, graded and bonus items) sit between `uni-os:begin` / `uni-os:end` marker lines: they are generated from `[[courses]]` in `_agent/uni-os.toml`, and `uni-os render` refreshes them even after this page was edited (everything outside the markers is kept). To change a slot, a rhythm or a graded item, change the config and render; text typed between the markers is overwritten. Notes and corrections go in the bullet lists under the tables.

## Fixed weekly grid
<!-- uni-os:begin grid -->
| Course | Lectures ({{calendar.lecture_prefix}}) | Exercise classes ({{calendar.exercise_prefix}}) |
|---|---|---|
{{#each courses}}| {{course.short}} ({{course.name}}) | {{course.lecture_slots}} | {{course.exercise_slots}} |
{{/each}}
<!-- uni-os:end grid -->

- Add one bullet per extra fact, starting with the course short name: recordings (where, how soon), unofficial extra sessions, other groups' slots you may join, room changes. Each with "checked <date>".

## Release and deadline rhythm
<!-- uni-os:begin rhythm -->
| Course | Released | Official deadline |
|---|---|---|
{{#each courses}}| {{course.short}} | {{course.sheet_release}} | {{course.sheet_due}} |
{{/each}}

{{#if study.personal_deadline_rule}}Personal deadline rule: {{study.personal_deadline_rule}} The week pages show each item's personal target next to its official deadline.{{else}}No personal deadline rule is set (`study.personal_deadline_rule` in the config); the week pages leave the personal target empty.{{/if}}
<!-- uni-os:end rhythm -->

- Exceptions to the rhythm (a moved deadline, a skipped week): one bullet each, with the course, the week and "checked <date>".

### Graded and bonus items
<!-- uni-os:begin graded -->
| Course | Item | Kind | Schedule | Counts for |
|---|---|---|---|---|
{{#each courses}}{{#each course.assessments}}| {{course.short}} | {{item.name}} | {{item.kind}} | {{item.schedule}} | {{item.counts_for}} |
{{/each}}
{{/each}}
<!-- uni-os:end graded -->

## Key dates from now on
| Date | Course | What |
|---|---|---|
|  |  |  |

Rules for this table: dates as `Ddd D Mon HH:MM` (e.g. `Tue 3 Nov 23:59`), sorted; **bold** for graded or bonus fixtures; a cancelled item stays, struck through, with "**DROPPED (<who>, <date>)**"; the check-in prunes rows older than one week. Dates within the next 10 days also go into the "Next 10 days" table of the progress dashboard.

## Term end, lecture-free period and exam session
- Last lectures: {{#if term.last_lecture_day}}{{term.last_lecture_day}}{{else}}_not set_{{/if}}.
- Lecture-free from: {{#if term.lecture_free_from}}{{term.lecture_free_from}}{{else}}_not set_{{/if}}.
- Exam session: {{#if term.exam_session_start}}{{term.exam_session_start}} to {{term.exam_session_end}}{{else}}_not set_{{/if}}.
{{#each term.holidays}}- Holiday: {{item.name}}, {{item.from}} to {{item.to}}.
{{/each}}- Last in-person must (the last fixture you have to attend): _fill in_.
- Items due online after teaching ends (sheets, peer grading): _fill in_; they constrain travel.
- Sources: the university's academic calendar (link), checked _date_.

## Exam logistics
Logistics only: when, how long, what you may bring, how to register. This is the input for [the exam-phase plan](plans/exam-phase-plan.md).

| Course | Date | Format and length | Allowed aids |
|---|---|---|---|
{{#each courses}}| {{course.short}} | TBD | {{course.exam_format}} |  |
{{/each}}

This table is filled by hand (dates arrive during the term): a course added later gets its row here when it is onboarded (`_agent/skills/course-facts/references/course-onboarding.md`, section 5).

- Registration window and deregistration deadline: _fill in, with source and date checked_.
- Bonus validity (does the bonus count for a retake?): _fill in per course_.
