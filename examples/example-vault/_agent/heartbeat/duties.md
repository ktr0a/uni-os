---
type: agent
audience: both
updated: 2026-11-07
tags: [uni/agent]
---
# Duty checklist (the heartbeat's safety net)

Role sessions only act when someone speaks to them; only scheduled jobs act on their own. Every duty promised in a role brief should therefore map to a trigger: a job, an explicit request from Alex Example, or another role or job that asks for it. The original system found 16 duties that had none (quiz-prep pages, summary sheets, results nobody asked for, hand-offs after a review, exam-phase planning, ...). This list is where such duties live, and it is itself the last trigger: no row may be left with nothing.

Each heartbeat run checks the rows due within the next 48 h: does the output exist, or does a job that is switched on (`_agent/jobs/`, and on an always-on host `uni-vm jobs`) or a calendar block now cover it? Only rows with neither become flags (`duty:<row id>`), and the flag goes to the role that owns the duty or to Alex Example. A job named in "Covered by" only counts while it is switched on: an optional job that ships switched off covers nothing until Alex Example says yes. When a duty gets its own job or standing trigger, write it into "Covered by" and leave the row in the table (the heartbeat then only verifies the output).

Edit freely: add a row whenever a brief promises something "every week", "before each quiz", "before each lecture" or "after each review".

| Row id | Duty | Due (date or rule) | Output that proves it | Covered by (first that applies), else |
|---|---|---|---|---|
| week-plan | Next week's plan written and applied to the calendar | the day the week page is created | `semester/plans/week-NN-plan.md` for next week | job `week-page` (module check-in) when switched on: its inbox note asks Plan & progress; else this row's flag to Plan & progress |
| exam-phase-plan | Exam-phase schedule drafted (study blocks for the exam session) | 4 weeks before the exam session starts (`term.exam_session_start`) | `semester/plans/exam-phase-plan.md` with no `[EXAM ...: TBD]` placeholder left and its countdown blocks booked in the calendar (the file itself exists from setup on, so it proves nothing) | no job: this row's flag to Plan & progress, which drafts it with Alex Example |
| deadline-audit | Deadline audit before the exam phase: every documented date compared with the calendar and the study blocks before it | on the last lecture day (2026-12-18) | `semester/plans/deadline-audit-YYYY-MM-DD.md` | job `deadline-audit` (module planning) when switched on; else Plan & progress when Alex Example asks; else this row's flag to Plan & progress |
| quiz-prep | Prep page for each graded weekly quiz | 4 days before each quiz, at the latest the evening before | `<course>/quiz-prep/<slug>-quiz-<quiz id>-prep.html` (or `.md`) | job `quiz-prep` (module quiz-coaching) when switched on, on the dates in `schedule.quiz_prep_dates`; else role `quiz-coach` when Alex Example asks; else this row's flag |
| lecture-skim | Skim page before each lecture of the courses in `study.rundowns.skim_courses` | 1 h before each such lecture | `<course>/notes/<slug>-lecture-<ddd><d><mon>-*-skim.html` (or `.md`) | job `lecture-skim` (module lecture-rundowns) when switched on; else role `lecture-rundown` when Alex Example asks; else this row's flag |
| results | Results of graded work recorded | within a day of being returned | a tracker-log line and the week page status | the heartbeat's own daily question (at most one a day) |
| waiting-on-you | Alex Example told what waits on them (decisions, physical steps, results to report) | daily, at 19:00 | `waiting-on-you.md` (vault root) generated today | job `waiting-on-you` (module roles) when switched on: one page and one push; else the coordinator when Alex Example asks "what's waiting on me?" |
| summary-sheets | Summary sheet per course kept current | before the last lecture day (`term.last_lecture_day`) | `<course>/notes/` summary page | no job: this row's flag to the course's lecture-rundown session (role `lecture-rundown`) or to Alex Example |
