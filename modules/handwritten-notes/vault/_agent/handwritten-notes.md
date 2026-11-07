---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Handwritten notes: folder contract and rules

The student writes on a tablet{{#if study.handwriting_app}} with {{study.handwriting_app}}{{/if}}. The app exports each notebook as a PDF into a handwritten folder inside the matching course folder, so handwritten lecture notes, exercise drafts and scratch work sit next to the official files and the notes. Agents may read these PDFs for context. They never write there.

## Where the PDFs are
| Course | Handwritten folder (written only by the app) |
|---|---|
{{#each courses}}| {{course.short}} | `{{course.folder}}/{{course.handwritten_dir}}/` |
{{/each}}

{{#if paths.handwriting_app_exports}}
The app's own export folder: `{{paths.handwriting_app_exports}}/`. Notebooks the app can't map to a course, loose notebooks, and exports made while a course folder was missing or renamed land here. Read-only like the course folders; look here when a file is missing from a course folder (and tell the student that the app's course-folder mapping may need fixing). Its private subfolder, if any, is in `paths.never_open` below.

{{/if}}
{{#if paths.handwriting_app_data}}
App data folder (the app's own sync files): `{{paths.handwriting_app_data}}/`. **Never edit, move, rename or delete anything there**: deleting a file in an app's data folder can delete the notebook on the tablet. Don't read it either; it is not meant for people or agents.

{{/if}}
{{#if paths.never_open}}
Private paths (`paths.never_open`): {{#each paths.never_open}}`{{item}}`{{#unless @last}}, {{/unless}}{{/each}}. **Agents never open, list, search, index or copy anything there.** If the note app has a folder for personal documents, it belongs on this list.

{{/if}}
## Rules
1. **The handwritten folders are written only by the app.** Agents read and link; they never create, edit, rename, move or delete a file there, and never put a README, a transcript or any other file into them. Agent-made material about a handwritten note goes into the course's `notes/` folder.
2. **The app rewrites PDFs in place** whenever a notebook changes, and a deleted notebook's PDF can disappear. A link stays valid but the content may change: date any summary you write ("read Tue 3 Nov 2026, 6 pages") and re-read when it matters.
3. **Reading is allowed for context**: what the student wrote in a lecture, where an exercise attempt stands, which definitions they copied. Say which file and pages you read.
4. **Help policy first.** Before reading a file about an exercise, check the course's assistance level for that work (course card, "Weekly rhythm and bonus"). Work marked `solo` is never transcribed, summarised, checked or stored, handwritten or not. If a file name or date suggests it may contain solo work and you are not sure, don't open it: ask.
5. **No silent transcription.** Don't write full transcriptions of handwritten notes unless the student asks. If they ask, the copy goes into `notes/` as `<slug>-<notebook name>-transcript.md`, says which PDF and pages it came from, marks unreadable parts `[unclear]`, and says "If this copy and the PDF ever differ, the PDF wins."
6. **Link by relative path in angle brackets**, with a page where useful: from a course card, `[Mon lecture notes](<{{#each courses}}{{#if @first}}{{course.handwritten_dir}}{{/if}}{{/each}}/week5mon.pdf#page=2>)`.
7. **Files the student adds by hand.** If the app uses per-file drive access (it only sees the files it created), files the student puts into these folders by hand are safe from the app. Agents still treat the whole folder as read-only.
8. **The app's setup belongs to the student.** Agents never connect the note app to the drive, pick its folders or approve its permission or consent screens on the student's behalf. If PDFs stop arriving, say so and describe the fix; the student does it on the tablet.
9. **Searches and indexes skip the app's folders.** Text indexes, history snapshots and watchers built by other modules leave out the app data folder and the private paths entirely; the handwritten folders may be watched for new files, but changed PDFs there are normal (the app rewrites them) and are not alarms.

## Reading a handwritten PDF
Handwriting PDFs usually have no text layer: text extraction (and cloud drive connectors) return empty text. Read the pages as images instead. The procedure, including a small page-render helper, is in the skill `read-handwritten-notes` (`_agent/skills/read-handwritten-notes/SKILL.md`). In short: find the file, check the help policy, try the text layer once, then render only the pages you need at about 75 dpi (raise it for small writing or dense formulas), read them, and report with page numbers.

## Naming the student uses
Apps name exports after the notebook: a timestamp by default (`YYYY-MM-DD HH-MM.pdf`) or whatever the student called the notebook (`week5mon.pdf`, `lecture-26oct.pdf`, `ex3.pdf`, `hand-in ex3.pdf`, `scratch.pdf`). Some keep an archive subfolder. When the student refers to "today's notes", list the folder by modification time and confirm the file if there is more than one candidate.
