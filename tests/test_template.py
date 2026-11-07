"""Tests for the template engine: values, blocks, whitespace, errors."""

import datetime as dt
import unittest

import support  # noqa: F401  (puts tools/ on sys.path)
from uni_os import template as t
from uni_os.errors import TemplateError

CFG = {
    "student": {"name": "Alex Example", "dictates": False, "pronouns": ""},
    "university": {"short": "EIT"},
    "term": {"label": "Autumn 2026", "week0_monday": dt.date(2026, 9, 14), "holidays": []},
    "study": {"formats": ["html", "md"], "chunk_words": 750},
    "notify": {"max_per_day": 3, "min_gap_hours": 1.5, "provider": "none"},
    "courses": [
        {
            "id": "algo",
            "name": "Algorithms",
            "short": "AD",
            "folder": "A&D",
            "slug": "ad",
            "slots": ["Mon 10:15-12:00", "Thu 10:15-12:00"],
            "assessments": [{"name": "Sheets", "kind": "sheet"}, {"name": "Quiz", "kind": "quiz"}],
        },
        {"id": "dm", "name": "Discrete Maths", "short": "DM", "folder": "DM", "slug": "dm", "slots": [], "assessments": []},
    ],
}


def ctx(enabled=("core", "progress")):
    return t.build_context(CFG, enabled=list(enabled), generated={"date": "2026-11-07", "version": "0.1.0"})


def render(text, **kw):
    return t.render(text, ctx(**kw), filename="test.md")


class ValueTests(unittest.TestCase):
    def test_simple_value_and_whitespace_inside_braces(self):
        self.assertEqual(render("Hi {{student.name}} / {{ student.name }}"), "Hi Alex Example / Alex Example")

    def test_list_joined_with_comma(self):
        self.assertEqual(render("{{study.formats}}"), "html, md")

    def test_bool_number_float_date(self):
        self.assertEqual(render("{{student.dictates}} {{notify.max_per_day}} {{notify.min_gap_hours}} {{term.week0_monday}}"), "false 3 1.5 2026-09-14")

    def test_generated_values(self):
        self.assertEqual(render("{{generated.date}} {{generated.version}}"), "2026-11-07 0.1.0")

    def test_list_index_and_id_lookup(self):
        self.assertEqual(render("{{courses.0.short}} {{courses.dm.name}}"), "AD Discrete Maths")

    def test_unknown_roots_left_untouched(self):
        text = "{{date}} {{date:YYYY-MM-DD}} {{title}} {{week.nn}} {{foo.bar}} {{time:HH:mm}}"
        self.assertEqual(render(text), text)

    def test_non_tag_braces_untouched(self):
        text = r"$\frac{a}{{b}}$ and {{{x}}} and {{ }}"
        self.assertEqual(render(text), text)

    def test_escape_renders_literal_tag(self):
        self.assertEqual(render(r"Write \{{course.name}} in templates."), "Write {{course.name}} in templates.")

    def test_escape_of_unknown_root_keeps_backslash(self):
        self.assertEqual(render(r"\{{title}}"), r"\{{title}}")

    def test_modules_value(self):
        self.assertEqual(render("{{modules.progress}} {{modules.vm}} {{modules.enabled}}"), "true false core, progress")


class BlockTests(unittest.TestCase):
    def test_each_courses_binds_course_and_loop_vars(self):
        out = render("{{#each courses}}{{@index}}:{{course.short}}{{#if @first}}(first){{/if}}{{#unless @last}}, {{/unless}}{{/each}}")
        self.assertEqual(out, "0:AD(first), 1:DM")

    def test_nested_each_over_assessments_binds_item(self):
        out = render("{{#each courses}}[{{course.short}}:{{#each course.assessments}}{{item.name}}/{{course.slug}}{{#unless @last}},{{/unless}}{{/each}}]{{/each}}")
        self.assertEqual(out, "[AD:Sheets/ad,Quiz/ad][DM:]")

    def test_each_else_on_empty_list(self):
        out = render("{{#each courses}}{{course.short}}:{{#each course.assessments}}{{item.kind}} {{else}}none{{/each}};{{/each}}")
        self.assertEqual(out, "AD:sheet quiz ;DM:none;")

    def test_each_over_scalar_list_binds_item(self):
        self.assertEqual(render("{{#each study.formats}}<{{item}}>{{/each}}"), "<html><md>")

    def test_if_else_and_unless(self):
        self.assertEqual(render("{{#if student.dictates}}yes{{else}}no{{/if}}"), "no")
        self.assertEqual(render("{{#unless student.dictates}}typing{{/unless}}"), "typing")

    def test_truthiness(self):
        self.assertEqual(render("{{#if student.pronouns}}x{{else}}empty{{/if}}"), "empty")
        self.assertEqual(render("{{#if notify.provider}}x{{else}}none-is-false{{/if}}"), "none-is-false")
        self.assertEqual(render("{{#if term.holidays}}x{{else}}empty-list{{/if}}"), "empty-list")
        self.assertEqual(render("{{#if notify.max_per_day}}three{{/if}}"), "three")

    def test_if_modules(self):
        self.assertEqual(render("{{#if modules.progress}}P{{/if}}{{#if modules.vm}}V{{else}}-{{/if}}"), "P-")

    def test_comparisons(self):
        self.assertEqual(render('{{#if term.label == "Autumn 2026"}}A{{/if}}{{#if term.label != "Spring"}}B{{/if}}'), "AB")
        self.assertEqual(render("{{#if notify.max_per_day == 3}}three{{/if}}"), "three")
        self.assertEqual(render('{{#if study.formats contains "html"}}H{{/if}}{{#if study.formats contains "pdf"}}P{{/if}}'), "H")
        self.assertEqual(render('{{#if term.week0_monday == "2026-09-14"}}date-eq{{/if}}'), "date-eq")
        self.assertEqual(render("{{#if student.dictates == false}}f{{/if}}"), "f")

    def test_standalone_block_lines_are_removed(self):
        text = "| Course |\n|---|\n{{#each courses}}\n| {{course.short}} |\n{{/each}}\nend\n"
        self.assertEqual(render(text), "| Course |\n|---|\n| AD |\n| DM |\nend\n")

    def test_standalone_with_indentation_and_crlf(self):
        text = "a\r\n  {{#if modules.progress}}  \r\nb\r\n  {{/if}}\r\nc"
        self.assertEqual(render(text), "a\r\nb\r\nc")

    def test_inline_blocks_keep_surrounding_text(self):
        self.assertEqual(render("x {{#if modules.vm}}vm{{else}}novm{{/if}} y"), "x novm y")

    def test_foreign_blocks_pass_through(self):
        text = "{{#if foo}}keep {{student.name}}{{else}}other{{/if}}"
        self.assertEqual(render(text), "{{#if foo}}keep Alex Example{{else}}other{{/if}}")

    def test_extra_roots(self):
        c = ctx()
        c["week"] = {"nn": "08", "number": 8}
        out = t.render("Week {{week.nn}} {{#if week.number}}ok{{/if}} {{title}}", c, roots=t.INSTALL_ROOTS | {"week"})
        self.assertEqual(out, "Week 08 ok {{title}}")

    def test_bindings_for_path_expansion(self):
        tpl = t.compile("{{course.folder}}/{{course.slug}}.md")
        self.assertEqual(tpl.render(ctx(), bindings={"course": CFG["courses"][0]}), "A&D/ad.md")
        self.assertTrue(t.expands_per_course("vault/{{ course.folder }}/x.md"))
        self.assertFalse(t.expands_per_course("vault/{{paths.inbox}}/x.md"))
        self.assertTrue(t.expands_per_error_log("{{course.folder}}/{{error_log.file}}"))


class ErrorTests(unittest.TestCase):
    def assertTemplateError(self, text, *fragments, line=None):
        with self.assertRaises(TemplateError) as cm:
            render(text)
        message = str(cm.exception)
        self.assertIn("test.md", message)
        for frag in fragments:
            self.assertIn(frag, message)
        if line is not None:
            self.assertEqual(cm.exception.line, line)
        return cm.exception

    def test_missing_key_reports_file_line_key_and_suggestion(self):
        exc = self.assertTemplateError("ok\n{{student.nmae}}", "student.nmae", "did you mean 'student.name'", line=2)
        self.assertEqual(exc.key, "student.nmae")

    def test_missing_table(self):
        self.assertTemplateError("{{vm.host_alias}}", "vm.host_alias", "no [vm] table")

    def test_missing_key_in_course_names_the_course(self):
        self.assertTemplateError("{{#each courses}}{{course.colour}}{{/each}}", "course.colour", "for course 'algo'")

    def test_course_outside_loop(self):
        self.assertTemplateError("{{course.name}}", "outside a course loop")

    def test_item_outside_loop(self):
        self.assertTemplateError("{{item.name}}", "outside")

    def test_loop_var_outside_loop(self):
        self.assertTemplateError("{{@index}}", "@index")

    def test_unclosed_block(self):
        self.assertTemplateError("a\n{{#if modules.core}}x", "never closed", line=2)

    def test_unmatched_close(self):
        self.assertTemplateError("{{/each}}", "without a matching")

    def test_mismatched_close(self):
        self.assertTemplateError("{{#each courses}}{{/if}}", "closes {{#each}}")

    def test_double_else(self):
        self.assertTemplateError("{{#if modules.core}}a{{else}}b{{else}}c{{/if}}", "second {{else}}")

    def test_each_needs_list(self):
        self.assertTemplateError("{{#each student}}{{/each}}", "needs a list")

    def test_table_cannot_be_printed(self):
        self.assertTemplateError("{{student}}", "is a table")

    def test_list_of_tables_cannot_be_printed(self):
        self.assertTemplateError("{{courses}}", "list of tables")

    def test_unsupported_expressions(self):
        self.assertTemplateError("{{student.name | upper}}", "unsupported expression")
        self.assertTemplateError("{{#if student.name and student.handle}}x{{/if}}", "unsupported condition")

    def test_modules_sub_key_is_error(self):
        self.assertTemplateError("{{modules.core.x}}", "no sub-keys")

    def test_missing_key_inside_if_condition_is_error(self):
        self.assertTemplateError("{{#if student.nickname}}x{{/if}}", "student.nickname")

    def test_unknown_module_id_warns(self):
        warnings = []
        out = t.render("{{#if modules.nope}}x{{/if}}", ctx(), filename="w.md", known_modules=["core"], warnings=warnings)
        self.assertEqual(out, "")
        self.assertEqual(len(warnings), 1)
        self.assertIn("unknown module id 'nope'", warnings[0])


class HelperTests(unittest.TestCase):
    def test_is_truthy(self):
        for value in (False, 0, 0.0, "", "  ", "none", "None", [], {}, None):
            self.assertFalse(t.is_truthy(value), value)
        for value in (True, 1, "x", ["a"], {"a": 1}, dt.date(2026, 1, 1)):
            self.assertTrue(t.is_truthy(value), value)

    def test_find_tags_skips_escaped_and_foreign(self):
        text = "{{course.name}} \\{{student.name}} {{title}} {{#if modules.x}}{{/if}}"
        tags = [tag for _line, tag in t.find_tags(text, t.KNOWN_ROOTS)]
        self.assertEqual(tags, ["{{course.name}}", "{{#if modules.x}}"])

    def test_compile_once_render_many(self):
        tpl = t.compile("{{course.short}}")
        outs = [tpl.render(ctx(), bindings={"course": c}) for c in CFG["courses"]]
        self.assertEqual(outs, ["AD", "DM"])


if __name__ == "__main__":
    unittest.main()
