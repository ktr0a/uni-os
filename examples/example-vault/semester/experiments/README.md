---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/semester]
---
# Study experiments

How to test a change to the way you study (the layout of the week, a technique, a rule) so that the result means something. One experiment at a time, a fixed period, logged per block, reviewed on a date set in advance. Habit changes outside study (sleep, evenings) use the lighter format in [me/habits-experiments](../../me/habits-experiments.md).

## Files
Per experiment, these files in this folder (unique names, prefixed with the month and a slug):
- `YYYY-MM-<slug>-plan.md`, from the [experiment-plan template](../../_templates/experiment-plan.md): trigger, evidence, diagnosis, the change, period, pre-registered measures, baseline, confounders, freeze rules, parking list, running review notes, verdict.
- `YYYY-MM-<slug>-block-log.md`, from the [block-log template](../../_templates/experiment-block-log.md): one line per study block. **Append-only.**
- `YYYY-MM-<slug>-coverage.md`, from the [coverage-list template](../../_templates/experiment-coverage.md): written a day or two before the review (method step 8).

Decisions that come out of an experiment go into [study-approach](../study-approach.md) with the date and your words.

## The method
1. **Trigger.** A bad stretch, stated with evidence ("the week ended mostly undone again, although I worked on six of seven days").
2. **Evidence.** Gather it before proposing anything: the tracker log, the week pages, the error logs, last week's calendar by title, your answers. Write it as observations with sources; mark estimates "(est.)"; list "constraints already known (do not ask again)".
3. **Diagnosis with supply and demand.** A table `| Item | h/week | Note |` of what the work needs at your current speed, against the focused hours the week really yields (not the planned hours). The original's finding: "capacity is fragmented, not missing": about 38 planned hours in 1-2 h pieces yielded about 18-22 focused hours against ~25 needed, so every week ended 3-6 h short and the gap landed on whatever was scheduled last.
4. **Levers.** A short numbered list of concrete, checkable changes, per course where needed ("build the week around four deep blocks", "worked example first", "start the sheet on release day, finish by Thursday"). Say what to drop or accept. You adopt, change or reject; quote your answer.
5. **Pre-register** before the first day: the period (2 weeks by default), the checkpoints and success measures (rough guides, not hard cut-offs), the review date, and the known confounders. Put calendar blocks on the coverage-list day (a day or two before the review) and on the review date, so both have a trigger.
6. **Log every block.** One line per study block in the block log (format below), as you report it. Misses are logged as misses.
7. **Review notes while it runs.** Dated observations in the plan's "Review notes" section, each followed by `-> Review question: ...` or `-> Reading for the review: ...`. Tally as you go ("6 done, 8 partial, 4 missed or failed").
8. **Coverage list first (a day or two before the review).** Write `YYYY-MM-<slug>-coverage.md` from the [coverage-list template](../../_templates/experiment-coverage.md): which planned study blocks have no logged outcome, so you are asked about the holes once, in one batch, before the review rather than during it. It is a coverage list, not an assessment:
   - `## At a glance`: blocks ended, blocks with at least one log line, holes with their total planned minutes, the weakest day.
   - Per day a table `| Block | Logged outcome | Note |`. CAPITALS (`DONE`, `PARTIAL`, `MISSED`, `FAILED`) are the log's own verdict words; a lower-case word with `*` is the reader's own interpretation of a line that has no verdict word ("partial*").
   - `## Holes`: blocks with no log line (with planned minutes), lines with a missing piece (no minutes, no verdict), days with no line at all, and which checkpoints each hole affects.
   - One batch of short questions (a few words each). Check that the planner isn't already asking the same ones, so nobody is asked twice.
   - `## What I checked and what I inferred`: every inference listed. A moved or retitled block is matched through its own description; duplicates in the append-only log are stated as judgment calls, never edited out.
   - The answers go into the block log as new lines (source: you, via the coverage list); what stays unknown is marked "not reported", never invented.
9. **Review on the date, not before**, and not without the coverage list: if it is missing on the review date, write it first. Check each checkpoint against the log and the results; write a verdict: **keep / change / try next**, at most three items each, every item with its evidence and caveats. Record decisions in `study-approach.md`; calendar and plan changes go to Plan & progress.
10. **Freeze the next design** if you want to judge it on clean data (below).

## Freeze rules (a frozen plan)
For a structure you want to evaluate, freeze it for a set period (the original froze three weeks: "I want to have a system which we can fix ... so we can have a proper evaluation. Every week, I'm trying to change something, and this is not good. It's very bad for data."):
1. Block times and the subject of each slot don't change until the evaluation date. That holds for every session and job.
2. **Not a change:** which tasks go into a block (the prep job fills the MATERIAL); the bad-day rule; the declared valves (e.g. an overflow slot, off by default, and a default slot that overflow may take); a small boundary shift (about 20 minutes) at a task boundary; the exceptions declared at the start.
3. **A missed block is logged as missed, not replanned.** Its item goes to a valve or is dropped.
4. A real change only for a new fixed event (e.g. an exam date); it gets one tracker-log line marked `deviation`.
5. Ideas for changes go on the **parking list** at the end of the plan, looked at on the evaluation date, not before.
6. Data per deep block: planned vs real start, focused minutes, focus 1-5, what got done. Outcomes to compare: the graded results of the period and the share of each sheet done.

Success measures are agreed up front as rough guides (the original's: blocks that happened at least 80 %; on time within 20 minutes at least 70 %, mornings vs afternoons; median focus at least 3 of 5, afternoons included; every bonus item due in the period submitted). The original student: "we both don't know yet which success measure is actually successful", so they may adapt as the data shows what matters.

## Block log format
```
| Date | Block | Subject | Focused min (focus 1-5) | Done |
|---|---|---|---|---|
| Tue 10 Nov | 08:00-09:45 morning block (started ~08:10, stopped 09:40) | AD sheet 7.2 (bonus) | ~80 (4) | DONE: first version ~09:05; stuck on a recurrence, fixed with one hint. Source: Alex Example, via Plan & progress |
```
- **Block:** planned time, then planned vs real start and stop.
- **Focused min:** the student's own estimate, `~` in front; focus 1-5 if given.
- **Done** starts with a verdict word: **DONE**, **PARTIAL**, **FAILED**, **MISSED** or **SKIPPED**; then what got done, the traps, what fixed it, why it slipped; and ends with `Source: <who reported it, via which session>`.
- Tags: `OUTLIER DAY` (excluded from averages, with the reason), `INFERRED` for anything not reported by the student. Unknown at the end of the day: ask once, batched; never invent.

## Who runs it
By default the **Plan & progress** role keeps the block log and the review notes: it already hears about every missed or moved block. In the original, a separate "trial owner" session kept them and never edited the calendar or the week plans (it sent changes to the planner); that separation keeps the evaluator independent of the plan's author. To get it, ask your agent to create a role "Experiment owner" from this brief:

> Run one time-boxed study experiment: keep the block log (append-only), collect patterns as review questions in the plan's review notes, ask the student once a day (batched) for blocks whose outcome is unknown, and run the review on the agreed date with the student (verdict keep / change / try next with evidence and caveats). Record decisions dated in `semester/study-approach.md`. Never edit the calendar or the week plan: send changes to Plan & progress and say so. Don't push options the student said they didn't want.

## Rules
- One change at a time. Don't run a technique test in the same weeks as a layout test, or list it as a confounder (the original credited nothing to a habit experiment that overlapped a layout trial).
- Validate a new layout against `me/rhythm-and-habits.md` before it starts.
- Self-reported minutes are rough; tag outlier days and leave them out of averages.
- Quote the student's words for every decision; say what is inferred.
- Features must be easy to switch off: the original dropped error-log retests after a week ("that doesn't really work"); keep old artefacts read-only, don't delete them.
