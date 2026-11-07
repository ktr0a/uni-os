# Academic integrity

Uni OS puts capable agents next to your coursework. Used carelessly, an agent writes the proof you were supposed to find, or helps on work your course requires to be yours alone. This page explains the rules every agent in the system follows, how you set them per course and per graded item, what each role does at each level, and why the default is "hints only".

**Your university's rules come first.** Uni OS enforces the levels you configure; it cannot know your course's policy on collaboration and AI use. Read each course's rules (course page, syllabus, the first exercise session), set the levels to match or stricter, and disclose AI use wherever your course asks you to. When in doubt, ask the course staff. This page is not legal or official advice.

## The assistance levels

Every course has an assistance level, and every graded assessment can override it. The levels are defined in the vault's `_agent/rules.md` (section "Academic integrity (non-negotiable)") and in the exercise-help role brief:

| Level | The agent may | The agent must never |
|---|---|---|
| `solo` | **nothing on this work.** It says so in one sentence and stops. No hints, no checking, no diagrams, no "related" examples aimed at it, no error-log rows, no links, no storing or summarising your own solution, handwritten or typed. | help in any way on that work |
| `hints-only` (default) | give the **smallest hint that gets you moving**, a stronger one only if you are still stuck; explain a technique on a *different* worked example; check your own steps and point at the exact wrong line and why; ask guiding questions; check complexity and edge cases; write extra test cases for your own code | write your proof, derivation, final answer or code; give "the last step"; point to the official solution of the same task |
| `coach` | everything in `hints-only`, plus full explanations on similar tasks, a line-by-line review of your complete draft with each fix named in words, and discussion of the structure of an approach | write the final text or code of the graded task itself: you write it |
| `full` | full worked solutions, every step written out, for ungraded practice where the course allows it and you chose it | skip steps; be used for work the course restricts; hand in or submit anything |

Rules that hold at every level:
- **Course rules are never overridden in the moment**, not even when you ask in a hurry. For `solo` work, graded work the course requires to be your own, and timed graded windows, the agent declines in one sentence and offers what is allowed.
- **The level changes in the config, not in the conversation.** Under `hints-only` the agent never gives the full solution, not even at the end, also on ungraded practice. Asked for one, it gives the next rung of the hint ladder (or, after the time cap, the missing idea in one line) and tells you that a looser level is a config change.
- **Timed graded windows** (a live quiz, a timed bonus task) get no help of any kind while they run.
- **Graded programming:** never your code, not even a "fixed" line. Allowed: the exact line that is wrong, a hand trace, extra test inputs, the idea or data structure to use, complexity checks.
- **Reused tasks:** if a task is identical to an older one, the agent says so openly but does not point to the official solution of an identical graded task by default; it uses a different solved example.
- **Visuals follow the same rules:** a diagram of the concept on a different example, or of your own attempt with the wrong spot marked, never the structure of a graded solution.
- **When it is unclear which level applies** (is this task graded? is this the solo one?), the agent uses the stricter level and asks.

### Never store solutions to graded work

From `_agent/rules.md`: no AI-written finished solutions or code for graded tasks in the vault, and no transcripts or summaries of your own `solo` work. Coaching notes, error logs (except for `solo` work) and technique explanations are fine. The error log's "Correct idea" column holds the general rule, a check on a small case and the habit, never the full solution of a current graded task. The inbox sync refuses update notes that would put protected graded work into the vault.

## Setting the levels

Three config keys decide the level, resolved in this order (first match wins), with `hints-only` as the last fallback:

1. the assessment's `assistance` (`[[courses.assessments]]`),
2. the course's `assistance` (`[[courses]]`),
3. `study.assistance_default` (default `"hints-only"`),
4. if none of them is set: `hints-only`.

An assessment's level applies to that assessment only; the course level covers everything else in the course (ungraded sheets, practice). An example from the fictional `examples/alex.toml`:

```toml
[study]
assistance_default = "hints-only"

[[courses]]
id = "dm"
short = "DM"
assistance = "hints-only"          # practice and anything not listed below

  [[courses.assessments]]
  name = "Graded sheets"
  kind = "sheet"
  counts_for = "bonus"
  assistance = "solo"              # the course requires these to be your own work: no help at all

  [[courses.assessments]]
  name = "Practice sheets"
  kind = "sheet"
  counts_for = "none"
  assistance = "hints-only"

[[courses]]
id = "prog"
short = "PROG"
assistance = "coach"               # ungraded practice: draft reviews allowed
notes = ["Never store finished solutions or code for graded tasks."]

  [[courses.assessments]]
  name = "Programming exercises"
  kind = "sheet"
  counts_for = "admission"
  assistance = "hints-only"        # graded: stricter than the course level
```

- `courses[].notes` holds course-specific rules every agent reads, such as "solo only in the weeks of your own oral interview"; they appear in `rules.md` under "Course-specific rules" and on the course card.
- `courses[].integrity` holds the course's official integrity or AI-use rule in one or two sentences; agents follow it on top of `assistance`.
- After changing a level, run `python tools/uni_os.py render` (or ask your agent to). The levels appear in `_agent/rules.md`, the role briefs, the course cards, the `course-facts` skill and `_agent/uni-os.json` (from which the cockpit assistant fills its integrity lines). `render` updates every one of these files that nobody edited since setup, and always regenerates `uni-os.json`, so the cockpit assistant is current at once. The course-level table in `_agent/roles/README.md` sits in a generated region (`integrity`), so `render` refreshes it even after the file was edited. Other files you or an agent edited, which is normal for `rules.md` and the course cards after a few weeks, are kept and listed as "kept ... you edited"; their integrity tables have no generated region, so ask your agent to update the table in `rules.md` and the level on the course card by hand, in the same turn. `python tools/uni_os.py render --dry-run` shows which files would be updated and which are kept.
- `rules.md` is protected from casual edits: its integrity section changes only when you deliberately change a course policy, never because a task would be easier.

The setup interview asks for each course's official rule on collaboration and AI use (quote it if you can), your default level for graded work, any course that needs a different level, and which graded items must be entirely your own work (oral bonus problems, timed tasks, solo-graded sheets). It recommends `hints-only` as the default and `solo` wherever the course demands it ([`../setup/interview.md`](../setup/interview.md), questions 3.4 to 3.7).

## What each part of the system does at each level

| Part | `solo` | `hints-only` (default) | `coach` | `full` |
|---|---|---|---|---|
| **Exercise help** (role) | one sentence, then nothing; no logging, linking or storing | the hint ladder after a cold attempt (`study.exercise_help.cold_minutes`, 25), a time cap per part (`part_cap_minutes`, 45), then the missing idea in one line; HTML hint pages with a hint ladder only; checks of your steps | plus full explanations on similar tasks and line-by-line reviews of your draft | worked solutions for allowed ungraded practice |
| **Quiz coaching** (role and `quiz-prep` job) | builds nothing aimed at that quiz, no review, logs nothing from it; the prep job skips solo quizzes | prep sheets, mocks on request (a mock's own questions may have worked answers, because they are practice), explanations, and the review after the result is out; current sheet tasks inside prep material stay at their own level; the attempt itself is always yours, no help while it runs | as `hints-only` | as `hints-only` |
| **Study pages and lecture rundowns** | nothing is built for that work | teaching pages, skims, rundowns, recaps, summaries and cheat sheets from the course's real sources; never the finished solution of a current graded task (sheet questions are routed to exercise help); no solution links | same | same; graded work keeps the stricter rule |
| **Error logs** | never discussed, logged or linked; a solo row found later is deleted (the one exception to append-only) | every error logged unasked, in the same turn; "Correct idea" = the general rule, never the full solution | same | same |
| **Handwritten notes** | never transcribed, summarised, checked or stored | reads your attempt and points at the first wrong line without writing the solution | reviews the draft line by line in words | as allowed for ungraded practice |
| **Cockpit assistant panel** | its prompt (`_agent/cockpit/assistant-prompt.md`) lists each course's level (and every assessment that differs) and tells it to follow the rules exactly and say why it declines; it never edits notes or the calendar | answers from your notes within the level | same | same |
| **Daily prep** | only the task sheet goes into the prep note, with the integrity warning in the item | material per block, with the assistance level noted; never a solution of a graded or identical older task; nothing you keep closed inside an integrity window (for example your own summary sheet in the week before an oral) | same | same |
| **Course files fetch** | never opens solo or integrity-window work (filing needs no reading) | official files only; date-gated solutions stay out until their date, enforced in the requester and in the pick-up (`course_fetch.date_guards`) | same | same |
| **Waiting-on-you page, heartbeat** | graded work appears only with its status and deadline, never with help | same | same | same |

Official solutions of **ungraded** tasks: with `study.exercise_help.official_solutions_after_attempt = true` (the default), the exercise-help role points to the official solution on your explicit request after your own attempt. Graded work: never.

Practice questions in prep sheets, study pages and mocks are always labelled: official (which sheet, quiz or handout, from this term), adapted, or invented.

## Why hints-only is the default

The original system began with looser rules: full answers for some courses' ungraded tasks, worked solutions for some sheets. After a few weeks the student switched every course to hints only, for every sheet, graded or not, for two reasons that apply to most students:

1. **Learning.** A worked solution feels like progress but is gone a day later. The smallest nudge, then finishing yourself, is what makes the next sheet (and the exam) doable. The bar the original's plans used was "you can solve that week's exercises unaided".
2. **Integrity.** Most courses allow help with understanding but require graded work to be your own; some forbid any AI help on specific tasks (an oral bonus problem, a timed bonus task), and for graded programming tasks AI-written code can count as plagiarism. Getting caught can cost every bonus point of the course, and worse. An agent that writes solutions makes the boundary fuzzy; an agent that only hints keeps it clear.

Setting the level in the config rather than in the moment is deliberate: a tired "just tell me" late at night should not end in a worked solution.

## Your responsibility

- Check every course's integrity and AI-use rules at the start of the term and whenever a new kind of graded work appears; set `solo` wherever the course demands your own work.
- Record the rule in `courses[].integrity` or `courses[].notes`, so every agent sees it.
- Disclose AI assistance where your course requires it.
- Treat an agent's refusal as the system working, not as a bug. If a level is wrong, change the config after re-reading the course rules.
- If an agent ever helped on `solo` work (for example because the assessment was not marked `solo`), set the level, delete anything stored about that work, and tell the course staff if your course requires it.

## Related pages

- [`../modules/exercise-help/README.md`](../modules/exercise-help/README.md): the hint ladder and the help protocol in detail.
- [`../modules/quiz-coaching/README.md`](../modules/quiz-coaching/README.md): quiz prep and reviews.
- [`security-and-privacy.md`](security-and-privacy.md): credentials, course sites and the password step.
- [`../config/schema.md`](../config/schema.md): `study.assistance_default`, `courses[].assistance`, `[[courses.assessments]]`.
