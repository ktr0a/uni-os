#!/usr/bin/env bash
# job.conf parsing: defaults, the original runner's key names, quoting, export lines, and the
# static reader used before a job from the vault is accepted.
. "$(dirname "$0")/lib.sh"
. "$HOST_DIR/lib/jobconf.sh"
mk() { mkdir -p "$T/jobs/$1"; printf '%s\n' "$2" > "$T/jobs/$1/job.conf"; }
g() { job_get "$T/jobs/$1" "$2"; }

echo "== defaults"
mk plain 'TITLE="Daily study prep"
SLOTS="17:30, 19:30"'
check "TITLE" "$(g plain TITLE)" "Daily study prep"
check "KIND" "$(g plain KIND)" agent
check "SESSION" "$(g plain SESSION)" print
check "KEEP_H" "$(g plain KEEP_H)" 8
check "MODEL empty = host default" "$(g plain MODEL)" ""
check "TIMEOUT_MIN" "$(g plain TIMEOUT_MIN)" 45
check "NEEDS_VAULT" "$(g plain NEEDS_VAULT)" yes
check "PRECHECK" "$(g plain PRECHECK)" ""
check "QUIET_OK" "$(g plain QUIET_OK)" no
check "DRY_OK" "$(g plain DRY_OK)" no
check "AGENT_LOCK" "$(g plain AGENT_LOCK)" shared
check "LOCK_WAIT_MIN" "$(g plain LOCK_WAIT_MIN)" 20
check "LAPTOP_TASK = job name" "$(g plain LAPTOP_TASK)" plain
check "FAILOVER_DELAY_MIN" "$(g plain FAILOVER_DELAY_MIN)" 25
check "MARKER" "$(g plain MARKER)" yes
check "RUNTIME" "$(g plain RUNTIME)" any
check "DEFAULT_MODE" "$(g plain DEFAULT_MODE)" off
check "SLOTS kept as written" "$(g plain SLOTS)" "17:30, 19:30"
mk notitle 'TITLE=""'
check "empty TITLE = job name" "$(g notitle TITLE)" notitle

echo "== the original runner's names"
mk legacy 'KIND=claude
NEEDS_MOUNT=no
CLAUDE_LOCK=exclusive
LAPTOP_TASK=desk-task'
check "KIND=claude -> agent" "$(g legacy KIND)" agent
check "NEEDS_MOUNT -> NEEDS_VAULT" "$(g legacy NEEDS_VAULT)" no
check "CLAUDE_LOCK -> AGENT_LOCK" "$(g legacy AGENT_LOCK)" exclusive
check "LAPTOP_TASK set" "$(g legacy LAPTOP_TASK)" desk-task

echo "== quoting and environment"
mk quoting "MODEL='opus'
EFFORT=xhigh
PRECHECK='[ -f \"inbox/x-update.md\" ]'
NOTIFY_DONE=\"Check-in is waiting. Tap to open.\""
check "single quotes" "$(g quoting MODEL)" opus
check "no quotes" "$(g quoting EFFORT)" xhigh
check "precheck kept verbatim" "$(g quoting PRECHECK)" '[ -f "inbox/x-update.md" ]'
check "double quotes with punctuation" "$(g quoting NOTIFY_DONE)" "Check-in is waiting. Tap to open."
mk exp 'export FOO=bar
KIND=command'
check "export lines reach the job's commands" "$( ( job_load "$T/jobs/exp"; bash -c 'echo "$FOO"' ) )" bar
check "job_get does not leak into the caller" "$(g exp FOO)|${FOO:-unset}" "bar|unset"

echo "== static reader (never runs the file)"
mk static "RUNTIME=\"vm\"   # host-only
DEFAULT_MODE=always
COMMAND=\"\$(touch '$T/executed')\""
check "RUNTIME with a comment" "$(static_value "$T/jobs/static/job.conf" RUNTIME)" vm
check "DEFAULT_MODE unquoted" "$(static_value "$T/jobs/static/job.conf" DEFAULT_MODE)" always
check "missing key" "$(static_value "$T/jobs/static/job.conf" SESSION)" ""
check "the file was not executed" "$([ -e "$T/executed" ] && echo ran || echo not-run)" not-run
mk twice 'DEFAULT_MODE=off
DEFAULT_MODE="failover"'
check "the last assignment wins" "$(static_value "$T/jobs/twice/job.conf" DEFAULT_MODE)" failover

echo "== the module's own job files parse"
for d in "$TESTS_DIR"/../jobs/*/; do
  j=$(basename "$d")
  check "$j: sources cleanly" "$(bash -n "$d/job.conf" 2>&1 && echo ok)" ok
  check "$j: RUNTIME=vm" "$(static_value "$d/job.conf" RUNTIME)" vm
done
summary
