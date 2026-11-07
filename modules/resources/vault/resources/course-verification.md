---
type: resource
audience: both
updated: {{generated.date}}
tags: [uni/resources, verification]
---
# Course verification: claims, checks, verdicts

A read-only fact-check of every course fact the system relies on, against the real course pages. It turns "we think the sheets come out on Friday" into "WRONG: the course page says 'every Thursday', checked Sat 24 Oct", and pushes the corrections into the course cards, the overview, the plans and the config. In the original system one full pass in week 5 found a wrong release day, two "extra sessions" that were other groups' regular slots, a quiz scope broader than believed, an exam-language disagreement between catalogue and course page, and a week-numbering offset, all of which had been steering plans and answers.

## When to run it
- **Week 0 or 1**, as soon as the course pages are up: the first full pass, right after setup.
- **After any announcement that changes a date, a rule or a scope.** Check just the affected claims.
- **Around the middle of the term** (week 5 or 6): a full pass; rhythms and rules drift.
- **Before relying on a fact for points** (a quiz scope the evening before, a deadline that looks odd).
- **When two sources disagree**, or the student says "are you sure?".

Each run gets its own dated folder: `resources/course-verification-YYYY-MM-DD/` with `course-verification-claims.md` (written first) and `course-verification-results.md` (written during the pass). Add one line per run to the run log at the bottom of this page.

## The method
1. **Collect the claims before browsing.** Gather every course fact the system believes from the course cards, the course-facts skill, the courses overview, the topic plans{{#if modules.progress}} and the status page{{/if}}. Write each as a precise, testable statement with an ID per course (`AD1`, `AD2`, ..., `G1` for general claims). Include open questions as claims ("Total number of quizzes and the last date?").
2. **Open a session that can see the pages.** Logged-in pages need the student's signed-in browser (in Claude Code: a laptop session with the desktop app's built-in browser, or Claude in Chrome for sites that need HTTP credentials; other agents: their browser tool, or the student pastes the pages). The student signs in first; the agent never types a password and asks for all sign-ins in one request.
3. **Walk each course strictly read-only:** the course page, **every** announcement thread since the start of term, the graded-items overview, special pages (bonus system, exam information), the course website, the course catalogue entry. "Do not change anything: solely click through the data and read." No quiz attempts, no submissions, no downloads of graded content.
4. **Give every claim a verdict** with the official wording in double quotes and a source abbreviation: `OK` · `PARTLY` (say which part) · `WRONG` (give the correction) · `NOT FOUND` (nothing official says it; it stays an estimate or an inference, labelled).
5. **Write down new facts** you met on the way, per course, and a "Still open after the full pass" list with who can answer each item.
6. **Propagate.** Correct each course card in place with the date and source ("Corrected <date> (verification run): ..."), then the courses overview, the topic plans, the week page if this week is affected, and the config entries (`_agent/uni-os.toml`) so the course-facts skill re-renders right. Tell the student in a few lines what changed and what it means this week.

## Claims file template
```markdown
# Course verification: claims to check (<Ddd D Mon YYYY>, week <n>)

Built from the course cards, the course-facts skill, the courses overview and the topic plans.
Each claim gets a verdict from the real course pages: OK / PARTLY / WRONG / NOT FOUND, with source.
Results go into course-verification-results.md in this folder.

## <COURSE> (<LMS course page>, <other platforms>)
- <C>1 Lecturers; lecture days, times, rooms; extra or swapped lectures.
- <C>2 Own exercise group, slot, room.
- <C>3 Release and due rhythm; hand-in channel; group rules.
- <C>4 Each graded stream: window, timer, number of questions, points, attempts; scope. Total number and last date?
- <C>5 Bonus formula and what full bonus needs; official semester maximum?
- <C>6 Integrity and AI rules.
- <C>7 Exam format (length, mode, language, aids): logistics only.

## General
- G1 Course catalogue entries for this term (times, rooms, exam mode).
- G2 Last lecture days.
- G3 Every announcement since the start of term that changes a date, a rule or a scope.
```

## Results file template
```markdown
# Course verification: results (<Ddd D Mon YYYY>, week <n>)

Read-only pass through the real course pages (<which browser/session>). Claim IDs refer to the claims file in this folder. Nothing was submitted or changed on any site.

## <COURSE>
Sources: CP = course page <url> · ANN = announcements (all <N> threads) · GB = graded items overview · SITE = course website · CAT = course catalogue

| ID | Verdict | Official wording / correction | Source |
|---|---|---|---|
| <C>1 | OK | "<verbatim quote>" | CP |

New facts (<COURSE>):
- ...

## Catalogue cross-check
- ...

## Still open after the full pass
- <item> (who can answer: TA / course page later / the student)
```

## Starter claims from your config
Copy these into the first claims file (they use the claim IDs of the template above; give several graded streams of one course letters when you copy them: 4a, 4b, ...), then add what the cards say beyond them. Every value here comes from `_agent/uni-os.toml`; "(not configured)" items are open questions to answer during the pass.
{{#each courses}}

### {{course.short}}: {{course.name}}
- {{course.short}}1 Lectures: {{#if course.lecture_slots}}{{course.lecture_slots}}{{else}}(not configured){{/if}} · lecturers, rooms, extra or swapped lectures?
- {{course.short}}2 Exercise session: {{#if course.exercise_slots}}{{course.exercise_slots}}{{else}}(not configured){{/if}}{{#if course.exercise_group}} · {{course.exercise_group}}{{/if}} · room?
- {{course.short}}3 Sheets out {{#if course.sheet_release}}{{course.sheet_release}}{{else}}(not configured){{/if}} · due {{#if course.sheet_due}}{{course.sheet_due}}{{else}}(not configured){{/if}} · hand-in: {{#if course.hand_in}}{{course.hand_in}}{{else}}(not configured){{/if}}
- {{course.short}}3s Session rule: {{#if course.session_rule}}{{course.session_rule}}{{else}}(not configured: what does the exercise session of week n cover?){{/if}}{{#if course.week_numbering}} · week numbering: {{course.week_numbering}}{{/if}}
{{#each course.assessments}}
- {{course.short}}4 Graded stream "{{item.name}}" ({{item.kind}}){{#if item.schedule}}: {{item.schedule}}{{/if}} · counts for: {{item.counts_for}}{{#if item.points_max}} · {{item.points_max}} points{{/if}}{{#if item contains "scope"}} · scope: {{item.scope}}{{/if}} · total number and last date?
{{else}}
- {{course.short}}4 Graded streams: (none configured: does anything count for a bonus, the grade or admission?)
{{/each}}
- {{course.short}}5 Bonus: {{#if course.bonus.scheme}}scheme `{{course.bonus.scheme}}`{{#if course.bonus.rule}} · rule: {{course.bonus.rule}}{{/if}}{{#if course.bonus.target}} · full bonus at: {{course.bonus.target}}{{/if}} · official semester maximum?{{else}}none configured: confirm that the course has no bonus{{/if}}
- {{course.short}}6 Integrity and AI rules: {{#if course.integrity}}{{course.integrity}}{{else}}(not configured){{/if}}
- {{course.short}}7 Exam format (logistics only): {{#if course.exam_format}}{{course.exam_format}}{{else}}(not configured){{/if}}
{{/each}}

## Lessons from past runs
- Facts inferred from file timestamps can be wrong: re-uploads on Friday made a Thursday release look like Friday. Announcements win.
- "Extra sessions" were other groups' regular slots. Check the group list.
- A quiz's time limit was not written anywhere official; only the student's experience confirmed it. Record such facts as "confirmed by the student on <date>".
- Week numbers on the LMS ran one ahead of the term weeks.
- The course catalogue and the course page disagreed about the exam language: record both and which is binding.
- A bonus formula depended on a semester maximum that was never published: keep the estimate, labelled.
- The mobile LMS app did not show groups; a browser did.
- Only one language version of a sheet was binding; "the last push before the deadline is binding" (a commit before but a push after counts as late).

## Run log
| Date | Week | Scope | Folder | Corrections propagated to |
|---|---|---|---|---|
