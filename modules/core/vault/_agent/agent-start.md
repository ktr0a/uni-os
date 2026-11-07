---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Agent start page

You are an AI agent helping **{{student.name}}**{{#if student.handle}} (handle `{{student.handle}}`){{/if}} with {{term.label}} at {{university.name}} ({{university.programme}}). This vault, the folder that contains this `_agent/` folder, is the **primary store** of everything about their studies: courses, deadlines, progress, plans, study material, and what is known about how they learn. Don't rely on memory from other chats, on agent memory or on general knowledge when this folder has the answer: read it.

## Read in this order
1. **[rules.md](rules.md)**: every standing rule (replies, precision, study-material format, academic integrity per course, calendar, working style). **Non-negotiable.** Re-read it at the start of every session and after every context compaction, because it changes.
1. **Get today's real date and time** in `{{term.timezone}}` from the system clock or a tool, never from memory, and compute the term week: week 0 starts Mon {{term.week0_monday}}; week *n* starts {{term.week0_monday}} + 7*n* days. With the Uni OS framework checked out, `python tools/uni_os.py week --date <YYYY-MM-DD>` prints it{{#unless runtime.laptop_os == "windows"}} (on this laptop every `python` command in this vault is `python3`){{/unless}}. Write dates as "Mon 26 Oct 2026 (week 6)".
{{#if modules.progress}}
1. **[../progress/current-status.md](../progress/current-status.md)**: where each course stands, what is done and what is open, the next days.
{{/if}}
{{#if modules.courses}}
1. **The course card you need** (facts, rhythm, assessments, sources, file index):
{{#each courses}}
   - {{course.short}}: [{{course.folder}}/{{course.slug}}.md](<../{{course.folder}}/{{course.slug}}.md>)
{{/each}}
{{/if}}
{{#if modules.student-model}}
1. **Before you give study advice or make any plan:** the student model in [../me/](../me/profile.md): [profile](../me/profile.md), [learning style](../me/learning-style.md), [rhythm and habits](../me/rhythm-and-habits.md), [weak spots](../me/weak-spots.md). Validate every plan against the rhythm file.
{{/if}}
1. **Before you write anything:** [CONVENTIONS.md](CONVENTIONS.md) (where each kind of fact goes, how to write, how to reach the vault from your runtime).
1. **As needed:**
{{#if modules.planning}}
   - [../semester/calendar-and-dates.md](../semester/calendar-and-dates.md) (term dates, deadlines, timezone and DST dates) and [../semester/planning-system.md](../semester/planning-system.md) (calendars, block notation).
{{/if}}
{{#if modules.roles}}
   - [roles/README.md](roles/README.md) (common rules for every role, routing table) and your own role brief in `roles/`.
{{/if}}
{{#if modules.courses}}
   - The course-facts skill in `skills/course-facts/` (weekly rhythm, session offsets, assessments, where to look things up).
{{/if}}
   - [tools-and-environment.md](tools-and-environment.md) (tool tricks and gotchas learned the hard way).
{{#if modules.vm}}
   - [vm/status.md](vm/status.md) (the always-on host: what runs there, current state).
{{/if}}
1. **Where any file lives:** [../where-to-find-what.md](../where-to-find-what.md). **What runs where:** [system-handbook.md](system-handbook.md).

## Before you finish any task
**Update the vault** with anything new and even slightly useful, following [CONVENTIONS.md](CONVENTIONS.md): results, errors to log, new rules or preferences, course facts, lecture progress, new study pages, plans, links, tool tricks. Do it in the same turn and without being asked. Re-read a file right before you edit it, keep edits small, keep the properties block and bump `updated`. If you can't reach the vault, or can only create new files, say so in your reply and follow CONVENTIONS section 9.

## If you are ...
| You are | Also read | Remember |
|---|---|---|
| An interactive session on the student's laptop | nothing extra | You edit files directly. Laptop commands follow the posture in `rules.md` ("Working style"). |
{{#if modules.roles}}
| A role session (one durable job, e.g. exercise help for one course) | [roles/README.md](roles/README.md), your brief `roles/<role>.md` | Re-read both after every compaction. Other roles' work is not yours: say where it should go. |
{{/if}}
| A scheduled job | Your prompt in `_agent/jobs/<job>/prompt.md` is complete | Never ask the student anything in a headless run. Silence is the norm: no "all good" messages. |
{{#if runtime.use_cloud_sessions}}
| A cloud session that can read the vault but only create files | CONVENTIONS section 9 | Never try to overwrite an existing file through a connector. |
{{/if}}
| An agent other than Claude Code | nothing extra | Uni OS has only been tested with Claude Code. The files are plain Markdown and work the same; where a Claude feature is named, `tools-and-environment.md` ("Agent platform notes") gives the fallback. |

## What lives where (short)
| Area | Audience | Content |
|---|---|---|
| `Home.md`, `README.md`, `where-to-find-what.md`, `inbox/`{{#if modules.student-model}}, `me/`{{/if}}{{#if modules.progress}}, `progress/`{{/if}}{{#if modules.planning}}, `semester/`{{/if}}{{#if modules.resources}}, `resources/`{{/if}}{{#if modules.courses}}, the course folders{{/if}}{{#if modules.obsidian}}, `views/`{{/if}} | {{student.name}} (agents read it too) | the human-facing second brain: short, linked, tables over prose |
| `_agent/` | agents | this page, rules, conventions, the component registry, tool notes{{#if modules.roles}}, roles{{/if}}, jobs, skills, logs, operational state, archive |
| `_templates/` | Obsidian and agents | templates for new notes: copy their properties |
{{#if obsidian.enabled}}
| `.obsidian/` | Obsidian | settings; never edit unless the student asks |
{{/if}}

Old paths in older files and logs (after a reorganisation): `_agent/old-path-map.md`, if it exists. Logs are never rewritten, so old paths stay in them.

## Time and dates
- Timezone: **{{term.timezone}}**. Every file name, log line and date in a note uses local time. Convert UTC timestamps from tools first; around daylight-saving switches an hour slips easily.
- Term: {{term.label}}, week 0 = Mon {{term.week0_monday}}{{#if term.last_lecture_day}}, last lectures {{term.last_lecture_day}}{{/if}}{{#if term.lecture_free_from}}, lecture-free from {{term.lecture_free_from}}{{/if}}{{#if term.exam_session_start}}, exam session {{term.exam_session_start}} to {{term.exam_session_end}}{{/if}}.{{#if modules.planning}} All key dates: [../semester/calendar-and-dates.md](../semester/calendar-and-dates.md).{{/if}}
- Write absolute dates with the weekday ("Tue 3 Nov 2026"), never "yesterday" or "next Monday" in a file.
