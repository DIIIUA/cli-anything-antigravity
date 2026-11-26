"""Materialize Antigravity plugin/workspace bundles and Python SDK runner scripts."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from cli_anything.antigravity.core.project import validate_project


EXPORT_PRESETS: dict[str, dict[str, Any]] = {
    "plugin-bundle": {
        "description": "Full Google Antigravity v1 plugin directory (plugin.json, skills/, rules/, agents/, hooks.json, mcp_config.json)",
        "include_plugin_json": True,
        "include_discovery": False,
    },
    "workspace-agents": {
        "description": "Repository .agents/ customization directory (skills/, rules/, agents/, hooks.json, skills.json, plugins.json)",
        "include_plugin_json": False,
        "include_discovery": True,
    },
    "full": {
        "description": "Materialize all declared plugin, customization, and discovery files",
        "include_plugin_json": True,
        "include_discovery": True,
    },
}


def _render_skill_md(skill: dict[str, Any]) -> str:
    lines = [
        "---",
        f"name: {skill['name']}",
        f"description: {json.dumps(skill['description'], ensure_ascii=False)}",
    ]
    if skill.get("allowed_tools"):
        lines.append("allowed-tools:")
        for t in skill["allowed_tools"]:
            lines.append(f"  - {t}")
    lines.extend(["---", "", skill["body"].strip(), ""])
    return "\n".join(lines)


def _render_rule_md(rule: dict[str, Any]) -> str:
    lines = ["---", f"trigger: {rule['trigger']}"]
    if rule.get("globs"):
        lines.append(f"globs: {json.dumps(rule['globs'], ensure_ascii=False)}")
    if rule.get("description"):
        lines.append(f"description: {json.dumps(rule['description'], ensure_ascii=False)}")
    lines.extend(["---", "", rule["body"].strip(), ""])
    return "\n".join(lines)


def _render_agent_md(agent: dict[str, Any]) -> str:
    lines = [
        "---",
        f"name: {agent['name']}",
        f"description: {json.dumps(agent['description'], ensure_ascii=False)}",
        f"model: {agent.get('model', 'inherit')}",
        f"mainAgent: {'true' if agent.get('mainAgent', True) else 'false'}",
        f"subagent: {'true' if agent.get('subagent', True) else 'false'}",
        f"commandExecutionPolicy: {agent.get('commandExecutionPolicy', 'sandbox')}",
    ]
    if agent.get("skills"):
        lines.append("skills:")
        for sk in agent["skills"]:
            lines.append(f"  - {sk}")
    lines.extend(["---", "", agent["body"].strip(), ""])
    return "\n".join(lines)


def export_project(
    project: dict[str, Any],
    dest_dir: str,
    *,
    preset: str = "full",
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export an `.agyproj.json` manifest into a valid Google Antigravity directory structure."""
    if preset not in EXPORT_PRESETS:
        raise ValueError(f"Unknown export preset '{preset}'. Choose from: {sorted(EXPORT_PRESETS)}")
    validation = validate_project(project)
    if not validation["valid"]:
        raise ValueError("Project validation failed: " + "; ".join(validation["errors"]))

    cfg = EXPORT_PRESETS[preset]
    root = Path(dest_dir).resolve()
    planned: dict[Path, str] = {}

    if cfg["include_plugin_json"] and project.get("scope", "plugin") == "plugin":
        planned[root / "plugin.json"] = json.dumps(project["plugin"], indent=2, ensure_ascii=False) + "\n"

    for sk in project.get("skills", []):
        planned[root / "skills" / sk["name"] / "SKILL.md"] = _render_skill_md(sk)

    for rule in project.get("rules", []):
        planned[root / "rules" / f"{rule['name']}.md"] = _render_rule_md(rule)

    for ag in project.get("agents", []):
        planned[root / "agents" / f"{ag['name']}.md"] = _render_agent_md(ag)

    if project.get("hooks"):
        planned[root / "hooks.json"] = json.dumps(project["hooks"], indent=2, ensure_ascii=False) + "\n"

    if project.get("mcp_servers"):
        planned[root / "mcp_config.json"] = (
            json.dumps({"mcpServers": project["mcp_servers"]}, indent=2, ensure_ascii=False) + "\n"
        )

    if cfg["include_discovery"]:
        disc = project.get("discovery", {})
        if disc.get("skills_entries"):
            planned[root / "skills.json"] = (
                json.dumps({"entries": disc["skills_entries"]}, indent=2, ensure_ascii=False) + "\n"
            )
        if disc.get("plugins_entries"):
            planned[root / "plugins.json"] = (
                json.dumps({"entries": disc["plugins_entries"]}, indent=2, ensure_ascii=False) + "\n"
            )

    rel_files = sorted(str(p.relative_to(root)).replace("\\", "/") for p in planned)
    if dry_run:
        return {
            "dry_run": True,
            "destination": str(root),
            "preset": preset,
            "file_count": len(rel_files),
            "files": rel_files,
        }

    if not overwrite:
        conflicts = [str(p) for p in planned if p.exists()]
        if conflicts:
            raise FileExistsError(
                f"Destination already contains {len(conflicts)} conflicting file(s) (e.g. {conflicts[0]}). Pass --overwrite to replace."
            )

    for path, content in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return {
        "dry_run": False,
        "destination": str(root),
        "preset": preset,
        "file_count": len(rel_files),
        "files": rel_files,
    }


def render_sdk_python(project: dict[str, Any]) -> str:
    """Generate a syntactically verified `google-antigravity` Python SDK runner script."""
    sdk = project.get("sdk_config", {})
    profile = sdk.get("profile", "local")
    model = sdk.get("model", "gemini-4-hydrogen")
    capabilities = sdk.get("capabilities", "read_only")
    policy_name = sdk.get("policy", "confirm_run_command")
    skills_paths = sdk.get("skills_paths", [])

    config_cls = {
        "local": "LocalAgentConfig",
        "litert": "LiteRTAgentConfig",
        "local-openai": "LocalOpenAIAgentConfig",
    }.get(profile, "LocalAgentConfig")

    cap_expr = f"BuiltinTools.{capabilities}()" if capabilities != "default" else "BuiltinTools.default()"
    skills_line = f"        skills_paths={skills_paths!r},\n" if skills_paths else ""

    source = f'''"""Auto-generated Google Antigravity Python SDK runner for {project.get("name", "antigravity")}."""

from __future__ import annotations

import asyncio
import sys

from google.antigravity import Agent, {config_cls}
from google.antigravity.hooks import policy
from google.antigravity.types import BuiltinTools, CapabilitiesConfig


def build_config() -> {config_cls}:
    """Construct the declarative Antigravity agent configuration."""
    return {config_cls}(
        model={model!r},
        capabilities=CapabilitiesConfig(builtin_tools={cap_expr}),
        policies=[policy.{policy_name}()],
{skills_line}    )


async def run_prompt(prompt: str) -> str:
    """Execute a single prompt against the configured Google Antigravity agent."""
    chunks: list[str] = []
    async with Agent(build_config()) as agent:
        response = await agent.chat(prompt)
        async for token in response:
            chunks.append(token)
    return "".join(chunks)


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Summarize the active workspace."
    print(asyncio.run(run_prompt(prompt)))


if __name__ == "__main__":
    main()
'''
    ast.parse(source)
    return source
