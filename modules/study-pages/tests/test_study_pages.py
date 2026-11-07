"""Tests for the study-pages module scripts (standard library only).

Run from the repository root:
    python -m unittest discover -s modules/study-pages/tests -t .
"""
import contextlib
import datetime
import filecmp
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
SCRIPTS = os.path.join(MODULE, 'scripts')
VAULT_TOOLS = os.path.join(MODULE, 'vault', '_agent', 'tools')
TEMPLATE = os.path.join(MODULE, 'vault', '_templates', 'study-page.html')
sys.path.insert(0, SCRIPTS)

import html2md  # noqa: E402
import check_study_page  # noqa: E402
import html2pdf  # noqa: E402

BS = chr(92)
DAY = datetime.date(2026, 9, 14)


class MirrorTest(unittest.TestCase):
    def test_vault_copies_are_identical(self):
        # The vault copy (installed to <vault>/_agent/tools/) must never drift from scripts/.
        for name in ('html2md.py', 'check_study_page.py', 'html2pdf.py'):
            self.assertTrue(filecmp.cmp(os.path.join(SCRIPTS, name), os.path.join(VAULT_TOOLS, name), shallow=False),
                            f'{name}: vault/_agent/tools copy differs from scripts/')


class Html2MdTest(unittest.TestCase):
    def conv(self, html, rel='ad-test-study-page.html', course=None, cfg=None):
        md, _n = html2md.convert(html, rel, course, cfg, today=DAY)
        return md

    def test_template_twin(self):
        with open(TEMPLATE, encoding='utf-8') as fh:
            md = self.conv(fh.read(), 'ad-big-o-study-page.html')
        head = md.split('---')[1]
        for line in ('type: study-page', 'kind: teaching-page', 'course: algo', 'created: 2026-09-14',
                     'source_html: "ad-big-o-study-page.html"', 'converted: 2026-09-14', 'audience: me',
                     'tags: [uni/algo, study-page]'):
            self.assertIn(line, head)
        self.assertIn('> [!abstract] Markdown copy of [ad-big-o-study-page.html](ad-big-o-study-page.html)', md)
        self.assertIn('Auto-converted on Mon 14 Sep 2026', md)
        self.assertIn('# Big-O notation: comparing how fast functions grow', md)
        self.assertIn('### 1.1 Why constants do not matter *(template sample)*', md)
        self.assertIn('$$1 ' + BS + 'lt ' + BS + 'log n', md)
        self.assertIn('> [!warning] Order of the quantifiers:', md)
        self.assertIn('*Interactive part (quiz, demo or animation): only in the [HTML page](ad-big-o-study-page.html).*', md)
        self.assertNotIn('WIDGETMARK', md)
        self.assertNotIn('Your quiz progress', md)          # data-md="skip"
        self.assertIn('for i = 1..n:\n  for j = i..n:\n    count += 1', md)  # code indentation kept
        self.assertNotIn('```\n\n```', md)                  # empty JS-filled <pre> left out

    def test_math_and_stray_lt(self):
        html = ('<html><head><title>T</title></head><body><p>Inline ' + BS + '(a+b' + BS + ') and '
                + BS + '[x^2' + BS + '] and $1<x$ stays.</p></body></html>')
        md = self.conv(html)
        self.assertIn('Inline $a+b$', md)
        self.assertIn('$$x^2$$', md)
        self.assertIn('$1<x$ stays', md)  # "<x" is not a known tag, so the pre-pass protects it

    def test_callouts_tables_lists_details(self):
        html = ('<body><div class="card trap"><b>Watch out:</b> pitfall text</div>'
                '<div class="card key">plain</div>'
                '<table><tr><th>a|b</th><th>c</th></tr><tr><td>1</td><td>' + BS + '|x' + BS + '|</td></tr></table>'
                '<ol type="i"><li>one</li><li>two</li></ol>'
                '<details><summary>More</summary><p>hidden</p></details>'
                '<details class="hint"><summary>Hint 1</summary><p>h</p></details>'
                '<pre class="language-python"><code>if x:\n    y()</code></pre>'
                '<div aria-hidden="true"><svg></svg></div><p>after</p></body>')
        md = self.conv(html)
        self.assertIn('> [!warning] Watch out:\n> pitfall text', md)
        self.assertIn('> [!note]\n> plain', md)
        self.assertIn('| a' + BS + '|b | c |', md)
        self.assertIn(BS + 'Vert x' + BS + 'Vert', md)
        self.assertIn('- (i) one', md)
        self.assertIn('- (ii) two', md)
        self.assertIn('> [!info]- More', md)
        self.assertIn('> [!tip]- Hint 1', md)
        self.assertIn('```python\nif x:\n    y()\n```', md)
        self.assertNotIn('*Interactive part (quiz', md)  # the aria-hidden svg leaves no widget line
        self.assertIn('after', md)

    def test_plain_mode_details_and_cards(self):
        # Vaults read without Obsidian: no callouts; folded answers become <details> blocks with blank lines inside.
        html = ('<body><div class="card trap"><b>Watch out:</b> pitfall text</div>'
                '<div class="card key">plain</div>'
                '<div class="card key"><ul><li>one</li><li>two</li></ul></div>'
                '<div class="card key"><h4>Covered</h4><p>heaps</p></div>'
                '<details><summary>Answer</summary><p>It is ' + BS + '(n^2' + BS + ').</p></details>'
                '<details class="hint"><summary>Hint 1</summary><p>h</p></details>'
                '<details><summary>Is a &lt; b?</summary></details>'
                '<blockquote>quoted</blockquote></body>')
        md, _n = html2md.convert(html, 'ad-test-study-page.html', today=DAY, plain=True)
        self.assertNotIn('[!', md)
        self.assertIn('> **Markdown copy of [ad-test-study-page.html](ad-test-study-page.html).** '
                      'Auto-converted on Mon 14 Sep 2026', md)
        self.assertIn('only work in the HTML page: open it in the browser.', md)
        self.assertIn('\n> **Watch out:** pitfall text\n', md)          # the card's own bold title leads
        self.assertIn('\n> **Note.** plain\n', md)                       # else a bold label
        self.assertIn('\n> **Note.**\n>\n> - one\n> - two\n', md)       # label on its own line before a list
        self.assertIn('\n> #### Covered\n>\n> heaps\n', md)              # a heading is the title: no label
        self.assertIn('\n<details>\n<summary>Answer</summary>\n\nIt is $n^2$.\n\n</details>\n', md)
        self.assertIn('\n<details>\n<summary>Hint 1</summary>\n\nh\n\n</details>\n', md)
        self.assertIn('\n<details>\n<summary>Is a &lt; b?</summary>\n\n</details>', md)  # summary escaped
        self.assertIn('\n> quoted\n', md)

    def test_plain_mode_template_twin(self):
        with open(TEMPLATE, encoding='utf-8') as fh:
            src = fh.read()
        plain, _n = html2md.convert(src, 'ad-big-o-study-page.html', today=DAY, plain=True)
        obsidian, _n = html2md.convert(src, 'ad-big-o-study-page.html', today=DAY)
        self.assertNotIn('[!', plain)
        self.assertIn('> [!warning] Order of the quantifiers:', obsidian)
        self.assertIn('> **Order of the quantifiers:** first *there exist*', plain)
        self.assertEqual(plain.split('---')[1], obsidian.split('---')[1])  # same properties
        self.assertIn('### 1.1 Why constants do not matter *(template sample)*', plain)
        self.assertIn('*Interactive part (quiz, demo or animation): only in the [HTML page](ad-big-o-study-page.html).*', plain)

    def test_mode_from_flag_or_config(self):
        html = '<html><head><title>LA x</title></head><body><details><summary>Answer</summary><p>a</p></details></body></html>'
        cases = (  # (config obsidian table or None for no key, flags, expect plain)
            (None, [], False), ({'enabled': True}, [], False), ({'enabled': False}, [], True),
            ({'enabled': True}, ['--plain'], True), ({'enabled': False}, ['--obsidian'], False),
        )
        for obs, flags, want_plain in cases:
            with self.subTest(obs=obs, flags=flags), tempfile.TemporaryDirectory() as vault:
                os.makedirs(os.path.join(vault, '_agent'))
                cfg = {'courses': [{'id': 'la', 'slug': 'la', 'folder': 'LA'}]}
                if obs is not None:
                    cfg['obsidian'] = obs
                with open(os.path.join(vault, '_agent', 'uni-os.json'), 'w', encoding='utf-8') as fh:
                    json.dump(cfg, fh)
                page = os.path.join(vault, 'la-x-summary.html')
                with open(page, 'w', encoding='utf-8') as fh:
                    fh.write(html)
                self.assertEqual(html2md.main([page, '--date', '2026-09-14', '--quiet'] + flags), 0)
                with open(page[:-5] + '.md', encoding='utf-8') as fh:
                    out = fh.read()
                self.assertEqual('<summary>Answer</summary>' in out, want_plain, out)
                self.assertEqual('> [!info]- Answer' in out, not want_plain, out)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):  # the modes exclude each other
            html2md.main(['x.html', '--plain', '--obsidian'])

    def test_course_resolution(self):
        cfg = {'courses': [{'id': 'algo', 'slug': 'ad', 'short': 'AD', 'folder': 'A&D', 'name': 'Algorithms'}]}
        # any spelling maps to the course id, the vault-wide `course` property (as on the course card)
        self.assertEqual(html2md.resolve_course('A&D', cfg), 'algo')
        self.assertEqual(html2md.resolve_course('ad', cfg), 'algo')
        self.assertEqual(html2md.resolve_course('a&d', None), 'ad')  # no config: the original's mapping, now generic
        md = self.conv('<body><p>x</p></body>', 'ad-x-skim.html', course='AD', cfg=cfg)
        self.assertIn('course: algo', md)
        self.assertIn('tags: [uni/algo, study-page]', md)
        md = self.conv('<body><p>x</p></body>', 'ad-x-skim.html', cfg=cfg)  # from the file-name prefix
        self.assertIn('course: algo', md)
        self.assertIn('kind: skim', md)  # kind from the file-name suffix when there is no meta tag

    def test_kind_from_the_naming_scheme(self):
        # the study-page skill's names: course slug first, the kind word last
        for name, kind in (('ad-heaps-study-page.html', 'teaching-page'),
                           ('dm-lecture-mon2nov-monoids-skim.html', 'skim'),
                           ('dm-lecture-mon2nov-monoids-rundown.html', 'rundown'),
                           ('ad-weeks3-4-recap.html', 'recap'), ('la-chapter4-summary.html', 'summary'),
                           ('la-running-summary.html', 'summary'), ('ad-sorting-cheatsheet.html', 'cheat-sheet'),
                           ('dm-proof-skeletons-walkthrough.html', 'walkthrough'),
                           ('dm-definitions-deck.html', 'definitions-deck'), ('ad-sheet3-2b-hints.html', 'hint-page'),
                           ('ad-sheet4-mistake-map.html', 'mistake-map'),
                           ('dm-lecture-mon2nov-recall-key.html', 'recall-key'),
                           ('prog-lecture-tue3nov-transcript.html', 'transcript'),
                           ('la-quiz-week8-prep.html', 'quiz-prep'), ('ad-quiz-q2-mock.html', 'mock-quiz'),
                           ('ad-quiz-q2-selfstudy.html', 'quiz-prep')):
            self.assertEqual(html2md.kind_from_name(name), kind, name)

    def test_find_config_json(self):
        with tempfile.TemporaryDirectory() as vault:
            os.makedirs(os.path.join(vault, '_agent'))
            os.makedirs(os.path.join(vault, 'LA', 'notes'))
            with open(os.path.join(vault, '_agent', 'uni-os.json'), 'w', encoding='utf-8') as fh:
                json.dump({'courses': [{'id': 'la', 'slug': 'la', 'folder': 'LA'}]}, fh)
            page = os.path.join(vault, 'LA', 'notes', 'la-x.html')
            with open(page, 'w', encoding='utf-8') as fh:
                fh.write('<html><head><title>LA x</title></head><body><h2>Hi</h2></body></html>')
            self.assertEqual(html2md.find_config(page)['courses'][0]['slug'], 'la')
            self.assertEqual(html2md.main([page, '--date', '2026-09-14', '--quiet']), 0)
            with open(page[:-5] + '.md', encoding='utf-8') as fh:
                out = fh.read()
            self.assertIn('course: la', out)
            self.assertIn('## Hi', out)


class CheckTest(unittest.TestCase):
    def write(self, d, html):
        p = os.path.join(d, 'p.html')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(html)
        return p

    def test_template_is_clean(self):
        errors, warns, _ = check_study_page.check(TEMPLATE)
        self.assertEqual(errors, [])
        self.assertEqual(warns, [])

    def test_lt_detection_and_fix(self):
        with open(TEMPLATE, encoding='utf-8') as fh:
            src = fh.read()
        js_ok = "'$2^{n+1} " + BS + BS + "in O(2^n)$.'"
        self.assertIn(js_ok, src)
        bad = src.replace(js_ok, "'$j<i$ and $2^{n+1} " + BS + BS + "in O(2^n)$.'", 1)
        bad = bad.replace('<p>Let $f, g', '<p>Note $s_1<s_2$. Let $f, g', 1)
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, bad)
            errors, _w, _n = check_study_page.check(p)
            self.assertEqual(len([e for e in errors if 'before a letter' in e]), 2, errors)
            errors, _w, _n = check_study_page.check(p, fix=True)
            errors, _w, _n = check_study_page.check(p)
            self.assertEqual(errors, [])
            with open(p, encoding='utf-8') as fh:
                fixed = fh.read()
            self.assertIn("'$j" + BS + BS + "lt i$", fixed)
            self.assertIn('$s_1' + BS + 'lt s_2$', fixed)

    def test_report_through_a_cp1252_pipe(self):
        # A Windows pipe defaults to cp1252: quoting a formula with a symbol outside it must not crash the
        # report, least of all after --fix has already rewritten the page.
        import subprocess
        with open(TEMPLATE, encoding='utf-8') as fh:
            src = fh.read()
        bad = src.replace('<p>Let $f, g', '<p>Note $\\lambda_1<b ≤ c$. Let $f, g', 1)
        self.assertNotEqual(bad, src)
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, bad)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check_study_page.py'), p],
                               capture_output=True, env=env)
            out = r.stdout.decode('utf-8')
            self.assertEqual(r.returncode, 1, r.stderr.decode('utf-8', 'replace'))  # 1 = errors found, not a crash
            self.assertIn('before a letter', out)
            self.assertIn('≤', out)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check_study_page.py'), p, '--fix'],
                               capture_output=True, env=env)
            self.assertNotIn(b'Traceback', r.stderr)

    def test_structure_checks(self):
        html = ('<html><head><title>x</title></head><body><nav id="nav"><a href="#a">A</a><a href="#zz">Z</a></nav>'
                '<section id="a"><div id="quiz-A"></div></section><p>$x$ exam-style</p>'
                '<script>const QUIZZES={\n B:{title:"b"}\n};</script></body></html>')
        with tempfile.TemporaryDirectory() as d:
            errors, warns, _ = check_study_page.check(self.write(d, html))
        text = ' '.join(errors)
        self.assertIn('viewport', text)
        self.assertIn('"#zz"', text)
        self.assertIn('quiz-A', text)
        self.assertIn('entry B', text)
        wtext = ' '.join(warns)
        self.assertIn('KaTeX is not loaded', wtext)
        self.assertIn('dark mode', wtext)
        self.assertIn('exam-style', wtext)

    def test_js_string_scanner(self):
        code = "const r=/[\"'<]/g; // it's a comment\nconst s='a $j<i$ b'; const t=`x ${y} $p<q$`;"
        found = [s for _o, s in check_study_page.js_strings(0, code)]
        self.assertIn('a $j<i$ b', found)
        self.assertTrue(any('$p<q$' in s for s in found))
        self.assertFalse(any("it's" in s for s in found))


class PdfTest(unittest.TestCase):
    def test_find_browser_explicit_missing(self):
        self.assertIsNone(html2pdf.find_browser(os.path.join(tempfile.gettempdir(), 'no-such-browser.exe')))

    @unittest.skipUnless(html2pdf.find_browser('auto'), 'no Chromium browser installed')
    def test_print_template(self):
        with tempfile.TemporaryDirectory() as d:
            page = os.path.join(d, 'ad-big-o-study-page.html')
            shutil.copy(TEMPLATE, page)
            ok, _code, err = html2pdf.to_pdf(page, os.path.join(d, 'out.pdf'), html2pdf.find_browser('auto'), 8000)
            self.assertTrue(ok, err)


if __name__ == '__main__':
    unittest.main()
