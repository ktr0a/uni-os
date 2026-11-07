---
type: reference
course: algo
audience: both
updated: 2026-11-07
tags: [uni/algo]
---
# AD notes: what goes here

This folder holds everything the student and the agents write to learn Algorithms and Data Structures: study pages, lecture notes, summaries, cheat sheets, walkthroughs. Official files never go here (they stay in the course's official subfolders); tablet exports never go here either.

## What belongs here
Names follow one scheme: `ad-<what>-<kind>`, the course slug first and the kind word last; pages tied to one lecture put `lecture-<ddd><d><mon>` after the slug (`mon2nov`, `wed28oct`: the day of the month unpadded). Study pages exist as an `.html` original, a `.md` twin with the same base name, or one of the two, depending on `study.formats` in `_agent/uni-os.toml`; the `study-page` skill has the full list.

| Kind | Example name | What it is |
|---|---|---|
| Study page | `ad-<topic>-study-page.md` | Teaching page for one topic: chunks, examples, checks, cheat sheet, final self-test |
| Lecture skim (before a lecture) | `ad-lecture-<ddd><d><mon>-<topic>-skim.md` | Intuition first, what the plan predicts for the lecture, cited sections and pages; the official roadmap wins |
| Lecture rundown (after a lecture) | `ad-lecture-<ddd><d><mon>-<topic>-rundown.md` | What the lecture actually reached, with pages, examples and traps |
| Lecture note (your own, after a lecture) | `ad-lecture-<ddd><d><mon>.md` | What was covered, key definitions, open questions (from the lecture-note template) |
| Lecture transcript | `ad-lecture-<ddd><d><mon>-transcript.md` | From a recorder app: wording unchanged, `[mm:ss]` timestamps; check coverage against the recording length |
| Recap | `ad-<what>-recap.md` (e.g. `ad-weeks3-4-recap.md`) | Several lectures compressed, aimed at a sheet or a quiz |
| Summary | `ad-<topic>-summary.md` (running sheet: `ad-running-summary.md`) | A topic, chapter or several weeks: statements and procedures with pages, no explanations |
| Cheat sheet | `ad-<topic>-cheatsheet.md` | One page: every definition and result with its page, plus your own traps; no task solutions |
| Walkthrough or method guide | `ad-<method>-walkthrough.md` | How a technique works (e.g. invariants, lower bounds, proof skeletons) |
| Definitions deck | `ad-definitions-deck.md` | Exact wording quoted from the script with pages, for daily recall |
| Hint page | `ad-sheet<n>-<task>-hints.html` | The hint ladder for one task, rungs opening in order; never the answer |
| Mistake map (after a hand-in) | `ad-sheet<n>-mistake-map.md` | Locates and explains mistakes against the real sheet; the fixes are for the student to write |

## Rules
- Names are lowercase-kebab-case and start with `ad-`, so they stay unique across the vault. The kind word comes last (the converter reads the page kind from it).
- Content comes only from real sources (script, slides, official handouts, the LMS roadmap), with section and page cited. If the real source can't be opened, the page says so instead of filling in.
- Label which practice tasks are real (from an official sheet or quiz of this course) and which are invented.
- Help policy: graded work marked `solo` for this course is never solved, hinted or summarised in a note here. Explaining a technique on a different example is fine.
- Every new file gets one row in the course card's "In this folder" table ([ad.md](<../ad.md>)).
- Frontmatter on every note: `type` (e.g. `study-page`, `lecture-note`), `course: algo`, `audience`, `updated` or `created`, `tags: [uni/algo, ...]`. Dashboards filter on these.
