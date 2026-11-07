"""Tests for modules/error-logs/scripts/error_log.py (standard library only).

Run from the repository root:
    python -m unittest discover -s modules/error-logs/tests
"""
import contextlib
import datetime
import filecmp
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(MODULE))
sys.path.insert(0, os.path.join(MODULE, 'scripts'))
import error_log  # noqa: E402

try:  # the framework's template engine (tools/uni_os/template.py), if present
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    from uni_os import template as fw_template  # noqa: E402
except Exception:  # pragma: no cover - the module tests also run without the framework
    fw_template = None

VAULT_TEMPLATE = os.path.join(MODULE, 'vault', '{{course.folder}}', '{{error_log.file}}')
CFG = {
    'term': {'label': 'Autumn 2026', 'week0_monday': '2026-09-14'},
    'study': {'error_logs': {'retests': False, 'retest_items': 2, 'retest_minutes': 20}},
    'courses': [
        {'id': 'algo', 'name': 'Algorithms and Data Structures', 'short': 'AD', 'folder': 'A&D', 'slug': 'ad',
         'error_log_streams': ['theory', 'programming']},
        {'id': 'dm', 'name': 'Discrete Mathematics', 'short': 'DM', 'folder': 'DM', 'slug': 'dm'},
    ],
}


class ErrorLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = self.tmp.name
        os.makedirs(os.path.join(self.vault, '_agent'))
        self.write_cfg(CFG)

    def tearDown(self):
        self.tmp.cleanup()

    def write_cfg(self, cfg):
        with open(os.path.join(self.vault, '_agent', 'uni-os.json'), 'w', encoding='utf-8') as fh:
            json.dump(cfg, fh)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = error_log.main(['--vault', self.vault] + list(args))
        return code, out.getvalue()

    def read(self, *parts):
        with open(os.path.join(self.vault, *parts), encoding='utf-8') as fh:
            return fh.read()

    def test_vault_copy_identical(self):
        self.assertTrue(filecmp.cmp(os.path.join(MODULE, 'scripts', 'error_log.py'),
                                    os.path.join(MODULE, 'vault', '_agent', 'tools', 'error_log.py'), shallow=False))

    def test_naming_rule_matches_spec(self):
        courses = {c['slug']: c for c in error_log.course_list(CFG)}
        self.assertEqual(error_log.log_entries(courses['dm']), [('main', 'dm-error-log.md')])
        self.assertEqual(error_log.log_entries(courses['ad']),
                         [('theory', 'ad-error-log-theory.md'), ('programming', 'ad-error-log-programming.md')])

    @unittest.skipIf(fw_template is None, 'framework template engine not available')
    def test_vault_template_matches_builtin(self):
        # What `uni-os init` installs and what `sync` writes must be the same text (no drift between the two).
        with open(VAULT_TEMPLATE, encoding='utf-8') as fh:
            tpl = fh.read()
        for cc in error_log.course_list(CFG):
            files = [f for _s, f in error_log.log_entries(cc)]
            course = {'id': cc['id'], 'name': cc['name'], 'short': cc['short'], 'slug': cc['slug'], 'folder': cc['folder'],
                      'error_log_streams': cc['streams'], 'error_log_files': files}
            ctx = {'course': course, 'term': CFG['term'], 'generated': {'date': '2026-09-14', 'version': '0.1.0'},
                   'modules': {'enabled': []}}
            for stream, file in error_log.log_entries(cc):
                title = 'Error log' if len(files) == 1 else f'Error log ({stream})'
                log = {'stream': stream, 'file': file, 'path': f"{cc['folder']}/{file}", 'title': title}
                rendered = fw_template.render(tpl, ctx, bindings={'course': course, 'error_log': log},
                                              filename='error-log template')
                builtin = error_log.render_log(cc, stream, '2026-09-14', 'Autumn 2026')
                self.assertEqual(rendered, builtin, f'{file} differs')

    def test_sync_add_check(self):
        code, out = self.run_cli('sync')
        self.assertEqual(code, 0)
        for name in ('A&D/ad-error-log-theory.md', 'A&D/ad-error-log-programming.md', 'DM/dm-error-log.md'):
            self.assertIn('created ' + name.replace('/', os.sep), out)
        self.assertFalse(os.path.exists(os.path.join(self.vault, 'A&D', 'ad-error-log.md')))
        prog = self.read('A&D', 'ad-error-log-programming.md')
        self.assertIn('stream: programming', prog)
        # properties carry the course id (the vault-wide `course` convention), file names the slug
        self.assertIn('course: algo\n', prog)
        self.assertIn('tags: [uni/algo, error-log]', prog)
        self.assertIn('# AD error and misconception log · programming (Autumn 2026)', prog)
        self.assertIn('ad-error-log-theory.md, ad-error-log-programming.md', prog)
        self.assertNotIn('one log per stream', self.read('DM', 'dm-error-log.md'))
        code, out = self.run_cli('sync')
        self.assertIn('nothing to do', out)
        with self.assertRaises(SystemExit):  # several streams: never guess which log
            self.run_cli('add', '--course', 'A&D', '--where', 'x', '--what', 'y', '--idea', 'z', '--source', 'w')
        code, out = self.run_cli('add', '--course', 'A&D', '--stream', 'theory', '--where', 'Sheet 3, 3.2 b) sums',
                                 '--what', 'wrote a|b as one term', '--idea', 'test n = 1, 2, 3\nthen simplify',
                                 '--source', '[script] p. 12', '--date', '2026-10-26')
        self.assertEqual(code, 0)
        self.assertIn('| Mon 26 Oct | Sheet 3, 3.2 b) sums | wrote a\\|b as one term | test n = 1, 2, 3<br>then simplify | [script] p. 12 |', out)
        self.run_cli('add', '--course', 'algo', '--stream', 'programming', '--where', 'Sheet 2, task 1',
                     '--what', 'off by one', '--idea', 'inclusive vs exclusive bound', '--source', '[task]')
        theory = self.read('A&D', 'ad-error-log-theory.md')
        self.assertEqual(len([ln for ln in theory.split('\n') if ln.startswith('| Mon 26 Oct')]), 1)
        self.assertLess(theory.index('| Mon 26 Oct'), theory.index('## Patterns to watch'))
        self.assertIn('off by one', self.read('A&D', 'ad-error-log-programming.md'))
        self.run_cli('add', '--course', 'dm', '--where', 'Quiz W5 Q3', '--what', 'chose b', '--idea', 'read the qualifier',
                     '--source', '[quiz review]')
        code, out = self.run_cli('check')
        self.assertEqual(code, 0, out)
        path = os.path.join(self.vault, 'DM', 'dm-error-log.md')
        txt = self.read('DM', 'dm-error-log.md').replace('|---|---|---|---|---|\n', '|---|---|---|---|---|\n| a | b | c |\n')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(txt)
        code, out = self.run_cli('check', '--course', 'dm')
        self.assertEqual(code, 1)
        self.assertIn('3 cells instead of 5', out)

    def test_unknown_course_and_stream(self):
        self.run_cli('sync')
        with self.assertRaises(SystemExit):
            self.run_cli('add', '--course', 'xyz', '--where', 'a', '--what', 'b', '--idea', 'c', '--source', 'd')
        with self.assertRaises(SystemExit):
            self.run_cli('add', '--course', 'dm', '--stream', 'oral', '--where', 'a', '--what', 'b', '--idea', 'c',
                         '--source', 'd')

    def test_retest_bank_and_pick(self):
        self.run_cli('sync')
        code, out = self.run_cli('retest-bank', '--course', 'dm')
        self.assertEqual(code, 1)
        self.assertIn('retests are off', out)
        cfg = json.loads(json.dumps(CFG))
        cfg['study']['error_logs']['retests'] = True
        self.write_cfg(cfg)
        code, out = self.run_cli('retest-bank', '--course', 'dm')
        self.assertEqual(code, 0)
        bank = os.path.join(self.vault, 'DM', 'dm-retest-bank.md')
        with open(bank, encoding='utf-8') as fh:
            self.assertIn('[the error log](dm-error-log.md)', fh.read())
        with open(bank, 'a', encoding='utf-8') as fh:
            fh.write('| R1 | 1 Oct, quantifiers | new task 1 | look 1 |\n| R2 | 2 Oct | new task 2 | look 2 |\n'
                     '| R3 | 3 Oct | new task 3 | look 3 |\n')
        for d, item, res in (('2026-10-10', 'R1', 'ok'), ('2026-10-17', 'R1', 'ok'), ('2026-10-12', 'R2', 'again')):
            self.run_cli('add', '--course', 'dm', '--where', f'retest of 1 Oct row ({item})', '--what',
                         f'{res}, fine', '--idea', 'x', '--source', '[retest]', '--date', d)
        code, out = self.run_cli('retest-pick', '--course', 'dm')
        self.assertEqual(code, 0)
        ids = re.findall(r'^(R\d+) ', out, re.M)
        self.assertEqual(ids, ['R3', 'R2'])  # R1 retired (ok twice); never-tried R3 before R2
        self.assertIn('tried 1x, last Mon 12 Oct', out)

    def test_add_into_mixed_line_endings(self):
        # CRLF from one tool, LF rows appended by another: the new row still lands inside the table.
        self.run_cli('sync')
        path = os.path.join(self.vault, 'DM', 'dm-error-log.md')
        with open(path, encoding='utf-8', newline='') as fh:
            text = fh.read()
        text = text.replace('\n', '\r\n').replace(
            '|---|---|---|---|---|\r\n', '|---|---|---|---|---|\n| Tue 3 Nov | Sheet 6, 6.1 | a | b | [task] |\n'
                                         '| Tue 3 Nov | Sheet 6, 6.2 | c | d | [task] |\r\n')
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
        code, _ = self.run_cli('add', '--course', 'dm', '--where', 'Sheet 6, 6.3', '--what', 'e', '--idea', 'f',
                               '--source', '[task]', '--date', '2026-11-04')
        self.assertEqual(code, 0)
        with open(path, encoding='utf-8', newline='') as fh:
            after = fh.read()
        lines = after.splitlines()
        i = lines.index('| Wed 4 Nov | Sheet 6, 6.3 | e | f | [task] |')
        self.assertEqual(lines[i - 1], '| Tue 3 Nov | Sheet 6, 6.2 | c | d | [task] |')
        self.assertEqual(lines[i + 1], '')  # the blank line before "## Patterns to watch" is kept
        self.assertIsNone(re.search(r'(?<!\r)\n', after))  # written back with one ending: no bare LF left
        self.assertTrue(after.endswith('\r\n'))  # the majority ending (CRLF) and the trailing newline are kept
        code, out = self.run_cli('check', '--course', 'dm')
        self.assertEqual(code, 0, out)

    def test_add_prints_utf8_through_a_cp1252_pipe(self):
        # A Windows pipe defaults to cp1252: the print after the write must not crash (an agent would retry
        # and duplicate the row in an append-only log).
        import subprocess
        self.run_cli('sync')
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        r = subprocess.run([sys.executable, os.path.join(MODULE, 'scripts', 'error_log.py'), '--vault', self.vault,
                            'add', '--course', 'dm', '--where', 'Sheet 3, 3.2', '--what', 'wrote a ≤ b for the strict case',
                            '--idea', 'λ-eigenvalue check: Ax = λx', '--source', '[task]'],
                           capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8', 'replace'))
        self.assertIn('wrote a ≤ b', r.stdout.decode('utf-8'))
        self.assertEqual(self.read('DM', 'dm-error-log.md').count('strict case'), 1)

    def test_parse_day(self):
        ref = datetime.date(2026, 9, 14)
        self.assertEqual(error_log.parse_day('Mon 26 Oct', ref), datetime.date(2026, 10, 26))
        self.assertEqual(error_log.parse_day('12 Jan', ref), datetime.date(2027, 1, 12))
        self.assertEqual(error_log.parse_day('2026-11-02', ref), datetime.date(2026, 11, 2))
        self.assertIsNone(error_log.parse_day('soon', ref))


if __name__ == '__main__':
    unittest.main()
