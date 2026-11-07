#!/usr/bin/env python3
"""Ask the course pick-up (module course-files-fetch) to file a browser download into the vault.

Usable from any host that sees the vault: the laptop itself, an always-on VM with the vault mounted, or another
machine. Python 3.11+, standard library only.

  python request_pickup.py [--vault DIR] [--approved-large] [--no-wait] [--machine NAME] "<file name as the browser saved it>" "<course folder>/<official subfolder>"
  python request_pickup.py [--vault DIR] --status <request id>
  python request_pickup.py [--vault DIR] --pending

What it does:
  1. checks the request locally (plain file name, target is one of the configured official folders, date
     guards) so an obviously wrong request fails at once instead of after the pick-up's 30-minute wait;
     the pick-up task on the laptop checks everything again and decides (it trusts no request),
  2. writes <vault>/_agent/course-fetch/pending/<YYYYMMDD-HHMMSS>-<sanitised name>.json
     {"file", "target", "requested_at", "approved_large"[, "machine"]} (written to a temporary name first),
  3. waits for <vault>/_agent/course-fetch/done/<id>.result.json (default up to 15 min, checks every 10 s),
     prints it as one JSON line plus a hint, and
  4. for "filed" or "already-there", re-checks the SHA-256 of <vault>/<target>/<file> until it matches
     (the storage sync can lag; default up to 5 min).

Exit codes: 0 filed or already there (hash verified here), 1 refused, not found, changed on the server or failed,
2 usage error, 4 no answer yet (the laptop is off or asleep, or the sync has not delivered the file yet;
the request stays in pending/: check later with --status <id>).

The vault is found from --vault, else the UNI_OS_VAULT environment variable, else by walking up from the
current folder to the first folder that contains _agent/uni-os.toml.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_NO_ANSWER = 0, 1, 2, 4
BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

HINTS = {
    "filed": "Filed. Move nothing else; log it in _agent/course-fetch/course-fetch-log.md.",
    "already-there": "The same file (same hash) was already in the vault; the download went to the Recycle Bin.",
    "changed-on-server": "A different file with this name is in the vault. Both kept, nothing overwritten; the download "
                         "stays in Downloads. Replacing needs the user's yes (see _agent/course-fetch/RUNBOOK.md).",
    "rejected": "Refused by the pick-up policy (see the reason and _agent/course-fetch/pickup-policy.md).",
    "not-found": "The download never landed in Downloads (unfinished .crdownload, or a blocked multiple-download "
                 "prompt that leaves no trace). Check the browser's download list, download again in a NEW tab, "
                 "check that the download started, then request again.",
    "failed": "The pick-up hit an error (see the reason); the laptop's pickup.log has details.",
}


def find_vault(arg: str | None) -> Path | None:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("UNI_OS_VAULT")
    if env:
        return Path(env).expanduser()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "_agent" / "uni-os.toml").is_file():
            return p
    return None


def load_config(vault: Path) -> dict:
    """Effective config if available (_agent/uni-os.json), else the user's TOML, else {}."""
    j = vault / "_agent" / "uni-os.json"
    if j.is_file():
        try:
            return json.loads(j.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    t = vault / "_agent" / "uni-os.toml"
    if tomllib and t.is_file():
        try:
            return tomllib.loads(t.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def get(d: dict, path: str, default=None):
    cur = d
    for seg in path.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return default
        cur = cur[seg]
    return cur


def allowed_folders(cfg: dict) -> list[str]:
    out: list[str] = []
    for c in cfg.get("courses", []) or []:
        folder = str(c.get("folder", "")).replace("\\", "/").strip("/")
        if not folder:
            continue
        for s in c.get("official_subfolders", []) or []:
            t = folder + "/" + str(s).replace("\\", "/").strip("/")
            if t not in out:
                out.append(t)
    return out


def guard_hit(cfg: dict, name: str, target: str, today: dt.date) -> str | None:
    courses = cfg.get("courses", []) or []
    for g in get(cfg, "course_fetch.date_guards", []) or []:
        folder = str(g.get("folder", "")).strip("/")
        cname = str(g.get("course", ""))
        if not folder and cname:
            for c in courses:
                if cname.lower() in (str(c.get("id", "")).lower(), str(c.get("short", "")).lower(),
                                     str(c.get("folder", "")).lower()):
                    folder = str(c.get("folder", "")).replace("\\", "/").strip("/")
        if not folder:
            continue
        try:
            not_before = dt.date.fromisoformat(str(g.get("not_before", "")))
            # case-insensitive, like the pick-up's PowerShell -match, so both sides refuse the same names
            hit = re.search(str(g.get("pattern", "")), name, re.IGNORECASE)
        except (ValueError, re.error):
            continue
        if (target == folder or target.startswith(folder + "/")) and hit and today < not_before:
            return f"date guard: {g.get('reason') or 'integrity date guard'} (not before {not_before.isoformat()})"
    return None


def check_name(name: str) -> str | None:
    if not name or BAD_NAME.search(name) or name.startswith(".") or name[-1] in ". " or len(name) > 200:
        return "bad file name (give the plain name as the browser saved it, no folders)"
    return None


def make_id(name: str, now: dt.datetime) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:60]
    return f"{now:%Y%m%d-%H%M%S}-{safe}"


def write_request(queue: Path, req_id: str, payload: dict) -> Path:
    pending = queue / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (queue / "done").mkdir(parents=True, exist_ok=True)
    final = pending / f"{req_id}.json"
    n = 2
    while final.exists() or (queue / "done" / f"{final.stem}.result.json").exists():
        final = pending / f"{req_id}-{n}.json"
        n += 1
    tmp = pending / f".{final.name}.part"          # the pick-up only reads *.json
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, final)
    return final


def read_result(path: Path) -> dict | None:
    try:
        if path.is_file() and path.stat().st_size > 0:
            return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None                                   # still syncing or half written: try again
    return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wait_result(queue: Path, req_id: str, timeout_s: float, step_s: float) -> dict | None:
    path = queue / "done" / f"{req_id}.result.json"
    end = time.monotonic() + timeout_s
    while True:
        r = read_result(path)
        if r is not None or time.monotonic() >= end:
            return r
        time.sleep(step_s)


def verify(vault: Path, result: dict, file_name: str, timeout_s: float, step_s: float) -> bool:
    dest = vault / str(result.get("target", "")) / file_name
    want = str(result.get("sha256", "")).lower()
    end = time.monotonic() + timeout_s
    while True:
        try:
            if want and dest.is_file() and sha256(dest) == want:
                return True
        except OSError:
            pass
        if time.monotonic() >= end:
            return False
        time.sleep(step_s)


def report(result: dict) -> int:
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    status = str(result.get("status", ""))
    if status in HINTS:
        print(HINTS[status])
    return EXIT_OK if status in ("filed", "already-there") else EXIT_REFUSED


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ask the laptop's course pick-up to file a browser download into the vault.")
    ap.add_argument("file", nargs="?", help="file name exactly as the browser saved it (no folder)")
    ap.add_argument("target", nargs="?", help="vault-relative official folder, e.g. 'DM/assignments'")
    ap.add_argument("--vault", help="vault folder (default: $UNI_OS_VAULT or the nearest folder with _agent/uni-os.toml)")
    ap.add_argument("--approved-large", action="store_true", help="the user approved a file over the size limit")
    ap.add_argument("--no-wait", action="store_true", help="write the request and return at once")
    ap.add_argument("--machine", help="only this machine's pick-up may handle it (its Windows computer name)")
    ap.add_argument("--status", metavar="ID", help="print the result of an earlier request")
    ap.add_argument("--pending", action="store_true", help="list requests still waiting")
    ap.add_argument("--timeout-min", type=float, help="how long to wait for the result (default: course_fetch.request_timeout_min or 15)")
    ap.add_argument("--verify-min", type=float, help="how long to wait for the filed copy to sync here (default: course_fetch.verify_timeout_min or 5)")
    ap.add_argument("--poll-s", type=float, default=10.0, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    vault = find_vault(a.vault)
    if vault is None or not vault.is_dir():
        print("vault not found: pass --vault \"<vault folder>\" or set UNI_OS_VAULT", file=sys.stderr)
        return EXIT_USAGE
    queue = vault / "_agent" / "course-fetch"
    cfg = load_config(vault)

    if a.pending:
        now = time.time()
        rows = sorted((queue / "pending").glob("*.json")) if (queue / "pending").is_dir() else []
        for p in rows:
            print(f"{p.stem}  waiting {int((now - p.stat().st_mtime) // 60)} min")
        if not rows:
            print("no pending requests")
        return EXIT_OK

    if a.status:
        r = read_result(queue / "done" / f"{a.status}.result.json")
        if r is None:
            where = "pending" if (queue / "pending" / f"{a.status}.json").exists() else "unknown"
            print(f"no result yet for {a.status} ({where})")
            return EXIT_NO_ANSWER
        return report(r)

    if not a.file or not a.target:
        ap.print_usage(sys.stderr)
        return EXIT_USAGE
    name = a.file.strip()
    target = a.target.replace("\\", "/").strip("/")

    problem = check_name(name)
    folders = allowed_folders(cfg)
    if not problem and folders and target not in folders:
        problem = "target is not one of the configured official folders: " + ", ".join(folders)
    if not problem:
        problem = guard_hit(cfg, name, target, dt.date.today())
    if problem:
        print(f"refused here, nothing requested: {problem}")
        return EXIT_REFUSED

    now = dt.datetime.now().astimezone()
    payload = {"file": name, "target": target, "requested_at": now.isoformat(timespec="seconds"),
               "approved_large": bool(a.approved_large)}
    if a.machine:
        payload["machine"] = a.machine
    path = write_request(queue, make_id(name, now), payload)
    req_id = path.stem
    print(f"requested: {req_id}")
    if a.no_wait:
        return EXIT_OK

    timeout = a.timeout_min if a.timeout_min is not None else float(get(cfg, "course_fetch.request_timeout_min", 15))
    vtimeout = a.verify_min if a.verify_min is not None else float(get(cfg, "course_fetch.verify_timeout_min", 5))
    r = wait_result(queue, req_id, timeout * 60, a.poll_s)
    if r is None:
        print(f"no answer after {timeout:g} min (laptop off or asleep, or the sync is slow). The request stays in "
              f"pending/; check later with --status {req_id}")
        return EXIT_NO_ANSWER
    code = report(r)
    if code != EXIT_OK:
        return code
    if verify(vault, r, name, vtimeout * 60, a.poll_s):
        print(f"verified here: {vault / str(r.get('target', '')) / name}")
        return EXIT_OK
    print(f"the pick-up says {r.get('status')}, but the copy here does not match yet (sync lag): check "
          f"{vault / str(r.get('target', '')) / name} later")
    return EXIT_NO_ANSWER


if __name__ == "__main__":
    sys.exit(main())
