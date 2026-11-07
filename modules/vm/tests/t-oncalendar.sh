#!/usr/bin/env bash
# SLOTS/DAYS/DATES -> systemd OnCalendar, SCHEDULE override, the DATES guard, timer text.
. "$(dirname "$0")/lib.sh"
. "$HOST_DIR/lib/jobconf.sh"
nl=$'\n'
oc() { oncalendar_lines "$@" 2>/dev/null; }
rc() { oncalendar_lines "$@" >/dev/null 2>&1; echo "rc=$?"; }

echo "== slots and days"
check "two slots, every day" "$(oc '17:30, 19:30' '' '')" "*-*-* 17:30:00${nl}*-*-* 19:30:00"
check "all seven days = every day" "$(oc '07:50' 'Mon,Tue,Wed,Thu,Fri,Sat,Sun' '')" "*-*-* 07:50:00"
check "rendered list with spaces" "$(oc '07:50, 13:05' 'Mon, Tue, Wed, Thu, Fri' '')" "Mon,Tue,Wed,Thu,Fri *-*-* 07:50:00${nl}Mon,Tue,Wed,Thu,Fri *-*-* 13:05:00"
check "one day" "$(oc '19:30' 'Sun' '')" "Sun *-*-* 19:30:00"
check "a day range passes through" "$(oc '10:00' 'Mon..Fri' '')" "Mon..Fri *-*-* 10:00:00"
check "single-digit hour padded" "$(oc '7:05' '' '')" "*-*-* 07:05:00"
check "no slots: no timer" "$(oc '' 'Mon' '')" ""
check "bad time" "$(rc '25:00' '' '')" "rc=1"
check "bad minute" "$(rc '10:7' '' '')" "rc=1"
check "bad day name" "$(rc '10:00' 'Mo' '')" "rc=1"

echo "== dates"
check "range inside one month" "$(oc '08:00' '' '2026-11-09..2026-11-29')" "2026-11-09..29 08:00:00"
check "range across months" "$(oc '08:00' '' '2026-11-20..2026-12-05')" "2026-11-20..30 08:00:00${nl}2026-12-01..05 08:00:00"
check "range across a year and a leap February" "$(date_segments '2027-12-30..2028-03-01')" "2027-12-30..31${nl}2028-01-01..31${nl}2028-02-01..29${nl}2028-03-01"
check "one-off dates" "$(oc '12:15' '' '2026-11-20; 2026-12-04')" "2026-11-20 12:15:00${nl}2026-12-04 12:15:00"
check "systemd shorthand range" "$(date_segments '2026-11-09..29')" "2026-11-09..29"
check "days and a date range" "$(oc '20:30' 'Mon,Wed,Fri' '2026-11-02..2026-11-30')" "Mon,Wed,Fri 2026-11-02..30 20:30:00"
check "slots x dates" "$(oc '08:00, 18:00' '' '2026-12-08')" "2026-12-08 08:00:00${nl}2026-12-08 18:00:00"
check "invalid date" "$(rc '10:00' '' '2026-02-30')" "rc=1"
check "range that ends before it starts" "$(rc '10:00' '' '2026-12-05..2026-11-01')" "rc=1"

echo "== job_schedule"
mkdir -p "$T/jobs/raw" "$T/jobs/slots" "$T/jobs/none"
printf 'SCHEDULE="*-*-* *:00/15:00; Sun *-*-* 09:00:00"\nSLOTS="10:00"\n' > "$T/jobs/raw/job.conf"
printf 'SLOTS="17:30, 19:30"\nDAYS="Mon, Wed"\n' > "$T/jobs/slots/job.conf"
printf 'KIND=agent\n' > "$T/jobs/none/job.conf"
check "SCHEDULE wins over SLOTS" "$(job_schedule "$T/jobs/raw")" "*-*-* *:00/15:00${nl}Sun *-*-* 09:00:00"
check "SLOTS + DAYS" "$(job_schedule "$T/jobs/slots")" "Mon,Wed *-*-* 17:30:00${nl}Mon,Wed *-*-* 19:30:00"
check "nothing scheduled" "$(job_schedule "$T/jobs/none")" ""
check "human: every 15 min" "$(human_schedule "$T/jobs/raw")" "every 15 min; Sun 09:00"
check "human: days and times" "$(human_schedule "$T/jobs/slots")" "Mon,Wed 17:30; Mon,Wed 19:30"
mkdir -p "$T/jobs/every" "$T/jobs/every2h" "$T/jobs/everybad" "$T/jobs/everyslots"
printf 'EVERY_MIN="10"\nDAYS="Mon,Tue,Wed,Thu,Fri"\n' > "$T/jobs/every/job.conf"
printf 'EVERY_MIN="120"\n' > "$T/jobs/every2h/job.conf"
printf 'EVERY_MIN="90"\n' > "$T/jobs/everybad/job.conf"
printf 'EVERY_MIN="10"\nSLOTS="07:00"\n' > "$T/jobs/everyslots/job.conf"
check "EVERY_MIN (laptop scheduler key) when there is no SCHEDULE or SLOTS" "$(job_schedule "$T/jobs/every")" "Mon,Tue,Wed,Thu,Fri *-*-* *:00/10:00"
check "EVERY_MIN in whole hours" "$(job_schedule "$T/jobs/every2h")" "*-*-* 00/2:00:00"
check "EVERY_MIN that systemd can't express: error" "$(job_schedule "$T/jobs/everybad" >/dev/null 2>&1; echo "rc=$?")" "rc=1"
check "SLOTS win over EVERY_MIN" "$(job_schedule "$T/jobs/everyslots")" "*-*-* 07:00:00"
check "human: EVERY_MIN with days" "$(human_schedule "$T/jobs/every")" "Mon,Tue,Wed,Thu,Fri every 10 min"

echo "== DATES guard"
yn() { dates_include "$1" "$2" && echo yes || echo no; }
check "empty DATES: always" "$(yn '' 2026-11-10)" yes
check "inside a range" "$(yn '2026-11-09..2026-11-29' 2026-11-10)" yes
check "first day" "$(yn '2026-11-09..2026-11-29' 2026-11-09)" yes
check "last day" "$(yn '2026-11-09..2026-11-29' 2026-11-29)" yes
check "after" "$(yn '2026-11-09..2026-11-29' 2026-11-30)" no
check "one-off match" "$(yn '2026-11-20; 2026-12-04' 2026-12-04)" yes
check "one-off miss" "$(yn '2026-11-20; 2026-12-04' 2026-12-05)" no

echo "== timer text"
t=$(timer_unit demo "Demo job" "*-*-* 07:15:00" "Sun *-*-* 10:07:00")
check "two OnCalendar lines" "$(grep -c '^OnCalendar=' <<< "$t")" 2
check "accuracy 1 s" "$(grep -c '^AccuracySec=1s$' <<< "$t")" 1
check "jitter 20 s" "$(grep -c '^RandomizedDelaySec=20$' <<< "$t")" 1
check "starts the job unit" "$(grep '^Unit=' <<< "$t")" "Unit=uni-job@demo.service"

echo "== systemd accepts what we generate"
if have systemd-analyze; then
  for e in "$(oc '17:30' '' '')" "$(oc '07:50' 'Mon,Tue,Wed,Thu,Fri' '')" "$(oc '08:00' '' '2026-11-09..2026-11-29')" \
           "Mon,Wed,Fri 2026-11-02..30 20:30:00" "*-*-* *:00/15:00" "2028-02-01..29 08:00:00" \
           "$(job_schedule "$T/jobs/every")" "$(job_schedule "$T/jobs/every2h")"; do
    check "systemd-analyze calendar '$e'" "$(systemd-analyze calendar "$e" >/dev/null 2>&1 && echo ok || echo rejected)" ok
  done
else
  skip "systemd-analyze not available here (run on the host or in WSL)"
fi
summary
