"""Stateful Google Antigravity customization & SDK project manifest model."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

PLUGIN_SCHEMA_URL = "https://antigravity.google/schemas/v1/plugin.json"
ALLOWED_PLUGIN_FIELDS: frozenset[str] = frozenset(
    {
        "$schema",
        "name",
        "displayName",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "logo",
        "suggestedPrompts",
        "disabled",
        "license",
        "keywords",
        "skills",
        "extensions",
        "category",
    }
)
VALID_SCOPES: frozenset[str] = frozenset({"plugin", "workspace", "global"})
VALID_RULE_TRIGGERS: frozenset[str] = frozenset({"always_on", "model_decision", "glob", "manual"})
VALID_AGENT_POLICIES: frozenset[str] = frozenset({"sandbox", "off", "auto", "eager"})
VALID_HOOK_EVENTS: frozenset[str] = frozenset(
    {"SessionStart", "PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}
)
GROUPED_HOOK_EVENTS: frozenset[str] = frozenset({"PreToolUse", "PostToolUse"})
VALID_SDK_PROFILES: frozenset[str] = frozenset({"local", "litert", "local-openai"})
VALID_SDK_CAPABILITIES: frozenset[str] = frozenset(
    {"read_only", "nondestructive", "default", "file_tools", "minimal", "none"}
)
VALID_SDK_POLICIES: frozenset[str] = frozenset(
    {"confirm_run_command", "safe_defaults", "workspace_only", "deny_all", "allow_all"}
)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
MCP_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
RULE_MAX_BYTES = 24_000


def parse_yaml_frontmatter(markdown_text: str) -> tuple[dict[str, Any], str]:
    """Parse simple YAML frontmatter (`--- ... ---`) without external YAML libraries."""
    normalized = markdown_text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    end_idx = normalized.find("\n---", 4)
    if end_idx == -1:
        return {}, normalized
    header_lines = normalized[4:end_idx].splitlines()
    body = normalized[end_idx + 4 :].lstrip("\n")
    meta: dict[str, Any] = {}
    idx = 0
    while idx < len(header_lines):
        line = header_lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            idx += 1
            continue
        if ":" not in line:
            idx += 1
            continue
        key, raw_val = line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()
        if val in {">-", "|", ">", "|-"}:
            folded: list[str] = []
            idx += 1
            while idx < len(header_lines) and (header_lines[idx].startswith("  ") or not header_lines[idx].strip()):
                folded.append(header_lines[idx].strip())
                idx += 1
            meta[key] = " ".join(part for part in folded if part).strip()
            continue
        if not val:
            # Check for YAML list items on following lines
            items: list[str] = []
            idx += 1
            while idx < len(header_lines) and header_lines[idx].lstrip().startswith("- "):
                items.append(header_lines[idx].lstrip()[2:].strip().strip('"').strip("'"))
                idx += 1
            meta[key] = items if items else ""
            continue
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()] if inner else []
        elif val.lower() in {"true", "false"}:
            meta[key] = val.lower() == "true"
        else:
            meta[key] = val.strip('"').strip("'")
        idx += 1
    return meta, body


def create_project(
    name: str = "my-antigravity-plugin",
    *,
    scope: str = "plugin",
    display_name: str | None = None,
    description: str = "Google Antigravity customization bundle",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """Create a new in-memory Google Antigravity customization project manifest."""
    slug = name.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid project/plugin slug '{name}'. Use lowercase letters, digits, '-' or '_'.")
    scope_norm = scope.strip().lower()
    if scope_norm not in VALID_SCOPES:
        raise ValueError(f"Invalid scope '{scope}'. Choose from: {sorted(VALID_SCOPES)}")
    if not SEMVER_RE.match(version):
        raise ValueError(f"Invalid semver version '{version}'. Expected e.g. '1.0.0'.")

    disp = display_name or slug.replace("-", " ").replace("_", " ").title()
    return {
        "schema_version": 1,
        "name": slug,
        "scope": scope_norm,
        "plugin": {
            "$schema": PLUGIN_SCHEMA_URL,
            "name": slug,
            "displayName": disp,
            "version": version,
            "description": description,
            "license": "Apache-2.0",
            "keywords": ["antigravity"],
            "suggestedPrompts": [],
        },
        "skills": [],
        "rules": [],
        "agents": [],
        "hooks": {},
        "mcp_servers": {},
        "discovery": {
            "skills_entries": [],
            "plugins_entries": [],
        },
        "sdk_config": {
            "profile": "local",
            "model": "gemini-4-hydrogen",
            "capabilities": "read_only",
            "policy": "confirm_run_command",
            "skills_paths": [],
        },
    }


def open_project(path: str) -> dict[str, Any]:
    """Load a `.agyproj.json` project manifest from disk."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Project manifest not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or "plugin" not in data or "skills" not in data:
        raise ValueError(f"Invalid Antigravity project manifest: {path}")
    return data


def list_profiles() -> list[dict[str, str]]:
    """Return built-in Antigravity customization & SDK starter profiles."""
    return [
        {
            "name": "plugin-minimal",
            "scope": "plugin",
            "description": "Minimal Antigravity v1 plugin with one slash-command skill and glob-scoped rule",
        },
        {
            "name": "workspace-team",
            "scope": "workspace",
            "description": "Repository .agents/ configuration with skills.json sharing and sandboxed subagent",
        },
        {
            "name": "sdk-local-agent",
            "scope": "plugin",
            "description": "Plugin plus LocalAgentConfig Python SDK runner with confirm_run_command policy",
        },
        {
            "name": "sdk-litert-edge",
            "scope": "plugin",
            "description": "Lightweight LiteRTAgentConfig SDK runner for local on-device models",
        },
    ]


def set_plugin_meta(
    project: dict[str, Any],
    *,
    display_name: str | None = None,
    version: str | None = None,
    description: str | None = None,
    license_id: str | None = None,
    homepage: str | None = None,
    repository: str | None = None,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Update official v1 `plugin.json` metadata fields."""
    meta = project["plugin"]
    if version is not None:
        if not SEMVER_RE.match(version):
            raise ValueError(f"Invalid semver version '{version}'.")
        meta["version"] = version
    if display_name is not None:
        meta["displayName"] = display_name
    if description is not None:
        meta["description"] = description
    if license_id is not None:
        meta["license"] = license_id
    if homepage is not None:
        meta["homepage"] = homepage
    if repository is not None:
        meta["repository"] = repository
    if keywords is not None:
        meta["keywords"] = list(keywords)
    return copy.deepcopy(meta)


def add_suggested_prompt(project: dict[str, Any], prompt: str) -> list[str]:
    """Append a suggested prompt to `plugin.json`."""
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("Suggested prompt cannot be empty.")
    prompts = project["plugin"].setdefault("suggestedPrompts", [])
    if cleaned not in prompts:
        prompts.append(cleaned)
    return list(prompts)


def add_skill(
    project: dict[str, Any],
    name: str,
    description: str,
    body: str,
    *,
    allowed_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Add or update a `skills/<name>/SKILL.md` entry in the manifest."""
    slug = name.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid skill name '{name}'. Must match folder slug `{SLUG_RE.pattern}`.")
    if not description.strip():
        raise ValueError("Skill description cannot be empty.")
    entry: dict[str, Any] = {
        "name": slug,
        "description": description.strip(),
        "body": body.strip() or f"# `/{slug}`\n\nInstructions for `{slug}`.",
    }
    if allowed_tools:
        entry["allowed_tools"] = list(allowed_tools)

    for idx, existing in enumerate(project["skills"]):
        if existing["name"] == slug:
            project["skills"][idx] = entry
            return copy.deepcopy(entry)
    project["skills"].append(entry)
    return copy.deepcopy(entry)


def remove_skill(project: dict[str, Any], name: str) -> dict[str, Any]:
    """Remove a skill by name."""
    for idx, item in enumerate(project["skills"]):
        if item["name"] == name:
            return project["skills"].pop(idx)
    raise KeyError(f"Skill not found: {name}")


def add_rule(
    project: dict[str, Any],
    name: str,
    trigger: str,
    body: str,
    *,
    globs: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Add or update a `rules/<name>.md` entry with trigger/glob/24KB validation."""
    slug = name.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid rule name '{name}'.")
    trig = trigger.strip().lower()
    if trig not in VALID_RULE_TRIGGERS:
        raise ValueError(f"Invalid trigger '{trigger}'. Choose from: {sorted(VALID_RULE_TRIGGERS)}")
    if trig == "glob" and not (globs and globs.strip()):
        raise ValueError("Rules with `trigger: glob` require a non-empty comma-separated `--globs` string.")
    if trig == "model_decision" and not (description and description.strip()):
        raise ValueError("Rules with `trigger: model_decision` require `--description`.")
    if len(body.encode("utf-8")) > RULE_MAX_BYTES:
        raise ValueError(f"Rule body exceeds Antigravity's {RULE_MAX_BYTES}-byte per-file limit.")

    entry: dict[str, Any] = {
        "name": slug,
        "trigger": trig,
        "body": body.strip(),
    }
    if globs:
        entry["globs"] = globs.strip()
    if description:
        entry["description"] = description.strip()

    for idx, existing in enumerate(project["rules"]):
        if existing["name"] == slug:
            project["rules"][idx] = entry
            return copy.deepcopy(entry)
    project["rules"].append(entry)
    return copy.deepcopy(entry)


def remove_rule(project: dict[str, Any], name: str) -> dict[str, Any]:
    """Remove a rule by name."""
    for idx, item in enumerate(project["rules"]):
        if item["name"] == name:
            return project["rules"].pop(idx)
    raise KeyError(f"Rule not found: {name}")


def add_agent(
    project: dict[str, Any],
    name: str,
    description: str,
    body: str,
    *,
    model: str = "inherit",
    main_agent: bool = True,
    subagent: bool = True,
    command_execution_policy: str = "sandbox",
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """Add or update an `agents/<name>.md` custom agent definition."""
    slug = name.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid agent name '{name}'.")
    if not description.strip():
        raise ValueError("Agent description cannot be empty.")
    if command_execution_policy not in VALID_AGENT_POLICIES:
        raise ValueError(
            f"Invalid commandExecutionPolicy '{command_execution_policy}'. Allowed: {sorted(VALID_AGENT_POLICIES)}"
        )
    entry: dict[str, Any] = {
        "name": slug,
        "description": description.strip(),
        "model": model.strip() or "inherit",
        "mainAgent": bool(main_agent),
        "subagent": bool(subagent),
        "commandExecutionPolicy": command_execution_policy,
        "skills": list(skills or []),
        "body": body.strip() or f"# {slug}\n\nSystem instructions for `{slug}`.",
    }
    for idx, existing in enumerate(project["agents"]):
        if existing["name"] == slug:
            project["agents"][idx] = entry
            return copy.deepcopy(entry)
    project["agents"].append(entry)
    return copy.deepcopy(entry)


def remove_agent(project: dict[str, Any], name: str) -> dict[str, Any]:
    """Remove an agent definition by name."""
    for idx, item in enumerate(project["agents"]):
        if item["name"] == name:
            return project["agents"].pop(idx)
    raise KeyError(f"Agent not found: {name}")


def add_command_hook(
    project: dict[str, Any],
    group_name: str,
    event: str,
    command: str,
    *,
    matcher: str = "*",
    timeout: int = 10,
    enabled: bool = True,
) -> dict[str, Any]:
    """Add a command lifecycle hook into `hooks.json` structure."""
    if not SLUG_RE.match(group_name.strip().lower()):
        raise ValueError(f"Invalid hook group name '{group_name}'.")
    if event not in VALID_HOOK_EVENTS:
        raise ValueError(f"Invalid hook event '{event}'. Choose from: {sorted(VALID_HOOK_EVENTS)}")
    if not command.strip():
        raise ValueError("Hook command cannot be empty.")
    if timeout <= 0:
        raise ValueError("Hook timeout must be a positive integer.")

    group = project["hooks"].setdefault(group_name.strip().lower(), {"enabled": bool(enabled)})
    group["enabled"] = bool(enabled)
    handler = {"type": "command", "command": command.strip(), "timeout": int(timeout)}
    if event in GROUPED_HOOK_EVENTS:
        group.setdefault(event, []).append({"matcher": matcher, "hooks": [handler]})
    else:
        group.setdefault(event, []).append(handler)
    return copy.deepcopy(group)


def set_hook_enabled(project: dict[str, Any], group_name: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable a hook group in `hooks.json`."""
    if group_name not in project["hooks"]:
        raise KeyError(f"Hook group not found: {group_name}")
    project["hooks"][group_name]["enabled"] = bool(enabled)
    return copy.deepcopy(project["hooks"][group_name])


def remove_hook_group(project: dict[str, Any], group_name: str) -> dict[str, Any]:
    """Remove a hook group by name."""
    if group_name not in project["hooks"]:
        raise KeyError(f"Hook group not found: {group_name}")
    return project["hooks"].pop(group_name)


def add_mcp_stdio(
    project: dict[str, Any],
    name: str,
    command: str,
    *,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Add a stdio MCP server definition to `mcp_config.json`."""
    if not MCP_NAME_RE.match(name):
        raise ValueError(f"Invalid MCP server name '{name}'. Must match `{MCP_NAME_RE.pattern}`.")
    if not command.strip():
        raise ValueError("MCP stdio command cannot be empty.")
    cfg: dict[str, Any] = {"command": command.strip(), "args": list(args or [])}
    if env:
        cfg["env"] = dict(env)
    project["mcp_servers"][name] = cfg
    return copy.deepcopy(cfg)


def add_mcp_http(
    project: dict[str, Any],
    name: str,
    server_url: str,
    *,
    headers: dict[str, str] | None = None,
    auth_provider_type: str | None = None,
) -> dict[str, Any]:
    """Add a remote streamable HTTP MCP server definition to `mcp_config.json`."""
    if not MCP_NAME_RE.match(name):
        raise ValueError(f"Invalid MCP server name '{name}'. Must match `{MCP_NAME_RE.pattern}`.")
    if not server_url.startswith(("http://", "https://")):
        raise ValueError(f"MCP serverUrl must start with http:// or https:// (got: {server_url})")
    cfg: dict[str, Any] = {"serverUrl": server_url.strip()}
    if headers:
        cfg["headers"] = dict(headers)
    if auth_provider_type:
        cfg["authProviderType"] = auth_provider_type.strip()
    project["mcp_servers"][name] = cfg
    return copy.deepcopy(cfg)


def remove_mcp_server(project: dict[str, Any], name: str) -> dict[str, Any]:
    """Remove an MCP server definition by name."""
    if name not in project["mcp_servers"]:
        raise KeyError(f"MCP server not found: {name}")
    return project["mcp_servers"].pop(name)


def add_discovery_entry(
    project: dict[str, Any],
    kind: str,
    path: str,
    *,
    exclude: list[str] | None = None,
) -> dict[str, Any]:
    """Add a path entry to `skills.json` or `plugins.json` discovery config."""
    key = "skills_entries" if kind == "skills" else "plugins_entries" if kind == "plugins" else ""
    if not key:
        raise ValueError("Discovery kind must be 'skills' or 'plugins'.")
    cleaned = path.strip()
    if not cleaned:
        raise ValueError("Discovery entry path cannot be empty.")
    entry: dict[str, Any] = {"path": cleaned}
    if exclude:
        entry["exclude"] = list(exclude)
    entries = project["discovery"][key]
    for idx, existing in enumerate(entries):
        if existing.get("path") == cleaned:
            entries[idx] = entry
            return copy.deepcopy(entry)
    entries.append(entry)
    return copy.deepcopy(entry)


def configure_sdk(
    project: dict[str, Any],
    *,
    profile: str | None = None,
    model: str | None = None,
    capabilities: str | None = None,
    policy: str | None = None,
    skills_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Configure the `google-antigravity` Python SDK profile settings."""
    sdk = project["sdk_config"]
    if profile is not None:
        if profile not in VALID_SDK_PROFILES:
            raise ValueError(f"Invalid SDK profile '{profile}'. Allowed: {sorted(VALID_SDK_PROFILES)}")
        sdk["profile"] = profile
    if model is not None:
        sdk["model"] = model.strip()
    if capabilities is not None:
        if capabilities not in VALID_SDK_CAPABILITIES:
            raise ValueError(
                f"Invalid SDK capabilities '{capabilities}'. Allowed: {sorted(VALID_SDK_CAPABILITIES)}"
            )
        sdk["capabilities"] = capabilities
    if policy is not None:
        if policy not in VALID_SDK_POLICIES:
            raise ValueError(f"Invalid SDK policy '{policy}'. Allowed: {sorted(VALID_SDK_POLICIES)}")
        sdk["policy"] = policy
    if skills_paths is not None:
        sdk["skills_paths"] = list(skills_paths)
    return copy.deepcopy(sdk)


def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    """Validate an in-memory `.agyproj.json` manifest against Google Antigravity schemas."""
    errors: list[str] = []
    warnings: list[str] = []

    meta = project.get("plugin", {})
    unknown = set(meta.keys()) - ALLOWED_PLUGIN_FIELDS
    if unknown:
        errors.append(f"Unknown plugin.json fields: {sorted(unknown)}")
    if not meta.get("name") or not SLUG_RE.match(str(meta.get("name"))):
        errors.append(f"Invalid plugin.json name: {meta.get('name')}")
    if not meta.get("version") or not SEMVER_RE.match(str(meta.get("version"))):
        errors.append(f"Invalid plugin.json version: {meta.get('version')}")
    if not meta.get("description"):
        errors.append("plugin.json description is required.")

    for sk in project.get("skills", []):
        if not SLUG_RE.match(sk.get("name", "")):
            errors.append(f"Invalid skill slug: {sk.get('name')}")
        if not sk.get("description"):
            errors.append(f"Skill '{sk.get('name')}' missing description.")

    for rule in project.get("rules", []):
        trig = rule.get("trigger")
        if trig not in VALID_RULE_TRIGGERS:
            errors.append(f"Rule '{rule.get('name')}' has invalid trigger '{trig}'.")
        if trig == "glob" and not rule.get("globs"):
            errors.append(f"Rule '{rule.get('name')}' uses trigger: glob without globs.")
        if len(rule.get("body", "").encode("utf-8")) > RULE_MAX_BYTES:
            errors.append(f"Rule '{rule.get('name')}' exceeds 24 KB Antigravity rule cap.")

    for ag in project.get("agents", []):
        if ag.get("commandExecutionPolicy") not in VALID_AGENT_POLICIES:
            errors.append(f"Agent '{ag.get('name')}' has invalid commandExecutionPolicy.")
        if ag.get("tools"):
            warnings.append(
                f"Agent '{ag.get('name')}' defines a static `tools:` allowlist (may hang on some Antigravity runtimes; prefer commandExecutionPolicy)."
            )

    for grp, cfg in project.get("hooks", {}).items():
        if not isinstance(cfg, dict):
            errors.append(f"Hook group '{grp}' must be a JSON object.")
            continue
        for ev in cfg:
            if ev == "enabled":
                continue
            if ev not in VALID_HOOK_EVENTS:
                errors.append(f"Hook group '{grp}' has unknown event '{ev}'.")

    for srv_name, srv_cfg in project.get("mcp_servers", {}).items():
        if not MCP_NAME_RE.match(srv_name):
            errors.append(f"Invalid MCP server name: {srv_name}")
        if "command" not in srv_cfg and "serverUrl" not in srv_cfg:
            errors.append(f"MCP server '{srv_name}' must specify 'command' (stdio) or 'serverUrl' (http).")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "skills": len(project.get("skills", [])),
            "rules": len(project.get("rules", [])),
            "agents": len(project.get("agents", [])),
            "hooks": len(project.get("hooks", {})),
            "mcp_servers": len(project.get("mcp_servers", {})),
        },
    }


def import_from_dir(source_dir: str) -> dict[str, Any]:
    """Ingest an existing Antigravity plugin or `.agents/` folder into a `.agyproj.json` manifest."""
    root = Path(source_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {source_dir}")

    plugin_json_path = root / "plugin.json"
    if plugin_json_path.is_file():
        raw_meta = json.loads(plugin_json_path.read_text(encoding="utf-8-sig"))
        name = raw_meta.get("name", root.name)
        proj = create_project(
            name=name,
            scope="plugin",
            display_name=raw_meta.get("displayName"),
            description=raw_meta.get("description", "Imported Antigravity plugin"),
            version=raw_meta.get("version", "1.0.0"),
        )
        proj["plugin"] = raw_meta
    else:
        slug = re.sub(r"[^a-z0-9_-]+", "-", root.name.lower()).strip("-") or "workspace"
        proj = create_project(name=slug, scope="workspace")

    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.is_file():
                fm, body = parse_yaml_frontmatter(skill_md.read_text(encoding="utf-8-sig"))
                proj["skills"].append(
                    {
                        "name": str(fm.get("name") or child.name),
                        "description": str(fm.get("description") or ""),
                        "body": body.strip(),
                    }
                )

    rules_dir = root / "rules"
    if rules_dir.is_dir():
        for md in sorted(rules_dir.glob("*.md")):
            fm, body = parse_yaml_frontmatter(md.read_text(encoding="utf-8-sig"))
            entry: dict[str, Any] = {
                "name": md.stem,
                "trigger": str(fm.get("trigger") or "always_on"),
                "body": body.strip(),
            }
            if fm.get("globs"):
                entry["globs"] = str(fm["globs"])
            if fm.get("description"):
                entry["description"] = str(fm["description"])
            proj["rules"].append(entry)

    agents_dir = root / "agents"
    if agents_dir.is_dir():
        for md in sorted(agents_dir.glob("*.md")):
            fm, body = parse_yaml_frontmatter(md.read_text(encoding="utf-8-sig"))
            ag_entry: dict[str, Any] = {
                "name": str(fm.get("name") or md.stem),
                "description": str(fm.get("description") or ""),
                "model": str(fm.get("model") or "inherit"),
                "mainAgent": bool(fm.get("mainAgent", True)),
                "subagent": bool(fm.get("subagent", False)),
                "commandExecutionPolicy": str(fm.get("commandExecutionPolicy") or "sandbox"),
                "skills": fm.get("skills") if isinstance(fm.get("skills"), list) else [],
                "body": body.strip(),
            }
            if isinstance(fm.get("tools"), list) and fm["tools"]:
                ag_entry["tools"] = fm["tools"]
            proj["agents"].append(ag_entry)

    hooks_file = root / "hooks.json"
    if hooks_file.is_file():
        proj["hooks"] = json.loads(hooks_file.read_text(encoding="utf-8-sig"))

    mcp_file = root / "mcp_config.json"
    if mcp_file.is_file():
        mcp_raw = json.loads(mcp_file.read_text(encoding="utf-8-sig"))
        if isinstance(mcp_raw, dict) and isinstance(mcp_raw.get("mcpServers"), dict):
            proj["mcp_servers"] = mcp_raw["mcpServers"]

    skills_json = root / "skills.json"
    if skills_json.is_file():
        raw = json.loads(skills_json.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
            proj["discovery"]["skills_entries"] = raw["entries"]

    plugins_json = root / "plugins.json"
    if plugins_json.is_file():
        raw = json.loads(plugins_json.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
            proj["discovery"]["plugins_entries"] = raw["entries"]

    return proj


def validate_plugin_directory(plugin_dir: str) -> dict[str, Any]:
    """Validate an Antigravity plugin directory on disk against v1 schemas."""
    root = Path(plugin_dir).resolve()
    if not (root / "plugin.json").is_file():
        return {
            "valid": False,
            "path": str(root),
            "errors": [f"Missing plugin.json in {root}"],
            "warnings": [],
        }
    proj = import_from_dir(str(root))
    report = validate_project(proj)
    # Check relative logo existence if declared
    logo = proj["plugin"].get("logo")
    if isinstance(logo, str) and logo and not logo.startswith(("http://", "https://")):
        if not (root / logo).is_file():
            report["errors"].append(f"Declared logo file does not exist: {logo}")
            report["valid"] = False
    # Check skill folder-name == frontmatter name parity
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.is_file():
                fm, _ = parse_yaml_frontmatter(skill_md.read_text(encoding="utf-8-sig"))
                if fm.get("name") != child.name:
                    report["errors"].append(
                        f"Skill folder '{child.name}' does not match frontmatter name '{fm.get('name')}'."
                    )
                    report["valid"] = False
    report["path"] = str(root)
    return report
