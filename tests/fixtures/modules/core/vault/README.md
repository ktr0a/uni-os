# {{university.name}} vault

Generated {{generated.date}} by uni-os {{generated.version}} for {{student.name}} ({{term.label}}).

<!-- uni-os:begin modules -->
| Module | Tier | Summary |
|---|---|---|
{{#each generated.modules}}
| {{item.name}} | {{item.tier}} | {{item.summary}} |
{{/each}}
<!-- uni-os:end modules -->

## Courses
{{#each courses}}
- [{{course.name}}](<{{course.card}}>) colour {{course.colour}} / rgb {{course.colour_rgb}}{{#if @last}} (last){{/if}}
{{/each}}

## Roles
{{#each generated.roles}}
- {{item.title}} ({{item.module}}): {{item.file}}
{{else}}
- no roles
{{/each}}

<!-- uni-os:begin progress -->
{{#if modules.progress}}
Progress lives in progress/.
{{else}}
No progress module.
{{/if}}
<!-- uni-os:end progress -->
{{#if study.formats contains "html"}}
Study pages come as HTML.
{{/if}}
Obsidian placeholders stay: {{date:YYYY-MM-DD}} and {{title}}.
Escaped: \{{student.name}}
