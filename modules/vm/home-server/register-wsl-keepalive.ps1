# register-wsl-keepalive.ps1: keep the WSL distro of the home server running 24/7, with nobody
# signed in to Windows (Windows, experimental). Run once as administrator; safe to re-run.
#   powershell -ExecutionPolicy Bypass -File register-wsl-keepalive.ps1 [-Distro Ubuntu-24.04]
# The task "Uni OS WSL keepalive" starts 30 s after boot (S4U logon: no stored password, works with
# nobody signed in), runs with highest rights, restarts up to 999 times every minute if it ends,
# and keeps one `wsl.exe --exec /bin/sleep infinity` attached, so systemd inside WSL (vault mount,
# Remote Control, role sessions, timers) keeps running. Pair it with vmIdleTimeout=-1 in .wslconfig.
# Check after a reboot (before any other wsl command): Get-ScheduledTask 'Uni OS WSL keepalive' |
#   Get-ScheduledTaskInfo  (LastTaskResult 267009 = running), then wsl -l -v shows the distro Running.
param([string]$Distro = 'Ubuntu-24.04', [string]$TaskName = 'Uni OS WSL keepalive')
$user = "$env:COMPUTERNAME\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\wsl.exe" -Argument "-d $Distro --exec /bin/sleep infinity"
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = 'PT30S'
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description 'Keeps the Uni OS home-server WSL distro running 24/7 (modules/vm/home-server).' -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | ForEach-Object { "$($_.TaskName): $($_.State), runs as $($_.Principal.UserId) ($($_.Principal.LogonType))" }
