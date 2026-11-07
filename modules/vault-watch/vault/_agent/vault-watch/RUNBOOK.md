---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent, vault-watch]
---
# Vault watch: runbook

> [!info] Experimental, Windows only
> A small PowerShell script on the laptop, started by Windows Task Scheduler. No agent, no network, no prompts. It diffs file metadata, writes [log.md](log.md) and [alerts.md](alerts.md) here, and shows a Windows toast for the few things someone must act on. Full spec: the framework's `modules/vault-watch/README.md`.

## What runs
- **Task:** Task Scheduler task (default name "Uni OS vault watch"; the exact name is in the "installed" line of [log.md](log.md)), current user, only while logged on. Daily at {{schedule.vault_watch}}, plus at logon (+5 min). Start when available (a slot missed while the laptop slept runs on wake), at most 10 minutes per run, never two runs at once, also on battery.
- **Chain:** `wscript.exe //B //Nologo vault-watch-launcher.vbs` starts `vault-watch.ps1` in a hidden PowerShell window.
- **Where:** the install folder outside the vault (default `%USERPROFILE%\Documents\uni-os\vault-watch\`): the scripts, `vault-watch.local.json` (vault path), `snapshot.json`, `state.json`, `snapshot-sources.json`, `state-sources.json`, `local-log.txt` (only errors and skips).
- **Settings:** `[vault_watch]` and `schedule.vault_watch` in `_agent/uni-os.toml`, read every run from the generated `_agent/uni-os.json`. The expected-files table is [sources-expected.json](sources-expected.json) (this folder).
- **Read-only on the vault** apart from `log.md`, `alerts.md` and `sources-inventory.tsv` in this folder. It never opens a file (metadata only: path, size, modified time), so a streaming cloud drive downloads nothing.

## Notes scope (your and the agents' notes)
- Root files matching `*.md`, `*.canvas`, `*.base`; the folders `me/`, `progress/`, `semester/`, `resources/`, `views/`, `inbox/`, `_agent/`, `_templates/` (recursive).
- In each course folder only the top-level `.md` files plus the note subfolders (defaults; `vault_watch.course_note_subfolders` changes them for all courses):
{{#each courses}}
  - `{{course.folder}}/`: top-level `.md`, `notes/`, `reference/`, `quiz-prep/`{{#if course.watch_note_subfolders}}, and {{course.watch_note_subfolders}}{{/if}}
{{/each}}
- Skipped: names starting with `.`, `node_modules`, `~$*`, `*.tmp`, `desktop.ini`, and churn files that machines rewrite all the time (`_agent/logs/`, `_agent/inbox-applied/`, this folder's own files, `_agent/course-fetch/pending|done/`, the heartbeat state and flags, the always-on host's status pages, `snapshot.json` and ran-markers in `_agent/vm/ran/`, `_agent/uni-os.json`).

## Sources scope (official material)
- In each course folder everything that is NOT a note part: the official subfolders, the handwritten folder, handouts and stubs at the course top level. Plus extra top-level source, app-export and archive folders from the config, and loose non-note files at the vault root.
- **Never listed** (checked before a folder is opened, so not even file names are read): every path in `vault_watch.never_list` (default: any folder called `private`), every glob in `paths.never_open`{{#if paths.never_open}} (now: {{#each paths.never_open}}`{{item}}`{{#unless @last}}, {{/unless}}{{/each}}){{/if}}, and the note app's own data folder (`paths.handwriting_app_data`{{#if paths.handwriting_app_data}}: `{{paths.handwriting_app_data}}`{{/if}}).
- **Area kinds:** normal (new-file alerts); quiet = handwritten folders and app-export folders (new and changed files are logged only; deletions and conflict copies still alert); frozen = archive folders, default `z_archive/` and `archive/` at the vault root (any change = one alert per subfolder per run; course-level archives must be listed in `vault_watch.frozen_dirs`, e.g. `AD/z_archive`).
- **Moves** (a deleted and a new file with the same size and time, or the same name and size) are logged, not alerted. A file that left the sources and appeared in the notes is reported as "moved into the notes".

## Alerts and what to do about them
Each alert fires once (a line in [alerts.md](alerts.md) plus a toast; more than 3 at once become one summary toast). Baselines are silent.

| Alert (starts with) | Meaning | What the agent does |
|---|---|---|
{{#if modules.inbox-sync}}
| `Vault: update note <name> unapplied >24 h` | an inbox update note was not applied: the sync did not run, or it parked the note | read the sync log; if parked, tell the sender's role what to fix; else run the inbox sync job |
{{/if}}
| `Vault: unsorted file in the inbox: <name>` | the user dropped something | sort it per the inbox rules in `_agent/CONVENTIONS.md`; ask if unclear |
| `Vault: sync conflict copy <path>` | the storage sync made a conflict copy | compare with the original, merge the difference into the original, then ask the user before deleting the copy |
| `Vault: file deleted: <path>` | a root or `_agent/` file vanished | check whether it was renamed or moved on purpose; if not, restore it from the storage's trash or version history |
{{#if modules.daily-prep}}
| `Study prep for today/tomorrow missing` | the daily prep note does not exist | run the daily prep job (see `schedule.daily_prep`); never write a prep note by hand outside the job's rules |
{{/if}}
| `Sources: new <course> file <name> in <folder>` | an official file arrived | nothing; if it fills a gap in today's or tomorrow's prep note, tell the planning role{{#if modules.planning}} (Plan & progress){{/if}} once per file |
| `Sources: <course> <label> not in the vault yet` | an expected file has not arrived | {{#if modules.course-files-fetch}}ask the course files fetch role to look for it on the course pages, or {{/if}}tell the user to download it |
| `Sources: reminder: ...` / `... looks too small` | still missing near its deadline / a broken or placeholder upload | as above; for "too small", compare with the course page |
| `Sources: frozen archive <folder> changed` | something touched an archive | check whether it was intended (archiving a replaced file is) |
| `Sources: new top-level folder in the vault: <name> (not watched)` | a folder no scope covers | ask the user: add it to `vault_watch.source_top_dirs` or `ignore_top_dirs`, or move it |
| `Sources: <path> deleted or moved out of the source folders` | official files are add-only | find out who moved it; restore it unless the user moved it on purpose |

## Expected files
[sources-expected.json](sources-expected.json) holds explicit rows and series (one row per weekly sheet, generated from the first release date). The agent fills it from the course-facts skill and the course cards: release weekday, file name pattern, your upload lag as grace days. Example series (fictional): `{"course": "dm", "label": "sheet {nn}", "first_release": "2026-09-17", "count": 13, "grace_days": 4, "pattern": "^exercise_?0*{n}(?!\\d).*\\.pdf$", "confidence": "firm"}`. Change patterns in this file, never in a prompt. Ask the user before changing a pattern beyond an obvious fix; when the user confirms how a course names its files, set that row's `confidence` to `firm`. Rows only for things that land as files in the vault: not LMS quizzes, programming-platform tasks or git hand-ins. After every edit, check it with a dry run (below).

## Log line formats
- Notes: `- YYYY-MM-DD HH:MM | new N, changed M, deleted K | new: <p1>; <p2> | changed: ... | deleted: ...` (at most 20 paths per line in total). First run: `| baseline taken: N files in scope (no alerts)`.
- Sources: `- YYYY-MM-DD HH:MM | sources: new a, changed b, deleted c, moved d | ... | moved: <from> -> <to> | expected missing: <ids> | new top-level folder: <name>`.
- Errors: `| ERROR: <message>` or `| sources: ERROR: <message>` (the sources scope never blocks the notes scope). Skips because the drive is half mounted appear only in `local-log.txt` (notes) or as `sources: skipped, ...`.
- Installs: `| installed: task '<name>', daily <times>, at logon +5 min; script folder <path>`.

## Switches for testing
Run in Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File "<install folder>\vault-watch.ps1" <switch>`
- `-DryRun`: prints the log lines, alerts and the sources scope summary; writes no file, no state, no toast, no push.
- `-Now '2026-10-29 21:30'` (with `-DryRun`): simulate a run time, e.g. to test the evening prep watchdog.
- `-NoToast`: a normal run without toasts. `-NoPush`: a normal run without the phone push. `-TestToast`: one toast, nothing else.

## Limits
- Runs only while the laptop is on and the user is logged in. Toasts show on the laptop only{{#if modules.notifications}}; with `vault_watch.push = true` each run with new alerts also sends one generic push through the push gate (no file names; stale inbox notes and missing prep notes are not counted, because the outcome checks already push those){{/if}}.
- Metadata only: it cannot tell what changed inside a file, only that it changed.
- Re-run `register-task.ps1` after changing the times or the task name. Course and scope changes need no re-install: the script reads `_agent/uni-os.json` on every run.
