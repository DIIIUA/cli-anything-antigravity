# Install CLI-Anything for Google Antigravity (Community Edition).
param(
    [switch]$Force,
    [string]$Workspace,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "Usage: .\install.ps1 [-Force] [-Workspace <path>]"
    Write-Host "Install CLI-Anything for Google Antigravity (Community Edition)."
    Write-Host "Global destination:    `$env:ANTIGRAVITY_PLUGINS_HOME\cli-anything (default: %USERPROFILE%\.gemini\config\plugins\cli-anything)"
    Write-Host "Workspace destination: <workspace>\.agents\plugins\cli-anything"
    exit 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "lib.ps1")

$pluginSrc = Split-Path -Parent $scriptDir

$required = @(
    "plugin.json",
    "skills\cli-anything\SKILL.md",
    "references\HARNESS.md",
    "references\commands\cli-anything.md",
    "references\docs\PREVIEW_PROTOCOL.md",
    "scripts\repl_skin.py",
    "scripts\preview_bundle.py",
    "scripts\skill_generator.py",
    "scripts\templates\SKILL.md.template"
)
foreach ($req in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $pluginSrc $req) -PathType Leaf)) {
        throw "Missing required plugin resource: $(Join-Path $pluginSrc $req)`nRun .\scripts\sync-upstream.ps1 or re-clone the complete repository."
    }
}

$isGlobal = $true
if (-not [string]::IsNullOrWhiteSpace($Workspace)) {
    $isGlobal = $false
    $wsRoot = Resolve-CliAnythingWorkspaceRoot -Raw $Workspace
    $pluginsHome = Join-Path $wsRoot ".agents\plugins"
    New-Item -ItemType Directory -Path $pluginsHome -Force | Out-Null
} else {
    if ($env:ANTIGRAVITY_PLUGINS_HOME) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw $env:ANTIGRAVITY_PLUGINS_HOME -Create
    } elseif ($env:USERPROFILE) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw (Join-Path $env:USERPROFILE ".gemini\config\plugins") -Create
    } elseif ($env:HOME) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw (Join-Path $env:HOME ".gemini\config\plugins") -Create
    } else {
        throw "ANTIGRAVITY_PLUGINS_HOME is not set and USERPROFILE/HOME is unavailable."
    }
}

$discoveryPointer = Get-CliAnythingDiscoveryPointerPath
$destDir = Join-Path $pluginsHome "cli-anything"
$stagingDir = $null
$backupDir = $null

if (Test-Path -LiteralPath $destDir) {
    if (-not $Force) {
        throw "Refusing to overwrite existing plugin: $destDir`nRe-run with -Force to upgrade, or remove it manually."
    }
}

try {
    $stagingDir = Join-Path $pluginsHome (".cli-anything.tmp." + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $stagingDir | Out-Null

    Get-ChildItem -LiteralPath $pluginSrc -Force | ForEach-Object {
        if ($_.Name -in @("tests", ".git", ".github", ".gitignore", "__pycache__")) {
            return
        }
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $stagingDir $_.Name) -Recurse -Force
    }

    if (Test-Path -LiteralPath $destDir) {
        $backupDir = Join-Path $pluginsHome (".cli-anything.bak." + [System.Guid]::NewGuid().ToString("N"))
        Move-Item -LiteralPath $destDir -Destination $backupDir
        try {
            Move-Item -LiteralPath $stagingDir -Destination $destDir
            $stagingDir = $null
            Remove-Item -LiteralPath $backupDir -Recurse -Force
            $backupDir = $null
        } catch {
            if ($backupDir -and (Test-Path -LiteralPath $backupDir)) {
                Move-Item -LiteralPath $backupDir -Destination $destDir -Force
            }
            throw
        }
    } else {
        Move-Item -LiteralPath $stagingDir -Destination $destDir
        $stagingDir = $null
    }
} finally {
    if ($stagingDir -and (Test-Path -LiteralPath $stagingDir)) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
}

$pluginRoot = [System.IO.Path]::GetFullPath($destDir)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $pluginRoot "PLUGIN_ROOT.txt"), ($pluginRoot + [Environment]::NewLine), $utf8NoBom)

if ($isGlobal) {
    $pointerDir = Split-Path -Parent $discoveryPointer
    New-Item -ItemType Directory -Path $pointerDir -Force | Out-Null
    [System.IO.File]::WriteAllText($discoveryPointer, ($pluginRoot + [Environment]::NewLine), $utf8NoBom)
}

Write-Host "Installed CLI-Anything (Community Edition) for Antigravity to: $pluginRoot"
if ($isGlobal) {
    Write-Host "Wrote PLUGIN_ROOT stamp and discovery pointer: $discoveryPointer"
} else {
    Write-Host "Wrote PLUGIN_ROOT stamp (workspace-scoped install; global discovery pointer unchanged)."
}
Write-Host "Antigravity discovers plugins automatically; the cli-anything skill is available on your next turn."
Write-Host "Consumer Hub/skills are separate: npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y"
