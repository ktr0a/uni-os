---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/plan]
---
# Plans

The written plan for each week, plus special plans (a week with a big outside event, a long weekend, the exam phase). Written by the Plan & progress role, read by you, by the daily-prep job and by the heartbeat.

## Files

| File | What |
|---|---|
| `week-NN-plan.md` | the plan of term week NN (two digits), from the [week-plan template](../../_templates/week-plan.md) |
| `week-NN-<topic>-plan.md` | a special plan inside a week (e.g. a weekend replan) |
| [exam-phase-plan.md](exam-phase-plan.md) | the frame for the lecture-free period and the exam session |
| `deadline-audit-YYYY-MM-DD.md` | a read-only docs-vs-calendar audit (see "Deadline audit" in [planning-system](../planning-system.md)) |

Dashboards pick "the newest plan" by file name, so keep the zero-padded `week-NN` prefix.

## Shape of a week plan

1. Title `# Week N plan (<Mon D Mon> to <Sun D Mon YYYY>): <context>` and one provenance line: who wrote it, when, on which basis, and whether the calendar edits are applied.
2. **Updates, stacked at the top, newest first**: `## Update <Ddd D Mon> ~HH:MM: <what changed> (<who decided>)`, quoting the student, listing each changed block as `**Mon 16:15-18:00** "<old title>" -> "<new title>": <content>`, the hours moved, and what it supersedes.
3. `## Where the week starts`: the state per course.
4. `## Rules`: the rules in force (unchanged unless noted).
5. `## Deadlines this week`: table `| Item | Deadline | Bonus |`.
6. `## Demand (hours, estimated)` and the supply it is compared with.
7. `## Blocks`: **one line per day** `- **Mon:** 08:00-09:45 <title> · 13:15-14:00 <title> · ...` (titles exactly as in the calendar), optionally followed by a table `| When | Title | Content, in order |`. The day lines are parsed by the heartbeat when no prep note exists.
8. `## If the week runs slow, cut in this order` and "Never cut: ...".
9. `## Material per block (links go in the descriptions; the prep jobs fill the MATERIAL part)`: per course, the sheets, study pages, script sections (with "PDF page = printed + N" offsets) and platform links the week needs. **Required**: the daily-prep job reads it.
10. `## Open items`: decisions pending, items for later plans, answered questions (with the answer).
11. `## Calendar edits (applied <Ddd D Mon HH:MM>, single instances, notifications off)`: Changed / Created / Deleted.

Once the edits are applied, the calendar is the source of truth; a later correction says "the block table below is the pre-correction version".
