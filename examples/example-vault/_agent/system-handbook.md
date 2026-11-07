---
type: agent
audience: both
updated: 2026-11-07
tags: [uni/agent]
---
# System handbook: every part of this study system and where it is defined

The component registry of Alex Example's Uni OS setup: what each part does, which vault file defines it, and where and when it runs. The rule behind it: **every definition lives as a file in this vault.** Nothing may exist only inside a hosted project's settings, an agent's memory, a scheduled task's prompt box or someone's head. If a part is defined elsewhere (an app setting, a scheduled task), its row says where, and the vault file stays the source.

Companion files: [../where-to-find-what.md](../where-to-find-what.md) (map of the vault), [CONVENTIONS.md](CONVENTIONS.md) (where facts go), [rules.md](rules.md) (standing rules), [roles/README.md](roles/README.md) (roles and routing). Config: `_agent/uni-os.toml` (the single source of all settings; `uni-os.json` beside it is a generated copy).

## 1. This setup
<!-- uni-os:begin setup -->
| Item | Value |
|---|---|
| Student | Alex Example (handle `alex`), BSc Computer Science, Example Institute of Technology |
| Term | Autumn 2026, week 0 = Mon 2026-09-14, timezone Europe/Zurich |
| Framework | Uni OS 0.1.0, rendered 2026-11-07 |
| Enabled modules | core, student-model, courses, error-logs, study-pages, exercise-help, obsidian, progress, planning, check-in, daily-prep, lecture-rundowns, quiz-coaching, roles, scheduler-local, notifications, heartbeat, resources, handwritten-notes, cockpit, inbox-sync, experiments |
| Primary agent | claude-code (tested: Claude Code only), permission posture `bypass` |
| Storage | google-drive |
| Laptop OS | windows |
| Always-on host | no: everything runs on the laptop while it is awake and the agent app is open |
| Cloud sessions | not used |
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
| Inbox (core) | One drop zone for unsorted items; the agent sorts it | `inbox/inbox.md` | sorted by the next interactive session (update notes by the inbox-sync job) |
| Templates (core and others) | Lecture note, study page, inbox note; other modules add theirs (e.g. week page, week plan, rundowns, quiz review) | `_templates/` | copied when a note is created |
| Dashboard and maps (core) | Home page, vault map, lookup table | `Home.md`, `README.md`, `where-to-find-what.md` | re-rendered by `uni-os render` when modules change |
| Obsidian views (obsidian) | Bases views, CSS snippet with course colours, graph groups, bookmarks, vault map canvas | `views/`, `.obsidian/snippets/uni-os.css`, `_agent/obsidian/` | inside Obsidian |
| Student model (student-model) | Who Alex Example is, how they learn, their rhythm, their recurring mistakes | `me/` | read before any advice or plan; written by whoever hears a change |
| Experiments (experiments) | One-change-at-a-time study or habit experiments with a measure and a review date | `me/habits-experiments.md` | the session that owns the experiment |
| Courses (courses) | One folder per course: course card, backlog, notes, reference, official files; the course-facts skill | `<Course>/`, `courses-overview.md`, `_agent/skills/course-facts/` | edited by whoever learns a course fact |
| Resources (resources) | Links registry, assistant/TA websites log, course-fact verification | `resources/` | appended when something is found |
| Handwritten notes (handwritten-notes) | A tablet app exports PDFs into each course's handwritten folder; agents read them with the `read-handwritten-notes` skill and never write there | `_agent/handwritten-notes.md` (folder contract), `_agent/skills/read-handwritten-notes/`, the handwritten folders (`<Course>/<Course> handwritten/` by default) | the app writes; agents read only |
| Error logs (error-logs) | One append-only mistake ledger per course and stream, with a "Patterns to watch" section | `<Course>/<c>-error-log*.md` | exercise help and quiz coaching append rows |
| Study pages (study-pages) | The study-page standard and formats (html, md), the HTML-to-Markdown converter | `<Course>/notes/` | made on request by course sessions |
| Lecture rundowns (lecture-rundowns) | Skims before, rundowns and recaps after lectures, from real sources only | `_agent/roles/lecture-rundown.md` | role session(s), on request or when the prep asks for a skim |
| Exercise help (exercise-help) | Help on sheets at each course's assistance level (default `hints-only`; per course in `_agent/rules.md`), error log always current | `_agent/roles/exercise-help.md` | role session(s), on request |
| Quiz coaching (quiz-coaching) | Prep and review for weekly graded quizzes | `_agent/roles/quiz-coach.md`, `<Course>/quiz-prep/` | role session, before and after each quiz |
| Progress (progress) | Status dashboard, append-only tracker log, week pages, bonus and grade tracking | `progress/`, `_templates/week-page.md` | updated by whoever learns a result |
| Planning (planning) | Term dates, planning system and block notation, week plans, exam-phase scheduling | `semester/` | planning role, on request and at the start of each week |
| Check-in (check-in) | Periodic check-in and the next week's page | `_agent/jobs/check-in/`, `_agent/jobs/week-page/` | job `check-in` Sat 19:45 (every week); job `week-page` Sun 10:00; on the laptop (where it is switched on: section 3) |
| Daily study prep (daily-prep) | A prep note for the next day's study blocks, and a morning check | `semester/prep/`, `_agent/jobs/daily-study-prep/`, `_agent/jobs/study-prep-morning-check/` | job `daily-study-prep` at 17:30, 19:30; job `study-prep-morning-check` at 07:30; on the laptop (where it is switched on: section 3) |
| Roles and coordinator (roles) | Durable role briefs, one coordinator session that routes requests and checks results | `_agent/roles/`, `_agent/coordinator-state.md`, `_agent/handoffs/`, `_agent/handover/` | coordinator and role sessions |
| Inbox sync (inbox-sync) | Applies update notes from create-only writers; parks stale ones; archives applied ones | `_agent/jobs/inbox-sync/`, `_agent/inbox-applied/`, `_agent/logs/inbox-sync-log.md` | job `inbox-sync` at 07:15, 13:15, 18:15 (skips when no note waits); on the laptop (where it is switched on: section 3) |
| Local scheduler (scheduler-local) | Runs jobs on the laptop: the agent app's scheduled tasks or the OS scheduler with a headless agent CLI | `_agent/jobs/*/` | the laptop, only while it is awake (desktop-app tasks only while the app is open) |
| Heartbeat (heartbeat) | Proactive watcher: a cheap deterministic pre-check decides whether the agent runs; at most one push or one question | `_agent/heartbeat/`, `_agent/jobs/heartbeat/` | job `heartbeat` at 07:50, 13:05, 18:05 on Mon, Tue, Wed, Thu, Fri; on the laptop (where it is switched on: section 3) |
| Notifications (notifications) | Phone pushes through one gate (daily budget, gaps, quiet hours, dedupe, never "all good") | config `[notify]`; the topic lives in a secret file outside the vault | wherever a job runs |
| Cockpit (cockpit) | Obsidian plugin: study dashboard read live from the vault and calendar feeds | `_agent/uni-os.json` (course registry), plugin settings | Obsidian on the laptop; keys only in Obsidian's keychain |

## 3. Scheduled jobs
Each job is defined by `_agent/jobs/<job>/job.conf` (schedule, kind, limits) and `prompt.md` (the full unattended prompt). Times are local (Europe/Zurich) and come from the config; change them in `_agent/uni-os.toml`, re-render, then re-install the job on its host.

| Job | Module | When (config key) | Can run on |
|---|---|---|---|
| `daily-study-prep` | daily-prep | 17:30, 19:30 (`schedule.daily_prep`) | laptop |
| `study-prep-morning-check` | daily-prep | 07:30 (`schedule.prep_check`) | laptop |
| `check-in` | check-in | Sat 19:45, every week (`schedule.check_in`) | laptop |
| `week-page` | check-in | Sun 10:00 (`schedule.week_page`) | laptop |
| `inbox-sync` | inbox-sync | 07:15, 13:15, 18:15 as a safety net, plus whenever `inbox-poll` finds a note (`schedule.inbox_sync`) | laptop |
| `inbox-poll` | inbox-sync | every 10 min within 07:00-22:00; a cheap check that starts `inbox-sync` only when a note waits | the laptop's OS scheduler only (`runtime.laptop_scheduler = "os"`); never a desktop-app task |
| `heartbeat` | heartbeat | 07:50, 13:05, 18:05 on Mon, Tue, Wed, Thu, Fri (`schedule.heartbeat`); a deterministic pre-check decides whether the agent runs | laptop |
| `heartbeat-weekend` | heartbeat | 09:00, 17:40 on Sun (`schedule.heartbeat_weekend`) | laptop |
| `heartbeat-watch`, `heartbeat-ask` | heartbeat | event check every few minutes; a question session started only when the heartbeat has one | VM only (see their `job.conf`) |
| `outcome-checks` | notifications | every 15 min: checks that each job's artefact exists by its deadline ("exit 0 is not success") | the laptop's OS scheduler only (`runtime.laptop_scheduler = "os"`); never a desktop-app task |
| `lecture-skim` (optional, off when installed) | lecture-rundowns | 19:00 on Sun, Tue (`schedule.lecture_skim`) | laptop |
| `quiz-prep` (optional, off when installed) | quiz-coaching | 09:00 on the dates in `schedule.quiz_prep_dates` (none set: never runs) | laptop |
| `deadline-audit` (optional, off when installed) | planning | 08:00 on 2026-12-18 (`term.last_lecture_day`, `schedule.day_start`) | laptop |
| `waiting-on-you` (optional, off when installed) | roles | 19:00 on Mon, Tue, Wed, Thu, Fri, Sat, Sun (`schedule.waiting_on_you`) | laptop |
| (any other job) | | see its `job.conf` | see its `job.conf` (`KIND`, `RUNTIME`) |

"Can run on" is what each job is built for, not where it is switched on: jobs arrive switched off or staged and are installed on a host one at a time. Agent jobs run as desktop-app scheduled tasks or through the OS scheduler; command jobs (`KIND="command"`) never run as desktop-app tasks. The live on/off state of a job is kept by its host, and where each job is switched on now is written in the "Scheduled jobs" table of [coordinator-state.md](coordinator-state.md), outside this generated table (which render overwrites). A job's `DEFAULT_MODE` is only its state when installed (many start `off` until Alex Example says yes). A job that is installed nowhere silently never runs: when you move, install or pause a job, update that Scheduled jobs table and the change log. Run each job on one host only (a second copy elsewhere may only run in failover mode, see section 7).

## 4. Roles
The roles, their owners and their triggers are listed in [roles/README.md](roles/README.md) (generated routing table) and the briefs in `roles/`. A role never relies on "noticing" a due duty: every duty names its trigger (a job, a message from Alex Example, or another role).
<!-- uni-os:end registry -->

## 5. Components added in this vault
Parts that Alex Example or an agent added outside the Uni OS modules (a one-off reminder, a custom script, an extra calendar). One row each; keep it current.

| Component | What it does | Defined in | Runs where, when |
|---|---|---|---|

## 6. Accounts, connectors and where secrets live
- Storage: google-drive. Course platform: Moodle. Calendar: google. Notifications: ntfy.
- Connectors in use (agent app integrations, e.g. storage, calendar, documents): list them here when you add one, with what they can and cannot do (see `tools-and-environment.md`).
- **Secrets never live in the vault.** API keys, private calendar (iCal) addresses, notification topics and tokens stay in the operating system's keychain, the app that uses them, or a secret file outside the vault (e.g. `~/.config/uni-os/ntfy-topic`). This page may name *where* a secret is, never the secret.

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
Append-only, newest last: `- Ddd D Mon YYYY: <what changed> (<who>; <Alex Example's words if a decision>)`. A catch-up from another store is logged as `- Ddd D Mon YYYY HH:MM: full sync from <store> (compared <what>)`; the newest such line is the watermark for the next catch-up (CONVENTIONS section 9).
- Sat 7 Nov 2026: Uni OS 0.1.0 set up with modules: core, student-model, courses, error-logs, study-pages, exercise-help, obsidian, progress, planning, check-in, daily-prep, lecture-rundowns, quiz-coaching, roles, scheduler-local, notifications, heartbeat, resources, handwritten-notes, cockpit, inbox-sync, experiments.
