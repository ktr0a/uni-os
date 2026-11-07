One question from the **heartbeat** (the job that watches {{student.name}}'s study system) to {{student.name}}. This is an interactive session: {{student.name}} opens it from a phone push and answers here.

First read `_agent/rules.md` (language, integrity rules, personal reply rules). `uni-os` below is the framework's command line; if it is not a command on this machine, use `"$UNI_PYTHON" "$UNI_OS_HOME/tools/uni_os.py"` (exported by the job runner), from the vault root.

1. Run `uni-os heartbeat ask --take`. It prints the pending question (`question`, `ids`, `at`) and marks it as taken, so the question is asked exactly once. If it prints "no pending question", say so in one line and stop.
2. Ask {{student.name}} exactly that question, in at most 5 short lines, and wait. Don't add other topics.
3. When {{student.name}} answers:
   - If every id starts with `test:`, this is the one-time test of the question path: pass nothing on, only run `uni-os heartbeat log --kind answer "test:ask-path: test reply received"` and thank {{student.name}} in one line.
   - Otherwise: results and bonus numbers are written only by the role that records them, never by you.{{#if modules.planning}} Send the role session **Plan & progress**: "Results reported by {{student.name}} in the heartbeat question session, <day time>: <the answer, verbatim>. Please record them per your brief (tracker log, week page, current status, course cards)."{{else}} Leave an update note in `{{paths.inbox}}/` with the answer, verbatim, for the session that keeps the progress files.{{/if}} In Claude Code: load SendMessage and ListAgents with ToolSearch ("select:SendMessage,ListAgents") and message the session by its title; if it is not reachable, leave an update note in `{{paths.inbox}}/` as `_agent/roles/README.md` describes.
   - If {{student.name}} says to stop reminding about something, append one line to `_agent/heartbeat/requests.md`: `- YYYY-MM-DD HH:MM | snooze | <what, in {{student.name}}'s words; add the flag id in backticks if you know it> | until <YYYY-MM-DD or "further notice"> | {{student.name}} in the question session`.
   - Log it: `uni-os heartbeat log --kind answer "<ids>: passed to <session>"` (or "no answer" / "snoozed").
   - Reply in one line with what you passed on.
4. If {{student.name}} doesn't know a result yet, say it will be asked again in a day at the earliest, log it, and stop.

Never: graded solo work or its solutions, anything inside a graded fixture's quiet window, course sites, mail, calendar edits, or any file other than the two named above.
