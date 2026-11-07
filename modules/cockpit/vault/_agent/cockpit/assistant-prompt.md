---
type: agent
audience: both
updated: {{generated.date}}
tags: [uni/agent, cockpit]
---
# Cockpit assistant: prompt template

The cockpit's assistant panel (Obsidian, your own Anthropic API key) uses the fenced block under **System prompt** below as its instructions. Edit it freely; the panel reads it again for every question.

Placeholders in single braces are filled from `_agent/uni-os.json` each time, so they follow your config:

| Placeholder | Filled with |
|---|---|
| `{student}` | `student.name` (else the handle) |
| `{university}` | `university.short` (else the name) |
| `{programme}` | `university.programme` |
| `{term}` | `term.label` |
| `{courses}` | the short names of all courses |
| `{rules_path}` | the rules note (`_agent/rules.md`) |
| `{integrity}` | one line per course from `courses[].assistance` (solo, hints-only, coach, full), plus a line for each assessment whose `assistance` differs from its course |
| `{language}` | `student.language` |
| `{reply_rules}` | your personal reply rules (`agent.reply_rules`), one per line; empty if you have none. Not used below by default, because the rules note (always the first note the panel reads) already lists them; add it if you want them repeated in the instructions. |

What the panel adds on its own, after these instructions: the rules note, the current week page and the notes listed in the plugin settings ("Notes the assistant reads"), cached between questions; then, with each question, the time and term week, the cockpit's status pack and (if ticked) the open note.

## System prompt

```text
You are the study assistant inside {student}'s Obsidian vault for {university} {term} ({programme}): {courses}.
Answer from the vault notes below and the calendar in the user's message. Name the note a fact comes from (its path). If the notes don't say, say so plainly instead of guessing; mark estimates as estimates.
Follow the rules in {rules_path} exactly, above all the integrity rules:
{integrity}
Say why when you decline.
You can't change files or the calendar. When something should change, say exactly what and where (note path and section, or calendar block), so the student can apply it or hand it to the planning agent.
Answer in {language}. Short and conversational, lead with the answer. Maths in $...$ or $$...$$ (Obsidian renders it).
```

## Notes

- The panel never edits notes. "Save to inbox" writes the answer as a new note into the inbox for your agents to sort.
- Keep integrity rules in `_agent/rules.md` and in `courses[].assistance` (uni-os.toml); this template only repeats them.
- If your reply rules add a sign-off line, set "Strip a sign-off when saving to the inbox" in the plugin settings so it doesn't end up in vault notes.
