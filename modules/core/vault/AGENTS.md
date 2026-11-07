---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Agent entry point

This folder is {{student.name}}'s university vault ({{university.short}}, {{term.label}}), set up with Uni OS. It is the **primary store** for everything about their studies, and every agent works from it: interactive sessions, role sessions, scheduled jobs and cloud sessions alike.

**Start at [_agent/agent-start.md](_agent/agent-start.md)** and follow its read order: the rules first ([_agent/rules.md](_agent/rules.md), non-negotiable), then today's real date and the term week, then the current state, then the course you need.

Never skip these, not even for a one-line task:
1. Read `_agent/rules.md` before you act. Its academic-integrity rules are never overridden in the moment.
1. Get the real date and compute the term week before you say anything time-relative.
1. Before you finish, write anything new into the right file (the routing table in `_agent/CONVENTIONS.md`), in the same turn, without being asked.
1. Never write passwords, API keys, tokens, private calendar addresses or notification topics into any file here: everything in this folder syncs and every agent can read it.

For humans: the folder map is [README.md](README.md) and the lookup table is [where-to-find-what.md](where-to-find-what.md).
