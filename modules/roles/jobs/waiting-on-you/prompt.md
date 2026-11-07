# What's waiting on you (job `waiting-on-you`)

Purpose: write one page for {{student.name}}, `waiting-on-you.md` at the vault root, that lists everything waiting on them right now, in the order they can act on it, so that agents ask for {{student.name}}'s attention once a day instead of in many small pings. Then send at most one push that points to the page. You run unattended: ask nothing, change nothing else. You collect and explain; you never decide, fix or route anything yourself (that is the coordinator's work).

## Read first
1. `_agent/agent-start.md` and `_agent/rules.md` (language, reply rules, integrity rules per course).
1. `_agent/coordinator-state.md`: "Open items" (the main source), the side-session table, "Scheduled jobs". Rows whose next-step cell starts with `Waiting on {{student.name}}:` are the coordinator's explicit asks; other rows count only when their text plainly waits on {{student.name}} (a decision, a yes, a physical step, an account or sign-in step, a result only they know).
1. `_agent/roles/README.md`, routing table only: who owns what, so each item can say who acts once {{student.name}} has done their part.
{{#if modules.heartbeat}}
1. `_agent/heartbeat/flags.json` (flags with ids `waiting:*`, `result:*`, `duty:*`, and red flags that only {{student.name}} can resolve) and the open `asks` in `_agent/heartbeat/state.json`.
{{/if}}
{{#if modules.progress}}
1. The current week page (`progress/weeks/week-NN.md` with `status: current`): the "Due this week" rows not done whose deadline is today or tomorrow.
{{/if}}
{{#if modules.inbox-sync}}
1. The last 20 lines of `_agent/logs/inbox-sync-log.md`: `WAITING` forwards older than a day (a message from a cloud session nobody could pass on) and `PARKED` notes older than a day.
{{/if}}
{{#if modules.vault-watch}}
1. `_agent/vault-watch/alerts.md`, lines from the last 3 days: sync conflict copies and unsorted inbox drops (only {{student.name}} can decide which copy wins or where a drop belongs).
{{/if}}
1. Side sessions the roster lists as active: their folder's `HANDOVER.md` or build report, the "Open questions" section only (each question with its proposed default).

Read small parts with targeted reads; never scan the vault recursively. Never open private folders, solution files or mail.

## 0. Should this run do anything?
{{#if modules.vm}}- **Failover marker.** Work out this run's nominal slot (the latest of {{schedule.waiting_on_you}} at or before now) as `YYYY-MM-DD HH:MM`. If `_agent/vm/ran/waiting-on-you.md` exists and its `slot:` line equals that slot, reply one line "Skipped: the host already ran the <slot> slot" and stop.
{{/if}}- **Date and time.** Get the real local time from the system ({{term.timezone}}): `date '+%a %Y-%m-%d %H:%M %z'` (Linux, macOS, Git Bash) or `Get-Date -Format 'ddd yyyy-MM-dd HH:mm zzz'` (Windows PowerShell). Never assume the date. Term week: week 0 starts on {{term.week0_monday}}, week n starts n weeks later.
- Read the existing `waiting-on-you.md` if there is one (its `generated:` time and items), to mark what is new since the last page.

## 1. Collect the items
One item per thing {{student.name}} must do. Merge duplicates (the same decision can appear as a state-page row and a heartbeat flag: one item, both links). Leave out everything an agent can do alone, and everything already done (check the file or the row, a few lines, before you list it). For each item work out:
- **State:** one line, what is true now, with the evidence ("the week page says open; the hand-in closes today 23:59").
- **Steps:** what {{student.name}} does, as numbered micro-steps small enough to do half-awake on a phone or at the laptop ("1. Open the cockpit. 2. Tap Done on LA A7."). For a decision: the options in one line each and "My recommendation: ..." with the reason the state page or the build report gives (never your own new recommendation, never present it as decided). Where the next move belongs to a role once {{student.name}} has answered, end with "Then tell <coordinator or session title>".
- **Time:** an honest estimate ("about 2 min", "about 20 min, at the laptop").
- **Details:** a relative link from the vault root to the file with the full story (the state-page row, the week page, the handover, the flag's file).
- **When:** today (a deadline or appointment today), at the laptop (needs the laptop or a desktop app: sign-ins, installs, files, settings), before a date (a decision or review with a date), or no deadline.

Graded work: state only status and deadline. Never add a hint, a solution step or material for an assessment, and nothing at all about work marked `solo` beyond its deadline.

Stale reminders: if a row or a handover mentions a one-off reminder or timer set earlier for something that is now done or moved, add one item under "Still open, no deadline": "A reminder for <thing> set on <date> may still fire: ignore it, or tell the coordinator to cancel it."

## 2. Write the page
Overwrite `waiting-on-you.md` at the vault root (create it if missing) with exactly this layout; leave out a section that has no item, except the first line of the body:
```markdown
---
type: digest
audience: me
generated: YYYY-MM-DD HH:MM
updated: YYYY-MM-DD
tags: [uni/agent, uni/roles]
---
# What's waiting on you

Written by the job `waiting-on-you` on <Ddd D Mon HH:MM> and rewritten at every run: don't write in this page, tell the coordinator ("{{agent.coordinator_title}}") instead. <N> items, <n> new since the last page. <or: Nothing is waiting on you.>

## Today
### <short title> (new)
- **State:** ...
- **Steps:**
  1. ...
  2. ...
- **Time:** about N min
- **Details:** [<file name>](<relative path>)

## When you're back at the laptop
### ...

## Before <Ddd D Mon>
### ...

## Still open, no deadline
### ...
```
Several "Before <date>" sections are fine, earliest first. Inside a section, the item with the nearest deadline comes first. Mark items that were not on the previous page with "(new)" in their heading. Plain words, short lines, the language and reply rules of `_agent/rules.md`.

## 3. One push, only if it is worth it
{{#if modules.notifications}}Push only when the page has at least one item under "Today", or under a "Before" date within the next two days, or at least one new item under "When you're back at the laptop". Otherwise stay silent: the page is enough, and the coordinator reads it when {{student.name}} asks "what's waiting on me?".

First check, then send:
```
uni-os push --check --source waiting-on-you --id waiting:digest:<YYYY-MM-DD>
uni-os push "Waiting on you: <n> for today, <m> at the laptop, <k> later. Open the page What's waiting on you." --source waiting-on-you --id waiting:digest:<YYYY-MM-DD>{{#if modules.obsidian}} --click "obsidian://open?vault=<the vault folder's name, URL-encoded>&file=waiting-on-you"{{/if}}
```
Counts only, in at most {{notify.max_length}} characters: no item titles, names, file names, scores or links in the text (the lock screen is public). The one id per day means at most one digest push a day, whatever runs again. If the gate holds (exit 10), has no budget (11), dedupes (12) or refuses (13), keep the page and say so in your final reply; never rephrase to get through and never use another channel. `uni-os` is the framework's command line; if it is not a command here, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"` (exported by the job runners), from the vault root.{{else}}No push: the notifications module is off. The page is the record; the coordinator reads it when {{student.name}} asks "what's waiting on me?".{{/if}}

## Idempotency
The page is regenerated from the sources at every run, so a second run (a catch-up after the laptop woke, another host, a manual rerun) only rewrites it; the push id `waiting:digest:<date>` keeps it to one push a day. If the page's `generated:` time is less than 30 minutes old and none of the sources changed since, write nothing and reply "Page is current".

## Failure flag
The contract is in `_agent/heartbeat/README.md` ("Writing a flag from a job"), when the heartbeat module is installed; create `_agent/logs/flags/` if it is missing.
- **Write** `_agent/logs/flags/waiting-on-you.md` when the page could not be written or a main source could not be read (the coordinator state page is unreadable, the write failed): front matter `job: waiting-on-you`, `at: YYYY-MM-DD HH:MM` (local time), `level: amber`; the first body line says in one plain sentence what failed, with no personal details. Overwrite an older flag with the newest text.
- **Delete** that file at the end of every run that wrote the page or found it current.

## Never
- Never edit `_agent/coordinator-state.md`, role briefs, the calendar, the week page or any other file: your only outputs are `waiting-on-you.md` and your own failure flag.
- Never message sessions, never start jobs, never answer an open question yourself.
- Never put passwords, sign-in codes, keys, private calendar addresses or notification topics on the page, even if a source mentions them; write "the sign-in step (details with the coordinator)".
- Never more than one push per run, never an "all good" push, never personal details in a push.
- Graded work: deadlines and status only; `solo` work gets no help in any form.

## Final reply
One line: `waiting-on-you <slot>: <N> items (<n> new); push sent|held|budget|dedupe|refused|not needed|off; flag written|cleared|none`.
