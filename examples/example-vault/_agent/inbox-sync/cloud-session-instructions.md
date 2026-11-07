---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent, inbox]
---
# Standing instructions for create-only cloud sessions

Cloud agent sessions work with the laptop off, but they reach the vault only through a storage connector that can **create** files and not change them. This page holds the standing instructions they need. The setup agent copies the block below into:

- **Claude Code cloud sessions:** a small private git repository used only as their workspace (cloud sessions need a git repository; the vault is not one). The repository holds just the block below as `AGENTS.md` (plus a `CLAUDE.md` containing `@AGENTS.md`) and `.claude/settings.json` with `{"permissions": {"defaultMode": "acceptEdits"}}` (cloud sessions can't use bypass mode). Start each role's cloud session on that repository with the role's exact title.
- **A chat project with a storage connector** (the original's first runtime): paste the block into the project's instructions. One-time setting: allow the connector's "create file" action always, or every note waits for an approval click.
- **Any other create-only agent:** its system prompt or instructions file.

Replace `<vault folder name>` and `<inbox folder id>` when you copy it (ids stay out of the vault on purpose).

---

```markdown
# EIT Autumn 2026: cloud workspace for Alex Example's study system

This workspace holds no study material. The only store is Alex Example's vault, the storage folder "<vault folder name>", which you reach only through the storage connector (Google Drive by default). Don't write study material, notes or logs into this repository and don't push branches for them.

## Start of every session (and after a context compaction)
1. Read from the vault with the connector (find a file by its exact title or by listing its parent folder, then read its content): `_agent/agent-start.md`, `_agent/rules.md` (non-negotiable), `_agent/roles/README.md` (sections "Common rules" and "Cloud sessions and other create-only writers"), your role brief `_agent/roles/<role-id>.md`, and your course card. Re-read them when unsure; they change. Where anything you remember disagrees with the vault, the vault wins.
2. Get the real date in Europe/Zurich (`TZ=Europe/Zurich date`) and the term week (week 0 starts Mon 2026-09-14; week n starts 7n days later). Convert every UTC time to Europe/Zurich before you write it anywhere.
3. If the `course-facts` skill is available, load it; otherwise read `_agent/skills/course-facts/SKILL.md` from the vault.

## Your role
Your session title names your role: "<COURSE> · <Role>" means the brief `_agent/roles/<role-id>.md` for that course. Course cards:
- AD: `AD/ad.md` (assistance: hints-only)
- DM: `DM/dm.md` (assistance: hints-only)
- LA: `LA/la.md` (assistance: hints-only)
- PROG: `PROG/prog.md` (assistance: coach)

## Rules that matter most
- Reply rules (language, personal rules) are in `_agent/rules.md`.
- Assistance levels per course are absolute: `solo` means no help of any kind; `hints-only` means hints, never the full solution. Timed graded windows get no help at all. Keep the course's error log current without being asked.
- Content only from real sources (script, slides, handouts), cited with section and page.
- Logged-in course pages are read-only; never enter the student's password; no emails, keys, tokens or private calendar addresses in any file.

## Saving (you can create files but not edit existing ones)
- **New files** (study pages, hint pages, quiz pages): create them straight in the target vault folder with conversion to Google formats turned off (`disableConversionToGoogleType: true`), only if no file of that name exists there. For an HTML page also make its Markdown twin if you can; otherwise the sync makes it.
- **Changes to existing files** (error-log rows, course-card lines, results, backlogs): ONE update note per turn into the vault's `inbox` folder (parent `<inbox folder id>`), title `YYYY-MM-DD_HHMM_<sender>-update.md` in Europe/Zurich local time, mime type `text/markdown`, conversion off. Name each target file and give the exact lines to append; for a replacement, read the vault file first and quote the current line exactly. The full format: `_agent/inbox-sync/README.md`.
- **Requests for other sessions** (a replan or calendar change, a block report, a prep gap): in the same note under `## For <session title>`.
- The job `inbox-sync` applies notes and forwards those sections, usually within about an hour inside the window 07:00-22:00; a note written later is applied at the next fixed run (07:15, 13:15, 18:15). You can't message other sessions: when something has to wait for the sync, say so in one line.
- To find a file, list its folder and filter yourself (title-contains searches return wrong files). Long files may come back cut off: say so instead of quoting a part you didn't see.
```
