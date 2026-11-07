"""Exception types and the ``Issue`` record shared by all uni-os components.

Every error meant for the user is a ``UniOsError`` (or subclass). The CLI prints
its message (and hint, if any) and exits with ``exit_code`` instead of showing a
traceback.
"""

from __future__ import annotations

from dataclasses import dataclass


class UniOsError(Exception):
    """An error with a user-facing message."""

    exit_code = 1

    def __init__(self, message: str, *, hint: str | None = None, exit_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        if exit_code is not None:
            self.exit_code = exit_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ConfigError(UniOsError):
    """The config file is missing, unreadable or invalid."""


class ModuleError(UniOsError):
    """A module is unknown, has a broken module.toml, or dependencies cannot be resolved."""


class TemplateError(UniOsError):
    """A template could not be rendered (bad syntax or a missing config key).

    ``filename`` and ``line`` point at the template; ``key`` is the config key
    involved (if any).
    """

    def __init__(
        self,
        message: str,
        *,
        filename: str | None = None,
        line: int | None = None,
        key: str | None = None,
        hint: str | None = None,
    ):
        super().__init__(message, hint=hint)
        self.filename = filename
        self.line = line
        self.key = key

    def located(self, filename: str | None = None, line: int | None = None) -> "TemplateError":
        """Fill in the location if it is not known yet; returns ``self``."""
        if self.filename is None and filename is not None:
            self.filename = filename
        if self.line is None and line is not None:
            self.line = line
        return self

    def __str__(self) -> str:
        where = ""
        if self.filename:
            where = self.filename
            if self.line:
                where += f":{self.line}"
            where += ": "
        text = where + self.message
        if self.hint:
            text += f" ({self.hint})"
        return text


LEVELS = ("error", "warning", "info")


@dataclass(frozen=True)
class Issue:
    """One validation or doctor finding.

    ``level`` is ``error`` (must fix), ``warning`` (should fix) or ``info``.
    ``where`` is a config key, a file path or a section name.
    """

    level: str
    where: str
    message: str

    def __str__(self) -> str:
        if self.where:
            return f"{self.level}: {self.where}: {self.message}"
        return f"{self.level}: {self.message}"

    @property
    def is_error(self) -> bool:
        return self.level == "error"


def errors_of(issues) -> list[Issue]:
    """Only the error-level issues."""
    return [i for i in issues if i.level == "error"]


def warnings_of(issues) -> list[Issue]:
    """Only the warning-level issues."""
    return [i for i in issues if i.level == "warning"]
