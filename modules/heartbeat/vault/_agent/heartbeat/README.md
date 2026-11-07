---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Heartbeat: memory and output of the watcher job

The job `heartbeat` (brief: `_agent/jobs/heartbeat/prompt.md`) wakes a few times a day ({{schedule.heartbeat}} on {{schedule.heartbeat_days}}{{#if schedule.heartbeat_weekend}}; {{schedule.heartbeat_weekend}} on {{schedule.heartbeat_weekend_days}}{{/if}}). A deterministic pre-check (`uni-os heartbeat precheck`, no agent) decides first whether anything fired since the last run; only then does an agent read the whole state of the study system and either stay silent, push one combined line, or ask one combined question. This folder is its memory and its output.

Not the same thing as a host's liveness ping or a dashboard's "host heartbeat" (the age of a status file): those are about the machine, this is about the study system.

| File | Written by | What |
|---|---|---|
| `flags.json` | the job only (`uni-os heartbeat commit`, overwritten in place so a synced file keeps its id) | what the heartbeat flags now; dashboards show it under "needs attention" as "flagged by the heartbeat at HH:MM" |
| `state.json` | the job only | its memory: last run, input hashes, flagged items with first and last seen and last push, snoozes, recent actions and asks |
| `heartbeat-log.md` | the job and its question session; append-only | one line per run: what fired, what it flagged, pushed, asked or did |
| `requests.md` | anyone; append-only | "stop telling me about X": one line per request |
| `duties.md` | {{student.name}} or the coordinator | the duty checklist: date-triggered duties that nothing else triggers |

Machine state that must not sync (event markers, the pending question, the pre-check log) lives outside the vault, in the heartbeat state folder (`uni-os heartbeat state --json` prints where).

## flags.json (schema 1)
```json
{
  "schema": 1,
  "generated": "2026-11-09T07:52:10+01:00",
  "writer": "uni-os heartbeat",
  "run": { "at": "2026-11-09T07:52:10+01:00", "kind": "slot|event", "act_mode": "safe|full", "dry_run": false },
  "flags": [
    { "id": "due:la-a7-hand-in:overdue", "level": "red|amber|grey",
      "text": "one line, at most 300 characters", "since": "ISO, first flagged", "last_seen": "ISO, this run",
      "pushed_at": "ISO or null", "snoozed_until": "YYYY-MM-DD, \"indefinite\" or null",
      "source": "rule:<name>|outcome-checks|judgment", "action": "flagged|pushed|asked|messaged ...", "where": "#progress or empty" }
  ]
}
```
Before the first committed run the file is a placeholder: `"generated": null`, `"status": "not-switched-on"`, no flags. `id` is stable across runs, so dashboards and the push gate can dedupe: rule findings use the pre-check's ids (`due:<item>:overdue|behind`, `prep:gap:<date>`, `prep:tomorrow-missing:<date>`, `week:missing:<file>`, `job:<name>:failed|missed`, `inbox:stuck:<slug of the file name>`, ...), the heartbeat's own judgments `judgment:<topic>`, `duty:<checklist row>`, `result:<item>`, `waiting:<item>`. A flag that is resolved is left out of the next file.

## state.json (schema 1)
`{schema, updated, last_run: {at, kind, fired: [...], act_mode}, inputs: {<label>: <hash>}, outcome_keys: [...], flagged: {<id>: {first, last, level, text, pushed}}, snoozes: {<id or prefix*>: {until, why, added}}, actions: [last 30], asks: [last 20]}`. `inputs` holds a short hash of every input the pre-check watches; a changed hash is one of the triggers.

## heartbeat-log.md
Append-only, one line per event: `- YYYY-MM-DD HH:MM | slot|event|note|answer[ DRY-RUN] | <what fired, what was flagged, pushed, asked or done>`.

## requests.md
One line per request, newest last: `- YYYY-MM-DD HH:MM | snooze | <what, in the student's words; `flag-id` in backticks if known> | until <YYYY-MM-DD or "further notice"> | <who wrote it down>`. A line that names an id (or a prefix ending in `*`, e.g. `` `prep:gap:*` ``) is honoured by the pre-check at once; free-text lines are turned into snoozes by the next agent run. `resume` instead of `snooze` lifts a snooze.

## Writing a flag from a job (instead of a push)
A job that could not finish its work (a calendar write was denied, a source was missing) writes one small file `_agent/logs/flags/<job-id>.md` and lets the heartbeat decide whether {{student.name}} must hear about it:
```markdown
---
job: daily-study-prep
at: 2026-11-10 17:31
level: red
---
calendar write denied; prep note written without MATERIAL blocks
```
The pre-check turns it into the finding `job:<job-id>:failed` (level from the file, default red; the first body line is the text). The next successful run of that job deletes its own flag file. An exit code of 0 says a job ended, not that its result is there: this is how a job says "ended, but the result is incomplete".

## Commands
`uni-os heartbeat report` (what the agent reads first) · `precheck` (the job's gate: exit 0 run, 1 skip) · `commit FILE` · `state` · `flags` · `log TEXT` · `tracker TEXT` · `ask --ids A,B --text Q` · `rerun JOB` · `outcomes [--push]`. All of them take `--dry-run` and `--now "YYYY-MM-DD HH:MM"`. `uni-os` is the framework's command line; where it is not a command, run `python "<framework folder>/tools/uni_os.py"` (in a scheduled job: `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"`) from the vault root.
