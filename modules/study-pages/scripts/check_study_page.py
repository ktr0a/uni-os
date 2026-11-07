"""Quality checks for a study page (HTML with KaTeX), before it is shown to the student.

Usage:
    python check_study_page.py <page.html> [<page.html> ...] [--fix] [--strict] [--katex] [--katex-module DIR]

Static checks (always, standard library only):
  ERROR  a literal "<" followed by a letter, "/" or "!" inside maths ($..$, $$..$$, \\(..\\), \\[..\\]), in the page
         text or inside JavaScript strings that the page inserts as HTML. The browser reads it as a tag and the rest
         of the formula disappears. Write \\lt (\\\\lt inside JS strings). --fix rewrites these in place.
  ERROR  no <meta name="viewport"> (the page must work at phone width)
  ERROR  a nav link "#id" without a matching element id
  ERROR  a quiz mount <div id="quiz-X"> without an entry X in QUIZZES, or the other way round
  WARN   maths on the page but KaTeX is not loaded, or the KaTeX URL has no pinned version
  WARN   no dark mode (prefers-color-scheme: dark)
  WARN   localStorage used without a try/catch wrapper (function store)
  WARN   missing uni-os meta tags (course, kind, sources), missing footer with sources, or no build date in it
  WARN   wording the framework avoids ("exam-style", "exam quiz"): the big quiz at the end is the final self-test
Optional render check (--katex): renders every formula with KaTeX under Node.js (throwOnError) and reports the ones
that fail. Needs `node` and the katex package (--katex-module DIR, env KATEX_MODULE, or resolvable by Node). If
either is missing the check is skipped with a note; the template's in-page banner reports render errors too.
Exit code: 1 if there are errors (or warnings with --strict), else 0.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MATH_RE = re.compile(r'\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)|\$([^$\n]{1,400}?)\$', re.S)
BAD_LT = re.compile(r'<(?=[A-Za-z/!])')
AVOID = [r'exam-style', r'exam style', r'exam quiz']


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def split_script(html):
    """Return (text_parts, script_parts) as lists of (offset, content)."""
    texts, scripts = [], []
    pos = 0
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script\s*>', html, re.S | re.I):
        texts.append((pos, html[pos:m.start()]))
        scripts.append((m.start(1), m.group(1)))
        pos = m.end()
    texts.append((pos, html[pos:]))
    return texts, scripts


def strip_comments_and_styles(offset, text):
    """Blank out HTML comments and <style> blocks, keeping offsets."""
    def blank(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    text = re.sub(r'<!--.*?-->', blank, text, flags=re.S)
    text = re.sub(r'<style\b.*?</style\s*>', blank, text, flags=re.S | re.I)
    return offset, text


def js_strings(offset, code):
    """Yield (absolute_offset, raw_content) of JS string literals ('', "", ``), skipping comments.
    Regex literals are detected heuristically (after an operator or bracket)."""
    i, n = 0, len(code)
    prev = ''
    while i < n:
        c = code[i]
        if c == '/' and i + 1 < n and code[i + 1] == '/':
            j = code.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '/' and i + 1 < n and code[i + 1] == '*':
            j = code.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '/' and (prev == '' or prev in '(,=:[!&|?{};+-*%<>~^'):
            j = i + 1
            in_class = False
            while j < n:
                if code[j] == '\\':
                    j += 2
                    continue
                if code[j] == '[':
                    in_class = True
                elif code[j] == ']':
                    in_class = False
                elif code[j] == '/' and not in_class:
                    break
                elif code[j] == '\n':
                    break
                j += 1
            i = j + 1
            prev = '/'
            continue
        if c in '\'"`':
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == '\\':
                    j += 1
                elif code[j] == '\n' and c != '`':
                    break
                j += 1
            yield offset + i + 1, code[i + 1:j]
            i = j + 1
            prev = 'x'
            continue
        if not c.isspace():
            prev = c
        i += 1


def math_spans(offset, text):
    for m in MATH_RE.finditer(text):
        k = next(g for g in range(1, 5) if m.group(g) is not None)
        yield offset + m.start(k), m.group(k)


def find_bad_lt(html):
    """Return a list of (abs_pos, formula, in_js) for '<' + letter inside maths."""
    hits = []
    texts, scripts = split_script(html)
    for off, part in texts:
        off, part = strip_comments_and_styles(off, part)
        for pos, formula in math_spans(off, part):
            for m in BAD_LT.finditer(formula):
                hits.append((pos + m.start(), formula, False))
    for off, code in scripts:
        for soff, s in js_strings(off, code):
            for pos, formula in math_spans(soff, s):
                for m in BAD_LT.finditer(formula):
                    hits.append((pos + m.start(), formula, True))
    return hits


def apply_fix(html, hits):
    out = html
    for pos, _formula, in_js in sorted(hits, key=lambda h: -h[0]):
        repl = '\\\\lt ' if in_js else '\\lt '
        out = out[:pos] + repl + out[pos + 1:]
    return out


def all_formulas(html):
    """Every formula as KaTeX would see it (JS string escapes undone), for the render check."""
    out = []
    texts, scripts = split_script(html)
    for off, part in texts:
        off, part = strip_comments_and_styles(off, part)
        part = re.sub(r'<[^>]+>', lambda m: ' ' * len(m.group(0)), part)
        for pos, f in math_spans(off, part):
            out.append((pos, f.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'), False))
    for off, code in scripts:
        for soff, s in js_strings(off, code):
            if '$' not in s:
                continue
            for pos, f in math_spans(soff, s):
                if '+' in f and ("'" in f or '"' in f):
                    continue  # a formula assembled from pieces at run time: checked in the browser only
                out.append((pos, f.replace('\\\\', '\\'), True))
    return out


def katex_check(html, module_dir):
    node = shutil.which('node')
    if not node:
        return None, 'skipped: node is not installed'
    formulas = [f for _p, f, _js in all_formulas(html)]
    script = r'''
const path=process.argv[2]; let katex;
try{ katex=require(path?require('path').join(path,'katex'):'katex'); }catch(e){ console.log(JSON.stringify({missing:true})); process.exit(0); }
const fs=require('fs'); const fl=JSON.parse(fs.readFileSync(process.argv[3],'utf8')); const bad=[];
fl.forEach((f,i)=>{ try{ katex.renderToString(f,{throwOnError:true,displayMode:false}); }catch(e){ bad.push([i,String(e.message).slice(0,200)]); } });
console.log(JSON.stringify({bad:bad,n:fl.length}));
'''
    with tempfile.TemporaryDirectory() as td:
        js = os.path.join(td, 'katex_check.js')
        data = os.path.join(td, 'formulas.json')
        with open(js, 'w', encoding='utf-8') as fh:
            fh.write(script)
        with open(data, 'w', encoding='utf-8') as fh:
            json.dump(formulas, fh)
        env = dict(os.environ)
        if module_dir:
            env['NODE_PATH'] = module_dir
        r = subprocess.run([node, js, module_dir or '', data], capture_output=True, text=True, env=env, timeout=120)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None, 'skipped: could not run the KaTeX check (' + (r.stderr.strip()[:200] or 'no output') + ')'
    if res.get('missing'):
        return None, 'skipped: the katex package was not found (npm install katex@0.16.9 in a folder outside the vault, then --katex-module <that folder>/node_modules)'
    return [(formulas[i], msg) for i, msg in res['bad']], f"rendered {res['n']} formulas"


def check(path, fix=False, katex=False, katex_module=None):
    with open(path, encoding='utf-8') as fh:
        html = fh.read()
    errors, warns = [], []
    hits = find_bad_lt(html)
    for pos, formula, in_js in hits:
        where = 'JS string' if in_js else 'page text'
        hint = '\\\\lt' if in_js else '\\lt'  # kept out of the f-string: Python 3.11 forbids backslashes there
        errors.append(f'line {line_of(html, pos)}: "<" before a letter inside maths ({where}): '
                      f'${formula.strip()[:70]}$ -> write {hint}')
    if fix and hits:
        html = apply_fix(html, hits)
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(html)
        errors = [e + ' [fixed]' for e in errors]
    if not re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        errors.append('no <meta name="viewport">: the page will not fit a phone screen')
    markup = re.sub(r'<!--.*?-->|<script\b.*?</script\s*>', '', html, flags=re.S | re.I)
    ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', markup))
    nav = re.search(r'<nav\b.*?</nav>', markup, re.S | re.I)
    if nav:
        for target in re.findall(r'href=["\']#([^"\']+)["\']', nav.group(0)):
            if target not in ids:
                errors.append(f'nav link "#{target}" has no element with that id')
    mounts = set(re.findall(r'\bid=["\']quiz-([A-Za-z0-9_]+)["\']', markup))
    qm = re.search(r'const\s+QUIZZES\s*=\s*\{(.*?)\n\};', html, re.S)
    if qm:
        defined = set(re.findall(r'(?m)^\s*([A-Za-z0-9_]+)\s*:\s*\{', qm.group(1)))
        for x in sorted(mounts - defined):
            errors.append(f'quiz mount "quiz-{x}" has no entry {x} in QUIZZES')
        for x in sorted(defined - mounts):
            errors.append(f'QUIZZES entry {x} has no mount <div id="quiz-{x}">')
    has_math = bool(MATH_RE.search(re.sub(r'<script\b.*?</script\s*>|<!--.*?-->', '', html, flags=re.S | re.I)))
    if has_math:
        if 'katex' not in html.lower():
            warns.append('maths on the page but KaTeX is not loaded')
        else:
            for url in re.findall(r'(?:src|href)=["\']([^"\']*katex[^"\']*)["\']', html, re.I):
                if not re.search(r'katex(?:@|/)\d+\.\d+\.\d+', url, re.I):
                    warns.append(f'KaTeX URL without a pinned version: {url}')
    if not re.search(r'prefers-color-scheme\s*:\s*dark', html):
        warns.append('no dark mode (@media (prefers-color-scheme:dark))')
    if 'localStorage' in html and not re.search(r'function\s+store\s*\(', html):
        warns.append('localStorage is used without the try/catch wrapper store()')
    for name in ('course', 'kind', 'sources'):
        if not re.search(r'<meta[^>]+name=["\']uni-os:%s["\']' % name, html, re.I):
            warns.append(f'missing <meta name="uni-os:{name}"> (the Markdown twin takes its properties from it)')
    foot = re.search(r'<footer\b.*?</footer>', html, re.S | re.I)
    if not foot or 'source' not in foot.group(0).lower():
        warns.append('no <footer> naming the sources')
    elif not re.search(r'Built\s+\w', foot.group(0)):
        warns.append('the footer has no "Built <date>" line')
    visible = re.sub(r'<script\b.*?</script\s*>|<!--.*?-->|<style\b.*?</style\s*>', '', html, flags=re.S | re.I)
    js_text = ' '.join(s for _o, code in split_script(html)[1] for _p, s in js_strings(0, code))
    for pat in AVOID:
        if re.search(pat, visible + ' ' + js_text, re.I):
            warns.append(f'wording "{pat}": call the quiz at the end the final self-test')
    notes = []
    if katex:
        bad, note = katex_check(html, katex_module or os.environ.get('KATEX_MODULE'))
        notes.append('KaTeX render check ' + note)
        for f, msg in bad or []:
            errors.append(f'KaTeX cannot render ${f.strip()[:70]}$: {msg}')
    return errors, warns, notes


def utf8_stdio():
    """Print UTF-8 whatever the console or pipe encoding is: a Windows pipe defaults to cp1252,
    and a formula or file name with a symbol like the one for "less or equal" would crash the
    report after the page was already written (or rewritten by --fix)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass  # not a real text stream (tests redirect to StringIO)


def main(argv=None):
    p = argparse.ArgumentParser(description='Check a study page before showing it.')
    p.add_argument('pages', nargs='+')
    p.add_argument('--fix', action='store_true', help='rewrite "<" before a letter in maths as \\lt')
    p.add_argument('--strict', action='store_true', help='warnings count as errors')
    p.add_argument('--katex', action='store_true', help='also render every formula with KaTeX under Node.js')
    p.add_argument('--katex-module', help='folder that contains the katex package (node_modules)')
    utf8_stdio()
    a = p.parse_args(argv)
    failed = False
    for page in a.pages:
        errors, warns, notes = check(page, a.fix, a.katex, a.katex_module)
        print(f'{page}: {len(errors)} error(s), {len(warns)} warning(s)')
        for e in errors:
            print('  ERROR ' + e)
        for w in warns:
            print('  WARN  ' + w)
        for n in notes:
            print('  NOTE  ' + n)
        if errors or (a.strict and warns):
            failed = True
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
