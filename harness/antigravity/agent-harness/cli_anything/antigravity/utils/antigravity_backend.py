"""Real Google Antigravity CLI/IDE backend wrapper and read-only host inspector.

Wraps documented, sanctioned public Google Antigravity surfaces only:
- `antigravity-ide` CLI (`--version`, `--list-extensions`, `--diff`, `--goto`)
- `agy` CLI (`--version`, `agy plugin list|validate --strict`) when installed
- Public customization directories (`~/.gemini/config/{plugins,skills,rules,agents,skills.json,plugins.json,hooks.json}`
  and `<workspace>/.agents/`)

Never reads or modifies `~/.gemini/config/config.json` and never probes undocumented
local services.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SECRET_KEY_RE = re.compile(r"(token|key|secret|password|auth|bearer|credential)", re.IGNORECASE)
EXT_LINE_RE = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9._-]*\.[a-zA-Z0-9._-]+)(?:@([^\s]+))?$")


class AntigravityBackendError(RuntimeError):
    """Raised when an installed Antigravity CLI backend fails or is unavailable."""

    def __init__(
        self,
        message: str,
        returncode: int | None = None,
        stdout: str = "",
        stderr: str = "",
        command: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command or []


def redact_secrets(obj: Any) -> Any:
    """Recursively mask sensitive env/header values when rendering MCP configs."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, str) and SECRET_KEY_RE.search(str(k)):
                out[k] = "***"
            else:
                out[k] = redact_secrets(v)
        return out
    if isinstance(obj, list):
        return [redact_secrets(item) for item in obj]
    return obj


def find_antigravity_ide() -> str:
    """Locate the installed `antigravity-ide` CLI executable."""
    override = os.environ.get("CLI_ANYTHING_ANTIGRAVITY_IDE_BIN", "").strip()
    if override:
        if os.path.isfile(override):
            return override
        raise AntigravityBackendError(
            f"CLI_ANYTHING_ANTIGRAVITY_IDE_BIN points to a missing file: {override}"
        )

    for candidate in ("antigravity-ide", "antigravity-ide.cmd"):
        found = shutil.which(candidate)
        if found:
            return found

    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app, "Programs", "Antigravity IDE", "bin", "antigravity-ide.cmd"),
            os.path.join(local_app, "Programs", "Antigravity IDE", "Antigravity IDE.exe"),
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
    elif sys.platform == "darwin":
        mac_bin = "/Applications/Antigravity IDE.app/Contents/Resources/app/bin/antigravity-ide"
        if os.path.isfile(mac_bin):
            return mac_bin

    raise AntigravityBackendError(
        "Antigravity IDE CLI (`antigravity-ide`) was not found.\n"
        "Install Google Antigravity IDE from https://antigravity.google/ or set "
        "CLI_ANYTHING_ANTIGRAVITY_IDE_BIN=/path/to/antigravity-ide"
    )


def find_agy() -> str | None:
    """Locate the optional `agy` terminal CLI executable if installed on this host."""
    override = os.environ.get("CLI_ANYTHING_AGY_BIN", "").strip()
    if override and os.path.isfile(override):
        return override
    for candidate in ("agy", "agy.cmd", "agy.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def find_antigravity_app() -> str | None:
    """Locate the desktop Antigravity App binary if installed on this host."""
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        app_exe = os.path.join(local_app, "Programs", "antigravity", "Antigravity.exe")
        if app_exe and os.path.isfile(app_exe):
            return app_exe
    elif sys.platform == "darwin":
        mac_app = "/Applications/Antigravity.app"
        if os.path.exists(mac_app):
            return mac_app
    return None


def _run_subprocess(cmd: list[str], *, timeout: int = 60, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def get_ide_version() -> dict[str, Any]:
    """Query the live installed `antigravity-ide --version` output."""
    exe = find_antigravity_ide()
    proc = _run_subprocess([exe, "--version"])
    if proc.returncode != 0:
        raise AntigravityBackendError(
            f"antigravity-ide --version failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}",
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=[exe, "--version"],
        )
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return {
        "binary": exe,
        "version": lines[0] if len(lines) > 0 else "unknown",
        "commit": lines[1] if len(lines) > 1 else "",
        "arch": lines[2] if len(lines) > 2 else "",
        "raw_lines": lines,
    }


def parse_extensions_output(stdout: str) -> list[dict[str, str]]:
    """Parse `antigravity-ide --list-extensions [--show-versions]` lines cleanly."""
    items: list[dict[str, str]] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = EXT_LINE_RE.match(line)
        if not m:
            continue
        items.append({"id": m.group(1), "version": m.group(2) or ""})
    return items


def list_ide_extensions(*, show_versions: bool = True, category: str | None = None) -> dict[str, Any]:
    """List installed Antigravity IDE extensions via real `antigravity-ide --list-extensions`."""
    exe = find_antigravity_ide()
    cmd = [exe, "--list-extensions"]
    if show_versions:
        cmd.append("--show-versions")
    if category:
        cmd.extend(["--category", category])
    proc = _run_subprocess(cmd)
    if proc.returncode != 0:
        raise AntigravityBackendError(
            f"antigravity-ide --list-extensions failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}",
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=cmd,
        )
    exts = parse_extensions_output(proc.stdout)
    return {
        "binary": exe,
        "count": len(exts),
        "extensions": exts,
        "command": cmd,
    }


def run_agy(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
    """Run a documented `agy` CLI command when `agy` is installed on the host."""
    agy = find_agy()
    if not agy:
        raise AntigravityBackendError(
            "Antigravity CLI (`agy`) was not found in PATH. Install `agy` or set CLI_ANYTHING_AGY_BIN."
        )
    cmd = [agy] + args
    proc = _run_subprocess(cmd, timeout=timeout)
    if proc.returncode != 0:
        raise AntigravityBackendError(
            f"agy exited with code {proc.returncode}: {(proc.stderr or proc.stdout).strip()}",
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=cmd,
        )
    return {
        "binary": agy,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def detect_host_surfaces() -> dict[str, Any]:
    """Detect all installed Google Antigravity CLI/IDE/App/SDK surfaces on the host."""
    ide_bin: str | None = None
    try:
        ide_bin = find_antigravity_ide()
    except AntigravityBackendError:
        ide_bin = None

    sdk_installed = False
    try:
        sdk_installed = importlib.util.find_spec("google.antigravity") is not None
    except ModuleNotFoundError:
        sdk_installed = False

    global_config_dir = Path.home() / ".gemini" / "config"
    return {
        "antigravity_ide": ide_bin,
        "antigravity_app": find_antigravity_app(),
        "agy_cli": find_agy(),
        "python_sdk_installed": sdk_installed,
        "global_config_dir": str(global_config_dir),
        "global_config_exists": global_config_dir.is_dir(),
    }


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def inspect_host_customizations(
    *,
    global_root: str | None = None,
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """Read-only inventory of documented Antigravity customizations (never reads `config.json`)."""
    g_root = Path(global_root).resolve() if global_root else (Path.home() / ".gemini" / "config")
    result: dict[str, Any] = {
        "global_root": str(g_root),
        "plugins": [],
        "skills": [],
        "rules": [],
        "agents": [],
        "skills_json_entries": [],
        "plugins_json_entries": [],
        "workspace": None,
    }

    plugins_dir = g_root / "plugins"
    if plugins_dir.is_dir():
        for child in sorted(plugins_dir.iterdir()):
            manifest = child / "plugin.json"
            if child.is_dir() and manifest.is_file():
                data = _safe_read_json(manifest) or {}
                result["plugins"].append(
                    {
                        "dir": child.name,
                        "name": data.get("name", child.name),
                        "version": data.get("version", ""),
                        "displayName": data.get("displayName", ""),
                        "path": str(child),
                    }
                )

    skills_dir = g_root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                result["skills"].append({"name": child.name, "path": str(child / "SKILL.md")})

    rules_dir = g_root / "rules"
    if rules_dir.is_dir():
        for f in sorted(rules_dir.glob("*.md")):
            result["rules"].append({"name": f.stem, "path": str(f), "bytes": f.stat().st_size})

    agents_dir = g_root / "agents"
    if agents_dir.is_dir():
        for f in sorted(agents_dir.glob("*.md")):
            result["agents"].append({"name": f.stem, "path": str(f)})

    skills_json = _safe_read_json(g_root / "skills.json")
    if isinstance(skills_json, dict) and isinstance(skills_json.get("entries"), list):
        result["skills_json_entries"] = skills_json["entries"]

    plugins_json = _safe_read_json(g_root / "plugins.json")
    if isinstance(plugins_json, dict) and isinstance(plugins_json.get("entries"), list):
        result["plugins_json_entries"] = plugins_json["entries"]

    if workspace_root:
        ws = Path(workspace_root).resolve() / ".agents"
        ws_info: dict[str, Any] = {
            "agents_dir": str(ws),
            "exists": ws.is_dir(),
            "plugins": [],
            "skills": [],
            "rules": [],
            "agents": [],
        }
        if ws.is_dir():
            for sub, key, pattern in (
                ("plugins", "plugins", "*/plugin.json"),
                ("skills", "skills", "*/SKILL.md"),
                ("rules", "rules", "*.md"),
                ("agents", "agents", "*.md"),
            ):
                base = ws / sub
                if base.is_dir():
                    ws_info[key] = [str(p) for p in sorted(base.glob(pattern))]
        result["workspace"] = ws_info

    return result
