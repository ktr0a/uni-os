---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent]
---
# Agent start page

You are an AI agent helping **Alex Example** (handle `alex`) with Autumn 2026 at Example Institute of Technology (BSc Computer Science). This vault, the folder that contains this `_agent/` folder, is the **primary store** of everything about their studies: courses, deadlines, progress, plans, study material, and what is known about how they learn. Don't rely on memory from other chats, on agent memory or on general knowledge when this folder has the answer: read it.

## Read in this order
1. **[rules.md](rules.md)**: every standing rule (replies, precision, study-material format, academic integrity per course, calendar, working style). **Non-negotiable.** Re-read it at the start of every session and after every context compaction, because it changes.
1. **Get today's real date and time** in `Europe/Zurich` from the system clock or a tool, never from memory, and compute the term week: week 0 starts Mon 2026-09-14; week *n* starts 2026-09-14 + 7*n* days. With the Uni OS framework checked out, `python tools/uni_os.py week --date <YYYY-MM-DD>` prints it. Write dates as "Mon 26 Oct 2026 (week 6)".
1. **[../progress/current-status.md](../progress/current-status.md)**: where each course stands, what is done and what is open, the next days.
1. **The course card you need** (facts, rhythm, assessments, sources, file index):
   - AD: [AD/ad.md](<../AD/ad.md>)
   - DM: [DM/dm.md](<../DM/dm.md>)
   - LA: [LA/la.md](<../LA/la.md>)
   - PROG: [PROG/prog.md](<../PROG/prog.md>)
1. **Before you give study advice or make any plan:** the student model in [../me/](../me/profile.md): [profile](../me/profile.md), [learning style](../me/learning-style.md), [rhythm and habits](../me/rhythm-and-habits.md), [weak spots](../me/weak-spots.md). Validate every plan against the rhythm file.
1. **Before you write anything:** [CONVENTIONS.md](CONVENTIONS.md) (where each kind of fact goes, how to write, how to reach the vault from your runtime).
1. **As needed:**
   - [../semester/calendar-and-dates.md](../semester/calendar-and-dates.md) (term dates, deadlines, timezone and DST dates) and [../semester/planning-system.md](../semester/planning-system.md) (calendars, block notation).
   - [roles/README.md](roles/README.md) (common rules for every role, routing table) and your own role brief in `roles/`.
   - The course-facts skill in `skills/course-facts/` (weekly rhythm, session offsets, assessments, where to look things up).
   - [tools-and-environment.md](tools-and-environment.md) (tool tricks and gotchas learned the hard way).
1. **Where any file lives:** [../where-to-find-what.md](../where-to-find-what.md). **What runs where:** [system-handbook.md](system-handbook.md).

## Before you finish any task
**Update the vault** with anything new and even slightly useful, following [CONVENTIONS.md](CONVENTIONS.md): results, errors to log, new rules or preferences, course facts, lecture progress, new study pages, plans, links, tool tricks. Do it in the same turn and without being asked. Re-read a file right before you edit it, keep edits small, keep the properties block and bump `updated`. If you can't reach the vault, or can only create new files, say so in your reply and follow CONVENTIONS section 9.

## If you are ...
| You are | Also read | Remember |
|---|---|---|
| An interactive session on the student's laptop | nothing extra | You edit files directly. Laptop commands follow the posture in `rules.md` ("Working style"). |
| A role session (one durable job, e.g. exercise help for one course) | [roles/README.md](roles/README.md), your brief `roles/<role>.md` | Re-read both after every compaction. Other roles' work is not yours: say where it should go. |
| A scheduled job | Your prompt in `_agent/jobs/<job>/prompt.md` is complete | Never ask the student anything in a headless run. Silence is the norm: no "all good" messages. |
| An agent other than Claude Code | nothing extra | Uni OS has only been tested with Claude Code. The files are plain Markdown and work the same; where a Claude feature is named, `tools-and-environment.md` ("Agent platform notes") gives the fallback. |

## What lives where (short)
| Area | Audience | Content |
|---|---|---|
| `Home.md`, `README.md`, `where-to-find-what.md`, `inbox/`, `me/`, `progress/`, `semester/`, `resources/`, the course folders, `views/` | Alex Example (agents read it too) | the human-facing second brain: short, linked, tables over prose |
| `_agent/` | agents | this page, rules, conventions, the component registry, tool notes, roles, jobs, skills, logs, operational state, archive |
| `_templates/` | Obsidian and agents | templates for new notes: copy their properties |
| `.obsidian/` | Obsidian | settings; never edit unless the student asks |

Old paths in older files and logs (after a reorganisation): `_agent/old-path-map.md`, if it exists. Logs are never rewritten, so old paths stay in them.

## Time and dates
- Timezone: **Europe/Zurich**. Every file name, log line and date in a note uses local time. Convert UTC timestamps from tools first; around daylight-saving switches an hour slips easily.
- Term: Autumn 2026, week 0 = Mon 2026-09-14, last lectures 2026-12-18, lecture-free from 2026-12-19, exam session 2027-01-25 to 2027-02-19. All key dates: [../semester/calendar-and-dates.md](../semester/calendar-and-dates.md).
- Write absolute dates with the weekday ("Tue 3 Nov 2026"), never "yesterday" or "next Monday" in a file.
