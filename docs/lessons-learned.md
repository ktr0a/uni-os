# Lessons learned

These are the concrete gotchas from two months of running my own system: my first-year computer science semester, organised by several AI agent sessions over an Obsidian vault on Google Drive, first on a laptop, then with cloud sessions, then with an always-on VM (see [how-it-evolved.md](how-it-evolved.md)). They are grouped by topic. Each one says what happened and what to do about it, and links to where Uni OS already handles it.

Some items are specific to Claude products, because that is what my system ran on. Uni OS has only been tested with Claude Code. Other agents have their own versions of most of these limits.

## Connectors and create-only tools

- **The Google Drive connector creates files but cannot change an existing file's content.** It can also edit metadata, and moving a file by changing its parent keeps its id and links. This one limit produced the whole update-note protocol: create-only writers drop a self-contained note that quotes the current lines exactly, and one trusted job applies it ([inbox-sync](../modules/inbox-sync/README.md)).
- **Write directly or send an update note, never both.** A session that did both produced duplicate `name (1).md` files.
- **The applier can't read the sender's conversation.** An update note must carry everything needed to apply it: the target path, the operation, the exact anchor, and the student's words if they triggered it.
- **Connector reads truncate.** Long Markdown logs came back cut in the middle, slide decks stopped around slide 24, and some PDFs returned empty text. Writers must never quote lines they didn't see; the applier parks wrong quotes anyway. For PDFs, download the file and read the page images when it matters.
- **The connector can't upload binary PDFs**, and a note created with Google conversion on becomes an unreadable stub. Turn conversion off (`disableConversionToGoogleType: true`) and let the student upload binaries.
- **"Title contains" search is unreliable.** List the folder and filter instead.
- **The calendar connector's update replaces the whole description.** Start every edit from a fresh read of the event and keep machine-written lines such as the prep job's `MATERIAL` block. Its times come back in UTC and look an hour off. Recurring instances have their own ids, so edit the instance, never the series ([planning](../modules/planning/README.md)).
- **A report is not proof.** An evening's calendar edits were reported done but never applied. Read every write back, and have the coordinator check results itself ([roles](../modules/roles/README.md)).

## Scheduling: sleep, time zones and daylight saving

- **Desktop-app scheduled tasks run only while the app is open.** They start a few minutes late (I saw about 12 minutes), get a fixed offset added to their times, and catch up missed slots at random times after wake-up (an evening slot ran half an hour late, a morning check more than two hours late). Every prompt therefore computes its **nominal slot**, checks whether that slot is already done, and carries a catch-up rule ([scheduler-local](../modules/scheduler-local/README.md#slots-catch-up-and-idempotency)).
- **One cron expression can't mix minute values.** Slots at `07:50` and `13:05` need two tasks.
- **A scheduled task bound to a session that no longer exists silently never runs.** A weekly check-in was bound to a session that ended the same day, and nobody noticed for weeks. Audit what actually triggers each duty ([design-principles.md](design-principles.md#11-every-promised-duty-needs-a-trigger)).
- **Never run one job on two machines.** In failover mode the host writes a ran-marker so the laptop's catch-up skips that slot. In mode `always` no markers exist, so the laptop copy must be paused. When switching between schedulers, do both steps back to back, right after a slot, never around one ([vm](../modules/vm/README.md#failover-mode-optional)).
- **Failover built on an app's internal files is brittle.** Reading the desktop app's task file while the app was writing it sometimes failed. In the end I gave each job one host, in mode `always`.
- **Systemd timer precision matters for slot logic.** `AccuracySec=1s` plus `RandomizedDelaySec=20` keeps the start minute equal to the nominal slot. Host timers are not `Persistent`, so a slot missed while the host was down is not caught up, which is one more reason prompts must be idempotent.
- **Transient timers vanish on reboot.** I lost a one-off reminder timer on the host. Note it wherever you rely on one.
- **Keep every schedule in one place.** A hand edit in a generated job file was silently reverted by the next sync from another copy. In Uni OS the schedule is a `[schedule]` key; edit the config, run `uni-os render`, and reinstall the job.
- **Name the time zone.** Notes and logs use local time in `term.timezone`. A cloud session stamped notes an hour ahead after the daylight-saving switch, and the switch week's stamps came out an hour off. Convert first, and put the switch dates on the calendar page.
- **Python on Windows ships no time-zone database.** "Today" then follows the computer's clock zone. `python -m pip install tzdata` makes `term.timezone` exact ([tools/README.md](../tools/README.md#windows-notes)).
- **The laptop clock must be in the vault's time zone.** App tasks and OS schedulers use local time.
- **Week numbering is a trap.** LMS weeks were 1-indexed, a teaching assistant's "week N" was the term's week N-1, one course's weeks straddled two calendar weeks, and programming sheet numbers were the term week plus one. Every page says which numbering it uses, and `uni-os week` is the reference.

## Messaging and notifications

- **Never send "all good".** I explicitly did not want routine success messages. The push gate refuses them, and silence is the normal outcome ([notifications](../modules/notifications/README.md)).
- **Push fatigue comes from several senders, not one.** Health alerts, job failures and outcome checks each had their own spacing until one gate gave them one budget: by default 3 a day, 2 hours apart, no pushes from 21:00 to 07:30, dedupe per problem for 24 hours. Health alerts stay outside the budget but are rate-limited per problem.
- **One problem, one sender.** The gate dedupes per machine, so the same stuck note checked on two machines reached my phone twice. Now exactly one machine sends outcome pushes, with the same ids and texts everywhere ([notifications](../modules/notifications/README.md#one-sender-per-problem)).
- **Defer judgment pushes, queue host alerts.** A queued "no prep note for tomorrow" would arrive at 07:30 even though the note was written at 22:00. Judgment pushes held in quiet hours are dropped and raised again if still true; host alerts held in a quiet window go out as one combined push afterwards.
- **No pushes at the start of a timed quiz.** Quiet windows around graded fixtures hold every push, and the heartbeat's question checks the gate both now and 15 minutes later.
- **The agent app's own push is held back while you count as active**, and on a headless box the terminal always looks active. Use your own channel (ntfy). It is one-way: answers go through the agent app.
- **Every new Remote Control session notifies the phone**, and that can't be switched off. Jobs that ask nothing run headless; only jobs that must talk to the student open a session. A heartbeat question therefore costs two notifications (the push with its link and the app's own), so budget at most one question a day.
- **The ntfy topic is a password.** Anyone who knows it can read and send your pushes. I leaked mine in a README and a generated report. Keep it in one file outside the vault (`notify.ntfy_topic_file`); `uni-os doctor` scans for it.
- **No personal details in pushes.** File names and gap texts can carry them, so outcome pushes name the problem, not the file.
- **Android battery optimisation delays pushes.** Exempt the ntfy app.

## Google Drive and other sync layers

- **Drive is last-writer-wins per file.** Two machines writing within the sync window lose a change or create a conflict copy (`name (1).md`). Keep a list of risky files (the rules, the status page, the tracker and error logs, the week pages, the course cards, state files, coordinator files), re-read right before editing, keep edits small, and keep one writer per task. New files are always safe ([CONVENTIONS](../modules/core/vault/_agent/CONVENTIONS.md), section 9).
- **Write machine files in place when something reads them by file id.** A temp-file-and-rename creates a new Drive id, which broke a dashboard that read its source by id.
- **A streaming drive downloads every file a watcher opens.** Watchers compare metadata only (size, modified time).
- **Right after wake or logon the drive can be half mounted**, which looks like mass deletion. The vault watcher skips a run when a scope has under 20 % of its snapshot's files ([vault-watch](../modules/vault-watch/README.md)).
- **Drive for desktop quirks:** no symlinks, Google shortcuts appear as 0 KB `.gdoc` stubs that throw "Incorrect function", and files without an extension are shown differently on the rclone mount and on Windows.
- **Agent apps packaged as MSIX redirect writes under AppData.** Files the agent puts under `%LOCALAPPDATA%` are invisible to other processes, so install shared files under Documents.
- **rclone on the always-on host:** the Google OAuth client must be published "In production", or refresh tokens expire after 7 days. Tokens also die after a password change, a "remove access", or 6 months unused. A delete on the mount is a real delete. A recursive grep over the FUSE mount takes minutes, so use the host's git copy of the notes (`uni-vm grep`). rclone keeps its log open, so it must be trimmed in place. A remount strands the Remote Control server in the dead mount, so restart it after every mount ([vm](../modules/vm/README.md)).
- **Jobs that don't need the vault say so** (`NEEDS_VAULT="no"`), or a drive outage turns them into failure alerts.
- **Other providers** (OneDrive, Dropbox, iCloud, Syncthing, git) probably work but were not tested. Their conflict-copy names differ, so add a pattern for yours ([storage.md](storage.md)).

## Course sites, downloads and provenance

- **The password step always stays with the student**, even with blanket permission. Agents click through single sign-on but never type a password or a one-time code. Batch the sign-ins into one push.
- **Logged-in pages are read-only.** "Do not change anything, solely click through the data and read." Never start a quiz attempt, submit, post or change settings.
- **A browser download fails silently more often than you'd think.** In the first week about 90 files were filed, and about 35 requests ended "not found". A blocked click leaves no file and no partial download. Clicking several downloads in a row stalled the browser, and one site allowed only one automatic download per tab. So: one file at a time, one new tab per file, and the click, the check that the download started and the filing request as separate steps ([course-files-fetch](../modules/course-files-fetch/README.md)).
- **Trust no filing request.** Many sessions can write to the vault, and one might have read a malicious page. The pick-up files a download only if the browser's own download mark says it came from an allowed host. On Windows that is the NTFS `Zone.Identifier` stream with its `HostUrl=` line. The file must also be a document, recent and small enough, headed for a configured folder, and its name must be free. It never overwrites and it verifies the hash. A Downloads folder on FAT or exFAT has no such mark. A local process can forge it, so code execution on the laptop is out of scope.
- **"Changed on the server" never overwrites.** Several site versions were newer than the vault copies (corrections, a new slide). Replacement happens only after the student's yes, with the old copy archived under `z_archive/<course folder>-outdated-YYYY-MM-DD/`, keeping the vault names because notes link to them.
- **Timestamps lie.** Corrected re-uploads made a Thursday release look like a Friday one. Announcements win over file dates.
- **Sources outside the brief need a question.** A public slides server linked from the LMS was used without asking; the rule became "anything else: ask first".

## Obsidian

- **Bases columns need the `note.` prefix** for front-matter properties; plain keys only rename `file.*` columns ([obsidian](../modules/obsidian/README.md)).
- **Custom callout colours need explicit CSS.** The version I used ignored `--callout-color` for custom types.
- **Graph colour queries must be anchored regular expressions** (`path:me` also matched any path containing "me"), and they must follow folder moves. After a restructure the old queries silently coloured nothing for days. Generate them.
- **Move and rename notes inside Obsidian** (its file explorer, or its command line running `app.fileManager.renameFile`). Moves on the drive or through a storage API don't update links.
- **Obsidian's index lags deletions** by minutes. A deleted inbox note still counted as waiting, so plugins count the inbox from disk.
- **HTML study pages don't render in Obsidian.** Keep a Markdown twin and open the HTML page in the browser. In HTML maths, a literal `<` followed by a letter gets swallowed, so write `\lt`.
- **Settings sync with the vault.** `.obsidian/` travels to every device through the drive, so never ship `workspace.json` or a plugin's `data.json` (per-device state, possibly secrets). Merge recommended settings with a script instead of overwriting, and close Obsidian first, because it writes its settings back on close.
- **Dot-folders are invisible, and "Excluded files" only hide from search and graph.** Obsidian also rewrites `.base` and `.canvas` formatting, which is harmless.
- **Never run `npm install` inside the synced vault.** `node_modules` would sync to the cloud. Build the cockpit in the framework clone and copy the built files ([cockpit](../modules/cockpit/README.md)).
- **Without Obsidian** the views, the Home dashboard and the cockpit are hard to get. Everything else is plain Markdown.

## The always-on host: sizing and operations

- **Memory is the binding constraint, not CPU.** Measured footprints were about 360 MB per working role session (260-415 MB), 225-280 MB per headless job run, and about 120 MB for the Remote Control server. Six role sessions plus jobs on 4 GB got the verdict "tight". Seven more sessions would not fit: 6 GB is marginal, 8 GB comfortable ([vm](../modules/vm/README.md#cost-and-sizing)).
- **Per-session tool servers are expensive.** A browser tool server or a synced plugin adds 130-260 MB per session. Disable them on the host and use per-call command-line tools.
- **Use compressed RAM swap plus a small swap file** to absorb bursts. Give each class of session its own OOM priority so that interactive job sessions die first, role sessions last, and the vault mount never.
- **Cost.** My 4 GB Google Cloud VM was about $21 a month at list price. A 2 GB machine is below Claude Code's stated 4 GB minimum. A stopped VM costs only its disk. Google posts charges about a day late. Set a budget alert.
- **A home server trades money for chores.** On an 8 GB laptop running WSL2, Windows plus the agent app and Chrome took about 2 GB, so six sessions were again "tight". Expect power, Wi-Fi and Windows Update reboots to matter.
- **Idle time must come from transcript timestamps, never file modification times.** The agent touches an open transcript about hourly, so mtime-based idle closes never fired.
- **One-time dialogs silently block sessions.** Detect the missing permission-mode footer for 2 minutes and push once.
- **Always read a session's screen (`tmux capture-pane`) before sending keys.** A stray Enter meant for one session answered a dialog in another and flipped the machine-wide default permission mode.
- **tmux messages are capped at 16 KB.** Pass prompts through a file. systemd kills a oneshot unit's children, so interactive job sessions need their own tmux server unit.
- **The agent updates itself, but a running server keeps the old binary.** Restart it in a quiet hour.
- **Unset API-key variables in the job runner**, or jobs bill an API account instead of using the subscription.
- **A model change made inside a host role session is lost on resume** unless it is written to the role's config.
- **A deploy must not overwrite hot fixes.** Deploy only adds and overwrites files, checks a manifest for drift first, and never restarts services by itself.

## Agent sessions: context, recycling and usage

- **A session re-reads its whole context on every turn.** In one measured week the coordinator alone was about 19 % of usage and the infrastructure session about 13 %, while all scheduled jobs together were about 1.6 %. A fresh coordinator boots from its state page in about 31k tokens; the old one was re-reading over 550k per turn. Recycle long-lived sessions at about 300k tokens (`agent.context_refresh_tokens`), and measure first with the usage map (Claude Code only, [roles](../modules/roles/README.md#usage-map-optional-script-claude-code-only)).
- **Splitting the shared role brief per role saved only about 8k tokens per start.** It wasn't worth doing.
- **Don't save on teaching sessions.** On the strongest model at the highest effort they cost only about 1.5-2 % of a week each.
- **Keep state in files, and export before compaction.** Compaction dropped a long session's raw history, and coordinator memory degraded with every compaction.
- **Every edit to shared rules costs every session a re-read** once a hook tells running sessions that the rules changed. Edit briefs and rules only for real changes.
- **Sessions inherit permission mode.** Sessions started from a bypass session are in bypass too. Mixed modes make messages wait for an approval nobody gives, so keep all role sessions in one mode.
- **Never message a cloud session from a bypass session.** The message sits "held, waiting for approval" and then expires. Cloud sessions can't message laptop sessions either; they write `## For <session>` sections in update notes.
- **Address sessions by title.** Session references differ per viewer and change. Deliveries to Remote Control sessions are not confirmed, so record "delivery not confirmed" and check the file later.
- **Headless jobs can't see laptop sessions.** They relay through the host's main session with a fixed wording, and the receiver forwards the text unchanged and never acts on it.
- **Agents refuse to edit their own permission settings**, and registering an OS scheduled task from an agent was blocked as "unauthorized persistence". Hand the student a script or a one-liner to run.
- **Sessions misreport their own effort level.** Read it from the session record.
- **Visual output varies by runtime.** Mermaid sometimes showed as plain text, so diagrams should read well even unrendered. Some file-sending tools refused SVG on the host, while HTML worked.
- **Quote the student.** State-page rows that quoted my exact words, with a date, settled later misreadings, for example of a usage cap or a misheard name.

## Integrity

- **Hints-only everywhere was simpler than a patchwork.** I started with full answers for some ungraded tasks and switched every course to hints-only after a few weeks. A tired "just tell me" should not end in a worked solution, so the level changes in the config, never in the moment ([academic-integrity.md](academic-integrity.md)).
- **Graded code is special.** In one course AI-written code counted as plagiarism, so the agent pointed at lines and traces instead of fixing them, and declined full code even when asked.
- **Integrity rules bind everything**: diagrams, hint pages, prep notes, built tools and file fetchers. A fetcher refused a solution file that was only allowed after a date, with the date guard enforced in code on both sides.
- **Handwriting too.** Once handwritten PDFs were visible to agents, the rule "never transcribe, summarise or store the student's handwritten work on graded solo problems" was written down ([handwritten-notes](../modules/handwritten-notes/README.md)).
- **Reused tasks happen.** Many tasks of one course were reused from earlier years' public sheets. Say so openly, without pointing to the old solution.
- **The course skill must never pre-approve anything.** The skill in my own system contained a line pre-approving a university consent screen; the framework's skill has no such line.
- **Hold the line when the student pushes.** The coordinator kept "the password step stays with the student" when I asked it to let agents sign in, and proposed another route.

## Study engine: what helped learning

- **One fixed place for tomorrow's material.** Before the daily prep note, each of my study blocks started with ten minutes of hunting for the sheet, the task, the script page and the integrity status. The note also surfaced problems a day early ([daily-prep](../modules/daily-prep/README.md)).
- **One model page beats a style guide.** A single study page that worked became the template for every course: sections of about 700-800 words (`study.chunk_words`), one demo and one quiz each, a cheat sheet, and a final self-test at the end ([study-pages](../modules/study-pages/README.md)).
- **Answers checked by code.** Wrong-option explanations computed from the real algorithm were more reliable and more useful than typed ones. Matrix answers were checked by multiplying them out.
- **Pictures first.** I followed visual explanations much better than script-style text (`study.intuition_first`).
- **Show the page immediately.** Pages sent straight to my phone got used; pages only mentioned by path often did not.
- **The error log was the most reused file**, read by quiz prep, cheat sheets, weak spots and the daily prep. Log a mistake the moment it happens, concretely and with the tutor's words; "later" never happened ([error-logs](../modules/error-logs/README.md)).
- **Testing every closed form on n = 1, 2, 3** was the most frequent "correct idea" in my logs.
- **The stuck-task protocol came from one exercise that took me two and a half hours:** a content verdict first, a time cap per part, then the missing idea in one line ([exercise-help](../modules/exercise-help/README.md)).
- **Hints in too many small pieces frustrate.** "Say the missing idea in one line sooner" became part of the protocol.
- **Cold retests didn't work for me.** I dropped weekly redos of old errors after about a week and replaced them with a 15-minute open-notes recap at the start of each study block. Retests are therefore off by default (`study.error_logs.retests = false`).
- **Pre-lecture skims helped me most for the hardest course**, and only when they were ready before the lecture. That is why a skim has a readiness lead time (`study.rundowns.skim_lead_hours`), and the skim job's run times (`schedule.lecture_skim`) are chosen to meet it ([lecture-rundowns](../modules/lecture-rundowns/README.md)).
- **The quiz loop is prep, quiz, review, error log, next prep.** The review is where the learning happens. "How this quiz asks" tables from earlier reviews of the same course beat generic advice, and a checklist that dropped the words "in the worst case" caused a wrong answer: copy the exact words ([quiz-coaching](../modules/quiz-coaching/README.md)).
- **Mocks only on request.** I declined automatic weekly mocks; one targeted mock the day before a written quiz worked better.
- **Validate plans against the student's rhythm.** A deep proof block placed in my documented low failed. Count hours per subject: my best-liked course was getting the most time while two others fell behind, which produced the rebalance rule (freed time goes to the lowest-rated course) ([planning](../modules/planning/README.md), [student-model](../modules/student-model/README.md)).
- **Too many changes ruin the data.** Changing the method every week made it impossible to tell what helped. Hence one change at a time for two weeks ([experiments](../modules/experiments/README.md)).

## Process

- **Dry runs are instructions, not sandboxes.** A dry-run agent is told not to change anything, but only helpers that honour `UNI_DRY_RUN` guarantee it. A push job declared dry-run-safe once sent real pushes in a test and recorded them as sent.
- **Release new jobs like software:** staged with the timer off, dry-run at representative times, judged against fixed checks, switched on with the student's yes right after a slot, with a written rollback ([vm](../modules/vm/README.md#releasing-a-new-agent-job-staged-rollout)).
- **Simulated runs produce simulation artifacts.** A Sunday-evening run simulated on a Thursday's vault showed 14 red findings, most of them artifacts. Do one dry run at a real slot as well.
- **Probe a capability before relying on it.** Before the heartbeat's first dry run, the builder checked read-only that a headless run on the host could load the calendar tools and see the sessions it would message.
- **The model will "fix" a rule's verdict if you let it.** In a dry run the agent downgraded a red "overdue" itself after seeing a conflicting log line. Rule findings keep their level; staleness goes into the text, and the cure is a message to the file's owner ([heartbeat](../modules/heartbeat/README.md)).
- **Name things distinctly.** My system ended up with three different "heartbeats" (the watcher, a laptop ping, a dashboard's status-file age) and needed a disambiguation table. In Uni OS "heartbeat" means only the watcher.
- **Generated maps beat maintained ones.** After two restructures the vault map, canvas, CSS comment and graph settings all carried stale paths. Uni OS generates them and refreshes their regions on `uni-os render` ([design-principles.md](design-principles.md#24-generate-what-can-drift)).
- **Make every feature easy to drop.** Features I abandoned after a week (retests, recall tests) were switched off, and their old files stayed readable.
- **Test on the real machine with real input, and verify copies by size or hash.** A stale cached copy and a trackpad bug were found only that way.
- **UTF-8 without a byte-order mark** for every file a script or plugin parses. Windows PowerShell 5.1 writes ANSI by default, and a settings backup saved with a BOM broke a JSON loader.
