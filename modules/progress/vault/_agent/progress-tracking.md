---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Progress tracking: rules for agents

Read this before you record a result, create or close a week page, or touch `progress/`. The human pages are [current-status](../progress/current-status.md) (the dashboard), [tracker-log](../progress/tracker-log.md) (the history) and [weeks/](../progress/weeks/README.md) (one page per term week). Several formats below are parsed by{{#if modules.cockpit}} the cockpit plugin,{{/if}}{{#if modules.heartbeat}} the heartbeat pre-check,{{/if}} `uni-os doctor` and the scheduled jobs. Keep headings, column names, `x / y` numbers and dates like `Tue 3 Nov 23:59` exactly in the shapes given here.

## 1. Where a result goes

Whenever you learn a result, a bonus point, that a sheet is done or not done, or a self-rating, write it **in the same turn**, unasked, to all four places:

| # | File | How |
|---|---|---|
| 1 | `progress/current-status.md` | edit in place: the course's row in "Bonus standing", its detail table, "Exercises: done vs. to do", and the snapshot line |
| 2 | `progress/tracker-log.md` | append one dated line (section 2) |
| 3 | the course card | properties `bonus_banked`, `bonus_target`, `next_bonus` (section 6) |
| 4 | the week page of the week the item belongs to | its Status cell in "Due this week", plus one line under "Results this week" |

Course cards:
{{#each courses}}- {{course.short}}: `{{course.folder}}/{{course.slug}}.md`
{{/each}}

Writing rules:
- Re-read each file right before editing it; keep edits small and local; keep the properties block and bump `updated`. Two writers may touch these files (the student in Obsidian, another session, a job): never rewrite a whole file from memory.
- **User statements win over derived data.** A platform screenshot beats a guess; the student's own word beats both unless it contradicts the platform, then ask.
- **Never write a number nobody gave you.** No guessed scores, no assumed submissions. Mark estimates "(est.)", inferences "(inferred)", and open questions "**(?)**".
- **Dictated or ambiguous messages:** record them with "**to be confirmed by {{student.name}}**" and tick nothing anywhere until confirmed. Check the platform read-only if the student asks you to.
- **Attribution:** an item carried over into a new week keeps its result in the week it was due in until that week's check-in is done. After that, new results go to the current week.
- Times are local ({{term.timezone}}). Convert tool output from UTC first (a log line stamped one hour ahead happened in the original).

## 2. Tracker log entries

`progress/tracker-log.md` is append-only. One line per event, newest at the bottom:

```
- <Ddd D Mon YYYY> ~HH:MM (<source>): **<key fact>** <details>; <consequence>; <what is still unknown>.
```

- `<source>` says who reported it and through which session: `(user)`, `(user screenshot)`, `({{student.name}} via the coordinator)`, `(Plan & progress)`, `(check-in job)`, `(dictated, via the coordinator)`, `(read-only check of the LMS at {{student.name}}'s request)`, `(heartbeat)`.
- The key fact is bold; consequences follow ("bonus now 38 / 46 graded"); unknowns are stated ("score pending").
- Mark plan-freeze changes with the word `deviation`.
- A wrong line is never edited: append `- <date> ~HH:MM (<source>): correction to the <date> ~HH:MM line: <what is right>.`
- Example (fictional): `- Tue 3 Nov 2026 ~16:30 (user): **AD exercise sheet 6 tasks 1-3 done**; task 4 open (due Thu 5 Nov 23:59); nothing submitted yet.`

The log grows fast (the original reached 61 KB in six weeks). That is why the dashboard exists: nobody should have to read the whole log.

## 3. Week pages: lifecycle

One page per term week: `progress/weeks/week-NN.md`, NN = the two-digit term week (week 0 = Mon {{term.week0_monday}}; week n starts week 0 + 7n days). Template: `_templates/week-page.md`.

| Event | Who | What changes |
|---|---|---|
| Page created | {{#if modules.check-in}}the `week-page` job ({{schedule.week_page.day}} {{schedule.week_page.time}}){{else}}an agent when asked ("create next week's page"){{/if}}, or `uni-os new-week` | new page from the template; "Due this week" filled with the week's real items; `status: current`; the previous page's `status` set to `done` (only that line and `updated`) |
| Page created ahead of time | an agent on request, more than 3 days before its Monday | `status: upcoming`; the next week-page run makes it `current` |
| During the week | every session that hears a result | Status cells, "Results this week", "Notes" |
| Check-in | {{#if modules.check-in}}the `check-in` job ({{schedule.check_in.day}} {{schedule.check_in.time}}, every {{schedule.check_in.every}}){{else}}an agent when the student says "check-in"{{/if}} | "End-of-week check-in" filled (no `_To fill_` marker left); results added; `status: done` if it was `current` |

Two separate facts, two separate signals:
- **`status`** (frontmatter) says which page is the live one. Exactly one page is `current` at a time; between a check-in and the next page there may be none (readers then fall back to the page of today's term week).
- **The check-in is done** when the section `## End-of-week check-in` contains no `_To fill_` marker. A page can be `done` (closed by the next week's page) and still wait for its check-in, e.g. when the check-in runs on a Sunday evening or a Monday. Jobs and the heartbeat look for the marker, never for `status`.

Sections, in this order, with these exact headings: `## Due this week`, `## Results this week`, `## Notes`, `## End-of-week check-in`. Lines:
- Results: `- <Ddd D Mon> ~HH:MM: <item> = **<score>** (<source>). <consequence>`
- Notes: `- <Ddd D Mon> ~HH:MM: <note>`. The page's first note says who created it, when, and what was carried over ("Carried over from week 6: ... Their results belong in week 6 until its check-in.").
- Check-in, filled: one line `Filled <Ddd D Mon> with {{student.name}} (<session>).` then `- **Done:**`, `- **Focused hours:**`, `- **What worked:**`, `- **What didn't:**`, `- **Missed:**`, `- **Self-rating:**`, `- **Rolls over:**`, each replacing its `_To fill_` line. Quote the student where it helps.

## 4. The "Due this week" table

```
| Item | Official deadline | {{study.target_column}} | Bonus | Status |
|---|---|---|---|---|
| AD exercise sheet 6 (out Thu 29 Oct) | Thu 5 Nov 23:59 | Sun 1 Nov | 10 pts | open: tasks 1-3 done, 4 open |
| AD exercise sheet 7 (out Thu 5 Nov) | Thu 12 Nov 23:59 | Sun 8 Nov | 10 pts (est.) | not released yet |
| DM graded sheet 4 (out Mon 2 Nov) | Mon 9 Nov 12:00 | Sun 8 Nov | 2 pts (solo) | done 1.5 / 2 (Fri 6 Nov ~16:10, LMS feedback) |
| DM practice sheet 7 | tutorial Tue 3 Nov 16:15 |  | none | done (discussed in class) |
| LA online quiz 7 | Mon 9 Nov 09:00 |  | 4 pts (solo) | open |
```

(Fictional rows for the example student. The examples in this file are invented; your own week pages hold your real items.)

Columns are found by their header words, so keep them: `Item`, `Official deadline`, the personal-target column (`{{study.target_column}}`; readers find it by the word "target", the original called it "Sunday target"), `Bonus`, `Status`.

Cells:
- **Item:** starts with the course's short name ({{#each courses}}`{{course.short}}` {{/each}}) so readers can tell the course; unique within the week (Done taps match the Item cell exactly).
- **Official deadline:** `Ddd D Mon HH:MM` with English abbreviations and 24 h time (`Tue 3 Nov 23:59`); a range `Wed 11 Nov 14:15-14:45` for sittings (counts down to the start, "running" until the end); a room may follow after a comma. Always write the time. **Soft** dates (no hand-in): start the cell with `tutorial` or add `(tentative)`; they are never overdue. Unverified dates carry `(inferred)` or `(unconfirmed)`.
- **Personal target:** a date `Ddd D Mon` from the personal deadline rule{{#if study.personal_deadline_rule}} ("{{study.personal_deadline_rule}}"){{/if}}, empty when none applies.
- **Bonus:** `4 pts`, `2 x 2 pts (est.)`, or one of `none`, `no`, `feedback only` (these three mean "no bonus": a passed open item without bonus lapses quietly instead of showing as overdue).
- **Status:** the verdict first, then the evidence in brackets, then the old value when it changes: `submitted (LMS shows "Submitted for grading", checked Wed 4 Nov ~21:10). Before: open`.

### The done-status vocabulary (contract)

Readers classify a Status cell in this order, after leading spaces and Markdown emphasis (`**`, `__`, `*`, `_`) are stripped, ignoring case:

1. **Done tap mark:** `done (<Ddd D Mon HH:MM>, tapped). Before: ...` is **done**, whatever follows `Before:`.
2. **Pending:** the cell contains `not reported`, `pending` or `not recorded` anywhere: the item took place but its result isn't recorded yet. Readers ask for the result instead of calling it overdue. This wins over a done word at the start: `submitted (score pending)` is pending until the score is in.
3. **Done:** the cell **starts with** one of `✓` · `done` · `submitted` · `closed` · `handed in` · `uploaded` · `dropped` · `skipped` (as whole words) or a score `x / y` / `x/y` (e.g. `3.5 / 4`).
4. **Not released:** the cell contains `not released` (`not released yet`): a future item, no Done button.
5. **Open:** anything else (`open`, `open: ...`, `in progress ...`, `not done`, `not submitted`, empty). Open items are **overdue** once the deadline (or the end of a range) has passed, unless the date is soft, or the item has no bonus (then it lapses quietly).

A cell that starts with `not` never starts with a done word, so `not done` and `not submitted` are always open (and overdue after the deadline).

Write cells so that this strict rule and the looser reading "contains done / submitted / x/y / ✓ and not 'not done'" agree, by putting the verdict first:
- Good: `open: tasks 1-2 done, 3 open`, `in progress (2 of 4 tasks)`, `done 7 / 10 (Thu 12 Nov ~10:30, LMS)`, `dropped (no bonus; Wed 4 Nov, {{student.name}})`, `submitted (score pending)`.
- Bad: `tasks 1 and 2 done, 3 open` (a loose reader closes it), `2/2 done, task 3 open` (starts with a score, so even the strict rule closes it: split the row instead).

In the original, "done" or `x / y` anywhere in a cell counted as done, and that hid an open two-point bonus task until the rule became "only the start of the cell counts". Closed-by-choice items were reworded so they parse ("skipped by choice ..." instead of "not submitted, skipped").

A Done tap from a dashboard is applied by the inbox sync as `done (<Ddd D Mon HH:MM>, tapped). Before: <old cell>`; an undo puts back what follows `Before: `. Never remove a `tapped)` mark by hand; ask instead.

## 5. `progress/current-status.md` (the dashboard)

Sections and parsed shapes, in this order:
1. **Snapshot line**, the first bold line: `**Snapshot: <Ddd D Mon YYYY>, <time of day> (end of term week N).**` Re-date it on every update. A table that is older than the snapshot gets an inline note ("The table below dates from Thu 5 Nov.").
2. `## Bonus standing`: `| Course | Banked | Bonus now | What's still needed | Full bonus at |`, one row per course, the arithmetic written out (section 6).
3. `### <short> detail` tables `| Stream | Results | Total |` for courses with several assessment streams (results listed in order with dates, totals as `x / y`).
4. `## Exercises: done vs. to do (as of <Ddd D Mon>)` with one `### <short>` subsection per course: bullets per sheet (done, open, moved to the backlog, dropped and why). Dashboards show each subsection in that course's panel.
5. `## Self-rated understanding`: the **first line** is parsed: parts separated by ` · `, each `<short> ~NN %` (or `NN-MM %`), then the source and date in brackets. History follows on the same paragraph ("Before: ..., earlier: ...").
6. `## Next 10 days`: table `| When | What |`, When = `Ddd D Mon[ HH:MM]`, several items in one row separated by ` · `. Readers drop rows older than today; the check-in prunes them. A callout may sit above the table (e.g. a plan freeze). After the table one paragraph `Later: ...` for dates beyond 10 days.

Keep the headings exactly (the "Next 10 days" heading is embedded on the Home page too).

## 6. Bonus and grade tracker logic

Inputs: the course's `[[courses.assessments]]` in `_agent/uni-os.toml` (name, kind, `counts_for` = bonus | grade | admission | none, optional `points_max` and `dates`), its `[courses.bonus]` table (`scheme`, `max_bonus`, `description`, `rule`, and where set `threshold`, `total`, `total_estimated`, `proportional`, `full_at`, `required`, `unit`, `counts`), the course card, and the results recorded so far. The `rule` text is the authority; the numbers below only make it explicit.

Per scheme (show the arithmetic in "What's still needed"):

| Scheme | Meaning | Bonus now | Still needed |
|---|---|---|---|
| `threshold` | full bonus at a share (`threshold`, e.g. 0.8 = 80 %) of all points of the term; proportionally less below (`proportional = false`: all or nothing) | `max_bonus x min(1, banked / (threshold x total))`, or 0 below the line if not proportional | `threshold x total - banked` out of the points still available (`total - graded so far`), and the average share of each remaining point that requires |
| `points` | linear in points up to `full_at` (default: `total`, i.e. no slack); e.g. "5 of 7 quiz points give the full bonus" (`total = 7`, `full_at = 5`) or "bonus = 0.25 x points / 12" (`total = 12`) | `max_bonus x min(1, banked / full_at)` | `full_at - banked` from the fixtures left (count them from `dates`), and the average per remaining fixture |
| `best-n` | `required` of `total` assessments must be passed (admission style, e.g. "8 of 10 sheets"); proportional below if `proportional = true` | full when `passed >= required`, else `max_bonus x passed / required` if proportional, else 0 | `required - passed` more passes, out of the fixtures left |
| `custom` | follow `rule` literally (e.g. "average of the best 10 of 12 quizzes >= 70 %") | as the rule says | as the rule says |
| `none` | no bonus | `-` | `-` |

These are the same semantics the cockpit's bonus engine uses, so the dashboard and the cockpit agree. When a course's real rule doesn't fit a scheme exactly, say so in `rule` and compute from the rule.

- **Totals that are not published are estimates.** Derive them from the rhythm (e.g. "12 sheets x 10 ~ 120 (est.)"), write "(est.)" and say "the official maximum is not published".
- Assessments with `counts_for = "grade"` (a midterm, a project) go in the detail table with their weight; "Bonus now" stays `-`. `admission` items (e.g. "50 % of the programming exercises to be admitted") show the requirement and the count so far in "What's still needed".
- Never round in the student's favour; keep two decimals; say "on track" only with the numbers next to it.
- Fictional example row: `| **AD** | **38 of 46 graded points (83 %)** | on track | Estimated term total ~156 (12 sheets x ~8 (est.) = 96, plus 3 quizzes x 10 counted double = 60). 80 % ~ 124.8, so **~87 more out of the ~110 still available (~79 %)**. Estimate: the official maximum is not published. | 80 % of all points |`

Course-card properties (in each card's frontmatter; dashboards and the heartbeat read them):
```yaml
bonus_banked: "38 / 46 graded (83 %)"      # the first "x / y" pair is parsed: banked / graded so far
bonus_target: "80 % of ~156 pts (est.)"    # threshold courses: "NN % of ~M" is parsed for the pace check
next_bonus: "Wed 11 Nov 14:15 AD quiz 2 (solo)"
```
For points and best-n courses write e.g. `bonus_banked: "3.5 / 4 graded sheet points"` and `bonus_target: "8 points"`. Update all three whenever a result comes in and at every check-in.

## 7. Self-ratings

Asked at every check-in ("how well do you understand each course, in %"). Copy the answer into `current-status.md` ("Self-rated understanding", first line){{#if modules.student-model}}, into `me/profile.md` ("Self-rated understanding", earlier values kept in the Note cell){{/if}} and one tracker line. Mid-week ratings are labelled "provisional". The ratings drive the rebalance rule of the planner: freed time goes to the lowest-rated course.

## 8. Never

- Never delete or rewrite tracker lines, week pages or results; correct by appending.
- Never record a result for graded `solo` work beyond the score itself (no solutions, no transcripts of the student's own work).
- Never change a Status cell to done without evidence (the student's word, a platform view, or a tap).
- Never put emails, passwords, API keys or calendar addresses into these files.
- Never edit files in `semester/prep/` (prep notes are written only by the prep jobs).
