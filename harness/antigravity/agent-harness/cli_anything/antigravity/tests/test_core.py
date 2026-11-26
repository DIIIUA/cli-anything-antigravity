"""Unit tests for cli-anything-antigravity core modules (zero external dependencies)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from cli_anything.antigravity.core import export as export_mod
from cli_anything.antigravity.core import project as proj_mod
from cli_anything.antigravity.core.session import Session, _locked_save_json
from cli_anything.antigravity.utils import antigravity_backend as backend


def test_create_project_and_validation_rejects_bad_inputs() -> None:
    proj = proj_mod.create_project("demo-tools", scope="plugin", version="1.2.3")
    assert proj["name"] == "demo-tools"
    assert proj["plugin"]["$schema"] == proj_mod.PLUGIN_SCHEMA_URL
    assert proj_mod.validate_project(proj)["valid"] is True

    with pytest.raises(ValueError, match="Invalid project/plugin slug"):
        proj_mod.create_project("Bad Name!")
    with pytest.raises(ValueError, match="Invalid scope"):
        proj_mod.create_project("demo", scope="unknown")
    with pytest.raises(ValueError, match="Invalid semver"):
        proj_mod.create_project("demo", version="v1")


def test_parse_yaml_frontmatter_handles_folded_and_lists() -> None:
    md = """---
name: sample-agent
description: >-
  First line
  second line
subagent: true
mainAgent: false
skills:
  - skills/one
  - skills/two
---

# Body text
"""
    fm, body = proj_mod.parse_yaml_frontmatter(md)
    assert fm["name"] == "sample-agent"
    assert fm["description"] == "First line second line"
    assert fm["subagent"] is True
    assert fm["mainAgent"] is False
    assert fm["skills"] == ["skills/one", "skills/two"]
    assert body.startswith("# Body text")


def test_set_plugin_meta_and_suggested_prompts() -> None:
    proj = proj_mod.create_project("meta-test")
    meta = proj_mod.set_plugin_meta(
        proj,
        display_name="Meta Tools",
        version="2.0.0",
        description="Updated description",
        keywords=["cli", "antigravity"],
    )
    assert meta["displayName"] == "Meta Tools"
    assert meta["version"] == "2.0.0"

    prompts = proj_mod.add_suggested_prompt(proj, "/meta-run check repo")
    assert prompts == ["/meta-run check repo"]


def test_skill_crud_and_validation() -> None:
    proj = proj_mod.create_project("sk")
    proj_mod.add_skill(proj, "audit-code", "Audit repository", "# Audit", allowed_tools=["read_file"])
    assert len(proj["skills"]) == 1
    proj_mod.add_skill(proj, "audit-code", "Updated audit", "# Audit v2")
    assert len(proj["skills"]) == 1
    assert proj["skills"][0]["description"] == "Updated audit"

    removed = proj_mod.remove_skill(proj, "audit-code")
    assert removed["name"] == "audit-code"
    assert proj["skills"] == []


def test_rule_trigger_glob_and_24kb_cap() -> None:
    proj = proj_mod.create_project("rl")
    with pytest.raises(ValueError, match="--globs"):
        proj_mod.add_rule(proj, "bad-glob", "glob", "Rule body")
    with pytest.raises(ValueError, match="24000-byte"):
        proj_mod.add_rule(proj, "huge", "always_on", "x" * 25000)

    added = proj_mod.add_rule(
        proj, "py-style", "glob", "Use type hints.", globs="**/*.py, **/pyproject.toml"
    )
    assert added["globs"] == "**/*.py, **/pyproject.toml"
    assert proj_mod.validate_project(proj)["valid"] is True


def test_agent_and_tools_allowlist_warning() -> None:
    proj = proj_mod.create_project("ag")
    proj_mod.add_agent(
        proj,
        "code-auditor",
        "Read-only auditor",
        "Audit only.",
        command_execution_policy="sandbox",
        skills=["skills/audit-code"],
    )
    assert proj_mod.validate_project(proj)["warnings"] == []
    # Injecting static tools allowlist produces a proactive warning
    proj["agents"][0]["tools"] = ["read_file"]
    rep = proj_mod.validate_project(proj)
    assert rep["valid"] is True
    assert any("tools:" in w for w in rep["warnings"])


def test_hooks_add_toggle_and_remove() -> None:
    proj = proj_mod.create_project("hk")
    proj_mod.add_command_hook(
        proj, "pep420-guard", "PreToolUse", "python -S ./guard.py", matcher="write_file", enabled=False
    )
    assert proj["hooks"]["pep420-guard"]["enabled"] is False
    proj_mod.set_hook_enabled(proj, "pep420-guard", True)
    assert proj["hooks"]["pep420-guard"]["enabled"] is True
    proj_mod.remove_hook_group(proj, "pep420-guard")
    assert proj["hooks"] == {}


def test_mcp_stdio_http_and_secret_redaction() -> None:
    proj = proj_mod.create_project("mc")
    proj_mod.add_mcp_stdio(
        proj, "local_srv", "python", args=["server.py"], env={"API_KEY": "super-secret", "MODE": "dev"}
    )
    proj_mod.add_mcp_http(
        proj,
        "remote-srv",
        "https://mcp.example.com/sse",
        headers={"Authorization": "Bearer xyz123", "X-App": "agy"},
    )
    with pytest.raises(ValueError, match="Invalid MCP server name"):
        proj_mod.add_mcp_stdio(proj, "bad name!", "python")
    with pytest.raises(ValueError, match="http:// or https://"):
        proj_mod.add_mcp_http(proj, "bad_url", "ftp://example.com")

    redacted = backend.redact_secrets(proj["mcp_servers"])
    assert redacted["local_srv"]["env"]["API_KEY"] == "***"
    assert redacted["local_srv"]["env"]["MODE"] == "dev"
    assert redacted["remote-srv"]["headers"]["Authorization"] == "***"
    assert redacted["remote-srv"]["headers"]["X-App"] == "agy"


def test_discovery_and_sdk_config_validation() -> None:
    proj = proj_mod.create_project("disc")
    proj_mod.add_discovery_entry(proj, "skills", "~/.cli-hub/matrix")
    proj_mod.add_discovery_entry(proj, "plugins", "./custom-plugins", exclude=["draft-.*"])
    sdk = proj_mod.configure_sdk(
        proj, profile="litert", model="gemma-local", capabilities="file_tools", policy="safe_defaults"
    )
    assert sdk["profile"] == "litert"
    assert sdk["policy"] == "safe_defaults"


def test_export_dry_run_materialize_and_roundtrip_import(tmp_path: Path) -> None:
    proj = proj_mod.create_project("demo-bundle", version="1.0.0")
    proj_mod.add_skill(proj, "demo-skill", "Run demo", "# Demo Skill")
    proj_mod.add_rule(proj, "demo-rule", "glob", "Always check tests.", globs="**/*.py")
    proj_mod.add_agent(proj, "demo-auditor", "Read-only auditor", "Inspect cleanly.")
    proj_mod.add_command_hook(proj, "guard", "PreToolUse", "python ./guard.py", matcher="write_file", enabled=False)
    proj_mod.add_mcp_http(proj, "docs", "https://docs.example.com/mcp")
    proj_mod.add_discovery_entry(proj, "skills", "~/.cli-hub/matrix")

    out_dir = tmp_path / "exported"
    dry = export_mod.export_project(proj, str(out_dir), dry_run=True)
    assert dry["dry_run"] is True
    assert not out_dir.exists()

    written = export_mod.export_project(proj, str(out_dir), preset="full")
    assert written["file_count"] == 7
    assert (out_dir / "plugin.json").is_file()
    assert (out_dir / "skills" / "demo-skill" / "SKILL.md").is_file()
    assert (out_dir / "rules" / "demo-rule.md").is_file()
    assert (out_dir / "agents" / "demo-auditor.md").is_file()
    assert (out_dir / "hooks.json").is_file()
    assert (out_dir / "mcp_config.json").is_file()
    assert (out_dir / "skills.json").is_file()

    # Refuses overwrite without flag
    with pytest.raises(FileExistsError):
        export_mod.export_project(proj, str(out_dir), overwrite=False)

    # Round-trip import and directory validation
    rep = proj_mod.validate_plugin_directory(str(out_dir))
    assert rep["valid"] is True, rep
    reimported = proj_mod.import_from_dir(str(out_dir))
    assert reimported["plugin"]["name"] == "demo-bundle"
    assert len(reimported["skills"]) == 1
    assert len(reimported["rules"]) == 1
    assert len(reimported["agents"]) == 1


def test_render_sdk_python_produces_valid_ast() -> None:
    proj = proj_mod.create_project("sdk-demo")
    proj_mod.configure_sdk(
        proj,
        profile="local",
        model="gemini-4-hydrogen",
        capabilities="nondestructive",
        policy="workspace_only",
        skills_paths=["~/.gemini/config/skills"],
    )
    code = export_mod.render_sdk_python(proj)
    tree = ast.parse(code)
    assert isinstance(tree, ast.Module)
    assert "LocalAgentConfig" in code
    assert "policy.workspace_only()" in code


def test_export_presets_and_profiles_exist() -> None:
    assert {"plugin-bundle", "workspace-agents", "full"} <= set(export_mod.EXPORT_PRESETS)
    assert len(proj_mod.list_profiles()) >= 4


def test_session_atomic_mutate_rollback_and_undo_redo() -> None:
    sess = Session()
    sess.set_project(proj_mod.create_project("sess"))
    sess.mutate("add skill", lambda p: proj_mod.add_skill(p, "s1", "First skill", "Body"))
    assert sess.status()["undo_depth"] == 1

    with pytest.raises(KeyError):
        sess.mutate("remove missing", lambda p: proj_mod.remove_skill(p, "nonexistent"))
    assert sess.status()["undo_depth"] == 1
    assert len(sess.history()) == 1

    sess.undo()
    assert sess.require_project()["skills"] == []
    sess.redo()
    assert len(sess.require_project()["skills"]) == 1


def test_locked_save_json_truncates_shorter_payload(tmp_path: Path) -> None:
    p = tmp_path / "manifest.agyproj.json"
    _locked_save_json(str(p), {"payload": "x" * 2048})
    _locked_save_json(str(p), {"payload": "ok"})
    assert json.loads(p.read_text(encoding="utf-8")) == {"payload": "ok"}


def test_parse_extensions_output_filters_diagnostic_noise() -> None:
    sample = (
        "[createInstance] extensionManagementService depends on antigravityAnalytics which is NOT registered.\n"
        "golang.go@0.56.1\n"
        "ms-python.python@2026.4.0\n"
        "plain.extension\n"
    )
    parsed = backend.parse_extensions_output(sample)
    assert parsed == [
        {"id": "golang.go", "version": "0.56.1"},
        {"id": "ms-python.python", "version": "2026.4.0"},
        {"id": "plain.extension", "version": ""},
    ]


def test_inspect_host_customizations_isolated_never_reads_config_json(tmp_path: Path) -> None:
    g_root = tmp_path / "config"
    (g_root / "plugins" / "demo").mkdir(parents=True)
    (g_root / "plugins" / "demo" / "plugin.json").write_text(
        json.dumps({"name": "demo", "version": "1.0.0", "displayName": "Demo"}), encoding="utf-8"
    )
    (g_root / "config.json").write_text('{"private": "must-never-appear"}', encoding="utf-8")
    (g_root / "skills.json").write_text(json.dumps({"entries": [{"path": "~/.cli-hub/matrix"}]}), encoding="utf-8")

    info = backend.inspect_host_customizations(global_root=str(g_root))
    assert len(info["plugins"]) == 1
    assert info["plugins"][0]["name"] == "demo"
    assert info["skills_json_entries"] == [{"path": "~/.cli-hub/matrix"}]
    assert "must-never-appear" not in json.dumps(info)
