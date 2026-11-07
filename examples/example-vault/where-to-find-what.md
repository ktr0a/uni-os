---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/overview]
---
# Where to find what

One page to find any file in this vault. Folder overview: [README.md](README.md). What runs where: [_agent/system-handbook.md](_agent/system-handbook.md).

<!-- uni-os:begin lookup -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current (see _agent/CONVENTIONS.md, "Generated regions"). Add your own rows under "Added in this vault" at the bottom. -->
## Quick answers
| I want... | Open |
|---|---|
| The dashboard | [Home.md](Home.md) |
| My standing per course, what's due in the next 10 days | [progress/current-status.md](progress/current-status.md) |
| Every result and status message, dated | [progress/tracker-log.md](progress/tracker-log.md) |
| This week: due items, results, the check-in | `progress/weeks/week-NN.md` (the one with `status: current`), view [Weeks](views/Weeks.base) |
| This week's plan | `semester/plans/week-NN-plan.md` (the newest), Home "Latest" |
| Term dates, deadlines, exam-session dates | [semester/calendar-and-dates.md](semester/calendar-and-dates.md) |
| The plan for the lecture-free period and the exam session (study blocks) | [semester/plans/exam-phase-plan.md](semester/plans/exam-phase-plan.md) |
| Block notation, calendars, planning rules | [semester/planning-system.md](semester/planning-system.md) |
| How I study, study-approach decisions | [semester/study-approach.md](semester/study-approach.md) |
| Tomorrow's or today's material per study block | `semester/prep/prep-YYYY-MM-DD.md` (the highest `-rN` wins), Home "Study prep" |
| About me: profile, learning style, rhythm, weak spots | `me/`: [profile](me/profile.md), [learning style](me/learning-style.md), [rhythm and habits](me/rhythm-and-habits.md), [weak spots](me/weak-spots.md) |
| My running habit experiment | [me/habits-experiments.md](me/habits-experiments.md) |
| A study-method experiment and its block log | [semester/experiments/README.md](semester/experiments/README.md) (method), `semester/experiments/` (plans and logs) |
| All courses at a glance | [courses-overview.md](courses-overview.md) |
| What's waiting on me (decisions, steps at the laptop), by when | `waiting-on-you.md` at the vault root (written by the optional job waiting-on-you once it is switched on) |
| The rules every AI follows | [_agent/rules.md](_agent/rules.md) |
| Which help an AI may give per course | [_agent/rules.md](_agent/rules.md), section "Academic integrity" |
| Useful links, where course material lives online | [resources/sources-and-links.md](resources/sources-and-links.md) |
| Assistant and TA websites | [resources/ta-websites-log.md](resources/ta-websites-log.md) |
| Which course facts were checked against the official pages | [resources/course-verification.md](resources/course-verification.md) |
| Stop the watcher from mentioning something | [_agent/heartbeat/requests.md](_agent/heartbeat/requests.md) (one line) |
| Something dropped in unsorted | [inbox/](inbox/inbox.md), view [Inbox](views/Inbox.base) |

## Per course
| | AD | DM | LA | PROG | 
|---|---|---|---|---|
| Course card (facts, rhythm, assessments, file table) | [ad.md](<AD/ad.md>) | [dm.md](<DM/dm.md>) | [la.md](<LA/la.md>) | [prog.md](<PROG/prog.md>) | 
| Help policy for AI | `hints-only` | `hints-only` | `hints-only` | `coach` | 
| To-do backlog | [backlog](<AD/backlog.md>) | [backlog](<DM/backlog.md>) | [backlog](<LA/backlog.md>) | [backlog](<PROG/backlog.md>) | 
| Error log(s) | [ad-error-log.md](<AD/ad-error-log.md>) | [dm-error-log.md](<DM/dm-error-log.md>) | [la-error-log.md](<LA/la-error-log.md>) | [prog-error-log-theory.md](<PROG/prog-error-log-theory.md>) [prog-error-log-programming.md](<PROG/prog-error-log-programming.md>) | 
| Study pages (html, md) | `AD/notes/` | `DM/notes/` | `LA/notes/` | `PROG/notes/` | 
| Quiz prep and reviews | `AD/quiz-prep/` | `DM/quiz-prep/` | `LA/quiz-prep/` | `PROG/quiz-prep/` | 
| Reference (course guide, topic plan) | `AD/reference/` | `DM/reference/` | `LA/reference/` | `PROG/reference/` | 
| Official files | subfolders of `AD/` (listed on the card) | subfolders of `DM/` (listed on the card) | subfolders of `LA/` (listed on the card) | subfolders of `PROG/` (listed on the card) | 
| Handwritten notes (tablet app) | the handwritten folder in `AD/` | the handwritten folder in `DM/` | the handwritten folder in `LA/` | the handwritten folder in `PROG/` | 

## Source folders beside the notes
- Official course files sit in each course folder's official subfolders, under their official names. Agents may add new official files there, never rename, move or delete them.
- An official file replaced by a newer version (only with Alex Example's OK) keeps its name in `z_archive/<course folder>-outdated-YYYY-MM-DD/` at the vault root.
- Handwritten notes are written only by the tablet app; agents read and link them.
- App-owned or private folders (if any) are listed in `_agent/CONVENTIONS.md` section 8, with their rules.

## Obsidian
- [Home.md](Home.md) is the dashboard. `views/` holds the Bases views (Courses, Weeks, Study pages, Error logs, Inbox, Recently changed, Latest) and [vault-map.canvas](views/vault-map.canvas).
- `_templates/`: one template per note type (lecture note, study page, inbox note, week page, week plan, and those other modules add).
- `.obsidian/`: settings and the CSS snippet `snippets/uni-os.css` and the cockpit plugin. Don't touch unless asked.

## Agent area (`_agent/`)
| File or folder | What |
|---|---|
| [agent-start.md](_agent/agent-start.md) | first page for any agent |
| [rules.md](_agent/rules.md) | standing rules |
| [CONVENTIONS.md](_agent/CONVENTIONS.md) | where things go, how to write, how to reach the vault |
| [system-handbook.md](_agent/system-handbook.md) | every component, where it is defined, where it runs, change log |
| [tools-and-environment.md](_agent/tools-and-environment.md) | tool tricks and gotchas |
| `uni-os.toml` | the configuration (single source of all settings) |
| [roles/README.md](_agent/roles/README.md), `roles/` | common rules for every role, routing table, role briefs |
| `coordinator-state.md`, `handoffs/`, `handover/` | the coordinator's state page; role handoffs; side-session handovers |
| `jobs/` | scheduled jobs (`job.conf` + `prompt.md` each) |
| `skills/` | agent skills (`SKILL.md` each) |
| `tools/` | small scripts the agents run (when a module ships one) |
| `logs/` | job and sync logs |
| [progress-tracking.md](_agent/progress-tracking.md) | how the status page, bonus arithmetic and done-status words work |
| `daily-prep/` | the prep runbook, its state and log |
| `inbox-sync/` | the update-note protocol, note template, instructions for cloud sessions |
| `cockpit/` | notes for the cockpit plugin |
| `inbox-applied/` | applied update notes, by month |
| `heartbeat/` | the watcher's flags, state, log and requests |
| `obsidian/` | graph colour groups, bookmarks and recommended settings to merge into `.obsidian/` |
| `archive/` | frozen snapshots of agent material (e.g. archived inbox drops) |
<!-- uni-os:end lookup -->

## Added in this vault
Rows for things that have no generated row (a new kind of note, a one-off project). `uni-os render` never touches this section.

| I want... | Open |
|---|---|
