"""Convert the static parts of a KaTeX study page to its Markdown twin (Obsidian or plain Markdown).

Usage:
    python html2md.py <in.html> [<out.md>] [<course>] [<rel_html_name>] [options]

    <out.md>         default: same folder and base name as <in.html>, extension .md
    <course>         course id, slug, short name or folder (e.g. "a&d" -> "ad"); default: the page's
                     <meta name="uni-os:course">, else the file-name prefix before the first "-".
                     If the vault config (_agent/uni-os.json or _agent/uni-os.toml, searched upwards from
                     <in.html>) lists the course, its id is used (the vault-wide `course` property, as on
                     the course card); otherwise the spelling given, lowercased without punctuation.
    <rel_html_name>  link target written into the twin; default: the file name of <in.html>

Options:
    --tag-prefix P   tag prefix for the course tag (default "uni" -> "uni/<course>")
    --audience A     value of the audience property (default "me")
    --date D         conversion date YYYY-MM-DD (default today; for reproducible output)
    --quiet          do not print the body length
    --plain          plain Markdown, for vaults read without Obsidian: cards become blockquotes led by their own
                     bold title or heading, else by a bold label ("**Note.**"), instead of > [!note] callouts, and
                     <details> blocks (self-check answers, hints) stay folded <details><summary>...</summary>
                     blocks instead of > [!info]- callouts; the banner is a plain blockquote
    --obsidian       Obsidian callouts (the original output)
                     Without either flag the mode follows obsidian.enabled in the vault config (searched as for
                     <course>): only an explicit false means plain; no config, or no such key, means Obsidian.

Math written as \\( .. \\) / \\[ .. \\] becomes $..$ / $$..$$; $..$ and $$..$$ pass through unchanged.
Interactive parts built by JavaScript (quizzes, demos, animations) are not converted: each heading section that
had one gets the line "*Interactive part (quiz, demo or animation): only in the [HTML page](...).*".
Port of the original system's _agent/tools/html2md.py (same behaviour), generalised: no hard-coded courses,
metadata from <meta name="uni-os:*"> tags, the canonical study-page frontmatter, a plain-Markdown mode, and a few
documented additions (source chips, aria-hidden and data-md="skip" elements, quiz mounts, code languages).
Python 3 standard library only.
"""
import argparse
import datetime
import json
import os
import re
import sys
from html.parser import HTMLParser

BS = chr(92)
SKIP = {'script', 'style', 'head', 'svg', 'canvas', 'button', 'input', 'select',
        'textarea', 'noscript', 'nav', 'template', 'iframe', 'form', 'label'}
WIDGET_TAGS = ('canvas', 'svg', 'button', 'input', 'select', 'textarea', 'iframe', 'label')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
BLOCK = {'p', 'div', 'section', 'article', 'main', 'header', 'footer', 'aside',
         'figure', 'figcaption', 'dl', 'dt', 'dd', 'body', 'html'}
CALLOUT_CLASSES = [
    (('warn', 'warning', 'danger', 'trap', 'pitfall', 'bad'), 'warning'),
    (('tip', 'hint', 'good', 'ok', 'success'), 'tip'),
    (('def', 'definition', 'thm', 'theorem', 'lemma', 'formula', 'key', 'box', 'card', 'note', 'item', 'info', 'cheat'), 'note'),
    (('example', 'ex', 'worked'), 'example'),
    (('quiz', 'q', 'question'), 'question'),
]
CODE_LANGS = ('java', 'python', 'py', 'javascript', 'js', 'typescript', 'ts', 'c', 'cpp', 'csharp', 'go', 'rust',
              'haskell', 'scala', 'kotlin', 'sql', 'bash', 'sh', 'matlab', 'r', 'julia', 'latex', 'text')
KIND_SUFFIXES = [  # file-name endings -> kind (used when the page has no uni-os:kind meta tag)
    ('-study-page', 'teaching-page'), ('-skim', 'skim'), ('-rundown', 'rundown'),
    ('-recap', 'recap'), ('-summary', 'summary'), ('-cheatsheet', 'cheat-sheet'), ('-cheat-sheet', 'cheat-sheet'),
    ('-walkthrough', 'walkthrough'), ('-guide', 'walkthrough'), ('-hints', 'hint-page'),
    ('-mistake-map', 'mistake-map'), ('-recall-key', 'recall-key'), ('-transcript', 'transcript'),
    ('-mock', 'mock-quiz'), ('-prep', 'quiz-prep'), ('-selfstudy', 'quiz-prep'), ('-checklist', 'quiz-prep'),
    ('-quiz', 'quiz'), ('-deck', 'definitions-deck'), ('-animation', 'teaching-page'),
]
INTERACTIVE_LINE = '*Interactive part (quiz, demo or animation): only in the [HTML page]({rel}).*'
PLAIN_LABELS = {'warning': 'Warning', 'tip': 'Tip', 'note': 'Note', 'example': 'Example', 'question': 'Question'}
# A body that opens a Markdown block of its own: a plain-mode label goes on its own line before it, not in front of it.
BLOCK_START = re.compile(r'^(?:[-*+] |\d+[.)] |```|>|\||<|\$\$|\\\[)')


def callout_type(cls):
    toks = set(cls.lower().replace('-', ' ').replace('_', ' ').split())
    for keys, kind in CALLOUT_CLASSES:
        if toks & set(keys):
            return kind
    return None


def code_lang(cls):
    for tok in cls.lower().split():
        for pre in ('language-', 'lang-'):
            if tok.startswith(pre):
                return tok[len(pre):]
        if tok in CODE_LANGS:
            return tok
    return ''


class Frame:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.buf = []
        self.__dict__.update(kw)


class Conv(HTMLParser):
    def __init__(self, plain=False):
        super().__init__(convert_charrefs=True)
        self.plain = plain  # True: plain Markdown, no Obsidian callouts
        self.stack = [Frame('root')]
        self.skip = 0
        self.silent = []  # tags of elements skipped without a widget mark (aria-hidden, data-md="skip")
        self.pre = 0
        self.lists = []
        self.title = ''
        self.in_title = False
        self.meta = {}

    # ---- helpers
    def out(self, s):
        self.stack[-1].buf.append(s)

    def push(self, kind, **kw):
        self.stack.append(Frame(kind, **kw))

    def pop(self, kind):
        # pop until a frame of this kind is found
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].kind == kind:
                frames = self.stack[i:]
                self.stack = self.stack[:i]
                # flatten inner frames that were never closed into their parent text
                text = ''
                for fr in reversed(frames[1:]):
                    text = ''.join(fr.buf) + text
                frames[0].buf.append(text)
                return frames[0]
        return None

    def in_table(self):
        return any(f.kind in ('table', 'cell') for f in self.stack)

    # ---- parser callbacks
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            name = (a.get('name') or '').lower()
            if name.startswith('uni-os:'):
                self.meta[name[7:]] = a.get('content') or ''
            return
        if tag == 'title':
            self.in_title = True
            return
        if self.silent:
            if tag == self.silent[-1][0] and tag not in VOID:
                self.silent[-1][1] += 1
            return
        if not self.skip and (a.get('aria-hidden') == 'true' or a.get('data-md') == 'skip'):
            if tag not in VOID:
                self.silent.append([tag, 1])
            return
        if not self.skip and tag in WIDGET_TAGS:
            self.out('\n\nWIDGETMARK\n\n')
        if self.skip or tag in SKIP:
            if tag in SKIP and tag not in ('input', 'br'):
                self.skip += 1
            return
        cls = a.get('class', '') or ''
        if tag in ('div', 'section') and ((a.get('id') or '').startswith('quiz-') or 'data-widget' in a):
            self.out('\n\nWIDGETMARK\n\n')  # quiz mounts are empty until JavaScript fills them
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.push('h', level=int(tag[1]))
        elif tag == 'span' and 'src' in cls.split():
            self.push('src')
        elif tag == 'br':
            self.out('  \n' if not self.in_table() else '<br>')
        elif tag == 'hr':
            self.out('\n\n---\n\n')
        elif tag in ('strong', 'b'):
            self.out('**')
        elif tag in ('em', 'i'):
            self.out('*')
        elif tag == 'code' and not self.pre:
            self.push('code')
        elif tag == 'code' and self.pre:
            lang = code_lang(cls)
            for fr in reversed(self.stack):
                if fr.kind == 'pre':
                    if lang and not fr.lang:
                        fr.lang = lang
                    break
        elif tag == 'pre':
            self.pre += 1
            self.push('pre', lang=code_lang(cls))
        elif tag == 'a':
            self.push('a', href=a.get('href', ''))
        elif tag in ('ul', 'ol'):
            self.lists.append([tag, 0, (a.get('type') or '1')])
            self.out('\n')
        elif tag == 'li':
            self.push('li')
        elif tag == 'table':
            self.push('table', rows=[])
        elif tag == 'tr':
            self.push('tr', cells=[], header=False)
        elif tag in ('td', 'th'):
            self.push('cell', th=(tag == 'th'))
        elif tag == 'details':
            self.push('details', summary='', open_='open' in a, hint=('hint' in cls.split()))
        elif tag == 'summary':
            self.push('summary')
        elif tag == 'blockquote':
            self.push('callout', ctype='quote')
        elif tag == 'img':
            alt = a.get('alt', '')
            if alt:
                self.out(f'*[image: {alt}]*')
        elif tag in BLOCK:
            kind = callout_type(cls) if tag in ('div', 'section', 'aside') else None
            if kind and not self.in_table():
                self.push('callout', ctype=kind)
            else:
                self.push('block')

    def handle_startendtag(self, tag, attrs):
        # <br/>, <img/>, <input/>: void elements get no end tag (the original also sent one, which could end a
        # skipped region early, e.g. <input/> inside a <label>); <svg/>, <div/>: start plus end, as before.
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
            return
        if self.silent:
            if tag == self.silent[-1][0]:
                self.silent[-1][1] -= 1
                if self.silent[-1][1] == 0:
                    self.silent.pop()
            return
        if self.skip:
            if tag in SKIP:
                self.skip -= 1
            return
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            fr = self.pop('h')
            if fr:
                txt = clean_inline(''.join(fr.buf))
                if txt:
                    self.out('\n\n' + '#' * fr.level + ' ' + txt + '\n\n')
        elif tag == 'span':
            if self.stack[-1].kind == 'src':
                fr = self.pop('src')
                txt = clean_inline(''.join(fr.buf))
                if txt:
                    self.out(f' *({txt})*')
        elif tag in ('strong', 'b'):
            self.out('**')
        elif tag in ('em', 'i'):
            self.out('*')
        elif tag == 'code' and not self.pre:
            fr = self.pop('code')
            if fr:
                txt = ''.join(fr.buf)
                if txt.strip():
                    self.out('`' + txt.replace('`', "'") + '`')
        elif tag == 'pre':
            fr = self.pop('pre')
            self.pre = max(0, self.pre - 1)
            if fr:
                body = ''.join(fr.buf).strip('\n')
                if body.strip():  # an empty <pre> is filled by JavaScript at run time: leave it out
                    self.out(f'\n\n```{fr.lang}\n{body}\n```\n\n')
        elif tag == 'a':
            fr = self.pop('a')
            if fr:
                txt = clean_inline(''.join(fr.buf))
                href = fr.href or ''
                if not txt:
                    return
                if href.startswith('#') or href.startswith('javascript') or not href:
                    self.out(txt)
                else:
                    self.out(f'[{txt}]({href})')
        elif tag in ('ul', 'ol'):
            if self.lists:
                self.lists.pop()
            self.out('\n')
        elif tag == 'li':
            fr = self.pop('li')
            if fr:
                depth = max(0, len(self.lists) - 1)
                lst = self.lists[-1] if self.lists else ['ul', 0, '1']
                lst[1] += 1
                if lst[0] == 'ol' and lst[2] in ('i', 'I'):
                    marker = '- (' + roman(lst[1], lst[2] == 'I') + ')'
                elif lst[0] == 'ol' and lst[2] in ('a', 'A'):
                    marker = '- (' + chr((65 if lst[2] == 'A' else 97) + lst[1] - 1) + ')'
                elif lst[0] == 'ol':
                    marker = f'{lst[1]}.'
                else:
                    marker = '-'
                body = ''.join(fr.buf).strip()
                body = re.sub(r'\n{2,}', '\n', body)
                lines = body.split('\n')
                ind = '  ' * depth
                txt = ind + marker + ' ' + lines[0].strip()
                for ln in lines[1:]:
                    if ln.strip():
                        txt += '\n' + ind + '  ' + ln.strip() if not ln.lstrip().startswith(('-', '1', '2', '3', '4', '5', '6', '7', '8', '9')) else '\n' + ln
                self.out('\n' + txt)
        elif tag in ('td', 'th'):
            fr = self.pop('cell')
            if fr and self.stack[-1].kind == 'tr':
                txt = clean_inline(''.join(fr.buf).replace('\n', ' '))
                txt = txt.replace(BS + '|', BS + 'Vert ').replace('|', BS + '|')
                self.stack[-1].cells.append(txt)
                if fr.th:
                    self.stack[-1].header = True
        elif tag == 'tr':
            fr = self.pop('tr')
            if fr and self.stack[-1].kind == 'table':
                self.stack[-1].rows.append((fr.cells, fr.header))
        elif tag == 'table':
            fr = self.pop('table')
            if fr and fr.rows:
                ncol = max(len(r[0]) for r in fr.rows) or 1
                rows = [r[0] + [''] * (ncol - len(r[0])) for r in fr.rows]
                head = rows[0]
                lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * ncol]
                for r in rows[1:]:
                    lines.append('| ' + ' | '.join(r) + ' |')
                self.out('\n\n' + '\n'.join(lines) + '\n\n')
        elif tag == 'summary':
            fr = self.pop('summary')
            if fr and self.stack[-1].kind == 'details':
                self.stack[-1].summary = clean_inline(''.join(fr.buf))
        elif tag == 'details':
            fr = self.pop('details')
            if fr:
                body = tidy(''.join(fr.buf))
                title = fr.summary or 'Details'
                if self.plain:
                    self.out('\n\n' + details_block(title, body) + '\n\n')
                else:
                    kind = 'tip' if fr.hint else 'info'
                    self.out('\n\n' + quote_block(f'[!{kind}]- {title}\n' + body) + '\n\n')
        elif tag == 'blockquote':
            fr = self.pop('callout')
            if fr:
                self.out('\n\n' + quote_block(tidy(''.join(fr.buf))) + '\n\n')
        elif tag in BLOCK:
            top = self.stack[-1]
            if top.kind == 'callout' and tag in ('div', 'section', 'aside'):
                fr = self.pop('callout')
                body = tidy(''.join(fr.buf))
                if body:
                    lines = body.split('\n')
                    first = lines[0]
                    m = re.match(r'^\*\*(.+?)\*\*[:.]?\s*(.*)$', first)
                    titled = bool(m and len(m.group(1)) < 80)
                    if self.plain:
                        # A blockquote: the card's own bold title stays where it is, else a bold label leads.
                        text = body if titled else plain_label(PLAIN_LABELS.get(fr.ctype, 'Note'), body)
                    elif titled:
                        rest = '\n'.join(([m.group(2)] if m.group(2) else []) + lines[1:])
                        text = f'[!{fr.ctype}] {m.group(1)}\n' + rest
                    else:
                        text = f'[!{fr.ctype}]\n' + body
                    self.out('\n\n' + quote_block(text) + '\n\n')
            elif top.kind == 'block':
                fr = self.pop('block')
                body = ''.join(fr.buf)
                self.out('\n\n' + body + '\n\n')

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        if self.skip or self.silent:
            return
        if self.pre:
            self.out(data)
        else:
            self.out(re.sub(r'\s+', ' ', data))

    def result(self):
        while len(self.stack) > 1:
            fr = self.stack.pop()
            self.stack[-1].buf.append(''.join(fr.buf))
        return tidy(''.join(self.stack[0].buf))


def quote_block(s):
    return '\n'.join('> ' + ln if ln.strip() else '>' for ln in s.strip('\n').split('\n'))


def details_block(title, body):
    """Plain mode: a folded <details> block. The blank lines inside let Markdown and maths render in it;
    VS Code, GitHub and most viewers keep it folded until it is opened."""
    summary = title.replace('&', '&amp;').replace('<', '&lt;')
    inner = f'\n\n{body}\n\n' if body else '\n\n'
    return f'<details>\n<summary>{summary}</summary>{inner}</details>'


def plain_label(label, body):
    """Plain mode: '**Note.** text' for a card without a bold title of its own. A card that opens with a heading
    keeps it as its title (no label); the label gets its own line (then a blank line) when the body opens with a
    list, code fence, quote, table, HTML or display maths."""
    if re.match(r'#{1,6} ', body):
        return body
    if BLOCK_START.match(body):
        return f'**{label}.**\n\n' + body
    return f'**{label}.** ' + body


def clean_inline(s):
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('** **', ' ').replace('****', '')
    return s


def tidy(s):
    lines = [ln.rstrip() for ln in s.split('\n')]
    out = []
    fence = False  # inside a ``` code block indentation is content (the original stripped 2-space indents there)
    for ln in lines:
        if ln.lstrip().startswith('```'):
            fence = not fence
        elif not fence and ln.startswith(' ') and not re.match(r'^\s*(-|\d+\.)\s', ln) and not ln.startswith('    '):
            ln = ln.lstrip()
        out.append(ln)
    s = '\n'.join(out)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def fix_math(s):
    # display math first, then inline
    s = re.sub(re.escape(BS + '[') + r'(.+?)' + re.escape(BS + ']'), lambda m: '\n$$' + m.group(1).strip() + '$$\n', s, flags=re.S)
    s = re.sub(re.escape(BS + '(') + r'(.+?)' + re.escape(BS + ')'), lambda m: '$' + m.group(1).strip() + '$', s, flags=re.S)
    return s


def roman(n, upper=False):
    vals = [(10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]
    out = ''
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out.upper() if upper else out


TAGS = ('a|abbr|article|aside|b|blockquote|body|br|button|canvas|caption|circle|cite|code|col|colgroup|dd|defs|'
        'details|div|dl|dt|ellipse|em|figcaption|figure|footer|form|g|h1|h2|h3|h4|h5|h6|head|header|hr|html|i|'
        'iframe|img|input|kbd|label|li|line|link|main|mark|marker|meta|nav|noscript|ol|option|output|p|path|'
        'polygon|polyline|pre|q|rect|s|samp|script|section|select|small|span|strong|style|sub|summary|sup|svg|'
        'table|tbody|td|template|text|textarea|tfoot|th|thead|time|title|tr|tspan|u|ul|var|wbr')
STRAY_LT = re.compile(r'<(?!/?(?:' + TAGS + r')\b|!)', re.I)


def escape_stray_lt(html):
    # A "<" that does not start a real tag (e.g. "1<x" inside maths) would swallow the rest of the line.
    return STRAY_LT.sub('&lt;', html)


def fill_empty_headings(md, relname):
    lines = md.split('\n')
    out = []
    seen = False
    for ln in lines:
        if re.match(r'^#{1,6} ', ln):
            seen = False
        if ln.strip() == 'WIDGETMARK' or ln.strip() == '> WIDGETMARK':
            if not seen:
                prefix = '> ' if ln.startswith('>') else ''
                out.append(prefix + INTERACTIVE_LINE.format(rel=relname))
                seen = True
            continue
        out.append(ln.replace('WIDGETMARK', ''))
    md = '\n'.join(out)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md


# ---- course resolution and config -------------------------------------------------------------

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())


def find_config(start):
    """Search upwards from a file for the vault config; return the parsed dict or None."""
    d = os.path.dirname(os.path.abspath(start))
    while True:
        for name in ('uni-os.json', 'uni-os.toml'):
            p = os.path.join(d, '_agent', name)
            if os.path.isfile(p):
                try:
                    if name.endswith('.json'):
                        with open(p, encoding='utf-8') as fh:
                            return json.load(fh)
                    import tomllib  # Python 3.11+
                    with open(p, 'rb') as fh:
                        return tomllib.load(fh)
                except Exception:
                    return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def resolve_course(arg, cfg):
    """Map any course spelling (id, slug, short, folder, name) to the course id."""
    if not arg:
        return ''
    key = norm(arg)
    for c in (cfg or {}).get('courses', []) or []:
        names = [c.get('id'), c.get('slug'), c.get('short'), c.get('folder'), c.get('name')]
        if any(norm(n) == key for n in names if n):
            return str(c.get('id') or c.get('slug') or key)
    return key


def kind_from_name(base):
    stem = re.sub(r'\.html?$', '', base.lower())
    for suffix, kind in KIND_SUFFIXES:
        if stem.endswith(suffix) or (suffix + '-') in stem:
            return kind
    return 'other'


def yaml_str(s):
    return '"' + str(s).replace('\\', '/').replace('"', "'") + '"'


def build_frontmatter(title, kind, course, sources, created, relname, converted, audience, tag_prefix):
    tag = f'{tag_prefix}/{course}' if tag_prefix else course
    src_list = '[' + ', '.join(yaml_str(s) for s in sources) + ']'
    return ['---', f'title: {yaml_str(title)}', 'type: study-page', f'kind: {kind}', f'course: {course}',
            f'sources: {src_list}', f'created: {created}', f'source_html: {yaml_str(relname)}',
            f'converted: {converted}', f'audience: {audience}', f'tags: [{tag}, study-page]', '---', '']


def obsidian_enabled(cfg):
    """The vault's obsidian.enabled: only an explicit false means "read without Obsidian"."""
    obs = (cfg or {}).get('obsidian')
    return not (isinstance(obs, dict) and obs.get('enabled') is False)


def convert(html_text, relname, course_arg=None, cfg=None, tag_prefix='uni', audience='me', today=None, plain=False):
    """Return the Markdown twin as a string, plus the body length. plain=True: plain Markdown, no Obsidian callouts."""
    today = today or datetime.date.today()
    day_text = f'{today:%a} {today.day} {today:%b %Y}'  # e.g. Wed 28 Oct 2026
    c = Conv(plain=plain)
    c.feed(escape_stray_lt(html_text))
    body = fix_math(c.result())
    body = re.sub(r'\*\*\s*\*\*', '', body)
    body = re.sub(r'(?m)^(#{1,6} \d+(?:\.\d+)*)([A-Za-z])', r'\1 \2', body)
    body = fill_empty_headings(body, relname)
    meta = c.meta
    course = resolve_course(course_arg or meta.get('course') or relname.split('-')[0], cfg)
    title = re.sub(r'\s+', ' ', c.title).strip() or relname
    kind = meta.get('kind') or kind_from_name(relname)
    sources = [s.strip() for s in (meta.get('sources') or '').split(';') if s.strip()]
    created = meta.get('created') or today.isoformat()
    fm = build_frontmatter(title, kind, course, sources, created, relname, today.isoformat(), audience, tag_prefix)
    if plain:
        head = (f'> **Markdown copy of [{relname}]({relname}).** '
                f'Auto-converted on {day_text} so the content and maths read in a Markdown viewer. '
                f'Interactive parts (quizzes with answer checking, animations, demos) only work in the HTML page: open it in the browser.\n')
    else:
        head = (f'> [!abstract] Markdown copy of [{relname}]({relname})\n'
                f'> Auto-converted on {day_text} so the content and maths read inside Obsidian. '
                f'Interactive parts (quizzes with answer checking, animations, demos) only work in the HTML page: open it in the browser.\n')
    return '\n'.join(fm) + '\n' + head + '\n' + body + '\n', len(body)


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
    p = argparse.ArgumentParser(description='Convert a study page (HTML with KaTeX) to its Markdown twin '
                                            '(Obsidian callouts, or plain Markdown with --plain).')
    p.add_argument('src')
    p.add_argument('dst', nargs='?')
    p.add_argument('course', nargs='?')
    p.add_argument('relname', nargs='?')
    p.add_argument('--tag-prefix', default='uni')
    p.add_argument('--audience', default='me')
    p.add_argument('--date')
    p.add_argument('--quiet', action='store_true')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--plain', dest='plain', action='store_const', const=True,
                      help='plain Markdown: bold-labelled quotes and <details> blocks instead of Obsidian callouts')
    mode.add_argument('--obsidian', dest='plain', action='store_const', const=False,
                      help='Obsidian callouts (the default unless the vault config sets obsidian.enabled = false)')
    p.set_defaults(plain=None)
    utf8_stdio()
    a = p.parse_args(argv)
    dst = a.dst or re.sub(r'\.html?$', '', a.src, flags=re.I) + '.md'
    relname = a.relname or os.path.basename(a.src)
    today = datetime.date.fromisoformat(a.date) if a.date else None
    with open(a.src, encoding='utf-8') as fh:
        html_text = fh.read()
    cfg = find_config(a.src)
    plain = a.plain if a.plain is not None else not obsidian_enabled(cfg)
    md, n = convert(html_text, relname, a.course, cfg, a.tag_prefix, a.audience, today, plain=plain)
    with open(dst, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(md)
    if not a.quiet:
        print(n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
