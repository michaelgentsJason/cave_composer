param(
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$galleryRelative = 'exports/caves_difficulty_v01/index.html'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "Python environment missing: $pythonExe" }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $galleryRelative))) { throw 'Gallery file missing.' }
$logDirectory = Join-Path $repoRoot 'outputs\gallery_server'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

$ready = $false
foreach ($candidatePort in $Port..($Port + 10)) {
    $galleryUrl = "http://127.0.0.1:$candidatePort/$galleryRelative"
    $listener = Get-NetTCPConnection -State Listen -LocalPort $candidatePort -ErrorAction SilentlyContinue
    if ($listener) {
        try {
            $existing = Invoke-WebRequest -Uri $galleryUrl -UseBasicParsing -TimeoutSec 3
            if ($existing.StatusCode -eq 200 -and $existing.Content.Contains('Cave Composer')) {
                $ready = $true
                break
            }
        } catch { }
        continue
    }
    $serverProcess = Start-Process -FilePath $pythonExe -ArgumentList @(
        '-m', 'http.server', "$candidatePort", '--bind', '127.0.0.1',
        '--directory', ('"' + $repoRoot + '"')
    ) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $logDirectory "http_$candidatePort.stdout.log") `
      -RedirectStandardError (Join-Path $logDirectory "http_$candidatePort.stderr.log")
    for ($probe = 0; $probe -lt 20; $probe++) {
        Start-Sleep -Milliseconds 200
        try {
            $response = Invoke-WebRequest -Uri $galleryUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content.Contains('Cave Composer')) {
                $ready = $true
                break
            }
        } catch { }
        if ($serverProcess.HasExited) { break }
    }
    if ($ready) {
        @{ pid = $serverProcess.Id; url = $galleryUrl; root = $repoRoot } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDirectory 'server.json') -Encoding UTF8
        break
    }
}
if (-not $ready) { throw "Unable to start the gallery server. See $logDirectory" }
if (-not $NoBrowser) { Start-Process $galleryUrl }
Write-Output $galleryUrl
