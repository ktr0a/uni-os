"""Module presets offered during setup (Minimal / Standard / Full + VM).

These lists are the single definition used by ``uni-os init --preset``,
``uni-os modules --preset`` and the setup docs (``setup/presets.md``).

- **Minimal**: the study engine on a plain vault. ``core``, ``student-model``,
  ``courses``, ``error-logs``, ``study-pages``, ``exercise-help``
  (+ ``obsidian`` if you use Obsidian).
- **Standard**: Minimal + the organisation layer and automation that runs on the
  laptop: ``progress``, ``planning``, ``check-in``, ``daily-prep``,
  ``lecture-rundowns``, ``quiz-coaching``, ``roles``, ``scheduler-local``,
  ``heartbeat``, ``notifications``, ``resources``, ``handwritten-notes``
  (+ ``cockpit`` if you use Obsidian).
- **Full**: Standard + ``inbox-sync``, ``experiments``, ``vault-watch``,
  ``course-files-fetch``, ``vm``. ``vault-watch`` and ``course-files-fetch`` are
  Windows-only (experimental); ``vm`` needs an always-on host.

Dependencies (``requires`` in each module.toml) are always added on top.

Presets are resolved for the laptop's operating system: a module whose ``os`` in
module.toml does not include it is left out (``filter_for_os``), and the commands print
what was left out and why. The system is ``runtime.laptop_os`` when the config sets it;
``init --preset`` and ``modules --preset`` fall back to the system of the computer they run
on (``laptop_os_for``). A preset taken from the config (``uni_os.preset`` with an empty
``modules.enabled``) uses only the config's value, so every machine resolves it the same
way. An explicit module list (``--modules``, ``modules.enabled``, ``uni-os enable``) is
never filtered: it only gets a warning.
"""

from __future__ import annotations

import sys

PRESETS = ("minimal", "standard", "full")

MINIMAL = ("core", "student-model", "courses", "error-logs", "study-pages", "exercise-help")
MINIMAL_OBSIDIAN = ("obsidian",)

STANDARD_ADDS = (
    "progress",
    "planning",
    "check-in",
    "daily-prep",
    "lecture-rundowns",
    "quiz-coaching",
    "roles",
    "scheduler-local",
    "heartbeat",
    "notifications",
    "resources",
    "handwritten-notes",
)
STANDARD_OBSIDIAN = ("cockpit",)

FULL_ADDS = ("inbox-sync", "experiments", "vault-watch", "course-files-fetch", "vm")

#: The module catalogue (``modules/README.md``): id -> tier.
CATALOGUE: dict[str, str] = {
    "core": "core",
    "obsidian": "standard",
    "student-model": "core",
    "courses": "core",
    "resources": "standard",
    "handwritten-notes": "standard",
    "progress": "standard",
    "planning": "standard",
    "check-in": "standard",
    "daily-prep": "standard",
    "experiments": "advanced",
    "error-logs": "core",
    "study-pages": "standard",
    "lecture-rundowns": "standard",
    "exercise-help": "standard",
    "quiz-coaching": "standard",
    "roles": "standard",
    "inbox-sync": "advanced",
    "scheduler-local": "standard",
    "heartbeat": "standard",
    "notifications": "standard",
    "vault-watch": "advanced",
    "course-files-fetch": "advanced",
    "vm": "addon",
    "cockpit": "addon",
}

DESCRIPTIONS = {
    "minimal": "study engine on a plain vault: course folders, study pages, hints-only exercise help, error logs",
    "standard": "Minimal + week pages, planning, check-ins, daily prep, quiz coaching, roles, laptop scheduling, heartbeat and pushes",
    "full": "Standard + inbox sync for create-only writers, experiments, Windows watchers/fetchers and the always-on VM",
}


def preset_modules(name: str, *, obsidian: bool = True) -> list[str]:
    """The module ids of a preset (without dependency resolution).

    ``obsidian=False`` drops the Obsidian-only modules (``obsidian``, ``cockpit``).
    """
    name = name.lower()
    if name not in PRESETS:
        raise ValueError(f"unknown preset '{name}' (use one of {', '.join(PRESETS)})")
    ids = list(MINIMAL)
    if obsidian:
        ids += MINIMAL_OBSIDIAN
    if name in ("standard", "full"):
        ids += STANDARD_ADDS
        if obsidian:
            ids += STANDARD_OBSIDIAN
    if name == "full":
        ids += FULL_ADDS
    return ids


OS_NAMES = ("windows", "macos", "linux")


def current_os(platform: str | None = None) -> str | None:
    """The system this Python runs on, as a ``runtime.laptop_os`` value (None = other)."""
    plat = (platform or sys.platform).lower()
    if plat.startswith(("win", "cygwin", "msys")):
        return "windows"
    if plat.startswith("darwin"):
        return "macos"
    if plat.startswith("linux"):
        return "linux"
    return None


def laptop_os_for(raw: dict, *, detect: bool = True) -> tuple[str | None, str]:
    """(os, where it came from) for resolving a preset: ``runtime.laptop_os`` from the
    user's config if set, else (``detect``) the system of this computer."""
    runtime = raw.get("runtime") if isinstance(raw.get("runtime"), dict) else {}
    value = runtime.get("laptop_os") if isinstance(runtime, dict) else None
    if isinstance(value, str) and value in OS_NAMES:
        return value, "runtime.laptop_os"
    if detect:
        found = current_os()
        if found:
            return found, "this computer (runtime.laptop_os is not set)"
    return None, ""


def left_out_note(dropped: list[str], catalog, laptop_os: str | None, source: str) -> list[str]:
    """Printable lines: which preset modules were left out for ``laptop_os`` and why."""
    if not dropped:
        return []
    lines = [f"left out for {laptop_os} (from {source}): {', '.join(dropped)}"]
    for mid in dropped:
        mod = catalog.modules.get(mid) if catalog is not None else None
        why = mod.os_note(laptop_os) if mod is not None else None
        if why:
            lines.append(f"  - {why}")
    lines.append("  add one anyway with --modules or `uni-os enable <id>` (you get a warning; port its laptop "
                 "scripts: docs/porting-to-other-os.md)")
    return lines


def filter_for_os(ids: list[str], catalog, laptop_os: str | None) -> tuple[list[str], list[str]]:
    """Split ids into (supported, dropped) for a laptop OS using the module manifests."""
    if catalog is None or not laptop_os:
        return list(ids), []
    keep, dropped = [], []
    for mid in ids:
        mod = catalog.modules.get(mid)
        if mod is not None and not mod.supports_os(laptop_os):
            dropped.append(mid)
        else:
            keep.append(mid)
    return keep, dropped
