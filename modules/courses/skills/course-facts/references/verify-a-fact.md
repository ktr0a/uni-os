# Verifying a course fact

Use this when a fact decides points or time (a deadline, a quiz scope, a bonus rule, which sheet a session covers) and the course card is old, two sources disagree, or the student asks "are you sure?".

## Quick check (one fact)
1. **Write the claim precisely**, as a testable sentence with the source it came from: "Sheets are released on Friday around 12:00 (card, written Sep)."
2. **Find the official source**, in authority order: the course's announcements and course page on the LMS, the course website, the course catalogue. File timestamps and last year's material are weak evidence: corrected re-uploads have made a Thursday release look like a Friday one.
3. **Read it in a session that can see it.** Logged-in pages need the student's signed-in browser; the student signs in, the agent never types a password. Strictly read-only: never start a quiz attempt, submit, post, or change a setting.
4. **Give a verdict:** `OK` (the official wording says so), `PARTLY` (right in part; say which part), `WRONG` (give the official wording), `NOT FOUND` (nothing official says it; it stays an estimate or inference).
5. **Quote the official wording** in double quotes, with where it was found (page, announcement title, date).
6. **Correct the course card in place**, keeping the trace: "(Corrected Sat 24 Oct 2026, LMS announcement 'Exercise sheets': sheets come out Thursday, no fixed time. Older notes said Friday.)" Update every other place that repeats the fact: the courses overview, the topic plan, the week page, the config entry (tell the student which key to change so the skill re-renders right).
7. **Tell the student** in one line what changed and what it means for this week.

## Full pass (all facts, start of term and mid-term)
Collect every claim the system relies on into a claims file before browsing, then check them all in one sitting, then propagate. The method, the file formats and the run log are in `resources/course-verification.md` when the resources module is installed. Run a full pass:
- in the first week, once the course pages are up;
- after any announcement that changes a date, a rule or a scope;
- around the middle of the term (rules and rhythms drift);
- whenever two sources disagree about something that decides points.

## Lessons behind these rules
- An "extra session" turned out to be other groups' regular slot.
- A quiz's time limit was not written anywhere official; only the student's experience confirmed it. Write "confirmed by the student on <date>" in such cases.
- The course catalogue and the course page disagreed about the exam language. Record both and say which one is binding.
- A bonus formula needed a semester maximum that was never published. The card shows an estimate, labelled as one.
- The mobile LMS app hid group information that the browser showed. Use a browser.
