Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$scratch = Join-Path $projectRoot ('.work\exe-build-' + [guid]::NewGuid().ToString('N'))
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$oldConfig = $env:PYINSTALLER_CONFIG_DIR
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
Push-Location $projectRoot
try {
    $env:TEMP = $scratch
    $env:TMP = $scratch
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $scratch 'cache'
    & .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\secretscan.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    $artifact = Get-Item -LiteralPath (Join-Path $projectRoot 'dist\secretscan.exe')
    Write-Output ('exe build: PASS; bytes=' + $artifact.Length)
}
finally {
    Pop-Location
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    $env:PYINSTALLER_CONFIG_DIR = $oldConfig
    $resolvedScratch = [IO.Path]::GetFullPath($scratch)
    if (-not $resolvedScratch.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar)) {
        throw 'Refusing cleanup outside project'
    }
    Remove-Item -LiteralPath $resolvedScratch -Recurse -Force
}
