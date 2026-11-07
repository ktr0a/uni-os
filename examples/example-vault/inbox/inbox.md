---
type: inbox
audience: both
updated: 2026-11-07
tags: [uni/inbox]
---
# Inbox

The drop zone for anything not sorted yet: exports from other AI tools or notebook apps, screenshots of grades, pasted chats, quick notes from the phone, a PDF someone sent. Drop it here and an agent sorts it. New notes created in Obsidian and pasted attachments land here too, if the recommended Obsidian settings are on (new notes in `inbox/`, attachments in `inbox/attachments/`).

## What lands here
- **Alex Example's drops:** exports, screenshots, quick notes, files to file away.
- **Update notes from agents that can only create files** (cloud sessions, dashboard "Done" taps): `YYYY-MM-DD_HHMM_<sender>-update.md`. They carry exact edits for existing files. The inbox-sync job applies them, moves them to `_agent/inbox-applied/YYYY-MM/` and logs every run; a note whose quoted lines no longer match stays here as PARKED until its sender re-sends it. Don't apply or delete them by hand unless the sync is down.

## Rules
- Name files `YYYY-MM-DD_short-topic.ext` (e.g. `2026-11-03_quiz-review-screenshot.png`) so the order stays clear.
- Keep it near-empty: anything older than a week should have been sorted.
- Nothing secret goes here either (no passwords, keys or private calendar addresses): the inbox syncs like the rest of the vault.

## How an agent sorts the inbox
Whoever processes the inbox (Alex Example or an interactive agent session; jobs only touch update notes) goes through each item, oldest first:
1. **Read it and decide what it is.** A grade screenshot, a pasted chat, an official file, a note. If it doesn't name its course, match by date, time window and item name, and say that you matched.
1. **Record the facts** in the right file, following the routing table in `_agent/CONVENTIONS.md` section 3: a score goes to the status page and the log, a mistake to the error log, a course fact to the course card, a preference to the student model, a rule to `_agent/rules.md`.
1. **File the item itself** where it belongs, if it is worth keeping: an official file into the course's official subfolder (official name kept, add-only), a study page into the course's `notes/`, a review extract into the course's quiz material. Move notes inside Obsidian so links update.
1. **Remove the inbox copy:** move it to `_agent/archive/inbox-YYYY-MM/` (or delete it if it is a pure duplicate and Alex Example agreed). Never delete their only copy of something without asking.
1. **Say in your reply** what you sorted where, and what you couldn't place (it stays here with a note on what is missing).

Integrity applies here too: if a drop contains Alex Example's own work on graded `solo` tasks, don't summarise or store it; leave it and ask what they want done with it.
