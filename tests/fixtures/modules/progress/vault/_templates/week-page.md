---
type: week
week: {{week.number}}
start: "{{week.monday}}"
end: {{week.sunday}}
status: {{week.status}}
audience: me
updated: {{date}}
tags: [uni/week]
---
# Week {{week.nn}}: {{week.label}}

Plan: [week-{{week.nn}}-plan.md](../../semester/plans/week-{{week.nn}}-plan.md)

## Due this week
| Item | Official deadline | Target | Bonus | Status |
|---|---|---|---|---|
{{#each courses}}
| {{course.short}} {{course.sheet_label}} | | | | not released yet |
{{/each}}

## Results this week

## Notes

## End-of-week check-in ({{schedule.check_in.day}})
- Done:
- Rolls over:
