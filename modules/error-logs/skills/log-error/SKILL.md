---
name: log-error
description: Append a row to a course's error log when the student says "log this error", or the moment an error or point of confusion shows up (exercise help, quiz review, TA correction, study-page quiz, another AI chat, a handwritten page). Keeps the log's "Patterns to watch" and me/weak-spots.md current. Use it unasked, in the same turn.
---
# Log an error

The error logs are the study engine's memory of what goes wrong. Quiz prep, study-page trap cards, cheat sheets and `me/weak-spots.md` are built from them, so a missing row is a lost lesson. Log **the moment it shows up, unasked, in the same turn**; "log this error" from the student means log it now.

## Which file
- One log per course and stream. A course with one stream: `<course folder>/<slug>-error-log.md`. A course with several streams (`courses[].error_log_streams` in `_agent/uni-os.toml`, e.g. theory and programming): `<course folder>/<slug>-error-log-<stream>.md` for each; pick the stream the error belongs to.
- Course unclear? Infer it from the conversation (the sheet, the topic, the session's course). Ask only if a wrong guess would put the row in the wrong course.
- A missing log: run `python _agent/tools/error_log.py sync` (creates missing logs, never overwrites).
- File names use the course **slug**; the log's `course` property and its `uni/<course id>` tag hold the course **id** from `_agent/uni-os.toml`, as on the course card.

## What never goes in
- Anything about work under the `solo` assistance level (resolve: the assessment's `assistance`, else the course's `assistance`, else `study.assistance_default`). Not the error, not the task, not a link. Say in one line that you did not log it and why.
- The full solution of a current graded task. The "Correct idea" column holds the general rule.
- Secrets, emails, other students' names.

## The row
`| Date | Where | What went wrong | Correct idea | Source |`
1. **Date**: `Ddd D Mon` (e.g. `Mon 26 Oct`), the day the error happened (or the day of the quiz or correction).
2. **Where**: `Sheet 3, 3.2 b) <short task name>`, `Quiz W5 Q3`, `Lecture Mon 26 Oct, clicker 2`, `Study page <name>, quiz B Q4`, `Sheet 4 corrections p. 2`, `retest of <date> row (R3)`. Write which numbering is meant when a course numbers weeks or quizzes differently from the term weeks.
3. **What went wrong**: concretely what was written or chosen. Quote the TA's words if there are any. Add the student's state if they said it (tired, rushed, frustrated, timer running out): errors made under fatigue weigh differently when patterns are drawn.
4. **Correct idea**: the rule or idea, a check on a small case (e.g. "test every closed form on n = 1, 2, 3"), and the habit that prevents the error.
5. **Source**: a tag plus the place: `[script] p. 42` (printed page; the page offset is in the course card's "Real sources"), `[slides] L5 s. 12`, `[handout] week 4`, `[task]`, `[lecture]`, `[TA correction] S4 p. 2`, `[quiz review]`, `[derived]`, `[user note]`, `[other AI]`, `[retest]`.

Append at the **bottom of the table** (above "## Patterns to watch"). Re-read the file right before editing. Never edit or delete an old row: a wrong row gets a new row "Correction to the row of <date>: ...". Either edit the file directly or use the helper, which does the insertion and escaping:

```
python _agent/tools/error_log.py add --course <course id> [--stream <stream>] --where "..." --what "..." --idea "..." --source "[script] p. 12" [--date YYYY-MM-DD]
```

## After the row
1. **Patterns**: if this is the second error of the same family, add or extend a numbered pattern in "Patterns to watch": `1. **<pattern name>** (<dates and where>): <what goes wrong>. Fix: <habit, technique or page>.`
2. **Weak spots**: mirror every new or changed pattern as one line in `me/weak-spots.md` under the course (`**<pattern name>**: <what goes wrong>. Fix: <...>. Source: [<log>](../<folder>/<log>.md)`). A pattern seen in two courses also goes under "Across courses". Remove a line there (with a dated note) when the pattern has not come back for a while and the student agrees it is gone.
3. **Open points**: a sticking point that is still unresolved (to take to the exercise class) goes under "Open points".
4. **Session note**: if the student says something that changes how this batch of rows should be weighed (very tired, frustrated, rushed by a timer), add or extend a dated `## Session note (<Ddd D Mon>)` section right below the table, so a bad evening does not later read as a pattern.
5. **Reply**: show the row you added in one line, so the student sees what was logged.

## Batches
- **Quiz review**: every miss becomes one row (`[quiz review]`), plus one pattern check at the end.
- **TA corrections** (annotated graded hand-ins): one row per lost point with the TA's words and the PDF page. For group hand-ins say that authorship is inferred, since the error may be a teammate's.
- **Errors reported from elsewhere** (another AI chat, a handwritten page, a mock quiz): log them like any other, with the right source tag.
{{#if study.error_logs.retests}}
## Retests (on in this vault)
A cold redo of an item from `<course folder>/<slug>-retest-bank.md` is logged as `| <date> | retest of <date of the original row> (R<n>) | ok / again, one line on what was shaky | what to look at next time | [retest] |`. `ok` = solved cold, correct at the first try; `again` = needed a hint or failed. An item `ok` twice is retired. `python _agent/tools/error_log.py retest-pick --course <course id>` lists the next items.
{{/if}}
