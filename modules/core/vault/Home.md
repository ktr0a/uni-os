---
type: home
audience: me
cssclasses: [uni-os-home]
updated: {{generated.date}}
tags: [uni]
---
# {{university.short}} {{term.label}} · Home

{{university.programme}}, {{university.name}}. Week 0 = Mon {{term.week0_monday}}{{#if term.last_lecture_day}} · last lectures {{term.last_lecture_day}}{{/if}}{{#if term.lecture_free_from}} · lecture-free from {{term.lecture_free_from}}{{/if}}{{#if term.exam_session_start}} · exam session {{term.exam_session_start}} to {{term.exam_session_end}}{{/if}}{{#if modules.planning}} ([all dates](semester/calendar-and-dates.md)){{/if}}.

{{#if obsidian.enabled}}
{{#if modules.cockpit}}
```uni-os-cockpit
```

{{/if}}
> [!agent]- For AI agents (not for me)
> Start at [_agent/agent-start.md](_agent/agent-start.md). Rules, update protocol, routing and the raw archive live in `_agent/`. Keep this Home page and the views up to date as described in [_agent/CONVENTIONS.md](_agent/CONVENTIONS.md).
{{else}}
*For AI agents:* start at [_agent/agent-start.md](_agent/agent-start.md). Rules, update protocol and routing live in `_agent/`.
{{/if}}

{{#if modules.courses}}
## Where I stand
{{#if obsidian.enabled}}
{{#if modules.obsidian}}
![[Courses.base]]

{{/if}}
{{/if}}
{{#if modules.progress}}
Done vs to do per course, bonus standing: [progress/current-status.md](progress/current-status.md) · every result, dated: [progress/tracker-log.md](progress/tracker-log.md)
{{else}}
Each course card holds its own standing (properties `bonus_banked`, `bonus_target`, `next_bonus`).
{{/if}}

{{/if}}
{{#if modules.progress}}
## Next deadlines
{{#if obsidian.enabled}}
![[current-status#Next 10 days]]
{{else}}
See "Next 10 days" in [progress/current-status.md](progress/current-status.md).
{{/if}}

## This week
{{#if obsidian.enabled}}
{{#if modules.obsidian}}
![[Weeks.base]]

{{/if}}
{{/if}}
The current week page is the one in `progress/weeks/` with `status: current`.

{{/if}}
{{#if modules.daily-prep}}
## Study prep
{{#if obsidian.enabled}}
{{#if modules.obsidian}}
![[Latest.base#Prep notes]]

{{/if}}
{{/if}}
Material for each study block: the newest `semester/prep/prep-YYYY-MM-DD.md` (if there are revisions, the highest `-rN` wins).

{{/if}}
{{#if modules.courses}}
## Courses
{{#if obsidian.enabled}}
> [!grid]
{{#each courses}}
>
> > [!{{course.slug}}] [{{course.short}}](<{{course.folder}}/{{course.slug}}.md>)
> > {{course.name}} · help policy: `{{course.assistance}}`
> > [Backlog](<{{course.folder}}/backlog.md>){{#if modules.error-logs}} · {{#each course.error_log_files}}[{{item}}](<{{course.folder}}/{{item}}>){{#unless @last}}, {{/unless}}{{/each}}{{/if}}{{#if modules.obsidian}} · [study pages](<views/Study pages.base>){{#if modules.quiz-coaching}} · [latest quiz prep](<#Latest>){{/if}}{{/if}}
> > Pinned: (add links to the pages you use most)
{{/each}}
{{else}}
{{#each courses}}
- **[{{course.short}}](<{{course.folder}}/{{course.slug}}.md>)**: {{course.name}} (help policy: `{{course.assistance}}`) · [backlog](<{{course.folder}}/backlog.md>)
{{/each}}
{{/if}}

All courses at a glance: [courses-overview.md](courses-overview.md).

{{/if}}
{{#if modules.student-model}}
## Me
{{#if obsidian.enabled}}
> [!grid]
>
> > [!me] [Profile](me/profile.md)
> > Who I am, goals, tools, shorthand, self-ratings.
>
> > [!me] [Weak spots](me/weak-spots.md)
> > Recurring mistakes per course and their fixes.
>
> > [!me] [Learning style](me/learning-style.md)
> > What works for me, per course; study-page preferences.
>
> > [!me] [Rhythm and habits](me/rhythm-and-habits.md)
> > Energy curve, focus span, week shape.
{{#if modules.experiments}}
>
> > [!me] [Experiments](me/habits-experiments.md)
> > One change at a time, measured, reviewed.
{{/if}}
{{else}}
- [Profile](me/profile.md) · [Weak spots](me/weak-spots.md) · [Learning style](me/learning-style.md) · [Rhythm and habits](me/rhythm-and-habits.md){{#if modules.experiments}} · [Experiments](me/habits-experiments.md){{/if}}
{{/if}}

{{/if}}
{{#if modules.planning}}
## Semester
- [Dates and deadlines](semester/calendar-and-dates.md) · [Planning system](semester/planning-system.md) (calendars, block notation) · [Study approach](semester/study-approach.md)
- Week plans: `semester/plans/week-NN-plan.md` (the newest wins; the calendar wins over the plan file) · [Exam-phase plan](semester/plans/exam-phase-plan.md) (study blocks for the lecture-free period and the exam session){{#if modules.experiments}} · [Study experiments](semester/experiments/README.md){{/if}}

{{/if}}
{{#if obsidian.enabled}}
{{#if modules.obsidian}}
{{#if modules.planning}}
### Latest
![[Latest.base#Week plan]]
{{#if modules.quiz-coaching}}
{{#each courses}}
![[Latest.base#{{course.short}} quiz prep]]
{{/each}}
{{/if}}

{{else}}
{{#if modules.quiz-coaching}}
### Latest
{{#each courses}}
![[Latest.base#{{course.short}} quiz prep]]
{{/each}}

{{/if}}
{{/if}}
{{/if}}
{{/if}}
{{#if modules.resources}}
## Resources
[Sources and links](resources/sources-and-links.md) · [Assistant and TA websites](resources/ta-websites-log.md) · [Course facts checked](resources/course-verification.md)

{{/if}}
## Inbox
Unsorted drops: [inbox/](inbox/inbox.md) (an agent sorts them; keep it near-empty).
{{#if obsidian.enabled}}
{{#if modules.obsidian}}
![[Inbox.base]]
{{/if}}
{{/if}}

{{#if obsidian.enabled}}
{{#if modules.obsidian}}
## Views
[Study pages](<views/Study pages.base>) · [Error logs](<views/Error logs.base>) · [Courses](views/Courses.base) · [Weeks](views/Weeks.base) · [Inbox](views/Inbox.base) · [Recently changed](<views/Recently changed.base>) · [Map of the vault](views/vault-map.canvas)

### Recently changed
![[Recently changed.base]]

{{/if}}
> [!tip]- How this vault works
> - **Study material** comes in the formats chosen in setup ({{study.formats}}).{{#if study.formats contains "html"}} An HTML page is the interactive original (quizzes, demos; opens in the browser){{#if study.formats contains "md"}}; a Markdown copy beside it reads inside Obsidian with rendered maths{{/if}}.{{else}} Study pages are Markdown notes that read inside Obsidian with rendered maths; answers sit in folded callouts.{{/if}}
> - **New things** I drop in go to `inbox/`; an agent sorts them.{{#if modules.courses}} New study pages land in each course's `notes/`.{{/if}}
> - **Templates** are in `_templates/`. Insert one with the command "Templates: Insert template".
{{#if modules.obsidian}}
> - **Colours:** each course has its colour (tiles above, its folder in the file list, the graph, the vault map). Other areas have their own: me, progress and weeks, semester, deadlines, agents.
{{/if}}
> - `_agent/` is for AI agents (rules, protocols, job definitions, logs). I don't need to read it.
{{else}}
## How this vault works
- **Study material** comes in the formats chosen in setup ({{study.formats}}).{{#if study.formats contains "html"}} An HTML page opens in the browser{{#if study.formats contains "md"}}; a Markdown copy beside it reads in any Markdown viewer{{/if}}.{{else}} Study pages are Markdown files that read in any Markdown viewer; answers sit in folded `<details>` blocks.{{/if}}
- **New things** I drop in go to `inbox/`; an agent sorts them.{{#if modules.courses}} New study pages land in each course's `notes/`.{{/if}}
- **Templates** for new notes are in `_templates/`.
- `_agent/` is for AI agents (rules, protocols, job definitions, logs). I don't need to read it.
- Without Obsidian there are no live views on this page: ask your agent "what's due this week?" or open the files linked above.
{{/if}}
