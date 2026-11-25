# Sync canonical methodology and helper scripts from HKUDS/CLI-Anything (Windows PowerShell).
param(
    [string]$Source,
    [string]$Repo = "https://github.com/HKUDS/CLI-Anything.git"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$tmpDir = $null

try {
    if ([string]::IsNullOrWhiteSpace($Source)) {
        $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cli-anything-sync-" + [System.Guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
        $Source = Join-Path $tmpDir "upstream"
        git clone --depth 1 $Repo $Source
        if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    }

    $canonical = Join-Path $Source "cli-anything-plugin"
    $preview = Join-Path $Source "docs\PREVIEW_PROTOCOL.md"
    if (-not (Test-Path -LiteralPath (Join-Path $canonical "HARNESS.md"))) {
        throw "Missing HARNESS.md in $canonical"
    }
    if (-not (Test-Path -LiteralPath $preview)) {
        throw "Missing PREVIEW_PROTOCOL.md at $preview"
    }

    $refDir = Join-Path $repoRoot "references"
    $tplDir = Join-Path $repoRoot "scripts\templates"
    if (Test-Path -LiteralPath $refDir) { Remove-Item -LiteralPath $refDir -Recurse -Force }
    if (Test-Path -LiteralPath $tplDir) { Remove-Item -LiteralPath $tplDir -Recurse -Force }

    New-Item -ItemType Directory -Path `
        (Join-Path $refDir "commands"), `
        (Join-Path $refDir "guides"), `
        (Join-Path $refDir "docs"), `
        $tplDir -Force | Out-Null

    Copy-Item -Path (Join-Path $canonical "HARNESS.md") -Destination (Join-Path $refDir "HARNESS.md")
    Copy-Item -Path (Join-Path $canonical "commands\*.md") -Destination (Join-Path $refDir "commands")
    Copy-Item -Path (Join-Path $canonical "guides\*.md") -Destination (Join-Path $refDir "guides")
    Copy-Item -Path $preview -Destination (Join-Path $refDir "docs\PREVIEW_PROTOCOL.md")
    Copy-Item -Path (Join-Path $canonical "repl_skin.py") -Destination (Join-Path $repoRoot "scripts\repl_skin.py")
    Copy-Item -Path (Join-Path $canonical "preview_bundle.py") -Destination (Join-Path $repoRoot "scripts\preview_bundle.py")
    Copy-Item -Path (Join-Path $canonical "skill_generator.py") -Destination (Join-Path $repoRoot "scripts\skill_generator.py")
    Copy-Item -Path (Join-Path $canonical "templates\*") -Destination $tplDir

    $commit = (git -C $Source rev-parse HEAD 2>$null | Out-String).Trim()
    $short = (git -C $Source rev-parse --short HEAD 2>$null | Out-String).Trim()
    if (-not $commit) { $commit = "unknown"; $short = "unknown" }

    $meta = [ordered]@{
        upstream_repo   = "HKUDS/CLI-Anything"
        upstream_commit = $commit
        upstream_short  = $short
        synced_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    } | ConvertTo-Json
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText((Join-Path $repoRoot "UPSTREAM_SYNC.json"), ($meta + "`n"), $utf8NoBom)

    Write-Host "Synced canonical resources from HKUDS/CLI-Anything@$short."
} finally {
    if ($tmpDir -and (Test-Path -LiteralPath $tmpDir)) {
        Remove-Item -LiteralPath $tmpDir -Recurse -Force
    }
}
