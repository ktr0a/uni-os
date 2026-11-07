# Tests for vault-watch.ps1 against a throwaway fake vault (never your real vault). Windows PowerShell 5.1.
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<framework>\modules\vault-watch\tests\test-vault-watch.ps1" [-WorkDir "<temp folder>"] [-Keep]
# Exit code 0 = all checks passed, 1 = at least one failed.
param([string]$WorkDir = [IO.Path]::GetTempPath(), [switch]$Keep)
$ErrorActionPreference = 'Stop'
$Script = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\scripts\vault-watch.ps1'))
$Base = Join-Path $WorkDir ('uni-os-vw-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$Vault = Join-Path $Base 'Fake & Vault'          # space and "&" on purpose
$State = Join-Path $Base 'state'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:fail = 0; $script:pass = 0

function Check([bool]$cond, [string]$what) {
    if ($cond) { $script:pass++; Write-Host "PASS  $what" } else { $script:fail++; Write-Host "FAIL  $what" -ForegroundColor Red }
}
function Put([string]$rel, [string]$text = 'x') {
    $p = Join-Path $Vault $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
    [IO.File]::WriteAllText($p, $text, $Utf8)
}
function Run([string]$now, [string[]]$extra = @()) {
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $Script -Root $Vault -StateDir $State -NoToast -NoPush -Now $now @extra 2>&1
    return @{ code = $LASTEXITCODE; out = ($out | Out-String) }
}
function ReadText([string]$rel) { $p = Join-Path $Vault $rel; if (Test-Path -LiteralPath $p) { return [IO.File]::ReadAllText($p) } else { return '' } }
function AlertCount { return @((ReadText '_agent/vault-watch/alerts.md') -split "`n" | Where-Object { $_ -match '^- \d{4}-' }).Count }

New-Item -ItemType Directory -Force -Path $Vault, $State | Out-Null
$config = @{
    modules  = @{ enabled = @('core', 'courses', 'daily-prep', 'inbox-sync', 'vault-watch') }
    paths    = @{ inbox = 'inbox'; never_open = @('**/secret-stuff/**'); handwriting_app_data = 'Notes App/Data' }
    schedule = @{ daily_prep = @('17:30', '19:30'); vault_watch = @('08:17') }
    courses  = @(
        @{ id = 'algo'; short = 'AD'; folder = 'A&D Course'; handwritten_folder = '' },
        @{ id = 'dm'; short = 'DM'; folder = 'DM'; watch_note_subfolders = @('code', 'labs') }
    )
    vault_watch = @{ frozen_dirs = @('archive'); source_top_dirs = @('Notes App') }
}
Put '_agent/uni-os.json' (ConvertTo-Json $config -Depth 6)
Put 'Home.md'; Put 'README.md'; Put 'me/profile.md'; Put 'inbox/inbox.md'; Put '_agent/rules.md'
Put 'A&D Course/ad.md'; Put 'A&D Course/notes/x.md'; Put 'A&D Course/assignments/sheet01.pdf' 'pdf-1'
Put 'A&D Course/A&D handwritten/n1.pdf'; Put 'DM/dm.md'; Put 'DM/code/Main.java'; Put 'DM/labs/lab1.md'; Put 'DM/assignments/Exercise_01.pdf' 'exercise one'
Put 'archive/old/a.pdf'; Put 'private/secret.txt'; Put 'DM/assignments/private/hidden.pdf'
Put 'DM/assignments/secret-stuff/s9.pdf'; Put 'Notes App/Data/appdata.bin'; Put 'Notes App/PDF/p1.pdf'
New-Item -ItemType Directory -Force -Path (Join-Path $Vault 'semester/prep') | Out-Null
$expected = @{
    about = 'test'
    series = @(@{ course = 'dm'; label = 'sheet {nn}'; first_release = '2026-09-17'; count = 3; grace_days = 4; pattern = '^Exercise_0*{n}(?!\d).*\.pdf$'; confidence = 'firm' })
    expected = @(@{ id = 'AD slides 01'; course = 'AD'; label = 'slides 01'; release = '2026-09-20'; alertFrom = '2026-09-22'; confidence = 'soft'; pattern = '^slides-?0*1(?!\d).*\.pdf$' })
}
Put '_agent/vault-watch/sources-expected.json' (ConvertTo-Json $expected -Depth 6)

# ---- run 1: baseline -------------------------------------------------------------------------
$r = Run '2026-09-25 10:00'
Check ($r.code -eq 0) 'run 1 exits 0'
$log = ReadText '_agent/vault-watch/log.md'
Check ($log -match 'baseline taken: \d+ files in scope') 'notes baseline line'
Check ($log -match 'sources: baseline taken') 'sources baseline line'
Check (Test-Path (Join-Path $State 'snapshot.json')) 'notes snapshot written outside the vault'
Check (Test-Path (Join-Path $State 'snapshot-sources.json')) 'sources snapshot written'
$snapText = [IO.File]::ReadAllText((Join-Path $State 'snapshot.json')) + [IO.File]::ReadAllText((Join-Path $State 'snapshot-sources.json'))
Check (-not ($snapText -match 'secret\.txt|hidden\.pdf')) 'never_list folders are not enumerated'
Check (-not ($snapText -match 's9\.pdf')) 'paths.never_open globs (**/x/**) are not enumerated'
Check ((-not ($snapText -match 'appdata\.bin')) -and ($snapText -match 'Notes App/PDF/p1.pdf')) 'note app data folder never listed, its export folder is'
Check (($snapText -match 'DM/code/Main.java') -and ($snapText -match 'DM/labs/lab1.md')) 'course watch_note_subfolders (two of them) are in the notes scope'
Check ($snapText -match 'A(&|\\u0026)D Course/assignments/sheet01.pdf') 'official file in the sources scope'
$al = ReadText '_agent/vault-watch/alerts.md'
Check ($al -match 'Study prep for today missing; the daily prep job \(17:30\)') 'morning prep watchdog alert'
Check ($al -match 'AD slides 01 not in the vault yet \(out Sun 20 Sep\); name is a guess') 'explicit soft row missing alert'
Check (-not ($al -match 'DM sheet 01')) 'series row present -> no alert'
Check ((ReadText '_agent/vault-watch/sources-inventory.tsv') -match "DM/assignments/Exercise_01.pdf`t12`t") 'inventory written with sizes'

# ---- changes ---------------------------------------------------------------------------------
Put 'inbox/2026-09-27_1000_ad-help-update.md'
[IO.File]::SetCreationTime((Join-Path $Vault 'inbox/2026-09-27_1000_ad-help-update.md'), [datetime]'2026-09-27 08:00')
Put 'inbox/drop.png'
Put 'DM/dm (1).md'
Remove-Item -LiteralPath (Join-Path $Vault '_agent/rules.md')
Put 'A&D Course/assignments/sheet02.pdf' 'pdf-2'
foreach ($i in 1..4) { Put "DM/script/part$i.pdf" "p$i" }
Put 'archive/old/a.pdf' 'changed archive'
New-Item -ItemType Directory -Force -Path (Join-Path $Vault 'A&D Course/assignments/old') | Out-Null
Move-Item -LiteralPath (Join-Path $Vault 'A&D Course/assignments/sheet01.pdf') -Destination (Join-Path $Vault 'A&D Course/assignments/old/sheet01.pdf')
New-Item -ItemType Directory -Force -Path (Join-Path $Vault 'random') | Out-Null
Put 'A&D Course/A&D handwritten/n2.pdf'

# ---- dry run writes nothing ------------------------------------------------------------------
$before = (Get-ChildItem -LiteralPath $Base -Recurse -File | ForEach-Object { $_.FullName + $_.Length + $_.LastWriteTimeUtc.Ticks }) -join '|'
$r = Run '2026-09-29 21:30' @('-DryRun')
$after = (Get-ChildItem -LiteralPath $Base -Recurse -File | ForEach-Object { $_.FullName + $_.Length + $_.LastWriteTimeUtc.Ticks }) -join '|'
Check ($before -eq $after) 'dry run writes no file'
Check ($r.out -match '\[dry-run\] alerts.md: .*sync conflict copy DM/dm \(1\).md') 'dry run prints the alerts'

# ---- run 2: alerts ---------------------------------------------------------------------------
$r = Run '2026-09-29 21:30'
Check ($r.code -eq 0) 'run 2 exits 0'
$al = ReadText '_agent/vault-watch/alerts.md'
Check ($al -match 'update note 2026-09-27_1000_ad-help-update.md unapplied >24 h') 'stale update note (creation time older than first sight)'
Check ($al -match 'unsorted file in the inbox: drop.png') 'unsorted inbox file'
Check ($al -match 'Vault: sync conflict copy DM/dm \(1\).md') 'conflict copy'
Check ($al -match 'Vault: file deleted: _agent/rules.md') 'deleted _agent file'
Check ($al -match 'Study prep for tomorrow missing') 'evening prep watchdog'
Check ($al -match 'Sources: new AD file sheet02.pdf in A&D Course/assignments') 'new official file names the course'
Check ($al -match 'Sources: 4 new files in DM/script, e.g. part1.pdf') 'more than 3 new files -> one grouped alert'
Check ($al -match 'Sources: frozen archive archive/old changed') 'frozen archive change'
Check ($al -match 'Sources: new top-level folder in the vault: random \(not watched\)') 'new unwatched top-level folder'
Check ($al -match 'Sources: DM sheet 02 not in the vault yet \(out Thu 24 Sep\)') 'series row missing after grace days'
Check (-not ($al -match 'n2.pdf')) 'quiet (handwritten) area: no new-file alert'
Check (-not ($al -match 'sheet01.pdf')) 'move inside the sources: no alert'
$log = ReadText '_agent/vault-watch/log.md'
Check ($log -match 'moved: A&D Course/assignments/sheet01.pdf -> A&D Course/assignments/old/sheet01.pdf') 'move is logged'
Check ($log -match 'expected missing: .*DM sheet 02') 'expected missing in the sources log line'

# ---- run 3: once-only ------------------------------------------------------------------------
$n = AlertCount
$r = Run '2026-09-29 22:17'
Check ((AlertCount) -eq $n) 'no alert fires twice'

# ---- one phone sender per problem: stuck inbox notes and missing prep notes stay local ----------
$config.vault_watch.push = $true
Put '_agent/uni-os.json' (ConvertTo-Json $config -Depth 6)
Put 'inbox/2026-09-28_0900_la-help-update.md'
[IO.File]::SetCreationTime((Join-Path $Vault 'inbox/2026-09-28_0900_la-help-update.md'), [datetime]'2026-09-28 09:00')
$r = Run '2026-09-30 06:00' @('-DryRun')
Check ($r.out -match 'la-help-update.md unapplied') 'stale note alert still written locally (alerts.md, toast)'
Check (-not ($r.out -match '\[dry-run\] push')) 'a stale-note alert alone sends no vault-watch push (the outcome checks own it)'
Put 'me/profile (1).md'
$r = Run '2026-09-30 06:05' @('-DryRun')
Check ($r.out -match '\[dry-run\] push: Vault watch: 1 new alert,') 'other alerts still push, the stale one is not counted'
Remove-Item -LiteralPath (Join-Path $Vault 'me/profile (1).md'), (Join-Path $Vault 'inbox/2026-09-28_0900_la-help-update.md')
$config.vault_watch.push = $false
Put '_agent/uni-os.json' (ConvertTo-Json $config -Depth 6)

# ---- host-written files are churn, not drift ---------------------------------------------------
Put '_agent/vm/ran/inbox-sync.md' "slot: 2026-09-30 06:15`nran_on_host: 2026-09-30 06:40`nexit: 0`n"
Put '_agent/vm/snapshot.json' '{"schema": 1}'
$r = Run '2026-09-30 06:30'
Check (-not ((ReadText '_agent/vault-watch/log.md') -match '_agent/vm/(ran|snapshot)')) 'the host''s ran-markers and snapshot never show as drift'

# ---- half-mount guard ------------------------------------------------------------------------
foreach ($i in 1..60) { Put "me/bulk/f$i.md" }
$r = Run '2026-09-30 08:17'
$logBefore = ReadText '_agent/vault-watch/log.md'
Remove-Item -LiteralPath (Join-Path $Vault 'me') -Recurse -Force
Remove-Item -LiteralPath (Join-Path $Vault 'A&D Course') -Recurse -Force
$r = Run '2026-09-30 13:17'
Check ((ReadText '_agent/vault-watch/log.md') -eq $logBefore) 'half-mounted vault: run skipped, log untouched'
Check (([IO.File]::ReadAllText((Join-Path $State 'local-log.txt'))) -match 'vault not ready, skipped') 'half-mount skip in the local log'

# ---- state folder inside the vault is refused --------------------------------------------------
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File $Script -Root $Vault -StateDir (Join-Path $Vault '_agent') -NoToast -NoPush 2>&1
Check ($LASTEXITCODE -eq 2) 'state folder inside the vault -> exit 2'

Write-Host ''
Write-Host "$($script:pass) passed, $($script:fail) failed"
if (-not $Keep) { Remove-Item -LiteralPath $Base -Recurse -Force -ErrorAction SilentlyContinue } else { Write-Host "kept: $Base" }
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
