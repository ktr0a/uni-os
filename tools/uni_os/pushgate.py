"""Push gate: the one gate every phone push of Uni OS goes through (stdlib only).

Ported from the original system's `push-gate` (one budget file shared by every sender:
the heartbeat's judgment pushes and the deterministic outcome checks) and its
`notify` helper (ntfy via HTTP, pushes held during quiet windows and released later).

Rules, in this order (the first one that applies decides):

  13 refused   no problem id (a push is always about a flagged problem: never an
               "all good"), an empty text, an "all good" text, or personal details
               (a mail address, a link in the text: use --click, a long digit run)
  12 dedupe    every id was pushed in the last `dedupe_hours`; nothing left to say
  10 held      quiet hours or a quiet window (e.g. a graded fixture): not sent and
               not recorded ("deferred" in the original): the sender sends it again
               later if it is still true (the heartbeat keeps it as a flag, the
               outcome checks find it again on their next run). Nothing stale is
               ever released after the quiet time.
  11 budget    `max_per_day` pushes a day across all senders, `min_gap_hours` apart
               (--urgent skips the gap, never the day cap): not sent; keep it as a flag
   0 sent      (also: "would send" in a dry run; "logged only" with provider "none")
   1 failed    the HTTP request to the push server failed, or the gate was busy ("gate
               busy, try later": another sender held the gate's lock for over
               LOCK_WAIT_S seconds); nothing sent by this call, nothing recorded
   2 error     usage or setup error (no topic file, topic file inside the vault, ...)

Direct pushes (--direct: host health alerts, job failures) skip the id rule, the "all
good" rule, dedupe, quiet hours and the budget, and never count against it; the
personal-details refusal still applies (the lock screen is public). Inside a hard quiet
window (nobody wants a buzz in the middle of a timed quiz) a direct push is QUEUED, and
`uni-os push --flush` (run by the outcome checks and the host's health check) releases
the queue as one combined push once the window is over, as the original's notify
helper did ("Held during the timed task: a; b").

Quiet windows (notify.quiet_windows) come in two strengths. A HARD window (the default)
holds every push, --urgent ones too, and the heartbeat's pre-check skips its runs (it still
logs each skip): meant for a short graded fixture such as a two-hour timed quiz. A SOFT
window (urgent_ok = true) holds ordinary pushes only: --urgent and --direct pushes pass and
the heartbeat keeps running: meant for long periods such as the exam session. `uni-os
config validate` / `doctor` warn about a hard dated window longer than a day.

State lives OUTSIDE the vault, per user and machine:
  Linux/macOS  $XDG_STATE_HOME/uni-os/push-gate/  (default ~/.local/state/uni-os/push-gate/)
  Windows      %LOCALAPPDATA%/uni-os/push-gate/
  overrides    UNI_OS_PUSH_STATE (this folder) or UNI_OS_STATE / UNI_STATE_DIR (the uni-os state root)
Files: state.json (pushes, ids, held queue; pruned to 14 days), notify.log (every
attempt), notify-settings.json (last known [notify] settings, so pushes still work when
the vault is unreachable, e.g. during a Drive outage, or its config can't be used: invalid
TOML or an invalid [notify] value; then one stderr line says so and, without a cache, the
code's own defaults apply), .lock (held while a call reads, decides, sends and records:
a call that can't get it within LOCK_WAIT_S, longer than one send, exits 1 "gate busy"
and never sends without it).

Dry runs (--dry-run, or UNI_DRY_RUN=1 set by the job runner) write nothing and print the
decision. UNI_OS_PUSH_DRY_LOG=<file> additionally appends each dry decision to that file
(switch-on guards read it). UNI_OS_PUSH_FAKE_SEND=<file> appends the push to that file
instead of sending it, but records it as sent (tests). UNI_OS_NOW="YYYY-MM-DD HH:MM"
fixes "now" (tests, simulated runs).
"""
from __future__ import annotations

import base64
import contextlib
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:  # stdlib, but the IANA database may be missing on a bare Windows Python
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    import tomllib
except ImportError:  # pragma: no cover  (Python < 3.11)
    tomllib = None  # type: ignore

# ---- exit codes -------------------------------------------------------------------------
SENT, FAILED, ERROR, HELD, BUDGET, DEDUPE, REFUSED = 0, 1, 2, 10, 11, 12, 13
CODE_NAMES = {SENT: "sent", FAILED: "failed", ERROR: "error", HELD: "held", BUDGET: "budget",
              DEDUPE: "dedupe", REFUSED: "refused"}

# ---- timing -----------------------------------------------------------------------------
HTTP_TIMEOUT_S = 20                    # deliver(): the timeout of one ntfy request
LOCK_WAIT_S = 2 * HTTP_TIMEOUT_S + 5   # file_lock(): longer than the lock holder's slowest send


class GateBusy(RuntimeError):
    """Another sender held the gate's lock for longer than LOCK_WAIT_S: nothing was sent."""


class ConfigUnreadable(ValueError):
    """The vault config exists but can't be read or parsed (invalid TOML, a read error)."""

# ---- defaults (must equal modules/notifications/module.toml [defaults.notify]) ----------
DEFAULTS = {
    "provider": "ntfy",
    "ntfy_server": "https://ntfy.sh",
    "ntfy_topic_file": "~/.config/uni-os/ntfy-topic",
    "title": "Uni OS",
    "default_click": "",
    "max_per_day": 3,
    "min_gap_hours": 2,
    "dedupe_hours": 24,
    "quiet_hours": "21:00-07:30",
    "quiet_windows": [],
    "never_all_good": True,
    "require_id": True,
    "block_personal": True,
    "extra_all_good_patterns": [],
    "max_length": 300,
    "hold_max_hours": 24,
    "direct_priority": 4,
}

# The original's regex, plus a few English variants. Other languages: notify.extra_all_good_patterns.
ALL_GOOD = re.compile(
    r"\b(all (good|fine|ok|okay|clear|green)|nothing (to report|new|flagged|wrong|to flag)|"
    r"everything('s| is)? (ok|okay|fine|good|on track|in order)|no (problems|issues)( found)?)\b", re.I)
PERSONAL = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "a mail address"),
    (re.compile(r"https?://|www\.", re.I), "a link (pass it with --click instead)"),
    (re.compile(r"\+\d[\d ]{8,}\d|\b\d{7,}\b"), "a long number (phone, matriculation or account id)"),
]
NO_PERSONAL_REMINDER = ("No personal details in pushes: no names of people, mail addresses, links "
                        "(use --click), phone or id numbers, grades beyond a plain score, file names or contents. "
                        "The lock screen is public.")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---- small helpers -----------------------------------------------------------------------
def deep_get(cfg, dotted, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def as_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [v]


def hm_to_min(s):
    s = str(s).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    if not m:
        raise ValueError("not a HH:MM time: %r" % s)
    return int(m[1]) * 60 + int(m[2])


def one_line(text):
    return " ".join(str(text or "").split())


# ---- time (wall-clock in the term's time zone, naive datetimes internally) ------------
def get_zone(tz):
    if not tz or ZoneInfo is None:
        return None
    try:
        return ZoneInfo(tz)
    except Exception:  # ZoneInfoNotFoundError (no tzdata) or a bad name
        return None


def parse_when(s):
    """'YYYY-MM-DD HH:MM', ISO with or without offset, 'YYYY-MM-DD' -> datetime (aware or naive)."""
    if s is None or s == "":
        return None
    if isinstance(s, dt.datetime):
        return s
    if isinstance(s, dt.date):
        return dt.datetime(s.year, s.month, s.day)
    s = str(s).strip()
    try:
        return dt.datetime.fromisoformat(s.replace(" ", "T", 1) if re.match(r"^\d{4}-\d{2}-\d{2} \d", s) else s)
    except ValueError:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})", s)
        if m:
            return dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))
        return None


def to_local(d, tz=None):
    """Aware -> naive wall-clock time in tz (or the system zone); naive stays as it is."""
    if d is None:
        return None
    if d.tzinfo is None:
        return d
    z = get_zone(tz)
    return (d.astimezone(z) if z else d.astimezone()).replace(tzinfo=None)


def iso(d, tz=None):
    """Naive wall-clock -> ISO string with the zone's offset (system offset as a fallback)."""
    if d is None:
        return None
    if d.tzinfo is None:
        z = get_zone(tz)
        d = d.replace(tzinfo=z) if z else d.astimezone()
    return d.isoformat(timespec="seconds")


def now_local(tz=None, override=None):
    s = override or os.environ.get("UNI_OS_NOW")
    if s:
        d = parse_when(s)
        if d is None:
            raise ValueError('--now must look like "YYYY-MM-DD HH:MM", got %r' % s)
        return to_local(d, tz).replace(second=0, microsecond=0)
    z = get_zone(tz)
    d = dt.datetime.now(z) if z else dt.datetime.now().astimezone()
    return d.replace(tzinfo=None, microsecond=0)


def fmt_day(d):
    return "%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b"))


# ---- vault and config discovery (shared with the heartbeat command) -------------------
def find_vault(arg=None):
    # UNI_VAULT is exported by both job runners (laptop scheduler and always-on host)
    for cand in (arg, os.environ.get("UNI_OS_VAULT"), os.environ.get("UNI_VAULT")):
        if cand:
            return Path(cand).expanduser()
    here = Path.cwd()
    for d in [here, *here.parents]:
        for agent_dir in ("_agent",):
            if (d / agent_dir / "uni-os.toml").is_file():
                return d
    return None


def load_config(vault, config_path=None, modules_dir=None):
    """The config as a dict ({} when there is none). Uses the shared loader
    `uni_os.config.load` (module defaults merged in) when it exists, else reads
    <vault>/_agent/uni-os.toml (or `config_path`) as it is; the code's own defaults
    cover every key this module needs either way. A config file that exists but is not
    valid TOML (or can't be read) raises ConfigUnreadable, a ValueError naming the file."""
    if vault is None and not config_path:
        return {}
    loader = None
    try:
        from uni_os import config as shared  # the framework's loader
        loader = getattr(shared, "load", None)
    except ImportError:
        loader = None
    if loader is not None:
        try:
            kw = {}
            if config_path:
                kw["config_path"] = str(config_path)
            if modules_dir:
                kw["modules_dir"] = str(modules_dir)
            cfg = loader(str(vault) if vault is not None else None, **kw)
            return dict(cfg) if cfg else {}
        except Exception:  # noqa: BLE001  a strict loader must not stop pushes or the pre-check
            pass
    path = Path(config_path) if config_path else Path(vault) / "_agent" / "uni-os.toml"
    if not path.is_file() or tomllib is None:
        return {}
    shown = "_agent/uni-os.toml" if not config_path else path.name
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigUnreadable("the config %s is not valid TOML: %s" % (shown, one_line(e))) from None
    except OSError as e:
        raise ConfigUnreadable("cannot read the config %s: %s" % (shown, one_line(e.strerror or e))) from None


def state_root():
    """The per-user uni-os state folder (shared with the job runners, which export it as
    UNI_STATE_DIR): outside the vault, never synced."""
    for var in ("UNI_OS_STATE", "UNI_STATE_DIR"):
        if os.environ.get(var):
            return Path(os.environ[var]).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return Path(base) / "uni-os"
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "uni-os"


def gate_state_dir():
    if os.environ.get("UNI_OS_PUSH_STATE"):
        return Path(os.environ["UNI_OS_PUSH_STATE"]).expanduser()
    return state_root() / "push-gate"


def is_dry(flag=False):
    return bool(flag) or os.environ.get("UNI_DRY_RUN") == "1"


@contextlib.contextmanager
def file_lock(path, wait=None):
    """Exclusive lock on a lock file (fcntl on POSIX, msvcrt on Windows). Retries for up to
    `wait` seconds (default LOCK_WAIT_S, longer than one send by the lock holder), then
    raises GateBusy: the body never runs without the lock, so no push goes out twice."""
    import time
    wait = LOCK_WAIT_S if wait is None else float(wait)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+")
    locked = False
    try:
        deadline = time.monotonic() + wait
        while not locked:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise GateBusy("another sender has held the push gate's lock for over %g s" % wait) from None
                time.sleep(0.1)
        yield
    finally:
        try:
            if locked and os.name == "nt":
                import msvcrt
                f.seek(0)
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        finally:
            f.close()


# ---- settings ------------------------------------------------------------------------------
class Settings:
    """The [notify] table merged over DEFAULTS, plus the time zone and the vault path."""

    def __init__(self, notify=None, tz=None, vault=None):
        n = dict(DEFAULTS)
        n.update({k: v for k, v in (notify or {}).items() if v is not None})
        if os.environ.get("UNI_OS_NTFY_SERVER"):
            n["ntfy_server"] = os.environ["UNI_OS_NTFY_SERVER"]
        if os.environ.get("UNI_OS_NTFY_TOPIC_FILE"):
            n["ntfy_topic_file"] = os.environ["UNI_OS_NTFY_TOPIC_FILE"]
        self.raw = n
        self.tz = tz
        self.vault = Path(vault) if vault else None
        self.provider = str(n["provider"] or "none").lower()
        self.server = str(n["ntfy_server"] or DEFAULTS["ntfy_server"]).rstrip("/")
        self.topic_file = str(n["ntfy_topic_file"] or "")
        self.title = str(n["title"] or "Uni OS")
        self.default_click = str(n["default_click"] or "")
        self.max_per_day = int(n["max_per_day"])
        self.min_gap_min = float(n["min_gap_hours"]) * 60
        self.dedupe_h = float(n["dedupe_hours"])
        self.quiet_hours = self._parse_quiet_hours(n["quiet_hours"])
        self.quiet_windows = list(n["quiet_windows"] or [])
        self.never_all_good = bool(n["never_all_good"])
        self.require_id = bool(n["require_id"])
        self.block_personal = bool(n["block_personal"])
        self.extra_all_good = [re.compile(p, re.I) for p in as_list(n["extra_all_good_patterns"])]
        self.max_length = int(n["max_length"])
        self.hold_max_h = float(n["hold_max_hours"])
        self.direct_priority = int(n["direct_priority"])

    @staticmethod
    def _parse_quiet_hours(v):
        if not v:
            return None
        m = re.match(r"^\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*$", str(v))
        if not m:
            raise ValueError('notify.quiet_hours must look like "21:00-07:30", got %r' % v)
        return hm_to_min(m[1]), hm_to_min(m[2]), "%s-%s" % (m[1], m[2])

    @classmethod
    def from_config(cls, cfg, vault=None):
        return cls(deep_get(cfg, "notify", {}) or {}, deep_get(cfg, "term.timezone"), vault)

    def public(self):
        """What may be cached outside the vault (no secrets are in here anyway)."""
        return {k: (v if not isinstance(v, (dt.date, dt.datetime, dt.time)) else str(v))
                for k, v in self.raw.items()}


def cached_settings(vault=None):
    """(Settings, where from): the last known settings (notify-settings.json), else the code's
    own defaults. Never raises: a push must not stop because a cache or a config is broken."""
    try:
        data = json.loads((gate_state_dir() / "notify-settings.json").read_text(encoding="utf-8"))
        return Settings(data.get("notify"), data.get("timezone"), vault), "the last known notify settings"
    except Exception:  # noqa: BLE001  missing, unreadable or invalid cache
        return Settings({}, None, vault), "the default notify settings"


def settings_for(vault_arg=None, config_path=None, modules_dir=None):
    """Settings from the vault config; if the vault is unreachable, the last cached ones.
    If the config exists but can't be used (invalid TOML, an invalid [notify] value), one
    stderr line says so and the cached settings (else the defaults) apply: an invalid vault
    config must not stop every push. The cache is only rewritten from a usable config."""
    vault = find_vault(vault_arg)
    cfg = {}
    if (vault is not None and (Path(vault) / "_agent" / "uni-os.toml").is_file()) or \
            (config_path and Path(config_path).is_file()):
        try:
            cfg = load_config(vault, config_path, modules_dir) if (config_path or modules_dir) else load_config(vault)
            s = Settings.from_config(cfg, vault)
        except Exception as e:  # noqa: BLE001  ConfigUnreadable, a bad quiet_hours, a non-number ...
            s, source = cached_settings(vault)
            print("push gate: the vault config can't be used (%s); using %s" % (one_line(e), source), file=sys.stderr)
            return s, {}
        try:
            p = gate_state_dir() / "notify-settings.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {"notify": s.public(), "timezone": s.tz, "vault": str(vault) if vault else None}
            if not p.exists() or json.loads(p.read_text(encoding="utf-8") or "{}") != data:
                if not is_dry():
                    p.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
        except (OSError, ValueError):
            pass
        return s, cfg
    p = gate_state_dir() / "notify-settings.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return Settings(data.get("notify"), data.get("timezone"), None), cfg
    except (OSError, ValueError):
        return Settings({}, None, vault), cfg


# ---- quiet hours and quiet windows ---------------------------------------------------------
def _bound(v, end=False, base_date=None):
    """A window bound -> naive datetime. Date-only 'to' bounds mean the end of that day;
    a time-only 'to' bound means that time on the 'from' date."""
    if isinstance(v, dt.datetime):
        return v.replace(tzinfo=None)
    if isinstance(v, dt.date):
        d = dt.datetime(v.year, v.month, v.day)
        return d + dt.timedelta(days=1) if end else d
    if isinstance(v, dt.time):
        if base_date is None:
            return None
        return dt.datetime.combine(base_date, v)
    s = str(v or "").strip()
    if not s:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        d = dt.datetime.fromisoformat(s)
        return d + dt.timedelta(days=1) if end else d
    if re.match(r"^\d{1,2}:\d{2}$", s):
        if base_date is None:
            return None
        h, m = s.split(":")
        return dt.datetime.combine(base_date, dt.time(int(h), int(m)))
    d = parse_when(s)
    return d.replace(tzinfo=None) if d else None


def window_hit(w, now):
    """The label of quiet window `w` if it covers `now`, else None.
    Dated:  {from = "2026-11-19 07:30", to = "2026-11-19 10:00", reason = "..."}
            {from = "2026-11-24", to = "2026-11-24", reason = "..."}   (whole days)
    Weekly: {day = "Mon", from = "08:00", to = "10:00", since = "...", until = "2026-12-21", reason = "..."}
    Any window may add urgent_ok = true (soft: urgent and direct pushes pass)."""
    if not isinstance(w, dict):
        return None
    reason = one_line(w.get("reason") or w.get("label") or "quiet window")
    days = as_list(w.get("day") or w.get("days"))
    if days:
        days = [str(x)[:3].title() for x in days]
        if now.strftime("%a") not in days:
            return None
        today = now.date()
        since, until = w.get("since"), w.get("until")
        if since and today < _bound(since).date():
            return None
        if until and today > _bound(until).date():
            return None
        a = hm_to_min(w.get("from") if not isinstance(w.get("from"), dt.time) else w["from"].strftime("%H:%M"))
        b = hm_to_min(w.get("to") if not isinstance(w.get("to"), dt.time) else w["to"].strftime("%H:%M"))
        mins = now.hour * 60 + now.minute
        if a <= mins < b:
            return "quiet window: %s (%s %s-%s)" % (reason, "/".join(days), w.get("from"), w.get("to"))
        return None
    start = _bound(w.get("from"))
    if start is None:
        return None
    stop = _bound(w.get("to"), end=True, base_date=start.date()) if w.get("to") else start + dt.timedelta(days=1)
    if stop is None:
        return None
    if start <= now < stop:
        return "quiet window: %s (%s to %s)" % (reason, start.strftime("%Y-%m-%d %H:%M"), stop.strftime("%Y-%m-%d %H:%M"))
    return None


def window_now(settings, now, urgent=False, hard_only=False):
    """The quiet window holding pushes now, or None. A window with `urgent_ok = true` is
    soft (e.g. a whole exam session): urgent and direct pushes pass it, and the heartbeat
    keeps running inside it (hard_only=True ignores soft windows)."""
    for w in settings.quiet_windows:
        hit = window_hit(w, now)
        if hit:
            soft = isinstance(w, dict) and bool(w.get("urgent_ok"))
            if soft and (urgent or hard_only):
                continue
            return hit + (" (soft: --urgent passes)" if soft else "")
    return None


def quiet_hours_now(settings, now):
    q = settings.quiet_hours
    if not q:
        return None
    a, b, label = q
    mins = now.hour * 60 + now.minute
    inside = (a <= mins < b) if a < b else (mins >= a or mins < b)
    return "quiet hours (%s)" % label if inside else None


def held_now(settings, now, direct=False, urgent=False):
    """Why a push would be held now (None = it may go out)."""
    w = window_now(settings, now, urgent=urgent or direct)
    if w:
        return w
    if direct:
        return None
    return quiet_hours_now(settings, now)


def dated_windows_ended(settings, now, days=7):
    """Dated quiet windows that ended within the last `days` days (graded fixtures whose
    result may now be missing). Returns [(reason, start, stop)]."""
    out = []
    for w in settings.quiet_windows:
        if not isinstance(w, dict) or w.get("day") or w.get("days"):
            continue
        start = _bound(w.get("from"))
        if start is None:
            continue
        stop = _bound(w.get("to"), end=True, base_date=start.date()) if w.get("to") else start + dt.timedelta(days=1)
        if stop and stop <= now and now - stop <= dt.timedelta(days=days):
            out.append((one_line(w.get("reason") or "graded fixture"), start, stop))
    return out


# ---- state ---------------------------------------------------------------------------------
def _empty_state():
    return {"schema": 1, "pushes": [], "ids": {}, "held": []}


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("schema", 1)
            d.setdefault("pushes", [])
            d.setdefault("ids", {})
            d.setdefault("held", [])
            return d
    except (OSError, ValueError):
        pass
    return _empty_state()


def save_state(path, d, now, tz):
    cutoff = now - dt.timedelta(days=14)

    def keep(at):
        t = to_local(parse_when(at), tz)
        return t is not None and t >= cutoff

    d["pushes"] = [p for p in d["pushes"] if keep(p.get("at"))]
    d["ids"] = {k: v for k, v in d["ids"].items() if keep(v)}
    d["held"] = [h for h in d.get("held", []) if keep(h.get("at"))]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


# ---- the gate --------------------------------------------------------------------------------
class Decision:
    def __init__(self, code, reason, fresh=None, text=None):
        self.code, self.reason, self.fresh, self.text = code, reason, list(fresh or []), text

    def __repr__(self):  # pragma: no cover
        return "Decision(%s, %r, %r)" % (self.code, self.reason, self.fresh)


def check_text(settings, text, direct=False):
    """Refusal reason for a push text, or None. Direct (host) pushes skip the "all good"
    rule (a host may say "recovered"), never the personal-details rule."""
    if not one_line(text):
        return "refused: empty text"
    if not direct and settings.never_all_good and (ALL_GOOD.search(text) or
                                                   any(r.search(text) for r in settings.extra_all_good)):
        return "refused: reads like an 'all good' message (silence is the norm: push only problems)"
    if settings.block_personal:
        for rx, what in PERSONAL:
            if rx.search(text):
                return "refused: the text contains %s. %s" % (what, NO_PERSONAL_REMINDER)
    return None


def _today_gated(st, now, tz):
    day = now.date()
    return [p for p in st["pushes"] if not p.get("direct") and to_local(parse_when(p["at"]), tz).date() == day]


def decide(settings, st, now, ids, text, urgent=False, direct=False):
    """Pure decision (changes nothing). `text` None = only the ids are judged (check mode)."""
    tz = settings.tz
    if not direct and settings.require_id and not ids:
        return Decision(REFUSED, "refused: a push needs at least one problem id (--id): it must be about a "
                                 "flagged problem, never an 'all good'. Host alerts use --direct.")
    if text is not None:
        why = check_text(settings, text, direct)
        if why:
            return Decision(REFUSED, why)
    if direct:
        fresh = list(ids)
    else:
        fresh = []
        for i in ids:
            last = to_local(parse_when(st["ids"].get(i)), tz)
            if last is None or now - last >= dt.timedelta(hours=settings.dedupe_h):
                fresh.append(i)
        if ids and not fresh:
            return Decision(DEDUPE, "dedupe: every id was pushed in the last %g h" % settings.dedupe_h)
    why = held_now(settings, now, direct, urgent)
    if why:
        if direct:
            return Decision(HELD, "held: " + why + "; queued, released as one push by `uni-os push --flush` "
                                                   "after the window", fresh)
        return Decision(HELD, "held: " + why + "; not sent and not queued: send it again after the quiet "
                                               "time if it is still true (keep it as a flag)", fresh)
    if direct:
        return Decision(SENT, "ok (direct)", fresh)
    today = _today_gated(st, now, tz)
    if len(today) >= settings.max_per_day:
        return Decision(BUDGET, "budget: %d pushes today already (max %d)" % (len(today), settings.max_per_day), fresh)
    gated = [t for t in (to_local(parse_when(p["at"]), tz) for p in st["pushes"] if not p.get("direct")) if t <= now]
    if gated and not urgent:
        gap = (now - max(gated)).total_seconds() / 60
        if gap < settings.min_gap_min:
            return Decision(BUDGET, "budget: last push %d min ago (gap %d min; --urgent skips the gap)"
                            % (gap, settings.min_gap_min), fresh)
    return Decision(SENT, "ok", fresh)


def clip(text, n):
    text = one_line(text)
    return text if len(text) <= n else text[: max(1, n - 1)].rstrip() + "…"


# ---- sending --------------------------------------------------------------------------------
def _header_value(v):
    v = one_line(v)
    try:
        v.encode("latin-1")
        return v
    except UnicodeEncodeError:
        return "=?UTF-8?B?%s?=" % base64.b64encode(v.encode("utf-8")).decode("ascii")


def read_topic(settings):
    """(topic, error). The topic is a secret: it lives in a file outside the vault."""
    if not settings.topic_file:
        return None, "notify.ntfy_topic_file is not set"
    p = Path(os.path.expanduser(settings.topic_file))
    if settings.vault is not None:
        try:
            p.resolve().relative_to(Path(settings.vault).resolve())
            return None, ("the ntfy topic file %s is inside the vault: move it out (anyone who knows the "
                          "topic can read your pushes; the vault is synced and read by agents)" % p)
        except ValueError:
            pass
    try:
        topic = p.read_text(encoding="utf-8").strip()
    except OSError:
        return None, "no ntfy topic file at %s (see modules/notifications/README.md, 'Set up ntfy')" % p
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", topic):
        return None, "the ntfy topic in %s must be 1-64 characters of A-Z a-z 0-9 _ -" % p
    return topic, None


def build_request(settings, topic, text, title=None, priority=3, click=None, actions=None):
    server = settings.server
    if not (server.startswith("https://") or re.match(r"^http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$", server)):
        raise ValueError("notify.ntfy_server must be an https:// URL (plain http only for localhost)")
    headers = {"Title": _header_value(title or settings.title), "Priority": str(int(priority)),
               "Content-Type": "text/plain; charset=utf-8"}
    if click:
        headers["Click"] = click
    if actions:
        headers["Actions"] = "; ".join("view, %s, %s" % (_header_value(lbl).replace(",", " "), url) for lbl, url in actions)
    return urllib.request.Request(server + "/" + topic, data=text.encode("utf-8"), headers=headers, method="POST")


def deliver(settings, text, title=None, priority=3, click=None, actions=None, opener=None):
    """Send one push. Returns (code, note)."""
    fake = os.environ.get("UNI_OS_PUSH_FAKE_SEND")
    if fake:
        with open(fake, "a", encoding="utf-8") as f:
            f.write("[p%s] %s%s\n" % (priority, text, (" (click: %s)" % click) if click else ""))
        return SENT, "fake send"
    if settings.provider in ("none", "", "off", "log"):
        return SENT, "logged only (notify.provider = none)"
    if settings.provider != "ntfy":
        return ERROR, "unknown notify.provider %r (ntfy or none)" % settings.provider
    topic, err = read_topic(settings)
    if err:
        return ERROR, err
    try:
        req = build_request(settings, topic, text, title, priority, click, actions)
    except ValueError as e:
        return ERROR, str(e)
    try:
        with (opener or urllib.request.urlopen)(req, timeout=HTTP_TIMEOUT_S) as r:
            status = getattr(r, "status", 200)
        if status >= 300:
            return FAILED, "ntfy answered HTTP %s" % status
    except urllib.error.HTTPError as e:
        return FAILED, "ntfy answered HTTP %s" % e.code
    except (urllib.error.URLError, OSError) as e:
        return FAILED, "could not reach the push server (%s)" % getattr(e, "reason", e)
    return SENT, "sent via ntfy"


def log_line(sd, now, line):
    p = sd / "notify.log"
    try:
        sd.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s | %s\n" % (now.strftime("%Y-%m-%d %H:%M"), line))
        with open(p, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 1500:
            with open(p, "w", encoding="utf-8") as f:
                f.writelines(lines[-1000:])
    except OSError:
        pass


def _dry_record(line):
    out = os.environ.get("UNI_OS_PUSH_DRY_LOG")
    if out:
        try:
            with open(out, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def _busy(sd, now, what, err, out):
    """The gate's lock could not be had in time: nothing sent, nothing recorded (exit 1)."""
    log_line(sd, now, "busy | %s | %s" % (what, err))
    out("gate busy, try later: %s; nothing sent, nothing recorded" % err)
    return FAILED


# ---- the public API used by `uni-os push`, the heartbeat and the outcome checks --------
def push(settings, text=None, ids=(), items=None, prefix="", source="unknown", priority=None, title=None,
         click=None, actions=None, urgent=False, direct=False, check_only=False, dry_run=False,
         now=None, opener=None, out=print):
    """Run one push through the gate. `items` ({id: text}) builds the text from the fresh
    items only (deterministic senders). Returns the exit code; prints one decision line."""
    now = now or now_local(settings.tz)
    dry = is_dry(dry_run)
    sd = gate_state_dir()
    ids = [i for i in (x.strip() for x in ids) if i]
    items = {k.strip(): one_line(v) for k, v in (items or {}).items() if k.strip() and one_line(v)}
    if items:
        ids = list(items)
    if priority is None:
        priority = settings.direct_priority if direct else 3
    priority = int(priority)
    if not 1 <= priority <= 5:
        out("error: --priority must be 1-5")
        return ERROR
    click = click or settings.default_click or None
    stamp = now.strftime("%Y-%m-%d %H:%M")

    with contextlib.ExitStack() as stack:
        if not dry:
            try:
                stack.enter_context(file_lock(sd / ".lock"))
            except GateBusy as e:
                return _busy(sd, now, "%s | %s" % (source, ",".join(ids) or "-"), e, out)
        st = load_state(sd / "state.json")
        if items:
            judged = "; ".join(items.values())
        elif text is not None:
            judged = text
        else:
            judged = None if check_only else ""
        dec = decide(settings, st, now, ids, judged, urgent, direct)
        if items and dec.code in (SENT, HELD):
            body = prefix + "; ".join(dict.fromkeys(items[i] for i in dec.fresh))  # same text once
        else:
            body = one_line(text or "")
        body = clip(body, settings.max_length) if body else body
        idtxt = ",".join(ids) or "-"

        if check_only:
            out("%s (fresh ids: %s)" % (dec.reason, ",".join(dec.fresh) or "none"))
            return dec.code
        if dry:
            what = {SENT: "would send", HELD: "would hold" if direct else "would defer"}.get(dec.code, "would not send")
            line = "%s DRY RUN %s (exit %d) from %s ids=%s: %s | %s" % (stamp, what, dec.code, source, idtxt,
                                                                        dec.reason, body)
            out(line)
            _dry_record(line)
            return dec.code
        if dec.code == HELD:
            # Only direct (host) pushes are queued; a judgment push held by quiet time is
            # deferred: its sender raises it again later if it is still true.
            if direct and not any(h.get("text") == body for h in st.get("held", [])):
                st.setdefault("held", []).append({"at": iso(now, settings.tz), "source": source, "ids": dec.fresh,
                                                  "text": body, "priority": priority, "title": title, "click": click,
                                                  "direct": True, "reason": dec.reason})
                save_state(sd / "state.json", st, now, settings.tz)
            log_line(sd, now, "%s | %s | %s | %s" % ("held" if direct else "deferred", source, idtxt, body))
            out(dec.reason)
            return HELD
        if dec.code != SENT:
            log_line(sd, now, "%s | %s | %s | %s" % (CODE_NAMES[dec.code], source, idtxt, body))
            out("%s (fresh ids: %s)" % (dec.reason, ",".join(dec.fresh) or "none"))
            return dec.code
        code, note = deliver(settings, body, title, priority, click, actions, opener)
        log_line(sd, now, "%s | %s | %s | %s | %s" % ("sent" if code == SENT else CODE_NAMES[code], source, idtxt,
                                                       note, body))
        if code != SENT:
            out("send failed: %s" % note)
            return code
        st["pushes"].append({"at": iso(now, settings.tz), "source": source, "ids": dec.fresh, "text": body,
                             "direct": bool(direct)})
        for i in dec.fresh:
            st["ids"][i] = iso(now, settings.tz)
        save_state(sd / "state.json", st, now, settings.tz)
        if direct:
            out("sent (direct, outside the budget): %s" % body)
        else:
            out("sent (%d of %d today): %s" % (len(_today_gated(st, now, settings.tz)), settings.max_per_day, body))
        return SENT


def flush(settings, now=None, dry_run=False, opener=None, out=print):
    """Release the held queue (direct pushes held inside a quiet window) as ONE combined
    push once the window is over. Items older than hold_max_hours are dropped."""
    now = now or now_local(settings.tz)
    dry = is_dry(dry_run)
    sd = gate_state_dir()
    tz = settings.tz
    with contextlib.ExitStack() as stack:
        if not dry:
            try:
                stack.enter_context(file_lock(sd / ".lock"))
            except GateBusy as e:
                return _busy(sd, now, "flush", e, out)
        st = load_state(sd / "state.json")
        held = st.get("held", [])
        if not held:
            out("nothing held")
            return SENT
        keep, drop = [], []
        for h in held:
            at = to_local(parse_when(h.get("at")), tz)
            if at is None or now - at > dt.timedelta(hours=settings.hold_max_h):
                drop.append(h)
                continue
            if not h.get("direct") and h.get("ids"):
                fresh = [i for i in h["ids"] if not st["ids"].get(i) or
                         now - to_local(parse_when(st["ids"][i]), tz) >= dt.timedelta(hours=settings.dedupe_h)]
                if not fresh:
                    drop.append(h)
                    continue
                h = dict(h, ids=fresh)
            keep.append(h)
        if not keep:
            if not dry:
                st["held"] = []
                save_state(sd / "state.json", st, now, tz)
                log_line(sd, now, "flush | dropped %d expired or already pushed" % len(drop))
            out("nothing to release (%d expired or already pushed)" % len(drop))
            return SENT
        direct_only = all(h.get("direct") for h in keep)
        why = held_now(settings, now, direct_only)
        if why:
            out("still held: " + why)
            return HELD
        if not direct_only and len(_today_gated(st, now, tz)) >= settings.max_per_day:
            out("still held: the day's budget is used up (max %d); released tomorrow" % settings.max_per_day)
            return BUDGET
        texts = [h["text"] for h in keep]
        body = texts[0] if len(texts) == 1 else "Held during a quiet window: " + "; ".join(texts)
        body = clip(body, settings.max_length)
        ids = sorted({i for h in keep for i in h.get("ids", [])})
        prio = max(int(h.get("priority") or 3) for h in keep)
        click = next((h.get("click") for h in keep if h.get("click")), None)
        title = next((h.get("title") for h in keep if h.get("title")), None)
        if dry:
            line = "%s DRY RUN would release %d held push(es) ids=%s: %s" % (now.strftime("%Y-%m-%d %H:%M"), len(keep),
                                                                           ",".join(ids) or "-", body)
            out(line)
            _dry_record(line)
            return SENT
        code, note = deliver(settings, body, title, prio, click, None, opener)
        log_line(sd, now, "flush %s | %d item(s) | %s | %s | %s" % ("sent" if code == SENT else CODE_NAMES[code],
                                                                  len(keep), ",".join(ids) or "-", note, body))
        if code != SENT:
            out("send failed: %s (the queue is kept)" % note)
            return code
        st["pushes"].append({"at": iso(now, tz), "source": "flush", "ids": ids, "text": body, "direct": direct_only})
        for i in ids:
            st["ids"][i] = iso(now, tz)
        st["held"] = []
        save_state(sd / "state.json", st, now, tz)
        out("released %d held push(es) as one: %s" % (len(keep), body))
        return SENT


def status(settings, now=None):
    now = now or now_local(settings.tz)
    st = load_state(gate_state_dir() / "state.json")
    tz = settings.tz
    today = _today_gated(st, now, tz)
    gated = [p for p in st["pushes"] if not p.get("direct")]
    last = gated[-1] if gated else None
    recent = sorted(k for k, v in st["ids"].items()
                    if now - to_local(parse_when(v), tz) < dt.timedelta(hours=settings.dedupe_h))
    return {"now": iso(now, tz), "provider": settings.provider, "pushes_today": len(today),
            "day_max": settings.max_per_day, "left_today": max(0, settings.max_per_day - len(today)),
            "min_gap_min": int(settings.min_gap_min), "held_now_by": held_now(settings, now),
            "window_now": window_now(settings, now), "held_queue": len(st.get("held", [])),
            "last_push": last and {k: last.get(k) for k in ("at", "source", "ids")},
            "ids_pushed_recently": recent, "state_dir": str(gate_state_dir())}
