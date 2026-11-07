---
type: overview
audience: both
updated: {{generated.date}}
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
{{#if modules.progress}}
| My standing per course, what's due in the next 10 days | [progress/current-status.md](progress/current-status.md) |
| Every result and status message, dated | [progress/tracker-log.md](progress/tracker-log.md) |
| This week: due items, results, the check-in | `progress/weeks/week-NN.md` (the one with `status: current`){{#if modules.obsidian}}, view [Weeks](views/Weeks.base){{/if}} |
{{/if}}
{{#if modules.planning}}
| This week's plan | `semester/plans/week-NN-plan.md` (the newest){{#if modules.obsidian}}, Home "Latest"{{/if}} |
| Term dates, deadlines, exam-session dates | [semester/calendar-and-dates.md](semester/calendar-and-dates.md) |
| The plan for the lecture-free period and the exam session (study blocks) | [semester/plans/exam-phase-plan.md](semester/plans/exam-phase-plan.md) |
| Block notation, calendars, planning rules | [semester/planning-system.md](semester/planning-system.md) |
| How I study, study-approach decisions | [semester/study-approach.md](semester/study-approach.md) |
{{/if}}
{{#if modules.daily-prep}}
| Tomorrow's or today's material per study block | `semester/prep/prep-YYYY-MM-DD.md` (the highest `-rN` wins){{#if modules.obsidian}}, Home "Study prep"{{/if}} |
{{/if}}
{{#if modules.student-model}}
| About me: profile, learning style, rhythm, weak spots | `me/`: [profile](me/profile.md), [learning style](me/learning-style.md), [rhythm and habits](me/rhythm-and-habits.md), [weak spots](me/weak-spots.md) |
{{/if}}
{{#if modules.experiments}}
| My running habit experiment | [me/habits-experiments.md](me/habits-experiments.md) |
| A study-method experiment and its block log | [semester/experiments/README.md](semester/experiments/README.md) (method), `semester/experiments/` (plans and logs) |
{{/if}}
{{#if modules.courses}}
| All courses at a glance | [courses-overview.md](courses-overview.md) |
{{/if}}
{{#if modules.roles}}
| What's waiting on me (decisions, steps at the laptop), by when | `waiting-on-you.md` at the vault root (written by the optional job waiting-on-you once it is switched on) |
{{/if}}
| The rules every AI follows | [_agent/rules.md](_agent/rules.md) |
| Which help an AI may give per course | [_agent/rules.md](_agent/rules.md), section "Academic integrity" |
{{#if modules.resources}}
| Useful links, where course material lives online | [resources/sources-and-links.md](resources/sources-and-links.md) |
| Assistant and TA websites | [resources/ta-websites-log.md](resources/ta-websites-log.md) |
| Which course facts were checked against the official pages | [resources/course-verification.md](resources/course-verification.md) |
{{/if}}
{{#if modules.heartbeat}}
| Stop the watcher from mentioning something | [_agent/heartbeat/requests.md](_agent/heartbeat/requests.md) (one line) |
{{/if}}
| Something dropped in unsorted | [inbox/](inbox/inbox.md){{#if modules.obsidian}}, view [Inbox](views/Inbox.base){{/if}} |

{{#if modules.courses}}
## Per course
| | {{#each courses}}{{course.short}} | {{/each}}
|---|{{#each courses}}---|{{/each}}
| Course card (facts, rhythm, assessments, file table) | {{#each courses}}[{{course.slug}}.md](<{{course.folder}}/{{course.slug}}.md>) | {{/each}}
| Help policy for AI | {{#each courses}}`{{course.assistance}}` | {{/each}}
| To-do backlog | {{#each courses}}[backlog](<{{course.folder}}/backlog.md>) | {{/each}}
{{#if modules.error-logs}}
| Error log(s) | {{#each courses}}{{#each course.error_log_files}}[{{item}}](<{{course.folder}}/{{item}}>) {{/each}}| {{/each}}
{{/if}}
{{#if modules.study-pages}}
| Study pages ({{study.formats}}) | {{#each courses}}`{{course.folder}}/notes/` | {{/each}}
{{/if}}
{{#if modules.quiz-coaching}}
| Quiz prep and reviews | {{#each courses}}`{{course.folder}}/quiz-prep/` | {{/each}}
{{/if}}
| Reference (course guide, topic plan) | {{#each courses}}`{{course.folder}}/reference/` | {{/each}}
| Official files | {{#each courses}}subfolders of `{{course.folder}}/` (listed on the card) | {{/each}}
{{#if modules.handwritten-notes}}
| Handwritten notes (tablet app) | {{#each courses}}the handwritten folder in `{{course.folder}}/` | {{/each}}
{{/if}}

{{/if}}
## Source folders beside the notes
- Official course files sit in each course folder's official subfolders, under their official names. Agents may add new official files there, never rename, move or delete them.
{{#if modules.courses}}
- An official file replaced by a newer version (only with {{student.name}}'s OK) keeps its name in `z_archive/<course folder>-outdated-YYYY-MM-DD/` at the vault root.
{{/if}}
{{#if modules.handwritten-notes}}
- Handwritten notes are written only by the tablet app; agents read and link them.
{{/if}}
- App-owned or private folders (if any) are listed in `_agent/CONVENTIONS.md` section 8, with their rules.

{{#if obsidian.enabled}}
## Obsidian
- [Home.md](Home.md) is the dashboard.{{#if modules.obsidian}} `views/` holds the Bases views (Courses, Weeks, Study pages, Error logs, Inbox, Recently changed, Latest) and [vault-map.canvas](views/vault-map.canvas).{{/if}}
- `_templates/`: one template per note type (lecture note, study page, inbox note{{#if modules.progress}}, week page{{/if}}{{#if modules.planning}}, week plan{{/if}}, and those other modules add).
- `.obsidian/`: settings{{#if modules.obsidian}} and the CSS snippet `snippets/uni-os.css`{{/if}}{{#if modules.cockpit}} and the cockpit plugin{{/if}}. Don't touch unless asked.

{{/if}}
## Agent area (`_agent/`)
| File or folder | What |
|---|---|
| [agent-start.md](_agent/agent-start.md) | first page for any agent |
| [rules.md](_agent/rules.md) | standing rules |
| [CONVENTIONS.md](_agent/CONVENTIONS.md) | where things go, how to write, how to reach the vault |
| [system-handbook.md](_agent/system-handbook.md) | every component, where it is defined, where it runs, change log |
| [tools-and-environment.md](_agent/tools-and-environment.md) | tool tricks and gotchas |
| `uni-os.toml` | the configuration (single source of all settings) |
{{#if modules.roles}}
| [roles/README.md](_agent/roles/README.md), `roles/` | common rules for every role, routing table, role briefs |
| `coordinator-state.md`, `handoffs/`, `handover/` | the coordinator's state page; role handoffs; side-session handovers |
{{/if}}
| `jobs/` | scheduled jobs (`job.conf` + `prompt.md` each) |
| `skills/` | agent skills (`SKILL.md` each) |
| `tools/` | small scripts the agents run (when a module ships one) |
| `logs/` | job and sync logs |
{{#if modules.progress}}
| [progress-tracking.md](_agent/progress-tracking.md) | how the status page, bonus arithmetic and done-status words work |
{{/if}}
{{#if modules.daily-prep}}
| `daily-prep/` | the prep runbook, its state and log |
{{/if}}
{{#if modules.inbox-sync}}
| `inbox-sync/` | the update-note protocol, note template, instructions for cloud sessions |
{{/if}}
{{#if modules.vault-watch}}
| `vault-watch/` | the watcher's runbook, alerts and log |
{{/if}}
{{#if modules.course-files-fetch}}
| `course-fetch/` | the fetch runbook and log |
{{/if}}
{{#if modules.cockpit}}
| `cockpit/` | notes for the cockpit plugin |
{{/if}}
{{#if modules.inbox-sync}}
| `inbox-applied/` | applied update notes, by month |
{{/if}}
{{#if modules.heartbeat}}
| `heartbeat/` | the watcher's flags, state, log and requests |
{{/if}}
{{#if modules.obsidian}}
| `obsidian/` | graph colour groups, bookmarks and recommended settings to merge into `.obsidian/` |
{{/if}}
{{#if modules.vm}}
| `vm/` | state of the always-on host |
{{/if}}
| `archive/` | frozen snapshots of agent material (e.g. archived inbox drops) |
<!-- uni-os:end lookup -->

## Added in this vault
Rows for things that have no generated row (a new kind of note, a one-off project). `uni-os render` never touches this section.

| I want... | Open |
|---|---|
