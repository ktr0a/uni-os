#!/usr/bin/env python3
"""Uni OS host: read the vault config and write the host's settings file (stdlib only).

The host scripts are bash and read one file, ~/.config/uni-os/host.env. This helper builds it
from the vault config (<vault>/_agent/uni-os.toml, with every enabled module's [defaults] from
the framework copy merged underneath, user values win) plus the host-only values that the
install asks for. It also renders the host's text templates (@@KEY@@ placeholders).

Usage:
  vaultconf.py get KEY [--vault DIR] [--uni-os DIR] [--default VALUE]
      Print one config value (lists joined by ", ", true/false as yes/no). KEY may be "a|b":
      the first key that is set and not 0 or empty.
  vaultconf.py host-env [--vault DIR] [--uni-os DIR] [--existing FILE] [--set KEY=VALUE ...]
      Print a complete host.env. Host-only keys keep their value from --existing (or --set,
      or the default); config keys are refreshed from the vault when it is readable, else kept.
      Lines below the "local overrides" marker of --existing are kept verbatim.
  vaultconf.py set-local FILE KEY VALUE
      Set KEY in the "local overrides" section of host.env (later lines win in bash).
  vaultconf.py history-filters [--vault DIR] [--uni-os DIR]
      Print the rclone filter file for vault-history (excludes from vm.history_exclude).
  vaultconf.py render --host-env FILE [--set KEY=VALUE ...] SRC DST
      Copy SRC to DST, replacing @@KEY@@ with values from host.env and --set (plus @@HOST_DIR@@,
      @@HOME@@, @@STATE@@).
"""
import argparse
import os
import re
import shlex
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_UNI_OS = HERE.parents[3]          # .../uni-os/modules/vm/host/lib -> .../uni-os
MARKER = "# --- local overrides (kept by install-user.sh; later lines win) ---"

# Host-only keys: asked at the first install (or defaulted), then kept. (key, default, help)
HOST_LOCAL = [
    ("UNI_OS_HOME", str(DEFAULT_UNI_OS), "framework copy on this host"),
    ("UNI_OS_REPO_URL", "@vm.repo_url", "git URL to clone/pull the framework from; empty = laptop deploy"),
    ("VAULT_MOUNT", "@vm.mount_path", "where the vault is on this host"),
    ("VAULT_SENTINEL", "_agent/agent-start.md", "file that proves the mount is real"),
    ("STORAGE_MODE", "@storage", "rclone-mount | local"),
    ("DRIVE_REMOTE", "@vm.drive_remote", "rclone remote whose root is the vault folder"),
    ("DRIVE_READ_ONLY", "no", "yes = read-only mount (trial host)"),
    ("RCLONE_ALLOW_OTHER", "no", "yes = Windows may read the mount (WSL home server)"),
    ("RCLONE_CACHE_MAX", "6G", "rclone VFS cache size"),
    ("AGENT_BIN", "~/.local/bin/claude", "agent CLI binary"),
    ("AGENT_PERMISSION_MODE", "bypassPermissions", "permission mode for jobs, roles, RC"),
    ("AGENT_HEADLESS_CMD", "", "other agents: headless command (prompt appended)"),
    ("AGENT_INTERACTIVE_CMD", "", "other agents: interactive command (prompt appended)"),
    ("AGENT_LOGIN_CHECK_CMD", "", "other agents: exit 0 while logged in"),
    ("RC_ENABLED", "@rc", "yes = keep the Claude Code Remote Control server running"),
    ("JOBS_LIVE", "yes", "no = trial host, every job timer stays off"),
    ("VAULT_WRITES", "yes", "no = never write _agent/vm/* from this host (one writer)"),
    ("LAPTOP_SEEN_MIN", "15", "laptop ping younger than this = laptop online"),
]

# Config-derived keys: refreshed from the vault config at every install. (key, config key, default)
# "a|b" = the first of these keys that is set and not 0/empty: an alias first, then the one shared key.
FROM_CONFIG = [
    ("HOST_NAME", "vm.host_alias", "uni-vm"),
    ("HOST_KIND", "vm.provider", "gcp"),
    ("OWNER", "student.name", "the student"),
    ("TZ_NAME", "term.timezone", ""),
    ("AGENT_CLI", "agent.primary", "claude-code"),
    ("AGENT_DEFAULT_MODEL", "vm.default_model", "sonnet"),
    ("AGENT_DEFAULT_EFFORT", "vm.default_effort", "high"),
    ("RC_NAME", "vm.remote_control_name", "Uni (VM)"),
    ("RC_PREFIX", "vm.rc_prefix", "uni-vm"),
    ("RC_CAPACITY", "vm.rc_capacity", "10"),
    ("RC_CHROME", "vm.rc_chrome", "yes"),
    ("RC_UPDATE_HOUR", "vm.rc_update_hour", "4"),
    ("MACHINE_LABEL", "vm.machine_type", ""),
    ("BUDGET_MONTH", "vm.budget_month", ""),
    ("BUDGET_CURRENCY", "vm.budget_currency", ""),
    ("MONTHLY_CREDIT", "vm.monthly_credit", "0"),
    ("MEM_ALERT_MB", "vm.mem_alert_mb", "500"),
    ("MEM_CLOSE_JOBS_MB", "vm.mem_close_jobs_mb", "700"),
    ("SWAPIN_ALERT_RATE", "vm.swapin_alert_rate", "250"),
    ("DISK_ALERT_PCT", "vm.disk_alert_pct", "90"),
    ("ALERT_REPEAT_H", "vm.alert_repeat_h", "3"),
    ("BIG_CONTEXT_K", "vm.big_context_k", "300"),
    ("OUTCOME_PREP_GRACE_MIN", "vm.outcome_prep_grace_min", "60"),
    # Stuck inbox notes: one threshold for every sender (notify.inbox_stale_hours[_taps], module
    # inbox-sync); vm.inbox_stuck_h / vm.tap_stuck_h are aliases kept for old configs (0 = unset).
    ("INBOX_STUCK_H", "vm.inbox_stuck_h|notify.inbox_stale_hours", "4"),
    ("TAP_STUCK_H", "vm.tap_stuck_h|notify.inbox_stale_hours_taps", "14"),
    ("GAP_OPEN_H", "heartbeat.gap_open_hours", "24"),
    ("OUTCOME_PREFIX", "heartbeat.outcome_prefix", "Outcome check: "),
    ("AGENT_DIR", "paths.agent_dir", "_agent"),
    ("INBOX_DIR", "paths.inbox", "inbox"),
    ("DAILY_PREP_SLOTS", "schedule.daily_prep", ""),
    ("MODULES_ENABLED", "modules.enabled", ""),
    ("NOTIFY_PROVIDER", "notify.provider", "ntfy"),
    ("NTFY_TOPIC_FILE", "notify.ntfy_topic_file", "~/.config/uni-os/ntfy-topic"),
    ("NTFY_SERVER", "notify.ntfy_server", "https://ntfy.sh"),
]

HISTORY_INCLUDE = ["*.md", "*.html", "*.json", "*.canvas", "*.base", "*.css", "*.py",
                   "*.txt", "*.csv", "*.tsv", "*.ts"]


def deep_merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(vault, uni_os):
    """User config with module defaults merged underneath. None if the vault config is unreadable."""
    path = Path(vault).expanduser() / "_agent" / "uni-os.toml"
    try:
        with open(path, "rb") as f:
            user = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    enabled = set(user.get("modules", {}).get("enabled", [])) | {"core", "vm"}
    merged = {}
    mods = Path(uni_os).expanduser() / "modules"
    for mt in sorted(mods.glob("*/module.toml")):
        if mt.parent.name not in enabled:
            continue
        try:
            with open(mt, "rb") as f:
                defaults = tomllib.load(f).get("defaults", {})
        except (OSError, tomllib.TOMLDecodeError):
            continue
        defaults = {k: v for k, v in defaults.items() if k != "course"}
        merged = deep_merge(merged, defaults)
    return deep_merge(merged, user)


def lookup_chain(cfg, spec):
    """lookup() over "a|b|...": the first key that is set and not 0 or empty (aliases first)."""
    keys = spec.split("|")
    for i, key in enumerate(keys):
        v = lookup(cfg, key)
        if v is None:
            continue
        if i < len(keys) - 1 and (v == "" or (not isinstance(v, bool) and isinstance(v, (int, float)) and v == 0)):
            continue
        return v
    return None


def lookup(cfg, key):
    cur = cfg
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def as_text(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (list, tuple)):
        return ", ".join(as_text(x) for x in v)
    if isinstance(v, dict):
        return ""
    return "" if v is None else str(v)


def parse_env(path):
    """KEY=value lines of a bash env file (single/double quotes, no expansions). Returns
    (values, overrides_text)."""
    values, extra = {}, []
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except OSError:
        return values, ""
    in_extra = False
    for line in text.splitlines():
        if line.strip() == MARKER:
            in_extra = True
            continue
        if in_extra:
            extra.append(line)
        m = re.match(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if not m:
            continue
        try:
            parts = shlex.split(m.group(2), comments=True)
        except ValueError:
            continue
        values[m.group(1)] = parts[0] if parts else ""
    return values, "\n".join(extra).strip("\n")


def resolve_default(spec, cfg):
    if not spec.startswith("@"):
        return spec
    if spec == "@storage":
        prov = as_text(lookup(cfg, "storage.provider")) if cfg else "google-drive"
        return "rclone-mount" if prov in ("", "google-drive") else "local"
    if spec == "@rc":
        prim = as_text(lookup(cfg, "agent.primary")) if cfg else "claude-code"
        return "yes" if prim in ("", "claude-code") else "no"
    fallback = {"@vm.repo_url": "", "@vm.mount_path": "~/Uni", "@vm.drive_remote": "uni-drive"}
    v = as_text(lookup(cfg, spec[1:])) if cfg else ""
    return v or fallback.get(spec, "")


def finish(key, value):
    value = as_text(value) if not isinstance(value, str) else value
    if key == "AGENT_CLI":
        value = "claude" if value in ("claude-code", "claude", "") else value
    if key == "OWNER" and value:
        value = value.split()[0]
    if key == "RC_UPDATE_HOUR":
        try:
            value = "%02d" % int(value)
        except ValueError:
            value = "04"
    if value.startswith("~"):
        value = os.path.expanduser(value)
    return value


def cmd_get(a):
    cfg = load_config(a.vault, a.uni_os)
    v = lookup_chain(cfg, a.key) if cfg else None
    print(a.default if v is None else as_text(v))
    return 0


def cmd_host_env(a):
    old, extra = parse_env(a.existing) if a.existing else ({}, "")
    sets = dict(s.split("=", 1) for s in (a.set or []))
    vault = a.vault or sets.get("VAULT_MOUNT") or old.get("VAULT_MOUNT") or "~/Uni"
    cfg = load_config(vault, a.uni_os)
    lines = [
        "# Uni OS host settings: read by every script in modules/vm/host (bash syntax).",
        "# Written by install-user.sh. Re-run it after changing the vault config. Put your own",
        "# changes BELOW the 'local overrides' marker: they are kept, and later lines win.",
        "# Never put secrets here (topic, tokens and keys live in their own files).",
        "",
        "# -- host-only values (asked at the first install, then kept) --",
    ]
    for key, default, help_ in HOST_LOCAL:
        if key in sets:
            v = sets[key]
        elif key in old:
            v = old[key]
        else:
            v = resolve_default(default, cfg)
        lines.append(f"{key}={shlex.quote(finish(key, v))}    # {help_}")
    lines += ["", "# -- from the vault config (_agent/uni-os.toml + module defaults), refreshed by install-user.sh --"]
    if cfg is None:
        lines.append("# (vault config not readable at the last install: kept previous values or defaults)")
    for key, ckey, default in FROM_CONFIG:
        if key in sets:
            v = sets[key]
        elif cfg is not None and lookup_chain(cfg, ckey) is not None:
            v = lookup_chain(cfg, ckey)
        elif key in old:
            v = old[key]
        else:
            v = default
        lines.append(f"{key}={shlex.quote(finish(key, v))}    # {ckey}")
    lines += ["", MARKER]
    if extra:
        lines.append(extra)
    print("\n".join(lines))
    return 0


def cmd_set_local(a):
    p = Path(a.file).expanduser()
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if MARKER not in text:
        text = text.rstrip("\n") + ("\n\n" if text else "") + MARKER + "\n"
    head, _, tail = text.partition(MARKER)
    kept = [l for l in tail.splitlines() if l.strip() and not re.match(rf"^\s*{re.escape(a.key)}=", l)]
    kept.append(f"{a.key}={shlex.quote(a.value)}")
    p.write_text(head + MARKER + "\n" + "\n".join(kept) + "\n", encoding="utf-8", newline="\n")
    print(f"{a.key}={a.value} (in {p}, local overrides)")
    return 0


def _as_list(v):
    if v is None or v == "":
        return []
    return [str(x) for x in v] if isinstance(v, (list, tuple)) else [str(v)]


def cmd_history_filters(a):
    cfg = load_config(a.vault, a.uni_os) or {}
    excl = _as_list(lookup(cfg, "vm.history_exclude")) or [".obsidian/plugins/**", "**/node_modules/**",
                                                           "_agent/vm/snapshot.json"]
    # Private paths are never copied either: the shared privacy key paths.never_open (base
    # default: any "private" folder) and the note app's own data folder (handwritten-notes).
    never = lookup(cfg, "paths.never_open")
    private = _as_list(never) if never is not None else ["**/private/**"]
    app_data = as_text(lookup(cfg, "paths.handwriting_app_data")).strip().strip("/")
    if app_data:
        private.append(app_data + "/**")
    out = ["# rclone filter file for vault-history (generated by install-user.sh from vm.history_exclude,",
           "# paths.never_open and paths.handwriting_app_data; the first matching rule wins)"]
    seen = set()
    for p in private + excl:
        # rclone matches a pattern without a leading "/" at any depth, but "**/x/**" still needs
        # a "/" before x, so a top-level x/ would slip through: add "x/**" as well.
        for q in ([p, p[3:]] if p.startswith("**/") else [p]):
            if q and q not in seen:
                seen.add(q)
                out.append(f"- {q}")
    out += [f"+ {p}" for p in HISTORY_INCLUDE]
    out.append("- *")
    print("\n".join(out))
    return 0


def cmd_render(a):
    values, _ = parse_env(a.host_env)
    values.update(dict(s.split("=", 1) for s in (a.set or [])))
    values.setdefault("HOME", os.path.expanduser("~"))
    values.setdefault("HOST_DIR", str(HERE.parent))
    values.setdefault("STATE", os.path.expanduser("~/.local/state/uni-os"))
    text = Path(a.src).read_text(encoding="utf-8")

    def sub(m):
        return values.get(m.group(1), m.group(0))

    text = re.sub(r"@@([A-Z_][A-Z0-9_]*)@@", sub, text)
    runtime = {"ROLE", "TITLE", "BRIEF", "HANDOVER"}      # filled later by role-sessions
    left = sorted(set(re.findall(r"@@([A-Z_][A-Z0-9_]*)@@", text)) - runtime)
    Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
    Path(a.dst).write_text(text, encoding="utf-8", newline="\n")
    if left:
        print(f"render: {a.src}: no value for {', '.join(left)}", file=sys.stderr)
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(newline="\n")      # host.env and filter files: LF even on Windows
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("get")
    g.add_argument("key")
    g.add_argument("--vault", default="~/Uni")
    g.add_argument("--uni-os", default=str(DEFAULT_UNI_OS))
    g.add_argument("--default", default="")
    h = sub.add_parser("host-env")
    h.add_argument("--vault", default="")
    h.add_argument("--uni-os", default=str(DEFAULT_UNI_OS))
    h.add_argument("--existing", default="")
    h.add_argument("--set", action="append")
    s = sub.add_parser("set-local")
    s.add_argument("file")
    s.add_argument("key")
    s.add_argument("value")
    f = sub.add_parser("history-filters")
    f.add_argument("--vault", default="~/Uni")
    f.add_argument("--uni-os", default=str(DEFAULT_UNI_OS))
    r = sub.add_parser("render")
    r.add_argument("--host-env", required=True)
    r.add_argument("--set", action="append")
    r.add_argument("src")
    r.add_argument("dst")
    a = p.parse_args(argv)
    return {"get": cmd_get, "host-env": cmd_host_env, "set-local": cmd_set_local,
            "history-filters": cmd_history_filters, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
