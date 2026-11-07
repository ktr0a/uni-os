---
type: status
audience: both
updated: {{generated.date}}
tags: [uni/progress]
---
# Progress dashboard

**Snapshot: set up on {{generated.date}}, no results recorded yet.** The full dated history is in [tracker-log.md](tracker-log.md); the week pages are in [weeks/](weeks/README.md). Update this page whenever a result or bonus point comes in (rules for agents: [progress-tracking](../_agent/progress-tracking.md)).

## Bonus standing
| Course | Banked | Bonus now | What's still needed | Full bonus at |
|---|---|---|---|---|
{{#each courses}}| **{{course.short}}** | {{#if course.bonus.scheme}}nothing graded yet{{else}}no bonus scheme{{/if}} | {{#if course.bonus.scheme}}0 of {{course.bonus.max_bonus}}{{else}}-{{/if}} | {{#if course.bonus.scheme}}everything: {{course.bonus.description}}{{else}}-{{/if}} | {{#if course.bonus.scheme}}{{course.bonus.rule}}{{else}}-{{/if}} |
{{/each}}

{{#each courses}}
{{#if course.assessments}}
### {{course.short}} detail
| Stream | Results | Total |
|---|---|---|
{{#each course.assessments}}
| {{item.name}} ({{item.kind}}, counts for {{item.counts_for}}) | none yet |  |
{{/each}}

{{/if}}
{{/each}}
## Exercises: done vs. to do (as of {{generated.date}})
{{#each courses}}### {{course.short}}
- Nothing recorded yet.

{{/each}}
## Self-rated understanding
Not rated yet (the first check-in asks).

Format of the first line of this section (parsed): one part per course, `<short> ~NN %`, parts separated by a middle dot, then the source and date in brackets; earlier ratings after it.

## Next 10 days
| When | What |
|---|---|
|  |  |

Later: nothing recorded yet.
