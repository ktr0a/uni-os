# Uni OS course-file pick-up (module course-files-fetch). EXPERIMENTAL, Windows only.
# Windows PowerShell 5.1. Task Scheduler runs it every minute, hidden (course-pickup-launcher.vbs); installed by
# install-course-pickup.ps1. Spec and threat model: modules/course-files-fetch/README.md.
#
# An agent session downloads an official course file in the user's logged-in browser (the password step stays
# with the user), then asks for it with request_pickup.py, which writes a request to
# <vault>\_agent\course-fetch\pending\<id>.json. This script moves exactly that file from Downloads into its
# course folder and writes the outcome to <vault>\_agent\course-fetch\done\<id>.result.json.
#
# Any session can write to the vault, so a request is not trusted: it can only name a file the browser
# downloaded from an allowed host (the Zone.Identifier stream says where it came from), of a document type,
# recent, into one of the configured official folders. It never overwrites; the original goes to the Recycle
# Bin only after the copy's hash is verified. URLs are never logged, only hosts. The policy (hosts, folders,
# limits) lives in pickup-settings.json next to this script, OUTSIDE the vault, so a vault writer cannot widen it.
param(
  [string]$SettingsFile = '',   # default: pickup-settings.json next to this script
  [string]$TrashDir = ''        # testing only: move originals here instead of the Recycle Bin
)
$ErrorActionPreference = 'Stop'
if (-not $SettingsFile) { $SettingsFile = Join-Path $PSScriptRoot 'pickup-settings.json' }
$Utf8 = New-Object Text.UTF8Encoding $false

try { $S = Get-Content -LiteralPath $SettingsFile -Raw -Encoding UTF8 | ConvertFrom-Json }
catch { Write-Host "course-pickup: settings not readable ($SettingsFile): run install-course-pickup.ps1"; exit 2 }

$Vault       = [string]$S.vault
$Downloads   = [string]$S.downloads
$LogFile     = if ($S.log_file) { [string]$S.log_file } else { Join-Path $PSScriptRoot 'pickup.log' }
$Hosts       = @($S.allowed_hosts | Where-Object { $_ } | ForEach-Object { ([string]$_).ToLowerInvariant() })
$Folders     = @($S.folders | Where-Object { $_ } | ForEach-Object { [string]$_ })
$Types       = @($S.types | Where-Object { $_ } | ForEach-Object { ([string]$_).ToLowerInvariant().TrimStart('.') })
$MaxMB       = [double]$S.max_mb            # larger files need "approved_large": the user's OK
$MaxAgeHours = [double]$S.max_age_hours     # an older file in Downloads may be an old version
$WaitMinutes = [double]$S.wait_minutes      # how long a request may wait for its file (download or sync still running)
$CheckRef    = [bool]$S.check_referrer      # also accept a file whose ReferrerUrl host is allowed (weaker; default off)
$Guards      = @($S.date_guards | Where-Object { $_ })
$MutexName   = if ($S.mutex) { [string]$S.mutex } else { 'UniOS-CoursePickup' }
if (-not $Vault -or -not $Downloads) { Write-Host 'course-pickup: settings lack vault or downloads'; exit 2 }

$Pending = [IO.Path]::Combine($Vault, '_agent\course-fetch\pending')
$Done    = [IO.Path]::Combine($Vault, '_agent\course-fetch\done')
if (-not (Test-Path -LiteralPath $Pending)) { exit 0 }      # vault not mounted or nothing ever requested
$requests = @(Get-ChildItem -LiteralPath $Pending -Filter '*.json' -File -ErrorAction SilentlyContinue)
if ($requests.Count -eq 0) { exit 0 }

$mutex = New-Object Threading.Mutex($false, $MutexName)
$got = $false
try { $got = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }
if (-not $got) { exit 0 }
Add-Type -AssemblyName Microsoft.VisualBasic

function Write-Utf8($path, $text) { [IO.File]::WriteAllText($path, $text, $Utf8) }

function Write-Log([string]$line) {
  try {
    if ((Test-Path -LiteralPath $LogFile) -and ((Get-Item -LiteralPath $LogFile).Length -gt 500KB)) {
      $keep = Get-Content -LiteralPath $LogFile -Tail 2000
      [IO.File]::WriteAllLines($LogFile, [string[]]$keep, $Utf8)
    }
    [IO.File]::AppendAllText($LogFile, $line + "`r`n", $Utf8)
  } catch { }
}

function Finish($req, $result) {
  if (-not (Test-Path -LiteralPath $Done)) { New-Item -ItemType Directory -Path $Done | Out-Null }
  $result.id = $req.BaseName
  $result.at = (Get-Date).ToString('o')
  $out = Join-Path $Done "$($req.BaseName).result.json"
  Write-Utf8 ($out + '.tmp') ($result | ConvertTo-Json -Compress)
  Move-Item -LiteralPath ($out + '.tmp') -Destination $out -Force
  Move-Item -LiteralPath $req.FullName -Destination (Join-Path $Done "$($req.BaseName).request.json") -Force
  Write-Log "$($result.at) $($result.status) | $($result.file) | $($result.target) | $($result.reason)"
}

# Hosts from the NTFS alternate data stream Zone.Identifier that browsers write on downloads ("mark of the web").
function Zone-Hosts($path) {
  $r = @{ host = $null; referrer = $null }
  try { $zone = Get-Content -LiteralPath $path -Stream Zone.Identifier -ErrorAction Stop } catch { return $r }
  foreach ($line in $zone) {
    if ($line -match '^HostUrl=(.+)$')     { try { $r.host = ([uri]$Matches[1]).Host.ToLowerInvariant() } catch { } }
    if ($line -match '^ReferrerUrl=(.+)$') { try { $r.referrer = ([uri]$Matches[1]).Host.ToLowerInvariant() } catch { } }
  }
  return $r
}
function Host-Allowed([string]$h) {
  if (-not $h) { return $false }
  foreach ($a in $Hosts) { if ($h -eq $a -or ($a.StartsWith('*.') -and $h.EndsWith($a.Substring(1)))) { return $true } }
  return $false
}

function Sha256($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }

function Remove-Original([string]$path) {
  if ($TrashDir) {
    if (-not (Test-Path -LiteralPath $TrashDir)) { New-Item -ItemType Directory -Path $TrashDir -Force | Out-Null }
    Move-Item -LiteralPath $path -Destination (Join-Path $TrashDir ([guid]::NewGuid().ToString('N') + '-' + (Split-Path $path -Leaf)))
  } else {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($path, 'OnlyErrorDialogs', 'SendToRecycleBin')
  }
}

function Handle($req) {
  $age = ((Get-Date) - $req.LastWriteTime).TotalMinutes
  $r = @{ file = ''; target = ''; status = ''; reason = '' }
  try { $q = Get-Content -LiteralPath $req.FullName -Raw -Encoding UTF8 | ConvertFrom-Json }
  catch {
    if ($age -lt $WaitMinutes) { return }     # may still be syncing
    $r.status = 'rejected'; $r.reason = 'request is not valid JSON'; Finish $req $r; return
  }
  # a request may name the machine whose Downloads hold the file; other machines leave it alone
  if ($q.machine -and ([string]$q.machine -ine $env:COMPUTERNAME)) { return }

  $name = [string]$q.file; $target = (([string]$q.target) -replace '\\', '/').Trim('/')
  $r.file = $name; $r.target = $target
  $ext = [IO.Path]::GetExtension($name).TrimStart('.').ToLowerInvariant()

  $problem = $null
  if ($name -notmatch '^[^\\/:*?"<>|\x00-\x1f]+$' -or $name.StartsWith('.') -or $name -match '[. ]$' -or $name.Length -gt 200) { $problem = 'bad file name' }
  elseif ($Types -notcontains $ext) { $problem = "file type .$ext is not allowed" }
  elseif ($Folders -cnotcontains $target) { $problem = 'target is not one of the configured official folders' }
  else {
    foreach ($g in $Guards) {   # integrity: a gated file (e.g. a solution) stays out of the vault before its date
      $gf = ([string]$g.folder).Trim('/')
      if (($target -eq $gf -or $target.StartsWith($gf + '/')) -and $name -match [string]$g.pattern -and
          (Get-Date).Date -lt [datetime]::ParseExact([string]$g.not_before, 'yyyy-MM-dd', $null)) {
        $problem = "date guard: $([string]$g.reason) (not before $([string]$g.not_before))"; break
      }
    }
  }
  if ($problem) { $r.status = 'rejected'; $r.reason = $problem; Finish $req $r; return }
  $dir = [IO.Path]::Combine($Vault, $target.Replace('/', '\'))
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) { $r.status = 'rejected'; $r.reason = 'target folder does not exist'; Finish $req $r; return }

  # Browsers save a second download of a name as "name (1).pdf": take the newest exact or numbered match.
  $base = [IO.Path]::GetFileNameWithoutExtension($name)
  $pattern = '^' + [regex]::Escape($base) + '( \(\d+\))?' + [regex]::Escape([IO.Path]::GetExtension($name)) + '$'
  $source = Get-ChildItem -LiteralPath $Downloads -File | Where-Object { $_.Name -match $pattern } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $source -or ((Get-Date) - $source.LastWriteTime).TotalHours -gt $MaxAgeHours) {
    if ($age -lt $WaitMinutes) { return }     # the download may still be running
    $r.status = 'not-found'; $r.reason = if ($source) { 'only an old copy is in Downloads' } else { 'not in Downloads' }
    Finish $req $r; return
  }

  $r.size = $source.Length
  $z = Zone-Hosts $source.FullName
  $ok = Host-Allowed $z.host
  $shown = if ($z.host) { $z.host } else { 'unknown' }
  if (-not $ok -and $CheckRef -and (Host-Allowed $z.referrer)) { $ok = $true; $shown = "$shown via $($z.referrer)" }
  if (-not $ok) { $r.status = 'rejected'; $r.reason = "not downloaded from an allowed host (source: $shown)"; Finish $req $r; return }
  $r.host = $shown
  if ($source.Length -gt $MaxMB * 1MB -and $q.approved_large -ne $true) {
    $r.status = 'rejected'; $r.reason = "over $MaxMB MB: ask the user, then repeat with --approved-large"; Finish $req $r; return
  }

  $hash = Sha256 $source.FullName
  $r.sha256 = $hash
  $dest = Join-Path $dir $name
  if (Test-Path -LiteralPath $dest) {
    $old = Sha256 $dest
    if ($old -eq $hash) {
      Remove-Original $source.FullName
      $r.status = 'already-there'
    } else {
      $r.status = 'changed-on-server'; $r.reason = 'a different file with this name is in the vault; kept it, the download stays in Downloads'; $r.vault_sha256 = $old
    }
    Finish $req $r; return
  }

  # CreateNew fails if the name appeared meanwhile, so this can never overwrite.
  $in = [IO.File]::OpenRead($source.FullName)
  try {
    $out = [IO.File]::Open($dest, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $in.CopyTo($out) } finally { $out.Close() }
  } finally { $in.Close() }
  if ((Sha256 $dest) -ne $hash) {
    Remove-Item -LiteralPath $dest -Force      # our own partial copy
    throw 'copy failed the hash check'
  }
  Remove-Original $source.FullName
  $r.status = 'filed'
  Finish $req $r
}

try {
  foreach ($req in $requests) {
    try { Handle $req }
    catch {
      Write-Log "$((Get-Date).ToString('o')) error | $($req.Name) | $($_.Exception.Message)"
      if (((Get-Date) - $req.LastWriteTime).TotalMinutes -ge $WaitMinutes) {
        try { Finish $req @{ file = $req.Name; target = ''; status = 'failed'; reason = $_.Exception.Message } } catch { }
      }
    }
  }
} finally { $mutex.ReleaseMutex() }
exit 0
