---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent, uni/roles]
---
# Coordinator state

The working memory of the **coordinator** session: currently "Uni coordinator" (`<session id, if the app shows one>`), folder `<vault path on the laptop>`, permission mode `<mode>`, model `<model, effort>`. Predecessor: `<title and id of the previous coordinator, and its status: "Old coordinator (inactive)", archived or not>`.

The coordinator keeps this page current whenever something opens, closes or waits on Alex Example, so an automatic context compaction or a fresh coordinator session loses nothing. Role sessions don't use this page. Closed rows move to `_agent/archive/coordinator-state-closed-YYYY-MM.md` after a week.

**A fresh coordinator** (Alex Example starts a new session in the vault folder and says it is the coordinator): read [agent-start.md](agent-start.md), [rules.md](rules.md), this page, [roles/README.md](roles/README.md), [roles/coordinator.md](roles/coordinator.md) and [system-handbook.md](system-handbook.md). Update the identity paragraph above. Role sessions started by the old coordinator report their turn ends to it, not to you: message them directly, and read their recent turns with small limits.

## How the coordinator works (keep the context lean)
- Role sessions and helper agents do the reading and building; the coordinator reads their short reports and checks results with small, targeted reads (a few lines of a file, a short list of a session's recent turns).
- **Delegate as much as possible.** Most requests come here first: route them to the owning role or a side session, and point Alex Example to the session or file instead of doing the work here.
- Avoid tool calls with huge outputs: parse saved output with a script, or hand bulk work to a helper agent.
- Durable facts go into the vault in the same turn (routing, briefs, handbook, this page); the coordinator's own memory only points here.
- A session's report is not proof: check the file or calendar before telling Alex Example something is done.
- **Never message a cloud session**: the message is held for approval in that session and expires. Put the information in the vault where it reads it, or give Alex Example paste-ready text. Messages to sessions in the same permission mode are fine.
- Recycle this session at about 300000 tokens of context: bring this page up to date first.

## Live roster
The one place that says which session hosts which role right now. Old rows are marked "history" (keep them while their transcripts may still be needed), never silently deleted. Address always-on host sessions by title.

| Role | Session title | Runtime | Model, effort | Since | Notes (handoff file, predecessor, idle stop) |
|---|---|---|---|---|---|
| Coordinator | Uni coordinator | laptop | | 2026-11-07 | |

Side sessions (one-off work; each has a folder in [handover/](handover/README.md)):

| Side session (title) | Started | Brief | Status |
|---|---|---|---|

## Open items (newest first)
Rows hold Alex Example's words in quotes, what was sent to whom and when, what was checked and how, deliveries "not confirmed", and dated follow-ups ("coordinator checks at 18:30"). A row that waits on Alex Example starts its next-step cell with `Waiting on Alex Example:` (what they do, about how long, by when): the daily page `waiting-on-you.md` collects exactly those. Typical rows: a request routed to a role; a side session started (title, model, brief, the milestones that come back here); a decision waiting on Alex Example with a recommendation per sub-question; a rule change and what is not possible; the coordinator's own slips.

| Since | Item | Next step / owner |
|---|---|---|
| Sat 7 Nov 2026 | Uni OS set up. "<the student's first request, in their words>" | <route it; record what was checked> |

## Scheduled jobs (where each runs now)
Which host runs which job, in which mode. Never let two hosts run the same job in mode "always": switch one off and the other on right after each other, never around a scheduled time, or a slot runs twice.

| Job | Host | Mode (off / always / failover) | Since | Notes |
|---|---|---|---|---|

## Decisions log
Dated structural decisions, each with who decided and their words.

- Sat 7 Nov 2026: Uni OS installed with the modules listed in `_agent/system-handbook.md` (Alex Example, setup).
