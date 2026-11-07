---
name: course-facts
description: "EIT Autumn 2026 courses (AD, DM, LA, PROG): what a given week, lecture or exercise session covers, sheet and deadline rhythm, graded work and bonus rules, what help is allowed, and where to look each thing up. Use for any question about these courses this term."
---

# Course facts: Example Institute of Technology, Autumn 2026

Use this for any question about Algorithms and Data Structures (AD), Discrete Mathematics (DM), Linear Algebra (LA), Introduction to Programming (PROG) in Autumn 2026: what today's lecture or exercise session covers, what is due when, how the bonus works, what help is allowed on a task, or where a file lives.

This skill was rendered from the Uni OS config (`_agent/uni-os.toml`) on 2026-11-07. **The course cards beat this skill.** Facts learned later, and corrections, live in the course cards (`<course folder>/<slug>.md`). Authority order for course facts: (1) what the student says now, (2) the official course pages (Moodle course page and its announcements, course website), (3) the course catalogue, (4) the course cards, (5) this skill, (6) predicted topic plans, (7) anything else derived.

## Always do this first
1. **Get today's real date** (`date` in a shell, or the date your environment states). Never assume it.
2. **Compute the term week.** Week 0 starts Mon 2026-09-14; week n starts week 0 + 7n days. Last lecture day: 2026-12-18. Timezone: Europe/Zurich. One way to compute it:
   `python -c "import datetime as d; w0=d.date.fromisoformat('2026-09-14'); print((d.date.today()-w0).days // 7)"`
   (or `python tools/uni_os.py week --vault "<vault>"` in the framework folder, which also prints the week's dates). Put dates next to week numbers when you answer ("week 6, Mon <date> to Sun <date>"); a negative result means the term has not started, a result past the last lecture week means the lecture-free period.
3. **Read the course card** of the course in question (Facts, Weekly rhythm and bonus, Known gaps). Prefer its newer facts over anything below.
4. **Apply the session rule for that course** (below). An exercise session almost never covers the material of that same day: it lags the lectures by roughly a week, and the lag differs per course. Getting this wrong is the main failure mode.
5. **Say which parts are certain and which are predicted.** Fixed points (dates, rooms, deadlines, graded-work rules) come from the official pages and the cards; the per-week topic map is a prediction. If points depend on the answer, say so and offer to check the official page.

## Weekly rhythm per course
### AD: Algorithms and Data Structures
- Lectures: Tue 10:15-12:00, Thu 10:15-12:00 · language: English
- Exercise session: Wed 14:15-16:00 · group 3
- Sheets: released Thu 12:00 · due Thu 23:59, one week later · hand-in: LMS upload, one PDF per person
- **Session rule (what the exercise session of week n covers):** The exercise session of week n discusses sheet n-1 and introduces sheet n.
- Week numbering: Sheet k is released in term week k.
- Graded: **Weekly exercise sheets** (sheet): out Thu, due the next Thu 23:59 · counts for: bonus · help: `hints-only`
- Graded: **In-class quizzes** (quiz): weeks 4, 8 and 12, in the exercise session · counts for: bonus · 10 points · help: `hints-only`
- Written answers use the pseudocode conventions of the script.
- Card: `AD/ad.md` · topic plan: `AD/reference/ad-topic-plan.md`

### DM: Discrete Mathematics
- Lectures: Mon 08:15-10:00, Wed 08:15-10:00 · language: English
- Exercise session: Tue 16:15-18:00
- Sheets: released Mon 12:00 · due Mon 12:00, one week later
- **Session rule (what the exercise session of week n covers):** not configured yet. Work it out from the release and due days (see `references/rhythm-patterns.md`), say that it is inferred, and suggest adding it to the card and the config.
- Week numbering: not configured; assume term weeks and say so.
- Graded: **Graded sheets** (sheet): every second week · counts for: bonus · 2 points · help: `solo`
- Graded: **Practice sheets** (sheet): weekly · counts for: none · help: `hints-only`
- Card: `DM/dm.md` · topic plan: `DM/reference/dm-topic-plan.md`

### LA: Linear Algebra
- Lectures: Mon 13:15-15:00, Fri 10:15-12:00 · language: English
- Exercise session: Thu 16:15-18:00
- Sheets: released Fri 18:00 · due Mon 09:00
- **Session rule (what the exercise session of week n covers):** not configured yet. Work it out from the release and due days (see `references/rhythm-patterns.md`), say that it is inferred, and suggest adding it to the card and the config.
- Week numbering: not configured; assume term weeks and say so.
- Graded: **Online quizzes** (quiz): weekly on the LMS, open Fri 18:00 to Mon 09:00 · counts for: bonus · 4 points · help: `solo`
- Graded: **Exercise sheets** (sheet): weekly, discussed in the exercise session · counts for: none · help: `hints-only`
- Card: `LA/la.md` · topic plan: `LA/reference/la-topic-plan.md`

### PROG: Introduction to Programming
- Lectures: Tue 13:15-15:00, Fri 13:15-15:00 · language: English
- Exercise session: Wed 10:15-12:00
- Sheets: released Tue 18:00 · due Tue 18:00, one week later
- **Session rule (what the exercise session of week n covers):** not configured yet. Work it out from the release and due days (see `references/rhythm-patterns.md`), say that it is inferred, and suggest adding it to the card and the config.
- Week numbering: not configured; assume term weeks and say so.
- Graded: **Programming exercises** (sheet): weekly, autograded · counts for: admission · help: `hints-only`
- Graded: **Team project** (project): weeks 10 to 13, in pairs · counts for: grade · help: `hints-only`
- Never store finished solutions or code for graded tasks.
- Card: `PROG/prog.md` · topic plan: `PROG/reference/prog-topic-plan.md`

Calendar oddities (a lecture swapped with another course for a week, extra or cancelled lectures, other groups' regular slots that look like extra sessions) are on each card under Facts and Known gaps: check them before answering about a specific day.

## Per-week content map (predicted)
The cross-course map is in `courses-overview.md` ("Per-week content map"), the detail per course in `<course folder>/reference/<slug>-topic-plan.md` (one block per week: lectures, reading with pages, what to do, checkpoint, rough hours). Both are predictions: say "predicted" when an answer rests on them, and prefer the course card's Lecture log and the official roadmap for anything already past.

## Graded work and bonus schemes
| Course | Scheme | How it is earned | Rule | Max | Full bonus at |
|---|---|---|---|---|---|
| AD | `threshold` | +0.25 grade bonus at 80 % of all sheet points | Sum of sheet points over the term; quizzes count double. | 0.25 | 80 % of all sheet points |
| DM | `points` | Up to 2 points per graded sheet; 8 points give +0.25 | Bonus = 0.25 * min(points, 8) / 8. | 0.25 | 8 points |
| LA | `best-n` | Pass 10 of the 12 online quizzes (70 % each) for +0.25 | At least 10 of the 12 weekly quizzes passed with >= 70 %; fewer passes give a proportional share. | 0.25 | 10 / 12 |
| PROG | no bonus | - | - | - | - |

These rules decide where effort pays. When asked, work out the slack: how much can still be missed with the full bonus intact ("best 5 of 7 points already give the full bonus"; a linear scheme has no slack, every point counts). Integrity rules for bonus work are in the next section; graded `solo` work stays solo even when the bonus is at stake.

Totals that the course never publishes (semester maximum, points per task) are estimates: the card says so and says what would replace them. Never present an estimate as official.

## Help allowed (integrity)
| Course | Default assistance | Official rule |
|---|---|---|
| AD | `hints-only` | Sheets are individual work; AI may explain concepts, never produce solutions. |
| DM | `hints-only` | (see the course card) |
| LA | `hints-only` | (see the course card) |
| PROG | `coach` | (see the course card) |

Levels: `solo` = no help at all on that work (no solving, no hints, no checking; never discussed, logged or linked); `hints-only` = smallest hint first, technique on a different example, checking the student's own steps, never their proof, answer or code; `coach` = hints plus review of the student's own work; `full` = worked solutions, only where the course allows it. A per-stream override in the list above beats the course default. When unsure which stream a task belongs to, ask before helping.

## Key dates
- Week 0: Mon 2026-09-14. Last lectures: 2026-12-18. Lecture-free from 2026-12-19. Exam session: 2027-01-25 to 2027-02-19 (dates and format logistics only).
- Reading day (2026-11-20 to 2026-11-20): no teaching; check each course for moved sessions or deadlines
- AD exam format: written, 120 min, English, one handwritten A4 sheet allowed

## Where to look things up
- **Course cards** `<course folder>/<slug>.md`: facts, rhythm, graded work, bonus, help policy, real sources with page offsets, lecture log, known gaps, file index.
- **Courses overview** `courses-overview.md`: all courses side by side, session offsets, colours, page offsets, per-week content map.
- **Topic plans and course guides** in each course's `reference/` folder.
- **Calendars:** `Courses` holds the lectures, exercise sessions and graded fixtures; `Study blocks` holds self-study blocks, whose descriptions say what each block is for. Judge a block by its title; re-read the live calendar before answering.
- **Official sources, in order of authority:**
  - AD: https://lms.example.edu/course/algo · website https://algo.example.edu · online judge with hidden tests (programming tasks) · recordings: recorded, usually online the next day
  - DM: Moodle course page (link not configured)
  - LA: Moodle course page (link not configured)
  - PROG: Moodle course page (link not configured)
  - Course catalogue: (not configured)
- **Sources registry** `resources/sources-and-links.md` (authority order, the "real source" per course) and the last verification run in `resources/course-verification.md`.

## Known gaps (how to handle what you can't see)
- Logged-in pages (LMS, programming platform) are read only through a session that can see the student's logged-in browser. Read-only: never start a quiz attempt, submit, post or change a setting. Never type a password; the sign-in step and one-time codes stay with the student. Collect all needed sign-ins into one request.
- Sites behind HTTP basic authentication often work only in the student's own browser.
- Material behind a login you don't have is "not obtainable": say so, don't guess around it.
- Per-course gaps (unpublished totals, unclear groups, inferred scopes) are listed in each card's "Known gaps and open questions".
- Anything mapped from last year's course (topic plans, recordings, old sheets) is a prediction. Known differences between last year and this year (new script version, changed bonus scheme, new exam mode) are noted on the card; when they matter, say so.

## How to verify a course fact
When a fact matters (points, a deadline, a scope) and the card is old or two sources disagree: state the claim precisely, check it on the official page (announcements beat file timestamps), quote the official wording, then correct the card with the date and the source. The full method is in `references/verify-a-fact.md` and `resources/course-verification.md`. Never fix a fact silently: the card keeps the trace ("Corrected <date>: ...").

If a fact in this skill turns out wrong, correct the course card and tell the student which config entry should change (`_agent/uni-os.toml`, the course's `[[courses]]` entry), so the next render of this skill is right. Don't edit this skill by hand.

## Answer shape
For "what will today's AD exercise session cover?": name the session, the sheet number and when it was published, what happens in the room (quiz window, peer grading, new sheet), and the quiz scope if there is one. Two or three sentences. Add a verification line only when the answer rests on the predicted topic map rather than on the fixed rhythm.

## More
- `references/rhythm-patterns.md`: the patterns courses actually follow (lags, numbering offsets, quiz windows, deadline traps) and how to write them as a session rule.
- `references/verify-a-fact.md`: the quick verification procedure.
- `references/course-onboarding.md`: how to fill a new course card at the start of term.
