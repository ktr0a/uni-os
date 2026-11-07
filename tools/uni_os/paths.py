"""Filesystem helpers: framework location, vault discovery, safe writes, hashing.

Windows and Linux both work. Vault paths often contain spaces and ``&``
(e.g. ``G:/My Drive/Uni/A&D``); everything here uses ``pathlib`` and never a shell,
so no quoting is needed inside Python. Paths stored in files (the manifest) are
vault-relative POSIX strings (forward slashes) so they are identical on every OS.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path, PurePosixPath

from .errors import UniOsError

#: ``<repo>/tools/uni_os/paths.py`` -> ``<repo>``
FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = FRAMEWORK_ROOT / "tools"
DEFAULT_MODULES_DIR = FRAMEWORK_ROOT / "modules"

DEFAULT_AGENT_DIR = "_agent"
CONFIG_NAME = "uni-os.toml"
JSON_NAME = "uni-os.json"
MANIFEST_NAME = ".uni-os-manifest.json"

#: Environment variables understood by the tools.
ENV_VAULT = "UNI_OS_VAULT"
ENV_MODULES_DIR = "UNI_OS_MODULES_DIR"

_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
_BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def expand(path: str | os.PathLike) -> Path:
    """Expand ``~`` and environment variables; does not resolve symlinks."""
    return Path(os.path.expandvars(os.path.expanduser(str(path))))


def modules_dir(explicit: str | os.PathLike | None = None) -> Path:
    """The module catalogue folder: explicit argument, ``$UNI_OS_MODULES_DIR`` or ``<repo>/modules``."""
    if explicit:
        return expand(explicit)
    env = os.environ.get(ENV_MODULES_DIR)
    if env:
        return expand(env)
    return DEFAULT_MODULES_DIR


def config_in_vault(vault: Path, agent_dir: str | None = None) -> Path | None:
    """Find ``<vault>/<agent_dir>/uni-os.toml``.

    Looks in ``_agent/`` (or the given agent dir) first, then in any first-level
    folder of the vault (so a custom ``paths.agent_dir`` still works).
    """
    vault = Path(vault)
    candidates = [vault / (agent_dir or DEFAULT_AGENT_DIR) / CONFIG_NAME]
    for cand in candidates:
        if cand.is_file():
            return cand
    try:
        for child in sorted(vault.iterdir()):
            if child.is_dir() and (child / CONFIG_NAME).is_file():
                return child / CONFIG_NAME
    except OSError:
        pass
    return None


def find_vault(explicit: str | os.PathLike | None = None, start: str | os.PathLike | None = None) -> Path | None:
    """Locate the vault.

    Order: explicit path, ``$UNI_OS_VAULT``, then walk up from ``start`` (default:
    the current directory) looking for ``_agent/uni-os.toml``. Returns ``None``
    if nothing is found.
    """
    if explicit:
        return expand(explicit)
    env = os.environ.get(ENV_VAULT)
    if env:
        return expand(env)
    here = Path(start or os.getcwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / DEFAULT_AGENT_DIR / CONFIG_NAME).is_file():
            return folder
    return None


def is_within(child: Path, parent: Path) -> bool:
    """True if ``child`` is ``parent`` or inside it (after resolving)."""
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def check_name(segment: str) -> str | None:
    """Return a problem description if ``segment`` is not a portable file/folder name."""
    if not segment or not segment.strip():
        return "empty name"
    if segment in (".", ".."):
        return f"'{segment}' is not allowed"
    if _BAD_NAME_CHARS.search(segment):
        return 'contains a character that is not allowed in file names (< > : " / \\ | ? *)'
    if segment != segment.strip():
        return "starts or ends with a space"
    if segment.endswith("."):
        return "ends with a dot (not allowed on Windows)"
    if segment.split(".")[0].upper() in _WINDOWS_RESERVED:
        return f"'{segment}' is a reserved name on Windows"
    return None


def check_relpath(rel: str) -> str | None:
    """Problem description if ``rel`` is not a safe vault-relative POSIX path."""
    if not rel:
        return "empty path"
    if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or rel.startswith("\\"):
        return "must be relative to the vault"
    for seg in rel.split("/"):
        problem = check_name(seg)
        if problem:
            return f"segment '{seg}': {problem}"
    return None


def posix(rel: str | os.PathLike) -> str:
    """Normalise a relative path to POSIX form (forward slashes, no ``./``)."""
    text = str(rel).replace("\\", "/")
    parts = [p for p in PurePosixPath(text).parts if p not in ("", ".")]
    return "/".join(parts)


def vault_file(vault: Path, rel: str) -> Path:
    """Join a vault-relative POSIX path onto the vault, refusing escapes."""
    problem = check_relpath(rel)
    if problem:
        raise UniOsError(f"unsafe vault path '{rel}': {problem}")
    return Path(vault).joinpath(*rel.split("/"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    """SHA-256 of a file, or ``None`` if it cannot be read."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temporary file + rename.

    Synced folders (Google Drive, OneDrive) then never see a half-written file.
    Parent folders are created.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".uni-os-tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_text(path: Path, text: str) -> None:
    """UTF-8 text write (atomic), keeping ``\\n`` line endings as given."""
    atomic_write(path, text.encode("utf-8"))


def read_text(path: Path) -> str:
    """Read a UTF-8 text file (BOM tolerated)."""
    return Path(path).read_text(encoding="utf-8-sig")


def display(path: Path) -> str:
    """A short human-readable form: relative to the framework if inside it, else absolute (POSIX)."""
    p = Path(path)
    try:
        return p.resolve().relative_to(FRAMEWORK_ROOT).as_posix()
    except (ValueError, OSError):
        return p.as_posix()
