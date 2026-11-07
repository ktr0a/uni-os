# laptop-ping.ps1: tell the always-on host "the laptop is awake and the agent desktop app is open",
# with the app's last-run time per scheduled task (Windows, experimental).
#
# Only needed for FAILOVER mode: a host job in mode failover runs only when the laptop's
# desktop-app copy of that task missed its slot (run-job checks FAILOVER_DELAY_MIN after the slot).
# In the original system this was called "heartbeat"; renamed because the heartbeat module is the
# proactive watcher. Mode "always" (all recurring jobs on the host) needs none of this.
#
# Runs every 10 min from the Task Scheduler task "Uni OS laptop ping" (install-laptop.ps1),
# hidden through laptop-ping-launcher.vbs, also on battery.
# 1. Exits at once if the desktop app isn't running (app closed = treat the laptop as off).
# 2. Merges every scheduled-tasks.json of the app (oldest first, newer wins). If one can't be
#    read right now (the app may be writing it), it skips this ping rather than send an empty list.
# 3. Sends base64 of {"seen": ISO, "tasks": {"<task id>": {"lastRunAt", "lastScheduledFor",
#    "enabled"}}} to the host: uni-vm laptop-ping <b64> (stores laptop-seen + laptop-tasks.json).
# Claude desktop app internals used here (undocumented, may change with any app update; they
# are settings in laptop.env): the Store process path *\WindowsApps\Claude_*\app\Claude.exe and
# %LOCALAPPDATA%\Claude-Data\*\claude-code-sessions\*\*\scheduled-tasks.json (.scheduledTasks[]).
# Settings: %USERPROFILE%\.config\uni-os\laptop.env. Test: powershell -File laptop-ping.ps1 -DryRun
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$cfg = @{
  HOST_ALIAS = 'uni-vm'; HOST_TRANSPORT = 'ssh'; WSL_DISTRO = 'Ubuntu-24.04'; WSL_USER = ''
  APP_PROCESS_LIKE = '*\WindowsApps\Claude_*\app\Claude.exe'
  APP_TASKS_GLOB = '%LOCALAPPDATA%\Claude-Data\*\claude-code-sessions\*\*\scheduled-tasks.json'
}
$envFile = Join-Path $env:USERPROFILE '.config\uni-os\laptop.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)=(.*)$') { $cfg[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'") }
  }
}

$app = Get-Process -Name Claude -ErrorAction SilentlyContinue | Where-Object { $_.Path -like $cfg.APP_PROCESS_LIKE }
if (-not $app -and -not $DryRun) { exit 0 }

$tasks = @{}
$glob = [Environment]::ExpandEnvironmentVariables($cfg.APP_TASKS_GLOB)
$files = Get-ChildItem $glob -ErrorAction SilentlyContinue | Sort-Object LastWriteTime
foreach ($file in $files) {
  try {
    (Get-Content $file.FullName -Raw -ErrorAction Stop | ConvertFrom-Json).scheduledTasks | ForEach-Object {
      $tasks[$_.id] = @{ lastRunAt = $_.lastRunAt; lastScheduledFor = $_.lastScheduledFor; enabled = $_.enabled }
    }
  } catch { exit 0 }
}
$json = @{ seen = (Get-Date).ToString('o'); tasks = $tasks } | ConvertTo-Json -Depth 4 -Compress
if ($DryRun) { "app running: $([bool]$app)"; $json; exit 0 }
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
$ssh = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
if ($cfg.HOST_TRANSPORT -eq 'wsl') {
  $remote = "wsl.exe -d $($cfg.WSL_DISTRO) -u $($cfg.WSL_USER) --exec /home/$($cfg.WSL_USER)/.local/bin/uni-vm laptop-ping $b64"
} else {
  $remote = "~/.local/bin/uni-vm laptop-ping $b64"
}
& $ssh -o ConnectTimeout=60 -o BatchMode=yes $cfg.HOST_ALIAS $remote 2>$null | Out-Null
