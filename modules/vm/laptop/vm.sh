#!/usr/bin/env bash
# vm.sh: run ONE command on the always-on host from Git Bash on the laptop (Windows, experimental).
#   bash modules/vm/laptop/vm.sh 'uni-vm status'
#   bash modules/vm/laptop/vm.sh 'cat > ~/scratch/x.txt' < x.txt       (stdin reaches the command)
# Settings: ~/.config/uni-os/laptop.env (HOST_ALIAS, HOST_TRANSPORT, WSL_DISTRO, WSL_USER, SSH_EXE)
#   HOST_TRANSPORT=ssh  ssh <alias> to a Linux host (a cloud VM through its IAP tunnel, any Linux box)
#   HOST_TRANSPORT=wsl  ssh <alias> lands in Windows PowerShell on a home server; the command runs in WSL
# Either way the command travels base64-encoded and runs from a temp file on the host, so quoting
# survives every hop (Git Bash -> ssh -> PowerShell -> wsl.exe -> bash) and stdin and the exit
# code pass through. Harmless noise on stderr is filtered: the gcloud IAP tunnel prints Python
# tracebacks on Windows when a session ends, and newer OpenSSH prints post-quantum warnings.
# Exit: the remote command's exit code (255 = ssh could not connect).
set -uo pipefail
ENVF="${UNI_LAPTOP_ENV:-$HOME/.config/uni-os/laptop.env}"
HOST_ALIAS="uni-vm"; HOST_TRANSPORT="ssh"; WSL_DISTRO="Ubuntu-24.04"; WSL_USER=""
SSH_EXE="/c/Windows/System32/OpenSSH/ssh.exe"
NOISE_FILTER='iap_tunnel|Traceback|File "|raise |six\.|~~|\^\^|OSError: \[Errno 5\]|ERROR: \[0\] Error during local|_Recv|data = conn|return self|NumPy|increase the performance|using-tcp-forwarding|post-quantum|store now, decrypt|openssh.com/pq.html|^WARNING: $|^$'
# shellcheck disable=SC1090
[ -f "$ENVF" ] && . "$ENVF"
[ -x "$SSH_EXE" ] || SSH_EXE=ssh
[ $# -gt 0 ] || { echo "usage: vm.sh '<command>'   (settings: $ENVF)"; exit 2; }

b64=$(printf '%s' "export PATH=\$HOME/.local/bin:\$PATH; $*" | base64 -w0)
runner="f=\$(mktemp); echo $b64 | base64 -d > \$f; bash \$f; r=\$?; rm -f \$f; exit \$r"
exec 3>&2
case "$HOST_TRANSPORT" in
  ssh) "$SSH_EXE" -o BatchMode=yes "$HOST_ALIAS" "$runner" 2> >(grep -v -E "$NOISE_FILTER" >&3) ;;
  wsl) "$SSH_EXE" -o BatchMode=yes "$HOST_ALIAS" \
         "wsl.exe -d $WSL_DISTRO ${WSL_USER:+-u $WSL_USER} --exec bash -c '$runner'; exit \$LASTEXITCODE" \
         2> >(grep -v -E "$NOISE_FILTER" >&3) ;;
  *) echo "HOST_TRANSPORT must be ssh or wsl (in $ENVF)"; exit 2 ;;
esac
