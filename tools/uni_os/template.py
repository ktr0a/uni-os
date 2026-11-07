"""The Uni OS template engine (summary: ``docs/file-formats.md``, section "Template language").

Every text file under ``modules/<id>/vault/``, ``jobs/``, ``roles/`` and ``skills/``
is a template unless the module lists it under ``verbatim``. The language is a
small, strict, Handlebars-like subset.

Values
    ``{{ key.path }}`` is replaced by the config value. Only paths whose first
    segment is a *known root* are template keys::

        student university term paths storage obsidian agent study courses course
        schedule notify calendar runtime vm cockpit modules uni_os generated

    plus the loop/expansion roots ``item`` and ``error_log``. Anything else is
    left untouched, byte for byte: Obsidian's ``{{date}}``, ``{{date:YYYY-MM-DD}}``,
    ``{{title}}``, and the reserved runtime root ``{{week.*}}`` that
    ``uni-os new-week`` fills in later. Lists render joined by ``", "``; booleans
    render ``true``/``false``; dates render ISO (``2026-09-14``). A missing key under
    a known root is an error that names the file, line and key.

    Path segments may be list indices (``courses.0.name``) or, for lists of tables
    with an ``id`` key, ids (``courses.algo.name``).

Blocks
    ``{{#each courses}} ... {{/each}}`` binds ``course`` to the current item;
    ``{{#each <any other list>}} ... {{/each}}`` binds ``item`` (e.g.
    ``{{#each course.assessments}}{{item.name}}{{/each}}``). Inside a loop
    ``{{@index}}`` (0-based), ``{{@first}}`` and ``{{@last}}`` are available. An
    ``{{else}}`` branch in an each block renders when the list is empty.

    ``{{#if cond}} ... {{else}} ... {{/if}}`` and ``{{#unless cond}} ... {{/unless}}``.
    ``cond`` is a key path (truthiness), ``path == "literal"``, ``path != "literal"``
    or ``path contains "literal"`` (list membership / substring). Literals are
    quoted strings, numbers, ``true`` or ``false``.

    Truthiness: ``false``, ``""``, ``0``, empty lists/tables and the string
    ``"none"`` are false. ``modules.<id>`` is true when that module is enabled and
    false otherwise (never an error).

Whitespace
    A block tag (``{{#each}}``, ``{{#if}}``, ``{{#unless}}``, ``{{else}}``, closing
    tags) that stands alone on its line removes that whole line, so loops can
    build Markdown tables without blank lines.

Escaping
    ``\\{{course.name}}`` renders the literal text ``{{course.name}}`` (the backslash
    is dropped). Use it in docs that explain the template language.

The engine is deliberately strict: unknown block syntax under a known root,
unbalanced blocks and missing keys raise :class:`~uni_os.errors.TemplateError`.
"""

from __future__ import annotations

import bisect
import datetime as _dt
import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .errors import TemplateError

#: Roots that are substituted at install time.
KNOWN_ROOTS = frozenset(
    "student university term paths storage obsidian agent study courses course schedule "
    "notify calendar runtime vm cockpit modules uni_os generated".split()
)
#: Roots that only exist inside a loop (``item``) or an expanded path (``error_log``).
BOUND_ROOTS = frozenset({"item", "error_log"})
#: Roots reserved for later tools; never substituted at install time.
RESERVED_ROOTS = frozenset({"week", "date", "time", "title"})
#: Roots processed by a normal install-time render.
INSTALL_ROOTS = KNOWN_ROOTS | BOUND_ROOTS

LIST_SEPARATOR = ", "
LOOP_VARS = ("@index", "@first", "@last")

_TAG_RE = re.compile(r"\{\{([^{}\n]*)\}\}")
_SEG = r"(?:[A-Za-z_][A-Za-z0-9_-]*|\d+)"
_PATH = rf"(?:@(?:index|first|last)|[A-Za-z_][A-Za-z0-9_-]*(?:\.{_SEG})*)"
_PATH_FULL_RE = re.compile(rf"^{_PATH}$")
_LITERAL = r"(?:\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?|true|false)"
_COND_RE = re.compile(rf"^(?P<path>{_PATH})(?:\s+(?P<op>==|!=|contains)\s+(?P<lit>{_LITERAL}))?$")
_OPEN_RE = re.compile(r"^#(each|if|unless)(?:\s+(.*))?$", re.S)
_CLOSE_RE = re.compile(r"^/(each|if|unless)$")
_LEADING_ROOT_RE = re.compile(r"^(@?[A-Za-z_][A-Za-z0-9_-]*)")


# --------------------------------------------------------------------------- AST


@dataclass
class _Text:
    text: str


@dataclass
class _Var:
    path: str
    line: int


@dataclass
class _Block:
    kind: str  # each | if | unless
    path: str
    op: str | None
    literal: Any
    line: int
    body: list = field(default_factory=list)
    else_body: list | None = None


@dataclass
class _Frame:
    kind: str
    block: _Block | None  # None = passthrough block (unknown root, emitted verbatim)
    target: list
    line: int


# --------------------------------------------------------------------------- helpers


def _root_of(path: str) -> str:
    return path.split(".", 1)[0]


def _parse_literal(text: str) -> Any:
    if text[0] in "\"'":
        return text[1:-1]
    if text == "true":
        return True
    if text == "false":
        return False
    if "." in text:
        return float(text)
    return int(text)


def is_truthy(value: Any) -> bool:
    """Template truthiness: ``None``, ``False``, ``0``, blank strings, ``"none"`` (any case)
    and empty lists and tables are false; everything else is true."""
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip() != "" and value.strip().lower() != "none"
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def to_text(value: Any, *, path: str = "") -> str:
    """Render one value as text (lists joined by ``", "``)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = repr(value)
        return text[:-2] if text.endswith(".0") else text
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, _dt.time):
        return value.strftime("%H:%M") if value.second == 0 else value.isoformat()
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            if isinstance(item, (dict, list, tuple)):
                raise TemplateError(
                    f"'{path}' is a list of tables and cannot be printed directly",
                    key=path,
                    hint="loop over it with {{#each " + path + "}} ... {{/each}}",
                )
            parts.append(to_text(item, path=path))
        return LIST_SEPARATOR.join(parts)
    if isinstance(value, dict):
        raise TemplateError(
            f"'{path}' is a table and cannot be printed directly",
            key=path,
            hint="use one of its keys: " + ", ".join(f"{path}.{k}" for k in list(value)[:6]),
        )
    if value is None:
        return ""
    return str(value)


def _equals(value: Any, literal: Any) -> bool:
    if isinstance(literal, bool):
        return isinstance(value, bool) and value == literal
    if isinstance(literal, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value == literal
    try:
        return to_text(value) == literal
    except TemplateError:
        return False


class _Missing(Exception):
    def __init__(self, path: str, depth: int, available: Iterable[str]):
        super().__init__(path)
        self.path = path
        self.depth = depth
        self.available = [str(a) for a in available]


def walk(value: Any, segments: list[str], path: str, offset: int = 1) -> Any:
    """Follow ``segments`` into ``value`` (dict keys, list indices or ids).

    Raises ``_Missing`` (internal) when a segment does not exist.
    """
    for i, seg in enumerate(segments):
        depth = offset + i
        if isinstance(value, dict):
            if seg in value:
                value = value[seg]
                continue
            raise _Missing(path, depth, value.keys())
        if isinstance(value, (list, tuple)):
            if seg.isdigit():
                idx = int(seg)
                if idx < len(value):
                    value = value[idx]
                    continue
                raise _Missing(path, depth, [str(n) for n in range(len(value))])
            for entry in value:
                if isinstance(entry, dict) and entry.get("id") == seg:
                    value = entry
                    break
            else:
                ids = [str(e.get("id")) for e in value if isinstance(e, dict) and "id" in e]
                raise _Missing(path, depth, ids)
            continue
        raise _Missing(path, depth, [])
    return value


def _missing_error(exc: _Missing, *, line: int | None, filename: str | None, bound: dict | None) -> TemplateError:
    segs = exc.path.split(".")
    parent = ".".join(segs[: exc.depth]) or segs[0]
    missing = segs[exc.depth] if exc.depth < len(segs) else segs[-1]
    msg = f"missing config key '{exc.path}'"
    if exc.depth == 0:
        msg += f" (no [{missing}] table in the config)"
    else:
        msg += f" ('{parent}' has no key '{missing}')"
    if bound and "course" in bound and segs[0] == "course" and isinstance(bound["course"], dict):
        msg += f" for course '{bound['course'].get('id', '?')}'"
    hint_parts = []
    close = difflib.get_close_matches(missing, exc.available, n=2, cutoff=0.6)
    if close:
        hint_parts.append("did you mean " + " or ".join(f"'{parent}.{c}'" if exc.depth else f"'{c}'" for c in close) + "?")
    hint_parts.append("add it to uni-os.toml or to the module's [defaults]")
    return TemplateError(msg, filename=filename, line=line, key=exc.path, hint="; ".join(hint_parts))


# --------------------------------------------------------------------------- compiler


class Template:
    """A compiled template; render it many times with different bindings."""

    def __init__(self, nodes: list, filename: str, roots: frozenset[str]):
        self.nodes = nodes
        self.filename = filename
        self.roots = roots

    # -- rendering -----------------------------------------------------------------

    def render(
        self,
        context: dict,
        *,
        bindings: dict | None = None,
        known_modules: Iterable[str] | None = None,
        warnings: list | None = None,
    ) -> str:
        """Render with ``context`` (the resolved config + ``generated`` + ``modules``).

        ``bindings`` pre-binds loop roots, e.g. ``{"course": {...}}`` for per-course
        path expansion. ``known_modules`` (ids) turns references to unknown module
        ids in ``modules.<id>`` into warnings appended to ``warnings``.
        """
        scope = _Scope(context, bindings or {}, self.filename, known_modules, warnings)
        out: list[str] = []
        self._render_nodes(self.nodes, scope, out)
        return "".join(out)

    def _render_nodes(self, nodes: list, scope: "_Scope", out: list[str]) -> None:
        for node in nodes:
            if isinstance(node, _Text):
                out.append(node.text)
            elif isinstance(node, _Var):
                value = scope.lookup(node.path, node.line)
                try:
                    out.append(to_text(value, path=node.path))
                except TemplateError as exc:
                    raise exc.located(self.filename, node.line)
            else:
                self._render_block(node, scope, out)

    def _render_block(self, block: _Block, scope: "_Scope", out: list[str]) -> None:
        if block.kind == "each":
            value = scope.lookup(block.path, block.line)
            if isinstance(value, dict) or not isinstance(value, (list, tuple)):
                raise TemplateError(
                    f"{{{{#each {block.path}}}}} needs a list, but '{block.path}' is "
                    f"{'a table' if isinstance(value, dict) else type(value).__name__}",
                    filename=self.filename,
                    line=block.line,
                    key=block.path,
                )
            if not value:
                if block.else_body:
                    self._render_nodes(block.else_body, scope, out)
                return
            name = "course" if block.path == "courses" else "item"
            last = len(value) - 1
            for idx, entry in enumerate(value):
                scope.push({name: entry, "@index": idx, "@first": idx == 0, "@last": idx == last})
                try:
                    self._render_nodes(block.body, scope, out)
                finally:
                    scope.pop()
            return
        result = scope.condition(block)
        if block.kind == "unless":
            result = not result
        if result:
            self._render_nodes(block.body, scope, out)
        elif block.else_body:
            self._render_nodes(block.else_body, scope, out)


class _Scope:
    def __init__(self, context, bindings, filename, known_modules, warnings):
        self.context = context
        self.frames: list[dict] = [dict(bindings)] if bindings else []
        self.filename = filename
        self.known_modules = set(known_modules) if known_modules is not None else None
        self.warnings = warnings
        self._warned: set[str] = set()

    def push(self, frame: dict) -> None:
        self.frames.append(frame)

    def pop(self) -> None:
        self.frames.pop()

    def _bound(self) -> dict:
        merged: dict = {}
        for frame in self.frames:
            merged.update(frame)
        return merged

    def lookup(self, path: str, line: int) -> Any:
        segs = path.split(".")
        root = segs[0]
        if root.startswith("@"):
            for frame in reversed(self.frames):
                if root in frame:
                    return frame[root]
            raise TemplateError(f"{{{{{root}}}}} can only be used inside {{{{#each}}}}", filename=self.filename, line=line)
        if root == "modules":
            return self._modules(segs, line)
        base_found = False
        base = None
        for frame in reversed(self.frames):
            if root in frame:
                base, base_found = frame[root], True
                break
        if not base_found:
            if root == "course":
                raise TemplateError(
                    f"'{{{{{path}}}}}' used outside a course loop",
                    filename=self.filename,
                    line=line,
                    key=path,
                    hint="use it inside {{#each courses}} ... {{/each}} or in a file whose path contains {{course.<key>}}",
                )
            if root in BOUND_ROOTS:
                where = "{{#each <list>}}" if root == "item" else "a file whose path contains {{error_log.<key>}}"
                raise TemplateError(
                    f"'{{{{{path}}}}}' used outside {where}", filename=self.filename, line=line, key=path
                )
            if root not in self.context:
                raise _missing_error(_Missing(path, 0, self.context.keys()), line=line, filename=self.filename, bound=None)
            base = self.context[root]
        try:
            return walk(base, segs[1:], path)
        except _Missing as exc:
            raise _missing_error(exc, line=line, filename=self.filename, bound=self._bound())

    def _modules(self, segs: list[str], line: int) -> Any:
        mods = self.context.get("modules") or {}
        enabled = list(mods.get("enabled") or [])
        if len(segs) == 1:
            return enabled
        name = segs[1]
        if name == "enabled":
            try:
                return walk(enabled, segs[2:], ".".join(segs), offset=2)
            except _Missing as exc:
                raise _missing_error(exc, line=line, filename=self.filename, bound=None)
        if len(segs) > 2:
            raise TemplateError(
                f"'modules.{name}' is true or false (module enabled?) and has no sub-keys",
                filename=self.filename,
                line=line,
                key=".".join(segs),
            )
        if self.known_modules is not None and name not in self.known_modules and name not in self._warned:
            self._warned.add(name)
            if self.warnings is not None:
                loc = f"{self.filename}:{line}" if self.filename else f"line {line}"
                self.warnings.append(f"{loc}: unknown module id '{name}' in modules.{name} (always false)")
        return name in enabled

    def condition(self, block: _Block) -> bool:
        value = self.lookup(block.path, block.line)
        if block.op is None:
            return is_truthy(value)
        if block.op == "==":
            return _equals(value, block.literal)
        if block.op == "!=":
            return not _equals(value, block.literal)
        # contains
        if isinstance(value, (list, tuple)):
            return any(_equals(v, block.literal) for v in value)
        if isinstance(value, dict):
            return str(block.literal) in value
        if isinstance(value, str):
            return str(block.literal) in value
        raise TemplateError(
            f"'contains' needs a list, table or string, but '{block.path}' is {type(value).__name__}",
            filename=self.filename,
            line=block.line,
            key=block.path,
        )


def _classify(inner: str, roots: frozenset[str], filename: str, line: int):
    """Classify the inside of ``{{ ... }}``.

    Returns ``None`` for text that is not ours (left untouched), or a tuple:
    ``("var", path)``, ``("open", kind, path, op, literal)``,
    ``("open-pass", kind)`` (block with an unknown root: emitted verbatim),
    ``("else",)``, ``("close", kind)``.
    """
    if inner == "else":
        return ("else",)
    m = _CLOSE_RE.match(inner)
    if m:
        return ("close", m.group(1))
    m = _OPEN_RE.match(inner)
    if m:
        kind, expr = m.group(1), (m.group(2) or "").strip()
        lead = _LEADING_ROOT_RE.match(expr)
        root = lead.group(1) if lead else ""
        if not root or (not root.startswith("@") and root not in roots):
            if not root and not expr:
                raise TemplateError(f"{{{{#{kind}}}}} needs an argument", filename=filename, line=line)
            return ("open-pass", kind)
        if kind == "each":
            if not _PATH_FULL_RE.match(expr) or expr.startswith("@"):
                raise TemplateError(f"unsupported expression in {{{{#each {expr}}}}}", filename=filename, line=line)
            return ("open", kind, expr, None, None)
        cm = _COND_RE.match(expr)
        if not cm:
            raise TemplateError(
                f"unsupported condition '{expr}'",
                filename=filename,
                line=line,
                hint='use a key, key == "text", key != "text" or key contains "text"',
            )
        lit = cm.group("lit")
        return ("open", kind, cm.group("path"), cm.group("op"), _parse_literal(lit) if lit is not None else None)
    lead = _LEADING_ROOT_RE.match(inner)
    if not lead:
        return None
    root = lead.group(1)
    if root.startswith("@"):
        if inner in LOOP_VARS:
            return ("var", inner)
        return None
    if root not in roots:
        return None
    if not _PATH_FULL_RE.match(inner):
        raise TemplateError(
            f"unsupported expression '{{{{{inner}}}}}'",
            filename=filename,
            line=line,
            hint="only plain key paths like {{course.name}} are supported",
        )
    return ("var", inner)


def compile(text: str, filename: str = "<template>", *, roots: Iterable[str] | None = None) -> Template:  # noqa: A001
    """Parse ``text`` into a :class:`Template`.

    ``roots`` defaults to the install-time roots (known + loop roots). Pass a
    different set to process other roots (``uni-os new-week`` adds ``week``).
    """
    active = frozenset(roots) if roots is not None else INSTALL_ROOTS
    line_starts = [0]
    idx = text.find("\n")
    while idx != -1:
        line_starts.append(idx + 1)
        idx = text.find("\n", idx + 1)

    def lineno(offset: int) -> int:
        return bisect.bisect_right(line_starts, offset)

    nodes: list = []
    stack: list[_Frame] = []
    target = nodes
    pos = 0

    for m in _TAG_RE.finditer(text):
        start, end = m.span()
        if start < pos:
            continue
        inner = m.group(1).strip()
        line = lineno(start)
        cls = _classify(inner, active, filename, line)
        if cls is None:
            continue
        kind = cls[0]
        in_passthrough = bool(stack) and stack[-1].block is None

        # Escaped tag: \{{...}} renders literally (backslash dropped). Tags inside a
        # verbatim (foreign) block are left exactly as written.
        if start > 0 and text[start - 1] == "\\" and kind != "open-pass":
            if kind in ("else", "close") and in_passthrough:
                continue
            target.append(_Text(text[pos : start - 1]))
            target.append(_Text(m.group(0)))
            pos = end
            continue

        # Passthrough handling: else/close that belong to a verbatim block stay text.
        if kind == "else" and (not stack or in_passthrough):
            continue
        if kind == "open-pass":
            stack.append(_Frame(cls[1], None, target, line))
            continue
        if kind == "close":
            if not stack:
                raise TemplateError(f"{{{{/{cls[1]}}}}} without a matching {{{{#{cls[1]}}}}}", filename=filename, line=line)
            top = stack[-1]
            if top.kind != cls[1]:
                raise TemplateError(
                    f"{{{{/{cls[1]}}}}} closes {{{{#{top.kind}}}}} opened on line {top.line}",
                    filename=filename,
                    line=line,
                )
            if top.block is None:
                stack.pop()
                continue

        # Standalone block tags remove their whole line.
        chunk_end, new_pos = start, end
        if kind in ("open", "else", "close"):
            line_start = text.rfind("\n", 0, start) + 1
            nl = text.find("\n", end)
            line_end = len(text) if nl == -1 else nl
            if (
                line_start >= pos
                and text[line_start:start].strip(" \t") == ""
                and text[end:line_end].strip(" \t\r") == ""
            ):
                chunk_end = line_start
                new_pos = len(text) if nl == -1 else nl + 1
        if chunk_end > pos:
            target.append(_Text(text[pos:chunk_end]))
        pos = new_pos

        if kind == "var":
            target.append(_Var(cls[1], line))
        elif kind == "open":
            block = _Block(cls[1], cls[2], cls[3], cls[4], line)
            target.append(block)
            stack.append(_Frame(cls[1], block, target, line))
            target = block.body
        elif kind == "else":
            frame = stack[-1]
            if frame.block.else_body is not None:
                raise TemplateError(f"second {{{{else}}}} in the block opened on line {frame.line}", filename=filename, line=line)
            frame.block.else_body = []
            target = frame.block.else_body
        elif kind == "close":
            frame = stack.pop()
            target = frame.target

    if pos < len(text):
        target.append(_Text(text[pos:]))
    for frame in reversed(stack):
        if frame.block is not None:
            raise TemplateError(f"{{{{#{frame.kind}}}}} is never closed", filename=filename, line=frame.line)
    return Template(nodes, filename, active)


# --------------------------------------------------------------------------- API


def render(
    text: str,
    context: dict,
    *,
    filename: str = "<template>",
    bindings: dict | None = None,
    roots: Iterable[str] | None = None,
    known_modules: Iterable[str] | None = None,
    warnings: list | None = None,
) -> str:
    """Compile and render ``text`` in one go. See the module docstring for the syntax."""
    return compile(text, filename, roots=roots).render(
        context, bindings=bindings, known_modules=known_modules, warnings=warnings
    )


def lookup(
    path: str,
    context: dict,
    *,
    bindings: dict | None = None,
    filename: str = "<template>",
    known_modules: Iterable[str] | None = None,
    warnings: list | None = None,
) -> Any:
    """The value of a key path, resolved exactly like ``{{path}}`` in a template.

    ``bindings`` pre-binds loop roots (``course``, ``item``, ``error_log``). A missing
    key raises :class:`~uni_os.errors.TemplateError`.
    """
    scope = _Scope(context, bindings or {}, filename, known_modules, warnings)
    return scope.lookup(path, 0)


_COURSE_IN_PATH = re.compile(r"\{\{\s*course\.")
_ERROR_LOG_IN_PATH = re.compile(r"\{\{\s*error_log\.")


def expands_per_course(path: str) -> bool:
    """True if a template path contains ``{{course.`` (rendered once per course)."""
    return bool(_COURSE_IN_PATH.search(path))


def expands_per_error_log(path: str) -> bool:
    """True if a template path contains ``{{error_log.`` (rendered once per course and error-log stream)."""
    return bool(_ERROR_LOG_IN_PATH.search(path))


def find_tags(text: str, roots: Iterable[str] | None = None) -> list[tuple[int, str]]:
    """List ``(line, tag)`` for every tag in ``text`` that the engine would process.

    Used by ``uni-os doctor`` to spot placeholders that were never rendered.
    """
    active = frozenset(roots) if roots is not None else INSTALL_ROOTS
    found = []
    for m in _TAG_RE.finditer(text):
        inner = m.group(1).strip()
        try:
            cls = _classify(inner, active, "", 0)
        except TemplateError:
            cls = ("bad",)
        if cls is None or cls[0] in ("open-pass", "else", "close"):
            continue
        if cls[0] == "var" and inner.startswith("@"):
            continue
        if m.start() > 0 and text[m.start() - 1] == "\\":
            continue
        found.append((text.count("\n", 0, m.start()) + 1, m.group(0)))
    return found


def build_context(
    cfg: dict,
    *,
    enabled: Iterable[str],
    generated: dict | None = None,
) -> dict:
    """The render context: the resolved config, ``modules`` and ``generated``.

    ``modules`` becomes ``{"enabled": [...], "<id>": True, ...}``;
    ``generated`` must contain at least ``date`` and ``version``.
    """
    ctx = dict(cfg)
    enabled = list(enabled)
    mods = dict(cfg.get("modules") or {})
    mods["enabled"] = enabled
    for mid in enabled:
        mods[mid] = True
    ctx["modules"] = mods
    ctx["generated"] = dict(generated or {})
    return ctx
