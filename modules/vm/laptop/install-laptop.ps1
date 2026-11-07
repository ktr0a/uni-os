# install-laptop.ps1: set up the laptop-side helpers of the vm module (Windows, experimental).
# Run in a normal PowerShell (no admin needed) from this folder:
#   powershell -ExecutionPolicy Bypass -File install-laptop.ps1 -EnvFile -UniVmCmd [-LaptopPing]
#   -EnvFile     create %USERPROFILE%\.config\uni-os\laptop.env from laptop.env.example (if missing)
#   -UniVmCmd    copy uni-vm.cmd to %USERPROFILE%\.local\bin and add that folder to the user PATH
#   -LaptopPing  copy laptop-ping.ps1 + launcher to %USERPROFILE%\.uni-os\laptop-ping\ and register
#                the task "Uni OS laptop ping": every 10 min (and at log-on), hidden, also on
#                battery, one instance at a time, 5 min limit. Only for failover mode.
#   -Uninstall   remove what the other switches installed (the env file stays)
# Behaviour spec for porting to macOS/Linux: modules/vm/README.md, "Laptop helpers".
param([switch]$EnvFile, [switch]$UniVmCmd, [switch]$LaptopPing, [switch]$Uninstall)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cfgDir = Join-Path $env:USERPROFILE '.config\uni-os'
$binDir = Join-Path $env:USERPROFILE '.local\bin'
$pingDir = Join-Path $env:USERPROFILE '.uni-os\laptop-ping'
$taskName = 'Uni OS laptop ping'

if ($Uninstall) {
  if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false; "removed task $taskName" }
  if (Test-Path $pingDir) { Remove-Item -Recurse -Force $pingDir; "removed $pingDir" }
  $cmd = Join-Path $binDir 'uni-vm.cmd'
  if (Test-Path $cmd) { Remove-Item -Force $cmd; "removed $cmd" }
  return
}

if ($EnvFile) {
  New-Item -ItemType Directory -Force $cfgDir | Out-Null
  $dst = Join-Path $cfgDir 'laptop.env'
  if (Test-Path $dst) { "kept existing $dst" } else { Copy-Item (Join-Path $here 'laptop.env.example') $dst; "created ${dst} (edit HOST_ALIAS and HOST_TRANSPORT)" }
}

if ($UniVmCmd) {
  New-Item -ItemType Directory -Force $binDir | Out-Null
  Copy-Item (Join-Path $here 'uni-vm.cmd') (Join-Path $binDir 'uni-vm.cmd') -Force
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if (($userPath -split ';') -notcontains $binDir) {
    [Environment]::SetEnvironmentVariable('Path', ($userPath.TrimEnd(';') + ';' + $binDir), 'User')
    "added $binDir to your PATH (open a new terminal)"
  }
  "installed uni-vm.cmd: try 'uni-vm status' in a new terminal"
}

if ($LaptopPing) {
  New-Item -ItemType Directory -Force $pingDir | Out-Null
  Copy-Item (Join-Path $here 'laptop-ping.ps1'), (Join-Path $here 'laptop-ping-launcher.vbs') $pingDir -Force
  $action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('//B //Nologo "' + (Join-Path $pingDir 'laptop-ping-launcher.vbs') + '"')
  $every = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10)).Repetition
  $t1 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1); $t1.Repetition = $every
  $t2 = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"; $t2.Delay = 'PT2M'; $t2.Repetition = $every
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $t1, $t2 -Settings $settings -Principal $principal `
    -Description 'Uni OS: tells the always-on host that the laptop and the agent desktop app are up (failover mode).' -Force | Out-Null
  "registered task '$taskName' (every 10 min). Test now: powershell -File `"$pingDir\laptop-ping.ps1`" -DryRun"
}

if (-not ($EnvFile -or $UniVmCmd -or $LaptopPing)) { 'nothing to do: pass -EnvFile, -UniVmCmd, -LaptopPing or -Uninstall' }
