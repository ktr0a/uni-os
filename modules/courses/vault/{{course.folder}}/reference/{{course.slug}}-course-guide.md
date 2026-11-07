---
type: reference
course: {{course.id}}
audience: me
updated: {{generated.date}}
tags: [uni/{{course.id}}, course-guide]
---
# {{course.name}}: course guide, {{term.label}}

A one-page onboarding guide to the course, written once at the start of term from the course catalogue, the {{university.lms}} course page, the course website and the timetable, then kept short. It answers "how does this course work?" in five minutes. The course card ([{{course.slug}}.md](<../{{course.slug}}.md>)) holds the live facts; when the two disagree, the card wins and this guide gets a correction.

> [!tip] Building it
> Read the sources in the "Sources" section at the bottom, fill each section in plain language, and keep every number that decides points exactly as the course states it (quote it). Mark inferences. If you use HTML study pages, an agent can also turn this guide into an interactive page (a tappable "your week" grid, a greyed-out timeline of past items, a bonus calculator with sliders); the Markdown version stays the readable copy.

## At a glance
| | |
|---|---|
| Lectures | {{#if course.lecture_slots}}{{course.lecture_slots}}{{else}}(day, time, room){{/if}} |
| Your exercise session | {{#if course.exercise_slots}}{{course.exercise_slots}}{{else}}(day, time, room){{/if}}{{#if course.exercise_group}} · {{course.exercise_group}}{{/if}} |
| Graded work | {{#each course.assessments}}{{item.name}} ({{item.counts_for}}){{#unless @last}}; {{/unless}}{{else}}(none configured){{/each}} |
| Bonus | {{#if course.bonus.scheme}}{{#if course.bonus.description}}{{course.bonus.description}}{{else}}(how it is earned){{/if}}{{#if course.bonus.target}}; full bonus at {{course.bonus.target}}{{/if}}{{else}}none{{/if}} |
| Exam format | {{#if course.exam_format}}{{course.exam_format}}{{else}}(length, mode, language, allowed aids){{/if}} |
| Where to ask | (forum, session, messaging system of the programming platform; not private email unless the course says so) |

## Your week
One row per fixed slot of a normal week (lecture, exercise session, sheet release, deadline, quiz window, optional study centre).

| Day | Time | What | Where | Notes |
|---|---|---|---|---|

Calendar oddities (lecture swaps with other courses, extra lectures, cancelled sessions):
- 

## Your exercise session
- How it runs (class, then supervised work; group work; peer grading; attendance rule):
- First session, enrolment deadline, how groups are formed:
- Other formats (online class, focus groups, special classes):

## Term timeline
Dated one-off events: first lecture, enrolment deadlines, first quiz, first graded sheet, timed or oral fixtures, last lecture, exam session (dates only). Strike items when they are past.
1. 

## The weekly cycle
1. (release day: new sheet)
2. (session: what happens)
3. (deadline: how to hand in, what counts as on time, e.g. "the last push before the deadline is binding")
4. (feedback: when and how corrections come back)

## Bonus and graded work
| Source | Points | How |
|---|---|---|
{{#each course.assessments}}| {{item.name}} ({{item.counts_for}}) | {{#if item.points_max}}{{item.points_max}}{{else}}{{#if item.counts_for}}not published{{else}}-{{/if}}{{/if}} | {{item.schedule}} |
{{else}}| (no graded work configured) | | |
{{/each}}

{{#if course.bonus.scheme}}
- Rule: {{#if course.bonus.rule}}{{course.bonus.rule}}{{else}}(the official bonus formula, verbatim, and what "full bonus" needs){{/if}}
- Valid for: (which exam session(s) the bonus counts for, when it expires, whether it is added before or after rounding)
- Calculator: (optional) a small table or, in an HTML version, sliders: grade before the bonus, share of bonus points reached, resulting final grade after the course's rounding rule.
{{else}}
- No bonus scheme is configured for this course. If graded work counts for admission or the grade, write here what is needed to pass it (e.g. "at least 60 % of the programming exercises").
{{/if}}

## Topics and material
- Topics (from the course catalogue):
- Primary material (script, slides, handouts; where they appear):
- Books and further reading:

## Integrity rules
{{#if course.integrity}}Official rule, in short: {{course.integrity}}{{/if}}

| Allowed | Not allowed |
|---|---|
| | |

What happens on copying (e.g. "both groups lose the points"), and what the course says about AI tools, verbatim where possible.

## Where to look
| What | Where |
|---|---|
| Course page, sheets, announcements | {{#if course.lms_url}}{{course.lms_url}}{{else}}{{university.lms}}{{/if}} |
| Course website | {{#if course.website}}{{course.website}}{{else}}(none or add){{/if}} |
| Other platforms | {{#if course.platforms}}{{course.platforms}}{{else}}(none or add){{/if}} |
| Recordings | {{#if course.recordings}}{{course.recordings}}{{else}}(add){{/if}} |
| Course catalogue | {{#if university.catalogue}}{{university.catalogue}}{{else}}(add){{/if}} |

## Sources
Read on (date): course catalogue entry, {{university.lms}} course page and announcements, course website, timetable. Details can change until the term starts; the official exam timetable is binding for exam dates.
