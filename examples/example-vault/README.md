# Alex Example's university vault (EIT Autumn 2026)

My university memory and an Obsidian vault, built with Uni OS. It does three jobs:
1. **Second brain** for the term: courses, deadlines, progress, plans, study pages.
1. **Memory about me**: preferences, rules for AI helpers, how I learn, my rhythm, my recurring mistakes.
1. **Shared workspace** for every AI agent that helps me: they all read and write here, so nothing lives only in one chat.

| You are | Start at |
|---|---|
| Me (in Obsidian) | [Home.md](Home.md), the dashboard |
| An AI agent | [AGENTS.md](AGENTS.md), then [_agent/agent-start.md](_agent/agent-start.md) and [_agent/CONVENTIONS.md](_agent/CONVENTIONS.md) |
| Looking for a file | [where-to-find-what.md](where-to-find-what.md) |
| Wondering what runs where | [_agent/system-handbook.md](_agent/system-handbook.md) |

<!-- uni-os:begin map -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current (see _agent/CONVENTIONS.md, "Generated regions"). Write only outside the markers. -->
## Map
```
<vault>/                        (google-drive folder; Obsidian vault root)
├── Home.md                     dashboard: standing, deadlines, this week, course tiles, views
├── README.md                   this file
├── AGENTS.md, CLAUDE.md        entry points for AI agents (point to _agent/agent-start.md)
├── where-to-find-what.md       "I want ... -> open ..." lookup table
├── inbox/                      unsorted drops; an agent sorts them
├── courses-overview.md         all courses at a glance
├── waiting-on-you.md           what waits on me, by when (optional job waiting-on-you, once switched on)
├── me/                         about me: profile, learning style, rhythm and habits, weak spots, experiments
├── progress/                   current status, append-only tracker log, one page per week (weeks/)
├── semester/                   dates and deadlines, planning system, study approach, week plans (plans/), daily prep notes (prep/), study experiments (experiments/)
├── resources/                  links registry, assistant/TA websites log, course-fact checks
├── AD/  Algorithms and Data Structures: course card ad.md, backlog.md, notes/, reference/, error log(s), quiz-prep/, handwritten notes, official files
├── DM/  Discrete Mathematics: course card dm.md, backlog.md, notes/, reference/, error log(s), quiz-prep/, handwritten notes, official files
├── LA/  Linear Algebra: course card la.md, backlog.md, notes/, reference/, error log(s), quiz-prep/, handwritten notes, official files
├── PROG/  Introduction to Programming: course card prog.md, backlog.md, notes/, reference/, error log(s), quiz-prep/, handwritten notes, official files
├── views/                      Obsidian Bases views (courses, weeks, study pages, error logs, inbox, recently changed, latest) + vault-map.canvas
├── _templates/                 templates for new notes, one per note type (lecture note, study page, inbox note, week page, week plan, ...)
├── z_archive/                  outdated official files the student agreed to replace: <course folder>-outdated-YYYY-MM-DD/ (created when needed)
├── .obsidian/                  Obsidian settings (CSS snippet snippets/uni-os.css); don't touch unless needed
└── _agent/                     FOR AI AGENTS
    ├── agent-start.md          first page for any agent: read order, write-back duty
    ├── rules.md                standing rules (incl. academic integrity per course)
    ├── CONVENTIONS.md          where things go, how to write, how each runtime reaches the vault
    ├── system-handbook.md      every component, where it is defined, where it runs
    ├── tools-and-environment.md  tool tricks and gotchas
    ├── roles/                  role briefs + common rules and routing table; coordinator-state.md, handoffs/, handover/
    ├── jobs/                   scheduled jobs: job.conf + prompt.md each
    ├── skills/                 agent skills (SKILL.md each)
    ├── tools/                  small scripts the agents run (when a module ships one)
    ├── logs/                   job and sync logs (append-only)
    ├── progress-tracking.md    how standing, bonus arithmetic and done-status words work
    ├── daily-prep/             the prep runbook, its state and log
    ├── inbox-sync/             the update-note protocol and template
    ├── cockpit/                notes for the cockpit plugin (calendar snapshot, assistant prompt)
    ├── inbox-applied/          applied update notes, by month
    ├── heartbeat/              the watcher's flags, state, log and requests ("stop telling me about X")
    ├── obsidian/               graph colour groups, bookmarks and settings to merge into .obsidian/
    ├── archive/                frozen snapshots of agent material, e.g. archived inbox drops (never the source for current status)
    └── uni-os.toml             the configuration (uni-os.json beside it is generated)
```
<!-- uni-os:end map -->

Each course folder holds the official files (under their official names, never renamed) and my notes side by side. Study pages come in the formats I chose (html, md): an interactive HTML original plus a Markdown copy beside it that reads inside Obsidian. No email addresses, passwords, keys or private calendar addresses are stored here, on purpose: everything in this folder syncs and every agent can read it.

Built with Uni OS 0.1.0 on 2026-11-07. Uni OS has only been tested with Claude Code.
