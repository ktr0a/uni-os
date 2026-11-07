---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent]
---
# Obsidian setup for this vault (for agents)

How to finish setting up Obsidian for Alex Example's vault, and how to keep it in shape. Uni OS installs the views (`views/*.base`, `views/vault-map.canvas`) and the CSS snippet (`.obsidian/snippets/uni-os.css`) directly, but it **never overwrites Obsidian's own settings**: graph colours, bookmarks and app settings are rendered into this folder as files to merge.

| File here | Merges into | What |
|---|---|---|
| `graph-groups.json` | `.obsidian/graph.json` | one colour group per course folder and area, as anchored path regexes; the graph search filter that hides `_agent/`, `_templates/` and `reference/` |
| `bookmarks.json` | `.obsidian/bookmarks.json` | Home, status, dates, course cards, student model, views, the agent start page |
| `app-settings.json` | `.obsidian/app.json`, `templates.json`, `core-plugins.json`, `appearance.json` | relative Markdown links that update on rename, new notes and attachments into `inbox/`, HTML files visible, ignore filters, the templates folder, the core plugins Uni OS uses, the `uni-os` CSS snippet |

## First-time setup (step by step)
1. Alex Example installs Obsidian (version 1.9 or newer: Bases views need it) and opens the vault folder as a vault ("Open folder as vault"). Opening it once creates `.obsidian/`.
1. Alex Example closes Obsidian again. (Obsidian keeps its settings in memory and may write them back when it closes, undoing a merge made while it runs.)
1. Show the plan, from the framework folder:
   `python modules/obsidian/scripts/merge_obsidian_config.py --vault "<vault path>"`
   It prints one line per change: `+` added, `!` kept because Alex Example already chose something else, `-` skipped (e.g. a bookmarked note that doesn't exist yet).
1. Read the plan to Alex Example in a few lines and ask for a yes. Then run it again with `--apply`. Every changed file is backed up first to `.obsidian/uni-os-backup-<timestamp>/`. Only with an explicit yes per setting, add `--overwrite` to replace values they set differently.
1. Alex Example reopens Obsidian. Check together: Home shows the course table and the tiles in course colours; Settings > Appearance > CSS snippets lists `uni-os` switched on; the graph view colours course folders; the bookmarks sidebar has the Uni OS entries; new notes land in `inbox/`.
1. Restricted mode can stay on: Uni OS needs no community plugin. The optional cockpit is a community-style plugin installed from the framework (see the cockpit module); it needs restricted mode off.

**Without the script** (manual merge): Graph view > Filters/Groups: add one group per line of `graph-groups.json` with the query `path:/^<folder>\//` (escape regex characters in folder names; write spaces as `\s`). Bookmarks: right-click each note > Bookmark. Settings > Files and links: `Use [[Wikilinks]]` off, "New link format" relative, "Automatically update internal links" on, "Default location for new notes" `inbox`, "Default location for new attachments" `inbox/attachments`, "Detect all file extensions" on, and add the ignore filters under "Excluded files". Settings > Core plugins > Templates: folder `_templates`.

## When something changes
- **A course added, renamed or recoloured:** edit `_agent/uni-os.toml`, re-render (`python tools/uni_os.py render`), then run the merge again (it only adds the new groups and bookmarks; an old group for a renamed folder stays until Alex Example removes it in Graph view).
- **A folder moved:** move notes inside Obsidian so links update; then fix the folder name in the config and re-render.
- **Views look empty:** the notes lack the `type` property the view filters on (see `_agent/CONVENTIONS.md` section 4), or Obsidian is older than 1.9.

## Quirks (verified in the original system)
- Bases columns for frontmatter properties need the `note.` prefix in `properties:` (`note.bonus_banked`); a plain key only renames `file.*` columns.
- Custom callout colours: some versions ignored `--callout-color` for custom callout types, so the snippet sets background, border and title colours explicitly.
- Graph colour queries must be anchored regexes: `path:me` also matched every other path containing "me".
- Canvas: text cards with `[[path|Title]]` links; small file cards only show a clipped title.
- Obsidian reformats `.base`, `.canvas` and `graph.json` when it opens them. Harmless.
- Excluded files are hidden from search, graph and link suggestions, not from the file explorer.
- Deleted or moved files stay in Obsidian's index for minutes: scripts must read the disk.
- Never edit `.obsidian/workspace.json` or a plugin's `data.json`; they hold per-device state and, for plugins, possibly secrets.
