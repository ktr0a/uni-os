# shellcheck shell=bash
# Test harness for the vm module (sourced by tests/t-*.sh; run them all with run-tests.sh).
# Every test runs against a FAKE home, fake settings and a fake vault in a temp folder: nothing
# here can reach a real service, a real vault or a real push channel (every push goes to a file).
# Never run `uni-vm health` in a test: it restarts services.
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_DIR="$(cd "$TESTS_DIR/../host" && pwd)"
ok=0; bad=0; skipped=0
check() { if [ "$2" = "$3" ]; then ok=$((ok + 1)); else bad=$((bad + 1)); printf 'FAIL %s:\n  want [%s]\n  got  [%s]\n' "$1" "$3" "$2"; fi; }
skip() { skipped=$((skipped + 1)); echo "skip: $1"; }
summary() { echo "$(basename "$0"): $ok ok, $bad failed, $skipped skipped"; [ "$bad" = 0 ]; }
have() { command -v "$1" >/dev/null 2>&1; }

T=$(mktemp -d "${TMPDIR:-/tmp}/uni-vm-test.XXXXXX")
trap 'rm -rf "$T"' EXIT

# Git Bash on Windows: `python3` may be the Store alias; use `python` through a shim.
if ! python3 -c 'import tomllib' >/dev/null 2>&1 && python -c 'import tomllib' >/dev/null 2>&1; then
  mkdir -p "$T/shim"; printf '#!/bin/sh\nexec python "$@"\n' > "$T/shim/python3"; chmod +x "$T/shim/python3"
  export PATH="$T/shim:$PATH"
fi

export HOME="$T/home"
mkdir -p "$HOME"
export UNI_HOST_ENV="$HOME/.config/uni-os/host.env" UNI_STATE_DIR="$T/state" UNI_PUSH_FAKE_SEND="$T/sent"
unset UNI_DRY_RUN UNI_SCHEDULED

# fake_host_env: settings for a host whose vault is a plain local folder ($T/vault).
fake_host_env() {
  mkdir -p "$(dirname "$UNI_HOST_ENV")" "$T/vault/_agent"
  touch "$T/vault/_agent/agent-start.md"
  cat > "$UNI_HOST_ENV" <<EOF
STORAGE_MODE=local
VAULT_MOUNT='$T/vault'
UNI_OS_HOME='$T/no-framework'
HOST_NAME=test-host
TZ_NAME=''
AGENT_BIN='$T/bin/claude'
EOF
}
sent_lines() { [ -f "$T/sent" ] && wc -l < "$T/sent" | tr -d ' ' || echo 0; }
