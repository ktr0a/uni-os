# Uni OS course pick-up: install, update or remove (module course-files-fetch). EXPERIMENTAL, Windows only.
#
# What it does (run it on the machine whose browser downloads the course files; re-run it after changing
# courses, course URLs, official folders or any [course_fetch] setting, because the policy is baked in here):
#   1. derives the policy from <vault>\_agent\uni-os.json: allowed hosts (university.lms_url, each course's lms_url,
#      website and fetch_sources, plus course_fetch.extra_hosts), allowed target folders (every course.folder +
#      course.official_subfolders), file types, size/age limits, date guards,
#   2. copies course-pickup.ps1 and its launcher into an install folder OUTSIDE the vault and writes the policy
#      there as pickup-settings.json (a vault writer cannot change it),
#   3. registers a hidden Task Scheduler task for the current user: every N minutes (default 1), also on battery,
#      start when available, no parallel runs, 30 min limit,
#   4. creates <vault>\_agent\course-fetch\pending\ and done\, creates missing target folders whose parent folder
#      already exists (never a missing course folder: on Google Drive that could make a duplicate folder; skip with
#      -NoCreateFolders), and writes a read-only summary of the policy to
#      <vault>\_agent\course-fetch\pickup-policy.md (for the agents; the script never reads it).
#
# Run (Windows PowerShell; quote paths, they may contain spaces or "&"):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<framework>\modules\course-files-fetch\scripts\install-course-pickup.ps1" -Vault "G:\My Drive\Uni"
# Remove the task (keeps the install folder and pickup.log):  ... -Uninstall
# Note for agents: some agent apps block registering scheduled tasks as "persistence". Then run with
# -NoRegister and hand the user the printed one-line command.
param(
  [string]$Vault = '',
  [string]$InstallDir = '',
  [string]$TaskName = '',
  [string]$Downloads = '',
  [switch]$NoRegister,
  [switch]$NoCreateFolders,
  [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$Utf8 = New-Object System.Text.UTF8Encoding($false)

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
function Cfg([string]$path, $default) {
  $v = Get-Prop $Config $path
  if ($null -eq $v -or ($v -is [string] -and $v -eq '')) { return $default }
  return $v
}
function Get-List($obj, [string]$path, $default) {
  $v = Get-Prop $obj $path
  if ($null -eq $v) { $v = $default }
  foreach ($x in @($v)) { if ($null -ne $x -and [string]$x -ne '') { $x } }
}
function Expand-PathText([string]$p) {
  $p = [Environment]::ExpandEnvironmentVariables($p)
  if ($p.StartsWith('~')) { $p = $env:USERPROFILE + $p.Substring(1) }
  return $p.Replace('/', '\')
}
function Host-Of([string]$u) {
  $u = $u.Trim()
  if (-not $u) { return $null }
  if ($u -notmatch '^[a-z][a-z0-9+.-]*://') { $u = 'https://' + $u }
  try { return ([uri]$u).Host.ToLowerInvariant() } catch { return $null }
}

$Config = $null
if ($Vault) {
  $Vault = [IO.Path]::GetFullPath($Vault)
  if ($Vault.Length -gt 3) { $Vault = $Vault.TrimEnd('\') }
  $cfgFile = [IO.Path]::Combine($Vault, '_agent\uni-os.json')
  if (Test-Path -LiteralPath $cfgFile) { $Config = Get-Content -LiteralPath $cfgFile -Raw -Encoding UTF8 | ConvertFrom-Json }
}
if (-not $TaskName) { $TaskName = [string](Cfg 'course_fetch.task_name' 'Uni OS course pick-up') }

if ($Uninstall) {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed the task '$TaskName'. The install folder (scripts, settings, pickup.log) was left in place."
  } else { Write-Host "No task named '$TaskName'." }
  exit 0
}
if (-not $Vault) {
  Write-Host 'usage: install-course-pickup.ps1 -Vault "<vault folder>" [-InstallDir "<folder>"] [-TaskName "<name>"] [-Downloads "<folder>"] [-NoRegister] [-Uninstall]'
  exit 2
}
if (-not (Test-Path -LiteralPath $Vault)) { Write-Host "vault folder not found: $Vault"; exit 2 }
if ($null -eq $Config) {
  Write-Host "No _agent\uni-os.json in the vault. The pick-up policy comes from the config: run 'python tools/uni_os.py render' in the framework folder first."
  exit 2
}

# ---- derive the policy ------------------------------------------------------------------------------
$Courses = @(Get-List $Config 'courses' @())
$hosts = New-Object System.Collections.Generic.List[string]
function Add-Host([string]$h) { if ($h -and -not $hosts.Contains($h)) { $hosts.Add($h) } }
Add-Host (Host-Of ([string](Get-Prop $Config 'university.lms_url')))
foreach ($c in $Courses) {
  Add-Host (Host-Of ([string](Get-Prop $c 'lms_url')))
  Add-Host (Host-Of ([string](Get-Prop $c 'website')))
  foreach ($u in @(Get-List $c 'fetch_sources' @())) { Add-Host (Host-Of ([string]$u)) }
}
foreach ($h in @(Get-List $Config 'course_fetch.extra_hosts' @())) { Add-Host (([string]$h).Trim().ToLowerInvariant()) }

$folders = New-Object System.Collections.Generic.List[string]
foreach ($c in $Courses) {
  $cf = ([string](Get-Prop $c 'folder')).Replace('\', '/').Trim('/')
  if (-not $cf) { continue }
  foreach ($s in @(Get-List $c 'official_subfolders' @())) {
    $t = $cf + '/' + ([string]$s).Replace('\', '/').Trim('/')
    if (-not $folders.Contains($t)) { $folders.Add($t) }
  }
}

$defaultTypes = @('pdf', 'zip', 'txt', 'md', 'java', 'html', 'htm', 'tex', 'csv', 'py', 'ipynb', 'c', 'cpp', 'h', 'hpp', 'pptx', 'docx', 'xlsx')
$types = @(Get-List $Config 'course_fetch.allowed_types' $defaultTypes | ForEach-Object { ([string]$_).ToLowerInvariant().TrimStart('.') })
$blocked = @('exe', 'msi', 'bat', 'cmd', 'com', 'ps1', 'vbs', 'js', 'jse', 'wsf', 'scr', 'lnk', 'hta', 'jar', 'reg', 'dll', 'iso', 'img')
$bad = @($types | Where-Object { $blocked -contains $_ })
if ($bad.Count -gt 0) { Write-Host "refusing executable types in course_fetch.allowed_types: $($bad -join ', ')"; exit 2 }

$guards = @()
foreach ($g in @(Get-List $Config 'course_fetch.date_guards' @())) {
  $folder = [string](Get-Prop $g 'folder')
  $cname = [string](Get-Prop $g 'course')
  if (-not $folder -and $cname) {
    foreach ($c in $Courses) {
      if ([string](Get-Prop $c 'id') -ieq $cname -or [string](Get-Prop $c 'short') -ieq $cname -or [string](Get-Prop $c 'folder') -ieq $cname) {
        $folder = [string](Get-Prop $c 'folder')
      }
    }
  }
  if (-not $folder) { Write-Host "date guard without a known course or folder: $($g | ConvertTo-Json -Compress)"; exit 2 }
  $pat = [string](Get-Prop $g 'pattern'); $nb = [string](Get-Prop $g 'not_before')
  try { [void][regex]::new($pat) } catch { Write-Host "date guard pattern is not a valid regex: $pat"; exit 2 }
  try { [void][datetime]::ParseExact($nb, 'yyyy-MM-dd', $null) } catch { Write-Host "date guard not_before must be YYYY-MM-DD: $nb"; exit 2 }
  $guards += [ordered]@{ folder = $folder.Replace('\', '/').Trim('/'); pattern = $pat; not_before = $nb; reason = $(if ([string](Get-Prop $g 'reason')) { [string](Get-Prop $g 'reason') } else { 'integrity date guard' }) }
}

if (-not $Downloads) { $Downloads = [string](Cfg 'course_fetch.downloads_dir' '') }
if ($Downloads) { $Downloads = Expand-PathText $Downloads }
else {
  try { $Downloads = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path } catch { $Downloads = '' }
  if (-not $Downloads) { $Downloads = Join-Path $env:USERPROFILE 'Downloads' }
}

if (-not $InstallDir) { $InstallDir = [string](Cfg 'course_fetch.install_dir' '%USERPROFILE%\Documents\uni-os\course-pickup') }
$InstallDir = [IO.Path]::GetFullPath((Expand-PathText $InstallDir))
if (($InstallDir.TrimEnd('\') + '\').StartsWith($Vault.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
  Write-Host "The install folder must be outside the vault (the policy must not be writable through the vault): $InstallDir"
  exit 2
}
$Interval = [int](Cfg 'course_fetch.interval_minutes' 1)

$settings = [ordered]@{
  vault          = $Vault
  downloads      = $Downloads
  log_file       = [IO.Path]::Combine($InstallDir, 'pickup.log')
  allowed_hosts  = @($hosts)
  check_referrer = [bool](Cfg 'course_fetch.check_referrer' $false)
  folders        = @($folders)
  types          = @($types)
  max_mb         = [double](Cfg 'course_fetch.max_mb' 50)
  max_age_hours  = [double](Cfg 'course_fetch.max_age_hours' 12)
  wait_minutes   = [double](Cfg 'course_fetch.wait_minutes' 30)
  date_guards    = @($guards)
  mutex          = 'UniOS-CoursePickup'
  machine        = $env:COMPUTERNAME
  installed_at   = (Get-Date).ToString('o')
}

# ---- install --------------------------------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$src = [IO.Path]::GetFullPath($PSScriptRoot)
if ($src.TrimEnd('\') -ine $InstallDir.TrimEnd('\')) {
  foreach ($f in 'course-pickup.ps1', 'course-pickup-launcher.vbs') {
    Copy-Item -LiteralPath ([IO.Path]::Combine($src, $f)) -Destination ([IO.Path]::Combine($InstallDir, $f)) -Force
  }
}
Get-ChildItem -LiteralPath $InstallDir -File | Where-Object { $_.Extension -in '.ps1', '.vbs' } | Unblock-File -ErrorAction SilentlyContinue
[IO.File]::WriteAllText([IO.Path]::Combine($InstallDir, 'pickup-settings.json'), (ConvertTo-Json $settings -Depth 5), $Utf8)

foreach ($d in 'pending', 'done') { New-Item -ItemType Directory -Force -Path ([IO.Path]::Combine($Vault, "_agent\course-fetch\$d")) | Out-Null }

# Missing target folders: create them one level below an existing folder only (shortest first, so
# "assignments" exists before "assignments/solutions"). A missing course folder is never created.
$created = @()
if (-not $NoCreateFolders) {
  foreach ($t in @($folders | Sort-Object { $_.Length })) {
    $full = [IO.Path]::Combine($Vault, $t.Replace('/', '\'))
    if (Test-Path -LiteralPath $full -PathType Container) { continue }
    $parent = Split-Path $full -Parent
    if ($parent.TrimEnd('\') -ieq $Vault.TrimEnd('\')) { continue }
    $parentRel = $parent.Substring($Vault.TrimEnd('\').Length).Trim('\').Replace('\', '/')
    $isCourseFolder = @($Courses | Where-Object { ([string](Get-Prop $_ 'folder')).Replace('\', '/').Trim('/') -ieq $parentRel }).Count -gt 0
    if ((Test-Path -LiteralPath $parent -PathType Container) -and ($isCourseFolder -or $folders.Contains($parentRel))) {
      New-Item -ItemType Directory -Path $full | Out-Null
      $created += $t
    }
  }
}

$launcher = [IO.Path]::Combine($InstallDir, 'course-pickup-launcher.vbs')
# The same run without -NoRegister, for the student to paste into Windows PowerShell: every parameter this
# run was given, with the values as resolved above (full paths), so it installs exactly what was prepared here.
function Quote-PsArg([string]$s) { return "'" + $s.Replace("'", "''") + "'" }
$rerun = @("powershell -NoProfile -ExecutionPolicy Bypass -File $(Quote-PsArg ([IO.Path]::Combine($src, 'install-course-pickup.ps1')))")
foreach ($k in @($PSBoundParameters.Keys)) {
  $v = $PSBoundParameters[$k]
  switch ($k) {
    'NoRegister' { }
    'Vault'      { $rerun += "-Vault $(Quote-PsArg $Vault)" }
    'InstallDir' { $rerun += "-InstallDir $(Quote-PsArg $InstallDir)" }
    'TaskName'   { $rerun += "-TaskName $(Quote-PsArg $TaskName)" }
    'Downloads'  { $rerun += "-Downloads $(Quote-PsArg $Downloads)" }
    default {
      if ($v -is [System.Management.Automation.SwitchParameter]) { if ($v.IsPresent) { $rerun += "-$k" } }
      else { $rerun += "-$k $(Quote-PsArg ([string]$v))" }
    }
  }
}
$selfCmd = $rerun -join ' '
$registered = $false
if (-not $NoRegister) {
  try {
    $user = "$env:USERDOMAIN\$env:USERNAME"
    $action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\wscript.exe" -Argument "//B //Nologo `"$launcher`"" -WorkingDirectory $InstallDir
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Interval)
    $ts = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
      -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $ts -Principal $principal `
      -Description "Uni OS course pick-up (experimental): files course downloads that agents request into the vault. Script: $InstallDir\course-pickup.ps1" -Force | Out-Null
    $registered = $true
  } catch { Write-Warning "could not register the task: $($_.Exception.Message)" }
}

# ---- policy summary for the agents (informational; the script never reads it) ------------------------
$md = New-Object System.Text.StringBuilder
[void]$md.Append("---`ntype: agent`naudience: agent`ngenerated: $((Get-Date).ToString('yyyy-MM-dd HH:mm'))`ntags: [uni/agent, course-fetch]`n---`n")
[void]$md.Append("# Course pick-up policy (generated)`n`nWritten by ``install-course-pickup.ps1`` on the machine **$($env:COMPUTERNAME)**. Do not edit: change ``[course_fetch]`` or the course URLs and folders in ``_agent/uni-os.toml``, then the user re-runs the installer on that machine. The pick-up script reads its own copy outside the vault, never this file.`n`n")
[void]$md.Append("- Task: '$TaskName', every $Interval min$(if (-not $registered) { ' (NOT registered yet: the user must run the install command)' })`n")
[void]$md.Append("- Machine: $($env:COMPUTERNAME) (pass ``--machine $($env:COMPUTERNAME)`` when two machines run a pick-up)`n")
[void]$md.Append("- Allowed hosts (from the download's Zone.Identifier HostUrl): $(if ($hosts.Count) { ($hosts | ForEach-Object { '`' + $_ + '`' }) -join ', ' } else { 'NONE: every request will be rejected' })`n")
[void]$md.Append("- Referrer host also accepted: $(if ($settings.check_referrer) { 'yes' } else { 'no' })`n")
[void]$md.Append("- File types: $($types -join ', ')`n")
[void]$md.Append("- Limits: at most $($settings.max_mb) MB without ``--approved-large`` (the user's OK); download at most $($settings.max_age_hours) h old; a request waits at most $($settings.wait_minutes) min for its file`n")
[void]$md.Append("- Date guards: $(if ($guards.Count) { ($guards | ForEach-Object { '`' + $_.folder + '` /' + $_.pattern + '/ not before ' + $_.not_before + ' (' + $_.reason + ')' }) -join '; ' } else { 'none' })`n`n")
[void]$md.Append("## Allowed target folders`n`n")
if ($folders.Count -eq 0) { [void]$md.Append("NONE: set ``official_subfolders`` for each course, then re-run the installer.`n") }
foreach ($t in $folders) {
  $exists = Test-Path -LiteralPath ([IO.Path]::Combine($Vault, $t.Replace('/', '\'))) -PathType Container
  [void]$md.Append("- ``$t``$(if (-not $exists) { ' (does not exist yet: requests for it are rejected until the folder is created)' })`n")
}
try { [IO.File]::WriteAllText([IO.Path]::Combine($Vault, '_agent\course-fetch\pickup-policy.md'), $md.ToString(), $Utf8) }
catch { Write-Warning "could not write pickup-policy.md ($($_.Exception.Message))" }

Write-Host ''
Write-Host "Install folder : $InstallDir"
Write-Host "Downloads      : $Downloads"
Write-Host "Allowed hosts  : $(if ($hosts.Count) { $hosts -join ', ' } else { 'NONE (every request will be rejected)' })"
Write-Host "Target folders : $($folders.Count)$(if ($created.Count) { " ($($created.Count) created: $($created -join ', '))" })"
if ($registered) { Write-Host "Task           : '$TaskName' registered (every $Interval min)." }
else {
  Write-Host "Task           : NOT registered. Run this yourself in Windows PowerShell:"
  Write-Host "  $selfCmd"
}
Write-Host "Policy summary : $Vault\_agent\course-fetch\pickup-policy.md"
Write-Host "Remove         : add -Uninstall to the install command"
exit 0
