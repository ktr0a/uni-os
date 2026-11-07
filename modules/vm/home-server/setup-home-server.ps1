# setup-home-server.ps1: first setup of a spare Windows laptop as the Uni OS home server
# (Windows, experimental). Run ONCE in PowerShell as administrator on the home-server laptop:
#   powershell -ExecutionPolicy Bypass -File setup-home-server.ps1 -PublicKey "C:\path\to\uni-home.pub"
# (or double-click setup-home-server.cmd next to it; it asks for admin rights once).
# -PublicKey: your MAIN laptop's ssh public key, as a .pub file path or the key text itself.
# What it does (nothing is deleted, nothing asks for a password):
#   1. OpenSSH Server: install (fallback: Microsoft's Win32-OpenSSH MSI for trimmed Windows
#      images), start, start at boot, firewall rule for Private networks only, network = Private
#   2. key-only login for that public key (administrators_authorized_keys with Administrators +
#      SYSTEM rights only, plus the user's authorized_keys), password login off, PowerShell as the
#      ssh shell
#   3. power: never sleep or hibernate (on AC and on battery), closing the lid does nothing,
#      hibernation off (that also turns Fast Startup off)
#   4. Windows Update active hours 06:00-24:00 (restarts for updates only between 00:00 and 06:00)
#   5. prints a short report (IP, computer name, user) for your laptop's ~/.ssh/config; nothing is saved
# Next steps (HOME-SERVER.md): WSL2, .wslconfig, the keep-alive task, bootstrap inside WSL.
param([Parameter(Mandatory = $true)][string]$PublicKey)
$ErrorActionPreference = 'Continue'
if (Test-Path $PublicKey) { $pub = (Get-Content $PublicKey -Raw).Trim() } else { $pub = $PublicKey.Trim() }
if ($pub -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-\S+) ') { Write-Host 'That is not an ssh public key (expected "ssh-ed25519 AAAA...").' -ForegroundColor Red; return }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host 'Please run this in PowerShell as administrator.' -ForegroundColor Red; return }

Write-Host '1/5 OpenSSH Server (can take a few minutes the first time)' -ForegroundColor Cyan
$cap = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*' | Select-Object -First 1
if ($cap -and $cap.State -ne 'Installed') { Add-WindowsCapability -Online -Name $cap.Name | Out-Null }
if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
    Write-Host '   optional feature not available: using Microsoft Win32-OpenSSH from GitHub' -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $rel = Invoke-RestMethod 'https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest' -UseBasicParsing
    $msi = $rel.assets | Where-Object name -like 'OpenSSH-Win64*.msi' | Select-Object -First 1
    $out = Join-Path $env:TEMP $msi.name
    Invoke-WebRequest $msi.browser_download_url -OutFile $out -UseBasicParsing
    Start-Process msiexec.exe -ArgumentList '/i', "`"$out`"", '/qn' -Wait
}
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
} else { Enable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' }
Get-NetConnectionProfile | Where-Object NetworkCategory -eq 'Public' | Set-NetConnectionProfile -NetworkCategory Private

Write-Host '2/5 SSH key of the main laptop, key-only login' -ForegroundColor Cyan
$sshDir = Join-Path $env:ProgramData 'ssh'
New-Item -ItemType Directory -Force $sshDir | Out-Null
$adminKeys = Join-Path $sshDir 'administrators_authorized_keys'
if (-not (Test-Path $adminKeys) -or -not (Select-String -Path $adminKeys -SimpleMatch $pub -Quiet)) { Add-Content -Path $adminKeys -Value $pub -Encoding ascii }
# Only Administrators and SYSTEM may read it, or sshd ignores the file. SIDs work in every Windows language.
icacls.exe $adminKeys /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
$userSsh = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force $userSsh | Out-Null
$userKeys = Join-Path $userSsh 'authorized_keys'
if (-not (Test-Path $userKeys) -or -not (Select-String -Path $userKeys -SimpleMatch $pub -Quiet)) { Add-Content -Path $userKeys -Value $pub -Encoding ascii }
$cfg = Join-Path $sshDir 'sshd_config'
if (Test-Path $cfg) {
    $t = Get-Content $cfg | Where-Object { $_ -notmatch '^\s*#?\s*(PasswordAuthentication|KbdInteractiveAuthentication)\s' }
    Set-Content $cfg (@('PasswordAuthentication no', 'KbdInteractiveAuthentication no') + $t) -Encoding ascii
    Restart-Service sshd
}
Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Profile Private -ErrorAction SilentlyContinue
New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force | Out-Null

Write-Host '3/5 Power: never sleep, lid does nothing, hibernation and Fast Startup off' -ForegroundColor Cyan
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 5
# On battery too, so a short power cut does not put it to sleep. Low battery still shuts it down.
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-dc 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT
powercfg /h off

Write-Host '4/5 Windows Update active hours 06:00-24:00' -ForegroundColor Cyan
$wu = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
New-Item -Path $wu -Force | Out-Null
New-ItemProperty -Path $wu -Name SetActiveHours -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $wu -Name ActiveHoursStart -Value 6 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $wu -Name ActiveHoursEnd -Value 0 -PropertyType DWord -Force | Out-Null

Write-Host '5/5 Report' -ForegroundColor Cyan
$os  = Get-CimInstance Win32_OperatingSystem
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ips = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | ForEach-Object { "$($_.IPv4Address.IPAddress) ($($_.InterfaceAlias))" }
Write-Host "Windows:        $($os.Caption), build $($os.BuildNumber)"
Write-Host "CPU / RAM:      $($cpu.Name) / $([math]::Round($cs.TotalPhysicalMemory/1GB,1)) GB"
Write-Host "Virtualization: firmware $($cpu.VirtualizationFirmwareEnabled), hypervisor running $($cs.HypervisorPresent)"
Write-Host "SSH server:     $((Get-Service sshd).Status), start $((Get-Service sshd).StartType)"
Write-Host ''
Write-Host '========== for the Host entry in ~/.ssh/config on your main laptop ==========' -ForegroundColor Green
Write-Host "IP:        $($ips -join ', ')" -ForegroundColor Green
Write-Host "Name:      $env:COMPUTERNAME" -ForegroundColor Green
Write-Host "User:      $env:USERNAME" -ForegroundColor Green
Write-Host '==============================================================================' -ForegroundColor Green
Write-Host 'Done. Leave the laptop on and plugged in; it may stay on the sign-in screen or locked.'
