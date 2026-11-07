#!/usr/bin/env python3
"""Reference parser and checker for daily prep notes (stdlib only, Python 3.9+).

The executable version of the contract in the vault's semester/prep/README.md (and in
modules/daily-prep/README.md, "File formats"): file naming `prep-YYYY-MM-DD[-rN].md` (highest
revision wins, then the latest `generated`), the frontmatter, the title, one callout per block
`> [!<course>] HH:MM-HH:MM <title>` in time order, `> - ` items, and `## Gaps` as the last section.

The morning check's fourth test ("every vault path and relative link exists on disk") is
deterministic, so this script can do it for an agent:

  python prep_note.py check <vault> [--date YYYY-MM-DD]   validate the newest note of the date
                                                          (default: today) and test its paths
  python prep_note.py newest <vault> --date YYYY-MM-DD    print the newest note's file name
  python prep_note.py parse <note.md>                     print the parsed note as JSON

Read-only: it never writes. Exit code 1 when a problem is found.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path

NAME_RE = re.compile(r"^prep-(\d{4}-\d{2}-\d{2})(?:-r(\d+))?\.md$")
CALLOUT_RE = re.compile(r"^>\s*\[!([A-Za-z0-9_-]+)\][+-]?\s+(\d{2}):(\d{2})-(\d{2}):(\d{2})\s+(.+?)\s*$")
# Readers tolerate a suffix after "(week N)" (old notes say ", revision 2"); writers don't add one.
TITLE_RE = re.compile(r"^# Prep for (Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2}) ([A-Z][a-z]{2}) (\d{4}) \(week (-?\d+)\).*$")
RUN_RE = re.compile(r"^(\d{2}:\d{2}|manual)$")
GENERATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:?\d{2}|Z)$")
NO_GAPS = {"none", "no gaps", "nothing", "-", ""}
REQUIRED = ["type", "date", "generated", "run", "status"]
STATUSES = {"ready", "ready-with-gaps"}


def revision_of(name: str) -> tuple[str, int] | None:
    """('YYYY-MM-DD', N) for a prep note file name; the plain name is revision 1."""
    m = NAME_RE.match(name)
    if not m:
        return None
    return m.group(1), int(m.group(2) or 1)


def _frontmatter(text: str) -> tuple[dict, list[str]]:
    text = text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines
    meta: dict = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return meta, lines[i + 1:]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*(?:#.*)?$", lines[i])
        if m:
            meta[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return {}, lines


def parse_prep(text: str) -> dict:
    meta, body = _frontmatter(text)
    title = next((ln for ln in body if ln.startswith("# ")), "")
    callouts: list[dict] = []
    gaps: list[str] = []
    headings: list[str] = []
    intro: list[str] = []
    current = None
    in_gaps = False
    seen_title = False
    for ln in body:
        if ln.startswith("# "):
            seen_title = True
            continue
        if ln.startswith("## "):
            headings.append(ln[3:].strip())
            in_gaps = ln[3:].strip().lower().startswith("gaps")
            current = None
            continue
        m = CALLOUT_RE.match(ln)
        if m:
            current = {"course": m.group(1).lower(), "start": f"{m.group(2)}:{m.group(3)}",
                       "end": f"{m.group(4)}:{m.group(5)}", "title": m.group(6), "items": []}
            callouts.append(current)
            continue
        if current is not None and ln.startswith(">"):
            content = ln[1:].strip()
            if content.startswith("- "):
                current["items"].append(content[2:].strip())
            elif content and current["items"]:
                current["items"][-1] += " " + content
            continue
        if current is not None and not ln.strip():
            current = None
            continue
        if in_gaps and ln.strip().startswith("- "):
            gaps.append(ln.strip()[2:].strip())
        elif seen_title and not callouts and not headings and ln.strip():
            intro.append(ln.strip())
    real_gaps = [g for g in gaps if g.strip().lower().rstrip(".") not in NO_GAPS]
    return {"meta": meta, "title": title, "intro": " ".join(intro), "callouts": callouts,
            "gaps": real_gaps, "gaps_raw": gaps, "headings": headings}


def validate(text: str, name: str = "") -> list[str]:
    p = parse_prep(text)
    meta = p["meta"]
    out: list[str] = []
    tag = name or "note"
    for k in REQUIRED:
        if not meta.get(k):
            out.append(f"{tag}: property '{k}' missing")
    if meta.get("type") and meta["type"] != "prep":
        out.append(f"{tag}: type is '{meta['type']}', not 'prep'")
    if meta.get("status") and meta["status"] not in STATUSES:
        out.append(f"{tag}: status '{meta['status']}' is not ready | ready-with-gaps")
    if meta.get("run") and not RUN_RE.match(meta["run"]):
        out.append(f"{tag}: run '{meta['run']}' is not HH:MM or manual")
    if meta.get("generated") and not GENERATED_RE.match(meta["generated"]):
        out.append(f"{tag}: generated '{meta['generated']}' is not ISO with an offset")
    rev = revision_of(name) if name else None
    if rev and meta.get("date") and meta["date"] != rev[0]:
        out.append(f"{tag}: date property {meta['date']} differs from the file name")
    m = TITLE_RE.match(p["title"])
    if not m:
        out.append(f"{tag}: title is not '# Prep for Ddd D Mon YYYY (week N)'")
    elif meta.get("date"):
        try:
            d = dt.date.fromisoformat(meta["date"])
            if (d.day, d.strftime("%b"), d.year, d.strftime("%a")) != (int(m.group(2)), m.group(3), int(m.group(4)), m.group(1)):
                out.append(f"{tag}: title date does not match the date property")
        except ValueError:
            out.append(f"{tag}: date property is not an ISO date")
    last = ""
    for c in p["callouts"]:
        if c["end"] <= c["start"]:
            out.append(f"{tag}: callout {c['start']}-{c['end']} ends before it starts")
        if c["start"] < last:
            out.append(f"{tag}: callouts are not in time order ({c['start']} after {last})")
        last = c["start"]
    if not p["headings"] or not p["headings"][-1].lower().startswith("gaps"):
        out.append(f"{tag}: '## Gaps' is not the last section")
    elif not p["gaps_raw"]:
        out.append(f"{tag}: '## Gaps' is empty (write '- none')")
    if meta.get("status") == "ready" and p["gaps"]:
        out.append(f"{tag}: status ready but {len(p['gaps'])} gap(s) listed (use ready-with-gaps)")
    if meta.get("status") == "ready-with-gaps" and not p["gaps"]:
        out.append(f"{tag}: status ready-with-gaps but no gap listed")
    return out


def paths_in(text: str) -> list[str]:
    """Vault-relative paths the note points to: backticked paths with an extension, and relative
    Markdown links (resolved from semester/prep/). Web links and anchors are ignored."""
    found: list[str] = []
    for m in re.finditer(r"`([^`\n]+?\.[A-Za-z0-9]{1,6})`", text):
        s = m.group(1).strip()
        if "/" in s and not re.match(r"^[a-z]+://", s):
            found.append(s)
    for m in re.finditer(r"\]\((<[^>]+>|[^)\s]+)\)", text):
        target = m.group(1).strip("<>")
        if re.match(r"^[a-z]+:", target) or not target.startswith("../"):
            continue
        target = urllib.parse.unquote(target.split("#", 1)[0])
        parts = ["semester", "prep"]
        for seg in target.split("/"):
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg and seg != ".":
                parts.append(seg)
        found.append("/".join(parts))
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def missing_paths(vault: Path, text: str) -> list[str]:
    return [p for p in paths_in(text) if not (vault / p).exists()]


def newest(prep_dir: Path, date: str) -> Path | None:
    best = None
    best_key = None
    for f in prep_dir.glob(f"prep-{date}*.md"):
        rev = revision_of(f.name)
        if not rev or rev[0] != date:
            continue
        gen = parse_prep(f.read_text(encoding="utf-8"))["meta"].get("generated", "")
        key = (rev[1], gen)
        if best_key is None or key > best_key:
            best, best_key = f, key
    return best


def material_header(note_name: str, when: dt.datetime, obsidian: bool = True) -> str:
    """The first line of the MATERIAL block for calendar descriptions."""
    where = "Obsidian" if obsidian else "the vault"
    stamp = f"{when.strftime('%a')} {when.day} {when.strftime('%b %H:%M')}"
    return f"MATERIAL (daily prep, {stamp}; all of it in {where}: semester/prep/{note_name.removesuffix('.md')})"


def utf8_stdio():
    """Print UTF-8 whatever the console or pipe encoding is (a Windows pipe defaults to cp1252,
    which cannot encode many symbols that vault notes contain)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # not a real text stream (tests redirect to StringIO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("vault")
    c.add_argument("--date", default=None)
    n = sub.add_parser("newest")
    n.add_argument("vault")
    n.add_argument("--date", required=True)
    p = sub.add_parser("parse")
    p.add_argument("file")
    utf8_stdio()
    a = ap.parse_args(argv)
    if a.cmd == "parse":
        print(json.dumps(parse_prep(Path(a.file).read_text(encoding="utf-8")), indent=2, ensure_ascii=False))
        return 0
    vault = Path(a.vault)
    date = a.date or dt.date.today().isoformat()
    f = newest(vault / "semester" / "prep", date)
    if a.cmd == "newest":
        if not f:
            print(f"no prep note for {date}")
            return 1
        print(f.name)
        return 0
    if not f:
        print(f"PROBLEM no prep note for {date}")
        return 1
    text = f.read_text(encoding="utf-8")
    problems = validate(text, f.name) + [f"{f.name}: missing path {m}" for m in missing_paths(vault, text)]
    parsed = parse_prep(text)
    for pr in problems:
        print("PROBLEM " + pr)
    print(f"{f.name}: {len(parsed['callouts'])} callout(s), {len(parsed['gaps'])} gap(s), "
          f"{len(paths_in(text))} path(s) checked; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
