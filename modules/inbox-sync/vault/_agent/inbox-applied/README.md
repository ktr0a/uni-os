---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent, inbox]
---
# Applied update notes (archive)

The job `inbox-sync` moves every update note it has applied (or found already applied) from `{{paths.inbox}}/` into a month folder here, `YYYY-MM/`, named by the note's own date. Nothing here is ever edited or deleted: together with `_agent/logs/inbox-sync-log.md` it is the audit trail of every change a create-only writer made. Notes that were parked, refused or are waiting for a forward stay in `{{paths.inbox}}/` until they are resolved.
