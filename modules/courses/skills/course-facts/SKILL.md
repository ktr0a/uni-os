---
name: course-facts
description: "{{university.short}} {{term.label}} courses ({{#each courses}}{{course.short}}{{#unless @last}}, {{/unless}}{{/each}}): what a given week, lecture or exercise session covers, sheet and deadline rhythm, graded work and bonus rules, what help is allowed, and where to look each thing up. Use for any question about these courses this term."
---

# Course facts: {{university.name}}, {{term.label}}

Use this for any question about {{#each courses}}{{course.name}} ({{course.short}}){{#unless @last}}, {{/unless}}{{/each}} in {{term.label}}: what today's lecture or exercise session covers, what is due when, how the bonus works, what help is allowed on a task, or where a file lives.

This skill was rendered from the Uni OS config (`_agent/uni-os.toml`) on {{generated.date}}. **The course cards beat this skill.** Facts learned later, and corrections, live in the course cards (`<course folder>/<slug>.md`). Authority order for course facts: (1) what the student says now, (2) the official course pages ({{university.lms}} course page and its announcements, course website), (3) the course catalogue, (4) the course cards, (5) this skill, (6) predicted topic plans, (7) anything else derived.

## Always do this first
1. **Get today's real date** (`date` in a shell, or the date your environment states). Never assume it.
2. **Compute the term week.** Week 0 starts Mon {{term.week0_monday}}; week n starts week 0 + 7n days.{{#if term.last_lecture_day}} Last lecture day: {{term.last_lecture_day}}.{{/if}} Timezone: {{term.timezone}}. One way to compute it:
   `python -c "import datetime as d; w0=d.date.fromisoformat('{{term.week0_monday}}'); print((d.date.today()-w0).days // 7)"`
   (or `python tools/uni_os.py week --vault "<vault>"` in the framework folder, which also prints the week's dates). Put dates next to week numbers when you answer ("week 6, Mon <date> to Sun <date>"); a negative result means the term has not started, a result past the last lecture week means the lecture-free period.
3. **Read the course card** of the course in question (Facts, Weekly rhythm and bonus, Known gaps). Prefer its newer facts over anything below.
4. **Apply the session rule for that course** (below). An exercise session almost never covers the material of that same day: it lags the lectures by roughly a week, and the lag differs per course. Getting this wrong is the main failure mode.
5. **Say which parts are certain and which are predicted.** Fixed points (dates, rooms, deadlines, graded-work rules) come from the official pages and the cards; the per-week topic map is a prediction. If points depend on the answer, say so and offer to check the official page.

## Weekly rhythm per course
{{#each courses}}
### {{course.short}}: {{course.name}}
- Lectures: {{#if course.lecture_slots}}{{course.lecture_slots}}{{else}}(not configured; see the card){{/if}}{{#if course.language}} · language: {{course.language}}{{/if}}
- Exercise session: {{#if course.exercise_slots}}{{course.exercise_slots}}{{else}}(not configured; see the card){{/if}}{{#if course.exercise_group}} · {{course.exercise_group}}{{/if}}
- Sheets: released {{#if course.sheet_release}}{{course.sheet_release}}{{else}}(?){{/if}} · due {{#if course.sheet_due}}{{course.sheet_due}}{{else}}(?){{/if}}{{#if course.hand_in}} · hand-in: {{course.hand_in}}{{/if}}
- **Session rule (what the exercise session of week n covers):** {{#if course.session_rule}}{{course.session_rule}}{{else}}not configured yet. Work it out from the release and due days (see `references/rhythm-patterns.md`), say that it is inferred, and suggest adding it to the card and the config.{{/if}}
- Week numbering: {{#if course.week_numbering}}{{course.week_numbering}}{{else}}not configured; assume term weeks and say so.{{/if}}
{{#each course.assessments}}- Graded: **{{item.name}}** ({{item.kind}}){{#if item.schedule}}: {{item.schedule}}{{/if}} · counts for: {{item.counts_for}}{{#if item.points_max}} · {{item.points_max}} points{{/if}} · help: `{{item.assistance}}`{{#if item contains "scope"}} · scope: {{item.scope}}{{/if}}
{{/each}}{{#each course.notes}}- {{item}}
{{/each}}- Card: `{{course.folder}}/{{course.slug}}.md` · topic plan: `{{course.folder}}/reference/{{course.slug}}-topic-plan.md`

{{/each}}
Calendar oddities (a lecture swapped with another course for a week, extra or cancelled lectures, other groups' regular slots that look like extra sessions) are on each card under Facts and Known gaps: check them before answering about a specific day.

## Per-week content map (predicted)
The cross-course map is in `courses-overview.md` ("Per-week content map"), the detail per course in `<course folder>/reference/<slug>-topic-plan.md` (one block per week: lectures, reading with pages, what to do, checkpoint, rough hours). Both are predictions: say "predicted" when an answer rests on them, and prefer the course card's Lecture log and the official roadmap for anything already past.

## Graded work and bonus schemes
| Course | Scheme | How it is earned | Rule | Max | Full bonus at |
|---|---|---|---|---|---|
{{#each courses}}| {{course.short}} | {{#if course.bonus.scheme}}`{{course.bonus.scheme}}`{{else}}no bonus{{/if}} | {{#if course.bonus.description}}{{course.bonus.description}}{{else}}-{{/if}} | {{#if course.bonus.rule}}{{course.bonus.rule}}{{else}}-{{/if}} | {{#if course.bonus.max_bonus}}{{course.bonus.max_bonus}}{{else}}-{{/if}} | {{#if course.bonus.target}}{{course.bonus.target}}{{else}}-{{/if}} |
{{/each}}

These rules decide where effort pays. When asked, work out the slack: how much can still be missed with the full bonus intact ("best 5 of 7 points already give the full bonus"; a linear scheme has no slack, every point counts). Integrity rules for bonus work are in the next section; graded `solo` work stays solo even when the bonus is at stake.

Totals that the course never publishes (semester maximum, points per task) are estimates: the card says so and says what would replace them. Never present an estimate as official.

## Help allowed (integrity)
| Course | Default assistance | Official rule |
|---|---|---|
{{#each courses}}| {{course.short}} | `{{course.assistance}}` | {{#if course.integrity}}{{course.integrity}}{{else}}(see the course card){{/if}} |
{{/each}}

Levels: `solo` = no help at all on that work (no solving, no hints, no checking; never discussed, logged or linked); `hints-only` = smallest hint first, technique on a different example, checking the student's own steps, never their proof, answer or code; `coach` = hints plus review of the student's own work; `full` = worked solutions, only where the course allows it. A per-stream override in the list above beats the course default. When unsure which stream a task belongs to, ask before helping.

## Key dates
- Week 0: Mon {{term.week0_monday}}.{{#if term.last_lecture_day}} Last lectures: {{term.last_lecture_day}}.{{/if}}{{#if term.lecture_free_from}} Lecture-free from {{term.lecture_free_from}}.{{/if}}{{#if term.exam_session_start}} Exam session: {{term.exam_session_start}} to {{term.exam_session_end}} (dates and format logistics only).{{/if}}
{{#each term.holidays}}
- {{item.name}} ({{item.from}} to {{item.to}}): no teaching; check each course for moved sessions or deadlines
{{/each}}
{{#each courses}}
{{#if course.exam_format}}
- {{course.short}} exam format: {{course.exam_format}}
{{/if}}
{{/each}}

## Where to look things up
- **Course cards** `<course folder>/<slug>.md`: facts, rhythm, graded work, bonus, help policy, real sources with page offsets, lecture log, known gaps, file index.
- **Courses overview** `courses-overview.md`: all courses side by side, session offsets, colours, page offsets, per-week content map.
- **Topic plans and course guides** in each course's `reference/` folder.
- **Calendars:** `{{calendar.courses}}` holds the lectures, exercise sessions and graded fixtures; `{{calendar.study_blocks}}` holds self-study blocks, whose descriptions say what each block is for. Judge a block by its title; re-read the live calendar before answering.
- **Official sources, in order of authority:**
{{#each courses}}  - {{course.short}}: {{#if course.lms_url}}{{course.lms_url}}{{else}}{{university.lms}} course page (link not configured){{/if}}{{#if course.website}} · website {{course.website}}{{/if}}{{#if course.platforms}} · {{course.platforms}}{{/if}}{{#if course.recordings}} · recordings: {{course.recordings}}{{/if}}
{{/each}}  - Course catalogue: {{#if university.catalogue}}{{university.catalogue}}{{else}}(not configured){{/if}}{{#if university.recordings}} · recording portal: {{university.recordings}}{{/if}}
{{#if modules.resources}}- **Sources registry** `resources/sources-and-links.md` (authority order, the "real source" per course) and the last verification run in `resources/course-verification.md`.
{{/if}}

## Known gaps (how to handle what you can't see)
- Logged-in pages (LMS, programming platform) are read only through a session that can see the student's logged-in browser. Read-only: never start a quiz attempt, submit, post or change a setting. Never type a password; the sign-in step and one-time codes stay with the student. Collect all needed sign-ins into one request.
- Sites behind HTTP basic authentication often work only in the student's own browser.
- Material behind a login you don't have is "not obtainable": say so, don't guess around it.
- Per-course gaps (unpublished totals, unclear groups, inferred scopes) are listed in each card's "Known gaps and open questions".
- Anything mapped from last year's course (topic plans, recordings, old sheets) is a prediction. Known differences between last year and this year (new script version, changed bonus scheme, new exam mode) are noted on the card; when they matter, say so.

## How to verify a course fact
When a fact matters (points, a deadline, a scope) and the card is old or two sources disagree: state the claim precisely, check it on the official page (announcements beat file timestamps), quote the official wording, then correct the card with the date and the source. The full method is in `references/verify-a-fact.md`{{#if modules.resources}} and `resources/course-verification.md`{{/if}}. Never fix a fact silently: the card keeps the trace ("Corrected <date>: ...").

If a fact in this skill turns out wrong, correct the course card and tell the student which config entry should change (`_agent/uni-os.toml`, the course's `[[courses]]` entry), so the next render of this skill is right. Don't edit this skill by hand.

## Answer shape
For "what will today's {{#each courses}}{{#if @first}}{{course.short}}{{/if}}{{/each}} exercise session cover?": name the session, the sheet number and when it was published, what happens in the room (quiz window, peer grading, new sheet), and the quiz scope if there is one. Two or three sentences. Add a verification line only when the answer rests on the predicted topic map rather than on the fixed rhythm.

## More
- `references/rhythm-patterns.md`: the patterns courses actually follow (lags, numbering offsets, quiz windows, deadline traps) and how to write them as a session rule.
- `references/verify-a-fact.md`: the quick verification procedure.
- `references/course-onboarding.md`: how to fill a new course card at the start of term.
