"""Print a study page (HTML with KaTeX) to PDF with a headless Chromium browser (Chrome, Edge or Chromium).

Usage:
    python html2pdf.py <page.html> [<out.pdf>] [--browser auto|chrome|edge|chromium|<path>] [--wait-ms 15000]

<out.pdf> defaults to the page's path with .pdf. The page is opened as file:///...?print=1, which the study-page
template uses to open every <details> block (hint ladders, collapsible notes) before printing; its print CSS hides
the navigation and buttons. --wait-ms gives KaTeX (loaded from the CDN, so the machine needs internet) and the
page's JavaScript time to finish before the snapshot.

A throw-away browser profile is used, so a running browser and its logins are never touched.
The run counts as successful only if the PDF exists afterwards and is not empty ("exit 0 is not success").
Python 3 standard library only. Where no Chromium browser is installed, print from any browser instead
(Ctrl+P / Cmd+P -> "Save as PDF"), or for Markdown-only setups use Obsidian's "Export to PDF".
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

CANDIDATES = {
    'chrome': [
        r'%ProgramFiles%\Google\Chrome\Application\chrome.exe',
        r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe',
        r'%LocalAppData%\Google\Chrome\Application\chrome.exe',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'google-chrome', 'google-chrome-stable',
    ],
    'edge': [
        r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe',
        r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        'microsoft-edge', 'microsoft-edge-stable',
    ],
    'chromium': [
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        'chromium', 'chromium-browser',
    ],
}


def find_browser(choice='auto'):
    if choice not in ('auto', 'chrome', 'edge', 'chromium'):
        return choice if os.path.isfile(choice) else None
    order = ['chrome', 'edge', 'chromium'] if choice == 'auto' else [choice]
    for name in order:
        for cand in CANDIDATES[name]:
            path = os.path.expandvars(cand)
            if os.sep in path or '/' in path:
                if '%' not in path and os.path.isfile(path):
                    return path
            else:
                found = shutil.which(path)
                if found:
                    return found
    return None


def to_pdf(html_path, pdf_path, browser, wait_ms=15000, timeout_s=120):
    url = pathlib.Path(os.path.abspath(html_path)).as_uri() + '?print=1'
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with tempfile.TemporaryDirectory() as profile:
        cmd = [browser, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
               f'--user-data-dir={profile}', '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
               f'--virtual-time-budget={int(wait_ms)}', f'--print-to-pdf={pdf_path}', url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    ok = os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0
    return ok, r.returncode, (r.stderr or '')[-400:]


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
    p = argparse.ArgumentParser(description='Print a study page to PDF with headless Chrome/Edge/Chromium.')
    p.add_argument('src')
    p.add_argument('dst', nargs='?')
    p.add_argument('--browser', default='auto')
    p.add_argument('--wait-ms', type=int, default=15000)
    utf8_stdio()
    a = p.parse_args(argv)
    dst = a.dst or os.path.splitext(a.src)[0] + '.pdf'
    exe = find_browser(a.browser)
    if not exe:
        print('No Chrome, Edge or Chromium found. Print from a browser instead (Ctrl+P -> Save as PDF).', file=sys.stderr)
        return 2
    ok, code, err = to_pdf(a.src, dst, exe, a.wait_ms)
    if not ok:
        print(f'PDF was not written (browser exit {code}). {err.strip()}', file=sys.stderr)
        return 1
    print(f'{dst} ({os.path.getsize(dst)} bytes, printed with {os.path.basename(exe)})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
