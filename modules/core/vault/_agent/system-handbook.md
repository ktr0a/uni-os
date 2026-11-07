---
type: agent
audience: both
updated: {{generated.date}}
tags: [uni/agent]
---
# System handbook: every part of this study system and where it is defined

The component registry of {{student.name}}'s Uni OS setup: what each part does, which vault file defines it, and where and when it runs. The rule behind it: **every definition lives as a file in this vault.** Nothing may exist only inside a hosted project's settings, an agent's memory, a scheduled task's prompt box or someone's head. If a part is defined elsewhere (an app setting, a scheduled task), its row says where, and the vault file stays the source.

Companion files: [../where-to-find-what.md](../where-to-find-what.md) (map of the vault), [CONVENTIONS.md](CONVENTIONS.md) (where facts go), [rules.md](rules.md) (standing rules){{#if modules.roles}}, [roles/README.md](roles/README.md) (roles and routing){{/if}}. Config: `_agent/uni-os.toml` (the single source of all settings; `uni-os.json` beside it is a generated copy).

## 1. This setup
<!-- uni-os:begin setup -->
| Item | Value |
|---|---|
| Student | {{student.name}}{{#if student.handle}} (handle `{{student.handle}}`){{/if}}, {{university.programme}}, {{university.name}} |
| Term | {{term.label}}, week 0 = Mon {{term.week0_monday}}, timezone {{term.timezone}} |
| Framework | Uni OS {{generated.version}}, rendered {{generated.date}} |
| Enabled modules | {{modules.enabled}} |
| Primary agent | {{agent.primary}} (tested: Claude Code only), permission posture `{{agent.permission_posture}}` |
| Storage | {{storage.provider}} |
| Laptop OS | {{runtime.laptop_os}} |
| Always-on host | {{#if modules.vm}}yes (module `vm`){{else}}no: everything runs on the laptop while it is awake and the agent app is open{{/if}} |
| Cloud sessions | {{#if runtime.use_cloud_sessions}}yes (see CONVENTIONS section 9){{else}}not used{{/if}} |
<!-- uni-os:end setup -->

<!-- uni-os:begin registry -->
<!-- Generated from the enabled modules; `uni-os render` keeps it current (see CONVENTIONS.md, "Generated regions"). Add components of your own in section 5. -->
## 2. Components and where each is defined
| Component (module) | What it does | Defined in (vault) | Runs where, when |
|---|---|---|---|
| Agent entry and start order (core) | Points every agent to the read order and the write-back duty | `AGENTS.md`, `CLAUDE.md`, `_agent/agent-start.md` | every session, at start |
| Standing rules (core) | Reply style, precision, study-material format, academic integrity per course, calendar, working style | `_agent/rules.md` | every session, at start and after every compaction |
| Update conventions (core) | Routing table ("you learned X, put it in Y"), writing rules, logs, how each runtime reaches the vault | `_agent/CONVENTIONS.md` | every session, before writing |
| Component registry (core) | This page | `_agent/system-handbook.md` | read when something changes |
| Tool lore (core) | Connector quirks, gotchas, platform notes | `_agent/tools-and-environment.md` | read as needed; appended when something is learned |
| Inbox (core) | One drop zone for unsorted items; the agent sorts it | `inbox/inbox.md` | sorted by the next interactive session{{#if modules.inbox-sync}} (update notes by the inbox-sync job){{/if}} |
| Templates (core and others) | Lecture note, study page, inbox note; other modules add theirs (e.g. week page, week plan, rundowns, quiz review) | `_templates/` | copied when a note is created |
| Dashboard and maps (core) | Home page, vault map, lookup table | `Home.md`, `README.md`, `where-to-find-what.md` | re-rendered by `uni-os render` when modules change |
{{#if modules.obsidian}}
| Obsidian views (obsidian) | Bases views, CSS snippet with course colours, graph groups, bookmarks, vault map canvas | `views/`, `.obsidian/snippets/uni-os.css`, `_agent/obsidian/` | inside Obsidian |
{{/if}}
{{#if modules.student-model}}
| Student model (student-model) | Who {{student.name}} is, how they learn, their rhythm, their recurring mistakes | `me/` | read before any advice or plan; written by whoever hears a change |
{{/if}}
{{#if modules.experiments}}
| Experiments (experiments) | One-change-at-a-time study or habit experiments with a measure and a review date | `me/habits-experiments.md` | the session that owns the experiment |
{{/if}}
{{#if modules.courses}}
| Courses (courses) | One folder per course: course card, backlog, notes, reference, official files; the course-facts skill | `<Course>/`, `courses-overview.md`, `_agent/skills/course-facts/` | edited by whoever learns a course fact |
{{/if}}
{{#if modules.resources}}
| Resources (resources) | Links registry, assistant/TA websites log, course-fact verification | `resources/` | appended when something is found |
{{/if}}
{{#if modules.handwritten-notes}}
| Handwritten notes (handwritten-notes) | A tablet app exports PDFs into each course's handwritten folder; agents read them with the `read-handwritten-notes` skill and never write there | `_agent/handwritten-notes.md` (folder contract), `_agent/skills/read-handwritten-notes/`, the handwritten folders (`<Course>/<Course> handwritten/` by default) | the app writes; agents read only |
{{/if}}
{{#if modules.error-logs}}
| Error logs (error-logs) | One append-only mistake ledger per course and stream, with a "Patterns to watch" section | `<Course>/<c>-error-log*.md` | exercise help and quiz coaching append rows |
{{/if}}
{{#if modules.study-pages}}
| Study pages (study-pages) | The study-page standard and formats ({{study.formats}}), the HTML-to-Markdown converter | `<Course>/notes/` | made on request by course sessions |
{{/if}}
{{#if modules.lecture-rundowns}}
| Lecture rundowns (lecture-rundowns) | Skims before, rundowns and recaps after lectures, from real sources only | `_agent/roles/lecture-rundown.md` | role session(s), on request{{#if modules.daily-prep}} or when the prep asks for a skim{{/if}} |
{{/if}}
{{#if modules.exercise-help}}
| Exercise help (exercise-help) | Help on sheets at each course's assistance level (default `{{study.assistance_default}}`; per course in `_agent/rules.md`), error log always current | `_agent/roles/exercise-help.md` | role session(s), on request |
{{/if}}
{{#if modules.quiz-coaching}}
| Quiz coaching (quiz-coaching) | Prep and review for weekly graded quizzes | `_agent/roles/quiz-coach.md`, `<Course>/quiz-prep/` | role session, before and after each quiz |
{{/if}}
{{#if modules.progress}}
| Progress (progress) | Status dashboard, append-only tracker log, week pages, bonus and grade tracking | `progress/`, `_templates/week-page.md` | updated by whoever learns a result |
{{/if}}
{{#if modules.planning}}
| Planning (planning) | Term dates, planning system and block notation, week plans, exam-phase scheduling | `semester/` | planning role, on request and at the start of each week |
{{/if}}
{{#if modules.check-in}}
| Check-in (check-in) | Periodic check-in and the next week's page | `_agent/jobs/check-in/`, `_agent/jobs/week-page/` | job `check-in` {{schedule.check_in.day}} {{schedule.check_in.time}} (every {{schedule.check_in.every}}); job `week-page` {{schedule.week_page.day}} {{schedule.week_page.time}}; on the laptop{{#if modules.vm}} or the VM{{/if}} (where it is switched on: section 3) |
{{/if}}
{{#if modules.daily-prep}}
| Daily study prep (daily-prep) | A prep note for the next day's study blocks, and a morning check | `semester/prep/`, `_agent/jobs/daily-study-prep/`, `_agent/jobs/study-prep-morning-check/` | job `daily-study-prep` at {{schedule.daily_prep}}; job `study-prep-morning-check` at {{schedule.prep_check}}; on the laptop{{#if modules.vm}} or the VM{{/if}} (where it is switched on: section 3) |
{{/if}}
{{#if modules.roles}}
| Roles and coordinator (roles) | Durable role briefs, one coordinator session that routes requests and checks results | `_agent/roles/`, `_agent/coordinator-state.md`, `_agent/handoffs/`, `_agent/handover/` | coordinator and role sessions{{#if modules.vm}} (persistent ones on the VM){{/if}} |
{{/if}}
{{#if modules.inbox-sync}}
| Inbox sync (inbox-sync) | Applies update notes from create-only writers; parks stale ones; archives applied ones | `_agent/jobs/inbox-sync/`, `_agent/inbox-applied/`, `_agent/logs/inbox-sync-log.md` | job `inbox-sync` at {{schedule.inbox_sync}} (skips when no note waits); on the laptop{{#if modules.vm}} or the VM{{/if}} (where it is switched on: section 3) |
{{/if}}
{{#if modules.scheduler-local}}
| Local scheduler (scheduler-local) | Runs jobs on the laptop: the agent app's scheduled tasks or the OS scheduler with a headless agent CLI | `_agent/jobs/*/` | the laptop, only while it is awake (desktop-app tasks only while the app is open) |
{{/if}}
{{#if modules.heartbeat}}
| Heartbeat (heartbeat) | Proactive watcher: a cheap deterministic pre-check decides whether the agent runs; at most one push or one question | `_agent/heartbeat/`, `_agent/jobs/heartbeat/` | job `heartbeat` at {{schedule.heartbeat}} on {{schedule.heartbeat_days}}; on the laptop{{#if modules.vm}} or the VM{{/if}} (where it is switched on: section 3) |
{{/if}}
{{#if modules.notifications}}
| Notifications (notifications) | Phone pushes through one gate (daily budget, gaps, quiet hours, dedupe, never "all good") | config `[notify]`; the topic lives in a secret file outside the vault | wherever a job runs |
{{/if}}
{{#if modules.vault-watch}}
| Vault watch (vault-watch) | Watches notes for drift and source folders for new official files; local alerts | `_agent/vault-watch/RUNBOOK.md`, `_agent/vault-watch/sources-expected.json` | the laptop's OS scheduler (Windows, experimental) |
{{/if}}
{{#if modules.course-files-fetch}}
| Course files fetch (course-files-fetch) | Fetches official files from the LMS through the student's logged-in browser; add-only pick-up | `_agent/roles/course-files-fetch.md`, `_agent/course-fetch/RUNBOOK.md` | on demand, through the laptop's browser |
{{/if}}
{{#if modules.vm}}
| Always-on host (vm) | Runs jobs and persistent role sessions around the clock; health checks; vault history | `_agent/vm/` | the VM (a cloud VM or a home server) |
{{/if}}
{{#if modules.cockpit}}
| Cockpit (cockpit) | Obsidian plugin: study dashboard read live from the vault and calendar feeds | `_agent/uni-os.json` (course registry), plugin settings | Obsidian on the laptop; keys only in Obsidian's keychain |
{{/if}}

## 3. Scheduled jobs
Each job is defined by `_agent/jobs/<job>/job.conf` (schedule, kind, limits) and `prompt.md` (the full unattended prompt). Times are local ({{term.timezone}}) and come from the config; change them in `_agent/uni-os.toml`, re-render, then re-install the job on its host.

| Job | Module | When (config key) | Can run on |
|---|---|---|---|
{{#if modules.daily-prep}}
| `daily-study-prep` | daily-prep | {{schedule.daily_prep}} (`schedule.daily_prep`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
| `study-prep-morning-check` | daily-prep | {{schedule.prep_check}} (`schedule.prep_check`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.check-in}}
| `check-in` | check-in | {{schedule.check_in.day}} {{schedule.check_in.time}}, every {{schedule.check_in.every}} (`schedule.check_in`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
| `week-page` | check-in | {{schedule.week_page.day}} {{schedule.week_page.time}} (`schedule.week_page`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.inbox-sync}}
| `inbox-sync` | inbox-sync | {{schedule.inbox_sync}} as a safety net, plus whenever `inbox-poll` finds a note (`schedule.inbox_sync`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
| `inbox-poll` | inbox-sync | every {{schedule.inbox_poll_every_min}} min within {{schedule.inbox_poll_window}}; a cheap check that starts `inbox-sync` only when a note waits | {{#if modules.vm}}VM, or the laptop's OS scheduler{{else}}the laptop's OS scheduler only (`runtime.laptop_scheduler = "os"`){{/if}}; never a desktop-app task |
{{/if}}
{{#if modules.heartbeat}}
| `heartbeat` | heartbeat | {{schedule.heartbeat}} on {{schedule.heartbeat_days}} (`schedule.heartbeat`); a deterministic pre-check decides whether the agent runs | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
| `heartbeat-weekend` | heartbeat | {{schedule.heartbeat_weekend}} on {{schedule.heartbeat_weekend_days}} (`schedule.heartbeat_weekend`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
| `heartbeat-watch`, `heartbeat-ask` | heartbeat | event check every few minutes; a question session started only when the heartbeat has one | VM only (see their `job.conf`) |
{{/if}}
{{#if modules.notifications}}
| `outcome-checks` | notifications | every 15 min: checks that each job's artefact exists by its deadline ("exit 0 is not success") | {{#if modules.vm}}VM, or the laptop's OS scheduler{{else}}the laptop's OS scheduler only (`runtime.laptop_scheduler = "os"`){{/if}}; never a desktop-app task |
{{/if}}
{{#if modules.lecture-rundowns}}
| `lecture-skim` (optional, off when installed) | lecture-rundowns | {{schedule.lecture_skim}} on {{schedule.lecture_skim_days}} (`schedule.lecture_skim`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.quiz-coaching}}
| `quiz-prep` (optional, off when installed) | quiz-coaching | {{schedule.quiz_prep}} on the dates in `schedule.quiz_prep_dates` ({{#if schedule.quiz_prep_dates}}{{schedule.quiz_prep_dates}}{{else}}none set: never runs{{/if}}) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.planning}}
| `deadline-audit` (optional, off when installed) | planning | {{#if term.last_lecture_day}}{{schedule.day_start}} on {{term.last_lecture_day}}{{else}}only when started by hand{{/if}} (`term.last_lecture_day`, `schedule.day_start`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.roles}}
| `waiting-on-you` (optional, off when installed) | roles | {{schedule.waiting_on_you}} on {{schedule.waiting_on_you_days}} (`schedule.waiting_on_you`) | {{#if modules.vm}}laptop or VM{{else}}laptop{{/if}} |
{{/if}}
{{#if modules.vm}}
| `vm-health`, `vault-history`, `vm-performance-verdict` | vm | host health every few minutes, an hourly git snapshot of the notes, a weekly sizing verdict (see their `job.conf`) | VM only |
{{/if}}
| (any other job) | | see its `job.conf` | see its `job.conf` (`KIND`, `RUNTIME`) |

"Can run on" is what each job is built for, not where it is switched on: jobs arrive switched off or staged and are installed on a host one at a time. Agent jobs run as desktop-app scheduled tasks or through the OS scheduler; command jobs (`KIND="command"`) never run as desktop-app tasks. The live on/off state of a job is kept by its host{{#if modules.vm}} (VM: `uni-vm jobs on|off <job>` switches the job's timer; its mode, `always` or `failover`, is the file `~/.local/state/uni-os/modes/<job>` on the host, set with `uni-vm jobs mode`){{/if}}, and where each job is switched on now is written in {{#if modules.roles}}the "Scheduled jobs" table of [coordinator-state.md](coordinator-state.md){{else}}section 4b below{{/if}}, outside this generated table (which render overwrites). A job's `DEFAULT_MODE` is only its state when installed (many start `off` until {{student.name}} says yes). A job that is installed nowhere silently never runs: when you move, install or pause a job, update {{#if modules.roles}}that Scheduled jobs table{{else}}section 4b{{/if}} and the change log. Run each job on one host only (a second copy elsewhere may only run in failover mode, see section 7).

## 4. Roles
{{#if modules.roles}}
The roles, their owners and their triggers are listed in [roles/README.md](roles/README.md) (generated routing table) and the briefs in `roles/`. A role never relies on "noticing" a due duty: every duty names its trigger (a job, a message from {{student.name}}, or another role).
{{else}}
No role system is installed (module `roles`): interactive sessions do everything on request.
{{/if}}
<!-- uni-os:end registry -->
{{#unless modules.roles}}

## 4b. Where each job is switched on now
Kept by hand (render never touches it): one row per job that is installed somewhere, updated whenever a job is installed, moved, paused or removed. A job without a row is installed nowhere and never runs.

| Job | Host (laptop app task / laptop OS scheduler{{#if modules.vm}} / VM{{/if}}) | Mode (off / always / failover) | Since | Notes |
|---|---|---|---|---|
{{/unless}}

## 5. Components added in this vault
Parts that {{student.name}} or an agent added outside the Uni OS modules (a one-off reminder, a custom script, an extra calendar). One row each; keep it current.

| Component | What it does | Defined in | Runs where, when |
|---|---|---|---|

## 6. Accounts, connectors and where secrets live
- Storage: {{storage.provider}}. Course platform: {{university.lms}}.{{#if modules.planning}} Calendar: {{calendar.provider}}.{{/if}}{{#if modules.notifications}} Notifications: {{notify.provider}}.{{/if}}
- Connectors in use (agent app integrations, e.g. storage, calendar, documents): list them here when you add one, with what they can and cannot do (see `tools-and-environment.md`).
- **Secrets never live in the vault.** API keys, private calendar (iCal) addresses, notification topics and tokens stay in the operating system's keychain, the app that uses them, or a secret file outside the vault{{#if modules.notifications}} (e.g. `{{notify.ntfy_topic_file}}`){{/if}}. This page may name *where* a secret is, never the secret.

## 7. Moving parts between runtimes (checklist)
When a part moves (laptop to always-on host, cloud session to laptop, or back), go in this order, so nothing runs twice and nothing is lost:
1. **Entry point:** the session that coordinates points at `_agent/agent-start.md`.
1. **State files:** one live copy only; stop writing the old one.
1. **Watchers** (anything that reacts to new files).
1. **Recurring jobs:** start the new copy in a "failover" mode first (runs only if the old one missed its slot), then make it primary; **pause** the old copy, don't delete it, and write the rollback steps down before switching.
1. **One-off reminders:** let them run out or recreate them.
1. **Notifications:** decide which host may push.
1. **Fix stale lines** in this page, `agent-start.md`, `README.md` and the routing tables.
1. **Copy gaps:** compare the old store with the vault (names and sizes, contents where needed); export what is missing into a dated folder in `_agent/archive/`; keep the old store until its last reminder has run.

## 8. Change log
Append-only, newest last: `- Ddd D Mon YYYY: <what changed> (<who>; <{{student.name}}'s words if a decision>)`. A catch-up from another store is logged as `- Ddd D Mon YYYY HH:MM: full sync from <store> (compared <what>)`; the newest such line is the watermark for the next catch-up (CONVENTIONS section 9).
- {{generated.date_long}}: Uni OS {{generated.version}} set up with modules: {{modules.enabled}}.
