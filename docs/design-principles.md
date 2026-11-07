# Design principles

These are the cross-cutting rules behind Uni OS. Each one came out of something that went wrong, or nearly went wrong, in the original system (the author's first-year computer science semester, run by several AI agent sessions over an Obsidian vault on Google Drive; see [how-it-evolved.md](how-it-evolved.md)). Every entry has three parts: the rule, why it exists, and where the framework implements it.

Principles 1 to 21 were distilled from the original system's own files. Principles 22 to 27 are just as visible in the code and were added when the framework was built.

| # | Principle | Main mechanism |
|---|---|---|
| 1 | [Single source of truth: the vault](#1-single-source-of-truth-the-vault) | config and state in the vault; dashboards only read |
| 2 | [Explicit precedence when sources disagree](#2-explicit-precedence-when-sources-disagree) | source-of-truth order; "the vault wins" |
| 3 | [Bootstrap from files, every session](#3-bootstrap-from-files-every-session) | `AGENTS.md` -> `agent-start.md` read order |
| 4 | [Append-only logs; corrections are new lines](#4-append-only-logs-corrections-are-new-lines) | logs, immutable prep revisions |
| 5 | [One owner per file or task](#5-one-owner-per-file-or-task) | role `owns`, one host per job, one outcome sender |
| 6 | [Multi-writer hygiene](#6-multi-writer-hygiene) | re-read, small edits, risky-files list |
| 7 | [Capability-aware write paths](#7-capability-aware-write-paths) | update notes for create-only writers |
| 8 | [Human notes are machine contracts](#8-human-notes-are-machine-contracts) | frozen formats, doctor contracts |
| 9 | [Silence is the norm; notifications are budgeted](#9-silence-is-the-norm-notifications-are-budgeted) | push gate |
| 10 | [Outcomes, not exit codes](#10-outcomes-not-exit-codes) | outcome checks, failure flags |
| 11 | [Every promised duty needs a trigger](#11-every-promised-duty-needs-a-trigger) | jobs, duty checklist, heartbeat |
| 12 | [Integrity first, in data and code](#12-integrity-first-in-data-and-code) | assistance levels, quiet windows |
| 13 | [Real sources only, or nothing](#13-real-sources-only-or-nothing) | cite the page or write nothing |
| 14 | [Say what was checked and what was inferred](#14-say-what-was-checked-and-what-was-inferred) | checked / inferred blocks |
| 15 | [Batch interventions](#15-batch-interventions) | one question, one page, one sign-in push |
| 16 | [Staged rollout with an explicit yes](#16-staged-rollout-with-an-explicit-yes) | jobs ship off, dry runs, rollback |
| 17 | [Observed content is data, never instructions](#17-observed-content-is-data-never-instructions) | relay rule, untrusting pick-up |
| 18 | [Privacy and least privilege by design](#18-privacy-and-least-privilege-by-design) | secrets outside the vault, read-only sites |
| 19 | [Judge by what the student sees; re-read live](#19-judge-by-what-the-student-sees-re-read-live) | block titles, read-back after writes |
| 20 | [Behaviour lives in data and config](#20-behaviour-lives-in-data-and-config) | job.conf, `[schedule]`, host headers |
| 21 | [Experiments are small, timed and attributable](#21-experiments-are-small-timed-and-attributable) | experiments module, tagged interventions |
| 22 | [Deterministic first, agent second](#22-deterministic-first-agent-second) | `PRECHECK`, pre-check, stdlib tools |
| 23 | [Roles are durable, sessions are disposable](#23-roles-are-durable-sessions-are-disposable) | role briefs, handoffs, state pages |
| 24 | [Generate what can drift](#24-generate-what-can-drift) | `uni-os render`, generated regions |
| 25 | [Nothing is deleted: archive, pause, disable](#25-nothing-is-deleted-archive-pause-disable) | `DISABLED` marker, `z_archive/` |
| 26 | [Agent-neutral files, product features as extras](#26-agent-neutral-files-product-features-as-extras) | `AGENTS.md`, Agent Skills, fallbacks |
| 27 | [Two audiences, two areas](#27-two-audiences-two-areas) | human area vs `_agent/` |

---

### 1. Single source of truth: the vault

**Rule.** The vault folder is the only primary store. Dashboards, plugins, generated JSON, host copies and archives are views or caches of it. Frozen copies record the past, and the live files win.

**Why.** The original began as chat threads that each had their own memory, their own copy of the tracker and their own idea of what was true. A project library, the project memory and the vault drifted apart, and frozen exports were mistaken for live files. The dashboard was later built on the explicit rule "no second copy of my data to go stale".

**In the framework.**
- The config lives in the vault (`_agent/uni-os.toml`). `_agent/uni-os.json` is a generated copy that says "do not edit" ([config/schema.md](../config/schema.md)).
- The cockpit parses the notes on every refresh and keeps no second copy of them ([cockpit](../modules/cockpit/README.md)).
- The always-on host holds nothing that can't be rebuilt in 20 minutes, apart from its secrets ([vm](../modules/vm/README.md)).
- Outdated official files go to `z_archive/<course folder>-outdated-YYYY-MM-DD/`, which is never a source for current status ([CONVENTIONS](../modules/core/vault/_agent/CONVENTIONS.md), section 1).

### 2. Explicit precedence when sources disagree

**Rule.** When two sources disagree, a written order decides. What the student says now comes first, then the live vault files (the newest `updated` wins), then official course pages for course facts, then the course-facts skill, and last the archives. A newer rule beats an older one, and the live calendar beats a plan file.

**Why.** Cloud sessions worked on stale copies of files that laptop sessions had already changed. Without an order, every disagreement became a judgment call, and sometimes a silent overwrite.

**In the framework.**
- `CONVENTIONS.md` section 1, "Source of truth, in order".
- The update-note applier changes a line only if the quoted line is still there, and parks the note otherwise ("the vault wins", [inbox-sync](../modules/inbox-sync/README.md)).
- `rules.md` keeps superseded rules with a "(Since <date>: ...)" note, and the newest wins. Integrity rules are the exception: the student's request in the moment never loosens them.
- The resources module's sources registry has its own authority order ([resources](../modules/resources/README.md)).

### 3. Bootstrap from files, every session

**Rule.** Agents carry no trusted memory. Every session reads the start page, the rules and its own brief first, and reads them again after every context compaction.

**Why.** A long session auto-compacted and lost half its history. Coordinator threads degraded with each compaction. The rules changed often, so a session's memory of them was usually out of date.

**In the framework.**
- [`AGENTS.md`](../modules/core/vault/AGENTS.md) sends every agent to [`_agent/agent-start.md`](../modules/core/vault/_agent/agent-start.md): rules first, then the real date and term week, then the state pages.
- Role sessions start from a brief plus a handoff, and the coordinator from its state page ([roles](../modules/roles/README.md)).
- On the always-on host, an optional hook (`brief-nudge`) prints one fixed sentence when the rules or a brief changed ([vm](../modules/vm/README.md#the-re-read-nudge)).

### 4. Append-only logs; corrections are new lines

**Rule.** Logs are appended, never rewritten. A correction is a new row that refers to the old one. A status cell that changes keeps its evidence and its old value.

**Why.** Append-only history meant nobody had to wonder whether an old row had been rewritten. Status cells in the shape "done x/y (<day and time>, screenshot). Before: open" settled later disagreements about who decided what, and when.

**In the framework.**
- The tracker log ([progress](../modules/progress/README.md)), the error logs with their fixed five-column row ([error-logs](../modules/error-logs/README.md)), the heartbeat log and `requests.md`, the inbox-sync log, the TA-websites log and the experiment block logs.
- Prep notes are never edited: a change is a new revision `-r2`, `-r3` ([daily-prep](../modules/daily-prep/README.md)).
- `CONVENTIONS.md` section 7, "Logs: append, don't rewrite".

### 5. One owner per file or task

**Rule.** Every file and every task has one owner. Others send the owner a message instead of fixing things themselves. Watchers flag problems; they don't repair them.

**Why.** Two writers on one file lost edits. A scheduled task enabled on two machines ran twice. The proactive watcher's brief says it bluntly: "the cure is a message to the session that owns the file. Never fix the file yourself."

**In the framework.**
- Role briefs list the files they own (`owns`), and the generated routing table names the owner of each kind of request ([roles](../modules/roles/README.md)).
- A job runs on exactly one machine.
- Two modules producing the same vault path is a render error ([tools/README.md](../tools/README.md)).
- Each outcome problem has exactly one push sender ([notifications](../modules/notifications/README.md#one-sender-per-problem)).
- The heartbeat messages the owning role and never edits ([heartbeat](../modules/heartbeat/README.md)).

### 6. Multi-writer hygiene

**Rule.** Re-read a file right before editing it. Keep edits small and local, keep the front matter, and bump `updated`. Treat the sync layer as last-writer-wins, and watch for conflict copies.

**Why.** Google Drive keeps the last writer's version of a file. Two machines writing inside the sync window lost a change or produced `name (1).md` conflict copies.

**In the framework.**
- `CONVENTIONS.md` section 9 lists the files where a second writer is risky: the rules, the system handbook, the status page, the tracker log, the week pages, the course cards, the error logs, the coordinator's state page and role files, and the heartbeat's state (each only when its module is enabled).
- The vault watcher alerts on conflict copies ([vault-watch](../modules/vault-watch/README.md)).
- Machine-written JSON that dashboards read by file id is written in place ([heartbeat](../modules/heartbeat/README.md)).
- [storage.md](storage.md) covers other sync providers.

### 7. Capability-aware write paths

**Rule.** How an agent writes depends on what its runtime can do. Agents that can edit, edit. Agents that can only create files write new files plus one update note per turn, and a single trusted applier merges them. Never both write directly and send a note.

**Why.** The Google Drive connector could create files but not change an existing file's content. A session that wrote a file directly and also sent an update note for it produced duplicate `(1)` files.

**In the framework.**
- The update-note protocol with exact anchors, parking, `## For <session>` forwarding and an archive ([inbox-sync](../modules/inbox-sync/README.md)).
- The runtime capability table in `_agent/roles/README.md`.
- `CONVENTIONS.md` section 9, "How to reach the vault".
- The cockpit's rule-based Done-tap notes.

### 8. Human notes are machine contracts

**Rule.** Headings, table columns, `x / y` scores and `Ddd D Mon HH:MM` dates in notes are parsed by plugins, watchers and jobs, so their formats are frozen and documented. Study pages exist as an HTML page plus a Markdown twin.

**Why.** "done" or a score anywhere in a Status cell once counted as done, which hid an open bonus task. The fix ("only the start of the cell counts") became part of the format. Dashboards that parsed renamed headings showed nothing at all.

**In the framework.**
- The formats are listed in [file-formats.md](file-formats.md).
- `uni-os doctor` checks them through its contracts (`week-pages`, `course-cards`, `course-property`, `prep-notes`; [architecture.md](architecture.md#doctor)).
- One done-status vocabulary is shared by the progress module, `heartbeat.done_words` and `cockpit.done_words`.
- The study-pages module writes the Markdown twin ([study-pages](../modules/study-pages/README.md)).

### 9. Silence is the norm; notifications are budgeted

**Rule.** No "all good" messages. Every push goes through one gate with a daily budget, a minimum gap, dedupe by a stable problem id, quiet hours and quiet windows around graded work. Grey means unknown, never fine.

**Why.** Routine success messages were explicitly unwanted. Before the gate, health alerts, job failures and the outcome checks each had their own spacing, and one bad afternoon could produce a burst of pushes about a single cause.

**In the framework.**
- `uni-os push` ([`tools/uni_os/pushgate.py`](../tools/uni_os/pushgate.py), [notifications](../modules/notifications/README.md)) refuses pushes without an id, texts that read like "all good", and personal details. It holds pushes in quiet hours and windows and enforces `notify.max_per_day` and `notify.min_gap_hours`.
- The heartbeat brief says "Silence is the normal outcome" and allows at most one push or one question per run ([heartbeat](../modules/heartbeat/README.md)).

### 10. Outcomes, not exit codes

**Rule.** A job that exited 0 is judged by whether its result exists by its deadline.

**Why.** A green job status hid inbox notes that were parked rather than applied, and prep notes that were never written.

**In the framework.**
- Deterministic outcome checks every 15 minutes: `prep:tomorrow-missing`, `prep:today-missing`, `inbox:stuck`, `prep:gap-open` ([notifications](../modules/notifications/README.md#the-outcome-checks-exit-0-is-not-success)).
- Jobs that end without their full result write a failure flag `_agent/logs/flags/<job>.md`, and the heartbeat turns it into `job:<job>:failed` ([architecture.md](architecture.md#the-job-lifecycle)).

### 11. Every promised duty needs a trigger

**Rule.** Sessions act only when spoken to. A duty happens only if a scheduled job, a calendar block the student follows, or an explicit request triggers it. "Do it when you notice it is due" never fires.

**Why.** An audit of the role briefs found 16 promised duties with no trigger at all, among them pages before quizzes, a weekly plan and hand-offs after reviews. A weekly check-in task bound to a session that had already ended never ran, and nobody noticed for weeks.

**In the framework.**
- Every duty in a role brief names its trigger ([roles](../modules/roles/README.md)).
- The heartbeat keeps a duty checklist ([`duties.md`](../modules/heartbeat/vault/_agent/heartbeat/duties.md)) in which every row names its trigger.
- Date-bound duties got their own optional jobs: `quiz-prep`, `lecture-skim`, `deadline-audit`, `waiting-on-you`.
- The handbook's jobs table makes the mapping visible ([`system-handbook.md`](../modules/core/vault/_agent/system-handbook.md)).

### 12. Integrity first, in data and code

**Rule.** Help on graded work follows a per-course, per-assessment policy stored in the config. The default is hints-only; `solo` means no help at all. The policy binds every output, including chat, hint pages, diagrams, prep notes, tools and fetchers. Pushes and runs pause around timed graded work.

**Why.** A patchwork of per-course rules was hard for both the student and the agents to follow. A tired "just tell me" should never end in a worked solution. In one course AI-written code counted as plagiarism. A file fetcher had to refuse a solution file that was only allowed after a date.

**In the framework.**
- `study.assistance_default = "hints-only"`, `courses[].assistance` and `courses[].assessments[].assistance`, resolved most specific first ([exercise-help](../modules/exercise-help/README.md)).
- The integrity table in [`rules.md`](../modules/core/vault/_agent/rules.md).
- Quiet windows in `notify.quiet_windows`, and integrity filters in the daily prep.
- Date guards in the pick-up code ([course-files-fetch](../modules/course-files-fetch/README.md)).
- [academic-integrity.md](academic-integrity.md).

### 13. Real sources only, or nothing

**Rule.** Course content comes from the official script, slides or handouts, with section and page cited. If the source can't be opened, the agent says so and writes nothing. Practice questions say whether they are official, adapted or invented.

**Why.** A lecture rundown built from a predicted weekly plan instead of the real slides cited wrong pages and contained invented items.

**In the framework.**
- The lecture-rundown role and the `lecture-skim` job, which writes nothing without its source ([lecture-rundowns](../modules/lecture-rundowns/README.md)).
- Provenance labels in study pages and quiz prep ([study-pages](../modules/study-pages/README.md), [quiz-coaching](../modules/quiz-coaching/README.md)).
- The course-fact verification method: claims, checks, verdicts ([resources](../modules/resources/README.md)).

### 14. Say what was checked and what was inferred

**Rule.** Mark inferences, give confidence where it matters, and end every audit or handover with a "checked by running it" versus "only inferred" split. A report from another session is not proof.

**Why.** A planner reported calendar edits as done that had never been applied, and the next day ran on stale descriptions. Bonus maxima were often unpublished, and quiz scopes were the coach's reading of vague official lines.

**In the framework.**
- The coordinator checks results itself with small reads before reporting ([coordinator brief](../modules/roles/roles/coordinator.md)).
- Side sessions end with a [`HANDOVER.md`](../modules/roles/vault/_agent/handover/_template/HANDOVER.md) that has an undo table and a checked versus inferred section.
- The course facts skill separates confirmed from predicted facts, and derived bonus maxima carry "(est.)" ([progress](../modules/progress/README.md)).
- The experiment coverage list has a "What I checked and what I inferred" section ([experiments](../modules/experiments/README.md)).

### 15. Batch interventions

**Rule.** During long or unattended work, keep going on sensible defaults and collect every question, click and sign-in into one batch near the end. Irreversible steps wait for that answer. Questions from different roles are de-duplicated.

**Why.** Approval clicks and sign-in requests one at a time interrupted study blocks. A page that gathered everything waiting on the student, with micro-steps and times, replaced a stream of pings.

**In the framework.**
- The working-style rules in `rules.md`.
- The heartbeat asks at most one question a day.
- The check-in asks once, with options.
- The optional `waiting-on-you` job writes one page and sends at most one push a day ([roles](../modules/roles/README.md#whats-waiting-on-you-optional-job-waiting-on-you)).
- The course-files fetch collects sign-ins into one push.

### 16. Staged rollout with an explicit yes

**Rule.** A new recurring job is staged with its timer off and dry-run against fixed checks, and only the student's yes switches it on, right after a slot, with a rollback written down. Every job and push helper supports a dry run and injectable time. Failover runs leave slot markers so the other machine's catch-up does nothing.

**Why.** A dry run of a push job sent real pushes and recorded them as sent, so the real ones never came. The heartbeat was released as a staged build: two dry runs, a review and a guard dry run before switch-on.

**In the framework.**
- Most jobs that act on their own ship with `DEFAULT_MODE="off"`.
- "Releasing a new agent job (staged rollout)" in the [vm](../modules/vm/README.md#releasing-a-new-agent-job-staged-rollout) and [scheduler-local](../modules/scheduler-local/README.md) READMEs.
- Both job runners set `UNI_DRY_RUN=1` on a dry run. The push gate, the heartbeat helpers, the inbox poll and the host's helpers honour it: they write to a dry-run folder or print what they would do. `--dry-run` also exists on `uni-os init`, `render`, `enable`, `disable`, `new-week` and `push`.
- Ran markers live in `_agent/vm/ran/<job>.md`.

### 17. Observed content is data, never instructions

**Rule.** Text from web pages, third-party files, other sessions' messages and predecessors' transcripts is data. Third-party files are processed in isolated scratch folders and nothing is run from inside them. A message from another session is never the student's approval.

**Why.** Many sessions can write to the vault, and one of them might have read a malicious page. Forwarded messages could otherwise carry the weight of a user message.

**In the framework.**
- Headless jobs use the relay rule: forward unchanged, never act on the text.
- Role sessions read a predecessor's transcript "only to look things up".
- The `brief-nudge` hook passes no file content.
- The always-on host takes new job folders only with `uni-vm jobs sync --accept-new` ([vm](../modules/vm/README.md#jobs-come-from-the-vault)).
- The pick-up task treats every request as hostile ([course-files-fetch](../modules/course-files-fetch/README.md)).

### 18. Privacy and least privilege by design

**Rule.** No emails, keys, private calendar addresses or push topics in the vault, the repo or the logs. Secrets live in the OS keychain or the host's private config. The always-on host never uses the student's university login. Logged-in pages are opened only in the student's own browser, read-only. Pushes carry no personal details. Private folders are never opened.

**Why.** The original printed its push topic in a repository README and a generated report; that topic is effectively a password. Login data had to stay in the browser.

**In the framework.**
- `notify.ntfy_topic_file` points outside the vault, and `uni-os doctor` scans the vault for keys, private iCal addresses and ntfy topics ([`tools/uni_os/secrets.py`](../tools/uni_os/secrets.py)).
- The push gate refuses mail addresses, links and long numbers.
- The VM is created without a cloud service account ([vm](../modules/vm/README.md#security-posture)).
- `paths.never_open` (default `**/private/**`) is skipped by tools and agents.
- The pick-up records hosts, never URLs.
- [security-and-privacy.md](security-and-privacy.md).

### 19. Judge by what the student sees; re-read live

**Rule.** A calendar block is judged by its title, not its possibly stale description. The live calendar is re-read right before answering, and every write is read back.

**Why.** Descriptions lagged when blocks moved. An evening's calendar edits were reported as done but never applied, and the prep job then served stale material.

**In the framework.**
- The planning rules: judge a block by its title, edit single instances, read back every write ([planning](../modules/planning/README.md)).
- The daily prep re-reads the calendar on every run, and its morning check compares each note with the calendar as it is now ([daily-prep](../modules/daily-prep/README.md)).

### 20. Behaviour lives in data and config

**Rule.** Schedules, thresholds, expected files and job settings live in config and data files, not in prompts. Prompts are written once, host-neutral, and reused word for word behind a short per-host header. No day or time is hard-coded: every schedule is a config value the student chooses.

**Why.** A hand edit in one copy of a schedule was silently reverted by a later sync from another copy. Laptop prompts ran on the always-on host unchanged, behind a "translate as you go" header, which made the move between machines cheap.

**In the framework.**
- `job.conf` with `SLOTS="{{schedule.daily_prep}}"`, and every schedule in `[schedule]` ([config/schema.md](../config/schema.md#schedule)).
- The host headers [`_agent/jobs/_header.md`](../modules/scheduler-local/vault/_agent/jobs/_header.md) and [`host/agent/job-header.md`](../modules/vm/host/agent/job-header.md).
- The heartbeat thresholds (`[heartbeat]`) and the watcher's expected files (`[vault_watch]`) are config tables.

### 21. Experiments are small, timed and attributable

**Rule.** One change at a time, for a fixed period (two weeks by default), with one simple measure and a review date. Interventions are tagged so their effect can be separated later.

**Why.** "Every week I'm trying to change something, and this is not good. It's very bad for data." Constant changes made it impossible to tell what helped. That led to a frozen plan and to tagging every watcher intervention in the tracker log.

**In the framework.**
- The experiments module: pre-registered measures, a block log with verdict words, a coverage list before the review, freeze rules, `study.experiment_weeks = 2` ([experiments](../modules/experiments/README.md)).
- `uni-os heartbeat tracker` writes intervention lines tagged "heartbeat". The heartbeat starts in safe mode and is evaluated before full mode ([heartbeat](../modules/heartbeat/README.md)).

### 22. Deterministic first, agent second

**Rule.** Work that a script can do is not an agent task. A cheap deterministic check decides whether an expensive agent run is needed at all.

**Why.** A file fetcher wrapped in an agent task became a plain command. Shell pre-checks that skip the agent when there is nothing to do made most scheduled runs free. Hashing the heartbeat's inputs meant most slots ended without an agent start.

**In the framework.**
- `PRECHECK` in `job.conf` (11 of the 13 shipped agent jobs have one): non-zero means "skipped, nothing to do", and no agent starts.
- `uni-os heartbeat precheck` and the rule set in [`tools/uni_os/heartbeat_rules.py`](../tools/uni_os/heartbeat_rules.py).
- The outcome checks, the inbox poll ([`inbox_poll.py`](../modules/inbox-sync/scripts/inbox_poll.py)), the prep-note validator ([`prep_note.py`](../modules/daily-prep/scripts/prep_note.py)) and the vault watcher run without an agent.
- `uni-os` itself is plain standard-library Python.

### 23. Roles are durable, sessions are disposable

**Rule.** A role is a brief, a list of owned files and a routing row. A session is one conversation that hosts it on some runtime. Moving or recycling a role means a handoff file and a fresh session; nothing about the role changes.

**Why.** The roles moved from chat threads to laptop sessions, cloud sessions, an always-on VM and a home server in about ten days. The briefs barely changed. Long-lived sessions also had to be recycled: a fresh coordinator boots from its state page in about 31k tokens, while the old one was re-reading over 550k on every turn.

**In the framework.**
- Role briefs in `_agent/roles/`, the live roster only in `coordinator-state.md`, handoffs in `_agent/handoffs/`, and recycling at `agent.context_refresh_tokens` (default 300000) ([roles](../modules/roles/README.md)).
- Persistent role sessions on the host are resumed from their transcripts ([vm](../modules/vm/README.md#persistent-role-sessions)).

### 24. Generate what can drift

**Rule.** State each fact once. Generate maps, registries, routing tables and Obsidian artefacts from the config instead of maintaining them by hand. Generation must be reproducible and must never destroy the student's edits.

**Why.** After two restructures, the vault's README map, the inbox rules, the canvas, a CSS comment and the graph colour groups all carried stale paths. A "stale lines to fix" list appeared.

**In the framework.**
- `uni-os render` updates untouched files, refreshes only the generated regions (`<!-- uni-os:begin NAME -->` ... `<!-- uni-os:end NAME -->`) of edited files, and skips files with broken markers ([`tools/uni_os/regions.py`](../tools/uni_os/regions.py), [tools/README.md](../tools/README.md#how-installing-works)).
- Rendering is all-or-nothing, and designed to be byte-identical across operating systems (LF line endings, a pinned date; tested on Windows 11 only).
- Obsidian views, CSS, graph groups and the canvas are rendered from the config ([obsidian](../modules/obsidian/README.md)).
- A test keeps the schema, the example config and Alex's config in step with the module defaults.

### 25. Nothing is deleted: archive, pause, disable

**Rule.** Prefer archive, pause and disable over delete. Official files are add-only, and superseded versions are archived with the student's OK. Old schedules are paused and kept for rollback. Disabling a module leaves every file in place.

**Why.** A delete on a mounted cloud drive is a real delete. Official files were re-uploaded with corrections under the same name and still linked from about 20 notes. Every migration needed a rollback path.

**In the framework.**
- `uni-os disable` writes a `DISABLED` marker into the module's job folders and deletes nothing; render never deletes folders ([tools/README.md](../tools/README.md)).
- Outdated official files move to `z_archive/<course folder>-outdated-YYYY-MM-DD/` ([courses](../modules/courses/README.md)).
- Applied update notes move to `_agent/inbox-applied/YYYY-MM/`.
- Agents on the host never delete or rename on the mount, and an hourly git history makes damage cheap to undo ([vm](../modules/vm/README.md#notes-history-and-fast-search)).

### 26. Agent-neutral files, product features as extras

**Rule.** Every essential instruction lives in agent-neutral files. Product-specific features (desktop scheduled tasks, Remote Control, hooks, subagents, cross-session messaging) are optional extras with a documented fallback.

**Why.** The original ran on four different products and runtimes within weeks. Anything that existed only in one product's settings had to be dug out by hand at the next move. The framework is also meant for students who use other agents.

**In the framework.**
- `AGENTS.md` is the entry file, and `CLAUDE.md` only imports it.
- Skills use the open Agent Skills format (`SKILL.md`).
- `agent.headless_command` runs jobs with any CLI.
- Every module README has an "Agents other than Claude Code" section, and [agents.md](agents.md) maps the features. Uni OS has only been tested with Claude Code.

### 27. Two audiences, two areas

**Rule.** Everything outside `_agent/` is written for the student: short, linked, tables over prose. `_agent/` is for agents. The only crossing is a one-line pointer. Facts the student needs never hide in `_agent/`.

**Why.** Mixing agent instructions into human notes made both worse to read.

**In the framework.**
- `CONVENTIONS.md` section 2.
- The collapsed "For AI agents" callout on Home.
- `audience: me` on notes for the student.
- The `waiting-on-you.md` digest sits at the vault root rather than in `_agent/`, because the student must read it ([roles](../modules/roles/README.md)).
