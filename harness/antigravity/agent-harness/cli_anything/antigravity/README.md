# cli-anything-antigravity

Stateful CLI-Anything harness for **Google Antigravity** (built via the native CLI-Anything Antigravity plugin itself) that lets AI agents and developers author, validate, import, and export Antigravity v1 plugins, skills, glob rules, custom subagents, lifecycle hooks, MCP configs, zero-copy `skills.json` bridges, and `google-antigravity` Python SDK runners, while wrapping the live installed `antigravity-ide` / `agy` CLI binaries.

## Prerequisites

- **Python >= 3.10**
- **Google Antigravity IDE / App / CLI** (optional for offline plugin/SDK authoring; required for live `ide version` and `ide extensions` commands): https://antigravity.google/

## Installation

```bash
cd agent-harness
pip install -e .
```

Verify installation:

```bash
cli-anything-antigravity --help
cli-anything-antigravity --json ide detect
```

## Quick Start

```bash
# 1. Inspect local Google Antigravity installation and live IDE extensions
cli-anything-antigravity --json ide detect
cli-anything-antigravity --json ide version
cli-anything-antigravity --json ide extensions
cli-anything-antigravity --json ide inspect-host

# 2. Validate any existing Antigravity plugin directory against v1 schema
cli-anything-antigravity --json plugin validate-dir ~/.gemini/config/plugins/cli-anything

# 3. Create a stateful Antigravity customization project (.agyproj.json)
cli-anything-antigravity --json project new -o my-plugin.agyproj.json --name my-tools --scope plugin
cli-anything-antigravity --project my-plugin.agyproj.json skill add review --description "Run structured code review"
cli-anything-antigravity --project my-plugin.agyproj.json rule add py-guard --trigger glob --globs "**/*.py" --body "Use type annotations."
cli-anything-antigravity --project my-plugin.agyproj.json agent add auditor --description "Read-only code auditor" --policy sandbox
cli-anything-antigravity --project my-plugin.agyproj.json discovery bridge-clihub

# 4. Validate and materialize into a ready-to-install plugin directory
cli-anything-antigravity --json --project my-plugin.agyproj.json project validate
cli-anything-antigravity --json --project my-plugin.agyproj.json project export -o ./dist/my-tools --overwrite

# 5. Generate a verified google-antigravity Python SDK runner
cli-anything-antigravity --json --project my-plugin.agyproj.json sdk export-python -o ./dist/run_agent.py
```

## Safety Guarantees

- Never reads or modifies `~/.gemini/config/config.json`.
- Never probes undocumented local services.
- Automatically redacts tokens/keys/secrets when displaying MCP server configurations.
