---
type: agent
audience: agent
updated: 2026-11-07
tags: [uni/agent, cockpit]
---
# Cockpit (Obsidian plugin): notes for agents

The community plugin **Uni OS cockpit** (`.obsidian/plugins/uni-os-cockpit/`; source and build in the framework repo under `modules/cockpit/plugin/`) shows a calm study dashboard inside Obsidian: Home (Focus, Dashboard or Agenda layout), Week and Courses, a one-line banner (the ```` ```uni-os-cockpit ```` block at the top of `Home.md`), and an optional assistant side panel on Alex Example's own Anthropic API key. Human guide: the cockpit page of the framework docs (`modules/cockpit/README.md`).

It **reads** the vault. Keeping the notes right keeps the cockpit right. It writes only three things:
1. a **Done tap** or its **Undo**: a new update note in `inbox/` (format below), never an edit of the week page;
2. **Save to inbox** in the assistant panel: a new note in `inbox/`;
3. the **calendar snapshot** `_agent/cockpit/calendar-snapshot.json`, rewritten from the live calendar feeds when they change (only if that setting is on).

Its course list, colours, paths, schedule times and vocabulary come from `_agent/uni-os.json`, which `python tools/uni_os.py render` writes from `_agent/uni-os.toml`. After changing courses or times in the TOML, run the render (the plugin reloads the JSON by itself when it changes). Its own UI settings live in `.obsidian/plugins/uni-os-cockpit/data.json` (no secrets: the API key and the iCal addresses stay in Obsidian's secret storage on each device, and only their names are saved there).

## What it reads (keep these formats exact)

The headings, column names, status words and date shapes below are a contract between the cockpit and the agents that write these notes. Rename one only together with the matching `[cockpit]` key in `uni-os.toml`.

| Cockpit part | Source and format |
|---|---|
| Due this week | The week page in `progress/weeks/` with `type: week` and `status: current` (highest `week` wins; else `week-NN.md` for the term week). The first table under `## Due this week`, columns found by header words: Item, Official deadline, a personal target column (e.g. "Personal target" or "Sunday target"), Bonus, Status. Deadlines must look like `Tue 3 Nov 23:59`, `Tue 3 Nov 13:15-15:00` or `Sun 8 Nov` (English day and month abbreviations; a date without a time means 23:59; the year is inferred, so leave it out). |
| Status rules | Only a Status cell that **starts with** a score (`3/4`, `2.5 / 4`) or one of: ✓, done, submitted, closed, handed in, uploaded, dropped, skipped counts as done; so `task A done 2/2; task B open` stays open. Any of not reported, pending, not recorded anywhere means waiting for a result (never overdue). A deadline that starts with tutorial or contains (tentative) is soft: never overdue, never urgent. A row whose Bonus cell is empty or starts with none, no, feedback only moves to the done fold as "passed" once its date is over, finished or not; a row with a bonus stays red until someone closes it. A range counts down to its start, shows "running until HH:MM" during it, and is past only after its end. A past target date isn't shown. A status containing not released gets no Done button. |
| Week tab | The same week page's `## Results this week`, `## Notes` and `## End-of-week check-in` (a day in brackets after the last one is fine), shown folded under the week grid; the plan link is `semester/plans/week-NN-plan.md` if it exists. |
| Status snapshot, After this week, Done vs. to do, Self-rated | `progress/current-status.md`: the bold line `**Snapshot: ...**`; the table under `## Next 10 days` (columns When, What; any "Next N days" heading works); the section whose heading starts with `Exercises` (by default `## Exercises: done vs. to do`) with one `### <course short name>` subsection per course; the first line of the section whose heading starts with `Self-rated` (by default `## Self-rated understanding`), parts separated by ` · `, each like `LA ~80 %` or `LA 80-85 %`. |
| Bonus tiles and meters | The course cards' properties `bonus_banked` (the first `x / y` pair is read: banked / graded so far, or banked / total), `bonus_target` (for threshold courses, `~N pts` is read as the estimated total), `next_bonus`. The maths comes from `[courses.bonus]` in uni-os.toml (scheme AD: `threshold`, DM: `points`, LA: `best-n`, PROG: `none`). Course cards: `AD/ad.md`, `DM/dm.md`, `LA/la.md`, `PROG/prog.md`. |
| Today, Week, Next up | The live iCal feeds linked in the plugin settings; calendars without a feed come from the snapshot below. |
| Prep card | The newest `semester/prep/prep-YYYY-MM-DD[-rN].md` for today (until 18:00) or tomorrow (from then on): highest `-rN` wins, then the latest `generated`. One callout per calendar block, `> [!<course>] HH:MM-HH:MM <block title as in the calendar>`, where `<course>` is the course slug (`ad` for AD, `dm` for DM, `la` for LA, `prog` for PROG; the id or short name work too; anything else means no course), then `> - item` lines; Markdown links and `code` vault paths become one-click links. A `## Gaps` list becomes the gap count. The callout start time must equal the calendar event's start (the Agenda matches prep items to events by date and start time). |
| Assistant context | `_agent/rules.md` first, then the current week page, then the notes listed in the plugin settings (by default `progress/current-status.md`, `courses-overview.md`, every course card, `semester/planning-system.md` and `me/weak-spots.md`, the ones that exist). Its instructions: `_agent/cockpit/assistant-prompt.md`. |

## Done button and freshness

- **Why rows look late:** the cockpit redraws every 60 s and reads the notes in milliseconds; a file written elsewhere reaches Obsidian within about a minute of syncing. The real delay is the notes: a row changes only when an agent edits the week page, or at the next inbox sync (07:15, 13:15, 18:15) for update notes.
- **Done tap:** the row moves to the done fold at once, with 10 s to undo; then the plugin writes `inbox/YYYY-MM-DD_HHMM_cockpit-done-<slug>-update.md` (`<slug>`: the item in lower case, `&` dropped, other non-alphanumerics as `-`, at most 32 characters; a second note in the same minute gets `-2` before `-update.md`):

```markdown
---
type: inbox-update
from: Uni OS cockpit in Obsidian (Done tap by Alex Example)
created: YYYY-MM-DD HH:MM (Europe/Zurich)
tapped_at: <ISO time, UTC>
done_item: "<item text exactly as in the week page>"
---
# Done tap: <item>

Alex Example tapped Done on this item on <Ddd D Mon HH:MM>. Apply this before any later undo note for the same item.

## <week page path>
Section "Due this week", the row whose Item cell is `<item>`: change only its Status cell. Put `done (<Ddd D Mon HH:MM>, tapped). Before: ` in front of what the cell says now (if it is empty, write just `done (<stamp>, tapped)`). If the Status cell already starts with `done`, change nothing. Change nothing else. The tap says the item is finished, not how it went, so add no score or result.
```

- **Undo at any time:** in the notice for the first 10 s (nothing written yet); later with the undo icon on the tapped row. The row reopens at once and a `..._cockpit-undo-<slug>-update.md` note follows (property `undo_item`, title `# Undo of a Done tap: <item>`, "Apply this after any earlier Done-tap note for the same item"), telling the applier to put back what follows `Before: ` (or `open` if nothing follows) **only if** the Status cell starts with `done (` and contains `tapped)`; without that mark it changes nothing.
- **Applying them (the inbox sync):** oldest `tapped_at` first; per item the latest note wins (tap, undo, tap again all work); change only that item's Status cell on the current week page; anything else in such a note is parked. These notes are rule-based with no quoted row, so an edited row can't park them. A tap marks the row done even if the row says part of it is still open: that is what a tap means. Keep the `_cockpit-(done|undo)-` part of the file name: the sync's filter matches it, so a tap alone does not trigger a sync run, and it gets a longer grace period (the original used 14 h) before a "stuck note" alert.
- **Until the applier runs,** the waiting notes themselves mark the row as tapped, on every device. The plugin reads `inbox/` **from disk**, not from Obsidian's index: the index can keep a deleted note for minutes.

## Refreshing the calendar snapshot

`_agent/cockpit/calendar-snapshot.json` is a read-only copy of the calendar for this week and next, for any agent and for devices without live feeds. If the plugin's live feeds are linked and "Keep the vault's calendar snapshot up to date" is on, the plugin rewrites it whenever the calendar changes. Otherwise an agent with calendar access (a calendar connector or API) refreshes it: list the events of the calendars "Courses" and "Study blocks" (and "Events" / "Busy" as busy time) from Monday of this week to Sunday of next week, and write:

```json
{ "generated": "<ISO time>", "source": "<who wrote it, how>", "range": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "events": [ { "cal": "courses", "title": "L: LA", "start": "<ISO with offset>", "end": "<ISO with offset>", "location": "...", "desc": "..." } ] }
```

Rules: `cal` is the calendar's id: `courses`, `study_blocks`, `events` or `busy` (or the id of a calendar added in the plugin settings). Strip email addresses from descriptions. Busy-only calendars (`events`, `busy`) go in with title `"Personal"` and no location or description. All-day events get `"allDay": true`. The cockpit warns when the snapshot is older than 2 days or today is past `range.end`. Rewrite it only when something changed, or when it is about to go stale.

How the cockpit reads events: on the classes calendar a title starting with `L:` (or matching `^(?:V|L):`) is a lecture, `E:` (or `^(?:U|Ü|E):`) an exercise class, anything else a graded fixture (shown striped). On study calendars the course is the comma-separated segment containing `_` (block notation `LA_ mock A`), else the first course named; titles matching `^\(|^OP\b` are optional, `\bdeep\b` marks deep blocks; the lines after `FOCUS:` in the description are the block's focus (bullets stripped, at most 6; else its first line).

## Live calendar

- The plugin reads private iCal addresses (Google's "secret address in iCal format", Outlook's ICS link, ...) every 10 minutes while Obsidian is open and keeps the last good copy on the device for offline use.
- The addresses live only in Obsidian's secret storage on each device, never in the vault. **Agents never copy, type or ask for these addresses** (they work like passwords); the student links them in Settings → Uni OS cockpit → Live calendar.
- "Check the feeds" in the settings compares each feed with the snapshot: a cheap correctness check against the calendar connector's data.

## Study prep card

The daily-prep jobs (17:30, 19:30, morning check 07:30) write the prep notes. The cockpit shows today's note until 18:00 and tomorrow's from then on, with a presence line ("Prep for Wed 28 Oct: ready, 2 gaps · 18:16 · open note"). It turns orange when tomorrow's note is still missing after 19:30, or today's is missing although earlier days had one ("the morning check will try again" until 15 minutes after the morning check, then "didn't produce one either"). Old notes stay; nothing is deleted. If the schedule moves, change `schedule.daily_prep` / `schedule.prep_check` in uni-os.toml and render: the card's texts follow. The card exists only while `daily-prep` is in `modules.enabled`: after `python tools/uni_os.py disable daily-prep` the cockpit hides the card, its presence line and its warnings.

## Changing the plugin (laptop session)

- Work in the framework clone (`modules/cockpit/plugin/`), never inside the synced vault: `npm install` there would sync `node_modules`.
- `npm install`, `npm test` (parsers against synthetic fixtures), `npm run check`, `npm run build` (writes `modules/cockpit/dist/` and the module's vault copy); `npm run build -- --out "<vault>/.obsidian/plugins/uni-os-cockpit"` also copies the build into this vault.
- Reload: Settings → Community plugins → toggle Uni OS cockpit off and on. With the Obsidian CLI: `obsidian vault=<vault name> plugin:reload id=uni-os-cockpit` (always pass `vault=`; two vaults may be open), `dev:errors` for the console errors.
- Before changing anything in the real vault, keep a copy of the three built files so a bad build can be undone, and say which parts were only inferred, not tried (a real tap, the applier on a real note, the light theme).
- The assistant uses only the two model ids in its settings (fast and strong). Never type an API key or an iCal address for the student; they enter them themselves.
