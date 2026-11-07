---
description: What changed in the vault since yesterday (from the host's hourly notes history)
argument-hint: "[since, e.g. '3 days ago' or 'yesterday 18:00'; default 24 hours]"
---
Catch @@OWNER@@ up on vault changes. Read-only: change nothing.

1. The time span is: "$ARGUMENTS" (if that is empty, use "24 hours ago"). Run `uni-vm history since '<time span>'` in Bash. It lists, per hourly snapshot, the notes that were added (A), modified (M) or deleted (D). Paths are relative to the vault.
2. Ignore pure bookkeeping (`@@AGENT_DIR@@/vm/`, log files you can sum up in one phrase, `.obsidian/`). For the notes that matter (the progress dashboard, the current week page, course cards, error logs, new study pages, prep notes, the inbox), look at what changed with `git -C ~/vault-history log -p --since='<same span>' -- tree/<path> | head -80`.
3. Reply in at most 10 short lines, grouped by course or area: what is new or changed, and anything that needs @@OWNER@@ (a new deadline, a parked inbox note, a failed check). Say how far back you looked. Follow the reply rules in `@@AGENT_DIR@@/rules.md`.
