---
type: me
audience: me
updated: {{generated.date}}
tags: [uni/me]
---
# Weak spots and recurring mistakes

<!--
What this page is: the pattern view over {{student.name}}'s error logs, quiz reviews and graded feedback.
The detailed, dated entries stay in each course's error log; this page only holds the patterns.
How it is kept: every pattern in a course error log's "Patterns to watch" section (added at the second error of
the same family) gets one line here under that course; a pattern seen in two courses also goes under "Across
courses". When a pattern stops showing up, strike it through with the date; don't delete it. Quiz reviews and
graded feedback (TA corrections, oral feedback) count as sources too. Work that the course marks `solo` never
appears here.
How agents use it: put the relevant patterns into every cheat sheet, study plan, prep note and quiz prep for
that course, and name the pattern when it shows up again in a hint ("this is pattern 2 again").
Format of a pattern line (example, not about you):
1. **Off-by-one in loop invariants**: the invariant is stated for the wrong index range. Fix: check it on
   n = 0, 1, 2 before writing the proof. Source: error log rows Tue 13 Oct, Thu 22 Oct.
-->

## Across courses
<!-- Patterns that show up in more than one course (e.g. skipping the small-case check, misreading the quantifier order). -->
1. 

{{#each courses}}
## {{course.short}} ({{course.name}})
{{#if modules.error-logs}}
Source: {{#each course.error_log_files}}[{{item}}](<../{{course.folder}}/{{item}}>){{#unless @last}}, {{/unless}}{{/each}} (section "Patterns to watch").
{{/if}}
1. 

{{/each}}
