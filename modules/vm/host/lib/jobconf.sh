# shellcheck shell=bash
# Uni OS host: job.conf handling (sourced by uni-vm, run-job and the tests; never run).
#
# A job is a folder with job.conf (+ prompt.md for agent jobs). The vault holds the rendered
# jobs in <vault>/_agent/jobs/<job>/; `uni-vm jobs sync` copies them to the host
# (~/.local/share/uni-os/jobs/<job>/) and writes one systemd timer per scheduled job.
# job.conf is bash: `KEY="value"` lines, sourced AFTER the defaults below. Any `export VAR=...`
# line passes extra environment to the job. The full key list is in the module README.
#
# Schedules: SCHEDULE (raw systemd OnCalendar strings joined by ";") wins. Otherwise SLOTS
# ("HH:MM, HH:MM", local time), DAYS ("Mon,Tue,..."; empty or all seven = every day) and DATES
# ("YYYY-MM-DD" or "YYYY-MM-DD..YYYY-MM-DD", ";"-separated; empty = always) are converted by
# oncalendar_lines below. A date range that crosses months becomes one line per month, because
# systemd ranges work per date component ("2026-11-20..30" and "2026-12-01..05").
# EVERY_MIN (a fixed interval for polling jobs, read by the laptop scheduler of module
# scheduler-local) is used when a job has neither SCHEDULE nor SLOTS: "10" -> "*-*-* *:00/10:00",
# "120" -> "*-*-* 00/2:00:00" (DAYS still apply; DATES are checked at run time).

job_defaults() {
  TITLE="$1" KIND=agent COMMAND="" SLOTS="" EVERY_MIN="" DAYS="" DATES="" SCHEDULE="" SESSION=print KEEP_H=8
  MODEL="" EFFORT="" TIMEOUT_MIN=45 NEEDS_VAULT=yes PRECHECK="" QUIET_OK=no DRY_OK=no
  NOTIFY_DONE="" NOTIFY_GATE="" AGENT_LOCK=shared LOCK_WAIT_MIN=20 LAPTOP_TASK=""
  FAILOVER_DELAY_MIN=25 MARKER=yes RUNTIME=any DEFAULT_MODE=off
  NEEDS_MOUNT="" CLAUDE_LOCK=""
}

# job_load <job dir>: defaults, then source job.conf in THIS shell. Use it in a subshell when
# you only want to read values. Accepts the original runner's names (KIND=claude,
# NEEDS_MOUNT, CLAUDE_LOCK) so old job folders keep working.
job_load() {
  local dir="$1" name
  name=$(basename "$dir")
  job_defaults "$name"
  # shellcheck disable=SC1091
  . "$dir/job.conf"
  [ "$KIND" = claude ] && KIND=agent
  [ -n "$NEEDS_MOUNT" ] && NEEDS_VAULT="$NEEDS_MOUNT"
  [ -n "$CLAUDE_LOCK" ] && AGENT_LOCK="$CLAUDE_LOCK"
  [ -n "$LAPTOP_TASK" ] || LAPTOP_TASK="$name"
  [ -n "$TITLE" ] || TITLE="$name"
  return 0
}

# job_get <job dir> <KEY>: one value, read in a subshell (the job.conf can't leak).
job_get() { ( job_load "$1" >/dev/null 2>&1; eval "printf '%s' \"\${$2}\"" ); }

# static_value <job.conf> <KEY>: the last plain KEY=... value WITHOUT running the file. Used for
# job folders not yet accepted from the vault (sourcing them would execute their code).
static_value() { sed -n -E "s/^[[:space:]]*$2=[\"']?([^\"'#]*)[\"']?.*$/\1/p" "$1" 2>/dev/null | tail -n 1 | sed 's/[[:space:]]*$//'; }

# norm_days <DAYS>: "Mon, Tue" -> "Mon,Tue"; empty or all seven days -> empty (= every day).
# Accepts ranges written "Mon..Fri" (systemd style) or "Mon-Fri" (rewritten to
# "Mon..Fri", as the laptop runner reads both). Unknown names: message on stderr, exit 1.
norm_days() {
  local d tok all=1 x a b
  local -a out=()
  local seen=" "
  d=$(printf '%s' "$1" | tr -d ' ' | sed -E 's/([A-Za-z]{3})-([A-Za-z]{3})/\1..\2/g')
  [ -z "$d" ] && return 0
  local IFS=,
  for tok in $d; do
    case "$tok" in
      Mon|Tue|Wed|Thu|Fri|Sat|Sun) out+=("$tok"); seen="$seen$tok " ;;
      ?*..?*)
        a=${tok%%..*}; b=${tok##*..}
        case "$a" in Mon|Tue|Wed|Thu|Fri|Sat|Sun) ;; *) echo "bad day range: $tok" >&2; return 1 ;; esac
        case "$b" in Mon|Tue|Wed|Thu|Fri|Sat|Sun) ;; *) echo "bad day range: $tok" >&2; return 1 ;; esac
        out+=("$tok"); seen="$seen$tok " ;;
      *) echo "bad day: $tok (use Mon..Sun)" >&2; return 1 ;;
    esac
  done
  for x in Mon Tue Wed Thu Fri Sat Sun; do case "$seen" in *" $x "*) ;; *) all=0 ;; esac; done
  [ "$all" = 1 ] && return 0
  printf '%s' "${out[*]}"
}

# norm_slot <H:MM|HH:MM>: "HH:MM:00", or exit 1 with a message.
norm_slot() {
  local s="$1" h m
  if [[ "$s" =~ ^([0-9]{1,2}):([0-9]{2})$ ]]; then
    h=$((10#${BASH_REMATCH[1]})); m=$((10#${BASH_REMATCH[2]}))
    if [ "$h" -le 23 ] && [ "$m" -le 59 ]; then printf '%02d:%02d:00' "$h" "$m"; return 0; fi
  fi
  echo "bad time slot: $s (use HH:MM)" >&2
  return 1
}

# valid_date <YYYY-MM-DD>
valid_date() { [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && [ "$(date -d "$1" +%F 2>/dev/null)" = "$1" ]; }

# date_items <DATES>: normalised items, one per line: "A" or "A..B" (full ISO dates).
# "2026-11-09..29" (systemd shorthand) is accepted and expanded to "2026-11-09..2026-11-29".
date_items() {
  local item a b
  local -a items=()
  IFS=';' read -ra items <<< "$1"
  for item in "${items[@]}"; do
    item=$(printf '%s' "$item" | tr -d ' ')
    [ -z "$item" ] && continue
    if [[ "$item" == *..* ]]; then
      a=${item%%..*}; b=${item##*..}
      [[ "$b" =~ ^[0-9]{1,2}$ ]] && b="${a:0:8}$(printf '%02d' "$((10#$b))")"
      valid_date "$a" && valid_date "$b" || { echo "bad date range: $item" >&2; return 1; }
      [[ "$a" > "$b" ]] && { echo "date range ends before it starts: $item" >&2; return 1; }
      echo "$a..$b"
    else
      valid_date "$item" || { echo "bad date: $item" >&2; return 1; }
      echo "$item"
    fi
  done
}

# date_segments <DATES>: systemd date specs, one per line ("2026-11-09..29", "2026-12-08").
date_segments() {
  local items item a b cur y m d1 d2 last by bm
  items=$(date_items "$1") || return 1
  while IFS= read -r item; do
    [ -z "$item" ] && continue
    if [[ "$item" != *..* ]]; then echo "$item"; continue; fi
    a=${item%%..*}; b=${item##*..}; cur="$a"
    by=${b:0:4}; bm=${b:5:2}
    while true; do
      y=${cur:0:4}; m=${cur:5:2}; d1=${cur:8:2}
      last=$(date -d "$y-$m-01 +1 month -1 day" +%d)
      if [ "$y-$m" = "$by-$bm" ]; then d2=${b:8:2}; else d2=$last; fi
      if [ "$d1" = "$d2" ]; then echo "$y-$m-$d1"; else echo "$y-$m-$d1..$d2"; fi
      [ "$y-$m" = "$by-$bm" ] && break
      cur=$(date -d "$y-$m-01 +1 month" +%F)
    done
  done <<< "$items"
}

# oncalendar_lines <SLOTS> <DAYS> <DATES>: one systemd OnCalendar expression per line.
# No slots: prints nothing (a job without a timer, started by other tools). Errors: exit 1.
oncalendar_lines() {
  local slots="$1" dates="$3" days s t seg segs_out
  local -a raw=() times=() segs=()
  days=$(norm_days "$2") || return 1
  IFS=',' read -ra raw <<< "$slots"
  for s in "${raw[@]}"; do
    s=$(printf '%s' "$s" | tr -d ' ')
    [ -z "$s" ] && continue
    t=$(norm_slot "$s") || return 1
    times+=("$t")
  done
  [ "${#times[@]}" -eq 0 ] && return 0
  if [ -n "$(printf '%s' "$dates" | tr -d ' ;')" ]; then
    segs_out=$(date_segments "$dates") || return 1
    mapfile -t segs <<< "$segs_out"
  else
    segs=("*-*-*")
  fi
  for seg in "${segs[@]}"; do
    for t in "${times[@]}"; do echo "${days:+$days }$seg $t"; done
  done
}

# every_line <EVERY_MIN> <DAYS>: the OnCalendar expression of a fixed interval, or exit 1.
every_line() {
  local n days
  [[ "$1" =~ ^[0-9]+$ ]] && [ "$((10#$1))" -ge 1 ] || { echo "bad EVERY_MIN: $1 (minutes: 1-59 or a multiple of 60)" >&2; return 1; }
  n=$((10#$1)); days=$(norm_days "$2") || return 1
  if [ "$n" -lt 60 ]; then echo "${days:+$days }*-*-* *:00/$n:00"
  elif [ $(( n % 60 )) -eq 0 ] && [ "$n" -le 1440 ]; then echo "${days:+$days }*-*-* 00/$(( n / 60 )):00:00"
  else echo "bad EVERY_MIN: $1 (minutes: 1-59 or a multiple of 60)" >&2; return 1; fi
}

# job_schedule <job dir>: the OnCalendar lines of a job (SCHEDULE wins over SLOTS/DAYS/DATES,
# which win over EVERY_MIN).
job_schedule() {
  ( job_load "$1" >/dev/null 2>&1 || exit 1
    if [ -n "$(printf '%s' "$SCHEDULE" | tr -d ' ;')" ]; then
      local p; local -a parts=()
      IFS=';' read -ra parts <<< "$SCHEDULE"
      for p in "${parts[@]}"; do p=$(printf '%s' "$p" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'); [ -n "$p" ] && echo "$p"; done
    elif [ -z "$(printf '%s' "$SLOTS" | tr -d ' ,')" ] && [ -n "$(printf '%s' "$EVERY_MIN" | tr -d ' ')" ]; then
      every_line "$(printf '%s' "$EVERY_MIN" | tr -d ' ')" "$DAYS"
    else
      oncalendar_lines "$SLOTS" "$DAYS" "$DATES"
    fi )
}

# dates_include <DATES> <YYYY-MM-DD>: true when DATES is empty or covers the day.
dates_include() {
  local items item a b d="$2"
  [ -z "$(printf '%s' "$1" | tr -d ' ;')" ] && return 0
  items=$(date_items "$1" 2>/dev/null) || return 0      # a broken DATES never blocks a run here
  while IFS= read -r item; do
    [ -z "$item" ] && continue
    if [[ "$item" == *..* ]]; then
      a=${item%%..*}; b=${item##*..}
      [[ ! "$d" < "$a" && ! "$d" > "$b" ]] && return 0
    else
      [ "$d" = "$item" ] && return 0
    fi
  done <<< "$items"
  return 1
}

# human_schedule <job dir>: a short readable schedule for listings ("Mon,Wed 20:30", "every 15 min").
human_schedule() {
  job_schedule "$1" 2>/dev/null | sed -E 's/\*-\*-\* //; s/:00$//; s/(^| )\*:00\/([0-9]+)$/\1every \2 min/' | paste -sd ';' - | sed 's/;/; /g'
}

# timer_unit <job> <title> <OnCalendar lines...>: the text of uni-job-<job>.timer.
# AccuracySec=1s + RandomizedDelaySec=20 keep the start minute equal to the nominal slot,
# which the failover check and the ran-markers rely on.
timer_unit() {
  local job="$1" title="$2" l
  shift 2
  printf '[Unit]\nDescription=Uni OS job %s (%s)\n\n[Timer]\n' "$job" "$title"
  for l in "$@"; do printf 'OnCalendar=%s\n' "$l"; done
  printf 'AccuracySec=1s\nRandomizedDelaySec=20\nUnit=uni-job@%s.service\n\n[Install]\nWantedBy=timers.target\n' "$job"
}
