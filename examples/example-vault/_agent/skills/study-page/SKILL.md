---
name: study-page
description: Build a study page for a course (teaching page, lecture skim, rundown, recap, summary, cheat sheet, hint page, quiz-prep sheet, mock quiz) in the formats this vault uses (HTML with KaTeX plus a Markdown twin by default), from the course's real sources, with quizzes checked by code, quality checks, naming, filing and showing the page to the student.
---
# Build a study page

This vault's formats: **html, md** (`study.formats` in `_agent/uni-os.toml`; html = interactive HTML original, md = Markdown, pdf = printed from the HTML). Maths renderer: katex. Section size: about 750 words.

## Rules that are never skipped
1. **Real sources only.** Content comes from the course's actual material: script, lecture slides, official handouts, the official course plan or LMS roadmap. Open the file and cite section and page (or slide) on every subsection. Never fill in from a predicted weekly plan or general knowledge. **If a source can't be opened, say so** instead of filling in (the rule was added after a plan-based page cited wrong pages and invented items). The course card's "Real sources" section lists the files and the page offset (printed page vs PDF page): cite printed pages.
2. **Say what is inferred.** "Not in this version", "the plan predicts", "my own example" are written on the page.
3. **Maths is rendered**, never plain-text maths: HTML with KaTeX, or `$...$` / `$$...$$` in Markdown (never `\(...\)` in Markdown). Never skip "obvious" algebra steps.
4. **In HTML maths, a literal `<` followed by a letter is swallowed as a tag** (`$j<i$` loses everything after `<`): write `\lt` (`\\lt` inside JavaScript strings). The checker finds these.
5. **Label every practice question's origin**: `invented`, `adapted from <where>` or `official: <where>`. "Official" and "adapted" mean this term's official sheets, quizzes or practice material of the course.
6. **Integrity**: a page never contains the finished solution of a current graded task; hint pages give a hint ladder only (see the exercise-help role). Under the `solo` assistance level nothing is built at all.
7. **Intuition and pictures first**, then the precise definitions (the student learns visually; script-first reading is too slow for them).

## Page kinds and names
One naming scheme for every note a course session writes: lowercase kebab-case, **the course slug first, what the page is about next, the kind word last** (`<slug>-<what>-<kind>`). Pages tied to one lecture put `lecture-<ddd><d><mon>` right after the slug, with the day of the month unpadded (`mon2nov`, `wed28oct`). Names stay unique across the vault (no `README.md`, `notes.md`). The extension follows the formats: `.html` original plus a `.md` twin with the same base name, or `.md` only. `html2md.py` reads the kind from the last word when a page has no `uni-os:kind` meta tag, so keep the kind word last.

| Kind (`kind` property) | File name (without extension) | Folder |
|---|---|---|
| teaching-page (full template) | `<slug>-<topic>-study-page` | `<course folder>/notes/` |
| skim (before a lecture) | `<slug>-lecture-<ddd><d><mon>-<topic>-skim` | `notes/` |
| rundown (after a lecture) | `<slug>-lecture-<ddd><d><mon>-<topic>-rundown` | `notes/` |
| recall-key (optional, after a lecture) | `<slug>-lecture-<ddd><d><mon>-recall-key` | `notes/` |
| transcript (from a recorder app) | `<slug>-lecture-<ddd><d><mon>-transcript` | `notes/` |
| recap (several lectures, aimed at a sheet or quiz) | `<slug>-<what>-recap` (e.g. `ad-weeks3-4-recap`, `ad-sheet6-recap`) | `notes/` |
| summary (topic, chapter or several weeks) | `<slug>-<topic>-summary` (e.g. `la-chapter4-summary`) | `notes/` |
| summary: running summary sheet | `<slug>-running-summary` | `notes/` |
| cheat-sheet | `<slug>-<topic>-cheatsheet` | `notes/` |
| walkthrough (a method explained) | `<slug>-<topic>-walkthrough` | `notes/` |
| walkthrough: proof skeletons checklist | `<slug>-proof-skeletons-walkthrough` | `notes/` |
| definitions-deck | `<slug>-definitions-deck` (Markdown) | `notes/` |
| hint-page | `<slug>-sheet<N>-<task>-hints` | `notes/` |
| mistake-map | `<slug>-sheet<N>-mistake-map` (Markdown) | `notes/` |
| quiz-prep / mock-quiz | `<slug>-quiz-<quiz-id>-prep` / `<slug>-quiz-<quiz-id>-mock[-<n>]` / `<slug>-quiz-<quiz-id>-selfstudy` | `<course folder>/quiz-prep/` |

A plain lecture note from `_templates/lecture-note.md` is the bare lecture stem, `<slug>-lecture-<ddd><d><mon>.md`.

## Properties (canonical study-page schema)
```yaml
---
title: "<COURSE SHORT>: <topic>"
type: study-page
kind: teaching-page          # see the table above
course: <course id>          # the id from _agent/uni-os.toml, as on the course card
sources: ["<file> §x.y pp. a-b", "<slides> L5"]
created: YYYY-MM-DD
updated: YYYY-MM-DD          # bump on every edit
audience: me
tags: [uni/<course id>, study-page]
# Markdown twin only (html2md writes these):
source_html: "<page>.html"
converted: YYYY-MM-DD
---
```
In an HTML page the same facts live in `<meta name="uni-os:kind|course|sources|created">` tags; html2md copies them into the twin (any course spelling in the meta tag is mapped to the course id through the config).

## Steps
1. **Sources.** Open every source file you will use. Note section numbers and printed pages. If something can't be opened (too large, login, empty text), say so in the reply and on the page. For scanned or handwritten PDFs read the page images.
2. **Plan the sections.** Split the material into sections of about 750 words with 2-4 subsections, one demo or visual and one mid quiz each. The number of sections follows the material (a page that is too small is a common miss: aim slightly larger rather than smaller). Mark sections the course calls optional or non-examinable.
3. **Build.**
   - HTML (formats include `html`): copy `_templates/study-page.html` and follow the authoring notes at its top: meta tags, accent colour, nav in sync with the sections, a source chip on every `<h3>`, cards (`card key` definitions, `card trap` pitfalls, `card proc` procedures), demos, mid quizzes (mode `instant`), cheat sheet ("Mistakes this topic invites" from the course's error log, "Procedure to practise"), final self-test (mode `final`, optional timer), footer naming every source and the build date. Put the topic's real algorithms or formulas in `//<CORE>` and compute answers and wrong-option explanations with them. Question types: true/false, single choice, select-all (partial credit), typed number (tolerance, comma, fractions), typed formula in n (checked against computed values), self-marked proof with a rubric.
   - Markdown only (formats = `md`): copy `_templates/study-page.md`; same structure as a Markdown note. Callouts `> [!note]` (definitions), `> [!warning]` (traps), `> [!example]`, and self-checks as collapsible `> [!question]- Question 1` callouts with the answer inside. Say at the top that answers are not checked by code.
4. **Check** (HTML): `python _agent/tools/check_study_page.py <page.html>` must report 0 errors (`--fix` rewrites `<` before a letter in maths; `--katex` also renders every formula if Node and the katex package are available). Open the page once if you can: the template shows a red banner when a formula fails to render or KaTeX did not load.
5. **Twin** (formats include `html` and `md`): `python _agent/tools/html2md.py <page.html> --obsidian` writes `<page>.md` next to it, with Obsidian callouts (cards as `> [!note]` / `> [!warning]`, answers and hints as collapsible `> [!info]-` / `> [!tip]-` callouts). Without the flag the converter reads `obsidian.enabled` from the vault config itself. If you can't run Python (e.g. a create-only cloud agent), say so: the next session or sync job that can, makes the twin.
6. **PDF** (formats include `pdf`): `python _agent/tools/html2pdf.py <page.html> --browser auto` (headless Chrome, Edge or Chromium; needs internet for KaTeX). Without a Chromium browser: print from the browser (Save as PDF), or Obsidian "Export to PDF" for Markdown.
7. **File it.** Add one row to the course card's "In this folder" table: `` [<name>](<notes/<page>.md>) · [interactive HTML](<notes/<page>.html>) | <one line: what, date, which role made it> ``.
8. **Show it.** Give the student the page so they can open it at once, also on the phone. In Claude Code: send the HTML with `SendUserFile` (`display: "render"`). Other agents: give the vault path (and open it in the browser if you can).
9. **Daily prep.** If the page fills a gap listed in today's or tomorrow's prep note (`semester/prep/`), say so in the reply. Never edit prep notes.

## Quality checklist before showing
- Every subsection cites a real source with a printed page; nothing invented is presented as course content.
- Every number in a quiz answer comes from code or was checked by hand on the smallest cases.
- Prep and quiz wording keeps the course's exact qualifiers ("in the worst case", "for all n"): a dropped qualifier once caused a wrong quiz answer.
- Phone width, dark mode, no horizontal scrolling outside tables and formulas.
- The checker reports 0 errors; the twin exists; the card row exists.
