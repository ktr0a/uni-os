# Rhythm patterns: how courses really run, and how to write it down

Courses follow a small number of patterns. Most wrong answers about "what does today's session cover?" come from assuming the session covers the same week's lectures, or from mixing up two week numberings. This file lists the patterns seen in practice (anonymised from the original system, a first-year computer science term with four courses) and how to encode each one as a course's `session_rule` and `week_numbering` in the config and on the course card.

## 1. Session lag patterns
Write the session rule as one sentence of the form **"In the <day> session of week n: <which sheet is discussed>, <what happens in the room>, <which sheet comes out>."** It is always relative to the term week n.

| Pattern | Typical setup | Session rule (example wording) |
|---|---|---|
| Release at the session, due before the next one | Sheet out on the session day, due the evening before the next session | "In the Monday class of week n: discussion and peer grading of sheet n-1 (handed in last night), the weekly quiz, and sheet n is published." |
| Released before the week it is discussed | Sheet uploaded on a Thursday for the following week's tutorial; not handed in | "In the Tuesday tutorial of week n: sheet n is discussed (posted Thursday of week n-1, covering the lectures of week n-1)." |
| Course weeks straddle term weeks | The course counts a "week" as the Friday lecture plus the next Wednesday lecture | "In the Thursday class of week n: assignment n-1 is discussed; assignment n came out yesterday; on quiz weeks the written quiz runs at the start." Week numbering: "course week k = Friday of term week k-1 + Wednesday of term week k." |
| Session works ahead | Sheet out Tuesday evening, due the next Tuesday; the Wednesday session is for the new sheet | "In the Wednesday session of week n: the sheet that was due last night is sheet n; the session is for working on sheet n+1, released yesterday evening." Week numbering: "sheet number = term week + 1." |
| Two-week programming sheets | Individual programming sheets every second Friday, two weeks to solve | Put the release dates in the assessment's `schedule` ("released Fri of weeks 3, 5, 7, ...; due Friday 23:59 two weeks later"), not in the session rule. |

When you are not sure which pattern a course follows, derive it from the release and due days, say it is inferred, and check it in the first two weeks against what actually happens in the room.

## 2. Week-numbering traps
Always write which numbering you mean ("term week 6 = LMS 'Week 7'").
- **The LMS numbers weeks from 1** while the term counts from week 0: LMS "Week k" = term week k-1. Quizzes named "Quiz Week 7" happen in term week 6.
- **Sheet number = term week + 1** when sheet 1 comes out in week 0.
- **A TA's own material** may use yet another count (a TA's "Week N" was the term's week N-1). Check the first date on it.
- **Course weeks that straddle two term weeks** (Friday + Wednesday). On a Thursday, the course week closed the day before.
- **Schedules copied from last year** may be 1-indexed. Put the convention at the top of the file and keep it.
- **Last year's date + 364 days** is the same weekday this year. Use it to map last year's plans and recordings onto this year's dates, then mark the result "predicted".

## 3. Graded quiz windows
- A quiz may open a few minutes early behind a password given in the room, have a timer that starts with the attempt, and still close at a hard time. The time you get is the timer or what is left until the close, whichever is shorter: starting late costs minutes. Write both numbers in the assessment's `schedule`.
- Scope rules are often vague ("all material, focus on the previous two weeks"). Quote them verbatim in the assessment's `scope`, then write the practical reading ("in practice: the lectures of the two previous lecture days plus those weeks' sheets") and mark it inferred.
- A scope like "lectures up to and including the Wednesday of the week before, plus the matching assignment" needs a date computation each time: write the cut-off date and the assignment number into the prep material.
- In-class written quizzes count only in the student's own group: note it.
- "Best k of n" schemes leave slack: say how much ("5 of 7 points give the full bonus").

## 4. Deadline and hand-in traps
- "The last push before the deadline is binding": a commit made before the deadline but pushed after it is late.
- Code that doesn't compile can score 0 points.
- Only one language version of a sheet may be binding when translations exist.
- Hidden tests decide the points; passing the local tests gives nothing by itself.
- A task without points ("greyed out") is not graded: say so before the student spends time on it.
- Group hand-ins: one member submits; check the upload exists, not just that the group "did it".
- Feedback-only hand-ins (no points) are still worth submitting for corrections; say they carry no bonus.

## 5. Facts that drift
- **Release days inferred from file timestamps can be wrong.** Corrected re-uploads on a Friday made a Thursday release look like Friday. Announcements beat timestamps.
- **"Extra sessions" are often other groups' regular slots.** Check the group list before telling the student about an extra.
- **Lecture swaps between courses** (one course borrows another's slot for a week or two) are announced once and then forgotten. Put them on the card and in the calendar.
- **Exam format facts** (length, aids, language) can disagree between the course catalogue and the course page. Note both and which one is binding.
- **Unpublished totals** (semester maximum, points per task) stay estimates: write the estimate, its basis, and what would replace it.
- **Script versions change** during the term; page offsets and numbering can shift with them. Note the version and date you cite.

## 6. Turning a pattern into config
In the course's `[[courses]]` entry of `_agent/uni-os.toml`:
```toml
sheet_release = "Thu 12:00 (LMS)"
sheet_due = "Thu 23:59, one week later"
hand_in = "LMS upload, one per working group"
session_rule = "In the Wednesday session of week n: discussion of sheet n-2 (handed in last Thursday) and questions on sheet n-1 (due tomorrow); in quiz weeks the in-class quiz runs first; sheet n comes out on Thursday."
week_numbering = "LMS 'Week k' = term week k-1; sheet number = term week"

[[courses.assessments]]
name = "In-class quizzes"
kind = "quiz"
schedule = "weeks 4, 8 and 12, Wed 14:15-14:35; opens 14:10 behind a password; 15-min timer from the start of the attempt, hard close at 14:35"
counts_for = "bonus"
points_max = 10
assistance = "solo"
scope = "Official: 'all material is relevant; the focus lies on the previous 2 weeks'. In practice: the two previous lecture days and those weeks' sheets (inferred)."
```
Then copy the same sentences onto the course card, so humans and agents without the skill see them too.
