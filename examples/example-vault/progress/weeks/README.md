---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/progress]
---
# Week pages

One page per term week: what is due, what came back, notes, and the end-of-week check-in. File name `week-NN.md`, where NN is the two-digit term week (week 0 starts Mon 2026-09-14). The page with `status` set to `current` is the live one; dashboards (the cockpit) and the Home page show its "Due this week" table.

## How a week runs

1. **Before the week:** the `week-page` job (Sun 10:00) creates the page from [the template](../../_templates/week-page.md), fills "Due this week" with the week's real items (sheets, quizzes, hand-ins, graded sittings) and their deadlines, carries over what is still open, marks the new page current and the previous one done, and asks Plan & progress for the week plan if it doesn't exist yet.
2. **During the week:** whenever you report something ("sheet 7 submitted", "quiz 2.5 out of 4"), the session that hears it updates the Status cell, adds a line under "Results this week", and also updates the dashboard and the tracker log.
3. **End of the week:** the `check-in` job (Sat 19:45, every week) asks you once for the period's results in a session you can open from your phone; your answers fill "End-of-week check-in" and refresh the dashboard.

## What the parts mean

| Part | What goes in |
|---|---|
| `## Due this week` | Table `Item / Official deadline / Personal target / Bonus / Status`. Status cells start with the verdict (`done 3.5 / 4 (...)`, `submitted (...)`, `open`, `not released yet`) and keep the old value (`... Before: open`). |
| `## Results this week` | One line per result, with date, score and where it came from. |
| `## Notes` | Plan changes, events, collisions; the first note says who created the page and what was carried over. |
| `## End-of-week check-in` | Done, focused hours, what worked, what didn't, missed, self-rating, rolls over. Each line says `_To fill_` until the check-in fills it. |

## Status values

| `status` | Meaning |
|---|---|
| `upcoming` | created ahead of time; not the live week yet |
| `current` | the live week (only one page at a time) |
| `done` | closed. The check-in may still be open: it is done when no `_To fill_` marker is left. |

## For agents

The exact formats (done-status vocabulary, deadline and bonus cells, the lifecycle table, carry-over attribution) are in [progress-tracking](../../_agent/progress-tracking.md). Never delete a week page; never rewrite a past week except to apply a result or the check-in.

Placeholders in the template, filled by `uni-os new-week` (or by an agent by hand): `{{week.number}}` (term week), `{{week.nn}}` (two digits), `{{week.monday}}` and `{{week.sunday}}` (ISO dates), `{{week.label}}` (e.g. "Mon 14 Sep to Sun 20 Sep 2026"), `{{week.status}}`, and `{{date:YYYY-MM-DD}}` (today). The course rows of the template come from your course list and are replaced by the week's real items.
