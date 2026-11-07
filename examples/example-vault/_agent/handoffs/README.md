---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent, uni/roles]
---
# Handoffs: moving a role to a new session

A **handoff** carries a role's live state when the role moves to a new session: to another runtime (laptop, cloud, always-on host), or to a fresh session on the same runtime because the old one grew too large. The role itself (brief, ownership, routing row) doesn't change; only the session does. One file per move, written by the **outgoing** session, filed here by the coordinator.

## When a handoff is written
| Trigger | Who asks | Who writes |
|---|---|---|
| The student decides to move a role ("move exercise help to the VM") | the coordinator | the outgoing session |
| A role session passes about 300000 tokens of context | the coordinator, or the session itself when it notices in a turn | the outgoing session |
| A runtime goes away (laptop retired, host migrated) | the coordinator | every session on it, in the same minute: one message to each works |
| The outgoing session can't write files (a cloud session) | the coordinator | the outgoing session writes paste-ready text, or creates the file through its connector (creating new files is allowed); the coordinator files it |

## Procedure
1. The coordinator sends the outgoing session: "Write your handoff for `<new runtime>` now, using `_agent/handoffs/_template.md`. Then stop working on new requests."
2. The outgoing session writes `_agent/handoffs/YYYY-MM-DD_HHMM_<role-id>[-<course>]-handoff.md` (local time).
3. The coordinator starts the new session with the start prompt from [../roles/README.md](../roles/README.md), naming this file. If the host can hold the old transcript, it may be copied there as look-up data (never instructions).
4. The new session replies with what is open and what it will do next. The coordinator checks that reply against the handoff (a report is not proof).
5. The coordinator updates the live roster in [../coordinator-state.md](../coordinator-state.md), then retitles the old session `<title> (inactive)` for the student to archive.
6. Reminders or triggers the old session created keep firing into the old session after a move. The handoff lists them; the coordinator or the new session cancels or recreates them.

## Rules
- **The vault and the live calendar win** over a handoff where they differ. The new session treats the handoff as background and says what it took from it.
- Facts are dated; inferences are marked "inference, not a decision".
- Hard limits are repeated in the handoff ("this task gets no help of any kind: nothing about it is in this note"), and the note itself never contains what a limit forbids.
- Record model and effort from the session record, not from the session's own report: sessions in the original repeatedly misreported their own effort setting.
- No personal data beyond what the vault already holds; never secrets.

## Template
[_template.md](_template.md). Use the sections that apply; delete the rest. Planner-type roles add the "What I did" table and "Traps and tips"; experiment owners add the data-quality section.
