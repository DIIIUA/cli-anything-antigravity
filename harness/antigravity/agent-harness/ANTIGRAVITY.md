# Google Antigravity CLI Harness — Architecture & SOP (`cli-anything-antigravity`)

## 1. Upstream Analysis Summary (Phase 1)

- **Target repository:** `https://github.com/google-antigravity/antigravity-sdk-python` (`google-antigravity` v0.1.24, Apache-2.0) + official Google Antigravity customization & CLI surfaces.
- **Public Surfaces & Real Local Backends:**
  - **Antigravity IDE CLI (`antigravity-ide` / `antigravity-ide.cmd`):** Official VS Code-derived desktop CLI (`--version`, `--list-extensions --show-versions`, `--install-extension`, `--uninstall-extension`, `--diff`, `--merge`, `--goto`, `--add`, `--remove`, `--profile`).
  - **Antigravity CLI (`agy`):** Official terminal agent CLI (`--version`, `agy plugin list|validate --strict|install`, `agy mcp list`, `agy models`, `agy agents`, `agy -p --output-format json`).
  - **Antigravity App (`Antigravity.exe` / desktop installation) & Python SDK (`google-antigravity` + `localharness`):** Declarative configs (`LocalAgentConfig`, `LiteRTAgentConfig`, `LocalOpenAIAgentConfig`, `CapabilitiesConfig`, `Policy`, `InlineSkill`, `McpStdioServer`, `McpStreamableHttpServer`).
- **Official Public Customization Formats (strictly excluding private `config.json` and undocumented services):**
  - `plugin.json` (`https://antigravity.google/schemas/v1/plugin.json`)
  - `skills/<name>/SKILL.md` (YAML frontmatter `name`, `description`, Markdown body)
  - `rules/*.md` (YAML frontmatter `trigger: always_on|glob|model_decision|manual`, comma-separated `globs`, 24 KB per-file cap)
  - `agents/*.md` (YAML frontmatter `name`, `description`, `model`, `mainAgent`, `subagent`, `commandExecutionPolicy`, `skills`)
  - `hooks.json` (`SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`)
  - `mcp_config.json` (`mcpServers` with stdio `command`/`args`/`env` or HTTP `serverUrl`/`headers`/`authProviderType`)
  - `skills.json` / `plugins.json` (`entries` + `inherits` for zero-copy discovery such as `~/.cli-hub/matrix` and `~/.agents/skills`)

## 2. Stateful Project Model (`*.agyproj.json`)

Managed by `core/project.py` and `core/session.py` with atomic `Session.mutate()`, snapshot-based `undo`/`redo`, `_locked_save_json()`, one-shot auto-save, and `--dry-run`:

```json
{
  "schema_version": 1,
  "name": "my-antigravity-plugin",
  "scope": "plugin",
  "plugin": {
    "$schema": "https://antigravity.google/schemas/v1/plugin.json",
    "name": "my-antigravity-plugin",
    "displayName": "My Antigravity Plugin",
    "version": "1.0.0",
    "description": "Custom Antigravity plugin bundle",
    "license": "Apache-2.0",
    "keywords": ["antigravity"],
    "suggestedPrompts": []
  },
  "skills": [],
  "rules": [],
  "agents": [],
  "hooks": {},
  "mcp_servers": {},
  "discovery": {
    "skills_entries": [],
    "plugins_entries": []
  },
  "sdk_config": {
    "profile": "local",
    "model": "gemini-4-hydrogen",
    "capabilities": "read_only",
    "policy": "confirm_run_command",
    "skills_paths": []
  }
}
```

## 3. Command Groups (`cli-anything-antigravity`)

Global options: `--json`, `--project <manifest>`, `--dry-run`. Running with no subcommand starts the interactive REPL (`ReplSkin`).

| Group | Commands | Role |
|---|---|---|
| `project` | `new`, `open`, `save`, `info`, `validate`, `import-dir`, `export` | Manage `.agyproj.json`, ingest existing plugins/workspaces, validate schemas, and materialize Antigravity bundles |
| `plugin` | `set-meta`, `add-prompt`, `show`, `validate-dir` | Configure `plugin.json` metadata and validate any existing plugin directory on disk against v1 schema |
| `skill` | `add`, `remove`, `list` | Author and manage `skills/<name>/SKILL.md` entries (undoable) |
| `rule` | `add`, `remove`, `list` | Author and manage `rules/<name>.md` with trigger/glob/24KB validation (undoable) |
| `agent` | `add`, `remove`, `list` | Author and manage `agents/<name>.md` subagent/main-agent definitions (undoable) |
| `hook` | `add-command`, `set-enabled`, `remove`, `list` | Configure `hooks.json` lifecycle groups and tool matchers (undoable) |
| `mcp` | `add-stdio`, `add-http`, `remove`, `list` | Manage `mcp_config.json` servers with regex name validation and automatic secret redaction |
| `discovery` | `add-skills`, `add-plugins`, `bridge-clihub`, `list` | Configure `skills.json` / `plugins.json` zero-copy paths (including 1-command `~/.cli-hub/matrix` + `~/.agents/skills` bridge) |
| `sdk` | `configure`, `export-python` | Configure and emit valid `google-antigravity` Python SDK runner scripts (`LocalAgentConfig`/`LiteRTAgentConfig`/`LocalOpenAIAgentConfig`) |
| `ide` | `detect`, `version`, `extensions`, `inspect-host` | Invoke real installed `antigravity-ide` (and `agy` when present) plus read-only host customization inventory (never touches `config.json`) |
| `session` | `status`, `undo`, `redo`, `history` | Inspect session state and undo/redo history |

## 4. Safety & Boundary Guarantees

- Never reads or modifies `~/.gemini/config/config.json`.
- Never probes undocumented local RPC endpoints or bypasses permissions.
- Automatically redacts token/key/secret headers and environment values when displaying `mcp_config.json`.
- Passes `stdin=subprocess.DEVNULL` to all real `antigravity-ide` / `agy` subprocess invocations and disables Click Windows wildcard expansion (`windows_expand_args=False`) so glob rules like `**/agent-harness/**` stay intact.
