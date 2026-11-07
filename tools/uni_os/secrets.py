"""Secret detection for ``uni-os doctor`` and config validation.

The vault syncs to every device and every agent session can read it, so it must
never contain API keys, tokens, private calendar (iCal) addresses or the ntfy
topic (anyone who knows the topic can read and send your pushes). This module
finds such strings so they can be removed.

Findings are always *redacted* when printed: only the first characters and the
length are shown, never the secret itself.

To silence a deliberate false positive (e.g. a documented fake key), put
``uni-os: allow-secret`` on the same line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

ALLOW_MARKER = "uni-os: allow-secret"

#: Substrings that mark an obvious placeholder (not a real secret).
_PLACEHOLDER_HINTS = ("example", "xxxx", "your-", "your_", "<", "...", "changeme", "placeholder", "dummy")

#: ntfy.sh paths that are not topics.
_NTFY_NON_TOPICS = {"app", "docs", "account", "signup", "login", "pricing", "static", "v1", "_matrix", "about", "subscribe"}


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern
    level: str  # error | warning
    description: str


@dataclass(frozen=True)
class Hit:
    pattern: str
    description: str
    level: str
    line: int
    redacted: str


def _p(name: str, regex: str, description: str, level: str = "error", flags: int = 0) -> Pattern:
    return Pattern(name, re.compile(regex, flags), level, description)


PATTERNS: list[Pattern] = [
    _p("anthropic-key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}", "Anthropic API key"),
    _p("openai-key", r"\bsk-(?!ant-)(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}", "OpenAI-style API key"),
    _p("google-api-key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "Google API key"),
    _p("google-oauth-secret", r"\bGOCSPX-[A-Za-z0-9_\-]{20,}", "Google OAuth client secret"),
    _p("github-token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})", "GitHub token"),
    _p("gitlab-token", r"\bglpat-[A-Za-z0-9_\-]{20,}", "GitLab token"),
    _p("slack-token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}", "Slack token"),
    _p("aws-access-key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "AWS access key id"),
    _p("stripe-live-key", r"\b[sr]k_live_[0-9A-Za-z]{20,}", "Stripe live key"),
    _p("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    _p("jwt", r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", "JSON web token"),
    _p(
        "ical-google-private",
        r"calendar\.google\.com/calendar/ical/[^\s/]+/private-[0-9a-fA-F]{16,}",
        "private Google Calendar iCal address (anyone with it can read the calendar)",
    ),
    _p(
        "ical-private",
        r"(?:https?|webcal)://[^\s\"'<>]*/private-[0-9a-fA-F]{16,}[^\s\"'<>]*",
        "private calendar feed address",
    ),
    _p(
        "ical-outlook",
        r"outlook\.(?:office365|live|office)\.com/owa/calendar/[^\s\"'<>]+\.ics",
        "published Outlook calendar address",
    ),
    _p(
        "ical-icloud",
        r"p\d+-caldav\.icloud\.com/published/\d/[A-Za-z0-9_\-]{20,}",
        "published iCloud calendar address",
    ),
    _p("ntfy-topic-url", r"\bntfy\.sh/([A-Za-z0-9_\-]{3,})", "ntfy topic (anyone who knows it can read your pushes)"),
    _p(
        "bearer-token",
        r"(?i)\bauthorization:\s*bearer\s+[A-Za-z0-9_\-\.=]{16,}",
        "bearer token in an Authorization header",
    ),
    _p(
        "secret-assignment",
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|secret[_-]?key|password|passwd|token)\b"
        r"\s*[:=]\s*[\"']?([A-Za-z0-9_\-/+=.]{20,})",
        "value assigned to a key/token/password name",
        level="warning",
    ),
]


def redact(secret: str) -> str:
    """Show only a short prefix and the length."""
    secret = secret.strip()
    prefix = secret[:6] if len(secret) > 12 else secret[:2]
    return f"{prefix}... ({len(secret)} chars)"


def _looks_placeholder(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in _PLACEHOLDER_HINTS)


def scan_text(
    text: str,
    *,
    literals: Iterable[tuple[str, str]] = (),
    extra_patterns: Iterable[Pattern] = (),
) -> list[Hit]:
    """Scan ``text`` line by line.

    ``literals`` are ``(name, exact_string)`` pairs that must never appear (for
    example the real ntfy topic read from its secret file). Their hits are
    reported by name only.
    """
    hits: list[Hit] = []
    patterns = list(PATTERNS) + list(extra_patterns)
    lits = [(n, s) for n, s in literals if s and len(s) >= 4]
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        seen_spans: list[tuple[int, int]] = []
        for pat in patterns:
            for m in pat.regex.finditer(line):
                matched = m.group(0)
                if pat.name == "ntfy-topic-url" and m.group(1).lower() in _NTFY_NON_TOPICS:
                    continue
                if pat.name == "secret-assignment":
                    value = m.group(1)
                    if value.startswith(("~", "/", "./", "$")) or "/" in value or _looks_placeholder(value):
                        continue
                if _looks_placeholder(matched):
                    continue
                span = m.span()
                if any(span[0] < e and s < span[1] for s, e in seen_spans):
                    continue  # overlaps a finding already reported on this line
                seen_spans.append(span)
                hits.append(Hit(pat.name, pat.description, pat.level, lineno, redact(matched)))
        for name, literal in lits:
            if literal in line:
                hits.append(Hit("literal", name, "error", lineno, "(value hidden)"))
    return hits


def scan_value(value: str) -> list[Hit]:
    """Scan a single config value (no line structure)."""
    return scan_text(value)
