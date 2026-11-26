"""Click CLI and interactive REPL for Google Antigravity (`cli-anything-antigravity`)."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import click

from cli_anything.antigravity.core import export as export_mod
from cli_anything.antigravity.core import project as proj_mod
from cli_anything.antigravity.core.session import get_session
from cli_anything.antigravity.utils import antigravity_backend as backend
from cli_anything.antigravity.utils.repl_skin import ReplSkin

_use_json: bool = False
_repl_mode: bool = False
_repl_use_json: bool = False
_repl_dry_run: bool = False
_dry_run: bool = False


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _emit(data: Any, human: str | None = None) -> None:
    if _use_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    elif human is not None:
        click.echo(human)
    else:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _handle_error(exc: Exception) -> None:
    if _use_json:
        payload: dict[str, Any] = {"error": str(exc), "type": type(exc).__name__}
        if isinstance(exc, backend.AntigravityBackendError) and exc.returncode is not None:
            payload["returncode"] = exc.returncode
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Error: {exc}", err=True)
    if not _repl_mode:
        sys.exit(1)


def _parse_kv_pairs(pairs: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in pairs:
        if "=" not in raw:
            raise ValueError(f"Expected KEY=VALUE pair, got: {raw}")
        k, v = raw.split("=", 1)
        out[k.strip()] = v.strip()
    return out


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output structured JSON for agents.")
@click.option(
    "--project",
    "project_path",
    type=str,
    default=None,
    help="Load an existing .agyproj.json manifest before executing the command.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Preview mutations or exports without writing files to disk.",
)
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project_path: str | None, dry_run: bool) -> None:
    """Stateful CLI-Anything harness for Google Antigravity customizations, SDK configs, and IDE/agy CLI."""
    global _use_json, _dry_run
    _configure_utf8_stdio()
    if _repl_mode:
        _use_json = _repl_use_json or use_json
        _dry_run = _repl_dry_run or dry_run
    else:
        _use_json = use_json
        _dry_run = dry_run

    if project_path:
        try:
            sess = get_session()
            proj = proj_mod.open_project(project_path)
            sess.set_project(proj, project_path)
        except Exception as exc:
            _handle_error(exc)
            return

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, project_path=project_path)


@cli.result_callback()
def auto_save_on_exit(
    result: Any,
    use_json: bool,
    project_path: str | None,
    dry_run: bool,
    **kwargs: Any,
) -> None:
    """Auto-save modified session manifests after one-shot commands unless --dry-run."""
    if _repl_mode or dry_run:
        return
    sess = get_session()
    if sess.has_project() and sess._modified and sess.project_path:
        try:
            sess.save_session()
        except Exception as exc:
            click.echo(f"Warning: Auto-save failed: {exc}", err=True)


# ---------------------------------------------------------------------------
# project group
# ---------------------------------------------------------------------------
@cli.group()
def project() -> None:
    """Manage stateful Google Antigravity project manifests (.agyproj.json)."""


@project.command("new")
@click.option("-o", "--output", "manifest_path", required=True, help="Output path for the new .agyproj.json file.")
@click.option("--name", default=None, help="Plugin/workspace slug.")
@click.option("--scope", type=click.Choice(["plugin", "workspace", "global"]), default="plugin", show_default=True)
@click.option("--display-name", default=None, help="Human-readable plugin displayName.")
@click.option("--description", default="Google Antigravity customization bundle", show_default=True)
@click.option("--version", default="1.0.0", show_default=True)
def project_new(
    manifest_path: str,
    name: str | None,
    scope: str,
    display_name: str | None,
    description: str,
    version: str,
) -> None:
    """Create and save a new `.agyproj.json` manifest."""
    try:
        slug = name or os.path.splitext(os.path.basename(manifest_path))[0].replace(".agyproj", "")
        proj = proj_mod.create_project(
            name=slug,
            scope=scope,
            display_name=display_name,
            description=description,
            version=version,
        )
        sess = get_session()
        sess.set_project(proj, manifest_path)
        saved = manifest_path if _dry_run else sess.save_session(manifest_path)
        _emit(
            {"project_path": saved, "dry_run": _dry_run, "project": proj},
            f"Created Antigravity project '{proj['name']}' (scope={scope}) -> {saved}",
        )
    except Exception as exc:
        _handle_error(exc)


@project.command("open")
@click.argument("manifest_path")
def project_open(manifest_path: str) -> None:
    """Load an existing `.agyproj.json` manifest into the active session."""
    try:
        proj = proj_mod.open_project(manifest_path)
        sess = get_session()
        sess.set_project(proj, manifest_path)
        _emit(
            {"project_path": sess.project_path, "project": proj},
            f"Opened project '{proj['name']}' (skills={len(proj['skills'])}, rules={len(proj['rules'])}, agents={len(proj['agents'])})",
        )
    except Exception as exc:
        _handle_error(exc)


@project.command("save")
@click.argument("manifest_path", required=False, default=None)
def project_save(manifest_path: str | None) -> None:
    """Save the active project manifest via locked JSON write."""
    try:
        sess = get_session()
        target = manifest_path or sess.project_path
        if _dry_run:
            _emit({"dry_run": True, "project_path": target}, f"[dry-run] Would save manifest to {target}")
            return
        saved = sess.save_session(target)
        _emit({"project_path": saved, "saved": True}, f"Saved manifest to {saved}")
    except Exception as exc:
        _handle_error(exc)


@project.command("info")
def project_info() -> None:
    """Display the active project manifest summary."""
    try:
        sess = get_session()
        proj = sess.require_project()
        redacted = dict(proj)
        redacted["mcp_servers"] = backend.redact_secrets(proj.get("mcp_servers", {}))
        payload = {"project_path": sess.project_path, "modified": sess._modified, "project": redacted}
        human = (
            f"Project: {proj['name']} (scope={proj['scope']}, v{proj['plugin'].get('version')})\n"
            f"Skills: {len(proj['skills'])}, Rules: {len(proj['rules'])}, Agents: {len(proj['agents'])}, "
            f"Hooks: {len(proj['hooks'])}, MCP: {len(proj['mcp_servers'])}"
        )
        _emit(payload, human)
    except Exception as exc:
        _handle_error(exc)


@project.command("profiles")
def project_profiles() -> None:
    """List built-in Antigravity customization & SDK starter profiles."""
    profiles = proj_mod.list_profiles()
    lines = [f"  {p['name']:<18} [{p['scope']}] {p['description']}" for p in profiles]
    _emit({"profiles": profiles}, "\n".join(lines))


@project.command("validate")
def project_validate() -> None:
    """Validate the active manifest against Google Antigravity v1 schemas."""
    try:
        proj = get_session().require_project()
        report = proj_mod.validate_project(proj)
        lines = [f"Validation: {'VALID' if report['valid'] else 'INVALID'}"]
        for err in report["errors"]:
            lines.append(f"  ERROR: {err}")
        for warn in report["warnings"]:
            lines.append(f"  WARN:  {warn}")
        _emit(report, "\n".join(lines))
        if not report["valid"] and not _repl_mode:
            sys.exit(1)
    except Exception as exc:
        _handle_error(exc)


@project.command("import-dir")
@click.argument("source_dir")
@click.option("-o", "--output", "manifest_path", default=None, help="Optional path to save imported .agyproj.json.")
def project_import_dir(source_dir: str, manifest_path: str | None) -> None:
    """Ingest an existing Antigravity plugin or `.agents/` folder into a project manifest."""
    try:
        proj = proj_mod.import_from_dir(source_dir)
        sess = get_session()
        sess.set_project(proj, manifest_path)
        saved = None
        if manifest_path and not _dry_run:
            saved = sess.save_session(manifest_path)
        report = proj_mod.validate_project(proj)
        _emit(
            {
                "source_dir": str(Path(source_dir).resolve()),
                "saved_manifest": saved,
                "valid": report["valid"],
                "summary": report["summary"],
                "plugin_name": proj["plugin"].get("name"),
            },
            f"Imported '{proj['name']}' from {source_dir} (skills={len(proj['skills'])}, rules={len(proj['rules'])}, agents={len(proj['agents'])})",
        )
    except Exception as exc:
        _handle_error(exc)


@project.command("export")
@click.option("-o", "--out", "dest_dir", required=True, help="Target directory for exported Antigravity files.")
@click.option(
    "--preset",
    type=click.Choice(sorted(export_mod.EXPORT_PRESETS.keys())),
    default="full",
    show_default=True,
)
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing files in destination.")
def project_export(dest_dir: str, preset: str, overwrite: bool) -> None:
    """Materialize the project into an Antigravity plugin or `.agents/` directory."""
    try:
        proj = get_session().require_project()
        res = export_mod.export_project(proj, dest_dir, preset=preset, overwrite=overwrite, dry_run=_dry_run)
        prefix = "[dry-run] Would export" if res["dry_run"] else "Exported"
        _emit(res, f"{prefix} {res['file_count']} file(s) -> {res['destination']}")
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# plugin group
# ---------------------------------------------------------------------------
@cli.group()
def plugin() -> None:
    """Configure `plugin.json` metadata and validate plugin directories on disk."""


@plugin.command("set-meta")
@click.option("--display-name", default=None)
@click.option("--version", default=None)
@click.option("--description", default=None)
@click.option("--license", "license_id", default=None)
@click.option("--homepage", default=None)
@click.option("--repository", default=None)
@click.option("--keyword", "keywords", multiple=True)
def plugin_set_meta(
    display_name: str | None,
    version: str | None,
    description: str | None,
    license_id: str | None,
    homepage: str | None,
    repository: str | None,
    keywords: tuple[str, ...],
) -> None:
    """Update official v1 `plugin.json` metadata fields."""
    try:
        sess = get_session()
        meta = sess.mutate(
            "plugin set-meta",
            lambda p: proj_mod.set_plugin_meta(
                p,
                display_name=display_name,
                version=version,
                description=description,
                license_id=license_id,
                homepage=homepage,
                repository=repository,
                keywords=list(keywords) if keywords else None,
            ),
        )
        _emit({"plugin": meta}, f"Updated plugin.json metadata for '{meta['name']}' v{meta['version']}")
    except Exception as exc:
        _handle_error(exc)


@plugin.command("add-prompt")
@click.argument("prompt")
def plugin_add_prompt(prompt: str) -> None:
    """Add a suggested prompt to `plugin.json`."""
    try:
        prompts = get_session().mutate("plugin add-prompt", lambda p: proj_mod.add_suggested_prompt(p, prompt))
        _emit({"suggestedPrompts": prompts}, f"Suggested prompts ({len(prompts)}): {prompts[-1]}")
    except Exception as exc:
        _handle_error(exc)


@plugin.command("show")
def plugin_show() -> None:
    """Display the active `plugin.json` block."""
    try:
        proj = get_session().require_project()
        _emit(proj["plugin"])
    except Exception as exc:
        _handle_error(exc)


@plugin.command("validate-dir")
@click.argument("plugin_dir")
def plugin_validate_dir(plugin_dir: str) -> None:
    """Validate an existing Antigravity plugin directory on disk against v1 schemas."""
    try:
        report = proj_mod.validate_plugin_directory(plugin_dir)
        lines = [f"Plugin validation ({report['path']}): {'VALID' if report['valid'] else 'INVALID'}"]
        for err in report["errors"]:
            lines.append(f"  ERROR: {err}")
        for warn in report["warnings"]:
            lines.append(f"  WARN:  {warn}")
        _emit(report, "\n".join(lines))
        if not report["valid"] and not _repl_mode:
            sys.exit(1)
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# skill group
# ---------------------------------------------------------------------------
@cli.group()
def skill() -> None:
    """Manage Antigravity slash-command skills (`skills/<name>/SKILL.md`)."""


@skill.command("add")
@click.argument("name")
@click.option("--description", required=True, help="Skill activation summary.")
@click.option("--body", default="", help="Markdown instructions body.")
@click.option("--allowed-tool", "allowed_tools", multiple=True)
def skill_add(name: str, description: str, body: str, allowed_tools: tuple[str, ...]) -> None:
    """Add or update a skill in the project manifest."""
    try:
        item = get_session().mutate(
            f"skill add {name}",
            lambda p: proj_mod.add_skill(p, name, description, body, allowed_tools=list(allowed_tools) or None),
        )
        _emit({"skill": item}, f"Added skill '/{item['name']}'")
    except Exception as exc:
        _handle_error(exc)


@skill.command("remove")
@click.argument("name")
def skill_remove(name: str) -> None:
    """Remove a skill by name."""
    try:
        removed = get_session().mutate(f"skill remove {name}", lambda p: proj_mod.remove_skill(p, name))
        _emit({"removed": removed}, f"Removed skill '/{removed['name']}'")
    except Exception as exc:
        _handle_error(exc)


@skill.command("list")
def skill_list() -> None:
    """List declared skills in the active project."""
    try:
        skills = get_session().require_project()["skills"]
        lines = [f"  /{s['name']}: {s['description']}" for s in skills] or ["(no skills)"]
        _emit({"skills": skills}, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# rule group
# ---------------------------------------------------------------------------
@cli.group()
def rule() -> None:
    """Manage scoped Antigravity rules (`rules/<name>.md`)."""


@rule.command("add")
@click.argument("name")
@click.option("--trigger", type=click.Choice(["always_on", "model_decision", "glob", "manual"]), required=True)
@click.option("--body", required=True, help="Markdown rule content (<= 24 KB).")
@click.option("--globs", default=None, help="Comma-separated glob patterns (required for trigger=glob).")
@click.option("--description", default=None, help="Routing summary (required for trigger=model_decision).")
def rule_add(name: str, trigger: str, body: str, globs: str | None, description: str | None) -> None:
    """Add or update a scoped rule in the project manifest."""
    try:
        item = get_session().mutate(
            f"rule add {name}",
            lambda p: proj_mod.add_rule(p, name, trigger, body, globs=globs, description=description),
        )
        _emit({"rule": item}, f"Added rule '{item['name']}' (trigger={item['trigger']})")
    except Exception as exc:
        _handle_error(exc)


@rule.command("remove")
@click.argument("name")
def rule_remove(name: str) -> None:
    """Remove a rule by name."""
    try:
        removed = get_session().mutate(f"rule remove {name}", lambda p: proj_mod.remove_rule(p, name))
        _emit({"removed": removed}, f"Removed rule '{removed['name']}'")
    except Exception as exc:
        _handle_error(exc)


@rule.command("list")
def rule_list() -> None:
    """List declared rules in the active project."""
    try:
        rules = get_session().require_project()["rules"]
        lines = [f"  {r['name']} [trigger={r['trigger']}]" for r in rules] or ["(no rules)"]
        _emit({"rules": rules}, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# agent group
# ---------------------------------------------------------------------------
@cli.group()
def agent() -> None:
    """Manage custom Antigravity agents and subagents (`agents/<name>.md`)."""


@agent.command("add")
@click.argument("name")
@click.option("--description", required=True)
@click.option("--body", default="")
@click.option("--model", default="inherit", show_default=True)
@click.option("--main-agent/--no-main-agent", default=True, show_default=True)
@click.option("--subagent/--no-subagent", default=True, show_default=True)
@click.option(
    "--policy",
    "command_execution_policy",
    type=click.Choice(["sandbox", "off", "auto", "eager"]),
    default="sandbox",
    show_default=True,
)
@click.option("--skill", "skills", multiple=True, help="Referenced skill path (e.g. skills/my-skill).")
def agent_add(
    name: str,
    description: str,
    body: str,
    model: str,
    main_agent: bool,
    subagent: bool,
    command_execution_policy: str,
    skills: tuple[str, ...],
) -> None:
    """Add or update an `agents/<name>.md` definition."""
    try:
        item = get_session().mutate(
            f"agent add {name}",
            lambda p: proj_mod.add_agent(
                p,
                name,
                description,
                body,
                model=model,
                main_agent=main_agent,
                subagent=subagent,
                command_execution_policy=command_execution_policy,
                skills=list(skills) or None,
            ),
        )
        _emit({"agent": item}, f"Added agent '{item['name']}' (policy={item['commandExecutionPolicy']})")
    except Exception as exc:
        _handle_error(exc)


@agent.command("remove")
@click.argument("name")
def agent_remove(name: str) -> None:
    """Remove an agent definition by name."""
    try:
        removed = get_session().mutate(f"agent remove {name}", lambda p: proj_mod.remove_agent(p, name))
        _emit({"removed": removed}, f"Removed agent '{removed['name']}'")
    except Exception as exc:
        _handle_error(exc)


@agent.command("list")
def agent_list() -> None:
    """List declared agents in the active project."""
    try:
        agents = get_session().require_project()["agents"]
        lines = [
            f"  {a['name']} (subagent={a['subagent']}, policy={a['commandExecutionPolicy']})" for a in agents
        ] or ["(no agents)"]
        _emit({"agents": agents}, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# hook group
# ---------------------------------------------------------------------------
@cli.group()
def hook() -> None:
    """Manage lifecycle command hooks (`hooks.json`)."""


@hook.command("add-command")
@click.argument("group_name")
@click.option(
    "--event",
    type=click.Choice(["SessionStart", "PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"]),
    required=True,
)
@click.option("--command", required=True, help="Shell command to execute.")
@click.option("--matcher", default="*", show_default=True, help="Tool matcher regex (for PreToolUse/PostToolUse).")
@click.option("--timeout", default=10, type=int, show_default=True)
@click.option("--enabled/--disabled", default=False, show_default=True)
def hook_add_command(
    group_name: str,
    event: str,
    command: str,
    matcher: str,
    timeout: int,
    enabled: bool,
) -> None:
    """Add a command hook handler to a hook group."""
    try:
        grp = get_session().mutate(
            f"hook add-command {group_name}",
            lambda p: proj_mod.add_command_hook(
                p, group_name, event, command, matcher=matcher, timeout=timeout, enabled=enabled
            ),
        )
        _emit({"group": group_name, "config": grp}, f"Added {event} hook to group '{group_name}' (enabled={enabled})")
    except Exception as exc:
        _handle_error(exc)


@hook.command("set-enabled")
@click.argument("group_name")
@click.option("--enabled/--disabled", required=True)
def hook_set_enabled(group_name: str, enabled: bool) -> None:
    """Enable or disable a hook group."""
    try:
        grp = get_session().mutate(
            f"hook set-enabled {group_name}",
            lambda p: proj_mod.set_hook_enabled(p, group_name, enabled),
        )
        _emit({"group": group_name, "enabled": grp["enabled"]}, f"Hook group '{group_name}' enabled={grp['enabled']}")
    except Exception as exc:
        _handle_error(exc)


@hook.command("remove")
@click.argument("group_name")
def hook_remove(group_name: str) -> None:
    """Remove a hook group."""
    try:
        removed = get_session().mutate(f"hook remove {group_name}", lambda p: proj_mod.remove_hook_group(p, group_name))
        _emit({"removed": group_name, "config": removed}, f"Removed hook group '{group_name}'")
    except Exception as exc:
        _handle_error(exc)


@hook.command("list")
def hook_list() -> None:
    """List declared hook groups."""
    try:
        hooks = get_session().require_project()["hooks"]
        lines = [f"  {k} (enabled={v.get('enabled', True)})" for k, v in hooks.items()] or ["(no hooks)"]
        _emit({"hooks": hooks}, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# mcp group
# ---------------------------------------------------------------------------
@cli.group()
def mcp() -> None:
    """Manage MCP server definitions (`mcp_config.json`) with automatic secret redaction."""


@mcp.command("add-stdio")
@click.argument("name")
@click.option("--command", required=True)
@click.option("--arg", "args", multiple=True)
@click.option("--env", "env_pairs", multiple=True, help="KEY=VALUE environment variable.")
def mcp_add_stdio(name: str, command: str, args: tuple[str, ...], env_pairs: tuple[str, ...]) -> None:
    """Add a stdio MCP server definition."""
    try:
        env = _parse_kv_pairs(env_pairs) if env_pairs else None
        cfg = get_session().mutate(
            f"mcp add-stdio {name}",
            lambda p: proj_mod.add_mcp_stdio(p, name, command, args=list(args), env=env),
        )
        _emit({"name": name, "server": backend.redact_secrets(cfg)}, f"Added stdio MCP server '{name}'")
    except Exception as exc:
        _handle_error(exc)


@mcp.command("add-http")
@click.argument("name")
@click.option("--url", "server_url", required=True)
@click.option("--header", "header_pairs", multiple=True, help="Header=Value.")
@click.option("--auth-provider", default=None)
def mcp_add_http(
    name: str,
    server_url: str,
    header_pairs: tuple[str, ...],
    auth_provider: str | None,
) -> None:
    """Add a streamable HTTP MCP server definition."""
    try:
        headers = _parse_kv_pairs(header_pairs) if header_pairs else None
        cfg = get_session().mutate(
            f"mcp add-http {name}",
            lambda p: proj_mod.add_mcp_http(p, name, server_url, headers=headers, auth_provider_type=auth_provider),
        )
        _emit({"name": name, "server": backend.redact_secrets(cfg)}, f"Added HTTP MCP server '{name}'")
    except Exception as exc:
        _handle_error(exc)


@mcp.command("remove")
@click.argument("name")
def mcp_remove(name: str) -> None:
    """Remove an MCP server definition by name."""
    try:
        get_session().mutate(f"mcp remove {name}", lambda p: proj_mod.remove_mcp_server(p, name))
        _emit({"removed": name}, f"Removed MCP server '{name}'")
    except Exception as exc:
        _handle_error(exc)


@mcp.command("list")
def mcp_list() -> None:
    """List declared MCP servers (sensitive env/header values are redacted)."""
    try:
        servers = backend.redact_secrets(get_session().require_project()["mcp_servers"])
        lines = [
            f"  {k}: {v.get('command') or v.get('serverUrl')}" for k, v in servers.items()
        ] or ["(no MCP servers)"]
        _emit({"mcpServers": servers}, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# discovery group
# ---------------------------------------------------------------------------
@cli.group()
def discovery() -> None:
    """Manage zero-copy `skills.json` and `plugins.json` discovery entries."""


@discovery.command("add-skills")
@click.argument("path")
@click.option("--exclude", "excludes", multiple=True)
def discovery_add_skills(path: str, excludes: tuple[str, ...]) -> None:
    """Add a directory path to `skills.json`."""
    try:
        entry = get_session().mutate(
            f"discovery add-skills {path}",
            lambda p: proj_mod.add_discovery_entry(p, "skills", path, exclude=list(excludes) or None),
        )
        _emit({"entry": entry}, f"Added skills.json entry: {entry['path']}")
    except Exception as exc:
        _handle_error(exc)


@discovery.command("add-plugins")
@click.argument("path")
@click.option("--exclude", "excludes", multiple=True)
def discovery_add_plugins(path: str, excludes: tuple[str, ...]) -> None:
    """Add a directory path to `plugins.json`."""
    try:
        entry = get_session().mutate(
            f"discovery add-plugins {path}",
            lambda p: proj_mod.add_discovery_entry(p, "plugins", path, exclude=list(excludes) or None),
        )
        _emit({"entry": entry}, f"Added plugins.json entry: {entry['path']}")
    except Exception as exc:
        _handle_error(exc)


@discovery.command("bridge-clihub")
def discovery_bridge_clihub() -> None:
    """Register `~/.cli-hub/matrix` and `~/.agents/skills` in `skills.json` for CLI-Anything Hub."""
    try:
        def _apply(p: dict[str, Any]) -> list[dict[str, Any]]:
            return [
                proj_mod.add_discovery_entry(p, "skills", "~/.cli-hub/matrix"),
                proj_mod.add_discovery_entry(p, "skills", "~/.agents/skills"),
            ]

        entries = get_session().mutate("discovery bridge-clihub", _apply)
        _emit({"entries": entries}, "Registered ~/.cli-hub/matrix and ~/.agents/skills in skills.json")
    except Exception as exc:
        _handle_error(exc)


@discovery.command("list")
def discovery_list() -> None:
    """Display `skills.json` and `plugins.json` discovery entries."""
    try:
        disc = get_session().require_project()["discovery"]
        _emit(disc)
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# sdk group
# ---------------------------------------------------------------------------
@cli.group()
def sdk() -> None:
    """Configure and emit `google-antigravity` Python SDK runner scripts."""


@sdk.command("configure")
@click.option("--profile", type=click.Choice(["local", "litert", "local-openai"]), default=None)
@click.option("--model", default=None)
@click.option(
    "--capabilities",
    type=click.Choice(["read_only", "nondestructive", "default", "file_tools", "minimal", "none"]),
    default=None,
)
@click.option(
    "--policy",
    type=click.Choice(["confirm_run_command", "safe_defaults", "workspace_only", "deny_all", "allow_all"]),
    default=None,
)
@click.option("--skills-path", "skills_paths", multiple=True)
def sdk_configure(
    profile: str | None,
    model: str | None,
    capabilities: str | None,
    policy: str | None,
    skills_paths: tuple[str, ...],
) -> None:
    """Configure the Python SDK profile for code generation."""
    try:
        cfg = get_session().mutate(
            "sdk configure",
            lambda p: proj_mod.configure_sdk(
                p,
                profile=profile,
                model=model,
                capabilities=capabilities,
                policy=policy,
                skills_paths=list(skills_paths) if skills_paths else None,
            ),
        )
        _emit({"sdk_config": cfg}, f"Updated SDK config: profile={cfg['profile']}, model={cfg['model']}, policy={cfg['policy']}")
    except Exception as exc:
        _handle_error(exc)


@sdk.command("export-python")
@click.option("-o", "--output", "out_path", required=True, help="Destination .py runner script path.")
def sdk_export_python(out_path: str) -> None:
    """Generate a syntactically validated `google-antigravity` Python SDK runner script."""
    try:
        proj = get_session().require_project()
        code = export_mod.render_sdk_python(proj)
        target = Path(out_path).resolve()
        if not _dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code, encoding="utf-8")
        _emit(
            {"dry_run": _dry_run, "output": str(target), "bytes": len(code.encode("utf-8"))},
            f"{'[dry-run] Would write' if _dry_run else 'Wrote'} SDK script -> {target}",
        )
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# ide group (real Antigravity IDE / agy CLI backend + read-only host inspector)
# ---------------------------------------------------------------------------
@cli.group()
def ide() -> None:
    """Invoke the real installed `antigravity-ide` / `agy` CLI and inspect host customizations."""


@ide.command("detect")
def ide_detect() -> None:
    """Detect installed Google Antigravity IDE, App, `agy` CLI, and Python SDK on this host."""
    try:
        info = backend.detect_host_surfaces()
        human = (
            f"Antigravity IDE: {info['antigravity_ide'] or '(not found)'}\n"
            f"Antigravity App: {info['antigravity_app'] or '(not found)'}\n"
            f"agy CLI:         {info['agy_cli'] or '(not found)'}\n"
            f"Python SDK:      {'installed' if info['python_sdk_installed'] else 'not installed'}"
        )
        _emit(info, human)
    except Exception as exc:
        _handle_error(exc)


@ide.command("version")
def ide_version() -> None:
    """Query the live installed `antigravity-ide --version`."""
    try:
        info = backend.get_ide_version()
        _emit(info, f"Antigravity IDE {info['version']} ({info['arch']}) — {info['binary']}")
    except Exception as exc:
        _handle_error(exc)


@ide.command("extensions")
@click.option("--show-versions/--no-versions", default=True, show_default=True)
@click.option("--category", default=None)
def ide_extensions(show_versions: bool, category: str | None) -> None:
    """List installed Antigravity IDE extensions via real `antigravity-ide --list-extensions`."""
    try:
        res = backend.list_ide_extensions(show_versions=show_versions, category=category)
        lines = [f"Antigravity IDE extensions ({res['count']}):"]
        for ext in res["extensions"]:
            ver = f"@{ext['version']}" if ext["version"] else ""
            lines.append(f"  {ext['id']}{ver}")
        _emit(res, "\n".join(lines))
    except Exception as exc:
        _handle_error(exc)


@ide.command("inspect-host")
@click.option("--global-root", default=None, help="Override ~/.gemini/config root for inspection.")
@click.option("--workspace", "workspace_root", default=None, help="Optional workspace root to inspect .agents/.")
def ide_inspect_host(global_root: str | None, workspace_root: str | None) -> None:
    """Read-only inventory of installed Antigravity plugins, skills, rules, and agents."""
    try:
        res = backend.inspect_host_customizations(global_root=global_root, workspace_root=workspace_root)
        human = (
            f"Global root: {res['global_root']}\n"
            f"Plugins: {len(res['plugins'])}, Skills: {len(res['skills'])}, "
            f"Rules: {len(res['rules'])}, Agents: {len(res['agents'])}"
        )
        _emit(res, human)
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# session group
# ---------------------------------------------------------------------------
@cli.group()
def session() -> None:
    """Inspect session state and navigate undo/redo history."""


@session.command("status")
def session_status() -> None:
    """Show active project, modified flag, and undo/redo depths."""
    try:
        st = get_session().status()
        _emit(
            st,
            f"Project: {st['project_name'] or '(none)'} | modified={st['modified']} | undo={st['undo_depth']} redo={st['redo_depth']}",
        )
    except Exception as exc:
        _handle_error(exc)


@session.command("undo")
def session_undo() -> None:
    """Undo the most recent mutation."""
    try:
        desc = get_session().undo()
        _emit({"undone": desc, "status": get_session().status()}, f"Undid: {desc}")
    except Exception as exc:
        _handle_error(exc)


@session.command("redo")
def session_redo() -> None:
    """Redo the most recently undone mutation."""
    try:
        desc = get_session().redo()
        _emit({"redone": desc, "status": get_session().status()}, f"Redid: {desc}")
    except Exception as exc:
        _handle_error(exc)


@session.command("history")
def session_history() -> None:
    """List session mutation history."""
    try:
        hist = get_session().history()
        lines = [f"  {i + 1}. [{item['timestamp']}] {item['action']}" for i, item in enumerate(hist)]
        _emit({"history": hist}, "\n".join(lines) or "(no history)")
    except Exception as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# Interactive REPL (default when invoked with no subcommand)
# ---------------------------------------------------------------------------
REPL_COMMANDS = {
    "project <new|open|save|info|profiles|validate|import-dir|export>": "Manage .agyproj.json manifests",
    "plugin <set-meta|add-prompt|show|validate-dir>": "Configure & validate v1 Antigravity plugins",
    "skill <add|remove|list>": "Manage slash-command SKILL.md entries",
    "rule <add|remove|list>": "Manage scoped rules/*.md entries",
    "agent <add|remove|list>": "Manage custom agents/*.md definitions",
    "hook <add-command|set-enabled|remove|list>": "Manage hooks.json lifecycle hooks",
    "mcp <add-stdio|add-http|remove|list>": "Manage mcp_config.json servers (redacted)",
    "discovery <add-skills|add-plugins|bridge-clihub|list>": "Manage skills.json & plugins.json discovery",
    "sdk <configure|export-python>": "Generate google-antigravity Python SDK runners",
    "ide <detect|version|extensions|inspect-host>": "Query live antigravity-ide CLI & host customizations",
    "session <status|undo|redo|history>": "Navigate undo/redo session state",
    "help": "Show available commands",
    "exit / quit": "Leave interactive REPL",
}


@cli.command("repl", hidden=True)
@click.option("--project", "project_path", default=None)
def repl(project_path: str | None) -> None:
    """Run the interactive Google Antigravity CLI REPL with ReplSkin."""
    global _repl_mode, _repl_use_json, _repl_dry_run
    _repl_mode = True
    _repl_use_json = _use_json
    _repl_dry_run = _dry_run
    skin = ReplSkin("antigravity", version="1.0.0")
    skin.print_banner()

    sess = get_session()
    if project_path and not sess.has_project():
        try:
            sess.set_project(proj_mod.open_project(project_path), project_path)
            skin.success(f"Loaded project: {project_path}")
        except Exception as exc:
            skin.error(str(exc))

    pt_session = None
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            pt_session = skin.create_prompt_session()
        except Exception:
            pt_session = None

    while True:
        try:
            proj_name = sess.project.get("name", "") if sess.has_project() and sess.project else ""
            raw = skin.get_input(pt_session, project_name=proj_name, modified=sess._modified)
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        line = raw.strip()
        if not line:
            continue
        if line.lower() in {"exit", "quit", "q"}:
            skin.print_goodbye()
            break
        if line.lower() in {"help", "?"}:
            skin.help(REPL_COMMANDS)
            continue

        try:
            tokens = shlex.split(line, posix=(sys.platform != "win32"))
            cleaned_tokens: list[str] = []
            for tok in tokens:
                if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in {'"', "'"}:
                    cleaned_tokens.append(tok[1:-1])
                elif "=" in tok:
                    k, v = tok.split("=", 1)
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
                        cleaned_tokens.append(f"{k}={v[1:-1]}")
                    else:
                        cleaned_tokens.append(tok)
                else:
                    cleaned_tokens.append(tok)
            cli.main(args=cleaned_tokens, standalone_mode=False, windows_expand_args=False)
        except SystemExit:
            continue
        except click.ClickException as exc:
            skin.error(exc.format_message())
        except Exception as exc:
            skin.error(str(exc))

    _repl_mode = False


def main() -> None:
    """Console script entry point."""
    _configure_utf8_stdio()
    cli(windows_expand_args=False)


if __name__ == "__main__":
    main()
