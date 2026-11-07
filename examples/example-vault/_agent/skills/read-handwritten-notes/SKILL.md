---
name: read-handwritten-notes
description: "Find and read the student's handwritten notes: PDFs a tablet note app exports into each course's handwritten folder. Use when the student refers to their handwritten or tablet notes, lecture notes they wrote, or an exercise attempt they wrote by hand. Reads pages as images when there is no text layer; never writes into the handwritten folders."
---

# Reading handwritten notes

The tablet app (GoodNotes) exports notebooks as PDFs into one folder per course:
- AD: `AD/AD handwritten/`
- DM: `DM/DM handwritten/`
- LA: `LA/LA handwritten/`
- PROG: `PROG/PROG handwritten/`

The folder contract and the rules are in `_agent/handwritten-notes.md`. The short version: read and link, never write, never touch the app's data folder, never open private folders, and never touch `solo` work.

## Procedure
1. **Find the file.** List the course's handwritten folder by modification time. Exports are named after the notebook: a timestamp by default (`YYYY-MM-DD HH-MM.pdf`) or the student's own name (`week5mon.pdf`, `ex3.pdf`). If more than one file could be meant, ask which one before reading.
2. **Check the help policy.** Read the course card's "Weekly rhythm and bonus" table. If the file may contain work marked `solo`, stop and ask; never transcribe, summarise or check solo work. For `hints-only` work, reading the attempt to point at a wrong line is fine; writing the solution is not.
3. **Try the text layer once.** Most handwriting PDFs have none (extraction and cloud drive connectors return empty text). Typed PDFs exported by the app do have one.
4. **Read the pages as images.** Render only the pages you need:
   - In Claude Code: the Read tool opens a PDF directly and shows the pages as images; pass a page range (`pages: "1-4"`) for long notebooks. If that is not available, render PNGs (next point) and read those.
   - Any agent with Python: `python scripts/render_pages.py "<pdf>" --pages 1-4 --dpi 75` (this skill's folder) writes PNGs to a temporary folder outside the vault and prints their paths. It uses PyMuPDF if installed (`pip install pymupdf`), otherwise `pdftoppm` (poppler) if found, otherwise it says what to install.
   - 75 dpi is enough for normal handwriting and keeps images small; use 110-150 dpi for small writing, dense formulas or diagrams. Never write rendered images into the handwritten folder.
5. **Read carefully and say what you read.** Name the file and pages. Mark anything you can't read as `[unclear]` and ask instead of guessing, especially in formulas (a misread index or sign changes the maths). Lecturers' handwritten slides read badly too: same procedure.
6. **Put results in the right place,** only if the student wants them kept: a summary or the stop point of a lecture goes to the course card's Lecture log; a study note goes into `notes/`; a requested transcription goes into `notes/<slug>-<notebook name>-transcript.md` with its source PDF and pages, `[unclear]` marks, and the line "If this copy and the PDF ever differ, the PDF wins." Date anything you write: the app rewrites PDFs when a notebook changes.

## Never
- Create, edit, rename, move or delete anything in a handwritten folder or in the app's data folder.
- Open, list, search or index a private folder.
- Transcribe, summarise, check or store handwritten work on `solo` graded tasks.
- Leave rendered page images inside the vault.
