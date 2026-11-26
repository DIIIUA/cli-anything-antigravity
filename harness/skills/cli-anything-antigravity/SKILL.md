---
name: cli-anything-antigravity
description: >-
  Stateful CLI-Anything harness for Google Antigravity supporting v1 plugin
  authoring and validation, skills/rules/agents/hooks/MCP/skills.json
  management, google-antigravity Python SDK code generation, and real
  antigravity-ide/agy CLI execution.
---

# cli-anything-antigravity

Stateful CLI-Anything harness for **Google Antigravity** (built using the native CLI-Anything Antigravity plugin) that lets AI agents and developers author, validate, import, and export Antigravity v1 plugins, slash-command skills, glob rules, custom subagents, lifecycle hooks, MCP server definitions, zero-copy `skills.json` bridges, and `google-antigravity` Python SDK runners, while wrapping the live installed `antigravity-ide` / `agy` CLI binaries.

## Installation

```bash
pip install cli-anything-antigravity
```

**Prerequisites:**
- Python 3.10+
- Optional for offline plugin/SDK authoring; required for live `ide version` and `ide extensions`: Google Antigravity IDE / App / CLI (https://antigravity.google/)

## Usage

Global options (`--json`, `--project <manifest>`, `--dry-run`) are passed **before** the command group.

```bash
# Show help or enter interactive REPL
cli-anything-antigravity --help
cli-anything-antigravity

# Inspect local Google Antigravity installation and extensions
cli-anything-antigravity --json ide detect
cli-anything-antigravity --json ide version
cli-anything-antigravity --json ide extensions
cli-anything-antigravity --json ide inspect-host

# Validate an existing Antigravity plugin directory against v1 schema
cli-anything-antigravity --json plugin validate-dir ~/.gemini/config/plugins/cli-anything

# Author a stateful .agyproj.json manifest and export a ready-to-install plugin
cli-anything-antigravity --json project new -o my-plugin.agyproj.json --name my-tools --scope plugin
cli-anything-antigravity --json --project my-plugin.agyproj.json skill add review --description "Structured code review"
cli-anything-antigravity --json --project my-plugin.agyproj.json rule add py-guard --trigger glob --globs "**/*.py" --body "Use type hints."
cli-anything-antigravity --json --project my-plugin.agyproj.json agent add auditor --description "Read-only auditor" --policy sandbox
cli-anything-antigravity --json --project my-plugin.agyproj.json discovery bridge-clihub
cli-anything-antigravity --json --project my-plugin.agyproj.json project export -o ./dist/my-tools --overwrite
cli-anything-antigravity --json --project my-plugin.agyproj.json sdk export-python -o ./dist/run_agent.py
```

## Command Groups

### `project`

| Command | Description |
|---------|-------------|
| `new` | Create and save a new `.agyproj.json` manifest. |
| `open` | Load an existing `.agyproj.json` manifest into the active session. |
| `save` | Persist the active manifest via locked JSON write. |
| `info` | Display active project metadata and counts (MCP secrets redacted). |
| `profiles` | List built-in Antigravity customization & SDK starter profiles. |
| `validate` | Validate the manifest against Google Antigravity v1 schemas. |
| `import-dir` | Ingest an existing plugin or `.agents/` folder into `.agyproj.json`. |
| `export` | Materialize `plugin.json`, `skills/`, `rules/`, `agents/`, `hooks.json`, `mcp_config.json`, `skills.json`, `plugins.json`. |

### `plugin`, `skill`, `rule`, `agent`, `hook`, `mcp`, `discovery`

| Group | Commands |
|-------|----------|
| `plugin` | `set-meta`, `add-prompt`, `show`, `validate-dir` |
| `skill` | `add`, `remove`, `list` |
| `rule` | `add`, `remove`, `list` (enforces `trigger`, comma-separated `globs`, and 24 KB cap) |
| `agent` | `add`, `remove`, `list` (`subagent`, `mainAgent`, `commandExecutionPolicy`, `skills`) |
| `hook` | `add-command`, `set-enabled`, `remove`, `list` (`SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`) |
| `mcp` | `add-stdio`, `add-http`, `remove`, `list` (automatic secret redaction) |
| `discovery` | `add-skills`, `add-plugins`, `bridge-clihub`, `list` |

### `sdk`, `ide`, `session`

| Group | Commands |
|-------|----------|
| `sdk` | `configure`, `export-python` (emits AST-verified `google-antigravity` Python SDK runners) |
| `ide` | `detect`, `version`, `extensions`, `inspect-host` (live `antigravity-ide` / `agy` backend; never reads `config.json`) |
| `session` | `status`, `undo`, `redo`, `history` |

## For AI Agents

1. Pass `--json` before the command group for structured machine-readable output.
2. Check process exit codes: `0` for success, non-zero for errors.
3. In `--json` mode, structured error JSON (`{"error": "...", "type": "..."}`) is written to **stdout**; in human mode, errors go to **stderr**.
4. Pass `--dry-run` before the command group to preview mutations or exports without writing files.
5. This CLI never touches `~/.gemini/config/config.json` and automatically redacts secret values when listing MCP servers.

## Version

1.0.0
