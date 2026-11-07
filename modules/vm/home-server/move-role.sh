#!/usr/bin/env bash
# move-role.sh: move one persistent role session from one host to another, keeping its
# conversation (and, in the original system, its app link). Git Bash on the laptop, experimental.
#   bash modules/vm/home-server/move-role.sh --from <laptop.env of the source> --to <laptop.env of the target> <role>
# Each laptop.env names one host (HOST_ALIAS, HOST_TRANSPORT, ...), as for laptop/vm.sh.
#   1. refuses if the role is mid-turn on the source (footer "esc to interrupt" / running tasks)
#   2. source: uni-vm roles stop <role> (keeps the conversation)
#   3. copies the role's .sid and .link, its role.conf, the transcript <sid>.jsonl (+ its <sid>/
#      folder) and ~/handoff/<role>/ through the laptop (tar | base64; contents are never printed),
#      putting the transcript into the TARGET's project folder (it depends on the vault path there)
#   4. compares the transcript's md5 on both sides; a mismatch stops before resuming
#   5. target: uni-vm roles resume <role> (NORESUME=1 copies only), prints its state and the
#      target's free memory
# Rollback: the same command with --from and --to swapped (copy the NEWER transcript back).
# Rules: one role at a time; never while the role is busy; rehearse once with a throwaway role.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FROM=""; TO=""; r=""
while [ $# -gt 0 ]; do
  case "$1" in --from) FROM="$2"; shift 2 ;; --to) TO="$2"; shift 2 ;; *) r="$1"; shift ;; esac
done
[ -f "$FROM" ] && [ -f "$TO" ] && [ -n "$r" ] || { echo "usage: move-role.sh --from <laptop.env> --to <laptop.env> <role>"; exit 2; }
SRC() { UNI_LAPTOP_ENV="$FROM" bash "$HERE/../laptop/vm.sh" "$1"; }
DST() { UNI_LAPTOP_ENV="$TO" bash "$HERE/../laptop/vm.sh" "$1"; }
S=.local/state/uni-os

sid=$(SRC "cat ~/$S/roles/$r.sid" </dev/null | tr -d '\r\n ')
[ -n "$sid" ] && [ "$sid" != "-" ] || { echo "no conversation id for $r on the source"; exit 1; }
echo "== $r  sid $sid"
if SRC "tmux -L uni-roles capture-pane -p -t $r 2>/dev/null | grep -v '^[[:space:]]*\$' | tail -n 4 | grep -qE 'esc to interrupt|[0-9]+ (shell|agent|task)s?( |\$)' && echo BUSY" </dev/null | grep -q BUSY; then
  echo "$r is busy on the source (mid-turn or a background task): not moving it now"; exit 2
fi
tr_rel=$(SRC "f=\$(find ~/.claude/projects -maxdepth 2 -name '$sid.jsonl' | head -n 1); [ -n \"\$f\" ] && realpath --relative-to=\$HOME \"\$f\"" </dev/null | tr -d '\r')
[ -n "$tr_rel" ] || { echo "transcript $sid.jsonl not found on the source"; exit 1; }
dst_vault=$(DST "uni-vm hostenv get VAULT_MOUNT" </dev/null | tr -d '\r')
[ -n "$dst_vault" ] || { echo "the target has no host.env yet (run install-user.sh there)"; exit 1; }
dst_proj=".claude/projects/$(printf '%s' "$dst_vault" | sed 's|[^A-Za-z0-9]|-|g')"

SRC "uni-vm roles stop $r" </dev/null; sleep 3
paths="$S/roles/$r.sid $tr_rel"
SRC "test -f ~/$S/roles/$r.link && echo yes" </dev/null | grep -q yes && paths="$paths $S/roles/$r.link"
SRC "test -f ~/.config/uni-os/roles/$r.conf && echo yes" </dev/null | grep -q yes && paths="$paths .config/uni-os/roles/$r.conf"
SRC "test -d ~/${tr_rel%.jsonl} && echo yes" </dev/null | grep -q yes && paths="$paths ${tr_rel%.jsonl}"
SRC "test -d ~/handoff/$r && echo yes" </dev/null | grep -q yes && paths="$paths handoff/$r"
echo "copying: $paths"
SRC "cd ~ && tar -czf - $paths | base64 -w0" </dev/null | DST "t=\$(mktemp -d) && cd \$t && base64 -d | tar --no-same-owner -xzf - \
  && mkdir -p ~/$S/roles ~/$dst_proj ~/.config/uni-os/roles \
  && cp -f $S/roles/$r.sid ~/$S/roles/ && { [ ! -f $S/roles/$r.link ] || cp -f $S/roles/$r.link ~/$S/roles/; } \
  && { [ ! -f .config/uni-os/roles/$r.conf ] || [ -f ~/.config/uni-os/roles/$r.conf ] || cp .config/uni-os/roles/$r.conf ~/.config/uni-os/roles/; } \
  && cp -f $tr_rel ~/$dst_proj/ && { [ ! -d ${tr_rel%.jsonl} ] || cp -rf ${tr_rel%.jsonl} ~/$dst_proj/; } \
  && { [ ! -d handoff/$r ] || { mkdir -p ~/handoff && cp -rf handoff/$r ~/handoff/; }; } \
  && rm -rf \$t && echo extracted"
src_md5=$(SRC "md5sum ~/$tr_rel | cut -c1-32" </dev/null); dst_md5=$(DST "md5sum ~/$dst_proj/$sid.jsonl | cut -c1-32" </dev/null)
echo "transcript md5 source $src_md5 / target $dst_md5"
if [ -z "$src_md5" ] || [ "$src_md5" != "$dst_md5" ]; then
  echo "MISMATCH: not resuming on the target. Resume on the source with: UNI_LAPTOP_ENV=$FROM bash $HERE/../laptop/vm.sh 'uni-vm roles resume $r'"; exit 3
fi
if [ "${NORESUME:-}" = 1 ]; then echo "NORESUME=1: copied, left off on the target (later: uni-vm roles resume $r)"; exit 0; fi
DST "uni-vm roles resume $r; sleep 25; uni-vm roles | grep -E '^(ROLE|$r )'; free -m | sed -n 2p" </dev/null
