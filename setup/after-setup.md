# After setup: living with Uni OS

Your vault exists, `uni-os doctor` is green, and the pieces you chose are connected. This page is for you, the student: what the first week looks like, what a normal day and week look like, how to change things by talking to your agent, where things live, and what to do when something breaks.

The short version: **open your agent in the vault folder and talk to it.** Everything else (which file a fact belongs in, which job runs when, which session owns what) is written down in the vault, and the agents follow it. Uni OS has only been tested with Claude Code; other agents read the same files.

Times on this page come from your config (`[schedule]` in `<vault>/_agent/uni-os.toml`). Where an example time appears, it is the original system's value, not a recommendation.

## The first week

| When | What happens | What you do |
|---|---|---|
| Day 1 | The vault is new; course cards hold what the interview found | Open the agent in the vault ("what's due this week?"). With Obsidian, keep `Home.md` open. Save new course files into the course's official folders under their official names and tell the agent ("I downloaded sheet 3 into the AD assignments folder") |
| After the first exercise session of each course | The card's **session rule** (which sheet a session discusses) was a guess until now | Tell the agent what really happened: "The AD session discussed sheet 2 and introduced sheet 3." It corrects the card, the overview and the config |
| First lectures | Lecture rundowns need to know where a lecture stopped | "Lecture today stopped at slide 42, section 7.2." One line goes into the card's lecture log |
| Any day | Graded work and help policies apply from the first message | Ask for hints the normal way ("I'm stuck on sheet 3, task 2"); `solo` work gets no help at all, by design |
| Evening, with `daily-prep` | The evening job writes tomorrow's prep note (at `schedule.daily_prep`) | Open the prep note (or the cockpit's prep card) once. Each study block in your calendar ends with a MATERIAL block with the same links |
| End of the week, with `check-in` | The `week-page` job creates next week's page (`schedule.week_page`); the `check-in` job opens a session that asks you once for the week's results (`schedule.check_in`) | Answer the check-in in one message, one line per course: "AD: sheet 3 done 4/4; DM: sheet 3 done except 3.5 (parked); LA: quiz passed; ~15 h focused." |
| End of the week, with `planning` | Plan & progress is asked for next week's plan | Read the proposed calendar changes and say yes (or what to change) |
| After the first week | You have seen what the jobs do | Decide what to switch on next: the heartbeat (released with dry runs first, see its README), the optional jobs (`waiting-on-you`, `lecture-skim`, `quiz-prep` once quiz dates are out, `deadline-audit`). Add quiet windows for timed quizzes and orals when their dates are announced |

Also worth doing in the first week: let the agent check every course fact against the course pages with you (module `resources`: "check my course facts", you sign in, it only reads), and fill the student-model pages in a ten-minute chat ("interview me for my profile").

## A normal day

| Moment | What you do | Things you might say |
|---|---|---|
| Morning | Glance at Home (with Obsidian) or the cockpit (with `cockpit`): now/next, what is due, today's prep note (with `daily-prep`). In a Minimal vault, ask the agent: the course cards and backlogs hold what is due | "What's on today?" · "What's due this week?" |
| Before a study block | Open the block's material from the prep note or the calendar | "Add the LA recap page to tomorrow's prep." |
| While studying | Work; ask for the smallest hint when stuck; let mistakes be logged | "Give me a hint for task 2b, nothing more." · "Log this error: I mixed up the order of quantifiers." · "Make me a study page on heaps from today's lecture." |
| After a lecture | Say where it stopped, ask for a rundown | "Rundown of today's DM lecture." · "Skim of tomorrow's AD lecture." |
| When something is done | Tell any session; it updates the week page, the dashboard and the course card in the same turn | "AD sheet 7 submitted." · "LA quiz 4: 3.5/4." (or tap Done in the cockpit) |
| When plans break | Ask the planner | "Replan today: the 14:00 block didn't happen." · "I have an appointment Thu 15:00-16:30, move what collides." |
| Evening | Nothing, usually. The prep job runs; the heartbeat stays silent unless something matters | "What's waiting on me?" |

A push on your phone means something needs you. Silence is the normal state: the system never sends "all good".

## The weekly rhythm

| What | Module | When (config key) | Your part |
|---|---|---|---|
| Next week's page with its real due items | check-in | `schedule.week_page` | none |
| Next week's plan and calendar blocks | planning | after the week page exists, or when you ask | approve the calendar changes (unless you gave standing approval) |
| Check-in: results, focused hours, what worked, roll-overs | check-in | `schedule.check_in` (weekly or every two weeks) | answer once |
| Dashboard and course cards brought up to date | check-in, progress | during the check-in | none |
| Inbox sorted | core | when you ask | "Sort my inbox." once a week (jobs only touch update notes, never your drops) |
| Stuck or forgotten things raised | heartbeat | `schedule.heartbeat`, `schedule.heartbeat_weekend` | answer its one question when it asks (at most one a day) |

A weekend away? Say "check-in" in any session before you leave: the scheduled run then finds nothing left to fill. A lasting change goes into the config (next section).

## Changing things by chatting

Ask your agent; it edits `<vault>/_agent/uni-os.toml` (the single source of truth), checks it with `uni-os config validate`, applies it with `uni-os render`, and updates the job's scheduled task when a schedule changed. You should never have to edit a `job.conf` or a generated file by hand.

| You say | What changes | What else the agent does |
|---|---|---|
| "Move my check-in to Sunday evening, 18:00." | `schedule.check_in` | renders, then updates the check-in task (laptop app task or server timer) |
| "Make the daily prep run at 18:00 only." | `schedule.daily_prep` | renders, updates the tasks |
| "From now on, only hints in DM, never full solutions." | `courses[].assistance` for DM, or a dated rule in `_agent/rules.md` | quotes the rule back to you |
| "The oral bonus problem in LA is solo." | that assessment's `assistance = "solo"` | renders; from then on no help on it at all |
| "Fewer pushes: two a day, three hours apart." | `notify.max_per_day`, `notify.min_gap_hours` | renders |
| "Quiet window for the LA quiz on Thursday 19 November, 07:30 to 10:00." | `notify.quiet_windows` | renders |
| "Stop telling me about the LA reading pages until Monday." | a line in `_agent/heartbeat/requests.md` | nothing else; `resume` lifts it |
| "The DM sheets come out on Thursday now." | the DM card (dated correction), `courses[].sheet_release` | renders the overview and the skill |
| "Add my new course, Probability." | a new `[[courses]]` entry | renders: folder, card, backlog, notes, official folders; re-copies the skills; re-runs the Obsidian merge |
| "Switch on the daily waiting-on-you page at 18:30." | `schedule.waiting_on_you` | a dry run first, then the task, with your yes |
| "Add the always-on server." / "Turn off daily prep." | `modules.enabled` | see [changing-modules.md](changing-modules.md) |
| "I changed the block notation." | `calendar.notation = "custom"` and the table in `semester/planning-system.md` | matches the heartbeat's and cockpit's title patterns |

New facts are recorded the same way without asking: the start page tells every agent to write anything new into the right file before it finishes.

## Where things live

| You want | Open | Module |
|---|---|---|
| The dashboard | `Home.md` (best in Obsidian), or the cockpit | core; the cockpit with `cockpit` |
| What is due, where you stand | `progress/current-status.md` | progress |
| What is due, in a Minimal vault | each course card's assessments and the course's `backlog.md` | courses |
| This week | `progress/weeks/week-NN.md` (`status: current`) | progress |
| This week's plan | `semester/plans/week-NN-plan.md` | planning |
| Tomorrow's material | `semester/prep/prep-YYYY-MM-DD.md` (the highest `-rN` revision wins) | daily-prep |
| Everything about one course | `<course folder>/<slug>.md` (the course card), plus `notes/`, `reference/`, `backlog.md` and the official folders | courses |
| Your mistakes in one course | `<course folder>/<slug>-error-log.md` | error-logs |
| What waits on you | `waiting-on-you.md` (written by the optional `waiting-on-you` job) | roles |
| Dates, weekly grid, term weeks | `semester/calendar-and-dates.md` | planning |
| Outdated versions of official files | `z_archive/<course folder>-outdated-YYYY-MM-DD/` (moved there, never deleted, only with your OK) | courses |
| Anything else | `where-to-find-what.md`, and the folder map in `README.md` | core |
| Your settings | `_agent/uni-os.toml` | core |
| The rules every agent follows | `_agent/rules.md` | core |
| What runs where, and when | `_agent/system-handbook.md` | core |

A row whose module you don't have has no file in your vault; `python tools/uni_os.py modules --vault "<vault>"` lists what you have.

Everything under `_agent/` is written for agents; you can read it, but you rarely need to.

## When something breaks

Start with the health check. In the framework folder:

```bash
python tools/uni_os.py doctor --vault "<vault>"
python tools/uni_os.py doctor --vault "<vault>" -v      # more detail
```

Or just tell your agent "run doctor and fix what it finds". Doctor checks the config, the modules, every installed file and folder, the job files, the formats other parts parse, and scans the vault for secrets.

| Symptom | Likely cause | What to do |
|---|---|---|
| No prep note for tomorrow | the laptop slept or the agent app was closed at the job's time | the morning check catches up; "rerun the prep for tomorrow". Jobs on the laptop need the app open; an always-on server fixes this for good |
| No page for the new week | the same | "create this week's page" (`uni-os new-week --current` makes the skeleton; a late `week-page` run also creates it) |
| A file `_agent/logs/flags/<job>.md` exists | that job's last run ended without its full result; the first line says why | fix the cause or ask the agent to finish the step; the next complete run deletes the flag |
| A scheduled task ran but did nothing | it stopped at a permission prompt | recreate it from a session in the mode unattended jobs need (In Claude Code: you switch a session to bypass mode, then the agent recreates the task from it) |
| `render` says a file was skipped ("generated regions cannot be refreshed") | a marker line `<!-- uni-os:begin ... -->` / `<!-- uni-os:end ... -->` was deleted or changed while the file was edited | restore the marker lines (the agent can copy them from a fresh render into a scratch folder); everything else in the file stays yours |
| A page you deleted is still missing | `render` never recreates deleted files or folders | `python tools/uni_os.py init --vault "<vault>"` restores them; it never overwrites |
| Pushes stopped | topic file missing on this machine, battery optimisation on the phone, or provider `none` | "what did the system push today?" (`uni-os push --status`); check the ntfy app |
| The same problem arrives twice | two machines both push it | only one machine may send outcome pushes; see the notifications README |
| The cockpit shows no courses | `_agent/uni-os.json` missing or old | `python tools/uni_os.py render --vault "<vault>"` |
| A conflict copy (`name (1).md`) appeared | two writers changed one file within the sync window | keep the right version; one writer per file is the rule |
| Something is wrong and you don't know what | | "What is the heartbeat flagging right now?" · "Show me the last runs of the daily prep." |

The module READMEs have a "Failure modes and fixes" table each.

## Keeping the system healthy

- **One source of truth for settings.** Change settings in `_agent/uni-os.toml` (or ask the agent), then `render`. Never hand-edit a `job.conf` or a generated table: the next render or sync would undo it.
- **One machine per job.** A job runs on the laptop or on the server, never both (the only exception is the server's explicit failover mode).
- **Keep the agent app open** if your jobs run as desktop scheduled tasks (or let it start with the computer).
- **Recycle long sessions.** A session re-reads its whole context on every turn. When one gets slow, say "start a fresh coordinator" (or the role's name): it writes a handover and a new session continues from it. In Claude Code, `modules/roles/scripts/usage_map.py` shows which sessions use the most.
- **Run doctor now and then**, and after every change you are unsure about.
- **Secrets stay out of the vault.** The vault syncs everywhere and every agent can read it. Doctor scans for API keys, tokens, private calendar addresses and ntfy topics.
- **Your notes are backed up by the sync provider's history**; with the server, also by its hourly git history of the notes.
- **Updating the framework** (once it is published): pull the new version in your clone, then preview and apply. Files you never edited are updated; in files you edited only the generated regions are refreshed:

  ```bash
  python tools/uni_os.py render --vault "<vault>" --dry-run
  python tools/uni_os.py render --vault "<vault>"
  ```

  Then copy the skills again if any changed, and on the server run `uni-vm jobs sync` (see the vm module).
- **A new term:** Uni OS has no new-term command yet. Ask your agent to plan the move: archive the old term's week pages, plans and prep notes, then update `[term]` and `[[courses]]` and render. Old course folders stay untouched.

## More

- Add, remove or reconfigure modules: [changing-modules.md](changing-modules.md)
- The module catalogue: [modules/README.md](../modules/README.md)
- How the parts fit together: [docs/architecture.md](../docs/architecture.md)
- Assistance levels and why they exist: [docs/academic-integrity.md](../docs/academic-integrity.md)
- Common questions: [docs/faq.md](../docs/faq.md)
