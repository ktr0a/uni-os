<!-- uni-os host: machine-wide memory for Claude Code on @@HOST_NAME@@ (written by install-user.sh;
     edit modules/vm/host/agent/ in the framework instead: the next install overwrites this). -->
@~/.config/uni-os/agent/AGENTS.md

## Claude Code on this host
- Every session here (Remote Control server, role sessions, jobs) runs in the permission mode `@@AGENT_PERMISSION_MODE@@`, and `crossSessionInbound` is `accept`: mixed modes make cross-session messages wait for an approval nobody gives.
- Slash commands: `/vm-status` (health in a few lines), `/vm-help` (what this machine can and can't do), `/catch-up [since]` (what changed in the vault).
- PushNotification is held back on this machine ("terminal is active"): use `uni-vm notify "<text>"`.
- A UserPromptSubmit hook (brief-nudge) prints one fixed sentence when `@@AGENT_DIR@@/rules.md` or a role brief changed: re-read the common rules and your brief when you see it.
- Computer use is not available in the Linux CLI; the Claude in Chrome bridge reaches the laptop's Chrome only while that Chrome is open.
