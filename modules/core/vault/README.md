# {{student.name}}'s university vault ({{university.short}} {{term.label}})

My university memory{{#if obsidian.enabled}} and an Obsidian vault{{/if}}, built with Uni OS. It does three jobs:
1. **Second brain** for the term: courses, deadlines, progress, plans, study pages.
1. **Memory about me**: preferences, rules for AI helpers{{#if modules.student-model}}, how I learn, my rhythm, my recurring mistakes{{/if}}.
1. **Shared workspace** for every AI agent that helps me: they all read and write here, so nothing lives only in one chat.

| You are | Start at |
|---|---|
| Me{{#if obsidian.enabled}} (in Obsidian){{/if}} | [Home.md](Home.md), the dashboard |
| An AI agent | [AGENTS.md](AGENTS.md), then [_agent/agent-start.md](_agent/agent-start.md) and [_agent/CONVENTIONS.md](_agent/CONVENTIONS.md) |
| Looking for a file | [where-to-find-what.md](where-to-find-what.md) |
| Wondering what runs where | [_agent/system-handbook.md](_agent/system-handbook.md) |

<!-- uni-os:begin map -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current (see _agent/CONVENTIONS.md, "Generated regions"). Write only outside the markers. -->
## Map
```
<vault>/                        ({{storage.provider}} folder{{#if obsidian.enabled}}; Obsidian vault root{{/if}})
├── Home.md                     dashboard: standing, deadlines, this week, course tiles, views
├── README.md                   this file
├── AGENTS.md, CLAUDE.md        entry points for AI agents (point to _agent/agent-start.md)
├── where-to-find-what.md       "I want ... -> open ..." lookup table
├── inbox/                      unsorted drops; an agent sorts them
{{#if modules.courses}}
├── courses-overview.md         all courses at a glance
{{/if}}
{{#if modules.roles}}
├── waiting-on-you.md           what waits on me, by when (optional job waiting-on-you, once switched on)
{{/if}}
{{#if modules.student-model}}
├── me/                         about me: profile, learning style, rhythm and habits, weak spots{{#if modules.experiments}}, experiments{{/if}}
{{/if}}
{{#if modules.progress}}
├── progress/                   current status, append-only tracker log, one page per week (weeks/)
{{/if}}
{{#if modules.planning}}
├── semester/                   dates and deadlines, planning system, study approach, week plans (plans/){{#if modules.daily-prep}}, daily prep notes (prep/){{/if}}{{#if modules.experiments}}, study experiments (experiments/){{/if}}
{{/if}}
{{#if modules.resources}}
├── resources/                  links registry, assistant/TA websites log, course-fact checks
{{/if}}
{{#if modules.courses}}
{{#each courses}}
├── {{course.folder}}/  {{course.name}}: course card {{course.slug}}.md, backlog.md, notes/, reference/{{#if modules.error-logs}}, error log(s){{/if}}{{#if modules.quiz-coaching}}, quiz-prep/{{/if}}{{#if modules.handwritten-notes}}, handwritten notes{{/if}}, official files
{{/each}}
{{/if}}
{{#if modules.obsidian}}
├── views/                      Obsidian Bases views (courses, weeks, study pages, error logs, inbox, recently changed, latest) + vault-map.canvas
{{/if}}
├── _templates/                 templates for new notes, one per note type (lecture note, study page, inbox note{{#if modules.progress}}, week page{{/if}}{{#if modules.planning}}, week plan{{/if}}, ...)
{{#if modules.courses}}
├── z_archive/                  outdated official files the student agreed to replace: <course folder>-outdated-YYYY-MM-DD/ (created when needed)
{{/if}}
{{#if obsidian.enabled}}
├── .obsidian/                  Obsidian settings{{#if modules.obsidian}} (CSS snippet snippets/uni-os.css){{/if}}; don't touch unless needed
{{/if}}
└── _agent/                     FOR AI AGENTS
    ├── agent-start.md          first page for any agent: read order, write-back duty
    ├── rules.md                standing rules (incl. academic integrity per course)
    ├── CONVENTIONS.md          where things go, how to write, how each runtime reaches the vault
    ├── system-handbook.md      every component, where it is defined, where it runs
    ├── tools-and-environment.md  tool tricks and gotchas
{{#if modules.roles}}
    ├── roles/                  role briefs + common rules and routing table; coordinator-state.md, handoffs/, handover/
{{/if}}
    ├── jobs/                   scheduled jobs: job.conf + prompt.md each
    ├── skills/                 agent skills (SKILL.md each)
    ├── tools/                  small scripts the agents run (when a module ships one)
    ├── logs/                   job and sync logs (append-only)
{{#if modules.progress}}
    ├── progress-tracking.md    how standing, bonus arithmetic and done-status words work
{{/if}}
{{#if modules.daily-prep}}
    ├── daily-prep/             the prep runbook, its state and log
{{/if}}
{{#if modules.inbox-sync}}
    ├── inbox-sync/             the update-note protocol and template
{{/if}}
{{#if modules.vault-watch}}
    ├── vault-watch/            the watcher's runbook, alerts and log
{{/if}}
{{#if modules.course-files-fetch}}
    ├── course-fetch/           the fetch runbook and log
{{/if}}
{{#if modules.cockpit}}
    ├── cockpit/                notes for the cockpit plugin (calendar snapshot, assistant prompt)
{{/if}}
{{#if modules.inbox-sync}}
    ├── inbox-applied/          applied update notes, by month
{{/if}}
{{#if modules.heartbeat}}
    ├── heartbeat/              the watcher's flags, state, log and requests ("stop telling me about X")
{{/if}}
{{#if modules.obsidian}}
    ├── obsidian/               graph colour groups, bookmarks and settings to merge into .obsidian/
{{/if}}
{{#if modules.vm}}
    ├── vm/                     state of the always-on host
{{/if}}
    ├── archive/                frozen snapshots of agent material, e.g. archived inbox drops (never the source for current status)
    └── uni-os.toml             the configuration (uni-os.json beside it is generated)
```
<!-- uni-os:end map -->

Each course folder holds the official files (under their official names, never renamed) and my notes side by side. {{#if modules.study-pages}}Study pages come in the formats I chose ({{study.formats}}): {{#if study.formats contains "html"}}{{#if study.formats contains "md"}}an interactive HTML original plus a Markdown copy beside it{{else}}interactive HTML pages that open in the browser{{/if}}{{else}}Markdown pages{{/if}}{{#if study.formats contains "md"}}{{#if obsidian.enabled}} that read{{#if study.formats contains "html"}}s{{/if}} inside Obsidian{{else}} that read{{#if study.formats contains "html"}}s{{/if}} in any Markdown viewer{{/if}}{{/if}}. {{/if}}No email addresses, passwords, keys or private calendar addresses are stored here, on purpose: everything in this folder syncs and every agent can read it.

Built with Uni OS {{generated.version}} on {{generated.date}}. Uni OS has only been tested with Claude Code.
