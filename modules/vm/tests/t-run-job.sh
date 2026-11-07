#!/usr/bin/env bash
# run-job with a fake agent CLI, fake vault and fake push: command and agent jobs, dry runs,
# PRECHECK, NEEDS_VAULT, the job environment, RUNTIME, the DATES guard, the per-job lock, the
# shared/exclusive agent lock (fd 7), failure pushes, log footer and pruning, failover mode.
# Needs flock (Linux, WSL); skips itself where flock is missing (Git Bash on Windows).
. "$(dirname "$0")/lib.sh"
if ! have flock; then skip "run-job tests: no flock here (run them on the host or in WSL)"; summary; exit; fi
fake_host_env
echo "JOB_LOGS_KEEP=3" >> "$UNI_HOST_ENV"
export UNI_JOBS_DIR="$T/jobs" UNI_VAULT_WAIT_S=0 UNI_FAILOVER_RECHECK_S=0
mkdir -p "$T/bin" "$T/jobs"
cat > "$T/bin/claude" <<'EOF'
#!/usr/bin/env bash
# fake agent CLI: prints how it was called, then sleeps FAKE_SLEEP seconds
prompt=""; args=()
while [ $# -gt 0 ]; do case "$1" in -p) prompt="$2"; shift 2 ;; *) args+=("$1"); shift ;; esac; done
echo "start $(date +%s.%N) dry=${UNI_DRY_RUN:-0} fd7=$([ -e /proc/self/fd/7 ] && echo open || echo closed)"
echo "args: ${args[*]}"
echo "prompt-first-line: $(printf '%s' "$prompt" | head -n 1 | cut -c1-40)"
printf '%s' "$prompt" | grep -q 'the-task-text' && echo "task: included"
sleep "${FAKE_SLEEP:-0}"; echo "end $(date +%s.%N)"
EOF
chmod +x "$T/bin/claude"
RJ="$HOST_DIR/bin/run-job"
mk() { mkdir -p "$T/jobs/$1"; printf 'NEEDS_VAULT=no\nTIMEOUT_MIN=2\n%s\n' "$2" > "$T/jobs/$1/job.conf"; echo "the-task-text" > "$T/jobs/$1/prompt.md"; }
lastlog() { cat "$(ls -1t "$UNI_STATE_DIR/jobs/$1"/*.log | head -n 1)"; }
jl() { grep -F " | $1 | " "$UNI_STATE_DIR/jobs.log" | tail -n 1 | cut -d'|' -f3- | sed 's/^ //'; }

echo "== command jobs"
mk cmd 'KIND=command
COMMAND="echo hello-from-job"'
"$RJ" cmd >/dev/null; check "exit 0" "$?" 0
check "output in the log" "$(lastlog cmd | grep -c hello-from-job)" 1
check "log ends with the exit footer" "$(lastlog cmd | tail -n 1 | sed -E 's/[0-9]+s$/Ns/')" "# exit 0 after Ns"
check "jobs.log line" "$(jl cmd | cut -d'|' -f1 | sed 's/ $//')" "exit 0"
mk quiet 'KIND=command
QUIET_OK=yes
COMMAND="true"'
"$RJ" quiet; check "QUIET_OK: no jobs.log line on success" "$(grep -c ' | quiet | ' "$UNI_STATE_DIR/jobs.log")" 0
mk fail7 'KIND=command
COMMAND="exit 7"'
"$RJ" fail7; check "failure: exit code passed on" "$?" 7
check "failure: one direct high push" "$(grep -c $'^direct\thigh\tJob fail7 failed' "$T/sent")" 1
mk env 'KIND=command
COMMAND="echo \"env:\$UNI_JOB|\$UNI_HOST|\$(basename \$UNI_VAULT)\""'
"$RJ" env; check "job environment" "$(lastlog env | grep '^env:')" "env:env|vm|vault"
for i in 1 2 3 4 5; do "$RJ" cmd >/dev/null; sleep 1; done
check "only JOB_LOGS_KEEP logs kept" "$(ls -1 "$UNI_STATE_DIR/jobs/cmd"/*.log | wc -l | tr -d ' ')" 3

echo "== dry runs"
mk touchy "KIND=command
COMMAND=\"touch '$T/touched'\""
"$RJ" touchy --dry-run; check "DRY_OK=no: command not run" "$([ -e "$T/touched" ] && echo ran || echo not-run)" not-run
check "DRY_OK=no: says what it would run" "$(lastlog touchy | grep -c 'dry run: would run')" 1
check "dry run marked in jobs.log" "$(jl touchy | cut -d'|' -f1 | sed 's/ $//')" "dry run"
check "dry-run log name" "$(ls "$UNI_STATE_DIR/jobs/touchy" | grep -c -- '-dry\.log$')" 1
mk dryok 'KIND=command
DRY_OK=yes
COMMAND="echo args:"'
"$RJ" dryok --dry-run; check "DRY_OK=yes: --dry-run appended" "$(lastlog dryok | grep '^args:')" "args: --dry-run"
mk dryfail 'KIND=command
DRY_OK=yes
COMMAND="exit 5;"'
before=$(sent_lines); "$RJ" dryfail --dry-run; check "a failing dry run pushes nothing" "$(sent_lines)" "$before"

echo "== PRECHECK and the vault"
mk pre-no 'KIND=command
PRECHECK="false"
COMMAND="echo ran"'
"$RJ" pre-no; check "precheck false: exit 0" "$?" 0
check "precheck false: skipped line" "$(jl pre-no)" "skipped | nothing to do (precheck)"
check "precheck false: no log file" "$(ls "$UNI_STATE_DIR/jobs/pre-no" 2>/dev/null | grep -c '\.log$')" 0
mk pre-vault 'KIND=command
NEEDS_VAULT=yes
PRECHECK="[ -f _agent/agent-start.md ]"
COMMAND="echo ran-in-vault"'
"$RJ" pre-vault; check "precheck runs inside the vault" "$(lastlog pre-vault | grep -c ran-in-vault)" 1
mv "$T/vault/_agent/agent-start.md" "$T/vault/_agent/away.md"
"$RJ" pre-vault; check "vault missing: exit 3" "$?" 3
check "vault missing: skipped line" "$(jl pre-vault)" "skipped | vault $T/vault is not available"
mv "$T/vault/_agent/away.md" "$T/vault/_agent/agent-start.md"

echo "== agent jobs"
mk ag 'TITLE="Agent job"'
"$RJ" ag; log=$(lastlog ag)
check "headless (-p) with host default model" "$(grep -c -- '--model sonnet' <<< "$log")" 1
check "effort default" "$(grep -c -- '--effort high' <<< "$log")" 1
check "permission mode" "$(grep -c -- '--permission-mode bypassPermissions' <<< "$log")" 1
check "jobs never get the browser bridge" "$(grep -c -- '--no-chrome' <<< "$log")" 1
check "headless preamble first" "$(grep -c '^prompt-first-line: This run is headless' <<< "$log")" 1
check "task text included" "$(grep -c '^task: included' <<< "$log")" 1
check "not a dry run" "$(grep -o 'dry=[01]' <<< "$log")" "dry=0"
"$RJ" ag --dry-run; log=$(lastlog ag)
check "dry run: UNI_DRY_RUN exported" "$(grep -o 'dry=[01]' <<< "$log")" "dry=1"
check "dry run: DRY RUN preamble" "$(grep '^prompt-first-line' <<< "$log" | cut -c1-28)" "prompt-first-line: DRY RUN ("
mk agm 'MODEL="opus"
EFFORT="xhigh"'
"$RJ" agm; check "job MODEL and EFFORT" "$(lastlog agm | grep -c -- '--model opus --effort xhigh')" 1
mk rcdry 'SESSION="rc"'
"$RJ" rcdry --dry-run; check "a dry run of an rc job is headless" "$(lastlog rcdry | grep -c -- '^args:')" 1

echo "== RUNTIME, DISABLED and DATES"
mk offmod 'KIND=command
COMMAND="echo ran"'
touch "$T/jobs/offmod/DISABLED"
"$RJ" offmod; check "DISABLED marker: skipped" "$(jl offmod | cut -c1-25)" "skipped | module disabled"
mk laptoponly 'KIND=command
RUNTIME=laptop
COMMAND="echo ran"'
"$RJ" laptoponly; check "RUNTIME=laptop: skipped" "$(jl laptoponly | cut -c1-20)" "skipped | RUNTIME=la"
mk dated 'KIND=command
DATES="2020-01-01..2020-01-31"
COMMAND="echo ran"'
UNI_SCHEDULED=1 "$RJ" dated; check "scheduled run outside DATES: skipped" "$(jl dated)" "skipped | outside DATES"
"$RJ" dated; check "manual run ignores DATES" "$(jl dated | cut -d'|' -f1 | sed 's/ $//')" "exit 0"

echo "== locks"
mk slow 'KIND=command
COMMAND="sleep 3"'
"$RJ" slow & sleep 1
check "the same job twice: second exits 0 at once" "$("$RJ" slow 2>&1; echo "rc=$?")" "run-job: slow is already running"$'\n'"rc=0"
wait
mk hb 'AGENT_LOCK=exclusive
LOCK_WAIT_MIN=1'
mk other ''
mk hb0 'AGENT_LOCK=exclusive
LOCK_WAIT_MIN=0'
mk other2 ''
FAKE_SLEEP=4 "$RJ" hb & sleep 1; FAKE_SLEEP=0 "$RJ" other; wait
hb_end=$(lastlog hb | awk '/^end/ {print $2}'); o_start=$(lastlog other | awk '/^start/ {print $2}')
check "a shared job waits for the exclusive one" "$(awk -v a="$hb_end" -v b="$o_start" 'BEGIN {print (b >= a) ? "after" : "overlap"}')" after
FAKE_SLEEP=4 "$RJ" other & sleep 1; FAKE_SLEEP=0 "$RJ" hb0; wait
check "an exclusive job skips while another runs" "$(grep -c 'hb0 | skipped | another agent job' "$UNI_STATE_DIR/jobs.log")" 1
FAKE_SLEEP=2 "$RJ" other & sleep 0.5; FAKE_SLEEP=0 "$RJ" other2; wait
o_end=$(lastlog other | awk '/^end/ {print $2}'); o2_start=$(lastlog other2 | awk '/^start/ {print $2}')
check "two ordinary agent jobs run side by side" "$(awk -v a="$o_end" -v b="$o2_start" 'BEGIN {print (b < a) ? "overlap" : "after"}')" overlap
if [ -d /proc/self/fd ]; then check "fd 7 is closed in the agent" "$(lastlog other2 | grep -o 'fd7=[a-z]*')" "fd7=closed"; else skip "no /proc: fd check"; fi

echo "== failover mode"
if have jq; then
  mkdir -p "$UNI_STATE_DIR/modes"
  mk fo 'KIND=command
FAILOVER_DELAY_MIN=0
LAPTOP_TASK=desk-task
COMMAND="echo ran-here"'
  echo failover > "$UNI_STATE_DIR/modes/fo"
  printf '{"seen":"%s","tasks":{"desk-task":{"lastScheduledFor":"%s"}}}' "$(date -Iseconds)" "$(date -Iseconds)" > "$UNI_STATE_DIR/laptop-tasks.json"
  UNI_SCHEDULED=1 "$RJ" fo; check "the laptop ran this slot: skipped" "$(jl fo)" "skipped | laptop ran this slot"
  printf '{"tasks":{"desk-task":{"lastScheduledFor":"2020-01-01T08:00:00+00:00"}}}' > "$UNI_STATE_DIR/laptop-tasks.json"
  rm -f "$UNI_STATE_DIR/laptop-seen"
  UNI_SCHEDULED=1 "$RJ" fo; check "laptop off: runs here" "$(lastlog fo | grep -c ran-here)" 1
  check "ran-marker written with the slot" "$(grep -c '^slot: ' "$T/vault/_agent/vm/ran/desk-task.md" 2>/dev/null)" 1
  date -Iseconds > "$UNI_STATE_DIR/laptop-seen"
  UNI_SCHEDULED=1 "$RJ" fo; check "laptop online but did not run: runs after the re-check" "$(grep -c 'laptop online but did not run it' "$UNI_STATE_DIR/jobs.log")" 1
  "$RJ" fo; check "manual run: no failover wait, no marker change" "$(lastlog fo | head -n 1 | grep -c 'mode=failover')" 1
else
  skip "failover tests need jq"
fi
summary
