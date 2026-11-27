# Install CLI-Anything for Google Antigravity (Community Edition).
param(
    [switch]$Force,
    [switch]$DryRun,
    [string]$Workspace,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "Usage: .\install.ps1 [-Force] [-DryRun] [-Workspace <path>]"
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
    "hooks.json",
    "rules\cli-anything-generator.md",
    "agents\cli-anything-auditor.md",
    "skills\cli-anything\SKILL.md",
    "skills\cli-anything-refine\SKILL.md",
    "skills\cli-anything-test\SKILL.md",
    "skills\cli-anything-validate\SKILL.md",
    "skills\cli-anything-list\SKILL.md",
    "references\antigravity-tooling.md",
    "references\HARNESS.md",
    "references\commands\cli-anything.md",
    "references\docs\PREVIEW_PROTOCOL.md",
    "scripts\repl_skin.py",
    "scripts\preview_bundle.py",
    "scripts\skill_generator.py",
    "scripts\verify_harness.py",
    "scripts\list_harnesses.py",
    "scripts\pep420_guard.py",
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
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $pluginsHome -Force | Out-Null
    }
} else {
    $createSwitch = -not $DryRun
    if ($env:ANTIGRAVITY_PLUGINS_HOME) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw $env:ANTIGRAVITY_PLUGINS_HOME -Create:$createSwitch
    } elseif ($env:USERPROFILE) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw (Join-Path $env:USERPROFILE ".gemini\config\plugins") -Create:$createSwitch
    } elseif ($env:HOME) {
        $pluginsHome = Resolve-CliAnythingPluginsHome -Raw (Join-Path $env:HOME ".gemini\config\plugins") -Create:$createSwitch
    } else {
        throw "ANTIGRAVITY_PLUGINS_HOME is not set and USERPROFILE/HOME is unavailable."
    }
}

$discoveryPointer = Get-CliAnythingDiscoveryPointerPath
$destDir = Join-Path $pluginsHome "cli-anything"

if ($DryRun) {
    Write-Host "[dry-run] Source:            $pluginSrc"
    Write-Host "[dry-run] Destination:       $destDir"
    if ($isGlobal) {
        Write-Host "[dry-run] Discovery pointer: $discoveryPointer"
    } else {
        Write-Host "[dry-run] Discovery pointer: (unchanged for workspace install)"
    }
    exit 0
}

$lockPath = Join-Path $pluginsHome ".cli-anything.lock"
$lockHandle = $null
$stagingDir = $null
$backupDir = $null

try {
    $lockHandle = Acquire-CliAnythingInstallLock -LockPath $lockPath

    if ((Test-Path -LiteralPath $destDir) -and (-not $Force)) {
        throw "Refusing to overwrite existing plugin: $destDir`nRe-run with -Force to upgrade, or remove it manually."
    }

    $stagingDir = Join-Path $pluginsHome (".cli-anything.tmp." + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $stagingDir | Out-Null
    $lockKey = Normalize-CliAnythingPathKey (Resolve-CliAnythingRealPath -Path $lockPath)
    $stagingKey = Normalize-CliAnythingPathKey (Resolve-CliAnythingRealPath -Path $stagingDir)
    $destKey = Normalize-CliAnythingPathKey (Resolve-CliAnythingRealPath -Path $destDir)

    Get-ChildItem -LiteralPath $pluginSrc -Force | ForEach-Object {
        if ($_.Name -in @("tests", "harness", ".git", ".github", ".gitignore", ".gitattributes", ".agents", "__pycache__")) {
            return
        }
        $entryKey = Normalize-CliAnythingPathKey (Resolve-CliAnythingRealPath -Path $_.FullName)
        $entryPrefix = "$entryKey\"
        if (
            ($stagingKey -eq $entryKey) -or $stagingKey.StartsWith($entryPrefix) -or
            ($destKey -eq $entryKey) -or $destKey.StartsWith($entryPrefix) -or
            ($lockKey -eq $entryKey) -or $lockKey.StartsWith($entryPrefix)
        ) {
            return
        }
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $stagingDir $_.Name) -Recurse -Force
    }

    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if ($py) {
        $rs = Join-Path $stagingDir "scripts"
        & $py.Source -B -m py_compile `
            (Join-Path $rs "repl_skin.py") `
            (Join-Path $rs "preview_bundle.py") `
            (Join-Path $rs "skill_generator.py") `
            (Join-Path $rs "_toml_fallback.py") `
            (Join-Path $rs "verify_harness.py") `
            (Join-Path $rs "list_harnesses.py") `
            (Join-Path $rs "pep420_guard.py")
        if ($LASTEXITCODE -ne 0) {
            throw "Pre-publish py_compile failed for staged plugin scripts."
        }
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

    $pluginRoot = [System.IO.Path]::GetFullPath($destDir)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText((Join-Path $pluginRoot "PLUGIN_ROOT.txt"), ($pluginRoot + [Environment]::NewLine), $utf8NoBom)

    if ($isGlobal) {
        Write-CliAnythingDiscoveryPointer -PointerPath $discoveryPointer -Value $pluginRoot
    }
} finally {
    if ($stagingDir -and (Test-Path -LiteralPath $stagingDir)) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
    Release-CliAnythingInstallLock -LockHandle $lockHandle -LockPath $lockPath
}

Write-Host "Installed CLI-Anything (Community Edition) for Antigravity to: $pluginRoot"
if ($isGlobal) {
    Write-Host "Wrote PLUGIN_ROOT stamp and discovery pointer: $discoveryPointer"
} else {
    Write-Host "Wrote PLUGIN_ROOT stamp (workspace-scoped install; global discovery pointer unchanged)."
}
Write-Host "Slash commands ready on next turn: /cli-anything, /cli-anything-refine, /cli-anything-test, /cli-anything-validate, /cli-anything-list"
Write-Host "Consumer Hub/skills are separate: npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y"
