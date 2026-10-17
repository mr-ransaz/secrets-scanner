param([string]$ExePath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $ExePath) { $ExePath = Join-Path $projectRoot 'dist\secretscan.exe' }
$ExePath = (Resolve-Path -LiteralPath $ExePath).Path
$scratch = Join-Path $projectRoot ('.work\exe-verify-' + [guid]::NewGuid().ToString('N'))
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
Push-Location $projectRoot
try {
    $env:TEMP = $scratch
    $env:TMP = $scratch
    & .\.venv\Scripts\python.exe scripts\smoke_test.py --exe $ExePath
    if ($LASTEXITCODE -ne 0) { throw 'Executable smoke verification failed' }
    Write-Output 'exe verification: PASS; version, rules, text/JSON/SARIF/HTML, exits, baseline, masking'
    Write-Output 'exe startup verification: PASS; redirected no-args/folder/missing, exit 2, no prompts'
}
finally {
    Pop-Location
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    $resolvedScratch = [IO.Path]::GetFullPath($scratch)
    if (-not $resolvedScratch.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar)) {
        throw 'Refusing cleanup outside project'
    }
    Remove-Item -LiteralPath $resolvedScratch -Recurse -Force
}
