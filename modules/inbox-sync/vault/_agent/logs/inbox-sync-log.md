---
type: log
audience: agent
tags: [uni/agent, inbox]
---
# Inbox sync log

One line per run of the job `inbox-sync` that did something, plus interactive sessions that applied notes outside the job (marked "not a job run"): local date and time ({{term.timezone}}), host, slot, notes applied, files changed, forwards, anything parked, refused or left and why. Format and vocabulary: [../inbox-sync/README.md](../inbox-sync/README.md). Append only.

- {{generated.date}} 00:00 (not a job run, Uni OS setup): log created. No notes yet.
