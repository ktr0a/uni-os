---
type: resource
audience: both
updated: {{generated.date}}
tags: [uni/resources]
---
# Sources and links

Where everything lives outside this vault, which source wins, and which documents count as the real source for each course. Agents add a line here whenever they learn a new location (append; say when and how you found it).

**Authority order for course facts:** (1) what the student says now, (2) the official course pages ({{university.lms}} course page with its announcements, the course website), (3) the course catalogue, (4) the course cards in this vault (they record what was checked and when), (5) the course-facts skill, (6) predicted plans (topic plans, last year's material), (7) anything else derived. Announcements beat file timestamps; the newest dated fact wins among equals.

## Official course pages
| Course | {{university.lms}} | Website | Other platforms | Recordings |
|---|---|---|---|---|
{{#each courses}}| {{course.short}} | {{#if course.lms_url}}{{course.lms_url}}{{else}}(add){{/if}} | {{#if course.website}}{{course.website}}{{else}}-{{/if}} | {{#if course.platforms}}{{course.platforms}}{{else}}-{{/if}} | {{#if course.recordings}}{{course.recordings}}{{else}}-{{/if}} |
{{/each}}

- University website: {{#if university.website}}{{university.website}}{{else}}(add){{/if}}
- {{university.lms}}: {{#if university.lms_url}}{{university.lms_url}}{{else}}(add){{/if}}
- Course catalogue: {{#if university.catalogue}}{{university.catalogue}}{{else}}(add; note the term code it uses){{/if}}
- Recording portal: {{#if university.recordings}}{{university.recordings}}{{else}}(add, or "none"){{/if}}. Note which series are locked and which older series stand in for them.
- Archives of previous years' sheets and scripts (with or without official solutions): (add where they are public; anything behind a login you don't have is "not obtainable", never enter a password for an agent)

Logged-in pages are read only through the student's own signed-in browser, strictly read-only: never start a quiz attempt, submit, post or change a setting; the password step stays with the student.

## This vault as the file store
Each course folder holds the official files (under their official names, add-only) next to the notes. Uploads from the official pages may lag a day or two behind the release: say so when a file is "missing".

| Folder | Official subfolders | Notes and agent material |
|---|---|---|
{{#each courses}}| `{{course.folder}}/` | {{#each course.official_subfolders}}`{{item}}/`{{#unless @last}}, {{/unless}}{{else}}(none configured yet){{/each}}{{#if modules.handwritten-notes}}; app exports in `{{course.handwritten_dir}}/`{{/if}} | card `{{course.slug}}.md`, `backlog.md`, `notes/`, `reference/` |
{{/each}}

Record naming patterns here once you have seen a few files (e.g. "`assignments/sheetNN.pdf`, solutions `assignments/solutions/solutionNN.pdf`, lecture notes `script and slides/lecture-NN.pdf`"). Watchers and fetch jobs use them to recognise new files.

## Real source per course (for rundowns and study pages; cite section and page or slide)
{{#each courses}}- **{{course.short}}:** {{#if course.real_source}}{{course.real_source}}{{else}}(which documents say what was lectured, in order, e.g. "the official weekly handout first, then the script pages"; "the LMS roadmap, then the script sections"; "the lecture deck, and the student says where the lecture stopped"){{/if}}
{{/each}}

## Plans and guides
{{#each courses}}- {{course.short}}: [topic plan](<../{{course.folder}}/reference/{{course.slug}}-topic-plan.md>) (predicted) · [course guide](<../{{course.folder}}/reference/{{course.slug}}-course-guide.md>)
{{/each}}

## TA and third-party sites
Running log with reviews: [ta-websites-log.md](<ta-websites-log.md>). Saved copies of third-party material are listed in the log entry they came from, with their licence status.

## Verification
The last check of all course facts against the official pages: [course-verification.md](<course-verification.md>) (method and run log).

## Other
(Student organisations, tools, study spaces, anything useful that is not course material.)
