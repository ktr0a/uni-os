---
type: me
audience: me
updated: {{generated.date}}
tags: [uni/me]
---
# Daily rhythm and habits

<!--
What this page is: {{student.name}}'s energy over the day and the shape of their week. Every planner
reads it before placing a block, and every plan is checked against it: put hard, new material in the
sharpest window, light work in the low, and never cross a hard constraint.
(In the original system a deep proof block once landed in the student's biggest afternoon low, because
the plan was built from a template and not checked against this page.)
How it is kept: edit in place, date changes, strike through retired advice instead of deleting it.
Keep it to what planning needs; health details stay out.
To fill it, say: "Help me fill my rhythm file: walk me through a normal weekday from waking up to bed."
-->

## Day
| Time | What |
|---|---|
| | Up |
| | Sharpest focus |
| | Lunch |
| | Biggest low (light work only) |
| | Second focus window |
| | Stop studying |
| | In bed by (hard cap) |

**So:** hardest or new material HH:MM-HH:MM, easy tasks HH:MM-HH:MM, medium HH:MM-HH:MM. Hard stop for weekday study: HH:MM.

## Focus span
- Focus lasts about __ minutes, then a __-minute break.
- Realistic start time in the morning (the real one, not the ideal one): 

## Week
- Self-study budget: __ h planned, about __ focused hours realistic.
- Class hours per week (lectures and exercise sessions): 
- Rest day: 
- Fixed commitments (sport, job, club, travel home; with day and time): 
- Days for long deep-work blocks: 

## Places
<!-- Where studying works and where it doesn't. If finding a room costs time, every block gets a fixed place in the calendar event's location field. -->
- Works: 
- Doesn't work: 

## Hard constraints
<!-- Rules plans must never break, e.g. "no study after 19:00 on weekdays", "no blocks before 08:00", "Sunday afternoon free". Non-study events may override them as exceptions. -->
- 
{{#if modules.planning}}
- Planner settings (config `[schedule]`, change them there and keep them in line with this page): blocks start from {{schedule.day_start}}, weekday study ends by {{schedule.weekday_stop}}, no blocks after {{schedule.study_cutoff}}, focus {{schedule.focus_minutes}} minutes then a {{schedule.break_minutes}}-minute break.
{{/if}}

## Advice already given
<!-- Keep retired advice struck through, with the date, e.g. "~~Two short blocks before lunch~~ replaced by one 70-minute block (Tue 20 Oct)". -->
- 
