# Tests for install-course-pickup.ps1 (-NoRegister) and course-pickup.ps1 against a throwaway fake vault and a fake
# Downloads folder (never your real ones; originals go to a test trash folder, not the Recycle Bin; no task is
# registered). Windows PowerShell 5.1 on NTFS (the test writes Zone.Identifier streams).
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<framework>\modules\course-files-fetch\tests\test-course-pickup.ps1" [-WorkDir "<temp folder>"] [-Keep]
# Exit code 0 = all checks passed, 1 = at least one failed.
param([string]$WorkDir = [IO.Path]::GetTempPath(), [switch]$Keep)
$ErrorActionPreference = 'Stop'
$Scripts = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\scripts'))
$Base = Join-Path $WorkDir ('uni-os-cp-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$Vault = Join-Path $Base 'Fake & Vault'
$Dl = Join-Path $Base 'Downloads'
$Inst = Join-Path $Base 'install dir'
$Trash = Join-Path $Base 'trash'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:fail = 0; $script:pass = 0
function Check([bool]$cond, [string]$what) {
    if ($cond) { $script:pass++; Write-Host "PASS  $what" } else { $script:fail++; Write-Host "FAIL  $what" -ForegroundColor Red }
}
function Download([string]$name, [string]$content, [string]$hostUrl, [int]$ageMin = 1) {
    $p = Join-Path $Dl $name
    [IO.File]::WriteAllText($p, $content, $Utf8)
    if ($hostUrl) {
        Set-Content -LiteralPath $p -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3`r`nReferrerUrl=https://lms.example.edu/course/view.php?id=1`r`nHostUrl=$hostUrl"
    }
    (Get-Item -LiteralPath $p).LastWriteTime = (Get-Date).AddMinutes(-$ageMin)
}
function Request([string]$id, $obj, [int]$ageMin = 40, [string]$raw = '') {
    $p = Join-Path $Vault "_agent\course-fetch\pending\$id.json"
    $text = if ($raw) { $raw } else { ConvertTo-Json $obj -Compress }
    [IO.File]::WriteAllText($p, $text, $Utf8)
    (Get-Item -LiteralPath $p).LastWriteTime = (Get-Date).AddMinutes(-$ageMin)
}
function Result([string]$id) {
    $p = Join-Path $Vault "_agent\course-fetch\done\$id.result.json"
    if (Test-Path -LiteralPath $p) { return Get-Content -LiteralPath $p -Raw | ConvertFrom-Json } else { return $null }
}
function Pending([string]$id) { return Test-Path -LiteralPath (Join-Path $Vault "_agent\course-fetch\pending\$id.json") }

New-Item -ItemType Directory -Force -Path $Vault, $Dl | Out-Null
foreach ($d in 'A&D\assignments', 'A&D\script and slides', 'DM\assignments') { New-Item -ItemType Directory -Force -Path (Join-Path $Vault $d) | Out-Null }
$config = @{
    university = @{ lms_url = 'https://lms.example.edu/' }
    courses = @(
        @{ id = 'algo'; short = 'AD'; folder = 'A&D'; official_subfolders = @('assignments', 'script and slides'); website = 'https://course.example.org/ad/'; lms_url = '' },
        @{ id = 'dm'; short = 'DM'; folder = 'DM'; official_subfolders = @('assignments', 'missing folder'); fetch_sources = @('http://slides.example.org/dm/') },
        @{ id = 'la'; short = 'LA'; folder = 'LA'; official_subfolders = @('assignments') }
    )
    course_fetch = @{
        max_mb = 0.01; extra_hosts = @('*.cdn.example.net')
        date_guards = @(@{ course = 'dm'; pattern = '(?i)solution[_ -]?0*6(\D|$)'; not_before = '2099-01-01'; reason = 'graded quiz solution' })
    }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Vault '_agent') | Out-Null
[IO.File]::WriteAllText((Join-Path $Vault '_agent\uni-os.json'), (ConvertTo-Json $config -Depth 6), $Utf8)

# ---- installer ----------------------------------------------------------------------------------
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Scripts 'install-course-pickup.ps1') -Vault $Vault -InstallDir $Inst -Downloads $Dl -NoRegister -NoCreateFolders 2>&1 | Out-String
Check ($LASTEXITCODE -eq 0) 'installer exits 0'
Check ($out -match 'NOT registered') 'installer with -NoRegister prints the command for the user'
$S = Get-Content -LiteralPath (Join-Path $Inst 'pickup-settings.json') -Raw | ConvertFrom-Json
Check ((@($S.allowed_hosts) -join ',') -eq 'lms.example.edu,course.example.org,slides.example.org,*.cdn.example.net') 'hosts derived from lms_url, website, fetch_sources, extra_hosts'
Check ((@($S.folders) -join '|') -eq 'A&D/assignments|A&D/script and slides|DM/assignments|DM/missing folder|LA/assignments') 'target folders derived from official_subfolders'
Check ($S.date_guards[0].folder -eq 'DM') 'date guard course resolved to its folder'
Check (Test-Path -LiteralPath (Join-Path $Vault '_agent\course-fetch\pending')) 'pending folder created'
$policy = [IO.File]::ReadAllText((Join-Path $Vault '_agent\course-fetch\pickup-policy.md'))
Check ($policy -match '`lms.example.edu`' -and $policy -match 'DM/missing folder`? \(does not exist yet') 'policy summary written with hosts and missing-folder warning'
Check (Test-Path -LiteralPath (Join-Path $Inst 'course-pickup-launcher.vbs')) 'launcher copied'
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Scripts 'install-course-pickup.ps1') -Vault $Vault -InstallDir (Join-Path $Vault 'inside') -NoRegister 2>&1 | Out-String
Check ($LASTEXITCODE -eq 2) 'install folder inside the vault is refused'

# ---- requests -------------------------------------------------------------------------------------
$lms = 'https://lms.example.edu/pluginfile.php/1/mod_resource/content/0/x.pdf'
Download 'sheet01.pdf' 'sheet one' $lms;                Request 'r01-good' @{ file = 'sheet01.pdf'; target = 'A&D/assignments' }
Download 'evil.pdf' 'evil' 'https://evil.example.com/x.pdf'; Request 'r02-host' @{ file = 'evil.pdf'; target = 'A&D/assignments' }
Download 'nozone.pdf' 'no zone' '';                     Request 'r03-nozone' @{ file = 'nozone.pdf'; target = 'A&D/assignments' }
Download 'run.exe' 'MZ' $lms;                           Request 'r04-type' @{ file = 'run.exe'; target = 'A&D/assignments' }
Download 'ok.pdf' 'ok' $lms;                            Request 'r05-target' @{ file = 'ok.pdf'; target = 'A&D/notes' }
Request 'r06-name' @{ file = '..\ok.pdf'; target = 'A&D/assignments' }
Request 'r07-missing-old' @{ file = 'missing.pdf'; target = 'A&D/assignments' }
Request 'r08-missing-new' @{ file = 'missing2.pdf'; target = 'A&D/assignments' } 1
Download 'old.pdf' 'old' $lms 800;                      Request 'r09-old' @{ file = 'old.pdf'; target = 'A&D/assignments' }
Download 'big.pdf' ('B' * 20000) $lms;                  Request 'r10-big' @{ file = 'big.pdf'; target = 'A&D/assignments' }
Download 'big2.pdf' ('C' * 20000) $lms;                 Request 'r11-big-ok' @{ file = 'big2.pdf'; target = 'A&D/assignments'; approved_large = $true }
Download 'notes.pdf' 'older' $lms 30
Download 'notes (1).pdf' 'newer' $lms 2;                Request 'r12-numbered' @{ file = 'notes.pdf'; target = 'A&D/script and slides' }
Download 'Solution_06.pdf' 'sol' $lms;                  Request 'r13-guard' @{ file = 'Solution_06.pdf'; target = 'DM/assignments' }
Request 'r14-badjson-old' $null 40 '{not json'
Request 'r15-badjson-new' $null 1 '{not json'
Download 'other.pdf' 'other' $lms;                      Request 'r16-machine' @{ file = 'other.pdf'; target = 'A&D/assignments'; machine = 'SOME-OTHER-PC' }
Download 'cdn.pdf' 'cdn' 'https://files.cdn.example.net/a/cdn.pdf'; Request 'r17-wildcard' @{ file = 'cdn.pdf'; target = 'DM/assignments' }
Download 'nofolder.pdf' 'nf' $lms;                      Request 'r18-nofolder' @{ file = 'nofolder.pdf'; target = 'DM/missing folder' }

$run = { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Inst 'course-pickup.ps1') -TrashDir $Trash 2>&1 | Out-String }
$o = & $run
Check ($LASTEXITCODE -eq 0) 'pick-up run exits 0'

$r = Result 'r01-good'
Check ($r.status -eq 'filed' -and $r.host -eq 'lms.example.edu') 'allowed host -> filed, host recorded'
Check ((Test-Path -LiteralPath (Join-Path $Vault 'A&D\assignments\sheet01.pdf')) -and -not (Test-Path -LiteralPath (Join-Path $Dl 'sheet01.pdf'))) 'file copied, original removed'
Check (@(Get-ChildItem -LiteralPath $Trash -Filter '*sheet01.pdf').Count -eq 1) 'original went to the (test) trash'
Check ($r.sha256 -eq (Get-FileHash -LiteralPath (Join-Path $Vault 'A&D\assignments\sheet01.pdf') -Algorithm SHA256).Hash.ToLower()) 'result hash matches the filed copy'
Check (Test-Path -LiteralPath (Join-Path $Vault '_agent\course-fetch\done\r01-good.request.json')) 'request moved to done'
Check ((Result 'r02-host').status -eq 'rejected' -and (Result 'r02-host').reason -match 'evil.example.com') 'disallowed host -> rejected (host named, no URL)'
Check (-not ((Result 'r02-host').reason -match 'https?://')) 'no URL in the reason'
Check ((Result 'r03-nozone').reason -match 'source: unknown') 'no Zone.Identifier -> rejected'
Check ((Result 'r04-type').reason -match 'file type .exe') 'executable type -> rejected'
Check ((Result 'r05-target').reason -match 'not one of the configured') 'non-official target -> rejected'
Check ((Result 'r06-name').reason -eq 'bad file name') 'path in the name -> rejected'
Check ((Result 'r07-missing-old').status -eq 'not-found') 'missing file after the wait -> not-found'
Check ((Pending 'r08-missing-new') -and $null -eq (Result 'r08-missing-new')) 'missing file within the wait -> stays pending'
Check ((Result 'r09-old').reason -eq 'only an old copy is in Downloads') 'stale download -> not-found'
Check ((Result 'r10-big').reason -match 'approved-large') 'over the size limit -> rejected'
Check ((Result 'r11-big-ok').status -eq 'filed') 'over the limit with approved_large -> filed'
Check ((Result 'r12-numbered').status -eq 'filed' -and [IO.File]::ReadAllText((Join-Path $Vault 'A&D\script and slides\notes.pdf')) -eq 'newer') 'newest "name (1).ext" copy filed under the requested name'
Check ((Result 'r13-guard').reason -match 'date guard: graded quiz solution') 'date guard -> rejected'
Check ((Result 'r14-badjson-old').reason -eq 'request is not valid JSON') 'invalid JSON after the wait -> rejected'
Check (Pending 'r15-badjson-new') 'invalid JSON within the wait -> stays pending (may be syncing)'
Check ((Pending 'r16-machine') -and (Test-Path -LiteralPath (Join-Path $Dl 'other.pdf'))) 'request for another machine is left alone'
Check ((Result 'r17-wildcard').status -eq 'filed') 'wildcard host *.cdn.example.net -> filed'
Check ((Result 'r18-nofolder').reason -eq 'target folder does not exist') 'configured but missing folder -> rejected (the pick-up never creates folders)'

# ---- second round: already there, changed on the server ------------------------------------------
Download 'sheet01.pdf' 'sheet one' $lms;      Request 'r20-same' @{ file = 'sheet01.pdf'; target = 'A&D/assignments' }
$o = & $run
Check ((Result 'r20-same').status -eq 'already-there' -and -not (Test-Path -LiteralPath (Join-Path $Dl 'sheet01.pdf'))) 'same content -> already-there, download removed'
Download 'sheet01.pdf' 'sheet one, v2' $lms;  Request 'r21-changed' @{ file = 'sheet01.pdf'; target = 'A&D/assignments' }
$o = & $run
$r = Result 'r21-changed'
Check ($r.status -eq 'changed-on-server' -and $r.vault_sha256 -and $r.vault_sha256 -ne $r.sha256) 'different content -> changed-on-server with both hashes'
Check ([IO.File]::ReadAllText((Join-Path $Vault 'A&D\assignments\sheet01.pdf')) -eq 'sheet one' -and (Test-Path -LiteralPath (Join-Path $Dl 'sheet01.pdf'))) 'vault copy kept, download kept'
$log = [IO.File]::ReadAllText((Join-Path $Inst 'pickup.log'))
Check (-not ($log -match 'https?://')) 'pickup.log holds no URLs'
Check ($log -match ' filed \| sheet01.pdf \| A&D/assignments') 'pickup.log line format'

# ---- nothing pending: exits fast ----------------------------------------------------------------------
Get-ChildItem -LiteralPath (Join-Path $Vault '_agent\course-fetch\pending') -Filter '*.json' | Remove-Item
$sw = [Diagnostics.Stopwatch]::StartNew(); $o = & $run; $sw.Stop()
Check ($LASTEXITCODE -eq 0) 'empty queue -> exit 0'

# ---- installer creates missing target folders, but never a missing course folder -------------------
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Scripts 'install-course-pickup.ps1') -Vault $Vault -InstallDir $Inst -Downloads $Dl -NoRegister 2>&1 | Out-String
Check ((Test-Path -LiteralPath (Join-Path $Vault 'DM\missing folder')) -and ($out -match '1 created: DM/missing folder')) 'installer creates a missing target below an existing course folder'
Check (-not (Test-Path -LiteralPath (Join-Path $Vault 'LA'))) 'installer never creates a missing course folder'

Write-Host ''
Write-Host "$($script:pass) passed, $($script:fail) failed"
if (-not $Keep) { Remove-Item -LiteralPath $Base -Recurse -Force -ErrorAction SilentlyContinue } else { Write-Host "kept: $Base" }
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
