---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Phone pushes: how and when (for every agent, job and role)

Pushes reach {{student.name}}'s phone through **one gate**, `uni-os push`. Nothing in this system sends a push any other way. The gate keeps one budget for every sender, so a chatty job cannot use up {{student.name}}'s attention.

`uni-os` is the framework's command line. If it is not a command on this machine, run `python "<framework folder>/tools/uni_os.py"` instead (inside a scheduled job: `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"`), from the vault root.

**Silence is the norm.** Push only a problem, or something {{student.name}} must see or decide soon. Never an "all good", never a status summary, never a "done" message for routine work.

## The rules the gate enforces (config `[notify]` in `_agent/uni-os.toml`)
| Rule | Now |
|---|---|
| Pushes per day, across all senders | {{notify.max_per_day}} |
| Minimum gap between pushes | {{notify.min_gap_hours}} h (`--urgent` skips the gap, never the day cap) |
| Same problem id again | not within {{notify.dedupe_hours}} h |
| Quiet hours | {{notify.quiet_hours}}: pushes are **held**: not sent and not queued (send again later if it is still true) |
| Quiet windows (graded fixtures and other do-not-disturb times) | `notify.quiet_windows`: held the same way, even `--urgent` ones; the heartbeat skips its runs |
| "All good" texts | refused |
| Personal details (mail addresses, links in the text, long numbers) | refused; pass a link with `--click` |
| Length | at most {{notify.max_length}} characters (longer is cut) |

## How to push
```
uni-os push "<one line in plain words>" --id <problem-id> --source <your job or role id>
uni-os push --check --id <problem-id>          # what a send would do now; changes nothing
uni-os push "<text>" --id <id> --click "<url>"  # the URL opened when the push is tapped
```
- `--id` is a stable id of the problem (the same id every time you push about the same thing; reuse the heartbeat's ids when they exist, e.g. `prep:tomorrow-missing:2026-11-11`). One push may carry several ids (`--id a --id b`) and then combines several items in one line.
- `--urgent` only for a deadline within the next few hours.
- Host health alerts and job failures use `--direct`: no id needed, outside the budget and quiet hours, but still no personal details; inside a quiet window they are queued and released as one push afterwards (`uni-os push --flush`). Only the host's health check and job runners use it.
- Dry runs (`UNI_DRY_RUN=1` or `--dry-run`) send and record nothing; they print what would happen.

## Exit codes and what to do
| Exit | Meaning | Do |
|---|---|---|
| 0 | sent | note it in your log or final message |
| 10 | held (quiet hours or a quiet window): not sent, not queued | keep it as a flag; push it again after the quiet time only if it is still true and still urgent |
| 11 | budget (day cap or gap) | keep it as a flag; the heartbeat may push it later |
| 12 | dedupe (pushed recently) | nothing: {{student.name}} already knows |
| 13 | refused (no id, "all good", personal details) | fix the reason (never rephrase just to get through), or don't push |
| 1 / 2 | send failed / setup error | say so in your final message; never use another channel instead |

## Never in a push
Names of people, file names, file contents, gap texts, grades beyond a plain score, mail addresses, links in the text, anything about personal matters. The lock screen is public.

The ntfy topic is a secret: it lives only in a file outside the vault (`notify.ntfy_topic_file`). Never copy it into the vault, a log, a prompt or a message.

{{#if modules.heartbeat}}
## Who pushes
- The **heartbeat** job (at most one push or one question per run) and the **outcome checks** (deterministic, every 15 minutes) share the budget and the ids, so the same problem never arrives twice.
- **One sender per outcome problem** (stuck inbox notes `inbox:stuck:<slug>`, missing prep notes `prep:today-missing:<date>` / `prep:tomorrow-missing:<date>`, open prep gaps `prep:gap-open:<date>`): {{#if modules.vm}}the always-on host (its `outcome-checks` job, else the check inside `uni-vm health`). Nobody else pushes these, the heartbeat included: it flags them.{{else}}the `outcome-checks` job where the laptop runs command jobs (`runtime.laptop_scheduler = "os"`), else the heartbeat itself. `uni-os heartbeat report` says which ("Outcome sender: ...").{{/if}} A stuck note counts after {{notify.inbox_stale_hours}} h ({{notify.inbox_stale_hours_taps}} h for Done taps; `notify.inbox_stale_hours[_taps]`, the one threshold).
- Other jobs and roles: prefer a flag for the heartbeat (`_agent/logs/flags/<job>.md`, see `_agent/heartbeat/README.md`) over a push of your own; push yourself only when {{student.name}} must act within hours.
{{else}}
## Who pushes
- The **outcome checks** (deterministic, every 15 minutes, job `outcome-checks`{{#if modules.vm}}; with the always-on host it is the host that sends them, never a second machine{{/if}}) and any job or role that must reach {{student.name}} within hours. Without the heartbeat module nobody judges drift or remembers flags, so keep pushes rare and about one concrete problem each.
{{/if}}
