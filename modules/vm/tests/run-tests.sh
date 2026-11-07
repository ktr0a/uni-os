#!/usr/bin/env bash
# Run every test of the vm module: bash modules/vm/tests/run-tests.sh
# Plain bash, fake inputs only (temp folders, fake HOME, fake agent CLI, fake systemctl, every
# push into a file). Runs on Linux, in WSL and in Git Bash on Windows; tests that need flock,
# jq or systemd-analyze skip themselves where those are missing (run on the host or in WSL for
# the full set). Also checks every shell script of the module with `bash -n`.
cd "$(dirname "$0")" || exit 2
chmod +x ../host/bin/* ../host/*.sh ../laptop/*.sh ../home-server/*.sh 2>/dev/null   # a fresh clone may lack the x bits
fail=0
echo "== bash -n on every script"
n=0
for f in ../host/bin/* ../host/*.sh ../host/lib/*.sh ../laptop/*.sh ../home-server/*.sh ./*.sh; do
  [ -f "$f" ] || continue
  if bash -n "$f" 2>/tmp/uni-vm-syntax.$$; then n=$((n + 1)); else echo "SYNTAX $f: $(cat /tmp/uni-vm-syntax.$$)"; fail=1; fi
done
rm -f /tmp/uni-vm-syntax.$$
echo "bash -n: $n scripts ok"
for t in t-*.sh; do
  echo; echo "#### $t"
  bash "$t" || fail=1
done
echo
[ "$fail" = 0 ] && echo "ALL PASSED" || echo "SOME TESTS FAILED"
exit "$fail"
