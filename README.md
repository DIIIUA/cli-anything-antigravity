# CLI-Anything for Google Antigravity (Community Edition)

Standalone **Community Edition** native plugin adapter that brings the complete
[**HKUDS/CLI-Anything**](https://github.com/HKUDS/CLI-Anything) 7-phase CLI
harness generator to **Google Antigravity** (App, CLI `agy`, and IDE) — synced
verbatim with upstream and ready for upstream adoption via PR.

> **Upstream parity:** Canonical methodology (`references/HARNESS.md`, all 5
> command specs, all 8 guides, `references/docs/PREVIEW_PROTOCOL.md`) and
> reusable Python utilities (`repl_skin.py`, `preview_bundle.py`,
> `skill_generator.py`, `templates/SKILL.md.template`) are synced unmodified
> from [`HKUDS/CLI-Anything`](https://github.com/HKUDS/CLI-Anything). See
> [`UPSTREAM_SYNC.json`](UPSTREAM_SYNC.json) for the pinned upstream commit.

## Two Tracks (Same Architecture as Upstream)

| Track | What you get | How |
|---|---|---|
| **Generator** (this plugin) | 5 slash commands (`/cli-anything*`), glob-scoped guardrails, read-only `cli-anything-auditor` subagent, opt-in PEP 420 hook, `verify_harness.py`, and `list_harnesses.py` | Install this plugin |
| **Consumer** (unchanged) | Find, install, and invoke published CLIs & matrices from CLI-Hub | `npx skills` + `cli-hub` |

## Quick Install

### Option 1: Official Antigravity CLI (`agy`) — One Command

```bash
agy plugin install https://github.com/DIIIUA/cli-anything-antigravity
agy plugin validate --strict ~/.gemini/config/plugins/cli-anything
```

### Option 2: Bundled Installers (macOS / Linux / Git Bash / Windows PowerShell)

```bash
git clone https://github.com/DIIIUA/cli-anything-antigravity.git
bash cli-anything-antigravity/scripts/install.sh
```

Windows PowerShell:

```powershell
git clone https://github.com/DIIIUA/cli-anything-antigravity.git
.\cli-anything-antigravity\scripts\install.ps1
```

Options:
- `--force` / `-Force`: locked, pre-verified atomic upgrade with rollback.
- `--dry-run` / `-DryRun`: preview install targets without writing files.
- `--workspace <repo>` / `-Workspace <repo>`: project-scoped install to `<repo>/.agents/plugins/cli-anything` (leaves global discovery pointer untouched).
- `ANTIGRAVITY_PLUGINS_HOME`: override default global root `~/.gemini/config/plugins` (must point to a directory named `plugins`).

Uninstall:

```bash
bash cli-anything-antigravity/scripts/uninstall.sh          # or --workspace <repo>
# PowerShell:
.\cli-anything-antigravity\scripts\uninstall.ps1            # or -Workspace <repo>
```

## Included Antigravity-Native Components

| Component | Path | Role |
|---|---|---|
| `/cli-anything` | `skills/cli-anything/SKILL.md` | Full 7-phase harness build + Phase 6.5 `SKILL.md` + Preview Bundle Protocol |
| `/cli-anything-refine` | `skills/cli-anything-refine/SKILL.md` | Incremental gap analysis & coverage expansion (`[focus]`) |
| `/cli-anything-test` | `skills/cli-anything-test/SKILL.md` | Unit + real-backend E2E + `CLI_ANYTHING_FORCE_INSTALLED=1` + `TEST.md` |
| `/cli-anything-validate` | `skills/cli-anything-validate/SKILL.md` | Deterministic `verify_harness.py` + 52-check `validate.md` audit |
| `/cli-anything-list` | `skills/cli-anything-list/SKILL.md` | Deterministic `list_harnesses.py` (`--path`, `--depth`, `--json`) |
| **Glob Rule** | `rules/cli-anything-generator.md` | `trigger: glob` on `**/agent-harness/**, **/.cli-anything-progress.json, **/cli_anything/**` (0 tokens in unrelated chats) |
| **Auditor Subagent** | `agents/cli-anything-auditor.md` | Read-only Phase 1 codebase surveyor & independent contract auditor |
| **PEP 420 Hook** | `hooks.json` + `scripts/pep420_guard.py` | Opt-in (`"enabled": false` by default) `PreToolUse` guard blocking `cli_anything/__init__.py` |
| **Tooling Runbook** | `references/antigravity-tooling.md` | App/CLI/IDE paths, `~/.gemini/config/skills.json` bridge for `cli-hub matrix` & newly generated CLI skills, `/goal`/`/swarm` recipes, Failure Playbook |

## Dogfooded Bonus: `cli-anything-antigravity` CLI Harness

This repository also ships a full, verified CLI-Anything harness built **using this very plugin** for Google Antigravity itself (`harness/antigravity/agent-harness/`, passing `verify_harness.py --strict` **30/30**):

- Stateful `.agyproj.json` authoring with undo/redo, locked JSON saves, auto-save, and `--dry-run`.
- Author, import, validate, and export official Antigravity v1 `plugin.json`, `skills/*/SKILL.md`, `rules/*.md` (trigger/glob/24 KB checks), `agents/*.md`, `hooks.json`, `mcp_config.json` (with automatic secret redaction), and `skills.json` / `plugins.json` (including `discovery bridge-clihub`).
- Generate AST-verified `google-antigravity` Python SDK runner scripts (`LocalAgentConfig` / `LiteRTAgentConfig` / `LocalOpenAIAgentConfig`).
- Wrap the live installed `antigravity-ide` / `agy` CLI (`ide detect`, `ide version`, `ide extensions`, `ide inspect-host`) without ever touching private `config.json`.

Install the dogfooded CLI harness:

```bash
pip install -e ./harness/antigravity/agent-harness
cli-anything-antigravity --json ide detect
cli-anything-antigravity --json plugin validate-dir ~/.gemini/config/plugins/cli-anything
```

To expose its generated skill (`harness/skills/cli-anything-antigravity/SKILL.md`) inside Antigravity App, register `./harness/skills` in `.agents/skills.json` or `~/.gemini/config/skills.json`.

## Consumer Track & `cli-hub` Matrix Bridge

```bash
npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y
pip install cli-anything-hub
```

To expose `cli-hub matrix install` skills (`~/.cli-hub/matrix/`) and global
`npx skills` installs (`~/.agents/skills/`) inside **Antigravity App**
automatically, add them to `~/.gemini/config/skills.json` (details in
[`references/antigravity-tooling.md`](references/antigravity-tooling.md)).

## Syncing with Upstream `HKUDS/CLI-Anything`

```bash
bash scripts/sync-upstream.sh
# PowerShell: .\scripts\sync-upstream.ps1
```

A scheduled GitHub Actions workflow (`.github/workflows/sync-upstream.yml`)
checks upstream weekly and opens a PR automatically when canonical files change.

## Tests

```bash
bash tests/test_install.sh
# Windows PowerShell: .\tests\test_install.ps1

python3 -m pytest tests/test_verify_harness.py tests/test_install_race.py -v
```

## Upstream Contribution

An upstream-ready PR branch (`feat/antigravity-plugin`) with zero duplicated
canonical files is maintained at
[`DIIIUA/CLI-Anything`](https://github.com/DIIIUA/CLI-Anything/tree/feat/antigravity-plugin)
for direct upstream integration into `HKUDS/CLI-Anything`.

## License

Apache License 2.0 — same as [`HKUDS/CLI-Anything`](https://github.com/HKUDS/CLI-Anything). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
