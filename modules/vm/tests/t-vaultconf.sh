#!/usr/bin/env bash
# vaultconf.py: host.env from the vault config + module defaults, local overrides, set-local,
# rendering of @@KEY@@ templates, the notes-history filter file.
. "$(dirname "$0")/lib.sh"
have python3 || { skip "python3 missing"; summary; exit; }
VC=(python3 "$HOST_DIR/lib/vaultconf.py")
F="$T/fw"; mkdir -p "$F/modules/vm" "$F/modules/core" "$F/modules/unused"
cp "$TESTS_DIR/../module.toml" "$F/modules/vm/module.toml"
printf 'id = "core"\n[defaults.agent]\nprimary = "claude-code"\n' > "$F/modules/core/module.toml"
printf 'id = "unused"\n[defaults.vm]\nhost_alias = "from-a-disabled-module"\n' > "$F/modules/unused/module.toml"
V="$T/vault"; mkdir -p "$V/_agent"
cat > "$V/_agent/uni-os.toml" <<'EOF'
[student]
name = "Alex Example"
[term]
timezone = "Europe/Zurich"
[schedule]
daily_prep = ["17:30", "19:30"]
[vm]
remote_control_name = "Alex host"
history_exclude = ["Private/**"]
[modules]
enabled = ["core", "vm"]
EOF
envf="$T/host.env"

"${VC[@]}" host-env --uni-os "$F" --set "VAULT_MOUNT=$V" --set STORAGE_MODE=local > "$envf"
v() { ( set +u; . "$envf"; eval "printf '%s' \"\${$1}\"" ); }
check "sources cleanly in bash" "$(bash -n "$envf" && echo ok)" ok
check "asked value kept: VAULT_MOUNT" "$(basename "$(v VAULT_MOUNT)")" vault
check "config: OWNER is the first name" "$(v OWNER)" Alex
check "config: timezone" "$(v TZ_NAME)" Europe/Zurich
check "config: user value wins over the module default" "$(v RC_NAME)" "Alex host"
check "module default: HOST_NAME" "$(v HOST_NAME)" uni-vm
check "a disabled module's defaults are ignored" "$(v HOST_NAME | grep -c disabled)" 0
check "module default: machine" "$(v MACHINE_LABEL)" e2-custom-small-4096
check "list joined" "$(v DAILY_PREP_SLOTS)" "17:30, 19:30"
check "agent.primary claude-code -> claude" "$(v AGENT_CLI)" claude
check "hour zero-padded" "$(v RC_UPDATE_HOUR)" 04
check "bool -> yes" "$(v RC_CHROME)" yes

printf 'RC_NAME="Alex host (home)"\n' >> "$envf"
sed -i 's/^JOBS_LIVE=.*/JOBS_LIVE=no    # edited/' "$envf"
"${VC[@]}" host-env --uni-os "$F" --existing "$envf" > "$envf.new"; mv "$envf.new" "$envf"
check "host-only value kept across installs" "$(v JOBS_LIVE)" no
check "local override kept and wins" "$(v RC_NAME)" "Alex host (home)"
"${VC[@]}" set-local "$envf" VAULT_WRITES no >/dev/null
check "set-local: later line wins" "$(v VAULT_WRITES)" no
"${VC[@]}" set-local "$envf" VAULT_WRITES yes >/dev/null
ov() { sed -n '/^# --- local overrides/,$p' "$envf" | grep -c "^$1"; }
check "set-local replaces its own line" "$(ov VAULT_WRITES=yes),$(ov VAULT_WRITES=no)" "1,0"

printf 'Host @@HOST_NAME@@, role @@ROLE@@, odd @@NOPE@@.\n' > "$T/tpl"
"${VC[@]}" render --host-env "$envf" --set EXTRA=1 "$T/tpl" "$T/out" 2>"$T/err"
check "render: values filled, runtime placeholders kept" "$(cat "$T/out")" "Host uni-vm, role @@ROLE@@, odd @@NOPE@@."
check "render: unknown keys reported, runtime ones not" "$(grep -c 'no value for NOPE$' "$T/err"),$(grep -c ROLE "$T/err")" "1,0"

"${VC[@]}" history-filters --vault "$V" --uni-os "$F" > "$T/filters"
check "filters: user exclude" "$(grep -c '^- Private/\*\*$' "$T/filters")" 1
check "filters: private paths (paths.never_open default) excluded, at any depth" "$(grep -c -e '^- \*\*/private/\*\*$' -e '^- private/\*\*$' "$T/filters")" 2
check "filters: the first include comes after every exclude" "$(grep '^[-+] ' "$T/filters" | sed -n '/^+ /,$p' | grep -c '^- ')" 1
printf '[paths]\nnever_open = ["Notes App/PDF/private/**"]\nhandwriting_app_data = "Notes App/Data"\n' >> "$V/_agent/uni-os.toml"
"${VC[@]}" history-filters --vault "$V" --uni-os "$F" > "$T/filters2"
check "filters: paths.never_open from the config" "$(grep -c '^- Notes App/PDF/private/\*\*$' "$T/filters2")" 1
check "filters: the note app's data folder" "$(grep -c '^- Notes App/Data/\*\*$' "$T/filters2")" 1
check "filters: markdown included" "$(grep -c '^+ \*\.md$' "$T/filters")" 1
check "filters: everything else excluded last" "$(tail -n 1 "$T/filters")" "- *"
check "get: a value" "$("${VC[@]}" get vm.remote_control_name --vault "$V" --uni-os "$F")" "Alex host"
check "get: default for a missing key" "$("${VC[@]}" get vm.nope --vault "$V" --uni-os "$F" --default x)" x

echo "== stuck-note threshold: one shared key, vm.* only an alias"
check "no notify key, alias unset (0): built-in default" "$(v INBOX_STUCK_H),$(v TAP_STUCK_H)" "4,14"
printf '[notify]\ninbox_stale_hours = 6\ninbox_stale_hours_taps = 20\n' >> "$V/_agent/uni-os.toml"
"${VC[@]}" host-env --uni-os "$F" --set "VAULT_MOUNT=$V" --set STORAGE_MODE=local > "$envf"
check "notify.inbox_stale_hours[_taps] is the threshold" "$(v INBOX_STUCK_H),$(v TAP_STUCK_H)" "6,20"
sed -i 's/^remote_control_name = "Alex host"$/remote_control_name = "Alex host"\ninbox_stuck_h = 5/' "$V/_agent/uni-os.toml"
"${VC[@]}" host-env --uni-os "$F" --set "VAULT_MOUNT=$V" --set STORAGE_MODE=local > "$envf"
check "a non-zero vm alias still overrides (old configs)" "$(v INBOX_STUCK_H),$(v TAP_STUCK_H)" "5,20"
check "get: alias chain" "$("${VC[@]}" get 'vm.tap_stuck_h|notify.inbox_stale_hours_taps' --vault "$V" --uni-os "$F")" 20
check "outcome prefix default" "$(v OUTCOME_PREFIX)" "Outcome check: "

echo "== the host templates render with no unknown placeholders"
for f in "$HOST_DIR"/agent/*.md "$HOST_DIR"/agent/commands/*.md "$HOST_DIR"/systemd/*.service; do
  "${VC[@]}" render --host-env "$envf" --set HOST_DIR=/x --set RCLONE_EXTRA_FLAGS= "$f" "$T/r.out" 2>"$T/r.err"
  check "render $(basename "$f")" "$(cat "$T/r.err")" ""
done
summary
