#!/usr/bin/env bash
# install-user.sh: install or update the Uni OS host setup for the current user.
#
# Safe to re-run (deploys and `uni-vm update` run it every time). It never RESTARTS a running
# service (that would end open sessions); it only starts what is not running yet. Steps:
#   0. framework copy: with --repo URL (or UNI_OS_REPO_URL in host.env) it clones the public repo
#      to ~/uni-os or pulls it (fast-forward only) and continues with the fresh copy; without a
#      URL the copy came from the laptop (modules/vm/laptop/deploy.sh) and is used as it is
#   1. ~/.config/uni-os/host.env: on the first run it asks where the vault goes (mount path,
#      rclone remote, storage mode); later runs keep those answers
#   2. links in ~/.local/bin (uni-vm, role-sessions, uni-browse, vault-history, uni-os), PATH and
#      an interactive `uni-vm status` on login in ~/.bashrc, ~/scratch
#   3. systemd user units rendered from host/systemd/ (uni-drive, uni-rc, uni-jobs, uni-roles, uni-job@)
#   4. starts the vault mount (if the rclone remote exists) and waits for the sentinel file
#   5. refreshes host.env from the vault config (_agent/uni-os.toml + module defaults), writes
#      the notes-history filter file
#   6. agent config: machine notes (~/.config/uni-os/agent/AGENTS.md; Claude Code: ~/.claude/CLAUDE.md
#      imports it), slash commands, the job header and the role start prompt, settings.json keys
#      (bypass permissions, cross-session messages accepted, the brief-nudge hook)
#   7. `uni-vm jobs sync --accept-new`: jobs from the vault, timers, DEFAULT_MODE of new jobs
#   8. enables uni-jobs and uni-roles (started), uni-rc (enabled; its very first start needs one
#      interactive "y": systemctl --user start uni-rc, then uni-vm attach)
# Usage: bash ~/uni-os/modules/vm/host/install-user.sh [--non-interactive] [--repo URL] [--no-pull]
#          [--vault PATH] [--remote NAME] [--storage rclone-mount|local] [--trial] [--start-rc]
#   --trial: a second host next to a live one (home-server trial): read-only mount, every job
#            timer off, never writes _agent/vm/*, its own Remote Control name. Undo with
#            `uni-vm hostenv set JOBS_LIVE yes` etc. (HOME-SERVER.md, "Trial").
set -euo pipefail
HOST_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SELF_HOME="$(cd "$HOST_DIR/../../.." && pwd)"
CONF="$HOME/.config/uni-os"; ENVF="$CONF/host.env"
VC=(python3 "$HOST_DIR/lib/vaultconf.py")
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
INTERACTIVE=yes; REPO=""; PULL=yes; TRIAL=no; START_RC=no
declare -a SETS=()
ORIG_ARGS=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    --non-interactive) INTERACTIVE=no; shift ;;
    --repo) REPO="$2"; shift 2 ;;
    --no-pull) PULL=no; shift ;;
    --vault) SETS+=("VAULT_MOUNT=$2"); shift 2 ;;
    --remote) SETS+=("DRIVE_REMOTE=$2"); shift 2 ;;
    --storage) SETS+=("STORAGE_MODE=$2"); shift 2 ;;
    --trial) TRIAL=yes; shift ;;
    --start-rc) START_RC=yes; shift ;;
    *) echo "unknown option $1 (see the header of this script)"; exit 2 ;;
  esac
done
[ -t 0 ] && [ -t 1 ] || INTERACTIVE=no
log() { echo "[install-user] $*"; }
have() { command -v "$1" >/dev/null 2>&1; }
for t in python3 jq tmux git; do have "$t" || { echo "missing $t: run bootstrap-root.sh first"; exit 2; }; done
mkdir -p "$CONF" "$HOME/.local/bin" "$HOME/.config/systemd/user" "$HOME/.local/state/uni-os" "$HOME/scratch"

# ---- 0. framework copy -----------------------------------------------------------------------
[ -z "$REPO" ] && [ -f "$ENVF" ] && REPO=$(sed -n -E "s/^UNI_OS_REPO_URL='?([^' ]*)'?.*/\1/p" "$ENVF" | tail -n 1)
TARGET="$HOME/uni-os"
if [ -n "$REPO" ] && [ "$PULL" = yes ]; then
  if [ ! -d "$TARGET/.git" ]; then
    [ -e "$TARGET" ] && { echo "$TARGET exists but is not a git clone: move it away or drop --repo"; exit 2; }
    log "cloning $REPO -> $TARGET"; git clone -q "$REPO" "$TARGET"
  else
    log "updating $TARGET (git pull --ff-only)"; git -C "$TARGET" pull -q --ff-only || log "WARN: pull failed; using the copy as it is"
  fi
  # continue with the installer of the fresh copy (it may have changed)
  exec bash "$TARGET/modules/vm/host/install-user.sh" "${ORIG_ARGS[@]}" --no-pull
fi
[ -n "$REPO" ] && SETS+=("UNI_OS_REPO_URL=$REPO")
SETS+=("UNI_OS_HOME=$SELF_HOME")
chmod +x "$HOST_DIR"/bin/* "$HOST_DIR"/*.sh 2>/dev/null || true

# ---- 1. host.env -------------------------------------------------------------------------------
ask() {  # ask KEY "question" default
  local key="$1" q="$2" def="$3" a=""
  if [ "$INTERACTIVE" = yes ]; then read -r -p "$q [$def]: " a; fi
  SETS+=("$key=${a:-$def}")
}
if [ ! -f "$ENVF" ]; then
  log "first install on this host: a few questions (Enter keeps the default)"
  has_set() { local s; for s in "${SETS[@]}"; do [ "${s%%=*}" = "$1" ] && return 0; done; return 1; }
  has_set VAULT_MOUNT || ask VAULT_MOUNT "Where should the vault appear on this host" "$HOME/Uni"
  has_set STORAGE_MODE || ask STORAGE_MODE "Storage: rclone-mount (Google Drive, OneDrive, ... via rclone) or local (a folder synced some other way)" "rclone-mount"
  has_set DRIVE_REMOTE || ask DRIVE_REMOTE "Name of the rclone remote whose root is the vault folder" "uni-drive"
  ask AGENT_CLI "Agent CLI on this host: claude (Claude Code, the tested one) or other" "claude"
fi
if [ "$TRIAL" = yes ]; then
  SETS+=("JOBS_LIVE=no" "VAULT_WRITES=no" "DRIVE_READ_ONLY=yes")
fi
write_env() {
  local args=()
  local s; for s in "${SETS[@]}"; do args+=(--set "$s"); done
  "${VC[@]}" host-env --uni-os "$SELF_HOME" ${1:+--vault "$1"} $([ -f "$ENVF" ] && echo --existing "$ENVF") "${args[@]}" > "$ENVF.tmp"
  mv "$ENVF.tmp" "$ENVF"; chmod 600 "$ENVF"
}
write_env ""
# shellcheck disable=SC1090
. "$HOST_DIR/lib/common.sh"
if [ "$TRIAL" = yes ]; then   # its own Remote Control name next to the live host (local overrides)
  case "$RC_NAME" in *"(trial)") ;; *) "${VC[@]}" set-local "$ENVF" RC_NAME "$RC_NAME (trial)" >/dev/null
    "${VC[@]}" set-local "$ENVF" RC_PREFIX "$RC_PREFIX-trial" >/dev/null ;; esac
  . "$HOST_DIR/lib/common.sh"
fi
log "host.env: $ENVF (vault $VAULT, storage $STORAGE_MODE, agent $AGENT_CLI)"

# ---- 2. links, PATH ---------------------------------------------------------------------------
for b in uni-vm role-sessions uni-browse vault-history run-job doctor outcome-checks; do ln -sf "$HOST_DIR/bin/$b" "$HOME/.local/bin/$b"; done
printf '#!/bin/sh\n# the Uni OS CLI of the framework copy on this host\nexec python3 "%s/tools/uni_os.py" "$@"\n' "$SELF_HOME" > "$HOME/.local/bin/uni-os"
chmod +x "$HOME/.local/bin/uni-os"
grep -q '# uni-os host' "$HOME/.bashrc" 2>/dev/null || cat >> "$HOME/.bashrc" <<'EOF'
# uni-os host: PATH, and the host's health when logging in interactively
export PATH="$HOME/.local/bin:$PATH"
[ -t 1 ] && command -v uni-vm >/dev/null && uni-vm status
EOF

# ---- 3. systemd units ---------------------------------------------------------------------------
UNITS="$HOME/.config/systemd/user"
extra=""
yes_ "$DRIVE_READ_ONLY" && extra="$extra --read-only"
yes_ "$RCLONE_ALLOW_OTHER" && extra="$extra --allow-other"
for u in "$HOST_DIR"/systemd/*.service; do
  n=$(basename "$u")
  [ "$n" = uni-drive.service ] && [ "$STORAGE_MODE" != rclone-mount ] && { rm -f "$UNITS/$n"; continue; }
  "${VC[@]}" render --host-env "$ENVF" --set "HOST_DIR=$HOST_DIR" --set "RCLONE_EXTRA_FLAGS=$extra" "$u" "$UNITS/$n"
done
systemctl --user daemon-reload
log "systemd user units written to $UNITS"

# ---- 4. the vault -------------------------------------------------------------------------------
WAIT=120
if [ "$STORAGE_MODE" = rclone-mount ]; then
  if rclone listremotes 2>/dev/null | grep -qx "$DRIVE_REMOTE:"; then
    systemctl --user enable uni-drive.service >/dev/null 2>&1
    systemctl --user is-active -q uni-drive.service || systemctl --user start uni-drive.service
  else
    log "no rclone remote \"$DRIVE_REMOTE\" yet: do the rclone login (INSTALL.md, step 8), then re-run this script"
    WAIT=0
  fi
fi
# ---- 5. settings from the vault config -------------------------------------------------------------
if wait_vault "$WAIT"; then
  log "vault OK: $VAULT"
  write_env "$VAULT"
  . "$HOST_DIR/lib/common.sh"
  "${VC[@]}" history-filters --vault "$VAULT" --uni-os "$SELF_HOME" > "$CONF/history-filters.txt"
  [ -n "$TZ_NAME" ] && [ "$(cat /etc/timezone 2>/dev/null)" != "$TZ_NAME" ] && \
    log "WARN: the vault says timezone $TZ_NAME but the host uses $(cat /etc/timezone 2>/dev/null): sudo timedatectl set-timezone $TZ_NAME"
else
  log "WARN: the vault is not readable ($VAULT/$VAULT_SENTINEL): host.env uses defaults; re-run once the mount works"
fi

# ---- 6. agent config -----------------------------------------------------------------------------
mkdir -p "$AGENT_FILES/commands"
for f in AGENTS.md job-header.md role-start-prompt.md; do
  "${VC[@]}" render --host-env "$ENVF" --set "HOST_DIR=$HOST_DIR" "$HOST_DIR/agent/$f" "$AGENT_FILES/$f"
done
for f in "$HOST_DIR"/agent/commands/*.md; do
  "${VC[@]}" render --host-env "$ENVF" --set "HOST_DIR=$HOST_DIR" "$f" "$AGENT_FILES/commands/$(basename "$f")"
done
mkdir -p "$ROLES_CONF_DIR"
if is_claude; then
  mkdir -p "$HOME/.claude/commands"
  if [ -f "$HOME/.claude/CLAUDE.md" ] && ! grep -q 'uni-os host' "$HOME/.claude/CLAUDE.md"; then
    cp "$HOME/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md.before-uni-os"; log "kept your old ~/.claude/CLAUDE.md as CLAUDE.md.before-uni-os"
  fi
  "${VC[@]}" render --host-env "$ENVF" --set "HOST_DIR=$HOST_DIR" "$HOST_DIR/agent/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
  cp "$AGENT_FILES"/commands/*.md "$HOME/.claude/commands/"
  S="$HOME/.claude/settings.json"; [ -f "$S" ] || echo '{}' > "$S"
  # Every session on the host in the same permission mode: otherwise cross-session messages
  # wait for an approval nobody gives. NOTE: a running session can pick up a changed settings
  # file without a dialog, so treat every install as reaching live sessions.
  jq --arg mode "$AGENT_PERMISSION_MODE" --arg model "$AGENT_DEFAULT_MODEL" --arg hook "$HOST_DIR/bin/brief-nudge" '
    . + {permissions: ((.permissions // {}) + {defaultMode: $mode}),
         skipDangerousModePermissionPrompt: true,
         autoUpdatesChannel: (.autoUpdatesChannel // "stable"),
         model: $model,
         crossSessionInbound: "accept"}
    | .hooks.UserPromptSubmit = [{hooks: [{type: "command", command: $hook, timeout: 10}]}]' "$S" > "$S.tmp" && mv "$S.tmp" "$S"
  have claude || [ -x "$AGENT_BIN" ] || log "Claude Code is not installed yet: curl -fsSL https://claude.ai/install.sh | bash   then: claude auth login"
else
  [ -d "$HOME/.codex" ] && cp "$AGENT_FILES/AGENTS.md" "$HOME/.codex/AGENTS.md" && log "machine notes -> ~/.codex/AGENTS.md"
  [ -d "$HOME/.gemini" ] && cp "$AGENT_FILES/AGENTS.md" "$HOME/.gemini/GEMINI.md" && log "machine notes -> ~/.gemini/GEMINI.md"
  log "agent $AGENT_CLI: set AGENT_HEADLESS_CMD and AGENT_INTERACTIVE_CMD (uni-vm hostenv set ...); untested path"
fi

# ---- 7. jobs ------------------------------------------------------------------------------------
"$HOST_DIR/bin/uni-vm" jobs sync --accept-new || log "jobs sync skipped (vault not available)"

# ---- 8. services ----------------------------------------------------------------------------------
systemctl --user enable uni-jobs.service uni-roles.service >/dev/null 2>&1
systemctl --user is-active -q uni-jobs.service || systemctl --user start uni-jobs.service
systemctl --user is-active -q uni-roles.service || systemctl --user start uni-roles.service
if is_claude && yes_ "$RC_ENABLED"; then
  systemctl --user enable uni-rc.service >/dev/null 2>&1
  if [ "$START_RC" = yes ] && ! systemctl --user is-active -q uni-rc.service; then systemctl --user start uni-rc.service; fi
  systemctl --user is-active -q uni-rc.service || log "Remote Control: systemctl --user start uni-rc.service, then answer the one question with: uni-vm attach (detach: Ctrl-b d)"
else
  systemctl --user disable uni-rc.service >/dev/null 2>&1 || true
fi
log "done"
"$HOST_DIR/bin/uni-vm" status || true
