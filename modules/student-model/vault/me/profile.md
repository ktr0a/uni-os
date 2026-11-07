---
type: me
audience: me
updated: {{generated.date}}
tags: [uni/me]
---
# Profile

<!--
What this page is: who {{student.name}} is, written for every agent that advises or plans.
How it is kept: edit in place, date every change, keep the earlier value inline ("Before: ... (date)").
What does not belong here: emails, phone numbers, student IDs, passwords, health details beyond what
matters for planning. The vault syncs to the cloud and every agent can read it.
To fill it, say to your agent: "Interview me for my profile, one question at a time, and fill me/profile.md."
-->

## Basics
- Name{{#if student.handle}} and handle{{/if}}: {{student.name}}{{#if student.handle}} (`{{student.handle}}`){{/if}}
- Programme: {{university.programme}}, {{university.name}}; term: {{term.label}}
- Year or semester in the programme: 
- Exam session: {{#if term.exam_session_start}}{{term.exam_session_start}} to {{term.exam_session_end}}{{else}}(add the dates once they are published){{/if}}
- Courses this term:
{{#each courses}}
  - {{course.short}}: {{course.name}}
{{/each}}
- Prior knowledge (what I already know well, what is completely new): 
- Events this term that affect studying (dated): 

## Self-rated understanding (latest known)
<!--
Re-asked at the periodic check-in and whenever {{student.name}} volunteers one.
Keep the history in the Note cell: "end of week 5. Before: 65 % (Tue 20 Oct, provisional). Earlier: 75 % (Wed 7 Oct)".
Mark mid-week ratings "provisional". Planning uses these: freed time goes to the lowest-rated course first.
-->
| Course | Rating | Date | Note |
|---|---|---|---|
{{#each courses}}
| {{course.short}} | | | |
{{/each}}

## Goals (stated <date>)
<!-- In {{student.name}}'s words, dated. E.g. "Pass every course in the first exam session; get the full bonus in two courses; keep Saturdays free." -->
- 

## Tools I use
- AI agent: {{agent.primary}}
- Vault storage: {{storage.provider}}{{#if obsidian.enabled}}, opened in Obsidian{{/if}}
- Course platform: {{university.lms}}
{{#if modules.planning}}
- Calendars: {{calendar.courses}} (courses), {{calendar.study_blocks}} (self-study blocks), {{calendar.events}} (other events), {{calendar.busy}} (busy time)
{{/if}}
- Other platforms (autograder, git hosting, tablet note app, recorder app): 

## Shorthand I use
<!--
So agents understand {{student.name}}, especially when they dictate. Add nicknames for courses and platforms,
calendar nicknames, prefixes used in calendar titles (e.g. "L:" lecture, "E:" exercise class),
old block names to ignore, and words a dictation app keeps getting wrong.
-->
| I say | Meaning |
|---|---|
{{#each courses}}
| {{course.short}} | {{course.name}} |
{{/each}}

## Groups and course contacts (optional)
<!-- Only what helps agents: your exercise group, who you hand in with (first names are enough), how a TA likes questions asked. No emails, phone numbers or IDs. -->
- 

## See also
[Learning style](learning-style.md) · [Rhythm and habits](rhythm-and-habits.md) · [Weak spots](weak-spots.md)
