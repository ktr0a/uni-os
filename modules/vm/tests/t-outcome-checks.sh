#!/usr/bin/env bash
# outcome-checks on a fake vault with a fake push gate: timing edges, revision notes, stuck
# update notes and Done taps, prep gaps (jq), module switches, plugins, off switch, dry runs.
# Ids and texts must equal those of `uni-os heartbeat outcomes` (tools/uni_os/heartbeat_rules.py):
# prep:tomorrow-missing:<date>, inbox:stuck:<slug of the file name>, prep:gap-open:<date>, and
# no file name or gap text in a push.
# The gate's own decisions (budget, gap, dedupe, quiet windows) belong to the notifications
# module and its tests; here every gate call is one line in $T/sent.
. "$(dirname "$0")/lib.sh"
fake_host_env
echo "DAILY_PREP_SLOTS='17:30, 19:30'" >> "$UNI_HOST_ENV"
OC="$HOST_DIR/bin/outcome-checks"
U="$T/u"
export UNI_OUTCOMES_ROOT="$U" UNI_OUTCOMES_STATE="$T/s" UNI_OUTCOMES_MODULES="core, daily-prep, inbox-sync"
fresh() { rm -rf "$U" "$T/s" "$T/sent"; mkdir -p "$U/_agent/daily-prep" "$U/inbox" "$U/semester/prep"; touch "$U/_agent/agent-start.md"; echo '{"days":{}}' > "$U/_agent/daily-prep/state.json"; }
oc() { UNI_OUTCOMES_NOW="$1" "$OC" "${@:2}"; }

fresh; check "all fine: no output" "$(oc '2026-11-04 18:00' | wc -l | tr -d ' ')" 0; check "all fine: no push" "$(sent_lines)" 0
fresh; check "18:29: prep note not due yet" "$(oc '2026-11-04 18:29' | wc -l | tr -d ' ')" 0
fresh; check "18:30: missing prep note found" "$(oc '2026-11-04 18:30')" "OUTCOME prep:tomorrow-missing:2026-11-05: no prep note for Thu 5 Nov yet"
check "18:30: one gate call with the item and the time" "$(grep -c -- '--item prep:tomorrow-missing:2026-11-05=no prep note for Thu 5 Nov yet --now 2026-11-04 18:30' "$T/sent")" 1
check "gate call names its source and the heartbeat's prefix" "$(grep -c -- '--source outcome-checks --prefix Outcome check: ' "$T/sent")" 1
fresh; touch "$U/semester/prep/prep-2026-11-05-r2.md"; check "a revision note counts" "$(oc '2026-11-04 18:30' | wc -l | tr -d ' ')" 0
fresh; sed -i "s/^DAILY_PREP_SLOTS=.*/DAILY_PREP_SLOTS='20:00'/" "$UNI_HOST_ENV"
check "due time follows the first prep slot: 20:59" "$(oc '2026-11-04 20:59' | wc -l | tr -d ' ')" 0
check "due time follows the first prep slot: 21:00" "$(oc '2026-11-04 21:00' | wc -l | tr -d ' ')" 1
sed -i "s/^DAILY_PREP_SLOTS=.*/DAILY_PREP_SLOTS='17:30, 19:30'/" "$UNI_HOST_ENV"
fresh; check "daily-prep disabled: no prep check" "$(UNI_OUTCOMES_MODULES='core, inbox-sync' oc '2026-11-04 19:00' | wc -l | tr -d ' ')" 0

fresh; touch "$U/semester/prep/prep-2026-11-05.md"
touch -d '2026-11-04 04:00' "$U/inbox/a-update.md"
check "update note 4 h old: stuck" "$(oc '2026-11-04 08:00')" "OUTCOME inbox:stuck:a-update-md: update note waiting in the inbox for over 4 h, not applied by the inbox sync"
check "stuck note: the file name is never in a push" "$(grep -c 'a-update[.]md' "$T/sent")" 0
fresh; touch "$U/semester/prep/prep-2026-11-05.md"; touch -d '2026-11-04 03:00' "$U/inbox/2026-11-04_0300_AD Sheet 6 (v2)-update.md"
check "the id is the heartbeat rules' slug" "$(oc '2026-11-04 08:00' | grep -c '^OUTCOME inbox:stuck:2026-11-04-0300-ad-sheet-6-v2-update-md: ')" 1
# A slug over 60 characters is cut to 53 and gets "-" + 6 hex digits of the file name's SHA-1, so two
# long names sharing their start get two ids. The same literal is checked in tests/test_heartbeat_rules.py
# and modules/inbox-sync/tests (the Python slug()).
fresh; touch "$U/semester/prep/prep-2026-11-05.md"
touch -d '2026-11-04 03:00' "$U/inbox/2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part A-update.md"
touch -d '2026-11-04 03:00' "$U/inbox/2026-11-04_0300_LA exercise sheet 7 corrections and follow-up questions part B-update.md"
out=$(oc '2026-11-04 08:00')
check "long name: cut slug plus a hash, as in the heartbeat rules" "$(printf '%s\n' "$out" | grep -c '^OUTCOME inbox:stuck:2026-11-04-0300-la-exercise-sheet-7-corrections-and-f-2d4bf8: ')" 1
check "two long names sharing their start: two ids" "$(printf '%s\n' "$out" | sed -n 's/^OUTCOME \([^ ]*\): .*/\1/p' | sort -u | wc -l | tr -d ' ')" 2
check "a cut id is at most 60 characters after inbox:stuck:" "$(printf '%s\n' "$out" | sed -n 's/^OUTCOME inbox:stuck:\([^:]*\): .*/\1/p' | awk 'length($0) > 60' | wc -l | tr -d ' ')" 0
a50=$(printf 'a%.0s' $(seq 50))
fresh; touch "$U/semester/prep/prep-2026-11-05.md"
touch -d '2026-11-04 03:00' "$U/inbox/${a50}-update.md" "$U/inbox/${a50}a-update.md"
out=$(oc '2026-11-04 08:00')
check "a slug of exactly 60 characters is unchanged" "$(printf '%s\n' "$out" | grep -c "^OUTCOME inbox:stuck:${a50}-update-md: ")" 1
check "61 characters: cut to 53 and hashed (Python slug: ...a-u-cbbdb7)" "$(printf '%s\n' "$out" | grep -c "^OUTCOME inbox:stuck:${a50}a-u-cbbdb7: ")" 1
fresh; touch "$U/semester/prep/prep-2026-11-05.md"; touch -d '2026-11-04 03:00' "$U/inbox/a-update.md"
echo "INBOX_STUCK_H=4.5" >> "$UNI_HOST_ENV"
check "fractional threshold: 5 h old is stuck" "$(oc '2026-11-04 08:00' | grep -c 'for over 4.5 h')" 1
check "fractional threshold: 4 h old is not" "$(oc '2026-11-04 07:00' | wc -l | tr -d ' ')" 0
sed -i '/^INBOX_STUCK_H=4.5$/d' "$UNI_HOST_ENV"
fresh; touch -d '2026-11-04 05:00' "$U/inbox/a-update.md"; check "update note 3 h old: fine" "$(oc '2026-11-04 08:00' | wc -l | tr -d ' ')" 0
fresh; touch -d '2026-11-04 01:00' "$U/inbox/inbox.md"; check "not an update note: ignored" "$(oc '2026-11-04 08:00' | wc -l | tr -d ' ')" 0
fresh; touch -d '2026-11-04 13:20' "$U/inbox/2026-11-04_1320_cockpit-done-x-update.md"; check "Done tap at 5 h: fine" "$(oc '2026-11-04 18:14' | wc -l | tr -d ' ')" 0
fresh; touch "$U/semester/prep/prep-2026-11-05.md"; touch -d '2026-11-03 18:20' "$U/inbox/2026-11-03_1820_cockpit-undo-x-update.md"
check "Done tap at 13 h overnight: fine" "$(oc '2026-11-04 07:14' | wc -l | tr -d ' ')" 0
check "Done tap at 14 h: stuck" "$(oc '2026-11-04 08:20' | grep -c '^OUTCOME inbox:stuck:2026-11-03-1820-cockpit-undo-x-update-md: Done-tap note waiting in the inbox for over 14 h')" 1
fresh; touch "$U/semester/prep/prep-2026-11-05.md"; touch -d '2026-11-03 18:20' "$U/inbox/2026-11-03_1820_quickview-done-x-update.md"
check "quick-view taps are taps too (14 h)" "$(oc '2026-11-04 07:14' | wc -l | tr -d ' ')" 0
fresh; touch -d '2026-11-04 01:00' "$U/inbox/a-update.md"; check "inbox-sync disabled: no inbox check" "$(UNI_OUTCOMES_MODULES='core' oc '2026-11-04 08:00' | wc -l | tr -d ' ')" 0

if have jq; then
  fresh; echo '{"days":{"2026-11-05":{"gaps":["private text about a friend"],"prep_file_name":"prep-2026-11-05-r2.md"}}}' > "$U/_agent/daily-prep/state.json"
  touch "$U/semester/prep/prep-2026-11-05.md" "$U/semester/prep/prep-2026-11-06.md"
  check "gap first seen: nothing yet" "$(oc '2026-11-04 08:00' | wc -l | tr -d ' ')" 0
  check "gap at 23 h: nothing" "$(oc '2026-11-05 07:00' | wc -l | tr -d ' ')" 0
  check "gap at 24 h: found" "$(oc '2026-11-05 08:00' | grep -c '^OUTCOME prep:gap-open:2026-11-05: prep gap open for over 24 h for Thu 5 Nov$')" 1
  check "gap text never in a push" "$(grep -c 'friend' "$T/sent")" 0
  check "prep file name never in a push" "$(grep -c 'prep-2026' "$T/sent")" 0
  fresh; echo '{"days":{"2026-11-05":{"gaps":["x"]}}}' > "$U/_agent/daily-prep/state.json"; oc '2026-11-04 08:00' >/dev/null
  echo '{"days":{"2026-11-05":{"gaps":[]}}}' > "$U/_agent/daily-prep/state.json"; oc '2026-11-04 09:00' >/dev/null
  echo '{"days":{"2026-11-05":{"gaps":["y"]}}}' > "$U/_agent/daily-prep/state.json"
  check "gap closed, then a new one: the clock restarts" "$(oc '2026-11-05 08:30' | grep -c gap-)" 0
  fresh; echo 'not json' > "$U/_agent/daily-prep/state.json"; oc '2026-11-04 08:00' >/dev/null; check "broken state file: no crash" "$?" 0
else
  skip "prep-gap checks need jq"
fi

fresh; mkdir -p "$(dirname "$UNI_HOST_ENV")/outcome-checks.d"
cat > "$(dirname "$UNI_HOST_ENV")/outcome-checks.d/demo" <<'EOF'
#!/bin/sh
echo "OUTCOME custom-1: a module check found something"
echo "random noise"
echo "OUTCOME cards:next-bonus-past:ad: next bonus date is in the past"
EOF
chmod +x "$(dirname "$UNI_HOST_ENV")/outcome-checks.d/demo"; touch "$U/semester/prep/prep-2026-11-05.md"
check "plugin lines are included as outcome:<key>, noise ignored" "$(oc '2026-11-04 08:00' | head -n 1)" "OUTCOME outcome:custom-1: a module check found something"
check "a plugin key with a colon is the id as it is" "$(oc '2026-11-04 08:00' | tail -n 1)" "OUTCOME cards:next-bonus-past:ad: next bonus date is in the past"
rm -rf "$(dirname "$UNI_HOST_ENV")/outcome-checks.d"

fresh; mkdir -p "$T/s"; touch "$T/s/off"; check "off switch" "$(oc '2026-11-04 19:00' | wc -l | tr -d ' ')" 0
fresh; rm -f "$U/_agent/agent-start.md"; check "vault missing: quiet (health alerts about it)" "$(oc '2026-11-04 19:00' | wc -l | tr -d ' ')" 0
fresh; check "dry run: prints, sends nothing" "$(oc '2026-11-04 19:00' --dry-run | wc -l | tr -d ' '),$(sent_lines)" "1,0"
summary
