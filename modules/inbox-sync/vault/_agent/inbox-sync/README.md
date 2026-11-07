---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent, inbox]
---
# Inbox sync: the update-note protocol

Some writers can **create** files in the vault but cannot **change** an existing file: cloud agent sessions that reach the vault through a storage connector (the Google Drive connector creates files and edits metadata, but cannot change an existing file's content){{#if modules.cockpit}}, and the cockpit's Done taps{{/if}}. They write an **update note** into `{{paths.inbox}}/` instead. One trusted applier, the job `inbox-sync`, applies the notes to the vault files, files them away and logs every run. It is a create-only write-ahead log with optimistic concurrency: the writer quotes the current text exactly, the applier changes it only if that text is still there.

This is a **fallback**. Sessions that can edit files (laptop sessions, an always-on host) edit the vault directly and never write update notes.

## The three rules
1. **The vault wins.** A writer reads the target file fresh and quotes every line it wants replaced exactly as it stands now. The applier applies a note only if every quoted line is still there, character for character. Otherwise it applies nothing from that note, leaves it in the inbox and logs it as PARKED; the writer re-sends against the current file.
2. **Never merge guesses.** No fuzzy matching, no "close enough", no reconstructing what the writer probably meant.
3. **One applier.** Only the `inbox-sync` job (or an interactive session explicitly running its recipe and logging "(not a job run)") applies notes. Applied notes are moved, never deleted: `_agent/inbox-applied/YYYY-MM/` is the audit trail.

## For writers

### When to write a note
- A change to an existing file (an error-log row, a course-card line, a result, a backlog item, a status cell): **one update note per turn**, in the same turn you learn the fact. Error-log rows go out in the same turn the error shows up.
- A new file (a study page, a hint page): create it directly in its target folder, not through a note, and only if no file of that name exists there. Make the Markdown twin of an HTML page too if you can; otherwise the sync makes it.
- A request for another session (a replan, a block report, a prep gap): a `## For <session title>` section in the same note.
- **Exception: direct file access.** A normally create-only session that has been given real file access for a while (for example a desktop file-access connector to the laptop's vault folder) may edit directly instead of writing a note, but then it works like the applier: back up the file first, re-read it right before editing, keep the edit small, and log the change in `_agent/logs/inbox-sync-log.md` marked `(<session title>, not a job run)`.

### File name
`{{paths.inbox}}/YYYY-MM-DD_HHMM_<sender>-update.md`
- Local time in {{term.timezone}}: convert from UTC first (a writer once stamped notes one hour ahead after a daylight-saving switch).
- `<sender>`: lowercase kebab-case of the sending role and course, e.g. `ad-exercise-help`, `la-lecture-rundown`, `plan-week-page` for a job.
- Two notes in the same minute: add a letter, `..._0935b_<sender>-update.md`.
- Only names ending in `-update.md` are update notes. Everything else in the inbox is the student's own drop and the sync never touches it.

### Storage specifics (Google Drive connector)
- Create the note with the connector's create call, parent = the inbox folder, mime type `text/markdown`, and **turn Google-type conversion off** (`disableConversionToGoogleType: true`). A converted note arrives as a Google Doc stub the applier can't read.
- To find a file, list the folder and filter yourself: title "contains" searches returned non-matching files. An exact title match works.
- Connector reads truncate long files (long PDFs, long decks, long Markdown logs cut in the middle). If the part you need to quote may be cut, download the content instead, or say in the note that you could not read the end.

### Format
```markdown
---
type: inbox-update
from: "<Role title> (<runtime>)"
created: YYYY-MM-DD HH:MM ({{term.timezone}})
tags: [inbox, uni/<course>]
---
# <Role>: update, <Ddd D Mon YYYY HH:MM>

All "replace" lines below are quoted exactly as they stand in the vault now (read HH:MM). Apply a replacement only if the quoted line is still there.
Apply after today's HH:MM note.                       <- only when this note builds on an earlier one
Source: "<the student's words that triggered this, if any>"

## <path/of/target-file.md>

**1. Append this row at the end of the "<table name>" table** (after the row starting with `| <first cells of the current last row>`):

| <date> | <task> | <what went wrong> | <the correct idea> | [derived] |

**2. Append this bullet at the end of the section `## <heading>`:**

- <bullet>

**3. Replace the line**
`<exact current line>`
**with**
`<new line>`

**4. Insert after the line starting with** `<exact start of an existing line>`:

<new line(s)>

Also set `updated:` to YYYY-MM-DD.

## <another/target-file.md>
...

## For <session title>
- <request, with the evidence it needs; "your call how this fits" if it is a suggestion>

## Not changed
- <what you deliberately left alone, and why>
```

Rules for the body:
- One `## <path>` section per target file, path relative to the vault root, exactly as in the vault (spaces and `&` included).
- Number the instructions. Each names its operation (append row, append bullet, replace line, insert after line) and its anchor.
- Quote anchors and replaced lines in backticks, complete and unchanged (markup, trailing spaces and all). Never paraphrase a line you want replaced.
- Appends to append-only logs need only the table or section name; the "after the row starting with" anchor tells the applier where the end was when you read it.
- A note must carry everything needed to apply it: the applier can't read your conversation.
- `## For <session title>` sections are forwarded unchanged, so write them to be read alone. Use the exact session title from `_agent/roles/README.md`.
- `## Not changed` is read, never applied.
- Never put a solution of graded work the integrity rules protect into a note, never secrets (emails, passwords, keys, tokens, private calendar addresses).
- After writing a note that changes something the student is waiting for, say in one line that it waits for the next sync run.

{{#if modules.cockpit}}
### Done-tap notes (written by the cockpit)
When the student taps "Done" on a due item, the cockpit writes a rule-based note. It quotes no row, so it can't go stale.

File name: `YYYY-MM-DD_HHMM_cockpit-done-<item-slug>-update.md` (undo: `cockpit-undo-`).

```markdown
---
type: inbox-update
from: <dashboard name> (Done tap)
created: YYYY-MM-DD HH:MM ({{term.timezone}})
tapped_at: <ISO-8601 UTC>
done_item: "<item text exactly as in the week page>"
---
# Done tap: <item>

Tapped Done on <Ddd D Mon HH:MM>. Apply this before any later undo note for the same item.

## progress/weeks/week-NN.md
Section "Due this week", the row whose Item cell is `<item>`: change only its Status cell. Put `done (<Ddd D Mon HH:MM>, tapped). Before: ` in front of what the cell says now (if it is empty, write just `done (<Ddd D Mon HH:MM>, tapped)`). If the Status cell already starts with `done`, change nothing. Change nothing else. The tap says the item is finished, not how it went, so add no score or result.
```
An undo note has `undo_item:` instead of `done_item:` and says: if the Status cell starts with the tap mark `done (..., tapped)`, restore the text after `Before: ` (or empty it if there is none); otherwise change nothing.

{{/if}}
## For the applier (the `inbox-sync` job)
In this order:
1. Get the date and time in {{term.timezone}}. List `{{paths.inbox}}/` for `*-update.md`. Ignore everything else (`inbox.md`, the student's drops: exports, screenshots, archives). None: stop without logging.
1. Take the notes **oldest first** by the date and time in the file name (letter suffixes after the plain minute){{#if modules.cockpit}}; Done taps by `tapped_at`{{/if}}.
1. **Already applied?** If every change of a note is already in its target (another writer with direct access may have done it), or the log shows this note's parts as applied in an earlier run, don't apply it again: move it and log `ALREADY APPLIED`.
1. **Ordering hint:** a note that says "Apply after <note>" waits while that note is still in the inbox (parked): log `PARKED <note>: waits for <other note>`.
1. **Check every anchor before changing anything.** Every quoted line, every "after the row starting with", every section heading must be found exactly. One missing: apply nothing from this note, leave it, log `PARKED <note>: quoted line not found in <file>`. A later note from the same sender may anchor on text an earlier note of the same run added: that is an exact match, not a guess.
1. **Apply** with small local edits. Re-read each file right before editing (the student and other sessions write too). Keep the properties block; set `updated:` to today. Append-only logs get new lines only. If an append's "after the row" anchor is still there but no longer last (rows were added since), append at the end of the table so the time order holds, and log that choice.
{{#if modules.cockpit}}
1. **Done taps** follow their own rule (only that one item's Status cell on the current week page, the one with `status: current`), oldest `tapped_at` first. Anything else asked in a tap note: park it.
{{/if}}
{{#if modules.progress}}
1. **Results and bonus points** in a note also go to `progress/current-status.md`, the course card's bonus properties (keep the `x / y` format) and the current week page, because the dashboards read those.
{{/if}}
{{#if modules.study-pages}}
1. **A new HTML page without its Markdown twin**: make the twin with `python _agent/tools/html2md.py <page.html>` (module study-pages; it writes `<page>.md` beside the page). If the twin comes out under 1200 characters, delete it (a page that is all JavaScript). The page's row in the course card's "In this folder" table comes from the writer's note, like any other change to an existing file.
{{/if}}
1. **Refuse** a note that is unclear, contradicts the vault, or would put protected graded work (a solution the integrity rules forbid) or a secret into the vault: leave it, log `REFUSED <note>: <reason>`.
{{#if modules.daily-prep}}
1. **Prep notes are never edited.** A note asking to change a file in `semester/prep/` is forwarded to the prep owner (Plan & progress) as a `## For` section would be; the prep jobs write any new revision.
{{/if}}
1. **`## For <session title>` sections:** forward each, unchanged, starting with "Forwarded by inbox sync from `<note file name>`:". In Claude Code: SendMessage to the session (load it with tool search); a headless job without the target in its session list uses the relay rule in `_agent/roles/README.md`. If sending is impossible or fails: apply the rest, leave the note, log `WAITING <note>: could not forward to <session>`; the coordinator or the student forwards it. On later runs, parts the log shows as applied are not applied again.
1. Move each applied note to `_agent/inbox-applied/YYYY-MM/` (the note's own month; create the folder). Never delete a note.
1. A Google-converted stub instead of a Markdown note can't be read: leave it, log `LEFT <file>: converted document, can't be read`.
1. Append **one line per run that did something** to `_agent/logs/inbox-sync-log.md`.

### Log line format
```
- YYYY-MM-DD HH:MM (job inbox-sync, <host>, slot YYYY-MM-DD HH:MM): applied N notes from "<sender>": `<file1>`, `<file2>`. Files changed: `<path>` (<what>; `updated:` YYYY-MM-DD), ... Anchors matched. Forwarded: the `## For <session>` section (<topic>) to "<session title>" (<how>; delivery not confirmed). Notes moved to `_agent/inbox-applied/YYYY-MM/`. Left alone: `{{paths.inbox}}/inbox.md` and <n> drops of the student. Parked: none. Refused: none.
```
Interactive sessions that apply notes or edit for a create-only writer outside the job log here too, marked `(not a job run)` or `(<session title>, not a job run)`, with the choices they made, backups taken and what they skipped. Vocabulary: `PARKED`, `WAITING`, `REFUSED`, `ALREADY APPLIED`, `LEFT`.

### Timing
- Fixed runs at {{schedule.inbox_sync}} are the safety net. The job `inbox-poll` checks the inbox every {{schedule.inbox_poll_every_min}} minutes inside the window {{schedule.inbox_poll_window}} and starts the sync soon after a new note lands, at most once every {{schedule.inbox_poll_min_gap_min}} minutes counting the fixed runs.{{#if modules.cockpit}} Done taps alone don't start a sync: the cockpit hides the item at once, so taps wait for the next run.{{/if}} A parked note never restarts the sync by itself; the fixed runs retry it.
- A note still in the inbox after {{notify.inbox_stale_hours}} hours{{#if modules.cockpit}} ({{notify.inbox_stale_hours_taps}} hours for Done taps){{/if}} counts as **stuck**: an exit code 0 says the sync ran, not that the notes got applied. The poll writes an `OUTCOME inbox:stuck:<slug of the file name>` line into its run log{{#if modules.vm}}, and the always-on host is the one sender that pushes it (its `outcome-checks` job, or the check inside `uni-vm health`){{else}}{{#if modules.notifications}}, and one sender pushes it: the `outcome-checks` job where the laptop runs command jobs, else the heartbeat{{/if}}{{/if}}; the push has the same id everywhere and never the file name, so it arrives once. Typical causes: a parked note nobody re-sent, a `WAITING` forward, or a sync that isn't running at all.
