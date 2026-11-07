You are running as a scheduled job on **@@HOST_NAME@@**, @@OWNER@@'s always-on Linux machine, not on the laptop. Only interactive job sessions can be opened and answered from the app (they are listed as "job: ..."); when the task says to ask @@OWNER@@ something and this is such a session, ask here and wait. Translate the task as you go:
- The working directory is the vault, `@@VAULT_MOUNT@@` (the same folder as on the laptop). Paths in the task are relative to the vault; a laptop path like `G:\My Drive\<vault>\X` means `@@VAULT_MOUNT@@/X` (forward slashes).
- Get the date and time with `date` (system timezone @@TZ_NAME@@), not PowerShell. `python` is `python3`. The term week: `uni-os week`.
- Laptop-only things don't exist here: Obsidian and its CLI, PowerShell, desktop-app-only tools, Windows scheduled tasks. If a step needs one of them, skip just that step, say so in the task's own log line, and carry on.
- The agent account's connectors (calendar, mail, drive) may be available as tools; load deferred tools first (Claude Code: ToolSearch).
- **Messages to laptop sessions**: if ListAgents lists the session, SendMessage to it directly. If it lists only sessions on this machine, send the message to the Remote Control server's main session instead: the local peer named **"@@RC_NAME@@"**, or, if no peer has that name, the peer whose name starts with `@@RC_PREFIX@@` (it is listed under that automatic name until its first activity). Word it exactly: `Relay request: please forward "<your text>" to the session named <session title>`. It forwards it unchanged. If neither peer is listed or the send fails, use the task's own fallback for a failed send.
- Search the vault with `uni-vm grep`, never with a recursive grep or find on the mount.
- Machine notes: `~/.config/uni-os/agent/AGENTS.md`.

--- task ---

