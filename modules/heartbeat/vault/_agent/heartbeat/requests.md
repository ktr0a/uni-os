---
type: agent
audience: both
updated: {{generated.date}}
tags: [uni/agent]
---
# Requests to the heartbeat

"Stop telling me about X": any session (or {{student.name}}) appends one line here. Append-only, newest last.
Format: `- YYYY-MM-DD HH:MM | snooze | <what, in {{student.name}}'s words; the flag id in backticks if known> | until <YYYY-MM-DD or "further notice"> | <who wrote it down>`
A line that names a flag id (or a prefix ending in `*`) takes effect at the next pre-check; free-text lines are turned into snoozes by the next heartbeat run. Write `resume` instead of `snooze` to lift one.
Example: `- 2026-11-12 18:40 | snooze | the LA reading pages, `judgment:la-reading` | until 2026-11-20 | {{student.name}} to the coordinator`

