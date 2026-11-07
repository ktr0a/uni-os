# Uni OS vault watch (module vault-watch). EXPERIMENTAL, Windows only.
# Windows PowerShell 5.1, no extra modules. Started by vault-watch-launcher.vbs from the Task Scheduler task
# that register-task.ps1 creates. The precise behaviour spec (for porting to macOS/Linux) is in
# modules/vault-watch/README.md, section "Behaviour specification".
#
# Two scopes, each with its own snapshot and state, kept OUTSIDE the vault in -StateDir:
#   notes   - the vault's note files (an allowlist): snapshot.json, state.json
#   sources - official course material and other source folders: snapshot-sources.json, state-sources.json;
#             expected files from <vault>/_agent/vault-watch/sources-expected.json
# Metadata only (path, size, last-write time): it never opens a file in the vault, because a streaming cloud
# drive would download every file it opens. It reads exactly two small vault files: _agent/uni-os.json (the
# settings) and the expected-files table. It writes into the vault only: _agent/vault-watch/log.md, alerts.md
# and (optional) sources-inventory.tsv. Exit code 0 for every run, skip or error (errors are logged);
# 2 only when no vault path is configured at all.
param(
    [string]$Root = '',              # vault root; default: "vault" in vault-watch.local.json next to this script
    [string]$StateDir = $PSScriptRoot,
    [switch]$NoToast,                # testing: no toasts (files and state are still written)
    [switch]$TestToast,              # testing: show one toast and exit, touches no files
    [switch]$DryRun,                 # testing: print log lines and alerts; writes no file, no state, no toast, no push
    [switch]$NoPush,                 # testing: never call the push command
    [datetime]$Now = (Get-Date)      # testing: simulate a run time, e.g. -Now '2026-10-29 21:30' (use with -DryRun)
)

$ErrorActionPreference = 'Stop'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$AppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'   # PowerShell's AppUserModelID
$Invariant = [Globalization.CultureInfo]::InvariantCulture
$RunKey = $Now.ToString('yyyyMMddHHmm')

# ---- local settings (outside the vault) ------------------------------------------------------------
$LocalFile = Join-Path $PSScriptRoot 'vault-watch.local.json'
$Local = $null
if (Test-Path -LiteralPath $LocalFile) {
    try { $Local = Get-Content -LiteralPath $LocalFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $Local = $null }
}
if (-not $Root -and $Local -and $Local.vault) { $Root = [string]$Local.vault }
if (-not $Root) {
    Write-Host 'vault-watch: no vault path. Pass -Root "<vault>" or run register-task.ps1 -Vault "<vault>" first.'
    exit 2
}
$Root = [IO.Path]::GetFullPath($Root)
if ($Root.Length -gt 3) { $Root = $Root.TrimEnd('\') }      # keep "G:\" for a drive root
$RootPrefix = $Root.TrimEnd('\') + '\'
$StateDir = [IO.Path]::GetFullPath($StateDir)
if (($StateDir.TrimEnd('\') + '\').StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    # state inside the vault would change the vault on every run (sync churn, conflict copies)
    Write-Host "vault-watch: the state folder must be outside the vault ($StateDir)."
    exit 2
}

$SnapFile     = Join-Path $StateDir 'snapshot.json'
$StateFile    = Join-Path $StateDir 'state.json'
$SrcSnapFile  = Join-Path $StateDir 'snapshot-sources.json'
$SrcStateFile = Join-Path $StateDir 'state-sources.json'
$LocalLog     = Join-Path $StateDir 'local-log.txt'
$WatchDir     = [IO.Path]::Combine($Root, '_agent\vault-watch')     # Join-Path throws when the drive is missing
$LogMd        = [IO.Path]::Combine($WatchDir, 'log.md')
$AlertsMd     = [IO.Path]::Combine($WatchDir, 'alerts.md')
$InvFile      = [IO.Path]::Combine($WatchDir, 'sources-inventory.tsv')
$ExpectedFile = [IO.Path]::Combine($WatchDir, 'sources-expected.json')
$ConfigFile   = [IO.Path]::Combine($Root, '_agent\uni-os.json')

function Stamp([datetime]$d) { $d.ToString('yyyy-MM-dd HH:mm', $Invariant) }

function Write-LocalLog([string]$line) {
    if ($DryRun) { Write-Host ('[dry-run] local-log: ' + $line); return }
    try {
        if (-not (Test-Path -LiteralPath $StateDir)) { New-Item -ItemType Directory -Path $StateDir -Force | Out-Null }
        if ((Test-Path -LiteralPath $LocalLog) -and ((Get-Item -LiteralPath $LocalLog).Length -gt 200KB)) {
            $keep = Get-Content -LiteralPath $LocalLog -Tail 500
            [IO.File]::WriteAllLines($LocalLog, [string[]]$keep, $Utf8)
        }
        [IO.File]::AppendAllText($LocalLog, ((Stamp $Now) + ' ' + $line + "`r`n"), $Utf8)
    } catch { }
}

$ToastTitle = 'Uni OS vault watch'
function Show-Toast([string]$text) {
    if ($NoToast -or $DryRun) { if ($DryRun) { Write-Host ('[dry-run] toast: ' + $text) }; return }
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
        $t = [Security.SecurityElement]::Escape($ToastTitle)
        $esc = [Security.SecurityElement]::Escape($text)
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$t</text><text>$esc</text></binding></visual></toast>")
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
    } catch {
        Write-LocalLog ('toast failed: ' + $_.Exception.Message)
    }
}

if ($TestToast) { Show-Toast 'Test toast from vault-watch.ps1 (no file written).'; exit 0 }

function Append-Md([string]$path, [string]$header, [string]$line) {
    if ($DryRun) { Write-Host ('[dry-run] ' + (Split-Path $path -Leaf) + ': ' + $line); return }
    $dir = Split-Path $path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $text = ''
    if (-not (Test-Path -LiteralPath $path)) { $text = $header }
    $text += $line + "`r`n"
    [IO.File]::AppendAllText($path, $text, $Utf8)
}

$LogHeader = "---`r`ntype: agent`r`naudience: agent`r`ntags: [uni/agent, vault-watch]`r`n---`r`n# Vault watch log`r`n`r`nWritten by the vault-watch script on the laptop (Windows Task Scheduler). One line per run and scope; newest at the bottom. Runbook: [RUNBOOK.md](RUNBOOK.md).`r`n`r`n"
$AlertHeader = "---`r`ntype: agent`r`naudience: both`r`ntags: [uni/agent, vault-watch]`r`n---`r`n# Vault watch alerts`r`n`r`nWritten by the vault-watch script. Each alert fires once. Newest at the bottom. Runbook: [RUNBOOK.md](RUNBOOK.md).`r`n`r`n"

# ---- config helpers -------------------------------------------------------------------------------
# Get-Prop returns the value at a dotted path of a ConvertFrom-Json object, or $null. The leading comma keeps
# an (empty) array from being unrolled on return.
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
function Get-List([string]$path, $default) {         # callers wrap the result in @()
    $v = Get-Prop $Config $path
    if ($null -eq $v) { $v = $default }
    foreach ($x in @($v)) { if ($null -ne $x -and [string]$x -ne '') { $x } }
}
function Norm-Rel([string]$p) { return $p.Replace('\', '/').Trim('/') }

function Skip-Name([string]$name) {
    return ($name.StartsWith('.') -or $name -eq 'node_modules' -or $name.StartsWith('~$') -or
            $name.EndsWith('.tmp') -or $name -ieq 'desktop.ini' -or $name -ieq 'Thumbs.db')
}
# Match-Rel: patterns are vault-relative with forward slashes; "dir/**" = the folder and everything below it,
# anything else is a -like wildcard pattern (* matches across "/"). A leading "**/" also matches at the vault
# root ("**/private/**" covers "private/" and "DM/x/private/"). Case-insensitive. A base without * or ? is
# compared literally (folder names may contain "[" which -like would read as a character class).
function Match-Rel([string]$rel, $patterns) {
    $r = $rel.ToLowerInvariant()
    foreach ($p in $patterns) {
        $q = (Norm-Rel ([string]$p)).ToLowerInvariant()
        if (-not $q) { continue }
        $variants = @($q); if ($q.StartsWith('**/')) { $variants += $q.Substring(3) }
        foreach ($v in $variants) {
            if ($v.EndsWith('/**')) {
                $base = $v.Substring(0, $v.Length - 3)
                if ($base.IndexOfAny([char[]]'*?') -ge 0) {
                    if ($r -like $base -or $r -like ($base + '/*')) { return $true }
                } elseif ($r -eq $base -or $r.StartsWith($base + '/')) { return $true }
            } elseif ($v.IndexOfAny([char[]]'*?') -ge 0) {
                if ($r -like $v) { return $true }
            } elseif ($r -eq $v) { return $true }
        }
    }
    return $false
}
function Match-Name([string]$name, $patterns) {
    foreach ($p in $patterns) { if ($name -like [string]$p) { return $true } }
    return $false
}
function Rel-Of([string]$full) { return $full.Substring($RootPrefix.Length).Replace('\', '/') }
function Leaf-Of([string]$rel) { return $rel.Substring($rel.LastIndexOf('/') + 1) }
function Is-Reparse($fsi) { return [bool]($fsi.Attributes -band [IO.FileAttributes]::ReparsePoint) }
function Sig([IO.FileInfo]$f) { return @{ s = [string]$f.Length; t = [string]$f.LastWriteTimeUtc.Ticks } }

function Load-Map([string]$file) {
    $h = @{}
    if (Test-Path -LiteralPath $file) {
        $obj = Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($obj) { foreach ($p in $obj.PSObject.Properties) { $h[$p.Name] = $p.Value } }
    }
    return $h
}
function Save-Json($obj, [string]$file) {
    if ($DryRun) { Write-Host ('[dry-run] not saved: ' + (Split-Path $file -Leaf)); return }
    $tmp = $file + '.tmp'
    [IO.File]::WriteAllText($tmp, (ConvertTo-Json $obj -Depth 4 -Compress), $Utf8)
    Move-Item -LiteralPath $tmp -Destination $file -Force
}
function Parse-Iso([string]$s) { return [datetime]::Parse($s, $Invariant, [Globalization.DateTimeStyles]::RoundtripKind) }
function Parse-Day([string]$s) { return [datetime]::ParseExact($s, 'yyyy-MM-dd', $Invariant) }
function Day-Label([datetime]$d) { return $d.ToString('ddd d MMM', $Invariant) }

# Sends ONE generic push per run (no file names: pushes carry no personal details). Default command:
#   python "<framework>\tools\uni_os.py" push --vault "<vault>" --source vault-watch --id vault-watch "<message>"
# The push gate dedupes per id, so at most one vault-watch push per dedupe window (the original: one per day).
# or vault_watch.push_command = ["exe", "arg", ..., "{message}"] ("{vault}" is replaced too).
function Send-Push([string]$msg) {
    $ErrorActionPreference = 'Continue'
    if ($NoPush -or $DryRun -or -not $PushOn) { if ($DryRun -and $PushOn) { Write-Host ('[dry-run] push: ' + $msg) }; return }
    try {
        $tokens = @(Get-List 'vault_watch.push_command' @())
        if ($tokens.Count -gt 0) {
            $exe = [string]$tokens[0]
            $argv = @($tokens | Select-Object -Skip 1 | ForEach-Object { ([string]$_).Replace('{message}', $msg).Replace('{vault}', $Root) })
        } else {
            $fw = ''; if ($Local -and $Local.framework) { $fw = [string]$Local.framework }
            if (-not $fw) { Write-LocalLog 'push skipped: framework folder unknown (re-run register-task.ps1)'; return }
            $exe = 'python'; if ($Local -and $Local.python) { $exe = [string]$Local.python }
            $argv = @([IO.Path]::Combine($fw, 'tools\uni_os.py'), 'push', '--vault', $Root, '--source', 'vault-watch', '--id', 'vault-watch', $msg)
        }
        $out = & $exe @argv 2>&1
        # push gate exit codes: 0 sent, 10 held for after quiet time, 11 over budget, 12 deduped, 13 refused
        if (@(0, 10, 11, 12, 13) -notcontains $LASTEXITCODE) { Write-LocalLog ("push failed (exit $LASTEXITCODE): " + (($out | Out-String) -replace '\s+', ' ')) }
    } catch { Write-LocalLog ('push failed: ' + $_.Exception.Message) }
}

# ---- main ---------------------------------------------------------------------------------------
$mutex = $null
try {
    if (-not (Test-Path -LiteralPath $StateDir)) { New-Item -ItemType Directory -Path $StateDir -Force | Out-Null }
    $mutex = New-Object Threading.Mutex($false, 'UniOS-VaultWatch')
    $got = $false
    try { $got = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }   # previous run was killed
    if (-not $got) { $mutex = $null; Write-LocalLog 'another run is active, skipped'; exit 0 }

    if (-not (Test-Path -LiteralPath $Root)) {
        Write-LocalLog "vault not reachable ($Root), skipped"
        exit 0
    }
    if (-not (Test-Path -LiteralPath $ConfigFile)) {
        Write-LocalLog 'config _agent/uni-os.json not found, skipped'
        Append-Md $LogMd $LogHeader ("- $(Stamp $Now) | ERROR: _agent/uni-os.json not found; run ``python tools/uni_os.py render`` in the framework folder. Nothing was watched.")
        exit 0
    }
    try { $Config = Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch {
        Write-LocalLog ('config unreadable, skipped: ' + $_.Exception.Message)
        Append-Md $LogMd $LogHeader ("- $(Stamp $Now) | ERROR: _agent/uni-os.json is not valid JSON; nothing was watched.")
        exit 0
    }

    # ---- settings (module defaults; the config wins) ----
    $Enabled         = @(Get-List 'modules.enabled' @())
    $Scopes          = @(Get-List 'vault_watch.scopes' @('notes', 'sources'))
    $ToastTitle      = [string](Cfg 'vault_watch.toast_title' 'Uni OS vault watch')
    $InboxDir        = Norm-Rel ([string](Cfg 'paths.inbox' 'inbox'))
    $NoteRootFiles   = @(Get-List 'vault_watch.note_root_files' @('*.md', '*.canvas', '*.base'))
    $NoteFolders     = @(Get-List 'vault_watch.note_folders' @('me', 'progress', 'semester', 'resources', 'views', 'inbox', '_agent', '_templates') | ForEach-Object { Norm-Rel ([string]$_) })
    $CourseNoteSubs  = @(Get-List 'vault_watch.course_note_subfolders' @('notes', 'reference', 'quiz-prep'))
    $Churn           = @(Get-List 'vault_watch.churn' @('_agent/logs/**', '_agent/inbox-applied/**', '_agent/vault-sync-log.md',
                          '_agent/vault-watch/log.md', '_agent/vault-watch/alerts.md', '_agent/vault-watch/sources-inventory.tsv',
                          '_agent/course-fetch/pending/**', '_agent/course-fetch/done/**', '_agent/heartbeat/state.json',
                          '_agent/heartbeat/flags.json', '_agent/vm/status.md', '_agent/vm/performance.md',
                          '_agent/vm/snapshot.json', '_agent/vm/ran/**', '_agent/uni-os.json', '_agent/.uni-os-manifest.json'))
    # never enumerated: this module's list + the shared privacy key paths.never_open (globs, e.g. "**/private/**")
    # + the note app's own data folder (paths.handwriting_app_data, handwritten-notes module)
    $NeverList       = @(@(Get-List 'vault_watch.never_list' @('private', '*/private')) +
                         @(Get-List 'paths.never_open' @()) + @(Get-List 'paths.handwriting_app_data' @()) |
                         ForEach-Object { [string]$_ } | Where-Object { $_ })
    $SourceTopDirs   = @(Get-List 'vault_watch.source_top_dirs' @() | ForEach-Object { Norm-Rel ([string]$_) })
    $QuietDirs       = @(Get-List 'vault_watch.quiet_dirs' @() | ForEach-Object { Norm-Rel ([string]$_) })
    $QuietPatterns   = @(Get-List 'vault_watch.quiet_patterns' @('*handwritten*'))
    $FrozenDirs      = @(Get-List 'vault_watch.frozen_dirs' @('z_archive', 'archive') | ForEach-Object { Norm-Rel ([string]$_) })
    $IgnoreTopDirs   = @(Get-List 'vault_watch.ignore_top_dirs' @())
    $ConflictPats    = @(Get-List 'vault_watch.conflict_patterns' @('* (1)*', '*conflicted copy*', '*.sync-conflict-*', 'Copy of *'))
    $HalfRatio       = [double](Cfg 'vault_watch.half_mount_ratio' 0.2)
    $HalfMin         = [int](Cfg 'vault_watch.half_mount_min_files' 50)
    $PruneDays       = [int](Cfg 'vault_watch.alert_prune_days' 120)
    $StaleHours      = [double](Cfg 'vault_watch.stale_update_hours' 24)
    $UpdatePats      = @(Get-List 'vault_watch.update_note_patterns' @('*-update.md'))
    $SummaryOver     = [int](Cfg 'vault_watch.toast_summary_over' 3)
    $GroupOver       = [int](Cfg 'vault_watch.group_new_over' 3)
    $MaxPaths        = [int](Cfg 'vault_watch.log_max_paths' 20)
    $PrepOn          = [bool](Cfg 'vault_watch.prep_watchdog' $true) -and ($Enabled -contains 'daily-prep')
    $PrepFolder      = Norm-Rel ([string](Cfg 'vault_watch.prep_folder' 'semester/prep'))
    $PrepPattern     = [string](Cfg 'vault_watch.prep_pattern' 'prep-{date}*.md')
    $PrepMorning     = [string](Cfg 'vault_watch.prep_morning' '08:00-12:00')
    $PrepEvening     = [string](Cfg 'vault_watch.prep_evening_from' '21:00')
    $PrepSlots       = @(Get-List 'schedule.daily_prep' @())
    $StaleOn         = $Enabled -contains 'inbox-sync'
    $WriteInventory  = [bool](Cfg 'vault_watch.write_inventory' $true)
    $PushOn          = [bool](Cfg 'vault_watch.push' $false)
    $NoteExt         = @('.md', '.canvas', '.base')

    $Courses = @()
    foreach ($c in @(Get-List 'courses' @())) {
        $folder = [string](Get-Prop $c 'folder'); if (-not $folder) { continue }
        $folder = Norm-Rel $folder
        $short = [string](Get-Prop $c 'short'); if (-not $short) { $short = $folder }
        $extraSubs = Get-Prop $c 'watch_note_subfolders'      # assign first: @(Get-Prop ...) would wrap the array
        $subs = @($CourseNoteSubs) + @(@($extraSubs) | Where-Object { $_ })
        $hw = [string](Get-Prop $c 'handwritten_folder')
        $Courses += [pscustomobject]@{
            id = [string](Get-Prop $c 'id'); short = $short; folder = $folder
            noteSubs = @($subs | ForEach-Object { [string]$_ }); handwritten = $hw
        }
    }

    $RootDi = New-Object IO.DirectoryInfo $Root
    function Is-NoteScope { return ($Scopes -contains 'notes') }

    # ---- notes scope ----
    function Add-NoteFiles([IO.DirectoryInfo]$di, [bool]$recurse, [bool]$topNotesOnly, [hashtable]$out) {
        $rd = Rel-Of $di.FullName
        if ((Match-Rel $rd $NeverList) -or (Match-Rel $rd $Churn)) { return }      # checked before listing
        foreach ($f in $di.GetFiles()) {
            if (Skip-Name $f.Name) { continue }
            if ($topNotesOnly -and ($NoteExt -notcontains $f.Extension.ToLowerInvariant())) { continue }
            $rel = Rel-Of $f.FullName
            if (Match-Rel $rel $Churn) { continue }
            $out[$rel] = Sig $f
        }
        if ($recurse) {
            foreach ($d in $di.GetDirectories()) {
                if ((Skip-Name $d.Name) -or (Is-Reparse $d)) { continue }
                Add-NoteFiles $d $true $false $out
            }
        }
    }
    function Get-NoteScope {
        $out = @{}
        foreach ($f in $RootDi.GetFiles()) {
            if (Skip-Name $f.Name) { continue }
            if ((Match-Name $f.Name $NoteRootFiles) -and -not (Match-Rel $f.Name $Churn)) { $out[$f.Name] = Sig $f }
        }
        foreach ($d in $NoteFolders) {
            $p = [IO.Path]::Combine($Root, $d.Replace('/', '\'))
            if ([IO.Directory]::Exists($p)) { Add-NoteFiles (New-Object IO.DirectoryInfo $p) $true $false $out }
        }
        foreach ($c in $Courses) {
            $p = [IO.Path]::Combine($Root, $c.folder.Replace('/', '\'))
            if (-not [IO.Directory]::Exists($p)) { continue }
            Add-NoteFiles (New-Object IO.DirectoryInfo $p) $false $true $out
            foreach ($s in $c.noteSubs) {
                $sp = [IO.Path]::Combine($p, $s.Replace('/', '\'))
                if ([IO.Directory]::Exists($sp)) { Add-NoteFiles (New-Object IO.DirectoryInfo $sp) $true $false $out }
            }
        }
        return $out
    }

    # ---- sources scope ----
    function Add-SrcFiles([IO.DirectoryInfo]$di, [hashtable]$out) {
        if (Match-Rel (Rel-Of $di.FullName) $NeverList) { return }     # checked before anything inside is listed
        foreach ($f in $di.GetFiles()) { if (Skip-Name $f.Name) { continue }; $out[(Rel-Of $f.FullName)] = Sig $f }
        foreach ($d in $di.GetDirectories()) {
            if ((Skip-Name $d.Name) -or (Is-Reparse $d)) { continue }
            if (Match-Rel (Rel-Of $d.FullName) $NeverList) { continue }
            Add-SrcFiles $d $out
        }
    }
    function In-Course([string]$rel) {
        $rl = $rel.ToLowerInvariant()
        foreach ($c in $Courses) { if ($rl.StartsWith($c.folder.ToLowerInvariant() + '/')) { return $c } }
        return $null
    }
    function Get-SourceScope {
        $out = @{}
        foreach ($f in $RootDi.GetFiles()) {                                   # loose non-note files at the root
            if ((Skip-Name $f.Name) -or (Match-Name $f.Name $NoteRootFiles)) { continue }
            $out[$f.Name] = Sig $f
        }
        foreach ($c in $Courses) {
            $p = [IO.Path]::Combine($Root, $c.folder.Replace('/', '\'))
            if (-not [IO.Directory]::Exists($p)) { continue }
            if (Match-Rel $c.folder $NeverList) { continue }
            $cdi = New-Object IO.DirectoryInfo $p
            foreach ($f in $cdi.GetFiles()) {                                   # handouts, stubs at the course top
                if ((Skip-Name $f.Name) -or ($NoteExt -contains $f.Extension.ToLowerInvariant())) { continue }
                $out[(Rel-Of $f.FullName)] = Sig $f
            }
            foreach ($d in $cdi.GetDirectories()) {
                if ((Skip-Name $d.Name) -or (Is-Reparse $d)) { continue }
                if ($c.noteSubs -contains $d.Name) { continue }
                Add-SrcFiles $d $out
            }
        }
        foreach ($t in @($SourceTopDirs + $QuietDirs + $FrozenDirs | Sort-Object -Unique)) {
            if ($null -ne (In-Course ($t + '/x'))) { continue }                 # inside a course folder: already listed
            $p = [IO.Path]::Combine($Root, $t.Replace('/', '\'))
            if ([IO.Directory]::Exists($p)) { Add-SrcFiles (New-Object IO.DirectoryInfo $p) $out }
        }
        return $out
    }
    # kind: normal | quiet | frozen; group: folder used for grouping alerts; course: course object or $null
    function Get-SrcArea([string]$rel) {
        $parent = if ($rel.Contains('/')) { $rel.Substring(0, $rel.LastIndexOf('/')) } else { '(vault root)' }
        $rl = $rel.ToLowerInvariant()
        foreach ($fz in $FrozenDirs) {
            if ($rl.StartsWith($fz.ToLowerInvariant() + '/')) {
                $rest = $rel.Substring($fz.Length + 1).Split('/')
                $g = if ($rest.Count -gt 1) { $fz + '/' + $rest[0] } else { $fz }
                return @{ kind = 'frozen'; group = $g; course = $null; parent = $parent }
            }
        }
        $course = In-Course $rel
        $quiet = $false
        foreach ($q in $QuietDirs) { if ($rl.StartsWith($q.ToLowerInvariant() + '/')) { $quiet = $true; break } }
        if (-not $quiet -and $null -ne $course) {
            $rest = $rel.Substring($course.folder.Length + 1)
            if ($rest.Contains('/')) {
                $first = $rest.Substring(0, $rest.IndexOf('/'))
                if ((Match-Name $first $QuietPatterns) -or ($course.handwritten -and $first -ieq $course.handwritten)) { $quiet = $true }
            }
        }
        return @{ kind = $(if ($quiet) { 'quiet' } else { 'normal' }); group = $parent; course = $course; parent = $parent }
    }
    function Is-ConflictName([string]$leaf) { return (Match-Name $leaf $ConflictPats) }

    function Format-Line([string]$head, $sets) {
        $parts = @($head)
        $budget = $MaxPaths
        foreach ($set in $sets) {
            $items = @($set[1])
            if ($items.Count -gt 0 -and $budget -gt 0) {
                $take = @($items | Select-Object -First $budget)
                $budget -= $take.Count
                $parts += ($set[0] + ': ' + ($take -join '; '))
            }
        }
        return ($parts -join ' | ')
    }

    $alerts = New-Object System.Collections.ArrayList
    # Alerts that another module's outcome check already pushes to the phone (stuck inbox notes,
    # missing prep notes: ONE sender per problem, see the notifications module) stay local here:
    # alerts.md and a toast, but they don't count towards this script's own phone push.
    $localOnly = 0
    $today = $Now.ToString('yyyy-MM-dd')
    $cut = $Now.AddDays(-$PruneDays)

    # ================= notes scope =================
    $new = New-Object System.Collections.Generic.List[string]
    $cur = @{}
    $notesOk = $false
    if (Is-NoteScope) {
        $snapExists = Test-Path -LiteralPath $SnapFile
        $old = Load-Map $SnapFile           # rel -> object with s, t
        $cur = Get-NoteScope

        # half-mount guard: the scope is suddenly (almost) empty -> the drive is not ready; skip the whole run
        if ($snapExists -and $old.Count -ge $HalfMin -and $cur.Count -lt ($old.Count * $HalfRatio)) {
            Write-LocalLog "notes scope has only $($cur.Count) files vs $($old.Count) in the snapshot; vault not ready, skipped"
            exit 0
        }

        $stateRaw = Load-Map $StateFile
        $alerted = @{};   if ($stateRaw.ContainsKey('alerted'))   { foreach ($p in $stateRaw['alerted'].PSObject.Properties)   { $alerted[$p.Name] = $p.Value } }
        $inboxSeen = @{}; if ($stateRaw.ContainsKey('inboxSeen')) { foreach ($p in $stateRaw['inboxSeen'].PSObject.Properties) { $inboxSeen[$p.Name] = $p.Value } }

        $changed = New-Object System.Collections.Generic.List[string]
        $deleted = New-Object System.Collections.Generic.List[string]
        if ($snapExists) {
            foreach ($k in ($cur.Keys | Sort-Object)) {
                if (-not $old.ContainsKey($k)) { $new.Add($k) }
                elseif ([string]$old[$k].s -ne $cur[$k].s -or [string]$old[$k].t -ne $cur[$k].t) { $changed.Add($k) }
            }
            foreach ($k in ($old.Keys | Sort-Object)) { if (-not $cur.ContainsKey($k)) { $deleted.Add($k) } }
        }

        if (-not $snapExists) { $line = "$(Stamp $Now) | baseline taken: $($cur.Count) files in scope (no alerts)" }
        else {
            $line = Format-Line "$(Stamp $Now) | new $($new.Count), changed $($changed.Count), deleted $($deleted.Count)" @(@('new', $new), @('changed', $changed), @('deleted', $deleted))
        }
        Append-Md $LogMd $LogHeader ('- ' + $line)

        function Add-Alert([string]$key, [string]$text) {
            if (-not $alerted.ContainsKey($key)) {
                $alerted[$key] = $Now.ToString('o'); [void]$alerts.Add($text)
                if ($key.StartsWith('stale:') -or $key.StartsWith('prep-')) { $script:localOnly++ }
            }
        }
        $inboxPrefix = $InboxDir + '/'

        # a) update notes in the inbox not applied within N hours (inbox-sync module)
        if ($StaleOn) {
            $inboxFiles = @($cur.Keys | Where-Object { $_.StartsWith($inboxPrefix, [StringComparison]::OrdinalIgnoreCase) -and
                                                       -not $_.Substring($inboxPrefix.Length).Contains('/') -and
                                                       (Match-Name (Leaf-Of $_) $UpdatePats) })
            foreach ($rel in $inboxFiles) {
                if (-not $inboxSeen.ContainsKey($rel)) { $inboxSeen[$rel] = $Now.ToString('o') }
                $first = Parse-Iso ([string]$inboxSeen[$rel])
                $since = $first
                try {
                    $created = [IO.File]::GetCreationTime([IO.Path]::Combine($Root, $rel.Replace('/', '\')))
                    if ($created -lt $first) { $since = $created }
                } catch { }
                if (($Now - $since).TotalHours -gt $StaleHours) {
                    Add-Alert "stale:$rel" "Vault: update note $(Leaf-Of $rel) unapplied >$([int]$StaleHours) h, the inbox sync did not run or parked it"
                }
            }
            foreach ($k in @($inboxSeen.Keys)) { if ($inboxFiles -notcontains $k) { $inboxSeen.Remove($k) } }
        }

        # b) unsorted new file in the inbox (not an update note, not the index note)
        foreach ($rel in $new) {
            if ($rel.StartsWith($inboxPrefix, [StringComparison]::OrdinalIgnoreCase)) {
                $name = $rel.Substring($inboxPrefix.Length)
                if (-not (Match-Name (Leaf-Of $rel) $UpdatePats) -and $name -ine 'inbox.md') {
                    Add-Alert "unsorted:$rel" "Vault: unsorted file in the inbox: $name"
                }
            }
        }

        # c) sync conflict copies (in scope, plus conflict-named .md/.canvas at the root the allowlist could miss)
        $conflictNames = @($cur.Keys)
        foreach ($f in $RootDi.GetFiles()) {
            if (($f.Extension -eq '.md' -or $f.Extension -eq '.canvas') -and -not (Skip-Name $f.Name)) { $conflictNames += $f.Name }
        }
        foreach ($rel in ($conflictNames | Sort-Object -Unique)) {
            if (Is-ConflictName (Leaf-Of $rel)) { Add-Alert "conflict:$rel" "Vault: sync conflict copy $rel" }
        }

        # d) a file deleted at the vault root or under _agent/ (the key holds the run stamp: it can alert again later)
        foreach ($rel in $deleted) {
            if (-not $rel.Contains('/') -or $rel.StartsWith('_agent/', [StringComparison]::OrdinalIgnoreCase)) {
                Add-Alert ("deleted:${rel}:" + $RunKey) "Vault: file deleted: $rel"
            }
        }

        # e) prep watchdog (daily-prep module): today's note missing in the morning window, tomorrow's in the evening
        if ($PrepOn) {
            $prepDir = [IO.Path]::Combine($Root, $PrepFolder.Replace('/', '\'))
            $slot = ''; if ($PrepSlots.Count -gt 0) { $slot = ' (' + [string]$PrepSlots[0] + ')' }
            function Has-Prep([string]$day) {
                if (-not [IO.Directory]::Exists($prepDir)) { return $false }
                return [bool](Get-ChildItem -LiteralPath $prepDir -Filter ($PrepPattern.Replace('{date}', $day)) -File -ErrorAction SilentlyContinue)
            }
            $win = $PrepMorning.Split('-')
            if ($win.Count -eq 2 -and $Now.TimeOfDay -ge [TimeSpan]$win[0] -and $Now.TimeOfDay -lt [TimeSpan]$win[1]) {
                if (-not (Has-Prep $today)) { Add-Alert "prep-$today-morning" "Study prep for today missing; the daily prep job$slot may not have run" }
            }
            if ($PrepEvening -and $Now.TimeOfDay -ge [TimeSpan]$PrepEvening) {
                $tomorrow = $Now.AddDays(1).ToString('yyyy-MM-dd')
                if (-not (Has-Prep $tomorrow)) { Add-Alert "prep-$tomorrow-evening" "Study prep for tomorrow missing; the daily prep job$slot may not have run" }
            }
        }
        $notesOk = $true
    }

    # ================= sources scope (own snapshot/state; an error here never blocks the notes scope) =================
    $srcOk = $false
    if ($Scopes -contains 'sources') {
        try {
            $exp = $null
            if (Test-Path -LiteralPath $ExpectedFile) {
                try { $exp = Get-Content -LiteralPath $ExpectedFile -Raw -Encoding UTF8 | ConvertFrom-Json }
                catch { $exp = $null; Write-LocalLog ('sources: expected table unreadable, missing-file check skipped: ' + $_.Exception.Message) }
            }

            $srcSnapExists = Test-Path -LiteralPath $SrcSnapFile
            $srcOld = Load-Map $SrcSnapFile
            $srcCur = Get-SourceScope
            $srcState = Load-Map $SrcStateFile
            $srcAlerted = @{}; if ($srcState.ContainsKey('alerted')) { foreach ($p in $srcState['alerted'].PSObject.Properties) { $srcAlerted[$p.Name] = $p.Value } }
            $hadTop = $srcState.ContainsKey('topDirs')
            $knownTop = @(); if ($hadTop) { $knownTop = @($srcState['topDirs'] | ForEach-Object { [string]$_ }) }
            $topNow = @($RootDi.GetDirectories() | Where-Object { -not (Skip-Name $_.Name) } | ForEach-Object { $_.Name } | Sort-Object)
            $watchedTop = @($NoteFolders + ($Courses | ForEach-Object { $_.folder }) + $SourceTopDirs + $QuietDirs + $FrozenDirs + $IgnoreTopDirs |
                            ForEach-Object { ([string]$_).Split('/')[0] })

            if ($DryRun) {
                Write-Host "[dry-run] sources in scope: $($srcCur.Count) files"
                $srcCur.Keys | Group-Object { $p = $_.Split('/'); if ($p.Count -ge 3) { $p[0] + '/' + $p[1] } else { $p[0] } } | Sort-Object Name |
                    ForEach-Object { Write-Host ('[dry-run]   ' + $_.Name + ': ' + $_.Count + ' (' + (Get-SrcArea $_.Group[0]).kind + ')') }
            }

            if ($srcSnapExists -and $srcOld.Count -ge $HalfMin -and $srcCur.Count -lt ($srcOld.Count * $HalfRatio)) {
                Write-LocalLog "sources: only $($srcCur.Count) files vs $($srcOld.Count) in the snapshot; vault not ready, skipped"
                Append-Md $LogMd $LogHeader ("- $(Stamp $Now) | sources: skipped, only $($srcCur.Count) files vs $($srcOld.Count) in the snapshot (vault not ready)")
            } else {
                function Add-SrcAlert([string]$key, [string]$text) {
                    if (-not $srcAlerted.ContainsKey($key)) { $srcAlerted[$key] = $Now.ToString('o'); [void]$srcAlerts.Add($text) }
                }
                $srcAlerts = New-Object System.Collections.ArrayList

                # diff (empty on the baseline run, so the baseline is silent)
                $sNew = New-Object System.Collections.Generic.List[string]
                $sChanged = New-Object System.Collections.Generic.List[string]
                $sDeleted = New-Object System.Collections.Generic.List[string]
                if ($srcSnapExists) {
                    foreach ($k in ($srcCur.Keys | Sort-Object)) {
                        if (-not $srcOld.ContainsKey($k)) { $sNew.Add($k) }
                        elseif ([string]$srcOld[$k].s -ne $srcCur[$k].s -or [string]$srcOld[$k].t -ne $srcCur[$k].t) { $sChanged.Add($k) }
                    }
                    foreach ($k in ($srcOld.Keys | Sort-Object)) { if (-not $srcCur.ContainsKey($k)) { $sDeleted.Add($k) } }
                }

                # moves inside the sources: deleted + new with the same size and time (pass 1) or the same name and size (pass 2); log only
                $moves = New-Object System.Collections.Generic.List[string]; $movedFrom = @{}; $movedTo = @{}
                foreach ($pass in 1, 2) {
                    $idx = @{}
                    foreach ($k in $sNew) {
                        if ($movedTo.ContainsKey($k)) { continue }
                        $sg = if ($pass -eq 1) { $srcCur[$k].s + '|' + $srcCur[$k].t } else { (Leaf-Of $k).ToLowerInvariant() + '|' + $srcCur[$k].s }
                        if (-not $idx.ContainsKey($sg)) { $idx[$sg] = $k }
                    }
                    foreach ($k in $sDeleted) {
                        if ($movedFrom.ContainsKey($k)) { continue }
                        $sg = if ($pass -eq 1) { [string]$srcOld[$k].s + '|' + [string]$srcOld[$k].t } else { (Leaf-Of $k).ToLowerInvariant() + '|' + [string]$srcOld[$k].s }
                        if ($idx.ContainsKey($sg) -and -not $movedTo.ContainsKey($idx[$sg])) {
                            $to = $idx[$sg]; $movedFrom[$k] = $to; $movedTo[$to] = $k; $moves.Add("$k -> $to")
                        }
                    }
                }
                # files that left the sources for the notes scope (same size and time as a new note-scope file)
                $noteIdx = @{}
                foreach ($k in $new) { $sg = $cur[$k].s + '|' + $cur[$k].t; if (-not $noteIdx.ContainsKey($sg)) { $noteIdx[$sg] = $k } }

                # 1) frozen folders: any change (raw, moves included) = one alert per frozen subfolder per run
                $fz = [ordered]@{}
                foreach ($set in @(@('new', $sNew), @('changed', $sChanged), @('deleted', $sDeleted))) {
                    foreach ($k in @($set[1])) {
                        $a = Get-SrcArea $k
                        if ($a.kind -ne 'frozen') { continue }
                        if (-not $fz.Contains($a.group)) { $fz[$a.group] = @{ new = 0; changed = 0; deleted = 0; eg = (Leaf-Of $k) } }
                        $h = $fz[$a.group]; $h[$set[0]] = $h[$set[0]] + 1
                    }
                }
                foreach ($g in $fz.Keys) {
                    $h = $fz[$g]
                    Add-SrcAlert "srcfrozen:${g}:$RunKey" "Sources: frozen archive $g changed (new $($h.new), changed $($h.changed), deleted $($h.deleted); e.g. $($h.eg))"
                }

                # 2) new files: conflict copies everywhere (not frozen); a new-file alert for normal areas (quiet = log only);
                #    more than N new files in one folder in one run become one alert
                $newByParent = [ordered]@{}
                foreach ($k in $sNew) {
                    if ($movedTo.ContainsKey($k)) { continue }
                    $a = Get-SrcArea $k
                    if ($a.kind -eq 'frozen') { continue }
                    if (Is-ConflictName (Leaf-Of $k)) { Add-SrcAlert "srcconflict:$k" "Sources: sync conflict copy $k"; continue }
                    if ($a.kind -eq 'quiet') { continue }
                    if (-not $newByParent.Contains($a.parent)) { $newByParent[$a.parent] = New-Object System.Collections.ArrayList }
                    [void]$newByParent[$a.parent].Add($k)
                }
                foreach ($par in $newByParent.Keys) {
                    $list = @($newByParent[$par])
                    $course = (Get-SrcArea $list[0]).course
                    $who = if ($null -ne $course) { "$($course.short) file" } else { 'file' }
                    if ($list.Count -gt $GroupOver) {
                        $eg = (@($list | Select-Object -First 3) | ForEach-Object { Leaf-Of $_ }) -join '; '
                        Add-SrcAlert "srcnew:${par}:$RunKey" "Sources: $($list.Count) new files in $par, e.g. $eg"
                    } else {
                        foreach ($k in $list) { Add-SrcAlert ("srcnew:${k}:" + $srcCur[$k].t) "Sources: new $who $(Leaf-Of $k) in $par" }
                    }
                }

                # 3) deleted or moved out of the sources (not frozen, not a move inside the sources); > N per folder = one alert
                $delByParent = [ordered]@{}
                foreach ($k in $sDeleted) {
                    if ($movedFrom.ContainsKey($k)) { continue }
                    $a = Get-SrcArea $k
                    if ($a.kind -eq 'frozen') { continue }
                    if (-not $delByParent.Contains($a.parent)) { $delByParent[$a.parent] = New-Object System.Collections.ArrayList }
                    [void]$delByParent[$a.parent].Add($k)
                }
                foreach ($par in $delByParent.Keys) {
                    $list = @($delByParent[$par])
                    if ($list.Count -gt $GroupOver) {
                        $eg = (@($list | Select-Object -First 3) | ForEach-Object { Leaf-Of $_ }) -join '; '
                        Add-SrcAlert "srcdel:${par}:$RunKey" "Sources: $($list.Count) files deleted or moved out of $par, e.g. $eg"
                    } else {
                        foreach ($k in $list) {
                            $sg = [string]$srcOld[$k].s + '|' + [string]$srcOld[$k].t
                            $txt = if ($noteIdx.ContainsKey($sg)) { "Sources: $k moved out of the source folders into the notes ($($noteIdx[$sg]))" } else { "Sources: $k deleted or moved out of the source folders" }
                            Add-SrcAlert "srcdel:${k}:$RunKey" $txt
                        }
                    }
                }

                # 4) expected but missing (sources-expected.json): explicit rows plus expanded series
                $rows = New-Object System.Collections.ArrayList
                function Resolve-Course([string]$name) {
                    foreach ($c in $Courses) { if ($c.id -ieq $name -or $c.short -ieq $name -or $c.folder -ieq $name) { return $c } }
                    return [pscustomobject]@{ id = $name; short = $name; folder = (Norm-Rel $name); noteSubs = @(); handwritten = '' }
                }
                if ($null -ne $exp) {
                    foreach ($r in @($exp.expected)) {
                        if ($null -eq $r -or -not $r.pattern) { continue }
                        [void]$rows.Add(@{ id = [string]$r.id; course = (Resolve-Course ([string]$r.course)); label = [string]$r.label
                            release = [string]$r.release; alertFrom = [string]$r.alertFrom; remindFrom = [string]$r.remindFrom
                            confidence = [string]$r.confidence; pattern = [string]$r.pattern; minBytes = [long]$r.minBytes })
                    }
                    foreach ($s in @($exp.series)) {
                        if ($null -eq $s -or -not $s.pattern -or -not $s.first_release) { continue }
                        $n = 1; if ($null -ne $s.start) { $n = [int]$s.start }
                        $every = 7; if ($null -ne $s.every_days) { $every = [int]$s.every_days }
                        $count = 1; if ($null -ne $s.count) { $count = [int]$s.count }
                        $grace = 2; if ($null -ne $s.grace_days) { $grace = [int]$s.grace_days }
                        $skip = @(@($s.skip_dates) | Where-Object { $_ } | ForEach-Object { [string]$_ })
                        $crs = Resolve-Course ([string]$s.course)
                        $d = Parse-Day ([string]$s.first_release)
                        $made = 0; $guard = 0
                        while ($made -lt $count -and $guard -lt 400) {
                            $guard++
                            $ds = $d.ToString('yyyy-MM-dd')
                            if ($skip -contains $ds) { $d = $d.AddDays($every); continue }
                            $nn = $n.ToString('00', $Invariant)
                            $label = ([string]$s.label).Replace('{nn}', $nn).Replace('{n}', [string]$n)
                            $remind = ''; if ($null -ne $s.remind_days) { $remind = $d.AddDays([int]$s.remind_days).ToString('yyyy-MM-dd') }
                            $minB = 0; if ($null -ne $s.min_bytes) { $minB = [long]$s.min_bytes }
                            $conf = 'firm'; if ($s.confidence) { $conf = [string]$s.confidence }
                            [void]$rows.Add(@{ id = "$($crs.short) $label"; course = $crs; label = $label; release = $ds
                                alertFrom = $d.AddDays($grace).ToString('yyyy-MM-dd'); remindFrom = $remind; confidence = $conf
                                pattern = ([string]$s.pattern).Replace('{nn}', $nn).Replace('{n}', [string]$n); minBytes = $minB })
                            $made++; $n++; $d = $d.AddDays($every)
                        }
                    }
                }
                $missingNow = New-Object System.Collections.Generic.List[string]
                foreach ($row in $rows) {
                    try { $notYet = (-not $row.alertFrom -or (Parse-Day $row.alertFrom) -gt $Now.Date); $null = if ($row.release) { Parse-Day $row.release } }
                    catch { Write-LocalLog "sources: expected row '$($row.id)' has a bad date (use YYYY-MM-DD), skipped"; continue }
                    if ($row.remindFrom) { try { $null = Parse-Day $row.remindFrom } catch { $row.remindFrom = '' } }
                    if ($notYet) { continue }
                    $prefix = $row.course.folder.ToLowerInvariant() + '/'
                    $hits = @()
                    foreach ($k in $srcCur.Keys) {
                        if (-not $k.ToLowerInvariant().StartsWith($prefix)) { continue }
                        if ((Get-SrcArea $k).kind -ne 'normal') { continue }
                        if ((Leaf-Of $k) -match $row.pattern) { $hits += $k }
                    }
                    $rd = if ($row.release) { Day-Label (Parse-Day $row.release) } else { '?' }
                    if ($hits.Count -eq 0) {
                        $missingNow.Add($row.id)
                        $txt = "Sources: $($row.course.short) $($row.label) not in the vault yet (out $rd)"
                        if ($row.confidence -eq 'soft') { $txt += '; name is a guess, it may have come under another name' }
                        Add-SrcAlert ('missing:' + $row.id) $txt
                        if ($row.remindFrom -and (Parse-Day $row.remindFrom) -le $Now.Date) {
                            Add-SrcAlert ('remind:' + $row.id) "Sources: reminder: $($row.course.short) $($row.label) still not in the vault (out $rd)"
                        }
                    } elseif ($row.minBytes -gt 0) {
                        $big = @($hits | Where-Object { [long]$srcCur[$_].s -ge $row.minBytes })
                        if ($big.Count -eq 0) {
                            $kb = [math]::Round([long]$srcCur[$hits[0]].s / 1024)
                            Add-SrcAlert ('small:' + $row.id) "Sources: $($row.course.short) $($row.label) is in the vault but looks too small ($kb KB): $(Leaf-Of $hits[0])"
                        }
                    }
                }

                # 5) new top-level folder that neither scope watches; the first run records the list silently
                $newTop = @(); $goneTop = @()
                if ($hadTop) {
                    $newTop = @($topNow | Where-Object { $knownTop -notcontains $_ })
                    $goneTop = @($knownTop | Where-Object { $topNow -notcontains $_ })
                    foreach ($t in $newTop) {
                        if ($watchedTop -contains $t) { continue }
                        Add-SrcAlert "srctop:$t" "Sources: new top-level folder in the vault: $t (not watched)"
                    }
                }

                # log line
                $nNew = @($sNew | Where-Object { -not $movedTo.ContainsKey($_) })
                $nDel = @($sDeleted | Where-Object { -not $movedFrom.ContainsKey($_) })
                if (-not $srcSnapExists) { $sline = "$(Stamp $Now) | sources: baseline taken: $($srcCur.Count) files in scope (no alerts)" }
                else {
                    $sline = Format-Line "$(Stamp $Now) | sources: new $($nNew.Count), changed $($sChanged.Count), deleted $($nDel.Count), moved $($moves.Count)" @(@('new', $nNew), @('changed', $sChanged), @('deleted', $nDel), @('moved', $moves))
                }
                if ($missingNow.Count -gt 0) { $sline += ' | expected missing: ' + ($missingNow -join '; ') }
                if ($newTop.Count -gt 0)     { $sline += ' | new top-level folder: ' + ($newTop -join '; ') }
                if ($goneTop.Count -gt 0)    { $sline += ' | top-level folder gone: ' + ($goneTop -join '; ') }
                Append-Md $LogMd $LogHeader ('- ' + $sline)

                # inventory for agents (metadata only), rewritten only when something changed
                $srcChanges = $nNew.Count + $sChanged.Count + $nDel.Count + $moves.Count
                if ($WriteInventory -and -not $DryRun -and (-not $srcSnapExists -or $srcChanges -gt 0 -or -not (Test-Path -LiteralPath $InvFile))) {
                    $sb = New-Object System.Text.StringBuilder
                    [void]$sb.Append("path`tsize_bytes`tmodified_utc`tarea`n")
                    foreach ($k in ($srcCur.Keys | Sort-Object)) {
                        $mod = [DateTime]::new([long]$srcCur[$k].t, [DateTimeKind]::Utc).ToString('yyyy-MM-ddTHH:mm:ssZ', $Invariant)
                        [void]$sb.Append("$k`t$($srcCur[$k].s)`t$mod`t$((Get-SrcArea $k).kind)`n")
                    }
                    if (-not (Test-Path -LiteralPath $WatchDir)) { New-Item -ItemType Directory -Path $WatchDir -Force | Out-Null }
                    [IO.File]::WriteAllText($InvFile, $sb.ToString(), $Utf8)
                }

                foreach ($a in $srcAlerts) { [void]$alerts.Add($a) }
                $srcOk = $true
            }
        } catch {
            $srcOk = $false
            $smsg = ($_.Exception.Message -replace '\s+', ' ')
            Write-LocalLog ('sources ERROR: ' + $smsg + ' @ line ' + $_.InvocationInfo.ScriptLineNumber)
            try { Append-Md $LogMd $LogHeader ("- $(Stamp $Now) | sources: ERROR: $smsg") } catch { }
        }
    }

    # ---- deliver alerts (both scopes): alerts.md, toasts (one summary toast if many), at most one push ----
    foreach ($a in $alerts) { Append-Md $AlertsMd $AlertHeader ("- $(Stamp $Now) - $a") }
    if ($alerts.Count -gt $SummaryOver) { Show-Toast "$($alerts.Count) vault alerts, see _agent/vault-watch/alerts.md" }
    else { foreach ($a in $alerts) { Show-Toast $a } }
    $pushCount = $alerts.Count - $localOnly
    if ($pushCount -gt 0) {
        $word = if ($pushCount -eq 1) { 'alert' } else { 'alerts' }
        Send-Push "Vault watch: $pushCount new $word, see _agent/vault-watch/alerts.md"
    }

    # ---- save state, then snapshot (atomic writes) ----
    if ($notesOk) {
        foreach ($k in @($alerted.Keys)) { try { if ((Parse-Iso ([string]$alerted[$k])) -lt $cut) { $alerted.Remove($k) } } catch { } }
        Save-Json @{ alerted = $alerted; inboxSeen = $inboxSeen; day = $today } $StateFile
        Save-Json $cur $SnapFile
    }
    # sources: only after a complete pass; 'missing:', 'remind:' and 'small:' keys are never pruned
    if ($srcOk) {
        foreach ($k in @($srcAlerted.Keys)) {
            if ($k.StartsWith('missing:') -or $k.StartsWith('remind:') -or $k.StartsWith('small:')) { continue }
            try { if ((Parse-Iso ([string]$srcAlerted[$k])) -lt $cut) { $srcAlerted.Remove($k) } } catch { }
        }
        Save-Json @{ alerted = $srcAlerted; topDirs = @($topNow); day = $today } $SrcStateFile
        Save-Json $srcCur $SrcSnapFile
    }
}
catch {
    $msg = ($_.Exception.Message -replace '\s+', ' ')
    Write-LocalLog ('ERROR: ' + $msg + ' @ line ' + $_.InvocationInfo.ScriptLineNumber)
    try { if (Test-Path -LiteralPath $Root) { Append-Md $LogMd $LogHeader ("- $(Stamp $Now) | ERROR: $msg") } } catch { }
}
finally {
    if ($null -ne $mutex) { try { $mutex.ReleaseMutex() } catch { } }
}
exit 0
