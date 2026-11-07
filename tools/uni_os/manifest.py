"""The install manifest: ``<vault>/_agent/.uni-os-manifest.json``.

It records every file ``uni-os`` wrote: the module it belongs to, the template it
came from and the SHA-256 of the bytes written. Comparing that hash with the file
on disk tells the tools whether *you* (or an agent) edited the file since:

- ``unmodified``: safe to re-render (``uni-os render`` updates it);
- ``modified``: yours now; never overwritten without ``--force``;
- ``missing``: deleted; ``uni-os init`` restores it, ``render`` does not.

Generated regions (``<!-- uni-os:begin NAME -->`` ... ``<!-- uni-os:end NAME -->``,
see :mod:`uni_os.regions`) in an edited file are still refreshed by ``render``. Such a
region merge does **not** change the entry's ``sha256``: that stays the hash of the
last full rendering, so the file keeps counting as edited (it is: your text outside
the regions is still there) and the next render merges again instead of overwriting
it. The entry gains ``merged_sha256``, the hash of the file right after the merge, so
``doctor`` can tell "edited, regions refreshed by render" from later edits. When a
merge makes the file equal to a full rendering (you had only touched the regions),
the entry is recorded like a normal write and the file is untouched again.

Folders (``.gitkeep`` markers and module ``[[folders]]``) are recorded under
``dirs`` with the module that asked for them. They are never deleted.

Paths are vault-relative POSIX strings. The file holds no absolute paths and no
personal data, so it is safe in a public example vault.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__, paths
from .errors import UniOsError

SCHEMA = 1
NOTE = "do not edit; maintained by uni-os (what it installed, to detect your edits)"


@dataclass
class Manifest:
    path: Path
    files: dict[str, dict] = field(default_factory=dict)
    dirs: dict[str, str] = field(default_factory=dict)
    modules: dict[str, dict] = field(default_factory=dict)
    updated: str = ""
    exists: bool = False

    @classmethod
    def load(cls, vault: Path, agent_dir: str = paths.DEFAULT_AGENT_DIR) -> "Manifest":
        path = Path(vault) / agent_dir / paths.MANIFEST_NAME
        if not path.is_file():
            return cls(path=path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise UniOsError(
                f"cannot read the manifest {path}: {exc}",
                hint="if it is corrupted, rename it; `uni-os init` will then treat existing files as not installed by uni-os",
            ) from None
        return cls(
            path=path,
            files=dict(data.get("files", {})),
            dirs=dict(data.get("dirs", {})),
            modules=dict(data.get("modules", {})),
            updated=data.get("updated", ""),
            exists=True,
        )

    # -- queries -----------------------------------------------------------------

    def status(self, vault: Path, rel: str) -> str:
        """``untracked``, ``missing``, ``unmodified`` or ``modified``."""
        entry = self.files.get(rel)
        if entry is None:
            return "untracked"
        target = Path(vault).joinpath(*rel.split("/"))
        if not target.is_file():
            return "missing"
        return "unmodified" if paths.sha256_file(target) == entry.get("sha256") else "modified"

    def files_of(self, module: str) -> list[str]:
        return sorted(rel for rel, e in self.files.items() if e.get("module") == module)

    # -- updates -----------------------------------------------------------------

    def record(self, rel: str, *, module: str, source: str, sha256: str, verbatim: bool = False) -> None:
        entry = {"module": module, "source": source, "sha256": sha256}
        if verbatim:
            entry["verbatim"] = True
        self.files[rel] = entry

    def note_merge(self, rel: str, sha256: str) -> None:
        """Remember the hash after a region merge (the baseline ``sha256`` is kept)."""
        entry = self.files.get(rel)
        if entry is not None:
            entry["merged_sha256"] = sha256

    def record_dir(self, rel: str, module: str) -> None:
        self.dirs.setdefault(rel, module)

    def set_module(self, mid: str, status: str, date: str) -> None:
        entry = self.modules.get(mid, {})
        if entry.get("status") != status:
            entry = {"status": status, "since": date}
        self.modules[mid] = entry

    def to_json(self) -> str:
        data = {
            "_generated": NOTE,
            "schema": SCHEMA,
            "framework_version": __version__,
            "updated": self.updated,
            "modules": {k: self.modules[k] for k in sorted(self.modules)},
            "dirs": {k: self.dirs[k] for k in sorted(self.dirs)},
            "files": {k: self.files[k] for k in sorted(self.files)},
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def save(self, date: str) -> None:
        self.updated = date
        paths.write_text(self.path, self.to_json())
        self.exists = True
