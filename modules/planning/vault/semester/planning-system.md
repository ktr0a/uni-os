---
type: semester
audience: both
updated: {{generated.date}}
tags: [uni/semester]
---
# Planning system

How your week is planned, written into the calendar and reviewed. Kept by the Plan & progress role ([brief](../_agent/roles/plan-and-progress.md)); you can edit any section, then tell your agent what changed. Last reviewed: {{generated.date}} (set up).

## Calendars
{{#if calendar.provider}}| Calendar | Holds | Who writes it |
|---|---|---|
| **{{calendar.courses}}** | every lecture (title `{{calendar.lecture_prefix}} <course>`) and exercise class (`{{calendar.exercise_prefix}} <course>`), plus graded fixtures that are not part of a class (orals, timed tasks, quizzes in their own slot); a quiz that runs inside a class is not a separate event | you (the official timetable); the planner adds fixtures when their dates are known |
| **{{calendar.study_blocks}}** | your self-study blocks, titled in the block notation below | the planner; the daily-prep job appends the MATERIAL block |
| **{{calendar.events}}** | personal one-offs that can collide with study blocks (appointments, trips, chores) | you; agents read them only to avoid collisions and never copy their titles into files |
| **{{calendar.busy}}** | busy time only (sleep window, fixed commitments) | you |

Agents find these calendars by name every run (with the calendar tool's list function). Calendar ids, private addresses and feed URLs never go into any file.{{else}}No calendar is connected (`calendar.provider = "none"`). The "Blocks" section of each week plan is the schedule; everything below about titles and descriptions applies to those lines instead.{{/if}}

## Block notation (default; change it here and tell your agent)

> [!warning] This is the Uni OS default notation, inherited from the original system.
> You may replace it. Edit the table, set `calendar.notation = "custom"` in `_agent/uni-os.toml`, and tell your agent "I changed the block notation". Dashboards that read titles need the matching patterns too (cockpit: `optional_pattern`, `main_marker`, `lecture_pattern`, `exercise_pattern` in the `[cockpit]` table).

| Notation | Meaning |
|---|---|
| `X_` | X is the main subject of the block |
| `X, Y` | the order the subjects are worked in |
| `(X)` | X is optional |
| `[X]` | reading ahead for the next lecture or exercise class, not consolidating past material |
| `OP` | optional personal (gym, errands): not a study block |
| `(deep)` | a long focus block (about 3 h or more) |

Examples, with X and Y standing for course short names ({{#each courses}}`{{course.short}}` {{/each}}): `X_, Y` · `X_ Sheet 6` · `X_ quiz prep, (Y)` · `[X]` · `X_ Sheet 7 rest, Sheet 8 (deep)` · `OP Gym` · `(Catch-up)` · `(Bad-day overflow)` · `{{calendar.exercise_prefix}} X (other group's class)`.

Titles stay short; everything else goes in the description. **Judge a block by its title, not its description** (descriptions lag behind when a block is moved).

## Event descriptions

A study block's description has these parts, in this order:
1. The tasks in order, with time splits: "14:15-15:40 sheet 7 rest (7.3-7.6); break 15:40; 15:50-17:30 sheet 8".
2. The place (also in the location field).
3. Material links (vault paths or links), as far as the planner knows them.
4. The stop rule and the cut order: "cut 7.7 first, keep at least 60 min for sheet 8; stop 17:30".
5. A `FOCUS:` line: what the block must achieve, in one line or up to six short bullet lines under it. Dashboards show these lines under the block.
6. Last, written only by the daily-prep job: a block starting `MATERIAL (daily prep, ...)`. Nobody else edits it. The planner owns everything above it; the prep job replaces only that last block.

Location: every study block gets a real place in the location field{{#if calendar.default_location}} ("{{calendar.default_location}}" until better spots are named){{/if}}. In the original, "never plan deep or catch-up blocks at home" and "I lose time finding a room" led to this rule.

## Changing the calendar
{{#if calendar.standing_approval}}The planner has **standing approval** to change the {{calendar.study_blocks}} calendar (and to add fixtures to {{calendar.courses}}) without asking first. It always says exactly what it changed. When two options have really different trade-offs, it asks once, with a recommendation.{{else}}The planner **proposes** calendar changes ("Proposed calendar changes, not applied, waiting for your go") and applies them after your yes. Small corrections you asked for directly count as a yes. To give standing approval, set `calendar.standing_approval = true` in `_agent/uni-os.toml` (or tell your agent); the original student did that after the first weeks.{{/if}}

Rules for every edit:
- Re-read the live calendar right before answering or changing anything.
- Edit **single instances**, with notifications off. Never change a recurring series.
- Never change official classes in {{calendar.courses}}; add or update graded fixtures there only when their dates are known.
- Never touch the MATERIAL block. Calendar tools replace the **whole** description on update, so start from the event as it is now (read it first) and keep the final `MATERIAL (daily prep, ...)` block as it is. If you changed what the block is for, keep the old MATERIAL anyway and trigger a prep rerun: the job replaces it.
- After writing, read the event back and check title, times and description: in the original, edits that were reported as applied were not, and the next day ran on old descriptions.
- Record every applied change at the bottom of the week plan under "Calendar edits (applied <time>, single instances, notifications off)": Changed / Created / Deleted.
- Once applied, the calendar wins over the plan file.

## House rules
These come from your rhythm (edit them; the planner reads this section):
- Study blocks start at {{schedule.day_start}} at the earliest; weekday study ends by {{schedule.weekday_stop}}; no study blocks after {{schedule.study_cutoff}}.
- Focus lasts about {{schedule.focus_minutes}} minutes, then a {{schedule.break_minutes}}-minute break. Long blocks get a fixed break written into the description.
- Short slots between classes and the low after lunch take light work only: reading and sizing a new sheet, a short LMS quiz, a 10-minute recap of definitions, rereading an error log, peer grading. No proofs, no new hard material.
- Check every layout against {{#if modules.student-model}}[your rhythm file](../me/rhythm-and-habits.md){{else}}your energy curve (write it into this section: when you focus best, when you dip){{/if}}: the original once put a deep block inside the student's documented low, and it failed for exactly that reason.
- Protected slots (never offered up as free time): _list them, e.g. an exercise class you value_.
- Rest time: _fill in_.

## Planning principles
- **Bonus-bearing and hard-clock work first.** Non-bonus assignments rank below, except the assignment in a quiz's scope right before that quiz.
- **A personal target for every item due this week**{{#if study.personal_deadline_rule}} ({{study.personal_deadline_rule}}){{/if}}, with the official deadline shown next to it.
- **Freshest slots for the hardest subject.**
- **Quizzes:** recall the material in scope the session before; brand-new reading on the quiz morning earns nothing.
- **Count demand against supply** in hours (estimates labelled), so an overloaded week shows before it starts.
- **When time is short, give a cut order** (what to drop first) and a never-cut list, instead of overloading.
- **Rebalance rule:** when a course's bonus work finishes early, the freed time goes to the lowest-rated course (self-ratings in the progress dashboard), not to that course's non-bonus tasks.
- **Stuck rule:** a cold attempt with a timer per difficulty (e.g. 10 / 20 / 25-30 minutes), then one hint, then write the sticking point down and take the next task. The helping session holds the timer too.
- **A missed block is reported, not silently rescheduled.** Find a new slot before the personal target (bonus deadlines first), or drop it on purpose.
- **Plans change by stacked updates**, newest first, never by rewriting.
- **After teaching ends**, blocks no longer need to be on campus; the [exam-phase plan](plans/exam-phase-plan.md) takes over.

## Week-plan procedure
1. **Trigger:** {{#if modules.check-in}}the week-page job asks for the plan once the new week page exists, or {{/if}}you say "plan next week".
2. **Read:** this page, the last plan's open items, the new week page ("Due this week"), [calendar-and-dates](calendar-and-dates.md), your rhythm file, the progress dashboard (self-ratings, bonus standing){{#if modules.experiments}}, and the running experiment's rules{{/if}}, then the live calendar.
3. **Demand vs supply:** hours per item (estimates labelled) against block hours; bonus and hard-clock items first; hardest subject in the freshest slots; personal targets; the rebalance rule.
4. **Write the plan** from the [week-plan template](../_templates/week-plan.md) into `plans/week-NN-plan.md`: blocks (one line per day), deadlines, cut order, "Material per block" (required: the daily-prep job reads it), open items.
5. **Calendar:** titles in notation, descriptions as above, a place for every block; apply (standing approval) or propose.
6. **Ledger:** list every applied change under "Calendar edits".
7. **During the week:** replans are stacked updates at the top of the plan, each quoting your words and listing old -> new per block.{{#if modules.experiments}} After each replan, report the block outcome (done / partial / missed, why) to the running experiment's block log.{{/if}}{{#if modules.daily-prep}} If today's or tomorrow's blocks changed, rerun the prep job (today's blocks: the morning check; tomorrow's blocks after the first evening run: the daily prep); never edit a prep note.{{/if}}
8. **Questions** to you are batched; answers go under "Open items".

## Deadline audit (docs vs calendar, read-only)
Dates live in several places (this folder, the dashboard, the week page and plan, the course cards{{#if calendar.provider}}, the calendars{{/if}}) and drift apart. On request ("audit my deadlines"), and once before the exam phase, the planner compares every dated obligation in the notes with the calendar and with the study blocks before it, **changing nothing**, and writes one report `semester/plans/deadline-audit-YYYY-MM-DD.md`:
- A header with the run time, the term week, "Read-only: nothing was changed", the judging rule ("calendar coverage is judged by event **title**"), and a confidence legend: high = both sides read directly; medium = implied, or one side not verifiable from here; low = inference.
- `## 1. Due within 7 days and at risk`, most urgent first, each with evidence (`file.md l.NN`, or calendar + event title + date) and a confidence level.
- `## 2. Findings` table `| # | What | Docs say | Calendar says | Source | Sure |`.
- `## 3. Results by category`: (1) a date in the docs with no event or a different time; (2) docs that disagree with each other; (3) a course-calendar event that contradicts the docs; (4) graded deadlines in the next 14 days with no study block before them.
- `## 4. Checked and consistent`: one line per deadline family (weekly quizzes, sheets, hand-ins, graded sittings, term end, registration). Proving coverage matters as much as listing problems.
- `## 5. What I checked, and what I could not` (for example LMS states, unpublished exam dates, dates that are only inferred).

Lessons from the original's audit: a date that exists only in an event's description counts as "no event" (titles are what you see); stale duplicates hide in the personal calendar, not the course calendar; doc-vs-doc disagreements are as common as doc-vs-calendar ones; calendar tools can't return very long ranges, so read in chunks of a few weeks. Fixes then go through the usual rules (proposed or applied, ledger in the week plan).

The step-by-step procedure is `_agent/jobs/deadline-audit/prompt.md`. The optional job `deadline-audit` (off when installed) runs it headless once, on the last lecture day{{#if term.last_lecture_day}} ({{term.last_lecture_day}}){{/if}} at {{schedule.day_start}}; switch it on if you want the pre-exam-phase audit to happen without asking.

## Freezing a plan for evaluation
When you want to judge a week structure on clean data, freeze it: block times and the subject of each slot stay fixed for a set period, misses are logged instead of replanned, and change ideas go on a parking list that is opened only at the evaluation date. {{#if modules.experiments}}The full method (freeze rules, valves, success measures) is in [experiments](experiments/README.md).{{else}}The `experiments` module has the full method.{{/if}}

## Week plans (history)
| Week | File |
|---|---|
|  |  |

New week plans go into `semester/plans/week-NN-plan.md` (see [plans/README](plans/README.md)).
