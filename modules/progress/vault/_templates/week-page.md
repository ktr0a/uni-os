---
type: week
week: {{week.number}}
start: {{week.monday}}
end: {{week.sunday}}
status: {{week.status}}
audience: me
updated: {{date:YYYY-MM-DD}}
tags: [uni/week]
---
# Week {{week.number}}: {{week.label}}

{{#if modules.planning}}
Plan: [week-{{week.nn}}-plan.md](../../semester/plans/week-{{week.nn}}-plan.md)

{{/if}}
## Due this week
| Item | Official deadline | {{study.target_column}} | Bonus | Status |
|---|---|---|---|---|
{{#each courses}}{{#each course.assessments}}| {{course.short}} {{item.name}} | {{item.schedule}} |  | {{item.counts_for}} | open (from the course rhythm; replace with this week's real item) |
{{/each}}{{/each}}

## Results this week
- 

## Notes
- 

## End-of-week check-in
- Done: _To fill_
- Focused hours: _To fill_
- What worked: _To fill_
- What didn't: _To fill_
- Missed: _To fill_
- Self-rating: _To fill_
- Rolls over: _To fill_
