"""End-to-end and installed CLI subprocess tests against real Google Antigravity IDE & plugins."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from cli_anything.antigravity.core import project as proj_mod
from cli_anything.antigravity.utils import antigravity_backend as backend


def _resolve_cli(name: str) -> list[str]:
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ---------------------------------------------------------------------------
# Real Backend E2E Tests (real Antigravity IDE CLI & live installed plugin)
# ---------------------------------------------------------------------------
def test_e2e_real_antigravity_ide_version() -> None:
    info = backend.get_ide_version()
    assert os.path.isfile(info["binary"])
    assert info["version"] != "unknown"
    assert "." in info["version"]
    print(f"\n  Antigravity IDE: {info['version']} ({info['arch']}) @ {info['binary']}")


def test_e2e_real_antigravity_ide_extensions_list() -> None:
    res = backend.list_ide_extensions(show_versions=True)
    assert os.path.isfile(res["binary"])
    assert isinstance(res["extensions"], list)
    for item in res["extensions"]:
        assert "." in item["id"]
    print(f"\n  Antigravity IDE extensions discovered: {res['count']}")


def test_e2e_dogfood_validate_installed_cli_anything_plugin() -> None:
    live_plugin = Path.home() / ".gemini" / "config" / "plugins" / "cli-anything"
    assert live_plugin.is_dir(), f"Expected installed cli-anything plugin at {live_plugin}"
    report = proj_mod.validate_plugin_directory(str(live_plugin))
    assert report["valid"] is True, report
    assert report["summary"]["skills"] == 5
    assert report["summary"]["rules"] >= 1
    assert report["summary"]["agents"] >= 1
    assert report["summary"]["hooks"] >= 1


def test_e2e_host_customization_inventory_finds_cli_anything() -> None:
    inv = backend.inspect_host_customizations()
    names = {p["name"] for p in inv["plugins"]}
    assert "cli-anything" in names


# ---------------------------------------------------------------------------
# Installed CLI Subprocess Tests (uses _resolve_cli, no cwd pinning)
# ---------------------------------------------------------------------------
class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-antigravity")

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )

    def test_cli_help(self) -> None:
        res = self._run(["--help"])
        assert res.returncode == 0
        for grp in ("project", "plugin", "skill", "rule", "agent", "hook", "mcp", "discovery", "sdk", "ide", "session"):
            assert grp in res.stdout

    def test_cli_ide_detect_and_version_json(self) -> None:
        r_det = self._run(["--json", "ide", "detect"])
        det = json.loads(r_det.stdout)
        assert det["antigravity_ide"] is not None

        r_ver = self._run(["--json", "ide", "version"])
        ver = json.loads(r_ver.stdout)
        assert "." in ver["version"]

    def test_cli_autosave_dry_run_and_windows_glob_preservation(self, tmp_path: Path) -> None:
        manifest = tmp_path / "auto.agyproj.json"
        self._run(["--json", "project", "new", "-o", str(manifest), "--name", "glob-demo"])
        assert manifest.is_file()

        # One-shot rule add with wildcard globs MUST auto-save and preserve raw globs verbatim
        self._run(
            [
                "--json",
                "--project",
                str(manifest),
                "rule",
                "add",
                "harness-guard",
                "--trigger",
                "glob",
                "--globs",
                "**/agent-harness/**, *.tmp",
                "--body",
                "Follow PEP 420.",
            ]
        )
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        assert len(saved["rules"]) == 1
        assert saved["rules"][0]["globs"] == "**/agent-harness/**, *.tmp"

        # --dry-run mutation MUST NOT persist to disk
        self._run(
            [
                "--json",
                "--project",
                str(manifest),
                "--dry-run",
                "skill",
                "add",
                "ephemeral",
                "--description",
                "Should not save",
            ]
        )
        after_dry = json.loads(manifest.read_text(encoding="utf-8"))
        assert after_dry["skills"] == []

    def test_cli_full_plugin_authoring_export_validate_and_sdk_workflow(self, tmp_path: Path) -> None:
        manifest = tmp_path / "workflow.agyproj.json"
        exported_dir = tmp_path / "dist" / "team-plugin"
        sdk_script = tmp_path / "dist" / "run_agent.py"

        self._run(["--json", "project", "new", "-o", str(manifest), "--name", "team-plugin", "--version", "1.2.0"])
        self._run(["--json", "--project", str(manifest), "plugin", "add-prompt", "/team-audit inspect repo"])
        self._run(
            [
                "--json",
                "--project",
                str(manifest),
                "skill",
                "add",
                "team-audit",
                "--description",
                "Audit repository conventions",
                "--body",
                "# /team-audit\n\nCheck repository health.",
            ]
        )
        self._run(
            [
                "--json",
                "--project",
                str(manifest),
                "rule",
                "add",
                "py-rules",
                "--trigger",
                "glob",
                "--globs",
                "**/*.py",
                "--body",
                "Keep functions typed.",
            ]
        )
        self._run(
            [
                "--json",
                "--project",
                str(manifest),
                "agent",
                "add",
                "team-auditor",
                "--description",
                "Read-only auditor",
                "--policy",
                "sandbox",
            ]
        )
        self._run(["--json", "--project", str(manifest), "discovery", "bridge-clihub"])

        r_exp = self._run(
            ["--json", "--project", str(manifest), "project", "export", "-o", str(exported_dir), "--overwrite"]
        )
        exp_data = json.loads(r_exp.stdout)
        assert exp_data["file_count"] == 5

        r_val = self._run(["--json", "plugin", "validate-dir", str(exported_dir)])
        assert json.loads(r_val.stdout)["valid"] is True

        r_sdk = self._run(["--json", "--project", str(manifest), "sdk", "export-python", "-o", str(sdk_script)])
        assert json.loads(r_sdk.stdout)["bytes"] > 100
        ast.parse(sdk_script.read_text(encoding="utf-8"))
        print(f"\n  Exported Antigravity plugin: {exported_dir} + SDK runner: {sdk_script}")

    def test_cli_dogfood_validate_live_cli_anything_plugin(self) -> None:
        live_plugin = Path.home() / ".gemini" / "config" / "plugins" / "cli-anything"
        res = self._run(["--json", "plugin", "validate-dir", str(live_plugin)])
        data = json.loads(res.stdout)
        assert data["valid"] is True
        assert data["summary"]["skills"] == 5

    def test_cli_repl_preserves_json_and_rolls_back_failed_mutation(self, tmp_path: Path) -> None:
        manifest = tmp_path / "repl.agyproj.json"
        script = (
            f'project new -o "{manifest}" --name repl-demo\n'
            "skill remove does-not-exist\n"
            "session status\n"
            "exit\n"
        )
        proc = subprocess.run(
            self.CLI_BASE + ["--json"],
            input=script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        assert proc.returncode == 0
        assert '"undo_depth": 0' in proc.stdout
        assert '"modified": false' in proc.stdout
