---
type: agent
audience: both
updated: {{generated.date}}
tags: [uni/agent]
---
# Duty checklist (the heartbeat's safety net)

Role sessions only act when someone speaks to them; only scheduled jobs act on their own. Every duty promised in a role brief should therefore map to a trigger: a job, an explicit request from {{student.name}}, or another role or job that asks for it. The original system found 16 duties that had none (quiz-prep pages, summary sheets, results nobody asked for, hand-offs after a review, exam-phase planning, ...). This list is where such duties live, and it is itself the last trigger: no row may be left with nothing.

Each heartbeat run checks the rows due within the next 48 h: does the output exist, or does a job that is switched on (`_agent/jobs/`, and on an always-on host `uni-vm jobs`) or a calendar block now cover it? Only rows with neither become flags (`duty:<row id>`), and the flag goes to the role that owns the duty or to {{student.name}}. A job named in "Covered by" only counts while it is switched on: an optional job that ships switched off covers nothing until {{student.name}} says yes. When a duty gets its own job or standing trigger, write it into "Covered by" and leave the row in the table (the heartbeat then only verifies the output).

Edit freely: add a row whenever a brief promises something "every week", "before each quiz", "before each lecture" or "after each review".

| Row id | Duty | Due (date or rule) | Output that proves it | Covered by (first that applies), else |
|---|---|---|---|---|
{{#if modules.planning}}| week-plan | Next week's plan written and applied to the calendar | the day the week page is created | `semester/plans/week-NN-plan.md` for next week | job `week-page` (module check-in) when switched on: its inbox note asks Plan & progress; else this row's flag to Plan & progress |
| exam-phase-plan | Exam-phase schedule drafted (study blocks for the exam session) | 4 weeks before the exam session starts (`term.exam_session_start`) | `semester/plans/exam-phase-plan.md` with no `[EXAM ...: TBD]` placeholder left and its countdown blocks booked in the calendar (the file itself exists from setup on, so it proves nothing) | no job: this row's flag to Plan & progress, which drafts it with {{student.name}} |
| deadline-audit | Deadline audit before the exam phase: every documented date compared with the calendar and the study blocks before it | {{#if term.last_lecture_day}}on the last lecture day ({{term.last_lecture_day}}){{else}}once before the exam phase (no `term.last_lecture_day` set){{/if}} | `semester/plans/deadline-audit-YYYY-MM-DD.md` | job `deadline-audit` (module planning) when switched on; else Plan & progress when {{student.name}} asks; else this row's flag to Plan & progress |
{{/if}}{{#if modules.quiz-coaching}}| quiz-prep | Prep page for each graded weekly quiz | {{study.quiz.prep_lead_days}} days before each quiz, at the latest the evening before | `<course>/quiz-prep/<slug>-quiz-<quiz id>-prep.html` (or `.md`) | job `quiz-prep` (module quiz-coaching) when switched on, on the dates in `schedule.quiz_prep_dates`; else role `quiz-coach` when {{student.name}} asks; else this row's flag |
{{/if}}{{#if modules.lecture-rundowns}}| lecture-skim | Skim page before each lecture of the courses in `study.rundowns.skim_courses` | {{study.rundowns.skim_lead_hours}} h before each such lecture | `<course>/notes/<slug>-lecture-<ddd><d><mon>-*-skim.html` (or `.md`) | job `lecture-skim` (module lecture-rundowns) when switched on; else role `lecture-rundown` when {{student.name}} asks; else this row's flag |
{{/if}}{{#if modules.course-files-fetch}}| sheet-pickup | New exercise sheets filed in their course folders | the evening a sheet is released | the PDF in the course's official folder | role `course-files-fetch` when {{student.name}} asks (it needs the logged-in browser, so no job); else this row's flag |
{{/if}}{{#if modules.progress}}| results | Results of graded work recorded | within a day of being returned | a tracker-log line and the week page status | the heartbeat's own daily question (at most one a day) |
{{/if}}{{#if modules.roles}}| waiting-on-you | {{student.name}} told what waits on them (decisions, physical steps, results to report) | daily, at {{schedule.waiting_on_you}} | `waiting-on-you.md` (vault root) generated today | job `waiting-on-you` (module roles) when switched on: one page and one push; else the coordinator when {{student.name}} asks "what's waiting on me?" |
{{/if}}| summary-sheets | Summary sheet per course kept current | before the last lecture day (`term.last_lecture_day`) | `<course>/notes/` summary page | no job: this row's flag to the course's lecture-rundown session{{#if modules.lecture-rundowns}} (role `lecture-rundown`){{/if}} or to {{student.name}} |
