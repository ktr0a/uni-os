# Uni OS vault watch: install, update or remove the Windows Task Scheduler task. EXPERIMENTAL, Windows only.
#
# What it does (run it once; re-run it after changing the times, the task name or the install folder):
#   1. copies vault-watch.ps1 and vault-watch-launcher.vbs into an install folder OUTSIDE the vault
#      (default %USERPROFILE%\Documents\uni-os\vault-watch; state files live there too),
#   2. writes vault-watch.local.json there (vault path, framework folder, python command),
#   3. registers a task for the current user (only while logged on, no elevation): daily at the configured
#      times plus at logon (+N min), start when available, battery allowed, 10 min limit, no parallel runs,
#   4. appends one "installed" line to <vault>\_agent\vault-watch\log.md.
# Settings come from <vault>\_agent\uni-os.json (schedule.vault_watch, vault_watch.*); parameters override.
#
# Run (Windows PowerShell, from anywhere; quote paths, they may contain spaces or "&"):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<framework>\modules\vault-watch\scripts\register-task.ps1" -Vault "G:\My Drive\Uni"
# Remove the task (keeps the install folder and its state):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<framework>\modules\vault-watch\scripts\register-task.ps1" -Uninstall
#
# Note for agents: some agent apps block registering scheduled tasks as "persistence". Then run with
# -NoRegister (copies files and writes settings) and hand the user the printed one-line command.
param(
    [string]$Vault = '',
    [string]$InstallDir = '',
    [string]$TaskName = '',
    [string[]]$Times = @(),
    [switch]$NoLogon,
    [switch]$NoRegister,
    [switch]$Uninstall,
    [string]$Python = ''
)
$ErrorActionPreference = 'Stop'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$DefaultTimes = @('08:17', '13:17', '18:17', '22:17')

function Get-Prop($obj, [string]$path) {
    $cur = $obj
    foreach ($seg in $path.Split('.')) {
        if ($null -eq $cur) { return $null }
        $p = $cur.PSObject.Properties[$seg]
        if ($null -eq $p) { return $null }
        $cur = $p.Value
    }
    return ,$cur
}
function Expand-PathText([string]$p) {
    $p = [Environment]::ExpandEnvironmentVariables($p)
    if ($p.StartsWith('~')) { $p = $env:USERPROFILE + $p.Substring(1) }
    return $p.Replace('/', '\')
}

$Config = $null
if ($Vault) {
    $Vault = [IO.Path]::GetFullPath($Vault)
    if ($Vault.Length -gt 3) { $Vault = $Vault.TrimEnd('\') }
    $cfgFile = [IO.Path]::Combine($Vault, '_agent\uni-os.json')
    if (Test-Path -LiteralPath $cfgFile) {
        try { $Config = Get-Content -LiteralPath $cfgFile -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { Write-Warning "could not read $cfgFile ($($_.Exception.Message)); using defaults" }
    } else {
        Write-Warning "no _agent\uni-os.json in the vault yet; using defaults. Run 'python tools/uni_os.py render' in the framework folder."
    }
}

if (-not $TaskName) { $TaskName = [string](Get-Prop $Config 'vault_watch.task_name') }
if (-not $TaskName) { $TaskName = 'Uni OS vault watch' }

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed the task '$TaskName'. The install folder (scripts, snapshots, state) was left in place."
    } else {
        Write-Host "No task named '$TaskName'."
    }
    exit 0
}

if (-not $Vault) {
    Write-Host 'usage: register-task.ps1 -Vault "<vault folder>" [-InstallDir "<folder>"] [-TaskName "<name>"] [-Times 08:17,13:17] [-NoLogon] [-NoRegister] [-Uninstall]'
    exit 2
}
if (-not (Test-Path -LiteralPath $Vault)) { Write-Host "vault folder not found: $Vault"; exit 2 }

if (-not $InstallDir) { $InstallDir = [string](Get-Prop $Config 'vault_watch.install_dir') }
if (-not $InstallDir) { $InstallDir = '%USERPROFILE%\Documents\uni-os\vault-watch' }
$InstallDir = [IO.Path]::GetFullPath((Expand-PathText $InstallDir))
if (($InstallDir.TrimEnd('\') + '\').StartsWith($Vault.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "The install folder must be outside the vault (state files change on every run): $InstallDir"
    exit 2
}

# "-Times 08:17,13:17" arrives as ONE string under powershell -File: split on commas and spaces.
$Times = @($Times | ForEach-Object { ([string]$_) -split '[,\s]+' } | Where-Object { $_ })
if ($Times.Count -eq 0) { $cfgTimes = Get-Prop $Config 'schedule.vault_watch'; $Times = @(@($cfgTimes) | Where-Object { $_ } | ForEach-Object { [string]$_ }) }
if ($Times.Count -eq 0) { $Times = $DefaultTimes }
foreach ($t in $Times) { if ($t -notmatch '^([01]\d|2[0-3]):[0-5]\d$') { Write-Host "bad time '$t' (use HH:MM)"; exit 2 } }

$AtLogon = -not $NoLogon
$cfgLogon = Get-Prop $Config 'vault_watch.at_logon'
if ($null -ne $cfgLogon -and -not $NoLogon) { $AtLogon = [bool]$cfgLogon }
$LogonDelay = 5
$cfgDelay = Get-Prop $Config 'vault_watch.logon_delay_min'
if ($null -ne $cfgDelay) { $LogonDelay = [int]$cfgDelay }

if (-not $Python) { $Python = 'python' }
$Framework = ''
try {
    $fw = [IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot, '..\..\..'))
    if (Test-Path -LiteralPath ([IO.Path]::Combine($fw, 'tools\uni_os.py'))) { $Framework = $fw }
} catch { }

# 1. copy the scripts
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$src = [IO.Path]::GetFullPath($PSScriptRoot)
if ($src.TrimEnd('\') -ine $InstallDir.TrimEnd('\')) {
    foreach ($f in 'vault-watch.ps1', 'vault-watch-launcher.vbs') {
        Copy-Item -LiteralPath ([IO.Path]::Combine($src, $f)) -Destination ([IO.Path]::Combine($InstallDir, $f)) -Force
    }
}
Get-ChildItem -LiteralPath $InstallDir -File | Where-Object { $_.Extension -in '.ps1', '.vbs' } | Unblock-File -ErrorAction SilentlyContinue

# 2. local settings (outside the vault)
$localObj = [ordered]@{
    vault        = $Vault
    framework    = $Framework
    python       = $Python
    task_name    = $TaskName
    times        = @($Times)
    at_logon     = $AtLogon
    installed_at = (Get-Date).ToString('o')
}
[IO.File]::WriteAllText([IO.Path]::Combine($InstallDir, 'vault-watch.local.json'), (ConvertTo-Json $localObj -Depth 3), $Utf8)

$launcher = [IO.Path]::Combine($InstallDir, 'vault-watch-launcher.vbs')
# The same run without -NoRegister, for the student to paste into Windows PowerShell: every parameter this
# run was given, with the values as resolved above (full paths), so it installs exactly what was prepared here.
function Quote-PsArg([string]$s) { return "'" + $s.Replace("'", "''") + "'" }
$rerun = @("powershell -NoProfile -ExecutionPolicy Bypass -File $(Quote-PsArg ([IO.Path]::Combine($src, 'register-task.ps1')))")
foreach ($k in @($PSBoundParameters.Keys)) {
    $v = $PSBoundParameters[$k]
    switch ($k) {
        'NoRegister' { }
        'Vault'      { $rerun += "-Vault $(Quote-PsArg $Vault)" }
        'InstallDir' { $rerun += "-InstallDir $(Quote-PsArg $InstallDir)" }
        'TaskName'   { $rerun += "-TaskName $(Quote-PsArg $TaskName)" }
        'Times'      { $rerun += "-Times $(Quote-PsArg ($Times -join ','))" }
        'Python'     { $rerun += "-Python $(Quote-PsArg $Python)" }
        default {
            if ($v -is [System.Management.Automation.SwitchParameter]) { if ($v.IsPresent) { $rerun += "-$k" } }
            else { $rerun += "-$k $(Quote-PsArg ([string]$v))" }
        }
    }
}
$selfCmd = $rerun -join ' '

# 3. register the task
$registered = $false
if (-not $NoRegister) {
    try {
        $user = "$env:USERDOMAIN\$env:USERNAME"
        $action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\wscript.exe" -Argument "//B //Nologo `"$launcher`"" -WorkingDirectory $InstallDir
        $triggers = @($Times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
        if ($AtLogon) {
            $logon = New-ScheduledTaskTrigger -AtLogOn -User $user
            $logon.Delay = "PT$($LogonDelay)M"
            $triggers += $logon
        }
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
        $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal `
            -Description "Uni OS vault watch (experimental). Script: $InstallDir\vault-watch.ps1" -Force | Out-Null
        $registered = $true
    } catch {
        Write-Warning "could not register the task: $($_.Exception.Message)"
    }
}

# 4. one line in the vault log
$logMd = [IO.Path]::Combine($Vault, '_agent\vault-watch\log.md')
try {
    $dir = Split-Path $logMd
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $hdr = ''
    if (-not (Test-Path -LiteralPath $logMd)) {
        $hdr = "---`r`ntype: agent`r`naudience: agent`r`ntags: [uni/agent, vault-watch]`r`n---`r`n# Vault watch log`r`n`r`nWritten by the vault-watch script on the laptop (Windows Task Scheduler). One line per run and scope; newest at the bottom. Runbook: [RUNBOOK.md](RUNBOOK.md).`r`n`r`n"
    }
    $state = if ($registered) { 'installed' } else { 'files updated, task NOT registered' }
    $logonTxt = if ($AtLogon) { ", at logon +$LogonDelay min" } else { '' }
    $line = "- $((Get-Date).ToString('yyyy-MM-dd HH:mm')) | $($state): task '$TaskName', daily $($Times -join ', ')$logonTxt; script folder $InstallDir"
    [IO.File]::AppendAllText($logMd, $hdr + $line + "`r`n", $Utf8)
} catch { Write-Warning "could not write $logMd ($($_.Exception.Message))" }

Write-Host ''
Write-Host "Install folder : $InstallDir"
Write-Host "Vault          : $Vault"
Write-Host "Times          : $($Times -join ', ')$(if ($AtLogon) { " + at logon (+$LogonDelay min)" })"
if ($registered) {
    Write-Host "Task           : '$TaskName' registered."
} else {
    Write-Host "Task           : NOT registered. Run this yourself in Windows PowerShell:"
    Write-Host "  $selfCmd"
}
Write-Host "Test (prints, writes nothing): powershell -NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\vault-watch.ps1`" -DryRun"
Write-Host "Test toast                   : powershell -NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\vault-watch.ps1`" -TestToast"
Write-Host "Remove                       : add -Uninstall to the install command"
exit 0
