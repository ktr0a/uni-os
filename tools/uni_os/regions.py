"""Generated regions: the parts of an installed file that ``uni-os render`` keeps current.

A template marks a generated part with two marker lines::

    <!-- uni-os:begin routing -->
    ... generated from the config and the enabled modules ...
    <!-- uni-os:end routing -->

Each marker stands alone on its line (leading and trailing spaces allowed). A name is
lowercase letters, digits and ``-`` (``registry``, ``roles-table``) and is unique within
the file. Regions do not nest.

When you (or an agent) edited an installed file, ``uni-os render`` no longer replaces
the whole file. If the file on disk and the fresh rendering contain exactly the same
set of well-formed regions, :func:`merge` replaces only the region bodies (the lines
between the markers) with the freshly rendered ones and leaves every other byte alone.
If a marker is missing, renamed, duplicated, nested or malformed, nothing is guessed:
the file is skipped and the reason reported.

Marker lines inside the region body are never part of it: the markers themselves are
kept as they are in the file. A line that starts with ``<!-- uni-os:`` but is not a
valid marker counts as malformed, so a typo never silently disables a region. A marker
quoted inside a sentence (not alone on its line) is plain text, not a marker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NAME = r"[a-z0-9][a-z0-9-]*"
_MARKER_RE = re.compile(rf"^[ \t]*<!--[ \t]*uni-os:(begin|end)[ \t]+({NAME})[ \t]*-->[ \t]*$")
_LOOSE_RE = re.compile(r"^[ \t]*<!--[ \t]*uni-os:", re.IGNORECASE)


def begin_marker(name: str) -> str:
    return f"<!-- uni-os:begin {name} -->"


def end_marker(name: str) -> str:
    return f"<!-- uni-os:end {name} -->"


@dataclass
class Region:
    name: str
    start: int  # offset of the first body character (just after the begin line)
    end: int  # offset of the end marker line (the body is text[start:end])


@dataclass
class Parsed:
    regions: list[Region] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return [r.name for r in self.regions]

    def body(self, text: str, name: str) -> str:
        for r in self.regions:
            if r.name == name:
                return text[r.start:r.end]
        raise KeyError(name)


def parse(text: str) -> Parsed:
    """Find the regions of ``text``; problems go to ``Parsed.errors`` (never raises)."""
    out = Parsed()
    seen: set[str] = set()
    open_name: str | None = None
    open_start = 0
    open_line = 0
    offset = 0
    for lineno, line in enumerate(text.splitlines(keepends=True), start=1):
        content = line.rstrip("\r\n")
        m = _MARKER_RE.match(content)
        if m:
            kind, name = m.group(1), m.group(2)
            if kind == "begin":
                if open_name is not None:
                    out.errors.append(f"line {lineno}: 'begin {name}' inside region '{open_name}' (regions do not nest)")
                elif name in seen:
                    out.errors.append(f"line {lineno}: region '{name}' appears twice")
                else:
                    open_name, open_start, open_line = name, offset + len(line), lineno
            else:
                if open_name is None:
                    out.errors.append(f"line {lineno}: 'end {name}' without a matching begin")
                elif name != open_name:
                    out.errors.append(f"line {lineno}: 'end {name}' closes region '{open_name}' (begun on line {open_line})")
                else:
                    out.regions.append(Region(name, open_start, offset))
                    seen.add(name)
                    open_name = None
        elif _LOOSE_RE.match(content):
            out.errors.append(
                f"line {lineno}: malformed marker '{content.strip()}' (expected '<!-- uni-os:begin <name> -->' or '<!-- uni-os:end <name> -->')"
            )
        offset += len(line)
    if open_name is not None:
        out.errors.append(f"line {open_line}: region '{open_name}' is never closed")
    return out


@dataclass
class MergeResult:
    """Outcome of :func:`merge`.

    ``text`` is the merged file (``None`` when skipped), ``changed`` the names of the
    regions whose body changed, ``problem`` why the file was skipped.
    """

    text: str | None = None
    names: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    problem: str | None = None


def has_regions(text: str) -> bool:
    """True if ``text`` contains at least one marker line (well-formed or not)."""
    return any(_LOOSE_RE.match(line) for line in text.splitlines())


def merge(current: str, fresh: str) -> MergeResult:
    """Replace the region bodies of ``current`` with those of ``fresh``.

    Both texts must contain the same set of well-formed regions. The order of the
    regions in ``current`` is kept. If ``current`` uses CRLF line endings, the new
    bodies get CRLF too.
    """
    new = parse(fresh)
    if new.errors:
        return MergeResult(problem="the module template's markers are malformed: " + "; ".join(new.errors))
    if not new.regions:
        return MergeResult(problem="the template has no generated regions")
    cur = parse(current)
    if cur.errors:
        return MergeResult(problem="markers in the file are missing or malformed: " + "; ".join(cur.errors))
    missing = [n for n in new.names if n not in cur.names]
    extra = [n for n in cur.names if n not in new.names]
    if missing or extra:
        parts = []
        if missing:
            parts.append("not in the file: " + ", ".join(missing))
        if extra:
            parts.append("no longer generated: " + ", ".join(extra))
        return MergeResult(problem="regions differ (" + "; ".join(parts) + ")")
    crlf = "\r\n" in current and current.count("\r\n") * 2 >= current.count("\n")
    pieces: list[str] = []
    changed: list[str] = []
    pos = 0
    for region in cur.regions:
        body = new.body(fresh, region.name)
        if crlf:
            body = body.replace("\r\n", "\n").replace("\n", "\r\n")
        old = current[region.start:region.end]
        if body != old:
            changed.append(region.name)
        pieces.append(current[pos:region.start])
        pieces.append(body)
        pos = region.end
    pieces.append(current[pos:])
    return MergeResult(text="".join(pieces), names=cur.names, changed=changed)
