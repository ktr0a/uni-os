#!/usr/bin/env bash
# move-state.sh: move the scheduled jobs and the host state from one host to another in ONE go
# (e.g. cloud VM -> home server). Git Bash on the laptop, experimental.
#   bash modules/vm/home-server/move-state.sh --from <laptop.env> --to <laptop.env> check
#   bash modules/vm/home-server/move-state.sh --from <laptop.env> --to <laptop.env> go [--extra "<path> ..."]
# check (read-only): which jobs are on at each side, the source's next timers, which state exists.
# go:
#   1. source: remembers which jobs are on, switches EVERY job off, stops writing _agent/vm/*
#      (VAULT_WRITES=no): exactly one host writes those files
#   2. copies the host state source -> target through the laptop (job logs and jobs.log, job
#      modes, performance samples and verdicts, alert markers, status signatures, outcome-check
#      state, the push gate's budget ~/.local/state/uni-os/push-gate/, the laptop-ping files) plus
#      any --extra paths relative to home (other modules' host state outside that folder)
#   3. target: JOBS_LIVE=yes, VAULT_WRITES=yes, `uni-vm jobs sync --accept-new`, and switches on
#      the same jobs that were on at the source
# Afterwards: move the role sessions one at a time (move-role.sh), point laptop.env (and the
# laptop ping) at the new host, run `uni-vm health` once on the target, watch `uni-vm doctor`.
# Rules (from a real move):
#   - Start "go" right after a :x0 or :x5 minute and never around a job's slot: a slot must not
#     run on both hosts or on neither (`check` shows the next timers).
#   - Avoid the quiet windows (timed tests): nothing should push or run then.
#   - Pieces tied to one machine move together: a poll job that starts another job starts it on
#     ITS machine; the push budget lives on one machine; a watcher that re-runs a job does so locally.
# Rollback: the same command with --from and --to swapped.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FROM=""; TO=""; CMD="check"; EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;; --to) TO="$2"; shift 2 ;; --extra) EXTRA="$2"; shift 2 ;;
    check|go) CMD="$1"; shift ;; *) echo "unknown argument $1"; exit 2 ;;
  esac
done
[ -f "$FROM" ] && [ -f "$TO" ] || { echo "usage: move-state.sh --from <laptop.env> --to <laptop.env> check|go [--extra \"paths\"]"; exit 2; }
SRC() { UNI_LAPTOP_ENV="$FROM" bash "$HERE/../laptop/vm.sh" "$1" </dev/null; }
DST() { UNI_LAPTOP_ENV="$TO" bash "$HERE/../laptop/vm.sh" "$1"; }
S=.local/state/uni-os
STATE="$S/jobs $S/jobs.log $S/modes $S/perf.csv $S/perf-daily.md $S/perf-verdicts.md $S/perf.day $S/alerts $S/outcomes $S/push-gate $S/vault-status.sig $S/vault-status.day $S/vault-status.daily $S/health.log $S/laptop-seen $S/laptop-tasks.json $EXTRA"
on_jobs() { "$1" "uni-vm jobs | awk 'NR > 1 && \$2 == \"ON\" {print \$1}'" </dev/null | tr '\r\n' '  '; }

case "$CMD" in
  check)
    echo "== now $(date +%H:%M:%S)"
    echo "== source jobs on: $(on_jobs SRC)"
    echo "== target jobs on: $(on_jobs DST)"
    echo "== source next timers:"; SRC "systemctl --user list-timers --no-legend 'uni-job-*' | head -n 8 | cut -c1-110"
    echo "== source state:"; SRC "cd ~ && for p in $STATE; do [ -e \"\$p\" ] && echo \"  ok \$p\" || echo \"  -- \$p\"; done" ;;
  go)
    jobs=$(on_jobs SRC)
    echo "== 1 source: every job off (was on: $jobs), VAULT_WRITES=no  $(date +%H:%M:%S)"
    SRC "uni-vm jobs off all >/dev/null; uni-vm hostenv set VAULT_WRITES no; systemctl --user list-timers --no-legend 'uni-job-*' | grep -c uni-job- | sed 's/^/timers still listed: /'"
    echo "== 2 copy state source -> target  $(date +%H:%M:%S)"
    SRC "cd ~ && tar -czf - \$(for p in $STATE; do [ -e \"\$p\" ] && echo \"\$p\"; done) | base64 -w0" | DST "cd ~ && base64 -d | tar --no-same-owner -xzf - && echo extracted"
    echo "== 3 target: live, writes the vault status files, same jobs on  $(date +%H:%M:%S)"
    DST "uni-vm hostenv set JOBS_LIVE yes >/dev/null; uni-vm hostenv set VAULT_WRITES yes >/dev/null; uni-vm jobs sync --accept-new >/dev/null; for j in $jobs; do uni-vm jobs on \$j; done" </dev/null
    echo "== done $(date +%H:%M:%S). Next: move-role.sh per role, point laptop.env at the new host, uni-vm health once on the target, uni-vm doctor." ;;
esac
