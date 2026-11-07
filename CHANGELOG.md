# Changelog

All notable changes to Uni OS are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-07

The first public version. It generalises my private study system, built for the first year of BSc Computer Science at ETH Zurich (autumn semester 2026), into a framework any student can set up with an AI agent. It was developed with Claude Code and tested only with it. The Windows laptop automation is experimental, and a complete setup on a fresh machine has not been run end to end yet.

### Added

- **Agent-led setup.** `AGENTS.md` is the agent entry point (with `CLAUDE.md` as a thin Claude Code import). `setup/` holds the playbook, the interview, the presets (Minimal, Standard, Full + VM), a no-agent fallback, the after-setup guide and the guide for changing modules later.
- **`uni-os` command line** (`python tools/uni_os.py`, Python 3.11+, standard library only). Commands:
  - `init`, `render`, `enable` and `disable` create and change a vault;
  - `modules`, `doctor`, `week`, `new-week`, `config` and `jobs` inspect and check it;
  - `push` and `heartbeat` serve the notifications and heartbeat modules.
- **Template engine.** Strict Handlebars-like templates with per-course and per-error-log-stream path expansion, all-or-nothing rendering, and byte-identical output across runs, with LF line endings and a pinned date so that it holds across operating systems (tested on Windows only).
- **Layered config.** Base defaults, then module defaults, then the student's file; per-course defaults and derived fields (among them `term.weeks`, one row per teaching week, which fills the generated term-week table); validation with suggestions, and a note for settings of modules that are not enabled. A JSON copy for the cockpit.
- **Manifest with SHA-256 hashes.** `render` updates only files nobody edited. In edited files it refreshes only the generated regions between `<!-- uni-os:begin NAME -->` and `<!-- uni-os:end NAME -->` markers, and skips files with broken markers. It never recreates deleted files or folders. A file that can't be written is reported on its own line while everything else is written and recorded.
- **`[[folders]]` in `module.toml`** for folders named by the config, such as one folder per official subfolder of each course and one handwritten folder per course.
- **`doctor`.** Config validation, module dependencies, missing and edited files, stale skill copies, `job.conf` checks, format contracts (week pages, course cards, the `course` property, prep notes, generated regions, unrendered placeholders, declarative `[[contracts]]`) and a redacted secrets scan of the vault.
- **25 modules**, each with its own README:
  - Foundation: `core`, `student-model`, `courses`, `error-logs`.
  - Study engine: `study-pages`, `exercise-help`, `lecture-rundowns`, `quiz-coaching`, `handwritten-notes`, `resources`.
  - Organisation layer: `progress`, `planning`, `check-in`, `daily-prep`, `heartbeat`, `experiments`.
  - Agents and automation: `roles`, `scheduler-local`, `notifications`, `inbox-sync`.
  - Obsidian: `obsidian` (views and styling) and `cockpit` (dashboard plugin).
  - Add-ons: `vault-watch` and `course-files-fetch` (Windows laptop scripts, experimental) and `vm` (always-on host: Ubuntu on Google Cloud, any Linux box, or WSL2 on a spare laptop).
- **18 jobs** as data in the vault (`job.conf` plus `prompt.md`). They run as desktop-app scheduled tasks, through an experimental OS-scheduler runner, or as systemd timers on the always-on host. Agent job prompts write in the student's language and keep the headings, columns and dates that tools parse fixed. Optional agent jobs ship switched off and go live through a staged rollout.
- **6 role briefs.** `coordinator`, `plan-and-progress`, `lecture-rundown`, `exercise-help`, `quiz-coach` and `course-files-fetch`, with a generated routing table (one Exercise help session per course and error-log stream), messaging rules, handoffs and handovers.
- **4 skills** in the Agent Skills format: `course-facts`, `log-error`, `study-page` and `read-handwritten-notes`.
- **Study output formats.** Study pages as an HTML and Markdown twin, Markdown only, HTML only or PDF. The Markdown twin uses Obsidian callouts or plain `<details>` blocks, following `obsidian.enabled`.
- **Push gate** (`uni-os push`). A daily budget, a minimum gap, dedupe, quiet hours and quiet windows; it refuses "all good" messages and personal details. With a broken vault config it falls back to its cached settings, and it never sends without its lock. Outcome checks look for results instead of exit codes, with one outcome sender per setup.
- **Heartbeat.** A deterministic pre-check in Python decides whether an agent run is worth it; the agent then stays silent, sends one push or asks one question. A pre-check that hits an internal error fails open: the run goes ahead and a failure flag says why.
- **Cockpit.** An Obsidian plugin in TypeScript: now and next, due this week, bonus bars from a small rule engine, the daily prep card, a week grid, live iCal calendars, Done taps through the inbox, and an optional assistant panel on the student's own API key. The built `dist/` is committed.
- **Academic integrity.** An assistance level per course and per graded assessment (`solo`, `hints-only`, `coach`, `full`; default `hints-only`), read by every role, job and the cockpit's assistant.
- **Example config.** `examples/alex.toml` for the fictional student Alex Example at the Example Institute of Technology, plus `config/uni-os.example.toml` and `config/schema.md` covering every key, and the rendered `examples/example-vault`.
- **Documentation.** `docs/` covers architecture, the history of my own system, design principles, lessons learned, agent compatibility, runtimes, storage, porting to other operating systems, security and privacy, academic integrity, file formats, a glossary and an FAQ.
- **Tests.** 390 unit tests for the tools and the catalogue; 111 tests in nine Python module suites; 199 plain-bash checks for the host scripts; 80 PowerShell checks for `vault-watch` and the course-file pick-up; 109 checks in eight cockpit test files.

### Security

- Secrets (API keys, tokens, private calendar addresses, the ntfy topic) are refused in the config and kept out of the vault. The config holds only paths to secret files, and `doctor` scans the vault for leaks.
- The password step always stays with the student; logged-in course sites are read-only.
- The documented always-on host allows no public SSH, the Google Cloud VM gets no cloud identity, and the job runner unsets API-key variables so jobs use the subscription login.

[Unreleased]: https://github.com/ktr0a/uni-os/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ktr0a/uni-os/releases/tag/v0.1.0
