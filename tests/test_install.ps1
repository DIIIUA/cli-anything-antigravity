# Regression tests for CLI-Anything for Google Antigravity v2.0 (Community Edition, Windows PowerShell).
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginSrc = Split-Path -Parent $scriptDir

$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cli-anything-ce-test-" + [System.Guid]::NewGuid().ToString("N"))
$userHome = Join-Path $tmpDir "home"
$pluginsHome = Join-Path $tmpDir "plugins"
$installedDir = Join-Path $pluginsHome "cli-anything"
$staleStaging = Join-Path $pluginsHome ".cli-anything.tmp.stale"
$discoveryPointer = Join-Path $userHome ".gemini\cli-anything-generator.root"
$workspaceDir = Join-Path $tmpDir "sample-workspace"
$wsInstalledDir = Join-Path $workspaceDir ".agents\plugins\cli-anything"

function Fail([string]$Message) { throw "FAIL: $Message" }
function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Fail "expected file: $Path" }
}
function Assert-SameFile([string]$Left, [string]$Right) {
    if ((Get-FileHash -LiteralPath $Left -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $Right -Algorithm SHA256).Hash) {
        Fail "files differ: $Left $Right"
    }
}

$oldUserProfile = $env:USERPROFILE
$oldPluginsHome = $env:ANTIGRAVITY_PLUGINS_HOME

try {
    New-Item -ItemType Directory -Path $userHome, $workspaceDir -Force | Out-Null
    $env:USERPROFILE = $userHome

    $dryPlugins = Join-Path $tmpDir "dry-root\plugins"
    $env:ANTIGRAVITY_PLUGINS_HOME = $dryPlugins
    & (Join-Path $pluginSrc "scripts\install.ps1") -DryRun | Out-Null
    if (Test-Path -LiteralPath $dryPlugins) { Fail "-DryRun created plugins directory" }

    New-Item -ItemType Directory -Path $staleStaging -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $staleStaging "stale.txt") -Value "stale"

    $env:ANTIGRAVITY_PLUGINS_HOME = $pluginsHome
    & (Join-Path $pluginSrc "scripts\install.ps1")

    Assert-File (Join-Path $installedDir "plugin.json")
    Assert-File (Join-Path $installedDir "README.md")
    Assert-File (Join-Path $installedDir "LICENSE")
    Assert-File (Join-Path $installedDir "NOTICE")
    Assert-File (Join-Path $installedDir "UPSTREAM_SYNC.json")
    Assert-File (Join-Path $installedDir "PLUGIN_ROOT.txt")
    Assert-File (Join-Path $installedDir "assets\logo.svg")
    Assert-File (Join-Path $installedDir "hooks.json")
    Assert-File (Join-Path $installedDir "rules\cli-anything-generator.md")
    Assert-File (Join-Path $installedDir "agents\cli-anything-auditor.md")
    Assert-File $discoveryPointer
    foreach ($skill in @("cli-anything", "cli-anything-refine", "cli-anything-test", "cli-anything-validate", "cli-anything-list")) {
        Assert-File (Join-Path $installedDir "skills\$skill\SKILL.md")
    }
    Assert-File (Join-Path $installedDir "references\antigravity-tooling.md")
    Assert-File (Join-Path $installedDir "references\HARNESS.md")
    Assert-File (Join-Path $installedDir "references\docs\PREVIEW_PROTOCOL.md")
    Assert-File (Join-Path $installedDir "scripts\repl_skin.py")
    Assert-File (Join-Path $installedDir "scripts\preview_bundle.py")
    Assert-File (Join-Path $installedDir "scripts\skill_generator.py")
    Assert-File (Join-Path $installedDir "scripts\verify_harness.py")
    Assert-File (Join-Path $installedDir "scripts\list_harnesses.py")
    Assert-File (Join-Path $installedDir "scripts\pep420_guard.py")
    Assert-File (Join-Path $installedDir "scripts\templates\SKILL.md.template")

    if (Test-Path -LiteralPath (Join-Path $pluginsHome ".cli-anything.lock")) { Fail "stale lock remained" }

    $stamp = (Get-Content -LiteralPath (Join-Path $installedDir "PLUGIN_ROOT.txt") -Raw).Trim()
    $pointer = (Get-Content -LiteralPath $discoveryPointer -Raw).Trim()
    if ($stamp -ne $pointer) { Fail "pointer mismatch" }
    if (-not (Test-Path -LiteralPath $staleStaging)) { Fail "touched stale staging" }
    if (Test-Path -LiteralPath (Join-Path $installedDir "tests")) { Fail "copied tests/" }
    if (Test-Path -LiteralPath (Join-Path $installedDir ".github")) { Fail "copied .github/" }
    if (Test-Path -LiteralPath (Join-Path $installedDir "rules\AGENTS.md")) { Fail "must not ship always-on rules" }

    Assert-SameFile (Join-Path $pluginSrc "references\HARNESS.md") (Join-Path $installedDir "references\HARNESS.md")
    Assert-SameFile (Join-Path $pluginSrc "scripts\verify_harness.py") (Join-Path $installedDir "scripts\verify_harness.py")

    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    & $py.Source -B -m py_compile `
        (Join-Path $installedDir "scripts\repl_skin.py") `
        (Join-Path $installedDir "scripts\preview_bundle.py") `
        (Join-Path $installedDir "scripts\skill_generator.py") `
        (Join-Path $installedDir "scripts\verify_harness.py") `
        (Join-Path $installedDir "scripts\list_harnesses.py") `
        (Join-Path $installedDir "scripts\pep420_guard.py")
    if ($LASTEXITCODE -ne 0) { Fail "py_compile failed" }

    # Simulate direct `agy plugin install` without PLUGIN_ROOT.txt
    Remove-Item -LiteralPath (Join-Path $installedDir "PLUGIN_ROOT.txt") -Force
    & $py.Source (Join-Path $installedDir "scripts\list_harnesses.py") --path $tmpDir --json | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail "list_harnesses failed without PLUGIN_ROOT.txt" }

    $manifest = Get-Content -LiteralPath (Join-Path $installedDir "plugin.json") -Raw | ConvertFrom-Json
    $allowedKeys = @("`$schema", "name", "displayName", "version", "description", "author", "homepage", "repository", "logo", "suggestedPrompts", "disabled", "license", "keywords", "skills", "extensions")
    foreach ($prop in $manifest.PSObject.Properties) {
        if ($allowedKeys -notcontains $prop.Name) { Fail "unknown plugin.json field: $($prop.Name)" }
    }
    if ($manifest.name -ne "cli-anything" -or $manifest.license -ne "Apache-2.0") { Fail "manifest invalid" }
    if (@($manifest.suggestedPrompts).Count -ne 3) { Fail "expected 3 suggestedPrompts" }

    $refused = $false
    try { & (Join-Path $pluginSrc "scripts\install.ps1") } catch { $refused = $true }
    if (-not $refused) { Fail "overwrote without -Force" }

    & (Join-Path $pluginSrc "scripts\install.ps1") -Force
    & (Join-Path $pluginSrc "scripts\install.ps1") -Workspace $workspaceDir
    Assert-File (Join-Path $wsInstalledDir "references\HARNESS.md")
    if (((Get-Content -LiteralPath $discoveryPointer -Raw).Trim()) -ne $stamp) { Fail "workspace install clobbered global pointer" }
    & (Join-Path $pluginSrc "scripts\uninstall.ps1") -Workspace $workspaceDir
    if (Test-Path -LiteralPath $wsInstalledDir) { Fail "workspace uninstall left dir" }
    Assert-File $discoveryPointer

    & (Join-Path $pluginSrc "scripts\uninstall.ps1")
    if ((Test-Path -LiteralPath $installedDir) -or (Test-Path -LiteralPath $discoveryPointer)) { Fail "uninstall failed" }

    & (Join-Path $pluginSrc "scripts\install.ps1")
    $foreign = Join-Path $tmpDir "other-root"
    Set-Content -LiteralPath $discoveryPointer -Value $foreign
    & (Join-Path $pluginSrc "scripts\uninstall.ps1")
    if (((Get-Content -LiteralPath $discoveryPointer -Raw).Trim()) -ne $foreign) { Fail "foreign pointer changed" }

    Write-Host "PASS: Community Edition v2.0 Antigravity plugin tests passed."
} finally {
    if (Test-Path -LiteralPath $tmpDir) { Remove-Item -LiteralPath $tmpDir -Recurse -Force }
    if ($null -ne $oldUserProfile) { $env:USERPROFILE = $oldUserProfile } else { Remove-Item Env:USERPROFILE -ErrorAction SilentlyContinue }
    if ($null -ne $oldPluginsHome) { $env:ANTIGRAVITY_PLUGINS_HOME = $oldPluginsHome } else { Remove-Item Env:ANTIGRAVITY_PLUGINS_HOME -ErrorAction SilentlyContinue }
}
