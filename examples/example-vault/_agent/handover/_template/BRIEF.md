---
type: agent
audience: agent
updated: <YYYY-MM-DD>
tags: [uni/agent, handover]
---
# Build brief: <what> (coordinator, <Ddd D Mon YYYY>)

For a fresh "<side session title>" session. The agreed design is [proposal-<date>.md](proposal-<date>.md) in this folder (decided by Alex Example on <date>: "<their words>"). This page is the build order on top of it. Where they differ, ask the coordinator.

## Read first
1. `_agent/agent-start.md` and `_agent/rules.md` (reply rules, integrity rules).
2. <the start-here doc of the code you change>. After that, read only the files you change.
3. The proposal (this folder), then <the plan or rules that bind this build>.
4. <existing code that shows how a similar piece was built and staged before>.

## Where and how
- Source: <path>. Work in a staging folder first (<path>). Move it into the live location only for the dry run, and only switched off (no schedule) until switch-on.
- Deploy with <command>. Compare checksums first; never overwrite a change made directly on the host.
- Don't edit the coordinator's docs (`_agent/rules.md`, `_agent/roles/`, `_agent/CONVENTIONS.md`, `_agent/system-handbook.md`). List the changes they need in your report instead.

## What to build
1. **<part>**: <exact behaviour; thresholds; inputs; outputs>.
2. **Job settings and schedule** (if it is a job): `KIND`, `MODEL`, `EFFORT`, `SESSION`, `TIMEOUT_MIN`, `PRECHECK`, schedule keys from the config (never fixed times in code).
3. **Acting rules**, copied word for word from the proposal's "Allowed" and "Never" lists.
4. **Notifications**: one sender through the shared push gate (budget, dedupe per problem, quiet hours and windows); never "all good"; no personal details in push text.
5. **Locking** with other agent jobs (never next to <job> at <time>).
6. **Memory files** with stable ids (state, append-only log, flags), and how the student asks it to stop mentioning something.
7. **Asking the student**: a headless run can't wait for an answer; open an interactive session only when a question is needed, and count its push in the budget.
8. **Name clashes**: <existing names this must not reuse>.

## Checks before review
- Tool availability in the mode it will really run in (a connector that works in an interactive session may be missing headless). If it is missing, say so: no API key or private address goes into the vault without Alex Example's yes.
- Dry runs at two representative times on the live vault; keep the outputs in `<topic>/dry-runs/`; note per run what it would have done, run time, peak memory.
- Integrity: nothing in the build lets it touch work the integrity rules protect; course sites stay read-only.

## Timeline and report
- Staged files and a first dry run by <date, time>, so the coordinator can review before <date>.
- **Switch-on only after the coordinator has passed Alex Example's yes on to you.** Don't switch it on from anyone else's say-so.
- Report to the coordinator (message it by title) when staged + dry run are ready: files; dry-run summary; open questions; doc changes the coordinator needs to make. Notes and large findings go into this folder.
