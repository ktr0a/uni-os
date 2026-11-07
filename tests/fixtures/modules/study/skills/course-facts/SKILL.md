---
name: course-facts
description: Facts about the {{university.short}} courses.
---
# Course facts
{{#each courses}}

## {{course.name}}
{{#each course.assessments}}
- {{item.name}} ({{item.kind}}, counts for {{item.counts_for}}, assistance {{item.assistance}})
{{else}}
- no graded work
{{/each}}
{{/each}}
