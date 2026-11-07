# Glossary

The terms a newcomer meets in Uni OS, in alphabetical order. Each entry has one or two lines and a link to where the term is defined in full. `uni-os` is short for `python tools/uni_os.py`. Paths like `_agent/...` are inside your vault.

[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [Z](#z)

## A

- **Act mode.** How far the heartbeat may act on its own: `safe` (the default: only messages to the owning role, allowed re-runs and one question) or `full`. Set by `heartbeat.act_mode`. [heartbeat](../modules/heartbeat/README.md#3-the-agent-run-the-standing-brief)
- **Agent.** The AI coding agent you work with ("your agent"). Uni OS has only been tested with Claude Code; [agents.md](agents.md) covers the others.
- **Agent area, agent dir.** `_agent/` in the vault (`paths.agent_dir`): rules, conventions, roles, jobs, skills, logs and state, written for agents. Everything outside it is the human area. [architecture.md](architecture.md#the-vault-two-areas)
- **`AGENTS.md`.** The agent-neutral entry file at the vault root (and in this repo). It sends every agent to `_agent/agent-start.md`. `CLAUDE.md` only imports it. [core](../modules/core/README.md)
- **`agent-start.md`.** The start page every session reads first. It fixes the read order: rules, then the real date and term week, then state, then the course. [core](../modules/core/README.md#how-it-works)
- **Always-on host.** A machine that never sleeps and runs the agent CLI inside the vault: a cloud VM, a Linux box, or WSL2 on a spare laptop (a home server). Optional; provided by module `vm`. [vm](../modules/vm/README.md)
- **Applier.** The one trusted job that applies update notes: `inbox-sync`. [inbox-sync](../modules/inbox-sync/README.md)
- **Ask mode.** How the heartbeat asks its one question a day: `session` (an interactive session on the always-on host), `inline` (the question is the push) or `auto`. [heartbeat](../modules/heartbeat/README.md#3-the-agent-run-the-standing-brief)
- **Assistance level.** How much help an agent may give on a piece of work: `solo` (no help at all), `hints-only` (the default), `coach` or `full`. Set per course and per graded assessment (config key `assistance`, default `study.assistance_default`); the most specific level wins. [exercise-help](../modules/exercise-help/README.md), [academic-integrity.md](academic-integrity.md)

## B

- **Backlog.** `<course folder>/backlog.md`: the course's to-do list of things to catch up on or revisit. [courses](../modules/courses/README.md)
- **Block.** A self-study block in the study-blocks calendar (`calendar.study_blocks`). Its title follows the block notation; its description carries tasks, place, a `FOCUS:` line and the prep job's `MATERIAL` block. [planning](../modules/planning/README.md)
- **Block log.** A per-block table of what was planned and what happened, with verdict words; used during an experiment. [experiments](../modules/experiments/README.md)
- **Block notation.** The terse block-title code: `X_` main subject, `X, Y` order, `(X)` optional, `[X]` reading ahead, `OP` optional personal, `(deep)` a long focus block. It is a default and can be changed. [planning](../modules/planning/README.md#the-default-block-notation)
- **Build report.** A short report written next to a new job before its release: files, how it works, capability probes, tests and open questions. [vm](../modules/vm/README.md#releasing-a-new-agent-job-staged-rollout)
- **Bypass permissions.** An agent permission mode in which nothing asks for approval. Unattended jobs need it (or the highest mode your agent offers), or they stop at the first approval prompt; use it only on machines you trust (`agent.permission_posture`). [runtimes.md](runtimes.md), [security-and-privacy.md](security-and-privacy.md)

## C

- **Catch-up.** A scheduled run that fires late (after the laptop wakes) and does the work of the slot it missed, unless that slot is already done. [scheduler-local](../modules/scheduler-local/README.md#slots-catch-up-and-idempotency)
- **Check-in.** The periodic job (`check-in`, at `schedule.check_in`) that asks you once for the period's results and closes the week page. [check-in](../modules/check-in/README.md)
- **Cloud session.** A hosted agent session (for example a Claude Code cloud session). It works with the laptop off, but needs a git repository, has no bypass mode, can't read laptop files and, through a create-only storage connector, can only create files. [runtimes.md](runtimes.md)
- **Cockpit.** The Obsidian plugin `uni-os-cockpit`: now and next, due this week, bonus standing, the prep card and a week grid, all parsed from your notes. Its only write to your notes is a Done or Undo tap note in the inbox (it may also refresh its calendar snapshot file for agents). [cockpit](../modules/cockpit/README.md)
- **Config.** `_agent/uni-os.toml` in the vault: every parameter, one file, the single source of truth. [config/schema.md](../config/schema.md)
- **Contract.** A parsed format that agents, plugins and jobs rely on (week page headings, the prep-note name, the `course:` property, ...), checked by `uni-os doctor`. [architecture.md](architecture.md#doctor), [file-formats.md](file-formats.md)
- **Coordinator.** The one session that is your single entry point when you run several role sessions. It routes your requests, quotes your words, checks results in the vault and keeps a state page. [roles](../modules/roles/README.md)
- **Coordinator state page.** `_agent/coordinator-state.md`: the coordinator's working memory, with the live roster, open items, scheduled jobs per host and the decisions log. [roles](../modules/roles/README.md)
- **Course card.** `<course folder>/<slug>.md`: facts, weekly rhythm, assessments, bonus scheme, help policy, real sources, lecture log and file index of one course. Front matter `type: course`, `course: <course id>`. [courses](../modules/courses/README.md)
- **Course facts skill.** The skill `course-facts`: what a given week or class covers, the deadline rhythm, bonus rules and where to look things up, generated for your courses. [courses](../modules/courses/README.md)
- **Course id, slug, short, folder.** Four names per course in the config: `id` (`algo`, used in the `course:` property and the `uni/<id>` tag), `slug` (`ad`, used in file names), `short` (`AD`, used in titles), `folder` (`AD`, the vault folder; may contain spaces and `&`). [config/schema.md](../config/schema.md)
- **Coverage list.** In an experiment, a list of which blocks have a logged outcome and which are holes, written before the review. [experiments](../modules/experiments/README.md)
- **Current status.** `progress/current-status.md`: the dashboard page with bonus or grade standing per course, done versus to do, and the next 10 days. [progress](../modules/progress/README.md)

## D

- **Deadline audit.** A read-only comparison of every documented date with the calendar and the study blocks before it. On request, or by the optional job `deadline-audit`. [planning](../modules/planning/README.md)
- **`DEFAULT_MODE`.** A job's state when first installed on a host: `off`, `always` or `failover`. Most jobs that act on their own ship `off`. [architecture.md](architecture.md#job-state-on-a-host)
- **Defaults (layered).** Each module's `[defaults]` in `module.toml`, merged under your config: built-in base, then modules that are not enabled, then enabled modules, then your file. [architecture.md](architecture.md#layered-defaults)
- **Derived course fields.** Values the tools compute for every course (`card`, `error_logs`, `colour_rgb`, `handwritten_dir`, ...). Don't set them. [config/schema.md](../config/schema.md)
- **Digest.** The note type of `waiting-on-you.md`, the page the optional job `waiting-on-you` writes. [roles](../modules/roles/README.md#whats-waiting-on-you-optional-job-waiting-on-you)
- **Direct push.** `uni-os push --direct`: for host health alerts and job failures. Outside the daily budget and quiet hours, queued in quiet windows, never with personal details. [notifications](../modules/notifications/README.md)
- **`DISABLED` marker.** A file that `uni-os disable <module>` writes into each of the module's job folders. Both job runners skip such jobs. Nothing is deleted. [tools/README.md](../tools/README.md)
- **Doctor.** `uni-os doctor`: config validation, module checks, missing or edited files, job.conf checks, contracts and a secrets scan of the vault. [tools/README.md](../tools/README.md)
- **Done tap.** Tapping Done on a due row in the cockpit. It writes a rule-based update note (`..._cockpit-done-<item-slug>-update.md`) that the next inbox sync applies to the week page. [cockpit](../modules/cockpit/README.md), [inbox-sync](../modules/inbox-sync/README.md)
- **Done-status vocabulary.** The words that close a due row when they start its Status cell: `✓`, done, submitted, closed, handed in, uploaded, dropped, skipped, or a score `x/y`. Shared by progress, the heartbeat and the cockpit. [progress](../modules/progress/README.md)
- **Dry run.** A test run that reads for real and changes nothing. For agent jobs it is an instruction (a preamble), not a sandbox; every `uni-os` helper honours `UNI_DRY_RUN=1`. [vm](../modules/vm/README.md#releasing-a-new-agent-job-staged-rollout)
- **Duty checklist.** `_agent/heartbeat/duties.md`: every recurring duty and what triggers it. The heartbeat checks it. [heartbeat](../modules/heartbeat/README.md)

## E

- **Error log.** One append-only mistake ledger per course (`<slug>-error-log.md`), with the row `| Date | Where | What went wrong | Correct idea | Source |` and a "Patterns to watch" list that feeds `me/weak-spots.md`. [error-logs](../modules/error-logs/README.md)
- **Error-log stream.** A course with several kinds of work can have one log per stream (`<slug>-error-log-<stream>.md`), set by `courses[].error_log_streams`. [error-logs](../modules/error-logs/README.md)
- **`EVERY_MIN`.** A job.conf key for a fixed polling interval in minutes (1-59 or whole hours up to 1440), used by cheap check jobs such as `inbox-poll`. [config/schema.md](../config/schema.md#jobconf-schedule-keys-not-config-keys)
- **Exam-phase plan.** `semester/plans/exam-phase-plan.md`: a frame for scheduling study blocks in the exam session once the dates are out. [planning](../modules/planning/README.md)
- **Experiment.** A small, timed test of a change to how you study or live: a hypothesis, pre-registered measures, a block log and a review date. [experiments](../modules/experiments/README.md)

## F

- **Failover.** A host job mode in which the always-on host runs a job only when the laptop's agent app missed the slot, and writes a ran marker. Brittle; mode `always` is simpler. [vm](../modules/vm/README.md#failover-mode-optional)
- **Failure flag.** `_agent/logs/flags/<job>.md`, written by a job that ended without its full result (front matter `job`, `at`, `level`; the first body line is the reason). The next complete run deletes it, and the heartbeat shows it as `job:<job>:failed`. [architecture.md](architecture.md#the-job-lifecycle)
- **Final self-test.** The closing quiz at the end of a study page. [study-pages](../modules/study-pages/README.md)
- **Flags (`flags.json`).** `_agent/heartbeat/flags.json`: what the heartbeat flags right now (red, amber, grey), for dashboards. Grey means unknown, never fine. [heartbeat](../modules/heartbeat/README.md)
- **`FOCUS:` line.** The line in a study block's description that names the block's one focus. The planner writes it; the prep note and the cockpit show it. [planning](../modules/planning/README.md)
- **Folders (`[[folders]]`).** Folders a module declares in `module.toml` whose names come from the config, for example one per official subfolder of each course. Created empty, never deleted. [tools/README.md](../tools/README.md#extending)
- **Framework.** This repository: module templates, the `uni-os` command line and the docs. Your vault is built from it. [architecture.md](architecture.md)

## G

- **Gap.** In a prep note, something a block needs that is not in the vault yet. It is always listed with a fallback. [daily-prep](../modules/daily-prep/README.md)
- **Generated region.** The part of a generated file between `<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->`. `uni-os render` refreshes it even in a file you edited, and keeps everything outside the markers. [tools/README.md](../tools/README.md#how-installing-works)

## H

- **Handoff.** A file in `_agent/handoffs/` that a session writes when its role moves to a new session or machine, or is recycled. [roles](../modules/roles/README.md)
- **Handover.** The folder and `HANDOVER.md` of a one-off side session (`_agent/handover/<topic>/`), with an undo table and a split between what was checked by running it and what was only inferred. [roles](../modules/roles/README.md)
- **Handwritten folder.** `<course folder>/<course folder> handwritten/` (or `courses[].handwritten_folder`): where a tablet app exports PDFs of handwritten notes. Agents read it but never write there. [handwritten-notes](../modules/handwritten-notes/README.md)
- **Headless.** A run nobody can open or answer (`SESSION="print"`). Most jobs run headless, because every new interactive session notifies the phone. [vm](../modules/vm/README.md#the-job-runner)
- **Help level.** An older name for the [assistance level](#a) (config key `assistance`).
- **Heartbeat.** The proactive watcher. A deterministic pre-check decides whether an agent run is worth it; the agent then stays silent, sends one push or asks one question. Jobs `heartbeat`, `heartbeat-weekend`, `heartbeat-watch` (event wake-ups), `heartbeat-ask` (the question session). [heartbeat](../modules/heartbeat/README.md)
- **Hint ladder, hint page.** Hints from smallest to strongest, each opened only after the previous one. A hint page is an HTML page with the ladder behind clicks and never the final answer. [exercise-help](../modules/exercise-help/README.md)
- **Host header.** The text placed in front of every job prompt on a host (`_agent/jobs/_header.md` on the laptop): where the vault is, how to get the time, how the run may talk to you. It lets one prompt run on any host. [scheduler-local](../modules/scheduler-local/README.md#the-portable-host-header-_agentjobs_headermd)

## I

- **Inbox.** `inbox/` (`paths.inbox`): the drop zone for unsorted files and update notes. Keep it near-empty. [core](../modules/core/README.md)
- **`inbox-poll`.** A command job that looks for new update notes every `schedule.inbox_poll_every_min` minutes (default 10) and starts `inbox-sync` soon after one lands: only inside `schedule.inbox_poll_window`, at most once per `schedule.inbox_poll_min_gap_min` (default 60), and never for Done taps alone. [inbox-sync](../modules/inbox-sync/README.md)
- **`inbox-sync`.** The agent job that applies update notes, parks stale ones, forwards `## For <session>` sections, archives notes to `_agent/inbox-applied/YYYY-MM/` and logs every run. [inbox-sync](../modules/inbox-sync/README.md)

## J

- **Job.** A scheduled unit, defined as data: `_agent/jobs/<job>/job.conf` plus `prompt.md` for agent jobs. It runs on exactly one machine. [architecture.md](architecture.md#the-job-lifecycle)
- **`job.conf`.** Shell-style `KEY="value"` lines: `TITLE`, `KIND`, `SLOTS`, `DAYS`, `SESSION`, `PRECHECK`, `RUNTIME`, `DEFAULT_MODE`, ... [vm](../modules/vm/README.md#the-job-runner)

## L

- **Laptop ping.** A Windows task that tells the always-on host the laptop and its agent app are up. Needed only for failover mode. [vm](../modules/vm/README.md#laptop-helpers-windows-experimental-behaviour-spec-for-porting)
- **Lecture skim.** A short intuition-first page written before a lecture. The optional job `lecture-skim` writes skims for the courses in `study.rundowns.skim_courses`. [lecture-rundowns](../modules/lecture-rundowns/README.md)
- **Live roster.** The table in the coordinator state page that says which session hosts which role right now. [roles](../modules/roles/README.md)

## M

- **Manifest.** `_agent/.uni-os-manifest.json`: every installed file with its module, source template and SHA-256, and every created folder. It is how `render` tells your edits from untouched files. [tools/README.md](../tools/README.md#how-installing-works)
- **Markdown twin.** The Markdown copy of an HTML study page, so it reads inside Obsidian. [study-pages](../modules/study-pages/README.md)
- **`MATERIAL` block.** The block the daily prep job appends at the very end of each study block's calendar description, so the links are on your phone too. Only that block is ever replaced. [daily-prep](../modules/daily-prep/README.md)
- **Mistake map.** After a graded hand-in comes back: a table that locates and explains each mistake and leaves the fixes to you. [exercise-help](../modules/exercise-help/README.md)
- **Mode (`always`, `failover`).** Where an always-on host job runs: only on the host (`always`), or on the host only when the laptop missed the slot (`failover`). Stored in `~/.local/state/uni-os/modes/<job>` on the host. [architecture.md](architecture.md#job-state-on-a-host)
- **Module.** An installable feature: `modules/<id>/` with `module.toml`, templates, jobs, roles, skills and its README. 25 ship. [modules/README.md](../modules/README.md)
- **`module.toml`.** A module's manifest: id, tier, dependencies, OS, runtime, config keys, jobs, roles, skills, folders, contracts and `[defaults]`. [architecture.md](architecture.md#the-module-system)

## N

- **Never-open paths.** `paths.never_open` (default `**/private/**`): vault paths that tools and agents never read. [config/schema.md](../config/schema.md)
- **Nominal slot.** The latest scheduled time at or before now. A late or catch-up run belongs to the slot it replaces. [scheduler-local](../modules/scheduler-local/README.md#slots-catch-up-and-idempotency)
- **ntfy.** The default push channel: a free phone app plus an HTTP POST to a secret topic. The topic lives in a file outside the vault. [notifications](../modules/notifications/README.md#set-up-ntfy-5-minutes)

## O

- **Obsidian.** The Markdown editor Uni OS recommends but does not require. Without it, the Bases views, the Home dashboard and the cockpit are hard to get. [obsidian](../modules/obsidian/README.md)
- **Outcome check.** A deterministic check that a job's result exists: "exit 0 is not success". The ids are `prep:tomorrow-missing:<date>`, `prep:today-missing:<date>`, `inbox:stuck:<slug>` and `prep:gap-open:<date>`. [notifications](../modules/notifications/README.md#the-outcome-checks-exit-0-is-not-success)
- **Outcome sender.** The one machine or job that pushes outcome checks in a given setup: the host, the `outcome-checks` job, or the heartbeat. [notifications](../modules/notifications/README.md#one-sender-per-problem)

## P

- **`PARKED`.** An update note whose quoted line is no longer in the vault. Nothing is applied; the writer re-sends against the current file. Related log words: `WAITING`, `REFUSED`, `ALREADY APPLIED`, `LEFT`. [inbox-sync](../modules/inbox-sync/README.md)
- **Personal deadline rule, personal target.** A rule stricter than the official deadlines (`study.personal_deadline_rule`), shown as the "Personal target" column of every "Due this week" table (`study.target_column`). [config/schema.md](../config/schema.md)
- **Pick-up.** The experimental Windows task that files course downloads into the vault only after checking their origin host, type, size, age and target folder. [course-files-fetch](../modules/course-files-fetch/README.md)
- **Plan & progress.** The planner role that owns the week plans, the calendar's study blocks and the progress records. [planning](../modules/planning/README.md)
- **`PRECHECK`.** A shell test in job.conf that runs before the agent. Non-zero means "skipped, nothing to do", and no agent starts. The main cost saver. [vm](../modules/vm/README.md#the-job-runner)
- **Pre-check (heartbeat).** `uni-os heartbeat precheck`: the heartbeat's deterministic rules and input hashes that decide whether its agent runs. [heartbeat](../modules/heartbeat/README.md#1-the-pre-check-rules)
- **Prep note.** `semester/prep/prep-YYYY-MM-DD.md`: everything tomorrow's study blocks need, in one fixed place. Never edited; a change is a new revision `-r2`, `-r3`, and the highest wins. [daily-prep](../modules/daily-prep/README.md)
- **Preset.** A starting set of modules: Minimal, Standard or Full. [setup/presets.md](../setup/presets.md)
- **Push gate.** `uni-os push`: one shared gate for phone pushes, with a daily budget, a minimum gap, dedupe by problem id, quiet hours and quiet windows. It refuses "all good" messages and personal details. [notifications](../modules/notifications/README.md)

## Q

- **Quiet hours.** `notify.quiet_hours` (default `21:00-07:30`): no judgment pushes in this daily window. [notifications](../modules/notifications/README.md)
- **Quiet window.** `notify.quiet_windows`: dated or weekly periods (timed quizzes, orals) in which every push is held and the heartbeat skips runs. A soft window (`urgent_ok = true`) lets urgent pushes through. [notifications](../modules/notifications/README.md#configuration)

## R

- **Ran marker.** `_agent/vm/ran/<job>.md`, written after a failover run so that the laptop's catch-up skips that slot. [scheduler-local](../modules/scheduler-local/README.md#failover-markers-only-with-an-always-on-host)
- **Recap.** A page before a sheet or quiz with exactly the tools you need, each with its page; never the solution. [lecture-rundowns](../modules/lecture-rundowns/README.md)
- **Recycling.** Replacing a long-lived session with a fresh one that boots from its state page or a handoff, once its context passes `agent.context_refresh_tokens` (default 300000). [roles](../modules/roles/README.md)
- **Region.** See generated region.
- **Relay rule.** How a headless job reaches a session it can't see: it asks the host's main session to forward a quoted text unchanged, and the receiver never acts on it. [vm](../modules/vm/README.md#messaging-and-the-relay-rule)
- **Remote Control.** A Claude Code feature that lets you open and continue sessions on another machine (the always-on host) from the phone or the app. Every new session notifies the phone. [runtimes.md](runtimes.md), [vm](../modules/vm/README.md#remote-control-server)
- **Render.** `uni-os render`: apply config or module changes to the vault. It updates untouched files, refreshes generated regions in edited ones, creates new files and folders, and never recreates what you deleted. [tools/README.md](../tools/README.md)
- **Requests (`requests.md`).** `_agent/heartbeat/requests.md`: "stop telling me about X until Friday" lines the heartbeat honours. [heartbeat](../modules/heartbeat/README.md)
- **Role.** A durable job description for an agent session: a brief, the files it owns and a routing row. Shipped roles: `coordinator`, `plan-and-progress`, `lecture-rundown`, `exercise-help`, `quiz-coach`, `course-files-fetch`. [roles](../modules/roles/README.md)
- **Role brief.** `_agent/roles/<role>.md`: purpose, start-up reads, duties each with its trigger, rules, output formats, handoffs and a never-list. [roles](../modules/roles/README.md)
- **Routing table.** Two tables. `CONVENTIONS.md` section 3 maps a kind of fact to the file it belongs in ("you learned X, put it in Y"). `_agent/roles/README.md` maps a kind of request to the role that owns it. Both are generated from the enabled modules. [core](../modules/core/README.md), [roles](../modules/roles/README.md)
- **Rundown.** A page written after a lecture: what was actually covered, with definitions, results and pages. [lecture-rundowns](../modules/lecture-rundowns/README.md)
- **Runtime.** Where sessions and jobs run: `laptop`, `cloud` (hosted sessions) or `vm` (the always-on host). [runtimes.md](runtimes.md)

## S

- **Session.** One disposable agent conversation that hosts a role. [roles](../modules/roles/README.md)
- **`SESSION` (`print`, `rc`).** A job.conf key: `print` runs headless; `rc` opens an interactive Remote Control session you can answer from the phone (only for jobs that must talk to you, such as the check-in). [vm](../modules/vm/README.md#the-job-runner)
- **Session title.** The exact title a role session runs under, e.g. `AD · Exercise help` or `Plan & progress`. Other sessions address it by this title. [roles](../modules/roles/README.md)
- **Side session.** A one-off session for a bounded task (a migration, an overnight review) with its own brief, folder and `HANDOVER.md`. [roles](../modules/roles/README.md)
- **Skill.** An Agent Skills folder (`SKILL.md` with front matter) installed to `_agent/skills/<skill>/` and linked to where your agent reads skills (`agent.skills_dir`). Shipped: `course-facts`, `log-error`, `study-page`, `read-handwritten-notes`. [agents.md](agents.md)
- **Slot.** One scheduled run time of a job, from `SLOTS` (local times rendered from `[schedule]`). [scheduler-local](../modules/scheduler-local/README.md)
- **Snapshot (host).** `_agent/vm/snapshot.json`: the always-on host's machine-readable status, rewritten every 15 minutes, read by the heartbeat. [vm](../modules/vm/README.md)
- **Solo.** The assistance level for work you must do alone: the agent gives no help at all on it and says so in one sentence. See assistance level.
- **Staged rollout.** How a new recurring job is released: build report, staged with its timer off, dry runs judged against fixed checks, switched on with your yes, with a written rollback. [vm](../modules/vm/README.md#releasing-a-new-agent-job-staged-rollout)
- **State folder.** Machine state that must not sync, kept outside the vault: `~/.local/state/uni-os/` on Linux and macOS, `%LOCALAPPDATA%\uni-os\` on Windows (job logs, push-gate state, heartbeat state). [notifications](../modules/notifications/README.md)
- **Status pack.** The cockpit's plain-text summary (today, tomorrow, bonus standing, due this week, next 10 days), copied to the clipboard for any chat app. [cockpit](../modules/cockpit/README.md)
- **Student model.** Four pages in `me/` (profile, learning style, rhythm and habits, weak spots) that tell every agent who you are and how you learn. [student-model](../modules/student-model/README.md)
- **Study page.** A self-contained HTML teaching page with navigation, demos, quizzes checked by code, a cheat sheet and a final self-test, plus a Markdown twin. [study-pages](../modules/study-pages/README.md)
- **System handbook.** `_agent/system-handbook.md`: the setup summary, the registry of enabled modules, the jobs table with schedule keys, where secrets live and the change log. [core](../modules/core/README.md)

## T

- **Tap note.** See Done tap.
- **Template.** Every text file in a module. `{{key}}` values, `{{#each courses}}` loops and `{{#if modules.<id>}}` blocks are filled from the config at render time. [tools/README.md](../tools/README.md#template-language)
- **Term week.** Week *n* of the term starts `term.week0_monday + 7n` days. `uni-os week` prints the current week and phase. [tools/README.md](../tools/README.md)
- **Tier.** A module's place in the catalogue: `core`, `standard`, `advanced` or `addon`. [modules/README.md](../modules/README.md)
- **Tracker log.** `progress/tracker-log.md`: the append-only dated log of results and events. [progress](../modules/progress/README.md)

## U

- **`uni-os`.** The command line, `python tools/uni_os.py` (Python 3.11+, standard library only): `init`, `render`, `enable`, `disable`, `modules`, `doctor`, `week`, `new-week`, `config`, `jobs`, `push`, `heartbeat`. [tools/README.md](../tools/README.md)
- **`uni-os.json`.** The generated machine copy of the config for consumers that can't read TOML (the cockpit). Never edit it. [config/schema.md](../config/schema.md)
- **`uni-vm`.** The control tool on the always-on host: status, jobs, roles, health, doctor, grep, history and more. [vm](../modules/vm/README.md)
- **Update note.** A file `inbox/YYYY-MM-DD_HHMM_<sender>-update.md` that a create-only writer drops to change existing vault files. Each change quotes the current line exactly. [inbox-sync](../modules/inbox-sync/README.md), [file-formats.md](file-formats.md)
- **Usage map.** `modules/roles/scripts/usage_map.py` (Claude Code only): ranks sessions by estimated usage from local transcripts, to show which one to recycle. [roles](../modules/roles/README.md#usage-map-optional-script-claude-code-only)

## V

- **Vault.** Your folder of plain Markdown (an Obsidian vault if you use Obsidian), synced between devices. The single source of truth. [architecture.md](architecture.md)
- **Vault watch.** An experimental, Windows-only script that compares file metadata a few times a day and raises a toast only for things someone must act on. [vault-watch](../modules/vault-watch/README.md)
- **Verdict (performance).** The always-on host's weekly judgment of its memory headroom: enough, tight or upgrade. [vm](../modules/vm/README.md#performance-monitoring-and-the-weekly-verdict)

## W

- **Waiting on you.** The optional job `waiting-on-you`: once a day it writes `waiting-on-you.md` at the vault root with everything that waits on you, and sends at most one push. [roles](../modules/roles/README.md#whats-waiting-on-you-optional-job-waiting-on-you)
- **Weak spots.** `me/weak-spots.md`: the recurring patterns from the error logs, linked to their rows. [student-model](../modules/student-model/README.md)
- **Week 0.** The Monday in `term.week0_monday`; the anchor for every week number.
- **Week page.** `progress/weeks/week-NN.md`: one page per term week with a parsed "Due this week" table (`Item | Official deadline | Personal target | Bonus | Status`), results, notes and the end-of-week check-in. Status `upcoming`, `current` or `done`. [progress](../modules/progress/README.md)
- **Week plan.** `semester/plans/week-NN-plan.md`: the blocks of one week, the "Material per block" the prep job reads, and a ledger of calendar edits. [planning](../modules/planning/README.md)
- **Where to find what.** `where-to-find-what.md` at the vault root: the generated "I want... / Open" table. [core](../modules/core/README.md)

## Z

- **`z_archive/`.** At the vault root: outdated official files move to `z_archive/<course folder>-outdated-YYYY-MM-DD/` with the same name, never deleted, only with your OK. [courses](../modules/courses/README.md)
