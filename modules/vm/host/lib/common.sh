# shellcheck shell=bash
# Uni OS host: shared helpers for every script in host/bin (sourced, never run).
#
# Every host script starts with:
#   HOST_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
#   . "$HOST_DIR/lib/common.sh"
# and then has these variables and functions.
#
# Configuration comes from ONE file, ~/.config/uni-os/host.env (bash KEY='value' lines),
# written by install-user.sh from the vault config (<vault>/_agent/uni-os.toml) plus the
# values asked during the install. The defaults below are used when a key is missing.
# Test hooks: UNI_HOST_ENV (another host.env), UNI_STATE_DIR, UNI_JOBS_DIR, UNI_ROLES_DIR,
# UNI_PUSH_FAKE_SEND (every push is appended to that file instead of being sent),
# UNI_VAULT_WAIT_S (how long to wait for the vault mount; default 120).

UNI_HOST_ENV="${UNI_HOST_ENV:-$HOME/.config/uni-os/host.env}"

# ---- defaults (host.env overrides every one of them) ---------------------------------------
UNI_OS_HOME="$HOME/uni-os"            # the framework copy on this host (git clone or laptop deploy)
UNI_OS_REPO_URL=""                    # git URL install-user.sh pulls from; empty = copied by laptop deploy
VAULT_MOUNT="$HOME/Uni"               # the vault on this host (rclone mount or a local folder)
VAULT_SENTINEL="_agent/agent-start.md" # a file that proves the mount is not an empty directory
STORAGE_MODE="rclone-mount"           # rclone-mount | local
DRIVE_REMOTE="uni-drive"              # rclone remote whose root is the vault folder
DRIVE_READ_ONLY="no"                  # yes = mount read-only (trial of a second host)
RCLONE_ALLOW_OTHER="no"               # yes = other users (e.g. Windows via \\wsl.localhost) may read the mount
RCLONE_CACHE_MAX="6G"
HOST_NAME="uni-vm"                    # how agents and the student call this box
HOST_KIND="gcp"                       # gcp | home-server | other
OWNER="the student"
TZ_NAME=""
AGENT_CLI="claude"                    # claude (Claude Code, tested) | other (see AGENT_*_CMD)
AGENT_BIN="$HOME/.local/bin/claude"
AGENT_DEFAULT_MODEL="sonnet"
AGENT_DEFAULT_EFFORT="high"
AGENT_PERMISSION_MODE="bypassPermissions"
AGENT_HEADLESS_CMD=""                 # other agents: headless run, the prompt is appended as the last argument
AGENT_INTERACTIVE_CMD=""              # other agents: interactive session in tmux, prompt as the last argument
AGENT_LOGIN_CHECK_CMD=""              # other agents: exits 0 while logged in (empty = no check)
RC_ENABLED="yes"                      # Claude Code Remote Control server (rc-loop)
RC_NAME="Uni (VM)"
RC_PREFIX="uni-vm"
RC_CAPACITY="10"
RC_CHROME="yes"
RC_UPDATE_HOUR="04"
JOBS_LIVE="yes"                       # no = trial host: install keeps every job timer off
VAULT_WRITES="yes"                    # no = this host never writes _agent/vm/* (one writer per file)
MACHINE_LABEL=""
BUDGET_MONTH=""
BUDGET_CURRENCY=""
MONTHLY_CREDIT="0"
MEM_ALERT_MB="500"
MEM_CLOSE_JOBS_MB="700"
SWAPIN_ALERT_RATE="250"
DISK_ALERT_PCT="90"
ALERT_REPEAT_H="3"
BIG_CONTEXT_K="300"
LAPTOP_SEEN_MIN="15"
JOB_LOGS_KEEP="40"
AGENT_DIR="_agent"
INBOX_DIR="inbox"
DAILY_PREP_SLOTS=""
MODULES_ENABLED=""
OUTCOME_PREP_GRACE_MIN="60"
INBOX_STUCK_H="4"                     # stuck inbox notes: notify.inbox_stale_hours (one threshold for every sender)
TAP_STUCK_H="14"                      # Done taps: notify.inbox_stale_hours_taps
TAP_REGEX='_(cockpit|quickview)-(done|undo)-'   # the same tap pattern as the heartbeat rules and the inbox poll
GAP_OPEN_H="24"                       # heartbeat.gap_open_hours
OUTCOME_PREFIX="Outcome check: "      # heartbeat.outcome_prefix (the same push prefix as `uni-os heartbeat outcomes`)
NOTIFY_PROVIDER="ntfy"
NTFY_TOPIC_FILE="$HOME/.config/uni-os/ntfy-topic"
NTFY_SERVER="https://ntfy.sh"

# shellcheck disable=SC1090
[ -f "$UNI_HOST_ENV" ] && . "$UNI_HOST_ENV"

CONF_DIR="$(dirname "$UNI_HOST_ENV")"
STATE="${UNI_STATE_DIR:-$HOME/.local/state/uni-os}"
JOBS_DIR="${UNI_JOBS_DIR:-$HOME/.local/share/uni-os/jobs}"   # host copy of <vault>/_agent/jobs (uni-vm jobs sync)
ROLES_CONF_DIR="${UNI_ROLES_DIR:-$CONF_DIR/roles}"            # <role>.conf, host-only
AGENT_FILES="$CONF_DIR/agent"                                  # rendered machine notes, job header, start prompt
VAULT="$VAULT_MOUNT"
UNI_OS_PY="$UNI_OS_HOME/tools/uni_os.py"
export UNI_OS_VAULT="${UNI_OS_VAULT:-$VAULT}"    # lets `uni-os ...` (push, week, heartbeat) find the vault from any folder
export PATH="$HOME/.local/bin:${HOST_DIR:-$HOME/uni-os/modules/vm/host}/bin:$PATH"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[ -n "$TZ_NAME" ] && [ -z "${TZ:-}" ] && export TZ="$TZ_NAME"
mkdir -p "$STATE" 2>/dev/null

# One tmux server per session class, each a systemd user service with its own OOM priority.
TM_RC=(tmux -L uni-rc)        # the Remote Control server (uni-rc.service, OOMScoreAdjust 500)
TM_JOBS=(tmux -L uni-jobs)    # interactive job sessions (uni-jobs.service, 600: killed first)
TM_ROLES=(tmux -L uni-roles)  # persistent role sessions (uni-roles.service, 400: killed last)

have() { command -v "$1" >/dev/null 2>&1; }
yes_() { case "${1:-}" in yes|true|1|on) return 0 ;; *) return 1 ;; esac; }
now_hm() { date '+%Y-%m-%d %H:%M'; }

# The vault is usable: mounted (rclone mode) and the sentinel file is readable. A FUSE mount
# that died can hang a plain `test`, hence the timeout.
vault_ok() {
  if [ "$STORAGE_MODE" = rclone-mount ] && have mountpoint; then
    mountpoint -q "$VAULT" || return 1
  fi
  timeout 30 test -f "$VAULT/$VAULT_SENTINEL"
}

# wait_vault [seconds]: wait for the vault (default UNI_VAULT_WAIT_S or 120 s).
wait_vault() {
  local max="${1:-${UNI_VAULT_WAIT_S:-120}}" t=0
  while ! vault_ok; do
    [ "$t" -ge "$max" ] && return 1
    sleep 5; t=$((t + 5))
  done
  return 0
}

# trim <file> <lines>: keep the last N lines (rewrite, keeps it small).
trim() { [ -f "$1" ] && [ "$(wc -l < "$1")" -gt "$2" ] && tail -n "$2" "$1" > "$1.tmp" && mv "$1.tmp" "$1"; true; }

# trim_in_place <file> <max bytes> <keep bytes>: for files another process keeps open (rclone's
# log): rewrite the same inode instead of replacing it.
trim_in_place() {
  [ -f "$1" ] && [ "$(stat -c %s "$1")" -gt "$2" ] || return 0
  tail -c "$3" "$1" > "$1.tmp" && cat "$1.tmp" > "$1"; rm -f "$1.tmp"
}

# write_in_place <src> <dst>: copy content into an existing file without replacing it, so a
# reader that finds the file by its Drive id keeps working (temp file + rename gives a new id).
write_in_place() { timeout 30 bash -c 'cat "$1" > "$2"' _ "$1" "$2"; }

# ---- agent transcripts (Claude Code) -------------------------------------------------------
# Claude Code keeps a session's transcript in ~/.claude/projects/<cwd with every
# non-alphanumeric character turned into "-">/<session id>.jsonl.
project_dir() { printf '%s/.claude/projects/%s' "$HOME" "$(printf '%s' "$1" | sed 's|[^A-Za-z0-9]|-|g')"; }
transcript_path() {
  local sid="$1" cwd="${2:-$VAULT}" f
  f="$(project_dir "$cwd")/$sid.jsonl"
  if [ ! -f "$f" ]; then             # the folder name rule may change between versions: search
    f=$(find "$HOME/.claude/projects" -maxdepth 2 -name "$sid.jsonl" 2>/dev/null | head -n 1)
    [ -n "$f" ] || f="$(project_dir "$cwd")/$sid.jsonl"
  fi
  printf '%s' "$f"
}

# last_activity <transcript>: epoch of the newest timestamped entry in the last 300 lines,
# empty if none. NEVER the file's mtime: Claude Code touches an open session's transcript
# about hourly, so an mtime-based idle limit never fires.
last_activity() {
  local t
  have jq || return 0
  t=$(tail -n 300 "$1" 2>/dev/null | jq -rR 'fromjson? | .timestamp? | strings' 2>/dev/null | sort | tail -n 1)
  [ -n "$t" ] && date -d "$t" +%s 2>/dev/null
}

# context_k <transcript>: tokens the last turn carried, in thousands (input + cache read +
# cache creation of the last assistant entry). A session re-reads this much on every turn.
context_k() {
  have jq || return 0
  tail -n 400 "$1" 2>/dev/null | jq -r 'select(.type == "assistant") | .message.usage | select(. != null) | ((.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0))' 2>/dev/null | tail -n 1 | awk '{printf "%d", $1 / 1000}'
}

# ---- tmux panes ----------------------------------------------------------------------------
# pane_busy <socket> <target>: mid-turn, or a background shell/agent/task is running. Looks at
# the footer only (last 4 non-empty lines), so conversation text can't match.
pane_busy() {
  tmux -L "$1" capture-pane -p -t "$2" 2>/dev/null | grep -v '^[[:space:]]*$' | tail -n 4 |
    grep -qE 'esc to interrupt|[0-9]+ (shell|agent|task)s?( |$)'
}
# pane_ready <socket> <target>: the normal footer is visible. A one-time dialog (browser
# extension intro, auto-mode question, tips) hides it and blocks the session until answered.
pane_ready() {
  tmux -L "$1" capture-pane -p -t "$2" 2>/dev/null | grep -qE '(bypass permissions|auto mode|accept edits) on'
}
# pane_link <socket> <target>: the claude.ai session link printed by a Remote Control session.
pane_link() {
  tmux -L "$1" capture-pane -p -J -t "$2" 2>/dev/null | grep -o 'https://claude.ai/code/session_[A-Za-z0-9]*' | tail -n 1
}
# RULE: before any `tmux send-keys`, run `capture-pane -p` on that exact target and look.
# An Enter meant for one session once answered a one-time dialog in another one.

# ---- pushes --------------------------------------------------------------------------------
# uni_notify <text> [prio] [click-url]: a DIRECT push (host problems, job failures, dialog
# warnings). Goes through `uni-os push --direct` of the notifications module (no daily budget,
# but its personal-data refusals and quiet windows apply). Always logged in notify.log.
# If the framework's push command is missing, falls back to a plain ntfy call.
uni_notify() {
  local msg="$1" prio="${2:-default}" click="${3:-}" rc
  mkdir -p "$STATE"
  echo "$(now_hm) [$prio] $msg" >> "$STATE/notify.log"
  if [ -n "${UNI_PUSH_FAKE_SEND:-}" ]; then
    printf 'direct\t%s\t%s\t%s\n' "$prio" "$msg" "$click" >> "$UNI_PUSH_FAKE_SEND"; return 0
  fi
  if [ "${UNI_DRY_RUN:-0}" = 1 ]; then echo "dry run: would push: $msg"; return 0; fi
  if [ -f "$UNI_OS_PY" ]; then
    python3 "$UNI_OS_PY" push --direct --source "${UNI_PUSH_SOURCE:-host}" --title "$HOST_NAME" \
      --text "$msg" --prio "$prio" ${click:+--click "$click"} >>"$STATE/notify.log" 2>&1
    rc=$?
    # 10 = held for after a quiet window (released by `push --flush-held`), 13 = refused, 1/2 = failed
    [ "$rc" = 0 ] || echo "$(now_hm) push --direct exit $rc (held, refused or failed: uni-os push --status)" >> "$STATE/notify.log"
    return 0
  fi
  # Fallback only when the framework is missing on this host (never when the gate refused).
  [ "$NOTIFY_PROVIDER" = ntfy ] && [ -s "$NTFY_TOPIC_FILE" ] || return 0
  curl -fsS -m 20 -H "Title: $HOST_NAME" -H "Priority: $prio" -H "Tags: computer" \
    ${click:+-H "Click: $click"} -d "$msg" "$NTFY_SERVER/$(cat "$NTFY_TOPIC_FILE")" >/dev/null \
    || echo "$(now_hm) ntfy send failed" >> "$STATE/notify.log"
}

# outcome_checks_owner: who runs the deterministic outcome checks on this host, printed as "job"
# while the notifications module's job outcome-checks is taken (synced) AND its timer is switched
# on, else "built-in" (bin/outcome-checks, run by `uni-vm health`). Taken but switched off counts as
# built-in, so the checks run exactly once: never twice, never not at all.
outcome_checks_owner() {
  if [ -f "$JOBS_DIR/outcome-checks/job.conf" ] && systemctl --user is-enabled uni-job-outcome-checks.timer >/dev/null 2>&1; then
    echo job
  else
    echo built-in
  fi
}

# uni_push_gate <args of `uni-os push`>: a push through the shared gate (daily budget, gap,
# dedupe per id, quiet hours and windows, never "all good"). The gate honours UNI_DRY_RUN.
uni_push_gate() {
  if [ -n "${UNI_PUSH_FAKE_SEND:-}" ]; then printf 'gate\t%s\n' "$*" >> "$UNI_PUSH_FAKE_SEND"; return 0; fi
  [ -f "$UNI_OS_PY" ] || { echo "push gate missing ($UNI_OS_PY)"; return 1; }
  python3 "$UNI_OS_PY" push "$@"
}

# uni_push_flush: ask the push command to send what it held during a quiet window (as one push).
uni_push_flush() {
  [ -z "${UNI_PUSH_FAKE_SEND:-}" ] && [ -f "$UNI_OS_PY" ] || return 0
  python3 "$UNI_OS_PY" push --flush-held >/dev/null 2>&1 || true
}

# ---- vault frontmatter ---------------------------------------------------------------------
agent_frontmatter() { printf -- '---\ntype: agent\naudience: agent\nupdated: %s\ntags: [uni/agent]\n---\n' "$(date +%F)"; }

# ---- agent CLI -----------------------------------------------------------------------------
is_claude() { [ "$AGENT_CLI" = claude ]; }
agent_logged_in() {
  if is_claude; then
    have jq || return 0
    timeout 30 "$AGENT_BIN" auth status 2>/dev/null | jq -e '.loggedIn == true' >/dev/null 2>&1
  elif [ -n "$AGENT_LOGIN_CHECK_CMD" ]; then
    timeout 30 bash -c "$AGENT_LOGIN_CHECK_CMD" >/dev/null 2>&1
  else
    return 0
  fi
}
# Count agent processes (sessions): Remote Control sessions, SDK sessions, headless runs.
agent_procs() { local n; n=$(pgrep -u "$(id -u)" -f -c -- '(--remote-control=|--sdk-url| -p |remote-control )' 2>/dev/null); echo "${n:-0}"; }
