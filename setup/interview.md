# Setup interview: the question bank

Every question the setup agent may ask, grouped into the batches of [PLAYBOOK.md](PLAYBOOK.md) step 2 and step 3. For each question: how to ask it simply, the config key(s) it fills, the default, and why it is asked. The keys and defaults come from [config/schema.md](../config/schema.md) and the module READMEs; nothing here is a key of its own.

## How to use this page (for the agent)

- **Batches 1 to 5** come before the module menu, **batches 6 to 9** after it, and only for the modules the student chose. Each batch is one message with numbered questions.
- **Propose a default for every question**, in brackets: `5. On which Monday does week 0 start? [Mon 14 Sep 2026, from the academic calendar you linked]`. The student may answer "default", "skip", "don't know" or "defaults for the rest". "Don't know" takes the default and goes on the list of things to check later.
- **Defaults that are times or days are the original system's values, shown only as an example** (it was built for a first-year BSc Computer Science semester at ETH Zurich). Never present them as the right answer; ask what suits the student.
- **Fill what you can from sources** (course pages, a pasted timetable, earlier answers) and show it as a proposal. Mark inferred values "(inferred, please check)".
- **Never ask for secrets.** Passwords, API keys, private calendar (iCal) addresses and the ntfy topic are typed by the student into the app or file that needs them, later (PLAYBOOK step 7). The config holds at most the *path* of a secret file.
- **Keep names of real people out of anything shared.** `courses[].lecturers` is optional; it is fine in the student's own vault, never in examples or bug reports.
- A question that starts with a module id in brackets, such as "(lecture-rundowns)" or "(scheduler-local)", is read only by that module. In batches 1 to 5 skip it when the student will obviously not use the module (PLAYBOOK step 2, rule 4); "(Only if ...)" questions depend on an earlier answer.
- A **Keys** cell like `courses[].sheet_due` means the key inside each `[[courses]]` table; `courses[].assessments[].kind` is inside each `[[courses.assessments]]`.
- Keys that are pure tuning knobs (the heartbeat's grace minutes, the VM's memory thresholds, the vault watch's churn list, ...) are not asked. Their defaults are the original system's values; they are listed in [config/schema.md](../config/schema.md).

The fictional student Alex Example at the Example Institute of Technology (EIT) is used in examples; the complete answer set is [examples/alex.toml](../examples/alex.toml).

---

## Batch 1: You, your university and your term

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 1.1 | What's your name, and a short handle agents can use (letters, digits, `-`, `_`, `.`)? | `student.name`, `student.handle` | name required; handle `""` | agents address you by name; the handle is shown next to it on the agents' start page, in the system handbook and in your profile, and the cockpit uses it only when the name is empty |
| 1.2 | Which language should notes and replies be in? | `student.language` | `"English"` | agents write new notes, study pages and replies in this language; it is also the default language of each course's material. The pages Uni OS generates (course cards, rules, Home, the handbook) and the headings that tools parse stay in English; an agent can translate a generated page on request. With phone pushes, also ask 8.9 |
| 1.3 | Do you often dictate (speech to text)? | `student.dictates` | `false` | agents then work out mangled words from context and ask only when a wrong guess would change something |
| 1.4 | Pronouns, if you'd like agents to use them? | `student.pronouns` | `""` | optional |
| 1.5 | Any personal rules for how agents reply to you? (e.g. "short replies", "dates as Mon 26 Oct 2026") | `agent.reply_rules` | `[]` | written into `_agent/rules.md`, which every session reads first |
| 1.6 | University: full name, short name, and your degree programme? | `university.name`, `university.short`, `university.programme` | name required; `""`, `""` | titles, the start page, the course cards |
| 1.7 | Which learning platform does your university use, and what is its public start page? | `university.lms`, `university.lms_url` | `"Moodle"`, `""` | named in the source-of-truth order and the sign-in rule; a public address only, never a private link |
| 1.8 | University website, course catalogue and lecture-recording portal, if any? | `university.website`, `university.catalogue`, `university.recordings` | `""` each | where agents look things up; the sources registry |
| 1.9 | What is this term called, and in which time zone do you live? | `term.label`, `term.timezone` | both required | "Autumn 2026" appears in titles; "today" and the term week are computed in this IANA zone (e.g. `Europe/Zurich`), also on a server running in UTC |
| 1.10 | On which Monday does week 0 start (the Monday of the first lecture week)? | `term.week0_monday` | required, must be a Monday | every week number in the vault: week *n* starts week 0 + 7*n* days. Other numberings (the platform's "week 1", sheet numbers) are written down later as translations |
| 1.11 | Last lecture day, first lecture-free day, and the start and end of the exam session (dates only)? | `term.last_lecture_day`, `term.lecture_free_from`, `term.exam_session_start`, `term.exam_session_end` | `""` each | week pages stop after the last lecture day; the exam-phase study schedule and quiet windows use the session dates |
| 1.12 | Breaks or public holidays inside the term? | `term.holidays` | `[]` | planning skips them and `uni-os week` reports them; each is `{ name, from, to }` (dates, inclusive) |

## Batch 2: Your courses and timetable

One message per course, or one message for all courses if the student pastes a timetable. Fill as much as possible from the course pages yourself and ask only for the rest. Module-specific per-course keys (`aliases`, `detect`, `fetch_sources`, `watch_note_subfolders`, `handwritten_folder`) come in batch 9.

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 2.1 | Which courses do you take this term? Full name and the short name you use. | `courses[].name`, `courses[].short` | required | the short name appears in tables, calendar titles and session titles |
| 2.2 | (Propose, don't ask) a stable id and a file prefix per course | `courses[].id`, `courses[].slug` | required; propose e.g. `id = "algo"`, `slug = "ad"` | `id` (lowercase, `[a-z][a-z0-9_-]*`) is what every note's `course:` property holds and what lookups use; `slug` (kebab-case) prefixes file names (`ad.md`, `ad-error-log.md`). Never change them later. With Obsidian, avoid the slugs `me`, `week`, `semester`, `deadline`, `agent`, `course` and `grid`: each course's callout type is its slug, and the CSS snippet already uses these names for its area callouts (nothing checks this) |
| 2.3 | What is the course's folder called on your drive (or what should it be)? | `courses[].folder` | required | spaces and `&` are fine (`A&D`); unique, also ignoring upper and lower case |
| 2.4 | A colour per course? (I can suggest a palette that matches your calendar.) | `courses[].colour`, `courses[].colour_light` | colour required; `colour_light` `""` (computed as a 40 % tint) | course colours in Obsidian, the cockpit, study pages and the graph. Never two similar colours |
| 2.5 | When are the lectures and exercise sessions, and which is your group? | `courses[].lecture_slots`, `courses[].exercise_slots`, `courses[].exercise_group` | `[]`, `[]`, `""` | the weekly grid, planning around classes, prep notes; slots are `"Ddd HH:MM-HH:MM"`. Labs, tutorials and project meetings go into `exercise_slots` too, with a word after the time (`"Fri 13:15-17:00 lab"`) |
| 2.6 | Where does the course live online: platform page, website, other platforms (online judge, git server), recordings? | `courses[].lms_url`, `courses[].website`, `courses[].platforms`, `courses[].recordings` | `""`, `""`, `[]`, `""` | where agents read course facts; public course pages only |
| 2.7 | When do sheets come out, when are they due, and how are they handed in? | `courses[].sheet_release`, `courses[].sheet_due`, `courses[].hand_in` | `""` each | the weekly rhythm on week pages and in plans |
| 2.8 | What happens in the exercise session of a given week: which sheet is discussed, which comes out? | `courses[].session_rule` | `""` | the most important planning fact: sessions usually lag the lectures by about a week, differently per course. If unknown, infer it from the rhythm and mark it to check after the first two sessions |
| 2.9 | Does the course number weeks or sheets differently from the term? | `courses[].week_numbering` | `""` | stops off-by-one mistakes ("platform 'Week k' = term week k-1") |
| 2.10 | Which documents count as the truth for what was lectured (script, slides)? Any page offsets between printed and PDF pages? | `courses[].real_source`, `courses[].page_offsets` | `""`, `[]` | rundowns and study pages cite only real sources; offsets are `{ source, rule }`, e.g. `rule = "PDF page = printed page + 8"` |
| 2.11 | What does the course publish (sheets, solutions, slides, script)? I'll name one folder per kind. | `courses[].official_subfolders` | `["assignments", "assignments/solutions", "script and slides"]` (courses module) | `uni-os init` creates these folders empty; official files keep their official names there and are never renamed |
| 2.12 | Exam logistics, if known: length, written or oral, language, allowed aids? | `courses[].exam_format` | `""` | logistics only, used for exam-phase scheduling |
| 2.13 | In which language is the course material? | `courses[].language` | `student.language` | study pages and rundowns follow it |
| 2.14 | Credits? Lecturers (optional)? | `courses[].ects`, `courses[].lecturers` | `""`, `[]` | shown on the course card |
| 2.15 | Any course-specific rules agents must follow? (notation, page conventions) | `courses[].notes` | `[]` | written into the rules every session reads |
| 2.16 | Does the course have two kinds of work that should keep separate mistake logs (e.g. theory and programming)? | `courses[].error_log_streams` | `["main"]` | one stream gives `<slug>-error-log.md`, several give `<slug>-error-log-<stream>.md` |

## Batch 3: Graded work, bonus schemes and how much help you want

Ask per course, then per graded item. This batch decides what the agents may help with, so read the course's official rule before proposing levels.

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 3.1 | What is graded or earns a bonus in this course? For each: what, when, how many points, what it counts for. | `courses[].assessments[]`: `name`, `kind`, `schedule`, `counts_for`, `points_max`, `dates`, `scope` | `name` required; `kind = "other"`, `schedule = ""`, `counts_for = "none"`, `points_max = 0` (unknown), `dates = []`, `scope` not set | the progress tracker, week pages, quiz coaching, the heartbeat's "result missing" question. `kind`: sheet, quiz, oral, project, midterm, other (graded lab reports or lab tests: `sheet` when they are regular hand-ins, else `other`; a term project: `project`). `counts_for`: bonus, grade, admission, none. `dates` (`"YYYY-MM-DD"` or `"YYYY-MM-DD HH:MM"`) give "N left" counts. `scope` (optional) holds the official scope wording, inferred parts marked; the course card and the `course-facts` skill show it |
| 3.2 | How does the bonus or extra credit work, in the course's own words? | `courses[].bonus.scheme`, `.description`, `.max_bonus`, `.rule`, `.target` | `"none"`, `""`, `0`, `""`, `""` | agents and the cockpit compute the standing from it. Map the words to a scheme: "x % of all points" = `threshold`; "N points give the full bonus" = `points`; "pass n of m" = `best-n`; anything else = `custom` |
| 3.3 | (Only for the engine) Published total, threshold, points for the full bonus, how many must pass? | `courses[].bonus.threshold`, `.total`, `.total_estimated`, `.proportional`, `.full_at`, `.required`, `.unit`, `.counts` | `0.8`, `0`, `false`, `true`, `0`, `0`, `"points"`, `[]` | the bonus maths of the progress page and the cockpit; `0` means unknown or "the total" |
| 3.4 | What is the course's official rule on collaboration and AI use? Quote it if you can. | `courses[].integrity` | `""` | agents follow it on top of the assistance level below |
| 3.5 | How much help do you want by default on graded work? | `study.assistance_default` | `"hints-only"` | the default for every course and graded item. Recommend `hints-only` |
| 3.6 | Should any course get a different level? | `courses[].assistance` | `study.assistance_default` | one line in the rules per course |
| 3.7 | Which graded items must be entirely your own work, with no help at all? (oral bonus problems, timed tasks, solo-graded sheets) | `courses[].assessments[].assistance` | the course's level | set these to `"solo"`. For a recurring quiz, `hints-only` usually fits: the attempt is always yours, prep sheets and a review afterwards are allowed; `solo` would mean the coach prepares nothing aimed at it |

The four assistance levels, to show the student when asking 3.5 to 3.7:

| Level | What the agent does |
|---|---|
| `solo` | no help at all on that work; nothing that solves, hints at or summarises it is stored anywhere |
| `hints-only` | smallest hint first, checks your own steps, never a solution (the default) |
| `coach` | everything above, plus full explanations on similar tasks and a line-by-line review of your complete draft; never writes the final text or code of graded work |
| `full` | full worked solutions, for ungraded practice where the course allows it |

With `exercise-help`, also ask (defaults are fine for most students):

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 3.8 | How long do you try a task cold before the first hint? How long per task part before you get the missing idea in one line? How long stuck on one bug before asking? | `study.exercise_help.cold_minutes`, `.part_cap_minutes`, `.stuck_bug_minutes` | `25`, `45`, `25` | the pacing of hints-only help |
| 3.9 | For ungraded tasks: may the agent point you to the official solution after your own attempt, on request? | `study.exercise_help.official_solutions_after_attempt` | `true` | never for graded work, whatever the answer |

## Batch 4: How you study, and what you get

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 4.1 | Do you use Obsidian, or want to? | `obsidian.enabled` | `true` | asked first because the format recommendation depends on it; without Obsidian the dashboards (Bases views, Home, cockpit) are hard to get. Presets drop `obsidian` and `cockpit` when it is `false` |
| 4.2 | Which formats for study pages? (see the table below) | `study.formats` | `["html", "md"]` | which files every study page, rundown and hint page produces |
| 4.3 | (Only if 4.2 includes `html`) Maths in HTML pages: KaTeX, MathJax or none? | `study.math` | `"katex"` | the renderer in HTML pages |
| 4.4 | Do you prefer intuition and pictures first, or precise definitions first? | `study.intuition_first` | `true` | the order of every explanation |
| 4.5 | How long should one study-page section be? (700-800 words worked well) | `study.chunk_words` | `750` | section size of study pages and rundowns |
| 4.6 | (Only with PDF) Which browser should print PDFs? | `study.pdf_browser` | `"auto"` | `auto`, `chrome`, `edge`, `chromium` or a path |
| 4.7 | Do you keep a deadline rule stricter than the official one (e.g. "sheets released in a week are done by that Sunday")? What should its column be called? | `study.personal_deadline_rule`, `study.target_column` | `""`, `"Personal target"` | fills the personal-target column of every "Due this week" table and guides planning |
| 4.8 | (lecture-rundowns) Do you want a short skim before some lectures? For which courses, and how many hours before? Recall-key pages after lectures? | `study.rundowns.skim_courses`, `.skim_lead_hours`, `.recall_keys` | `[]`, `1`, `false` | the optional `lecture-skim` job writes skims for these course ids (the original: only its hardest course); its run times come in batch 6 |
| 4.9 | (quiz-coaching) Should every quiz prep sheet come with a timed mock quiz? How many days before a quiz should the prep sheet exist? | `study.quiz.auto_mocks`, `study.quiz.prep_lead_days` | `false`, `4` | mocks on request only, unless switched on |
| 4.10 | (error-logs) Do you want a weekly cold retest of your own past mistakes? (honest note: the original student dropped it after a week) | `study.error_logs.retests`, `.retest_items`, `.retest_minutes` | `false`, `3`, `20` | the optional retest bank |
| 4.11 | (experiments) How long should a study or habit experiment usually run, in weeks? | `study.experiment_weeks` | `2` | the default period of an experiment |

**Formats** (4.2), with the recommendation by Obsidian use:

| `study.formats` | What you get | Recommend when |
|---|---|---|
| `["html", "md"]` | an interactive HTML page (KaTeX, demos, quizzes checked by code, final self-test, dark mode, phone width) plus a Markdown twin: with Obsidian it uses callouts; without Obsidian it is plain Markdown (bold labels, answers folded in `<details>` blocks) that reads in VS Code, GitHub and most viewers | the student uses Obsidian and also opens pages in a browser or on the phone (the original setup); without Obsidian only if they want a searchable Markdown copy next to each page |
| `["md"]` | Markdown only; no code-checked quizzes, no demos; with Obsidian, callouts; without Obsidian, bold labels instead of callouts and self-check answers folded in `<details>` blocks | the student will never open a browser page for studying; pick html if the student wants checked quizzes |
| `["html"]` | HTML only, no twin | no Obsidian; pages open in the browser from the synced folder |
| add `"pdf"` | a printed PDF next to the HTML | printing, tablets, annotation apps |

## Batch 5: Your tools, devices and where things run

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 5.1 | Which operating system does your laptop run? (I checked: ...) | `runtime.laptop_os` | `"windows"` | the laptop automation is Windows-only and experimental; on macOS and Linux those scripts need porting ([docs/porting-to-other-os.md](../docs/porting-to-other-os.md)) |
| 5.2 | Which AI agent do you use? (I am: ...) | `agent.primary` | `"claude-code"` | only Claude Code was tested; other agents follow the same files, with the fallbacks in [docs/agents.md](../docs/agents.md) |
| 5.3 | How much may unattended jobs and role sessions do without asking? | `agent.permission_posture` | `"accept-edits"` | `bypass` (everything, only on a machine you trust; unattended jobs need it, the original ran its server this way), `accept-edits`, or `ask` |
| 5.4 | Any model preferences for ordinary and for long or hard work? | `agent.default_model`, `agent.heavy_model` | `""`, `""` (the agent's default) | job and role models |
| 5.5 | (Propose) Where does your agent read skills? | `agent.skills_dir` | `".claude/skills"` | setup copies `_agent/skills/*` there (PLAYBOOK 7.3). In Claude Code: `.claude/skills` inside the vault (project) or `~/.claude/skills` (user). Other agents: the folder their documentation names for Agent Skills, if any. Without skill support keep the default and skip the copy in PLAYBOOK 7.3: such agents read `_agent/skills/<id>/SKILL.md` |
| 5.6 | How does your vault sync between devices? | `storage.provider` | `"google-drive"` | `google-drive` (documented default: desktop sync on the laptop, an rclone mount on a server), `onedrive`, `dropbox`, `icloud`, `syncthing`, `git`, `local`; see [docs/storage.md](../docs/storage.md) |
| 5.7 | (Confirm) The vault's path on this laptop | `paths.vault` | `""` | informational for agents, job prompts and laptop scripts; the tools never write to it implicitly. Windows: e.g. `G:/My Drive/Uni`. macOS: Google Drive's folder `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/Uni` contains the account address, so record a link made outside it instead (`ln -s "<that path>" ~/Uni`, then `~/Uni`), or leave the key empty (PLAYBOOK, "Vault location") |
| 5.8 | Is there any folder with private documents agents must never open? | `paths.never_open` | `["**/private/**"]` | tools and agents never read these globs; the secrets scan skips them |
| 5.9 | (scheduler-local; skip for Minimal) How should scheduled jobs run on the laptop? | `runtime.laptop_scheduler` | `"agent-app"` | `agent-app` (the agent's desktop app runs them; In Claude Code: desktop "Scheduled" tasks, the app must be open), `os` (an OS scheduler starts the agent CLI headless; Windows Task Scheduler, experimental), `none` |
| 5.10 | (scheduler-local; only for `os`, or agents other than Claude Code) The agent's command line and headless command | `agent.cli`, `agent.headless_command` | `"claude"`, `""` (built-in Claude Code command) | the template uses `{model}`, `{effort}`, `{permission}`, `{title}`, `{prompt_file}`; untested for other agents |
| 5.11 | Will any of your agent sessions run in the cloud (hosted sessions that can't see laptop files)? | `runtime.use_cloud_sessions` | `false` | cloud sessions can only create files in the vault, so they need the `inbox-sync` module |
| 5.12 | Do you want an always-on server (a cloud VM or a spare computer at home)? | `runtime.use_vm` | `false` | adds the `vm` module (see the trade-off below) |
| 5.13 | Which calendar do you use, and may agents read and write it through your agent's connector? | `calendar.provider` | `"google"` | `google`, `other` (whatever connector your agent has) or `none` (the week plan's day lines become the schedule) |
| 5.14 | Do you want phone pushes when something needs you? | `notify.provider` | `"ntfy"` | `ntfy` (free phone app) or `none` (everything is logged, nothing is sent) |
| 5.15 | Do you write by hand on a tablet, with an app that can export PDFs? | (decides `handwritten-notes`) | | details in batch 9 |

**Where things run** (5.11 and 5.12), the trade-off to explain in a few lines:

| Runtime | Good | Limits |
|---|---|---|
| Laptop only | free; sessions edit the vault directly | stops when the laptop sleeps or the agent app is closed; scheduled tasks start late and catch up on wake |
| Cloud agent sessions | run with the laptop off | need a git repository, can't run in bypass-permissions mode, can't read laptop files (they write through update notes) |
| Always-on server (`vm`) | always on; can run in bypass mode, runs scheduled jobs and persistent role sessions, reachable from the phone | costs money and needs maintenance. The original: an `e2-custom-small` machine with 4 GB RAM on Google Cloud at roughly $21 a month, as an example; a home server (e.g. WSL2 on an old laptop) costs electricity |

---

*Here the agent shows the module menu ([PLAYBOOK.md](PLAYBOOK.md) step 3, [presets.md](presets.md)). The batches below are asked only for the chosen modules.*

---

## Batch 6: Schedules

Ask only for jobs of enabled modules. Every time is local (`term.timezone`, `"HH:MM"`), every day `"Mon"` ... `"Sun"`. The defaults are the original system's values, an example only. Most jobs are installed switched off; *whether* a job runs is decided in PLAYBOOK step 7.8, *when* it runs is decided here.

| # | Ask (simply) | Keys | Default (original, example only) | Why it matters |
|---|---|---|---|---|
| 6.1 | (daily-prep) When are you usually done planning tomorrow? The first evening run should come after that. Do you want a second evening run that catches late changes? | `schedule.daily_prep` | `["17:30", "19:30"]` | the first run writes tomorrow's prep note, later runs only check for changes |
| 6.2 | (daily-prep) When does your study day start? The morning check should run before it. | `schedule.prep_check` | `"07:30"` | verifies today's prep note against the calendar and repairs it |
| 6.3 | (check-in) When do you want to look back on your week? Which day leaves a buffer for catch-up? Weekly or every two weeks? | `schedule.check_in` = `{ day, time, every }` | `{ day = "Sat", time = "19:45", every = "week" }` | one interactive session that asks you once for the week's results. Thursday to Sunday covers the current week, Monday to Wednesday the previous one; `every = "2 weeks"` runs in odd term weeks only |
| 6.4 | (check-in) When should next week's page be created? | `schedule.week_page` = `{ day, time }` | `{ day = "Sun", time = "10:00" }` | a run from Friday to Sunday creates next week's page; Monday to Thursday creates the current week's page (so Monday morning works too) |
| 6.5 | (heartbeat) When should the watcher look on weekdays, and on which days? | `schedule.heartbeat`, `schedule.heartbeat_days` | `["07:50", "13:05", "18:05"]`, `["Mon", "Tue", "Wed", "Thu", "Fri"]` | the original: after the morning prep check, before the midday jobs, after the study day. Most runs cost nothing (a pre-check decides) |
| 6.6 | (heartbeat) And at the weekend? | `schedule.heartbeat_weekend`, `schedule.heartbeat_weekend_days` | `["09:00", "17:40"]`, `["Sun"]` | `[]` = never; the original skipped the check-in day |
| 6.7 | (inbox-sync) When should waiting update notes be applied as a safety net? In which window may the poll start extra runs? | `schedule.inbox_sync`, `schedule.inbox_poll_window`, `schedule.inbox_poll_every_min`, `schedule.inbox_poll_min_gap_min` | `["07:15", "13:15", "18:15"]`, `"07:00-22:00"`, `10`, `60` | fixed runs plus a cheap poll that starts the sync within minutes of a new note (at most once per gap) |
| 6.8 | (lecture-rundowns) When should the skim job run? An evening run covers the next morning's lecture. | `schedule.lecture_skim`, `schedule.lecture_skim_days` | `["10:30"]`, `["Mon", "Wed"]` | pick a time that ends `study.rundowns.skim_lead_hours` before the earliest skimmed lecture; the job runs only in teaching weeks when `term.last_lecture_day` is set |
| 6.9 | (quiz-coaching) Should a job build the quiz prep sheet a few days before each quiz? On which dates, at what time? | `schedule.quiz_prep`, `schedule.quiz_prep_dates` | `["09:00"]`, `""` (never runs) | dates like `"2026-11-07; 2026-12-05"`; add more when quiz dates are announced |
| 6.10 | (planning) Earliest start of a study block, weekday stop, latest block, focus span and break? | `schedule.day_start`, `schedule.weekday_stop`, `schedule.study_cutoff`, `schedule.focus_minutes`, `schedule.break_minutes` | `"08:00"`, `"18:15"`, `"19:00"`, `70`, `10` | the planner's house rules; the optional `deadline-audit` job runs once at `day_start` on `term.last_lecture_day` |
| 6.11 | (roles) Do you want one page each day listing what waits on you? At what time, on which days? | `schedule.waiting_on_you`, `schedule.waiting_on_you_days` | `["19:00"]`, every day | the optional `waiting-on-you` job; pick a time before your quiet hours when you can still act |
| 6.12 | (vault-watch) When should the watcher run? (default is fine for most) | `schedule.vault_watch` | `["08:17", "13:17", "18:17", "22:17"]` | it also runs at logon |
| 6.13 | (vm) When should the server's weekly performance verdict run? | `schedule.vm_verdict` = `{ day, time }` | `{ day = "Sun", time = "19:30" }` | says whether the server is big enough |
| 6.14 | (cockpit) From which hour should the prep card show tomorrow's note, and when should a missing note count as late? | `cockpit.prep_switch_hour`, `cockpit.prep_warn_after` | `18`, `"19:30"` | match them to 6.1 |

## Batch 7: Calendars and block notation

For `planning` and `daily-prep` (and the cockpit's calendar view).

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 7.1 | What are your calendars called? One for classes, one for study blocks, one for other events, one for busy time? | `calendar.courses`, `calendar.study_blocks`, `calendar.events`, `calendar.busy` | `"Courses"`, `"Study blocks"`, `"Events"`, `"Busy"` | agents find calendars by name at every run; ids are never stored. The planner writes only study blocks; classes are read-only, the busy calendar only shows busy time |
| 7.2 | How should lectures and exercise classes be titled in the class calendar? | `calendar.lecture_prefix`, `calendar.exercise_prefix` | `"L:"`, `"E:"` | `L: AD`, `E: AD`; everything else in that calendar counts as a graded fixture |
| 7.3 | Keep the default block notation for study-block titles, or define your own? (table below) | `calendar.notation` | `"default"` | a glance at the week says what each block is for, and machines can parse it. A custom notation is written into `semester/planning-system.md`; then set `"custom"` and match `heartbeat.non_study_block_prefixes` and the cockpit's title patterns |
| 7.4 | May the planner change study blocks without asking first, as long as it lists every change? | `calendar.standing_approval` | `false` | `false`: it proposes and waits for your yes. The original student switched it on after the first weeks |
| 7.5 | Where do you usually study? (written into every block until you name real places) | `calendar.default_location` | `""` | time lost finding a room was a real cost in the original |

The default block notation (it is a default; the student can change it):

| Notation | Meaning |
|---|---|
| `X_` | X is the main subject of the block |
| `X, Y` | the order the subjects are worked in |
| `(X)` | optional |
| `[X]` | reading ahead for the next lecture or exercise class |
| `OP` | optional personal (gym, errands), not a study block |
| `(deep)` | a long focus block |

Examples: `AD_, DM` · `AD_ Sheet 6` · `LA_ quiz prep, (PROG)` · `[DM]` · `OP Gym`.

## Batch 8: Phone pushes and the push gate

For `notifications` (and `heartbeat`, which pushes through the same gate). Every push passes one gate with these rules; offer them as defaults.

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 8.1 | The public ntfy server, or your own? | `notify.ntfy_server` | `"https://ntfy.sh"` | where pushes are posted |
| 8.2 | (Propose) The secret topic lives in a file outside the vault | `notify.ntfy_topic_file` | `"~/.config/uni-os/ntfy-topic"` | only the path is in the config; the student creates the file (PLAYBOOK 7.7). `doctor` errors if it points inside the vault |
| 8.3 | At most how many pushes a day, from everything together? At least how many hours apart? | `notify.max_per_day`, `notify.min_gap_hours` | `3`, `2` | one budget for all senders |
| 8.4 | When should your phone stay silent? | `notify.quiet_hours` | `"21:00-07:30"` | pushes in this window are held, not queued: the sender raises the problem again later if it is still true |
| 8.5 | After how long may the same problem be pushed again? | `notify.dedupe_hours` | `24` | no repeats about one problem |
| 8.6 | Which graded fixtures need silence (timed quizzes, orals, timed online tasks)? Should the exam session be quiet except for urgent things? | `notify.quiet_windows` | `[]` | propose windows from the assessments' `dates`. A window holds every push, urgent ones too, and the heartbeat skips its runs (right for a two-hour quiz). For a long period add `urgent_ok = true`: urgent and direct pushes pass and the heartbeat keeps running. Shapes: `{ from, to, reason }` with dates or `"YYYY-MM-DD HH:MM"`, or weekly `{ day, from, to, until, reason }` |
| 8.7 | What title should pushes show? Should tapping a push open something? | `notify.title`, `notify.default_click` | `"Uni OS"`, `""` | Claude Code users may use `https://claude.ai/code` |
| 8.8 | (Keep, don't ask) never "all good"; every push names its problem; no personal details | `notify.never_all_good`, `notify.require_id`, `notify.block_personal` | `true`, `true`, `true` | silence is the norm; the gate refuses "all good" texts, pushes without a problem id, and texts with mail addresses, links or long numbers |
| 8.9 | If you write in another language: how would "all good" look in it? | `notify.extra_all_good_patterns` | `[]` | regular expressions the gate also refuses, e.g. `["alles (gut\|ok)"]` |
| 8.10 | (inbox-sync) After how many hours does a waiting update note count as stuck? (Done taps wait longer by design) | `notify.inbox_stale_hours`, `notify.inbox_stale_hours_taps` | `4`, `14` | the one threshold every sender uses |
| 8.11 | (heartbeat) Should the watcher only ask the owning role for moves, or act itself? | `heartbeat.act_mode` | `"safe"` | start with `safe`; switch to `full` only after a few weeks and an evaluation |
| 8.12 | (heartbeat) How should it ask you its one daily question? | `heartbeat.ask_mode` | `"auto"` | `session` (a question session on the always-on server), `inline` (the question is the push), `auto` (session on the server, else inline) |

The other `[notify]` keys (`max_length`, `hold_max_hours`, `direct_priority`) are tuning knobs; keep their defaults.

## Batch 9: Add-ons

Ask each group only if its module is enabled.

### Roles and the coordinator (`roles`)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.1 | One agent session that reads the role files as needed (fine to start), or a coordinator plus one session per role? Which roles? | (no key; decides step 7.9) | single session | parallel sessions need cross-session messaging (In Claude Code: built in) |
| 9.2 | What should the coordinator session be called? | `agent.coordinator_title` | `"Uni coordinator"` | other sessions address it by title |
| 9.3 | When should a long session hand over to a fresh one? At what share of your weekly and 5-hour usage limits should side sessions stop or pause? How many helper agents at once? | `agent.context_refresh_tokens`, `agent.usage_stop_weekly_pct`, `agent.usage_pause_5h_pct`, `agent.max_helpers` | `300000`, `90`, `90`, `2` | a long-lived session re-reads its whole context every turn; recycling it is the main cost lever |

### Handwritten notes (`handwritten-notes`)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.4 | Which note app? | `study.handwriting_app` | `""` | named in the rules |
| 9.5 | Default folder names (`<course folder> handwritten`) or your own? | `courses[].handwritten_folder` | `""` (= `<folder> handwritten`) | `uni-os init` creates the folders; the app exports PDFs into them |
| 9.6 | Does the app keep its own data folder inside the vault? Its own export folder for notebooks that belong to no course? | `paths.handwriting_app_data`, `paths.handwriting_app_exports` | `""`, `""` | the data folder is never touched or read; the export folder is read-only |
| 9.7 | Any private folder of the app agents must never open? | `paths.never_open` | `["**/private/**"]` | add e.g. `"Notes App/PDF/private/**"` |

### Obsidian and the cockpit (`obsidian`, `cockpit`)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.8 | (obsidian) Colours for the non-course areas, or the defaults? | `obsidian.area_colours.me`, `.progress`, `.semester`, `.deadline`, `.agent`, `.course` | `"#F6BF26"`, `"#00BCD4"`, `"#795548"`, `"#EF6C00"`, `"#6E7681"`, `"#607D8B"` | callouts, graph groups, canvas; keep them distinct from each other and from the course colours |
| 9.9 | (cockpit) Which layout and start page first? Open it when Obsidian starts? Colour mode? | `cockpit.layout`, `cockpit.default_tab`, `cockpit.open_on_startup`, `cockpit.color_mode` | `"focus"`, `"home"`, `false`, `"accent"` | first-run settings; later the plugin's own settings win |
| 9.10 | (cockpit) Other names a course goes by in titles (e.g. a platform name)? | `courses[].aliases`, `courses[].detect` | `[]`, `""` | the cockpit recognises the course in calendar titles and table rows |
| 9.11 | (cockpit) Do you want the AI side panel on your own API key? Live calendars? | (no keys: secrets go into Obsidian's secret storage) | no | the student creates and links the key and the private calendar addresses themselves (PLAYBOOK 7.5); billed separately from any chat subscription |

### Inbox sync (`inbox-sync`)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.12 | Which sessions write only by creating files (cloud sessions, a chat project, the cockpit's Done taps)? | (no key; confirms the module is needed) | | without such writers the module is not needed |
| 9.13 | Should a stuck note reach your phone? | (decided by the modules: one sender per setup) | | with `notifications` or `vm` enabled, their outcome checks send it; see the notifications README |

### Vault watch (`vault-watch`, Windows, experimental)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.14 | Should new alerts also reach your phone (one generic push per run)? | `vault_watch.push` | `false` | toasts on the laptop are always on |
| 9.15 | Extra top-level folders with official material? App-output folders (logged, not alerted)? Archives where any change should alert? Folders that must never even be listed? | `vault_watch.source_top_dirs`, `vault_watch.quiet_dirs`, `vault_watch.frozen_dirs`, `vault_watch.never_list` | `[]`, `[]`, `["z_archive", "archive"]`, `["private", "*/private"]` | what the watcher looks at |
| 9.16 | Extra note subfolders in a course folder (e.g. `code`)? | `courses[].watch_note_subfolders` | `[]` | counted as notes, not as official files |

### Course files fetch (`course-files-fetch`; the pick-up task is Windows-only, experimental)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.17 | Extra official pages per course (e.g. a slides server linked from the platform)? Does the platform serve files from another host? | `courses[].fetch_sources`, `course_fetch.extra_hosts` | `[]`, `[]` | only files downloaded from allowed hosts are filed |
| 9.18 | Are some solutions only allowed after a date (after a quiz or an oral)? | `course_fetch.date_guards` | `[]` | `{ course, pattern, not_before, reason }`: such files stay out of the vault before their date |
| 9.19 | If a file exists in two languages, which one? | `course_fetch.preferred_language` | `"English"` | one language per file |
| 9.20 | Which browser may the agent drive, if several are connected? Where does it download to? | `course_fetch.browser_hint`, `course_fetch.downloads_dir` | `""`, `""` (your Downloads folder) | the fetch drives your own logged-in browser; passwords stay with you |

### Always-on server (`vm`)

| # | Ask (simply) | Keys | Default | Why it matters |
|---|---|---|---|---|
| 9.21 | Cloud VM, a spare computer at home, or another Linux box? | `vm.provider` | `"gcp"` | `gcp`, `home-server`, `other`; [modules/vm/INSTALL.md](../modules/vm/INSTALL.md) or [HOME-SERVER.md](../modules/vm/HOME-SERVER.md) |
| 9.22 | Monthly budget for the alert, currency, and any monthly cloud credit your subscription includes? | `vm.budget_month`, `vm.budget_currency`, `vm.monthly_credit` | `13`, `"EUR"`, `0` | the budget alert and the weekly verdict's cost view |
| 9.23 | (Cloud) Zone and machine size? | `vm.zone`, `vm.machine_type`, `vm.disk_gb` | `"us-central1-a"`, `"e2-custom-small-4096"`, `30` | used in the install commands; memory is the binding constraint (about 360 MB per working role session) |
| 9.24 | (Propose) ssh alias, Linux user, where the vault appears on the server, the drive remote's name | `vm.host_alias`, `vm.linux_user`, `vm.mount_path`, `vm.drive_remote` | `"uni-vm"`, `""`, `"~/Uni"`, `"uni-drive"` | host-only values (vault path on the host, agent binary) live in the server's own `host.env` |
| 9.25 | Deploy the framework from your laptop, or clone it on the server from a public URL? | `vm.repo_url` | `""` (deploy from the laptop) | updates with `uni-vm update` need the URL |
| 9.26 | What should the server's remote sessions be called in your agent app? | `vm.remote_control_name` | `"Uni (VM)"` | In Claude Code: the Remote Control environment's name |
| 9.27 | Which recurring jobs move to the server, and which roles run there permanently? Keep a laptop failover copy? | (no keys: host-side state, `uni-vm jobs on`, `uni-vm roles add`) | failover: no | every job runs on one machine; the laptop copy is paused at the moment the server's is switched on |
| 9.28 | Folders the server's hourly notes history must skip, beyond the private ones? | `vm.history_exclude` | plugins, `node_modules`, the server's snapshot file | the history is a git copy of the notes on the server |

`vm.project` (the cloud project id) is written only into the student's own config, never into anything shared.

---

## Writing the answers

A course answered in batches 2 and 3 becomes (fictional student, from [examples/alex.toml](../examples/alex.toml)):

```toml
[[courses]]
id = "algo"
name = "Algorithms and Data Structures"
short = "AD"
folder = "AD"
slug = "ad"
colour = "#1e66f5"
lecture_slots = ["Tue 10:15-12:00", "Thu 10:15-12:00"]
exercise_slots = ["Wed 14:15-16:00"]
sheet_release = "Thu 12:00"
sheet_due = "Thu 23:59, one week later"
session_rule = "The exercise session of week n discusses sheet n-1 and introduces sheet n."
official_subfolders = ["AD assignments", "AD slides & script"]
assistance = "hints-only"
integrity = "Sheets are individual work; AI may explain concepts, never produce solutions."

  [[courses.assessments]]
  name = "In-class quizzes"
  kind = "quiz"
  schedule = "weeks 4, 8 and 12, in the exercise session"
  counts_for = "bonus"
  assistance = "hints-only"
  points_max = 10
  dates = ["2026-10-14 14:15", "2026-11-11 14:15", "2026-12-09 14:15"]

  [courses.bonus]
  scheme = "threshold"
  description = "+0.25 grade bonus at 80 % of all sheet points"
  max_bonus = 0.25
  rule = "Sum of sheet points over the term; quizzes count double."
  target = "80 % of all sheet points"
```

Then run `python tools/uni_os.py config validate` (PLAYBOOK step 4).
