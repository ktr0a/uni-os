---
type: overview
audience: both
updated: 2026-11-07
tags: [uni/prep]
---
# Daily study prep: the contract

The rule: **every day, the material for the next day's study blocks is in one fixed place**, the note `semester/prep/prep-YYYY-MM-DD.md` in this folder, and the same links are appended to each study block in the calendar. The cockpit shows the note as its Prep card. This page is the format contract for everything that writes or reads these notes; the step-by-step routine is [`_agent/daily-prep/RUNBOOK.md`](../../_agent/daily-prep/RUNBOOK.md). Where the two differ on format, this page wins.

## The chain
1. **Plan & progress** puts the study blocks into the "Study blocks" calendar (title in block notation, a `FOCUS:` line in the description) and writes the week plan with a "Material per block" section.
2. **Course sessions** save the study pages a block needs in `<course folder>/notes/` (and quiz-prep pages in `quiz-prep/`).
3. **The prep jobs** write the note and the MATERIAL lines:
   - `daily-study-prep` at 17:30, 19:30: the first run prepares **tomorrow** in full; every later run is a change check for tomorrow.
   - `study-prep-morning-check` at 07:30: verifies **today's** note against the calendar and the disk, and repairs it with a new revision.
4. **Readers:** you (Obsidian, or the calendar on your phone), the cockpit (today's note before its switch time, tomorrow's after it), the heartbeat (planned blocks, prep presence).

## Rules for this folder
- **Written only by the prep jobs** (or an agent following the runbook by hand). Nobody else creates, edits, moves, renames, merges, archives or deletes files here: dashboards read them in place, and old notes are the history.
- **A note for every day**, also days without study blocks (then the body says so and there are no callouts). A missing note is what raises the alarm, so a free day must still have one.
- **Ready in time:** tomorrow's note exists within 30 minutes after the first evening run; dashboards warn when tomorrow's note is still missing after the last evening run, and when today's is missing after the morning check.
- **Never edit a note.** A change after a note was written (a moved block, a gap filled, a broken link) is a new file `prep-YYYY-MM-DD-r2.md`, then `-r3`, and so on. The plain name is revision 1. **The highest revision wins**; with equal revisions, the latest `generated` wins. (In the original, cloud writers could only create files, never change them; immutable revisions also keep the history readable.)

## The format (parsed: keep it exact)

The example is a Thursday of the framework's fictional example student (courses AD, DM, LA); your folders, classes and blocks differ, the shape doesn't.

```markdown
---
type: prep
audience: me
date: 2026-11-12
generated: 2026-11-11T17:31+01:00
run: "17:30"
status: ready
tags: [uni/prep]
---
# Prep for Thu 12 Nov 2026 (week 8)

Written by the 17:30 run. Two study blocks and two classes: a morning block before the AD lecture, the deep block at 13:15, then the LA exercise class.

> [!dm] 08:15-10:00 DM_ practice sheet 8
> - First 15 min: open-notes recap of the definitions: [dm-lecture-wed11nov-groups-rundown](../../DM/notes/dm-lecture-wed11nov-groups-rundown.md)
> - Sheet: `DM/DM assignments/sheet08.pdf` (practice sheet, hints only)

> [!ad] 10:15-12:00 L: AD
> - Script chapter 6 (predicted by the topic plan; PDF page = printed page + 2): `AD/AD slides & script/script.pdf`

> [!ad] 13:15-16:00 AD_ Sheet 7 rest (deep)
> - Sheet: `AD/AD assignments/sheet07.pdf` (tasks 7.3-7.5, due today 23:59; hints only, no solution of an identical older task)
> - Study page: [ad-dynamic-programming-study-page](../../AD/notes/ad-dynamic-programming-study-page.md), interactive `AD/notes/ad-dynamic-programming-study-page.html`

> [!la] 16:15-18:00 E: LA
> - Exercise class: sheet 8 is discussed: `LA/LA assignments/sheet08.pdf`

## Gaps
- none
```

**Properties:** `type: prep`; `audience: me`; `date` = the day being prepared (ISO); `generated` = when this file was written (ISO with offset); `run` = the nominal slot of the run that wrote it (`"HH:MM"`, quoted) or `manual`; `status` = `ready` or `ready-with-gaps`; `tags: [uni/prep]`.

**Title:** `# Prep for <Ddd D Mon YYYY> (week N)`, N the term week (week 0 = Mon 2026-09-14).

**First paragraph:** which run wrote it and why this revision exists ("Revision 2, written by the morning check: the sheet arrived in the vault yesterday evening, the gap is closed"), how many blocks, and the non-study events around them.

**Callouts, one per block, in time order:**
- Header exactly `> [!<course>] HH:MM-HH:MM <title>`: `<course>` is the course's callout id (`ad` for AD, `dm` for DM, `la` for LA, `prog` for PROG, anything else such as `[!note]` shows without a course colour); 24 h times with leading zeros; `<title>` exactly as in the calendar.
- **The start time equals the calendar event's start, the end its end.** Agenda views match items to events by date and start time; a different time loses the match. Take both from the calendar at run time, never from the plan.
- Lectures and exercise classes of the day get a callout too (the script chapter or slides only).
- A block about two courses takes the course of its main subject (the `X_` part of the title).

**Items:** one `> - ` line each, continuing lines also start with `> `.
- Vault notes as relative links from this folder: `[name](../../<course folder>/notes/<note>.md)`; wrap a path with spaces or `&` in angle brackets: `[name](<../../A&D/notes/x.md>)`.
- HTML study pages as a backticked vault path: `` `<course folder>/notes/<page>.html` `` (dashboards make it clickable; Obsidian opens HTML in the browser).
- PDFs and other files as a backticked vault path, plus a cloud-storage link as a phone fallback when one is already known.
- Time splits inside the item ("13:15-14:25 tasks 7.3-7.4; break; 14:35-16:00 task 7.5").
- **Integrity warnings stay in the item:** "task 6.1 only; the same PDF holds bonus task 6.3: don't read it", "solo, no AI help", "sheet only".

**`## Gaps` is the last section:** one `- ` line per missing item with its fallback, e.g. `- AD sheet 8 not in the vault yet (released today 12:00); fallback: download it from the LMS before the block`, or exactly `- none`.

Prose in English (the title, headings, callout headers and dates keep the exact format above); no reply sign-off tokens, emails, secrets or calendar addresses.

## The MATERIAL block in the calendar
Each study block of the day in "Study blocks" gets, as the **last** block of its description:

```
MATERIAL (daily prep, Wed 11 Nov 17:31; all of it in Obsidian: semester/prep/prep-2026-11-12)
- Sheet: AD/AD assignments/sheet07.pdf (tasks 7.3-7.5, due today 23:59; hints only)
- Obsidian AD/notes/ad-dynamic-programming-study-page.md
- PENDING: <a gap, if there is one> (fallback: <the fallback>)
```

- The header names the newest note (without `.md`) and when it was written.
- One line per item; gaps as `PENDING:` lines with their fallback.
- It is always the last block; a new run replaces only this block and keeps everything above it (the planner's tasks and `FOCUS:` line) byte for byte.
- Classes in "Courses" are never edited.

## If you change something upstream
- **Planner:** moving or adding a block for today or tomorrow after the first evening run means a rerun (today: the morning check; tomorrow: the daily prep); otherwise the next change check or the morning check catches it. Keep "Material per block" in every week plan.
- **Course sessions:** when a page listed under Gaps is ready, save it in the course's `notes/` folder and say so in your reply; the next run drops the gap.
- **Anyone changing this format:** first change the parsers that read it (the cockpit plugin's prep parser and its tests), then this page and the runbook.
