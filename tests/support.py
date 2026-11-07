"""Shared helpers for the tools tests (``python -m unittest discover -s tests``).

Importing this module puts ``tools/`` on ``sys.path`` so tests can ``import uni_os``.
The tools tests use the small fixture module set in ``tests/fixtures/modules`` and
write only into temporary folders. Only ``test_repo.py`` reads the real ``modules/``,
``config/`` and ``examples/alex.toml`` (read-only) to catch drift and template errors.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
TOOLS = REPO / "tools"
FIXTURES = TESTS / "fixtures"
FIXTURE_MODULES = FIXTURES / "modules"
FIXTURE_CONFIG = FIXTURES / "config" / "alex-mini.toml"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

#: Environment variables that would leak the developer's setup into tests.
_ISOLATE = ("UNI_OS_VAULT", "UNI_OS_MODULES_DIR", "UNI_OS_TODAY", "SOURCE_DATE_EPOCH", "UNI_OS_STATE")


def fixture_config_text(topic_file: Path) -> str:
    """The fixture config with the ntfy topic file pointed at ``topic_file``."""
    text = FIXTURE_CONFIG.read_text(encoding="utf-8")
    return text.replace("@TOPIC_FILE@", topic_file.as_posix())


def run_cli(*argv: str) -> tuple[int, str, str]:
    """Run ``uni_os.cli.main`` in-process; returns ``(exit_code, stdout, stderr)``."""
    from uni_os import cli

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:  # argparse errors / --help
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TempDirTestCase(unittest.TestCase):
    """A test case with ``self.tmp`` (fresh folder) and an isolated environment.

    ``self.config`` is a copy of the fixture config whose ntfy topic file lives in
    ``self.tmp / "secret"`` (outside the vault), and ``self.vault`` is
    ``self.tmp / "vault"`` (not created).
    """

    today = "2026-11-07"

    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="uni-os-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = {k: v for k, v in os.environ.items() if k not in _ISOLATE}
        env["UNI_OS_TODAY"] = self.today
        env["UNI_OS_STATE"] = str(self.tmp / "state")
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.tmp / "secret").mkdir()
        self.topic_file = self.tmp / "secret" / "ntfy-topic"
        self.config = self.tmp / "alex.toml"
        self.config.write_text(fixture_config_text(self.topic_file), encoding="utf-8")
        self.vault = self.tmp / "vault"

    # helpers -------------------------------------------------------------------

    def cli(self, *argv: str, expect: int | None = 0) -> tuple[int, str, str]:
        code, out, err = run_cli(*argv)
        if expect is not None:
            self.assertEqual(code, expect, f"uni-os {' '.join(argv)} -> {code}\nstdout:\n{out}\nstderr:\n{err}")
        return code, out, err

    def init(self, *extra: str, expect: int | None = 0) -> tuple[int, str, str]:
        return self.cli(
            "init", "--config", str(self.config), "--vault", str(self.vault),
            "--modules-dir", str(FIXTURE_MODULES), *extra, expect=expect,
        )

    def in_vault(self, *argv: str, expect: int | None = 0) -> tuple[int, str, str]:
        return self.cli(*argv, "--vault", str(self.vault), "--modules-dir", str(FIXTURE_MODULES), expect=expect)

    def read(self, rel: str) -> str:
        return (self.vault / rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
