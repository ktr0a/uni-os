#!/usr/bin/env bash
# deploy.sh: push the framework copy from the laptop to the always-on host and run its installer
# (Git Bash on Windows, experimental). Use it when the host's copy is NOT a git clone; a git clone
# is updated on the host with `uni-vm update` instead.
#   bash modules/vm/laptop/deploy.sh [--dry-run] [--force] [--restart-rc]
# 1. Drift stop: the host keeps a manifest of what the last deploy sent (~/uni-os/.deployed.md5).
#    If a file there changed since (a hot fix made on the host), the deploy lists it and stops
#    with exit 3, because it would overwrite that change. Bring the change into your laptop copy
#    first, or repeat with --force.
# 2. Sends the framework (no .git, node_modules, examples, caches) as one tar archive, base64
#    through vm.sh (works for both transports), unpacks it over ~/uni-os (adds and overwrites
#    only: a file deleted on the laptop stays on the host, so switch a removed job off first),
#    writes the new manifest and runs host/install-user.sh --non-interactive. The installer is
#    safe to re-run and restarts no service.
# 3. --restart-rc: restarts the Remote Control server afterwards. That ENDS open sessions on the
#    host: only with the student's go. Changes to rc-loop or unit files apply only after it.
# Settings: ~/.config/uni-os/laptop.env (FRAMEWORK_DIR, REMOTE_DIR, HOST_VAULT_MOUNT, HOST_DRIVE_REMOTE
# and the vm.sh settings). HOST_VAULT_MOUNT / HOST_DRIVE_REMOTE (vm.mount_path / vm.drive_remote, when
# they aren't the defaults ~/Uni and uni-drive) go to the installer as --vault / --remote: on the first
# install the vault isn't mounted yet, so the installer can't read them from the vault config.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENVF="${UNI_LAPTOP_ENV:-$HOME/.config/uni-os/laptop.env}"
FRAMEWORK_DIR=""; REMOTE_DIR="uni-os"; HOST_VAULT_MOUNT=""; HOST_DRIVE_REMOTE=""
# shellcheck disable=SC1090
[ -f "$ENVF" ] && . "$ENVF"
FRAMEWORK_DIR="${FRAMEWORK_DIR:-$(cd "$HERE/../../.." && pwd)}"
VM=(bash "$HERE/vm.sh")
FORCE=no; RESTART=no; DRY=no
for a in "$@"; do case "$a" in --force) FORCE=yes ;; --restart-rc) RESTART=yes ;; --dry-run) DRY=yes ;; *) echo "unknown option $a"; exit 2 ;; esac; done
[ -f "$FRAMEWORK_DIR/modules/vm/host/install-user.sh" ] || { echo "no framework at $FRAMEWORK_DIR (set FRAMEWORK_DIR in $ENVF)"; exit 2; }
INSTALL_OPTS="--non-interactive"
[ -n "$HOST_VAULT_MOUNT" ] && INSTALL_OPTS+=" --vault $(printf '%q' "$HOST_VAULT_MOUNT")"
[ -n "$HOST_DRIVE_REMOTE" ] && INSTALL_OPTS+=" --remote $(printf '%q' "$HOST_DRIVE_REMOTE")"

if "${VM[@]}" "[ -d ~/$REMOTE_DIR/.git ] && echo GIT-CLONE" </dev/null | grep -q GIT-CLONE; then
  if [ "$FORCE" != yes ]; then
    echo "~/$REMOTE_DIR on the host is a git clone: update it there with 'uni-vm update' (or repeat with --force)"; exit 2
  fi
fi
drift=$("${VM[@]}" "cd ~/$REMOTE_DIR 2>/dev/null && [ -f .deployed.md5 ] && md5sum -c --quiet .deployed.md5 2>/dev/null | cut -d: -f1" </dev/null || true)
if [ -n "$drift" ] && [ "$FORCE" != yes ]; then
  echo "Changed on the host since the last deploy, so a deploy would overwrite them:"
  echo "$drift" | sed 's/^/  /'
  echo "Bring those changes into $FRAMEWORK_DIR first, or repeat with --force."
  exit 3
fi
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
tar --force-local -C "$FRAMEWORK_DIR" --exclude=./.git --exclude='*/node_modules' --exclude=./examples \
  --exclude='__pycache__' --exclude='*.pyc' -czf "$TMP/uni-os.tgz" .
echo "archive: $(tar --force-local -tzf "$TMP/uni-os.tgz" | grep -vc '/$') files, $(( $(wc -c < "$TMP/uni-os.tgz") / 1024 )) KB"
echo "installer: install-user.sh $INSTALL_OPTS"
if [ "$DRY" = yes ]; then echo "dry run: nothing sent"; exit 0; fi
base64 -w0 "$TMP/uni-os.tgz" | "${VM[@]}" "base64 -d > /tmp/uni-os-deploy.tgz"
"${VM[@]}" "mkdir -p ~/$REMOTE_DIR && tar -C ~/$REMOTE_DIR -xzf /tmp/uni-os-deploy.tgz \
  && (cd ~/$REMOTE_DIR && tar -tzf /tmp/uni-os-deploy.tgz | grep -v '/\$' | sed 's|^\./||' | tr '\n' '\0' | xargs -0 md5sum > .deployed.md5) \
  && rm -f /tmp/uni-os-deploy.tgz && bash ~/$REMOTE_DIR/modules/vm/host/install-user.sh $INSTALL_OPTS" </dev/null
if [ "$RESTART" = yes ]; then
  "${VM[@]}" 'systemctl --user restart uni-rc.service && sleep 20 && uni-vm status | head -n 4' </dev/null
fi
