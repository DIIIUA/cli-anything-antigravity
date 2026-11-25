# Regression tests for CLI-Anything for Google Antigravity (Community Edition, Windows PowerShell).
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
    New-Item -ItemType Directory -Path $userHome, $staleStaging, $workspaceDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $staleStaging "stale.txt") -Value "stale"

    $env:USERPROFILE = $userHome
    $env:ANTIGRAVITY_PLUGINS_HOME = $pluginsHome
    & (Join-Path $pluginSrc "scripts\install.ps1")

    Assert-File (Join-Path $installedDir "plugin.json")
    Assert-File (Join-Path $installedDir "README.md")
    Assert-File (Join-Path $installedDir "LICENSE")
    Assert-File (Join-Path $installedDir "NOTICE")
    Assert-File (Join-Path $installedDir "UPSTREAM_SYNC.json")
    Assert-File (Join-Path $installedDir "PLUGIN_ROOT.txt")
    Assert-File (Join-Path $installedDir "assets\logo.svg")
    Assert-File $discoveryPointer
    Assert-File (Join-Path $installedDir "skills\cli-anything\SKILL.md")
    Assert-File (Join-Path $installedDir "references\HARNESS.md")
    Assert-File (Join-Path $installedDir "references\commands\cli-anything.md")
    Assert-File (Join-Path $installedDir "references\docs\PREVIEW_PROTOCOL.md")
    Assert-File (Join-Path $installedDir "scripts\repl_skin.py")
    Assert-File (Join-Path $installedDir "scripts\preview_bundle.py")
    Assert-File (Join-Path $installedDir "scripts\skill_generator.py")
    Assert-File (Join-Path $installedDir "scripts\templates\SKILL.md.template")

    $stamp = (Get-Content -LiteralPath (Join-Path $installedDir "PLUGIN_ROOT.txt") -Raw).Trim()
    $pointer = (Get-Content -LiteralPath $discoveryPointer -Raw).Trim()
    if ($stamp -ne $pointer) { Fail "pointer mismatch" }
    if (-not (Test-Path -LiteralPath $staleStaging)) { Fail "touched stale staging" }
    if (Test-Path -LiteralPath (Join-Path $installedDir "tests")) { Fail "copied tests/" }
    if (Test-Path -LiteralPath (Join-Path $installedDir ".github")) { Fail "copied .github/" }
    if (Test-Path -LiteralPath (Join-Path $installedDir "rules\AGENTS.md")) { Fail "must not ship always-on rules" }

    Assert-SameFile (Join-Path $pluginSrc "references\HARNESS.md") (Join-Path $installedDir "references\HARNESS.md")
    Assert-SameFile (Join-Path $pluginSrc "scripts\repl_skin.py") (Join-Path $installedDir "scripts\repl_skin.py")

    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    & $py.Source -m py_compile `
        (Join-Path $installedDir "scripts\repl_skin.py") `
        (Join-Path $installedDir "scripts\preview_bundle.py") `
        (Join-Path $installedDir "scripts\skill_generator.py")
    if ($LASTEXITCODE -ne 0) { Fail "py_compile failed" }

    $manifest = Get-Content -LiteralPath (Join-Path $installedDir "plugin.json") -Raw | ConvertFrom-Json
    $allowedKeys = @("name", "displayName", "version", "description", "author", "homepage", "repository", "logo", "suggestedPrompts", "disabled")
    foreach ($prop in $manifest.PSObject.Properties) {
        if ($allowedKeys -notcontains $prop.Name) { Fail "unknown plugin.json field: $($prop.Name)" }
    }
    if ($manifest.name -ne "cli-anything") { Fail "manifest name mismatch" }
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
    if (Test-Path -LiteralPath $installedDir) { Fail "uninstall left dir" }
    if (Test-Path -LiteralPath $discoveryPointer) { Fail "uninstall left pointer" }

    & (Join-Path $pluginSrc "scripts\install.ps1")
    $foreign = Join-Path $tmpDir "other-root"
    Set-Content -LiteralPath $discoveryPointer -Value $foreign
    & (Join-Path $pluginSrc "scripts\uninstall.ps1")
    if (((Get-Content -LiteralPath $discoveryPointer -Raw).Trim()) -ne $foreign) { Fail "foreign pointer changed" }

    Write-Host "PASS: Community Edition Antigravity plugin tests passed."
} finally {
    if (Test-Path -LiteralPath $tmpDir) { Remove-Item -LiteralPath $tmpDir -Recurse -Force }
    if ($null -ne $oldUserProfile) { $env:USERPROFILE = $oldUserProfile } else { Remove-Item Env:USERPROFILE -ErrorAction SilentlyContinue }
    if ($null -ne $oldPluginsHome) { $env:ANTIGRAVITY_PLUGINS_HOME = $oldPluginsHome } else { Remove-Item Env:ANTIGRAVITY_PLUGINS_HOME -ErrorAction SilentlyContinue }
}
