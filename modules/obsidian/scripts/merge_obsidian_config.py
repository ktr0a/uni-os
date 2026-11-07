#!/usr/bin/env python3
"""Merge Uni OS's recommended Obsidian settings into a vault's .obsidian/ folder, safely.

Uni OS never overwrites your Obsidian configuration at install time. Instead the obsidian module
renders three spec files into <vault>/_agent/obsidian/:

  graph-groups.json   graph colour groups (one per course folder and area) + graph search filter
  bookmarks.json      bookmarks (Home, status, dates, course cards, student model, views)
  app-settings.json   recommended app.json keys, ignore filters, templates folder, core plugins,
                      and the CSS snippet to enable

This script merges them into .obsidian/{graph,bookmarks,app,templates,core-plugins,appearance}.json.

Rules (the same ones the original system followed by hand):
  - Dry run by default: it prints the plan and changes nothing. Pass --apply to write.
  - It only ADDS what is missing. A value you already set differently is reported as "kept"
    and left alone, unless you pass --overwrite.
  - It never removes anything (no bookmark, colour group, ignore filter or plugin is deleted).
  - Before writing, every file it changes is copied to .obsidian/uni-os-backup-<timestamp>/.
  - Writes are atomic (temporary file, then replace), UTF-8 without BOM, 2-space JSON.
  - Close Obsidian before --apply: Obsidian keeps its settings in memory and may write its own
    copy back when it closes. Reopen it afterwards.

Usage:
  python merge_obsidian_config.py --vault "<path to vault>"            # show the plan
  python merge_obsidian_config.py --vault "<path to vault>" --apply    # write it
  options: --overwrite (replace differing values), --only graph,bookmarks,app

Exit codes: 0 = done (or nothing to do), 1 = a file could not be read or written, 2 = bad arguments
or the spec files are missing (run `uni-os init` / `uni-os render` with the obsidian module first).
Standard library only; runs on Windows, macOS and Linux.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

SPEC_DIR = Path("_agent") / "obsidian"
REGEX_SPECIALS = set("\\^$.|?*+()[]{}/")
HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


class Plan:
    """Collects planned changes per target file and messages for the user."""

    def __init__(self) -> None:
        self.files: dict[str, object] = {}     # target name -> new content
        self.originals: dict[str, bool] = {}   # target name -> existed before
        self.lines: list[str] = []
        self.changes = 0
        self.kept = 0
        self.errors = 0

    def add(self, msg: str) -> None:
        self.lines.append(f"  + {msg}")
        self.changes += 1

    def keep(self, msg: str) -> None:
        self.lines.append(f"  ! {msg}")
        self.kept += 1

    def note(self, msg: str) -> None:
        self.lines.append(f"  - {msg}")

    def error(self, msg: str) -> None:
        self.lines.append(f"  x {msg}")
        self.errors += 1


def js_regex_escape(text: str) -> str:
    """Escape a folder name for an Obsidian search regex; spaces become \\s (search splits on spaces)."""
    out = []
    for ch in text:
        if ch in REGEX_SPECIALS:
            out.append("\\" + ch)
        elif ch == " ":
            out.append("\\s")
        else:
            out.append(ch)
    return "".join(out)


def folder_query(folder: str) -> str:
    """Anchored path query: path:/^<folder>\\// (a plain path:me would also match other folders)."""
    return "path:/^" + js_regex_escape(folder.strip("/")) + "\\//"


def hex_to_int(colour: str) -> int:
    m = HEX_RE.match(colour.strip())
    if not m:
        raise ValueError(f"not a #RRGGBB colour: {colour!r}")
    return int(m.group(1), 16)


def load_json(path: Path, default, plan: Plan, label: str):
    if not path.exists():
        return default, False
    try:
        text = path.read_text(encoding="utf-8-sig")
        return (json.loads(text) if text.strip() else default), True
    except (OSError, ValueError) as exc:
        plan.error(f"{label}: cannot read {path} ({exc}); left untouched")
        return None, True


def load_spec(vault: Path, name: str):
    path = vault / SPEC_DIR / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def stage(plan: Plan, name: str, content, existed: bool) -> None:
    plan.files[name] = content
    plan.originals.setdefault(name, existed)


# ---------------------------------------------------------------------------
# graph.json
# ---------------------------------------------------------------------------
def merge_graph(vault: Path, obs: Path, plan: Plan, overwrite: bool) -> None:
    spec = load_spec(vault, "graph-groups.json")
    if spec is None:
        plan.note("graph: no _agent/obsidian/graph-groups.json, skipped")
        return
    graph, existed = load_json(obs / "graph.json", {}, plan, "graph.json")
    if graph is None:
        return
    changed = False
    groups = graph.setdefault("colorGroups", [])
    by_query = {g.get("query"): g for g in groups if isinstance(g, dict)}
    for item in spec.get("groups", []):
        folder = item.get("folder") if isinstance(item, dict) else None
        if not folder:
            continue  # the closing {"end": true} entry
        try:
            rgb = hex_to_int(item.get("colour", ""))
        except ValueError as exc:
            plan.error(f"graph.json: group {folder!r}: {exc}")
            continue
        query = folder_query(folder)
        current = by_query.get(query)
        if current is None:
            new = {"query": query, "color": {"a": 1, "rgb": rgb}}
            groups.append(new)
            by_query[query] = new
            plan.add(f"graph.json: colour group {query} = {item.get('colour')} ({item.get('label', folder)})")
            changed = True
        elif (current.get("color") or {}).get("rgb") != rgb:
            if overwrite:
                current["color"] = {"a": 1, "rgb": rgb}
                plan.add(f"graph.json: colour group {query} recoloured to {item.get('colour')} (--overwrite)")
                changed = True
            else:
                plan.keep(f"graph.json: colour group {query} has another colour; kept (use --overwrite)")
    want_search = spec.get("search", "")
    have_search = graph.get("search", "")
    if want_search and not have_search:
        graph["search"] = want_search
        plan.add(f"graph.json: search filter = {want_search!r}")
        changed = True
    elif want_search and have_search != want_search:
        if overwrite:
            graph["search"] = want_search
            plan.add(f"graph.json: search filter replaced with {want_search!r} (--overwrite)")
            changed = True
        else:
            plan.keep(f"graph.json: search filter is {have_search!r} (recommended {want_search!r}); kept")
    if changed:
        stage(plan, "graph.json", graph, existed)


# ---------------------------------------------------------------------------
# bookmarks.json
# ---------------------------------------------------------------------------
def _bookmarked_paths(items) -> set[str]:
    found: set[str] = set()
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "file" and it.get("path"):
            found.add(it["path"])
        if it.get("type") == "group":
            found |= _bookmarked_paths(it.get("items"))
    return found


def _new_file_item(vault: Path, item: dict, known: set[str], plan: Plan, ctime: int):
    path = item.get("path", "")
    if not path:
        return None
    if path in known:
        return None
    if not (vault / path).exists():
        plan.note(f"bookmarks.json: {path} does not exist in the vault, skipped")
        return None
    new = {"type": "file", "ctime": ctime, "path": path}
    if item.get("title"):
        new["title"] = item["title"]
    known.add(path)
    return new


def merge_bookmarks(vault: Path, obs: Path, plan: Plan, overwrite: bool) -> None:
    spec = load_spec(vault, "bookmarks.json")
    if spec is None:
        plan.note("bookmarks: no _agent/obsidian/bookmarks.json, skipped")
        return
    data, existed = load_json(obs / "bookmarks.json", {"items": []}, plan, "bookmarks.json")
    if data is None:
        return
    items = data.setdefault("items", [])
    known = _bookmarked_paths(items)
    ctime = int(time.time() * 1000)
    changed = False
    for item in spec.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "file":
            new = _new_file_item(vault, item, known, plan, ctime)
            if new:
                items.append(new)
                plan.add(f"bookmarks.json: {new['path']}")
                changed = True
        elif item.get("type") == "group":
            title = item.get("title", "")
            group = next((g for g in items if isinstance(g, dict) and g.get("type") == "group"
                          and g.get("title") == title), None)
            new_items = []
            for sub in item.get("items", []):
                if isinstance(sub, dict) and sub.get("type") == "file":
                    new = _new_file_item(vault, sub, known, plan, ctime)
                    if new:
                        new_items.append(new)
            if not new_items:
                continue
            if group is None:
                items.append({"type": "group", "ctime": ctime, "title": title, "items": new_items})
                plan.add(f"bookmarks.json: group {title!r} with {len(new_items)} item(s)")
            else:
                group.setdefault("items", []).extend(new_items)
                plan.add(f"bookmarks.json: {len(new_items)} item(s) added to existing group {title!r}")
            changed = True
    if changed:
        stage(plan, "bookmarks.json", data, existed)


# ---------------------------------------------------------------------------
# app.json, templates.json, core-plugins.json, appearance.json
# ---------------------------------------------------------------------------
def _merge_keys(target: dict, wanted: dict, label: str, plan: Plan, overwrite: bool) -> bool:
    changed = False
    for key, value in wanted.items():
        if key not in target:
            target[key] = value
            plan.add(f"{label}: {key} = {json.dumps(value)}")
            changed = True
        elif target[key] != value:
            if overwrite:
                plan.add(f"{label}: {key} {json.dumps(target[key])} -> {json.dumps(value)} (--overwrite)")
                target[key] = value
                changed = True
            else:
                plan.keep(f"{label}: {key} is {json.dumps(target[key])} (recommended {json.dumps(value)}); kept")
    return changed


def merge_app(vault: Path, obs: Path, plan: Plan, overwrite: bool) -> None:
    spec = load_spec(vault, "app-settings.json")
    if spec is None:
        plan.note("app: no _agent/obsidian/app-settings.json, skipped")
        return

    app, existed = load_json(obs / "app.json", {}, plan, "app.json")
    if app is not None:
        changed = _merge_keys(app, spec.get("app", {}), "app.json", plan, overwrite)
        filters = app.setdefault("userIgnoreFilters", [])
        for flt in spec.get("ignore_filters", []):
            if flt not in filters:
                filters.append(flt)
                plan.add(f"app.json: ignore filter {flt}")
                changed = True
        if changed:
            stage(plan, "app.json", app, existed)

    tpl, existed = load_json(obs / "templates.json", {}, plan, "templates.json")
    if tpl is not None and spec.get("templates"):
        if _merge_keys(tpl, spec["templates"], "templates.json", plan, overwrite):
            stage(plan, "templates.json", tpl, existed)

    plugins, existed = load_json(obs / "core-plugins.json", {}, plan, "core-plugins.json")
    if plugins is not None:
        changed = False
        for name in spec.get("core_plugins", []):
            if isinstance(plugins, list):  # older Obsidian: list of enabled plugin ids
                if name not in plugins:
                    plugins.append(name)
                    plan.add(f"core-plugins.json: enable {name}")
                    changed = True
            elif plugins.get(name) is True:
                continue
            elif name in plugins and plugins[name] is False and not overwrite:
                plan.keep(f"core-plugins.json: {name} is switched off; kept (Uni OS needs it for "
                          f"{'Home views' if name == 'bases' else 'some features'}; use --overwrite)")
            else:
                plugins[name] = True
                plan.add(f"core-plugins.json: enable {name}")
                changed = True
        if changed:
            stage(plan, "core-plugins.json", plugins, existed)

    snippet = spec.get("css_snippet")
    if snippet:
        if not (obs / "snippets" / f"{snippet}.css").exists():
            plan.note(f"appearance.json: .obsidian/snippets/{snippet}.css not found (render the obsidian module first)")
        look, existed = load_json(obs / "appearance.json", {}, plan, "appearance.json")
        if look is not None:
            enabled = look.setdefault("enabledCssSnippets", [])
            if snippet not in enabled:
                enabled.append(snippet)
                plan.add(f"appearance.json: enable CSS snippet {snippet}")
                stage(plan, "appearance.json", look, existed)


# ---------------------------------------------------------------------------
def write_all(obs: Path, plan: Plan) -> None:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = obs / f"uni-os-backup-{stamp}"
    obs.mkdir(parents=True, exist_ok=True)
    for name, content in plan.files.items():
        target = obs / name
        try:
            if plan.originals.get(name) and target.exists():
                backup.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup / name)
            tmp = target.with_name(target.name + ".uni-os-tmp")
            tmp.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, target)
        except OSError as exc:
            plan.error(f"{name}: write failed ({exc})")
    if backup.exists():
        plan.note(f"backups of the changed files: {backup}")


def utf8_stdio():
    """Print UTF-8 whatever the console or pipe encoding is (a Windows pipe defaults to cp1252,
    which cannot encode many symbols that vault notes contain)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # not a real text stream (tests redirect to StringIO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Merge Uni OS's Obsidian settings into <vault>/.obsidian/ (dry run by default).")
    ap.add_argument("--vault", required=True, help="path to the vault (the folder that contains _agent/)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: only show the plan)")
    ap.add_argument("--overwrite", action="store_true", help="also replace values you set differently")
    ap.add_argument("--only", default="graph,bookmarks,app", help="comma list of: graph, bookmarks, app")
    utf8_stdio()
    args = ap.parse_args(argv)

    vault = Path(args.vault).expanduser()
    if not (vault / SPEC_DIR).is_dir():
        print(f"error: {vault / SPEC_DIR} not found. Install the obsidian module first (uni-os init / enable obsidian).",
              file=sys.stderr)
        return 2
    parts = {p.strip() for p in args.only.split(",") if p.strip()}
    unknown = parts - {"graph", "bookmarks", "app"}
    if unknown:
        print(f"error: unknown --only part(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    obs = vault / ".obsidian"
    plan = Plan()
    try:
        if "graph" in parts:
            merge_graph(vault, obs, plan, args.overwrite)
        if "bookmarks" in parts:
            merge_bookmarks(vault, obs, plan, args.overwrite)
        if "app" in parts:
            merge_app(vault, obs, plan, args.overwrite)
    except ValueError as exc:  # broken spec JSON
        print(f"error: a spec file in {vault / SPEC_DIR} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY RUN (nothing written; add --apply)"
    print(f"Uni OS Obsidian merge: {vault}  [{mode}]")
    for line in plan.lines:
        print(line)
    if args.apply and plan.files:
        before = len(plan.lines)
        write_all(obs, plan)
        for line in plan.lines[before:]:
            print(line)
    print(f"{plan.changes} change(s), {plan.kept} kept as you set them, {plan.errors} error(s).")
    if args.apply and plan.files:
        print("Reopen Obsidian (or reload it) to see the changes.")
    elif plan.files:
        print("Close Obsidian, then run again with --apply.")
    return 1 if plan.errors else 0


if __name__ == "__main__":
    sys.exit(main())
