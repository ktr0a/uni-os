---
type: course
course: {{course.id}}
audience: both
tags: [uni/{{course.id}}, course]
---
# {{course.name}} ({{course.short}})

Assistance default: {{course.assistance}}. Lectures: {{course.lecture_slots}}.

| Assessment | Kind | Counts for | Assistance |
|---|---|---|---|
{{#each course.assessments}}
| {{item.name}} | {{item.kind}} | {{item.counts_for}} | {{item.assistance}} |
{{/each}}

Bonus scheme: {{course.bonus.scheme}}{{#if course.bonus.max_bonus}} (up to {{course.bonus.max_bonus}}){{/if}}.
