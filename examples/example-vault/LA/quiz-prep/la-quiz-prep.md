---
type: reference
kind: quiz-prep-index
course: la
audience: both
updated: 2026-11-07
tags: [uni/la, quiz-prep]
---
# LA quiz prep: facts, formats and index

Owner: the quiz-coach role for Linear Algebra (session "LA · Quiz coaching"). This folder holds the preparation for and the review of the course's **graded quizzes during the term**, built from this term's course material. Error-log rows from quiz reviews go to [la-error-log.md](<../la-error-log.md>) (the stream the question belongs to); course facts live in the course card [la.md](<../la.md>).

## Graded assessments of this course

From `_agent/uni-os.toml` (`[[courses.assessments]]`); quiz coaching handles the ones of kind `quiz`.

| Assessment | Kind |
|---|---|
| Online quizzes | quiz |
| Exercise sheets | sheet |

## Quiz facts

Write each fact once, with its date and source (course card, LMS page, announcement, graded paper), and mark what is inferred. Update in place and say when a fact corrects an older one.

- **Format**: <live LMS quiz | written in-class quiz | online quiz tied to a sheet>
- **When**: <day and window; timer per attempt vs hard close of the window ("start by HH:MM")>
- **Questions**: <how many; types: true/false, single choice, select-all, typed number, short proofs>
- **Points and counting**: <points per quiz; best n of m; what it is worth>
- **Attempts, aids, retries**: <one attempt; no aids; retries while open; lateness rule>
- **Scope rule** (official wording, quoted): "<...>". **Mapping** (inferred): <which lectures and sheets that means for the next quiz>.
- **Numbering**: <e.g. LMS "Quiz Week k" = term week k−1; course week k = Friday of term week k−1 + Wednesday of week k>
- **Review source**: <LMS attempt review, saved as HTML/PDF into raw/ | photo of the graded paper | pasted feedback>
- **Mock with the prep sheet**: <only on request | yes> (yes: the `quiz-prep` job and the coach build a timed mock with every prep sheet of this course)

## Planned quizzes

One row per graded quiz still to come, filled when the dates are known (term start or an announcement) and corrected when a quiz moves. The `quiz-prep` job (optional) reads this table; its run dates go into `schedule.quiz_prep_dates` in `_agent/uni-os.toml`. Mark inferred cells *(inferred)*.

| Run date | Quiz (course numbering) | Date and time | Lectures up to | Sheet in scope | File stem |
|---|---|---|---|---|---|

## File formats

### Prep sheet: `la-quiz-<quiz-id>-prep.html` (+ `.md` twin)
HTML from `_templates/study-page.html` when there is maths or quick checks; Markdown from `_templates/quiz-prep-sheet.md` otherwise. Built the evening before or the same morning. Parts, in this order:
1. **Quiz facts box**: format, window, timer vs close, questions, points, attempts (inferred items marked).
2. **Scope in four lines**: *Lectures* (cut-off date, script sections and printed pages), *Sheet/assignment* (which one and why; announced or inferred by the rule), *Not in scope*, *Unknown* (format details nobody announced).
3. **Weighting**: ★★★ the newest lecture ("never asked before, so expect most questions here"), ★★ the one before, ★ older material and the sheets, ★★ always: your trap family (from the error log).
4. **How this quiz asks**: real patterns from your past reviews, `| Pattern | Real example (quiz, Q) | What to do |` (e.g. "options differ by one symbol", "trace a tiny input, type a number", "guaranteed / necessarily / worst case", "what does the number mean?").
5. **Core material** per topic, each item tagged by origin: `Plan W<n>` (the official lecture plan), `S<k> Ex <j>` (used by sheet k, exercise j), `plan only` (lectured but no exercise drills it, so check it yourself), `sheet only` (the exercise needs it but the plan never introduced it), `edge` (possibly not lectured by the cut-off). Each block ends with "In practice: ..." and a traps callout from the error log. The course's exact qualifiers are copied word for word.
6. **Cheat card**: one screen of definitions, formulas, runtimes.
7. **Drill on the weak pattern**: a model from a real graded quiz (this term), then cold tries "under 3 minutes each".
8. **Quick checks**: about 10 questions, answers checked by code, each labelled with its pattern and origin (`invented` / `adapted from ...` / `official: ...`).
9. **Sheet map: hints only** for the sheet in scope.
10. **Last minutes before the quiz**: a three-line do-list (e.g. "open the LMS at HH:MM; on every counting item plug in n = 4").
11. **Sources and checks**: what was read (files, versions, pages), what was not re-read, what is inferred. Optional: a dated prediction.

### Mock quiz: `la-quiz-<quiz-id>-mock[-<n>].html` (only on request)
The real format and timing, built on the study-page engine (a `final` quiz with the timer). For written quizzes: "train at 10, expect 15" (set the clock shorter than the real quiz). Instructions on the page: "Write everything by hand. Don't enter anything until the end. Press Submit (or let the clock run out), then type your results. Computed answers are checked by code; proofs are marked by you against the rubric, the way the TA would." Every problem is labelled `official` (this term's sheets or quizzes), `adapted` (changed numbers from this term's material) or `invented`.

### Review extract: `la-quiz-<quiz-id>-review-extract.md`
A text copy of the saved review so it can be searched and quoted. Header: what it is, who made it, when, where the original is (`raw/...`). Then the student's chosen answers (read from the checked inputs of the saved page), the attempt summary (started, finished, duration, marks), and per question: status, mark, question text, feedback, correct answer. No quiz passwords, no other students' data.

### Review breakdown: `la-quiz-<quiz-id>-review.md`
Skeleton `_templates/quiz-review.md` (`type: quiz-review`): Result (`<got> / <max> = <bonus> of <bonus max> (<pct> %)`, time used, whether the timer ran out), Scope seen (topics with question numbers), Right, Missed (each with the correct idea and the error-log row), Pattern (what the misses share), Lesson for the next quizzes (numbered), Prep fixes (which prep wording misled, fixed how). Then: every miss into the error log, the result into the progress files and the course card, the prep page fixed if needed.

### Raw files: `raw/`
Saved attempt reviews (`la-quiz-<quiz-id>-review-<YYYY-MM-DD>.html|.mht|.pdf`) and photos of graded papers (`...-graded.jpg`), exactly as saved by the student.

## Index

Newest at the bottom. One row per file: `| [file](file) | what | date |`.

| File | What | Date |
|---|---|---|
