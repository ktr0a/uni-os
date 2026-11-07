#!/usr/bin/env python3
"""Render selected pages of a PDF to PNG images so an agent can read them visually.

Part of the Uni OS module "handwritten-notes". Handwritten PDFs exported by a
tablet note app usually have no text layer, so agents read the pages as images.

Usage:
    python render_pages.py "<file.pdf>" [--pages 1-3,5] [--dpi 75] [--out <dir>]

Behaviour:
- Writes page-<n>.png files into --out (default: a new temporary folder outside
  the vault) and prints one absolute path per line.
- Refuses to write into the folder that holds the PDF (handwritten folders are
  written only by the note app) or any folder below it.
- Never modifies the PDF.
- Backends, in order: PyMuPDF (`import fitz`), then the `pdftoppm` command from
  poppler. If neither is available it exits with code 2 and says what to install.

Exit codes: 0 ok, 1 bad arguments or unreadable file, 2 no backend available.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def parse_pages(spec, page_count=None):
    """Parse "1-3,5" into a sorted list of 1-based page numbers."""
    if not spec:
        if page_count is None:
            raise ValueError("page count unknown")
        return list(range(1, page_count + 1))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text) if end_text else (page_count or start)
            if start < 1 or end < start:
                raise ValueError("bad page range: " + part)
            pages.update(range(start, end + 1))
        else:
            number = int(part)
            if number < 1:
                raise ValueError("bad page number: " + part)
            pages.add(number)
    result = sorted(pages)
    if page_count is not None:
        result = [p for p in result if p <= page_count]
    return result


def is_inside(child, parent):
    child = os.path.realpath(child)
    parent = os.path.realpath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:  # different drives on Windows
        return False


def render_with_pymupdf(pdf, pages_spec, dpi, out_dir):
    import fitz  # PyMuPDF

    written = []
    with fitz.open(pdf) as doc:
        pages = parse_pages(pages_spec, doc.page_count)
        for number in pages:
            page = doc.load_page(number - 1)
            pixmap = page.get_pixmap(dpi=dpi)
            target = os.path.join(out_dir, "page-%d.png" % number)
            pixmap.save(target)
            written.append(target)
    return written


def render_with_pdftoppm(pdf, pages_spec, dpi, out_dir):
    exe = shutil.which("pdftoppm")
    if not exe:
        return None
    if pages_spec:
        pages = parse_pages(pages_spec)
    else:
        pages = None
    written = []
    if pages is None:
        prefix = os.path.join(out_dir, "page")
        subprocess.run([exe, "-png", "-r", str(dpi), pdf, prefix], check=True)
        for name in sorted(os.listdir(out_dir)):
            if name.startswith("page") and name.endswith(".png"):
                written.append(os.path.join(out_dir, name))
        return written
    for number in pages:
        prefix = os.path.join(out_dir, "page-%d" % number)
        subprocess.run(
            [exe, "-png", "-r", str(dpi), "-f", str(number), "-l", str(number),
             "-singlefile", pdf, prefix],
            check=True,
        )
        target = prefix + ".png"
        if os.path.exists(target):
            written.append(target)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render PDF pages to PNG for reading.")
    parser.add_argument("pdf", help="path to the PDF (quote it: paths may contain spaces and &)")
    parser.add_argument("--pages", default="", help='pages to render, e.g. "1-3,5" (default: all)')
    parser.add_argument("--dpi", type=int, default=75, help="resolution (75 for handwriting, 110-150 for small writing)")
    parser.add_argument("--out", default="", help="output folder (default: a new temporary folder)")
    args = parser.parse_args(argv)

    pdf = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf):
        print("error: not a file: " + pdf, file=sys.stderr)
        return 1
    if args.dpi < 30 or args.dpi > 400:
        print("error: --dpi must be between 30 and 400", file=sys.stderr)
        return 1

    out_dir = os.path.abspath(args.out) if args.out else tempfile.mkdtemp(prefix="uni-os-pages-")
    if is_inside(out_dir, os.path.dirname(pdf)):
        print("error: refusing to write next to the PDF (handwritten folders are written only "
              "by the note app); choose an --out folder outside it", file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)

    try:
        try:
            written = render_with_pymupdf(pdf, args.pages, args.dpi, out_dir)
        except ImportError:
            written = render_with_pdftoppm(pdf, args.pages, args.dpi, out_dir)
            if written is None:
                print("error: no PDF renderer found. Install PyMuPDF (pip install pymupdf) "
                      "or poppler (pdftoppm).", file=sys.stderr)
                return 2
    except ValueError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # unreadable or encrypted PDF, renderer failure
        print("error: could not render: %s" % exc, file=sys.stderr)
        return 1

    for path in written:
        print(path)
    if not written:
        print("warning: no pages rendered (page range outside the document?)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
