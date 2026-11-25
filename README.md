# CLI-Anything for Google Antigravity (Community Edition)

Standalone **Community Edition** native plugin adapter that brings the complete
[**HKUDS/CLI-Anything**](https://github.com/HKUDS/CLI-Anything) 7-phase CLI
harness generator to **Google Antigravity** — 1-to-1 with the official
`cli-anything-plugin` methodology, synced with upstream, and ready for upstream
adoption via PR.

> **Upstream parity:** Canonical methodology (`references/HARNESS.md`, all 5
> command specs, all 8 guides, `docs/PREVIEW_PROTOCOL.md`) and helper scripts
> (`repl_skin.py`, `preview_bundle.py`, `skill_generator.py`,
> `templates/SKILL.md.template`) are synced verbatim from
> [`HKUDS/CLI-Anything`](https://github.com/HKUDS/CLI-Anything). See
> [`UPSTREAM_SYNC.json`](UPSTREAM_SYNC.json) for the exact pinned upstream
> commit.

## Two Tracks (Same Architecture as Upstream)

| Track | What you get | How |
|---|---|---|
| **Generator** (this plugin) | Build, refine, test, validate, and list harnesses via the `cli-anything` skill | Install this plugin |
| **Consumer** (unchanged) | Find, install, and invoke published CLIs from CLI-Hub | `npx skills` + `cli-hub` |

## Quick Install

### macOS / Linux / Git Bash

```bash
git clone https://github.com/DIIIUA/cli-anything-antigravity.git
bash cli-anything-antigravity/scripts/install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/DIIIUA/cli-anything-antigravity.git
.\cli-anything-antigravity\scripts\install.ps1
```

Default global install path: `~/.gemini/config/plugins/cli-anything`
(override with `ANTIGRAVITY_PLUGINS_HOME` pointing at a directory named
`plugins`).

### Workspace-Scoped Install

Install into a single project repository (`<workspace>/.agents/plugins/cli-anything`)
without modifying your global `~/.gemini/config/plugins/` or global discovery
pointer:

```bash
bash cli-anything-antigravity/scripts/install.sh --workspace /path/to/your/repo
# PowerShell:
#   .\cli-anything-antigravity\scripts\install.ps1 -Workspace C:\path\to\your\repo
```

### Upgrade & Uninstall

```bash
# Upgrade
bash cli-anything-antigravity/scripts/install.sh --force
# PowerShell: .\cli-anything-antigravity\scripts\install.ps1 -Force

# Uninstall (global or --workspace)
bash cli-anything-antigravity/scripts/uninstall.sh
# PowerShell: .\cli-anything-antigravity\scripts\uninstall.ps1
```

## Usage in Google Antigravity

Google Antigravity auto-discovers newly installed plugins automatically (the
`cli-anything` skill becomes available on your next turn without a full
restart). Describe what you want in natural language:

```text
Use CLI-Anything to build a harness for ./gimp
Use CLI-Anything to refine ./shotcut for picture-in-picture workflows
Use CLI-Anything to test ./libreoffice
Use CLI-Anything to validate ./libreoffice
Use CLI-Anything to list generated harnesses in this workspace
```

For the **Consumer** track (discovering and installing published CLIs from
CLI-Hub):

```bash
npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y
pip install cli-anything-hub
```

## Why Native Antigravity Adaptation (Not a Copy)

- **Strict Antigravity `plugin.json` schema:** only valid Antigravity manifest
  fields (`name`, `displayName`, `version`, `description`, `author`, `homepage`,
  `repository`, `logo`, `suggestedPrompts`).
- **Zero idle context overhead:** intentionally ships **no** `rules/AGENTS.md`
  (plugin rules in Antigravity are always-on). All instructions load
  progressively via `skills/cli-anything/SKILL.md` only when invoked.
- **Native tool bindings:** maps every phase to `read_file`, `write_file`,
  `edit_file`, `run_command`, `invoke_subagent`, `update_steps`, and
  `update_focus`.
- **Hard phase gates & resume:** persists progress in
  `{software-root}/agent-harness/.cli-anything-progress.json`.
- **Cross-platform execution guidance:** first-class Windows PowerShell (`pwsh`)
  and POSIX instructions while keeping vendored upstream methodology intact.

## Syncing with Upstream `HKUDS/CLI-Anything`

Run the sync script anytime to refresh canonical methodology and scripts from
`HKUDS/CLI-Anything`:

```bash
bash scripts/sync-upstream.sh
# PowerShell: .\scripts\sync-upstream.ps1
```

A scheduled GitHub Actions workflow (`.github/workflows/sync-upstream.yml`)
also checks upstream weekly and can be triggered manually via
**workflow_dispatch**.

## Tests

```bash
# macOS / Linux / Git Bash
bash tests/test_install.sh

# Windows PowerShell
.\tests\test_install.ps1
```

## Upstream Contribution

An upstream-ready PR branch (`feat/antigravity-plugin`) with zero duplicated
canonical files is maintained alongside this repository at
[`DIIIUA/CLI-Anything`](https://github.com/DIIIUA/CLI-Anything/tree/feat/antigravity-plugin)
for direct upstream integration into `HKUDS/CLI-Anything`.

## License

Apache License 2.0 — same as [`HKUDS/CLI-Anything`](https://github.com/HKUDS/CLI-Anything). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
