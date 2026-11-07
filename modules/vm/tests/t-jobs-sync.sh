#!/usr/bin/env bash
# `uni-vm jobs sync` with a fake systemctl: new jobs need --accept-new, DEFAULT_MODE switches
# timers on (host-only jobs in mode always, any job in mode failover; RUNTIME=any jobs in mode
# always arrive off, because they may run on the laptop), changes are copied (and printed), removed jobs lose their timer, RUNTIME=laptop
# jobs stay on the laptop, bad job ids are ignored, --check reports drift (exit 10).
. "$(dirname "$0")/lib.sh"
fake_host_env
export UNI_JOBS_DIR="$T/hostjobs"
mkdir -p "$T/bin"
cat > "$T/bin/systemctl" <<EOF
#!/usr/bin/env bash
# fake systemctl: logs every call; is-enabled answers from a list file
echo "\$*" >> "$T/systemctl.log"
case "\$*" in
  *is-enabled*) grep -qx "\${@: -1}" "$T/enabled" 2>/dev/null ;;
  *"enable --now"*) echo "\${@: -1}" >> "$T/enabled" ;;
  *) exit 0 ;;
esac
EOF
chmod +x "$T/bin/systemctl"
export PATH="$T/bin:$PATH"
UV="$HOST_DIR/bin/uni-vm"
VJ="$T/vault/_agent/jobs"
mkjob() { mkdir -p "$VJ/$1"; printf '%s\n' "$2" > "$VJ/$1/job.conf"; echo "the task" > "$VJ/$1/prompt.md"; }
UNITS="$HOME/.config/systemd/user"

mkjob health 'KIND=command
COMMAND="uni-vm health"
SCHEDULE="*-*-* *:00/15:00"
RUNTIME=vm
DEFAULT_MODE=always'
mkjob prep 'SLOTS="17:30, 19:30"
DEFAULT_MODE=off'
mkjob desk-only 'SLOTS="09:00"
RUNTIME=laptop'
mkjob Bad_Name 'SLOTS="09:00"'
mkjob nosched 'KIND=agent'
mkjob poll 'KIND=command
SCHEDULE="*-*-* 07..21:00/10:00"
DEFAULT_MODE=always'
mkjob shadow 'SLOTS="07:30"
DEFAULT_MODE=failover'

out=$("$UV" jobs sync </dev/null 2>&1)
check "new jobs wait without --accept-new" "$(grep -c 'waits: uni-vm jobs sync --accept-new' <<< "$out")" 5
check "nothing copied yet" "$(ls "$UNI_JOBS_DIR" 2>/dev/null | wc -l | tr -d ' ')" 0
check "--check: drift exit 10" "$("$UV" jobs sync --check >/dev/null 2>&1; echo $?)" 10

out=$("$UV" jobs sync --accept-new </dev/null 2>&1)
check "five jobs taken (laptop-only and bad id left out)" "$(ls "$UNI_JOBS_DIR" | sort | tr '\n' ' ')" "health nosched poll prep shadow "
check "bad job id reported" "$(grep -c 'ignored Bad_Name' <<< "$out")" 1
check "timer for health" "$(grep '^OnCalendar=' "$UNITS/uni-job-health.timer")" "OnCalendar=*-*-* *:00/15:00"
check "timer for prep (two slots)" "$(grep -c '^OnCalendar=' "$UNITS/uni-job-prep.timer")" 2
check "no timer without a schedule" "$([ -e "$UNITS/uni-job-nosched.timer" ] && echo yes || echo no)" no
check "DEFAULT_MODE=always switched health on" "$(grep -c 'enable --now uni-job-health.timer' "$T/systemctl.log")" 1
check "DEFAULT_MODE=off left prep off" "$(grep -c 'enable --now uni-job-prep.timer' "$T/systemctl.log")" 0
check "RUNTIME=any + always arrives off (it may run on the laptop)" "$(grep -c 'enable --now uni-job-poll.timer' "$T/systemctl.log")" 0
check "... and says how to move it" "$(grep -c 'new job poll: off here until moved' <<< "$out")" 1
check "DEFAULT_MODE=failover switches on (runs only missed slots)" "$(grep -c 'enable --now uni-job-shadow.timer' "$T/systemctl.log")" 1
check "failover mode file" "$(cat "$UNI_STATE_DIR/modes/shadow")" failover
check "mode file written" "$(cat "$UNI_STATE_DIR/modes/health")" always
check "--check: in sync" "$("$UV" jobs sync --check 2>&1 | grep -v '^ignored'; echo "rc=${PIPESTATUS[0]}")" "host jobs match the vault"$'\n'"rc=0"

printf 'SLOTS="18:00"\nDEFAULT_MODE=off\n' > "$VJ/prep/job.conf"
check "--check sees the change" "$("$UV" jobs sync --check 2>&1 | grep -v '^ignored' | head -n 1)" "changed in the vault since the last sync: prep"
out=$("$UV" jobs sync </dev/null 2>&1)
check "change copied and printed" "$(grep -c '^updated prep' <<< "$out")" 1
check "timer rewritten" "$(grep '^OnCalendar=' "$UNITS/uni-job-prep.timer")" "OnCalendar=*-*-* 18:00:00"

rm -rf "$VJ/nosched" "$VJ/prep" "$VJ/poll" "$VJ/shadow"
out=$("$UV" jobs sync </dev/null 2>&1)
check "removed job reported" "$(grep -c 'removed job prep' <<< "$out")" 1
check "its timer is gone" "$([ -e "$UNITS/uni-job-prep.timer" ] && echo yes || echo no)" no
check "its host copy is gone" "$([ -d "$UNI_JOBS_DIR/prep" ] && echo yes || echo no)" no

echo "JOBS_LIVE=no" >> "$UNI_HOST_ENV"
out=$("$UV" jobs sync </dev/null 2>&1)
check "trial host: every timer off" "$(grep -c 'JOBS_LIVE=no' <<< "$out")" 1
check "jobs list shows the job" "$("$UV" jobs list | awk '$1 == "health" {print $1, $3}')" "health always"

echo "== who runs the outcome checks (uni-vm health step 12): the job only while its timer is on"
owner() { ( . "$HOST_DIR/lib/common.sh"; outcome_checks_owner ); }
check "job not taken: the built-in check" "$(owner)" built-in
mkdir -p "$UNI_JOBS_DIR/outcome-checks"; printf 'KIND=command
RUNTIME=any
DEFAULT_MODE=always
' > "$UNI_JOBS_DIR/outcome-checks/job.conf"
check "taken but switched off: still the built-in check (never neither)" "$(owner)" built-in
echo uni-job-outcome-checks.timer >> "$T/enabled"
check "taken and switched on: the job (never both)" "$(owner)" job
summary
