#!/usr/bin/env bash
# bootstrap-root.sh: base system for the Uni OS always-on host (run as root; safe to re-run).
#
# Works on Ubuntu 24.04 LTS: a cloud VM (Google Cloud by default, any provider) or WSL2 Ubuntu
# on a spare Windows laptop (detected automatically, or --wsl). Steps:
#   1. the Linux user (created if missing; on WSL with password-less sudo, so the owner never
#      needs a Linux password); WSL: /etc/wsl.conf with systemd on, default user, hostname
#   2. timezone (the vault config's term.timezone)
#   3. packages: tmux git curl jq ripgrep fuse3 python3 (+venv, pip, python-is-python3) poppler-utils
#      sqlite3 htop ncdu unattended-upgrades ...
#   4. FUSE user_allow_other (needed for --allow-other mounts)
#   5. memory: compressed RAM swap (zram, half of RAM, zstd, priority 100) + a 2 GB swap file
#      (priority 10); on WSL swap comes from .wslconfig instead
#   6. sysctl: swappiness 60, vfs_cache_pressure 100, inotify watches 524288
#   7. Node.js (NodeSource, major NODE_MAJOR, default 22), rclone (official installer),
#      Google Chrome stable (for the headless `uni-browse`; amd64 only)
#   8. linger for the user (user services run with nobody logged in)
#   9. unattended security upgrades; automatic reboot at 04:30 only when a kernel needs it
#      (never on WSL: a reboot inside WSL just stops the distro)
# The agent CLI is NOT installed here: install it as the user (INSTALL.md, step "Agent login").
#
# Usage: sudo bash bootstrap-root.sh --user <linux-user> [--tz Europe/Zurich] [--hostname uni-home]
#                                    [--wsl | --no-wsl] [--no-chrome] [--swap-gb 2]
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
USER_NAME="${SUDO_USER:-}"; TZ_NAME=""; HOSTNAME_WSL="uni-home"; WSL=auto; CHROME=yes; SWAP_GB=2
NODE_MAJOR="${NODE_MAJOR:-22}"
while [ $# -gt 0 ]; do
  case "$1" in
    --user) USER_NAME="$2"; shift 2 ;;
    --tz) TZ_NAME="$2"; shift 2 ;;
    --hostname) HOSTNAME_WSL="$2"; shift 2 ;;
    --wsl) WSL=yes; shift ;;
    --no-wsl) WSL=no; shift ;;
    --no-chrome) CHROME=no; shift ;;
    --swap-gb) SWAP_GB="$2"; shift 2 ;;
    *) echo "unknown option $1 (see the header of this script)"; exit 2 ;;
  esac
done
[ "$(id -u)" = 0 ] || { echo "run as root: sudo bash $0 --user <name>"; exit 2; }
[ -n "$USER_NAME" ] && [ "$USER_NAME" != root ] || { echo "--user <linux-user> is required (not root)"; exit 2; }
if [ "$WSL" = auto ]; then grep -qi microsoft /proc/version 2>/dev/null && WSL=yes || WSL=no; fi
log() { echo "[bootstrap-root] $*"; }
log "user $USER_NAME, WSL=$WSL"

# 1. user
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash -G sudo "$USER_NAME"
  log "created user $USER_NAME"
fi
if [ "$WSL" = yes ]; then
  echo "$USER_NAME ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/90-$USER_NAME" && chmod 440 "/etc/sudoers.d/90-$USER_NAME"
  log "/etc/wsl.conf: systemd on, default user $USER_NAME, hostname $HOSTNAME_WSL, Windows PATH not appended"
  cat > /etc/wsl.conf <<EOF
[boot]
systemd=true

[user]
default=$USER_NAME

[network]
hostname=$HOSTNAME_WSL
generateHosts=true

[interop]
enabled=true
appendWindowsPath=false
EOF
fi

# 2. timezone
if [ -n "$TZ_NAME" ]; then
  log "timezone -> $TZ_NAME"
  if [ -d /run/systemd/system ] && timedatectl set-timezone "$TZ_NAME" 2>/dev/null; then :
  else ln -sf "/usr/share/zoneinfo/$TZ_NAME" /etc/localtime && echo "$TZ_NAME" > /etc/timezone; fi
else
  log "no --tz given: timezone stays $(cat /etc/timezone 2>/dev/null || echo unknown) (jobs run in the host's local time!)"
fi

# 3. packages
log "apt packages"
apt-get update -qq
apt-get upgrade -y -qq
PKGS=(tmux git curl jq ripgrep fuse3 unzip zip python3 python3-venv python3-pip python-is-python3
      htop ncdu poppler-utils sqlite3 ca-certificates gnupg unattended-upgrades bc procps util-linux)
[ "$WSL" = no ] && PKGS+=(systemd-zram-generator needrestart)
apt-get install -y -qq "${PKGS[@]}" >/dev/null

# 4. FUSE
log "fuse: user_allow_other"
grep -q '^user_allow_other' /etc/fuse.conf || echo 'user_allow_other' >> /etc/fuse.conf

# 5. memory
if [ "$WSL" = no ]; then
  log "zram (compressed RAM swap, half of RAM) + ${SWAP_GB} GB swap file fallback"
  cat > /etc/systemd/zram-generator.conf <<'EOF'
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
EOF
  systemctl daemon-reload
  systemctl start systemd-zram-setup@zram0.service || true
  if [ ! -f /swapfile ]; then
    fallocate -l "${SWAP_GB}G" /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw,pri=10 0 0' >> /etc/fstab
  fi
  swapon -a || true
else
  log "WSL: no zram, swap comes from .wslconfig"
fi

# 6. sysctl
cat > /etc/sysctl.d/90-uni-os.conf <<'EOF'
vm.swappiness = 60
vm.vfs_cache_pressure = 100
fs.inotify.max_user_watches = 524288
EOF
sysctl --system >/dev/null 2>&1 || true

# 7. Node.js, rclone, Chrome
log "Node.js $NODE_MAJOR (NodeSource)"
if ! command -v node >/dev/null || ! node -v | grep -q "^v$NODE_MAJOR"; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi
log "rclone (official installer)"
command -v rclone >/dev/null || curl -fsSL https://rclone.org/install.sh | bash >/dev/null
if [ "$CHROME" = yes ]; then
  if [ "$(dpkg --print-architecture)" = amd64 ]; then
    log "Google Chrome stable (headless, for uni-browse)"
    if ! command -v google-chrome >/dev/null; then
      curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg --yes
      echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list
      apt-get update -qq
      apt-get install -y -qq google-chrome-stable >/dev/null
    fi
  else
    log "not amd64: no Google Chrome; uni-browse needs a chromium build (edit bin/uni-browse)"
  fi
fi

# 8. linger
if [ -d /run/systemd/system ]; then
  log "user services survive logout (linger) for $USER_NAME"
  loginctl enable-linger "$USER_NAME"
else
  log "systemd is not running yet (WSL): run 'wsl --terminate <distro>' in Windows, start it again, re-run this script"
fi

# 9. updates
if [ "$WSL" = no ]; then
  log "unattended security upgrades; automatic reboot at 04:30 only when a kernel needs it"
  cat > /etc/apt/apt.conf.d/52uni-os-reboot <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";
EOF
else
  log "unattended security upgrades, never an automatic reboot (WSL)"
  cat > /etc/apt/apt.conf.d/52uni-os-reboot <<'EOF'
Unattended-Upgrade::Automatic-Reboot "false";
EOF
fi

log "done: $(node -v 2>/dev/null), $(rclone version 2>/dev/null | head -n 1), $(google-chrome --version 2>/dev/null || echo 'no Chrome')"
log "next, as $USER_NAME: install the agent CLI, configure rclone, then run modules/vm/host/install-user.sh (INSTALL.md)"
