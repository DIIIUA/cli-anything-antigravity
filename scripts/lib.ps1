# Shared helpers for CLI-Anything Google Antigravity plugin install/uninstall (PowerShell).

function Normalize-CliAnythingPathKey {
    param([Parameter(Mandatory = $true)][string]$Path)
    return $Path.Replace("/", "\").TrimEnd("\").ToLowerInvariant()
}

function Expand-CliAnythingPath {
    param([Parameter(Mandatory = $true)][string]$Raw)
    if ($Raw.StartsWith("~")) {
        $homePath = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
        $Raw = Join-Path $homePath $Raw.Substring(1).TrimStart("\", "/")
    }
    if (-not [System.IO.Path]::IsPathRooted($Raw)) {
        $Raw = Join-Path (Get-Location).Path $Raw
    }
    return [System.IO.Path]::GetFullPath($Raw)
}

function Resolve-CliAnythingPluginsHome {
    param(
        [Parameter(Mandatory = $true)][string]$Raw,
        [switch]$Create
    )

    if ([string]::IsNullOrWhiteSpace($Raw) -or $Raw -eq "." -or $Raw -eq "..") {
        throw "Invalid ANTIGRAVITY_PLUGINS_HOME: $Raw"
    }

    # GetFullPath collapses ".." without creating the directory.
    $full = Expand-CliAnythingPath -Raw $Raw
    $name = [System.IO.Path]::GetFileName($full.TrimEnd("\", "/"))
    if ($name -ne "plugins") {
        throw "ANTIGRAVITY_PLUGINS_HOME must resolve to a directory named 'plugins' (got: $full)`nExample: $env:USERPROFILE\.gemini\config\plugins"
    }

    if ($Create) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
    }
    return $full
}

function Resolve-CliAnythingWorkspaceRoot {
    param([Parameter(Mandatory = $true)][string]$Raw)

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "Workspace path must not be empty."
    }
    $full = Expand-CliAnythingPath -Raw $Raw
    if (-not (Test-Path -LiteralPath $full -PathType Container)) {
        throw "Workspace directory does not exist: $full"
    }
    return $full
}

function Test-CliAnythingInstallPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $key = Normalize-CliAnythingPathKey $Path
    if (-not $key.EndsWith("\plugins\cli-anything")) {
        return $false
    }
    return ([System.IO.Path]::GetFileName($key) -eq "cli-anything")
}

function Get-CliAnythingDiscoveryPointerPath {
    $userGemini = if ($env:USERPROFILE) {
        Join-Path $env:USERPROFILE ".gemini"
    } elseif ($env:HOME) {
        Join-Path $env:HOME ".gemini"
    } else {
        throw "USERPROFILE/HOME unavailable."
    }
    return (Join-Path $userGemini "cli-anything-generator.root")
}
