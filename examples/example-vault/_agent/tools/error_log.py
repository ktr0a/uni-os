"""Error-log helper for a Uni OS vault: create stream logs, append rows, check the format, run the retest bank.

Usage (from anywhere; the vault is found from --vault, $UNI_OS_VAULT, the current folder or this file's location):
    python error_log.py [--vault DIR] list
    python error_log.py [--vault DIR] sync
    python error_log.py [--vault DIR] add --course C [--stream S] --where W --what X --idea Y --source Z [--date D]
    python error_log.py [--vault DIR] check [--course C]
    python error_log.py [--vault DIR] retest-bank --course C [--force]
    python error_log.py [--vault DIR] retest-pick --course C [--n N]

list         every course's log files and their row counts
sync         create missing logs. A course with one stream (courses[].error_log_streams, default ["main"]) has
             <folder>/<slug>-error-log.md; a course with several has <folder>/<slug>-error-log-<stream>.md for
             each (the same rule as `uni-os init`, docs/file-formats.md "Error-log row"). Never overwrites; prints what it created.
add          append one row at the bottom of the "Errors and misconceptions" table (re-reads the file right before
             writing, escapes "|", bumps `updated`). C is the course id (the slug, short name or folder also work).
             --date accepts YYYY-MM-DD; default is today written as "Ddd D Mon" (e.g. "Mon 26 Oct").
check        format check: properties, the three sections, a five-column table, five cells in every row.
retest-bank  create <folder>/<slug>-retest-bank.md (only when study.error_logs.retests is true, or with --force).
retest-pick  print the next N items of the course's retest bank (default study.error_logs.retest_items):
             never-tried items first, then the items tried longest ago; items that were "ok" twice are retired.
             Results are read from the error-log rows whose "Where" says "retest of ... (R<n>)".
Python 3.11+ standard library only. Exit code 1 on errors.
"""
import argparse
import datetime
import json
import os
import re
import sys

COLUMNS = ['Date', 'Where', 'What went wrong', 'Correct idea', 'Source']
LEGACY_WHERE = ('where', 'sheet / task', 'sheet and task', 'sheet/task')
SECTIONS = {
    'errors': (r'errors and misconceptions',),
    'patterns': (r'patterns to watch', r'recurring patterns'),
    'open': (r'open points', r'open items'),
}

HEADER_TEXT = """Owner: the exercise-help role for {name} (session "{short} · Exercise help{session_suffix}"). One row per error or point of confusion, newest at the bottom of the table. Append only: never edit or delete an old row; fix a wrong row with a new row "Correction to the row of <date>: ...".
{stream_line}Columns: date | where | what went wrong | the correct idea | source.
- **Where**: sheet and task (`Sheet 3, 3.2 b) <short task name>`), quiz question (`Quiz W5 Q3`), lecture or study-page item (`Lecture Mon 26 Oct, clicker 2`, `Study page <name>, quiz B Q4`), TA correction (`Sheet 4 corrections p. 2`), retest (`retest of <date> row (R3)`).
- **What went wrong**: concretely what was written or chosen, with the TA's words in quotes if there are any. Add the student's state if they mention it (tired, rushed, frustrated): errors made under fatigue weigh differently.
- **Correct idea**: the general rule or idea, a check on a small case, and the habit that prevents it. Never the full solution of a current graded task.
- **Session note**: context that changes how a batch of rows should be weighed (a very tired evening, frustration, a session that went off track) goes into a dated section `## Session note (<Ddd D Mon>)` right below the table, not into the rows.
Source tags: [script] = the course script (file and page offset: see the course card, section "Real sources"; cite printed pages), [slides] = lecture slides, [handout] = official handout or plan, [task] = the task statement, [lecture] = said in the lecture, [TA correction] = annotated graded hand-in, [quiz review] = the quiz's official feedback, [derived] = from the definitions or an own check, no page, [user note] = the student's own note, [other AI] = reconstructed from a chat with another AI tool, [retest] = a cold redo (only if retests are on).
Work under the `solo` assistance level is never discussed, logged or linked here (see the assistance policy in `_agent/uni-os.toml`)."""

LOG_TEMPLATE = """---
type: error-log
course: {cid}
stream: {stream}
audience: both
updated: {today}
tags: [uni/{cid}, error-log]
---
# {short} error and misconception log{stream_title} ({term})

{header}

## Errors and misconceptions

| Date | Where | What went wrong | Correct idea | Source |
|---|---|---|---|---|

## Patterns to watch

Update as the log grows. Format: `1. **<pattern name>** (<dates and where>): <what goes wrong>. Fix: <habit, technique or page>.` Mirror every pattern as one line in [weak spots](../me/weak-spots.md) under this course; a pattern that shows up in two courses also goes under "Across courses" there.

(none yet)

## Open points

Sticking points to take to the exercise class or office hours, and questions without an answer yet. Strike a point (`~~...~~`) when it is settled and say where.

(none yet)
"""

BANK_TEMPLATE = """---
type: reference
kind: retest-bank
course: {cid}
audience: both
updated: {today}
tags: [uni/{cid}, retest]
---
# {short} retest bank (cold redo of your own mistakes)

Owner: the exercise-help role for {name}. Each item is a small NEW task built from one or more rows of [the error log]({log}), testing the same idea: never a current graded task and never the original task again. The student does it cold, without notes, in about 10 minutes. The owning session checks the answer against "Look for" and appends a retest row to the error log:

`| <date> | retest of <date of the original row> (R<n>) | ok / again, one line on what was shaky | what to look at next time | [retest] |`

`ok` = solved cold and correct at the first try (first compile for code). `again` = needed a hint or failed: the item comes back next week. An item that was `ok` twice is retired.
Picking: once a week the daily prep (or the student) takes up to {items} items of this course for a {minutes}-minute slot: never-tried items first, then the items tried longest ago. `python _agent/tools/error_log.py retest-pick --course {cid}` prints them.

| # | From log rows | Prompt (given to the student, no hints) | Look for |
|---|---|---|---|
"""


# ---------------------------------------------------------------- vault and config

def find_vault(explicit=None):
    cands = [explicit, os.environ.get('UNI_OS_VAULT')]
    here = os.path.abspath(os.getcwd())
    while True:
        cands.append(here)
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    cands.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for c in cands:
        if c and (os.path.isfile(os.path.join(c, '_agent', 'uni-os.toml')) or
                  os.path.isfile(os.path.join(c, '_agent', 'uni-os.json'))):
            return os.path.abspath(c)
    return None


def load_config(vault):
    js = os.path.join(vault, '_agent', 'uni-os.json')
    if os.path.isfile(js):
        with open(js, encoding='utf-8') as fh:
            return json.load(fh)
    import tomllib
    with open(os.path.join(vault, '_agent', 'uni-os.toml'), 'rb') as fh:
        return tomllib.load(fh)


def norm(s):
    return re.sub(r'[^a-z0-9]+', '', str(s or '').lower())


def study_opts(cfg):
    el = ((cfg.get('study') or {}).get('error_logs') or {})
    return {'retests': bool(el.get('retests', False)), 'retest_items': int(el.get('retest_items', 3)),
            'retest_minutes': int(el.get('retest_minutes', 20))}


def course_list(cfg):
    out = []
    for c in cfg.get('courses', []) or []:
        slug = c.get('slug') or norm(c.get('id'))
        streams = c.get('error_log_streams') or ['main']
        out.append({'id': c.get('id', slug), 'slug': slug, 'short': c.get('short') or slug.upper(),
                    'name': c.get('name') or slug, 'folder': c.get('folder') or slug.upper(),
                    'streams': [str(s) for s in streams]})
    return out


def find_course(cfg, key):
    k = norm(key)
    for c in course_list(cfg):
        if k in (norm(c['id']), norm(c['slug']), norm(c['short']), norm(c['folder']), norm(c['name'])):
            return c
    raise SystemExit(f'error: no course "{key}" in the config (try one of the course ids: '
                     + ', '.join(str(c['id']) for c in course_list(cfg)) + ')')


def log_entries(c):
    """[(stream, file)] with the rule of `uni-os init` (docs/file-formats.md, "Error-log row"): one stream -> <slug>-error-log.md,
    several -> <slug>-error-log-<stream>.md each."""
    streams = c['streams']
    if len(streams) == 1:
        return [(streams[0], f"{c['slug']}-error-log.md")]
    return [(s, f"{c['slug']}-error-log-{s}.md") for s in streams]


def log_paths(vault, c):
    return [(s, os.path.join(vault, c['folder'], f)) for s, f in log_entries(c)]


def term_label(cfg):
    return str((cfg.get('term') or {}).get('label') or 'this term')


def render_log(c, stream, today, term):
    """The text `uni-os init` renders from vault/{{course.folder}}/{{error_log.file}} (kept identical; tested)."""
    multi = len(c['streams']) > 1
    files = ', '.join(f for _s, f in log_entries(c))
    stream_line = (f'This course keeps one log per stream ({files}); this file is the "{stream}" stream, '
                   f'owned by the session that handles it.\n') if multi else ''
    header = HEADER_TEXT.format(name=c['name'], short=c['short'], session_suffix=f' ({stream})' if multi else '',
                                stream_line=stream_line)
    return LOG_TEMPLATE.format(cid=c['id'], short=c['short'], term=term, today=today, header=header,
                               stream=stream, stream_title=f' · {stream}' if multi else '')


# ---------------------------------------------------------------- table handling

def split_cells(line):
    parts = re.split(r'(?<!\\)\|', line.strip())
    if parts and parts[0].strip() == '':
        parts = parts[1:]
    if parts and parts[-1].strip() == '':
        parts = parts[:-1]
    return [p.strip() for p in parts]


def cell(text):
    t = str(text).strip().replace('\r\n', '\n').replace('\n', '<br>')
    return re.sub(r'(?<!\\)\|', r'\\|', t)


def find_section(lines, key):
    pats = SECTIONS[key]
    for i, ln in enumerate(lines):
        m = re.match(r'^#{2,3}\s+(.*?)\s*$', ln)
        if m and any(re.match(p, m.group(1).strip().lower()) for p in pats):
            return i
    return None


def find_table(lines):
    """Return (header_idx, sep_idx, last_row_idx) of the errors table, or None."""
    s = find_section(lines, 'errors')
    if s is None:
        return None
    i = s + 1
    while i < len(lines) and not lines[i].lstrip().startswith('|'):
        if re.match(r'^#{1,3}\s', lines[i]):
            return None
        i += 1
    if i + 1 >= len(lines) or not re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
        return None
    last = i + 1
    j = i + 2
    while j < len(lines) and lines[j].lstrip().startswith('|'):
        last = j
        j += 1
    return i, i + 1, last


def read_lines(path):
    """The file's lines and its line ending. Mixed endings are split correctly (CRLF from one
    tool, LF rows appended by another); the ending written back is the majority one. A trailing
    newline shows as a last empty element, so nl.join(lines) keeps it."""
    with open(path, encoding='utf-8', newline='') as fh:
        text = fh.read()
    crlf = text.count('\r\n')
    nl = '\r\n' if crlf and crlf * 2 >= text.count('\n') else '\n'
    return re.split(r'\r\n|\r|\n', text), nl


def utf8_stdio():
    """Print UTF-8 whatever the console or pipe encoding is (a Windows pipe defaults to cp1252,
    and a row with maths symbols would crash the print after the row was already written)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass  # not a real text stream (tests redirect to StringIO)


def bump_updated(lines, today):
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                break
            if lines[i].startswith('updated:'):
                lines[i] = f'updated: {today}'
                return
    return


def fmt_day(d):
    return f'{d:%a} {d.day} {d:%b}'


def parse_day(text, ref):
    """Parse 'Mon 26 Oct', '26 Oct', '26 Oct 2026', '2026-10-26' near the reference date (term start)."""
    t = re.sub(r'\*', '', str(text)).strip()
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?(?:\s+(\d{4}))?', t)
    if not m:
        return None
    try:
        month = datetime.datetime.strptime(m.group(2).title(), '%b').month
    except ValueError:
        return None
    day = int(m.group(1))
    if m.group(3):
        return datetime.date(int(m.group(3)), month, day)
    best = None
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = datetime.date(y, month, day)
        except ValueError:
            continue
        mid = ref + datetime.timedelta(days=70)
        if best is None or abs((d - mid).days) < abs((best - mid).days):
            best = d
    return best


def term_start(cfg):
    w0 = (cfg.get('term') or {}).get('week0_monday')
    if isinstance(w0, datetime.date):
        return w0
    try:
        return datetime.date.fromisoformat(str(w0))
    except (TypeError, ValueError):
        return datetime.date.today()


# ---------------------------------------------------------------- commands

def cmd_list(vault, cfg, a):
    for c in course_list(cfg):
        for stream, p in log_paths(vault, c):
            rel = os.path.relpath(p, vault)
            if not os.path.isfile(p):
                print(f'{c["slug"]:8} {stream:12} {rel}  (missing: run sync)')
                continue
            lines, _ = read_lines(p)
            t = find_table(lines)
            n = (t[2] - t[1]) if t else 0
            print(f'{c["slug"]:8} {stream:12} {rel}  {n} row(s)')
    return 0


def cmd_sync(vault, cfg, a):
    today = datetime.date.today().isoformat()
    made = 0
    for c in course_list(cfg):
        for stream, p in log_paths(vault, c):
            if os.path.exists(p):
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(render_log(c, stream, today, term_label(cfg)))
            print('created ' + os.path.relpath(p, vault))
            made += 1
    if not made:
        print('nothing to do: every log exists')
    return 0


def target_log(vault, c, stream):
    paths = log_paths(vault, c)
    if stream is None:
        if len(paths) > 1:  # never guess the stream: a row in the wrong log is a lost lesson
            raise SystemExit(f'error: course {c["slug"]} has several streams; pass --stream '
                             f'({", ".join(c["streams"])})')
        return paths[0][1]
    for s, p in paths:
        if norm(s) == norm(stream):
            return p
    raise SystemExit(f'error: course {c["slug"]} has no stream "{stream}" (streams: {", ".join(c["streams"])})')


def cmd_add(vault, cfg, a):
    c = find_course(cfg, a.course)
    path = target_log(vault, c, a.stream)
    if not os.path.isfile(path):
        raise SystemExit(f'error: {os.path.relpath(path, vault)} does not exist (run: error_log.py sync)')
    for name in ('where', 'what', 'idea', 'source'):
        if not str(getattr(a, name) or '').strip():
            raise SystemExit(f'error: --{name} must not be empty')
    day = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    row = '| ' + ' | '.join(cell(x) for x in (fmt_day(day), a.where, a.what, a.idea, a.source)) + ' |'
    lines, nl = read_lines(path)  # re-read right before writing: other writers may have appended meanwhile
    t = find_table(lines)
    if not t:
        raise SystemExit(f'error: no "Errors and misconceptions" table in {os.path.relpath(path, vault)} (run check)')
    lines.insert(t[2] + 1, row)
    bump_updated(lines, datetime.date.today().isoformat())
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(nl.join(lines))
    print(f'{os.path.relpath(path, vault)}: {row}')
    return 0


def check_file(path):
    problems = []
    lines, _ = read_lines(path)
    head = '\n'.join(lines[:12])
    if not re.search(r'(?m)^type:\s*error-log\s*$', head):
        problems.append('properties: "type: error-log" missing')
    for key, label in (('errors', 'Errors and misconceptions'), ('patterns', 'Patterns to watch'), ('open', 'Open points')):
        if find_section(lines, key) is None:
            problems.append(f'section "## {label}" missing')
    t = find_table(lines)
    if not t:
        problems.append('no table under "Errors and misconceptions"')
        return problems
    hdr = [h.lower() for h in split_cells(lines[t[0]])]
    if len(hdr) != 5 or hdr[0] != 'date' or hdr[1] not in LEGACY_WHERE or 'source' not in hdr[4]:
        problems.append('table header should be: | ' + ' | '.join(COLUMNS) + ' |')
    for i in range(t[1] + 1, t[2] + 1):
        n = len(split_cells(lines[i]))
        if n != 5:
            problems.append(f'line {i + 1}: {n} cells instead of 5 (an unescaped "|"? write \\|)')
    return problems


def cmd_check(vault, cfg, a):
    bad = 0
    courses = [find_course(cfg, a.course)] if a.course else course_list(cfg)
    for c in courses:
        for _stream, p in log_paths(vault, c):
            rel = os.path.relpath(p, vault)
            if not os.path.isfile(p):
                print(f'{rel}: missing (run sync)')
                bad += 1
                continue
            probs = check_file(p)
            print(f'{rel}: ' + ('ok' if not probs else f'{len(probs)} problem(s)'))
            for pr in probs:
                print('  ' + pr)
            bad += bool(probs)
    return 1 if bad else 0


def bank_path(vault, c):
    return os.path.join(vault, c['folder'], f"{c['slug']}-retest-bank.md")


def cmd_retest_bank(vault, cfg, a):
    c = find_course(cfg, a.course)
    opts = study_opts(cfg)
    if not opts['retests'] and not a.force:
        print('retests are off (study.error_logs.retests = false); turn them on in _agent/uni-os.toml or use --force')
        return 1
    p = bank_path(vault, c)
    if os.path.exists(p):
        print(f'{os.path.relpath(p, vault)} exists; nothing changed')
        return 0
    with open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(BANK_TEMPLATE.format(cid=c['id'], slug=c['slug'], short=c['short'], name=c['name'], today=datetime.date.today(),
                                      log=log_entries(c)[0][1], items=opts['retest_items'],
                                      minutes=opts['retest_minutes']))
    print('created ' + os.path.relpath(p, vault))
    return 0


def bank_items(path):
    lines, _ = read_lines(path)
    items = []
    for ln in lines:
        if not ln.lstrip().startswith('|'):
            continue
        cells = split_cells(ln)
        if len(cells) >= 4 and re.fullmatch(r'R\d+', cells[0].strip()):
            items.append({'id': cells[0].strip(), 'from': cells[1], 'prompt': cells[2], 'look': cells[3]})
    return items


def retest_results(vault, c, ref):
    res = {}
    for _s, p in log_paths(vault, c):
        if not os.path.isfile(p):
            continue
        lines, _ = read_lines(p)
        t = find_table(lines)
        if not t:
            continue
        for i in range(t[1] + 1, t[2] + 1):
            cells = split_cells(lines[i])
            if len(cells) < 3:
                continue
            m = re.search(r'retest\b.*?\((R\d+)\)', cells[1], re.I)
            if not m:
                continue
            outcome = 'ok' if re.match(r'\W*ok\b', cells[2], re.I) else ('again' if re.match(r'\W*again\b', cells[2], re.I) else None)
            if outcome:
                res.setdefault(m.group(1), []).append((parse_day(cells[0], ref), outcome))
    return res


def cmd_retest_pick(vault, cfg, a):
    c = find_course(cfg, a.course)
    p = bank_path(vault, c)
    if not os.path.isfile(p):
        print(f'no retest bank for {c["id"]} (create it with: error_log.py retest-bank --course {c["id"]})')
        return 1
    n = a.n or study_opts(cfg)['retest_items']
    res = retest_results(vault, c, term_start(cfg))
    cands = []
    for pos, it in enumerate(bank_items(p)):
        tries = res.get(it['id'], [])
        if sum(1 for _d, o in tries if o == 'ok') >= 2:
            continue  # retired
        last = max((d for d, _o in tries if d), default=None)
        cands.append(((0 if not tries else 1), last or datetime.date.min, pos, it, len(tries)))
    cands.sort(key=lambda x: (x[0], x[1], x[2]))
    if not cands:
        print('no open items (all retired, or the bank is empty)')
        return 0
    for _k, last, _pos, it, ntries in cands[:n]:
        seen = 'never tried' if not ntries else f'tried {ntries}x, last {fmt_day(last) if last != datetime.date.min else "?"}'
        print(f"{it['id']} ({seen}; from {it['from']})\n  Prompt: {it['prompt']}\n  Look for: {it['look']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description='Error-log helper for a Uni OS vault.')
    p.add_argument('--vault')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    sub.add_parser('sync')
    ad = sub.add_parser('add')
    ad.add_argument('--course', required=True)
    ad.add_argument('--stream')
    ad.add_argument('--where', required=True)
    ad.add_argument('--what', required=True)
    ad.add_argument('--idea', required=True)
    ad.add_argument('--source', required=True)
    ad.add_argument('--date')
    ck = sub.add_parser('check')
    ck.add_argument('--course')
    rb = sub.add_parser('retest-bank')
    rb.add_argument('--course', required=True)
    rb.add_argument('--force', action='store_true')
    rp = sub.add_parser('retest-pick')
    rp.add_argument('--course', required=True)
    rp.add_argument('--n', type=int)
    utf8_stdio()
    a = p.parse_args(argv)
    vault = find_vault(a.vault)
    if not vault:
        print('error: no vault found (no _agent/uni-os.toml); pass --vault', file=sys.stderr)
        return 1
    cfg = load_config(vault)
    return {'list': cmd_list, 'sync': cmd_sync, 'add': cmd_add, 'check': cmd_check,
            'retest-bank': cmd_retest_bank, 'retest-pick': cmd_retest_pick}[a.cmd](vault, cfg, a)


if __name__ == '__main__':
    sys.exit(main())
