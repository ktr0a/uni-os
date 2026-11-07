# Job: inbox sync (apply update notes)

**Purpose:** apply the update notes that create-only writers leave in `{{paths.inbox}}/`, then file them away. You are the single trusted applier for {{student.name}}'s {{university.short}} {{term.label}} vault. Writers that can create files but not edit them ({{#if runtime.use_cloud_sessions}}cloud agent sessions working through a storage connector, {{/if}}{{#if modules.cockpit}}the cockpit's Done taps, {{/if}}any agent without edit access) describe their changes in these notes with exact anchors. Work only on the vault's notes; official course files and other source folders are not yours (see "Never"). Everything you write is in the language set in `_agent/rules.md`.

You run unattended. Ask nothing. Silence is the norm: no "all good" messages; the log is the record.

## Read first
1. `_agent/agent-start.md`, `_agent/rules.md` (non-negotiable, including the integrity rules per course) and `_agent/CONVENTIONS.md` (where each kind of information goes, the properties block every note needs, append-only logs).
2. `_agent/inbox-sync/README.md`: the update-note protocol. Its "For the applier" section is the full rule set for this job; this prompt repeats the essentials.
3. The last 10 lines of `_agent/logs/inbox-sync-log.md` (what earlier runs applied, parked or left waiting).
{{#if modules.daily-prep}}
4. The daily-prep contract `semester/prep/README.md`: prep notes are written only by the prep jobs and never edited, moved or deleted by anyone else.
{{/if}}

## Steps
1. **Date, time, slot.** Get the current date and time in {{term.timezone}} with a command (never assume them). This run's slot is the latest of {{schedule.inbox_sync}} at or before now, as `YYYY-MM-DD HH:MM`; if you were started by the inbox poll between slots, the slot is "poll HH:MM".
2. **List the inbox.** List `{{paths.inbox}}/` for update notes: Markdown files named `YYYY-MM-DD_HHMM_<sender>-update.md` (accept any other `*-update.md` too). Ignore `inbox.md` and everything else the student dropped there (exports, screenshots, archives, quick notes): those are for the student or an interactive session. **If there are no update notes, append nothing to the log, do step 6 and stop** with the final line `Nothing to do`.
3. **For each update note, oldest first** (by the date and time in its name; a letter suffix comes after the plain minute{{#if modules.cockpit}}; Done taps by their `tapped_at`{{/if}}):
   - **Read it completely.** It names each target file and gives the exact lines to append, insert or replace.
   - **Already applied?** If its changes are already in the targets (a writer with direct access may have made them), or the log shows this note's parts applied in an earlier run (a note left `WAITING` for a forward), don't apply them twice. File the note away and log it as `ALREADY APPLIED` (or apply only the parts that are missing and say which).
   - **Ordering hint.** If it says "Apply after <note>" and that note is still in the inbox, leave this one too and log `PARKED <note>: waits for <other note>`.
   - **The vault wins: check every anchor before you change anything.** Every quoted line to replace, every "after the row starting with", every named section must be in the target file exactly as quoted. If one is missing (the file changed after the note was written), apply nothing from that note, leave it in `{{paths.inbox}}/` and log `PARKED <note>: quoted line not found in <file>`. Don't guess and don't merge. The sender re-sends it against the current file. Exception: a later note from the same sender in this run may anchor on text an earlier note of this run added; that is an exact match.
   - **Apply** with small, local edits. Re-read each file right before editing (the student may have it open in an editor, and other sessions write too). Keep each file's properties block at the top and set `updated:` to today (YYYY-MM-DD). Append-only logs (the tracker log, the course error logs, any file `_agent/CONVENTIONS.md` marks append-only) only get new lines; never rewrite an old one. If an append's "after the row" anchor is still there but rows were added after it since, append at the end of the table so the time order holds, and log that choice.
{{#if modules.cockpit}}
   - **Done taps:** a note with a `done_item` or `undo_item` property is a Done tap. Apply its own rule instead of parking it, but only to set that one item's Status cell in the "Due this week" table of the current week page (`progress/weeks/week-NN.md` with `status: current`). If it asks for anything else, park it. Apply taps oldest `tapped_at` first.
{{/if}}
{{#if modules.progress}}
   - **Results and bonus points** go into all four places of `_agent/progress-tracking.md` section 1, also the ones the note doesn't name, because the dashboards read them: `progress/current-status.md` (the course's "Bonus standing" row, its detail table, "Exercises: done vs. to do" and the snapshot line), one dated line in `progress/tracker-log.md` (source: the note's sender), the course card's properties `bonus_banked` / `bonus_target` / `next_bonus` (keep the `x / y` number-pair format), and the week page of the week the item belongs to (its Status cell in "Due this week" plus one line under "Results this week"). Use exactly what the note says; never compute or guess a score.
{{else}}
{{#if modules.courses}}
   - **Results and bonus points** go into the course card's properties `bonus_banked` / `bonus_target` / `next_bonus` (keep the `x / y` number-pair format), exactly as the note says; never compute or guess a score. This vault has no progress module, so there is no status page, tracker log or week page to update.
{{/if}}
{{/if}}
{{#if modules.study-pages}}
   - **New HTML page without a Markdown twin:** if a note refers to a new HTML page in a course folder (`notes/`, `quiz-prep/`) that has no `.md` twin beside it, make the twin: `python _agent/tools/html2md.py "<page.html>"{{#if obsidian.enabled}} --obsidian{{else}} --plain{{/if}}` (it writes `<page>.md` beside the page; module study-pages{{#unless obsidian.enabled}}; plain Markdown, because this vault is read without Obsidian{{/unless}}). If the twin is shorter than 1200 characters, delete it (the page is JavaScript only).
{{/if}}
   - **Refuse** a note that is unclear, contradicts what the vault already says, or would put into the vault a solution the integrity rules forbid (work marked `solo`, a finished solution of graded `hints-only` work) or a secret. Don't apply it; leave it in `{{paths.inbox}}/` and log `REFUSED <note>: <reason>`.
{{#if modules.daily-prep}}
   - **Prep notes:** if a note asks to change a prep note in `semester/prep/`, do NOT edit it. Forward the request to the prep owner (Plan & progress) like a `## For` section (next bullet), log it, and file the note; the prep jobs write any new revision.
{{/if}}
   - **`## For <session title>` sections:** forward each one, unchanged, to that session. Start the message with `Forwarded by inbox sync from <note file name>:` and paste the section text exactly. In Claude Code: load SendMessage with tool search (`select:SendMessage`) and address the session by the exact title from `_agent/roles/README.md` (or the live roster in `_agent/coordinator-state.md`); if the session isn't in your session list, use the relay rule in `_agent/roles/README.md` ("Relay request: please forward ..."). Apply the note's other parts as usual. If sending is unavailable or fails, leave the note in `{{paths.inbox}}/`, log `WAITING <note>: could not forward to <session>`, and continue; the coordinator or the student forwards it.
   - **`## Not changed`:** read it, apply nothing from it.
   - Never write email addresses, passwords, API keys, tokens or private calendar addresses into any file.
   - **File the note:** move it to `_agent/inbox-applied/YYYY-MM/` (the note's own year and month; create the folder if needed). Never delete a note.
4. **Converted documents:** if a writer created a Google-converted document instead of a Markdown file (a stub you can't read), leave it and note it in the log (`LEFT <file>`).
5. **Log:** append one line for this run to `_agent/logs/inbox-sync-log.md` (create it with a heading if it is missing), in exactly this shape:
   `- YYYY-MM-DD HH:MM (job inbox-sync, <host>, slot <slot>): applied N notes from "<sender>": ` + the note names + `. Files changed: ` + each path with what changed and its `updated:` + `. Anchors matched.` + forwards (section, topic, target, "delivery not confirmed" unless confirmed) + `. Notes moved to _agent/inbox-applied/YYYY-MM/. Left alone: ` + the student's drops + `. ` + `Parked: ...` / `Refused: ...` / `Waiting: ...` or `Nothing skipped or parked.`

6. **Clear your failure flag.** If `_agent/logs/flags/inbox-sync.md` exists and this run could list the inbox and did every step it needed, delete that file (it is yours: an earlier run wrote it, see "Failure behaviour"). A run that stopped at step 2 with `Nothing to do` also clears it.

## Outputs
- Edited vault notes (small, local edits; properties block kept; `updated:` bumped).
- Applied notes moved to `_agent/inbox-applied/YYYY-MM/`.
- One line in `_agent/logs/inbox-sync-log.md` per run that did something.
- Forwarded `## For` sections (messages), nothing else.

## Idempotency
- A note is applied once: the "already applied" check and the log protect against a second run (another host, a catch-up run after the laptop woke, a rerun after a failed forward).
- If the log already has a line for this slot from another host and the inbox has no notes newer than that line, stop with `Skipped: slot already done`.

## Failure behaviour
- Can't list or read the inbox: append one log line `- <time> (job inbox-sync, <host>): inbox not readable: <error>`, write the failure flag below with `level: red`, and stop. Don't retry in a loop; the next run tries again.
- A tool you need doesn't exist on this host (file moves, session messaging): skip just that step, say so in the log line, write the failure flag with `level: amber`, and carry on.
- **Failure flag** (how a job says "ended, but the result is incomplete"; an exit code of 0 can't say it): write `_agent/logs/flags/inbox-sync.md`, replacing any older one, in exactly this shape:
  ```markdown
  ---
  job: inbox-sync
  at: YYYY-MM-DD HH:MM
  level: red
  ---
  inbox not readable on <host>; no notes applied
  ```
  The first body line is one plain sentence: what failed and what is left undone, no note contents and no personal details. {{#if modules.heartbeat}}The heartbeat's pre-check turns it into the finding `job:inbox-sync:failed`.{{else}}Dashboards and the next session read it there.{{/if}} The next run that succeeds deletes it (step 6). Parked, refused or `WAITING` notes are not failures: the log line and the stuck-note check cover them.
- Never send a push or a message other than the forwards: alerts about notes stuck too long come from the deterministic outcome checks, not from you.

## Never
- Never edit, move, rename or delete official course files or source folders: the official subfolders of each course folder (listed on each course card), handwritten-notes folders, Google stubs, official handouts, archives. Never touch the private folders `_agent/rules.md` names.
{{#if modules.daily-prep}}
- Never move, rename, merge, edit, archive or delete anything in `semester/prep/`: dashboards read it in place, and only the prep jobs write it.
{{/if}}
- Never touch `.obsidian/`, plugin sources, `_agent/archive/`, or files other jobs own (their logs and state), unless a note explicitly asks and the owner is that note's sender.
- Don't restructure, rename or delete vault notes; don't edit the calendar or anything outside the vault.
- Never apply a replacement whose quoted line isn't there exactly. Never merge guesses.

## Final report
One line: `inbox-sync <slot>: applied N, parked P, refused R, waiting W, left L` (or `Nothing to do`).
