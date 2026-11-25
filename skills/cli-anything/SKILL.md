---
name: cli-anything
description: >-
  Build, refine, test, validate, or list stateful CLI-Anything harnesses for
  any GUI application or source repository in Google Antigravity. Adapts the
  full 7-phase CLI-Anything generator methodology (including Phase 6.5 skill
  generation, Preview Bundle Protocol, and PEP 420 namespace packaging)
  without changing the generated Python harness format. Discovering and
  installing already-published CLIs from CLI-Hub remains a separate consumer
  skill (cli-hub-meta-skill).
---

# CLI-Anything Generator for Google Antigravity

Use this skill when the user wants Google Antigravity to act as the
`CLI-Anything` builder: creating a new stateful CLI harness, refining coverage
on an existing harness, running real-backend test suites, validating against
the full checklist, or listing installed and generated harnesses.

> **Two-track separation:** This plugin is the **Generator** track. Discovering,
> installing, and invoking already-published CLIs from CLI-Hub stays on the
> separate **Consumer** track (`cli-hub-meta-skill` + `cli-hub` + per-app
> `skills/cli-anything-*` via `npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y`).

## CRITICAL: Resolve `PLUGIN_ROOT` (Absolute Paths Only)

Never resolve `./HARNESS.md` against the user's workspace root. Before starting
any build, refine, test, or validate workflow, resolve `PLUGIN_ROOT` in this
order — stop at the first location where `{PLUGIN_ROOT}/references/HARNESS.md`
exists:

1. **Active skill path (preferred — works for both global and workspace installs):**
   Take the absolute path to this `SKILL.md` provided by Antigravity and go up
   two directories (`.../plugins/cli-anything/skills/cli-anything/SKILL.md` ->
   `.../plugins/cli-anything`).
2. **Global discovery pointer** (single-line absolute path):
   - Windows: `%USERPROFILE%\.gemini\cli-anything-generator.root`
   - macOS / Linux: `~/.gemini/cli-anything-generator.root`
3. **Install stamp or standard Antigravity plugin roots** (`{candidate}/PLUGIN_ROOT.txt` or `{candidate}` directly):
   - Workspace plugin: `{workspace}/.agents/plugins/cli-anything`
   - Custom root: `$ANTIGRAVITY_PLUGINS_HOME/cli-anything` (if set)
   - Global default: `%USERPROFILE%\.gemini\config\plugins\cli-anything` (Windows) or `~/.gemini/config/plugins/cli-anything` (macOS / Linux)
4. **Repository checkout fallback:** if the current workspace is a
   `CLI-Anything` checkout, use `{workspace}/cli-anything-plugin` (still prefer
   the installed plugin when present).
5. **Remote fallback:** clone `https://github.com/HKUDS/CLI-Anything` and use
   `cli-anything-plugin/` + `docs/PREVIEW_PROTOCOL.md`.

Only if every source above is unreachable, follow the **Condensed Fallback
Rules** at the end of this file.

## Read the Full Methodology First

1. Read `{PLUGIN_ROOT}/references/HARNESS.md` using an absolute path.
2. Read the matching mode specification under `{PLUGIN_ROOT}/references/commands/`.
3. Read on-demand guides under `{PLUGIN_ROOT}/references/guides/` and
   `{PLUGIN_ROOT}/references/docs/PREVIEW_PROTOCOL.md` only when they apply to
   the target software.

### Resource Map and Path Remapping

The installer vendors the canonical files from `cli-anything-plugin/` and
`docs/PREVIEW_PROTOCOL.md` into the installed plugin so it is completely
self-contained. When a vendored document references a relative repo path,
remap it under `{PLUGIN_ROOT}`:

| Document reference | Installed plugin path | Purpose |
|---|---|---|
| `./HARNESS.md` | `{PLUGIN_ROOT}/references/HARNESS.md` | Complete methodology & quality rules |
| `commands/cli-anything.md` | `{PLUGIN_ROOT}/references/commands/cli-anything.md` | Full 7-phase build spec |
| `commands/refine.md` | `{PLUGIN_ROOT}/references/commands/refine.md` | Incremental coverage expansion |
| `commands/test.md` | `{PLUGIN_ROOT}/references/commands/test.md` | Real-backend test runner & `TEST.md` |
| `commands/validate.md` | `{PLUGIN_ROOT}/references/commands/validate.md` | 52-check HARNESS compliance audit |
| `commands/list.md` | `{PLUGIN_ROOT}/references/commands/list.md` | Installed & generated CLI discovery |
| `guides/...` | `{PLUGIN_ROOT}/references/guides/...` | On-demand implementation guides |
| `docs/PREVIEW_PROTOCOL.md` | `{PLUGIN_ROOT}/references/docs/PREVIEW_PROTOCOL.md` | Shared `preview-bundle/v1` contract |
| `cli-anything-plugin/repl_skin.py` | `{PLUGIN_ROOT}/scripts/repl_skin.py` | Copy into harness `utils/repl_skin.py` |
| `cli-anything-plugin/preview_bundle.py` | `{PLUGIN_ROOT}/scripts/preview_bundle.py` | Copy into preview-capable harnesses |
| `cli-anything-plugin/skill_generator.py` | `{PLUGIN_ROOT}/scripts/skill_generator.py` | Generate canonical & packaged `SKILL.md` |
| `templates/SKILL.md.template` | `{PLUGIN_ROOT}/scripts/templates/SKILL.md.template` | Jinja2 template for `skill_generator.py` |

## Google Antigravity Tool Bindings

| Antigravity tool | Role in the CLI-Anything workflow |
|---|---|
| `read_file` | Read vendored `HARNESS.md`, commands, guides, target source, and generated files |
| `write_file` / `edit_file` | Author and update `agent-harness/`, `core/`, `utils/`, `tests/`, `setup.py`, `<SOFTWARE>.md`, `TEST.md`, `README.md` |
| `run_command` | Clone repos, inspect directories, run `pytest`, `pip install -e .`, `skill_generator.py`, verify PATH entry points |
| `invoke_subagent` (`research` / `self`) | Optional read-only survey of large upstream codebases (Phase 1) or gap analysis (Refine) without bloating main context |
| `update_steps` / `update_focus` | Surface live phase-by-phase progress in the Antigravity UI, kept in sync with `.cli-anything-progress.json` |
| `search_web` | Look up official backend CLI flags or native file-format specs when missing from local source |

> **Truthfulness rule:** Never use the `browser` subagent or OS screenshots to
> screen-scrape GUI windows as fake preview artifacts. Preview bundles must
> come from the real software backend or native inspection/export paths per
> `PREVIEW_PROTOCOL.md`.

## Inputs

- **Build / Test / Validate:** requires either a **local source path**
  (e.g., `./gimp`, `D:\src\blender`, `/home/user/inkscape`) or a **GitHub
  repository URL** (`https://github.com/org/repo`). Software names alone (such
  as `"gimp"`) are not accepted; clone URLs locally first and derive the
  software name from the directory name.
- **Refine:** requires a **local source path** (same tree used for the build)
  plus an optional natural-language **focus area** (e.g., `"picture-in-picture
  compositing"`).
- **List:** optional `--path <directory>`, `--depth <n>`, and `--json`.

## Modes

Map natural-language or command-style requests to the matching canonical mode:

| Mode | Example user request | Canonical specification |
|---|---|---|
| **Build** | `"Use CLI-Anything to build a harness for ./gimp"` | `{PLUGIN_ROOT}/references/commands/cli-anything.md` |
| **Refine** | `"Refine ./shotcut for picture-in-picture features"` | `{PLUGIN_ROOT}/references/commands/refine.md` |
| **Test** | `"Run CLI-Anything tests for ./libreoffice"` | `{PLUGIN_ROOT}/references/commands/test.md` |
| **Validate** | `"Validate the CLI-Anything harness at ./blender"` | `{PLUGIN_ROOT}/references/commands/validate.md` |
| **List** | `"List all CLI-Anything harnesses in this workspace"` | `{PLUGIN_ROOT}/references/commands/list.md` |

## Phase Gates and Resume (Hard Gate)

For **Build**, **Refine**, **Test**, and **Validate**, persist phase progress
at:

```text
{software-root}/agent-harness/.cli-anything-progress.json
```

Create `agent-harness/` as soon as tracking begins. Schema:

```json
{
  "software": "<name>",
  "mode": "build",
  "target": "<absolute software path>",
  "phases": {
    "0": { "status": "completed", "updated_at": "<ISO-8601 UTC>" },
    "1": { "status": "in_progress", "updated_at": "<ISO-8601 UTC>" }
  },
  "terminal": false,
  "terminal_status": null
}
```

Rules:

- **Build phases:** `0` (source acquisition) -> `1` (codebase analysis) -> `2`
  (CLI architecture & `<SOFTWARE>.md`) -> `3` (implementation) -> `4` (test
  plan in `TEST.md`) -> `5` (test implementation) -> `6` (run tests & update
  `TEST.md`) -> `6.5` (`SKILL.md` generation via vendored `skill_generator.py`)
  -> `7` (PEP 420 `setup.py`, `pip install -e .`, PATH verification).
- **Refine steps:** `inventory` -> `capability_scan` -> `gap_analysis` (confirm
  priorities with user before implementing) -> `implement` -> `test` ->
  `document`. Never remove existing commands unless explicitly requested.
- **Test steps:** `locate` -> `unit_tests` -> `e2e_and_subprocess` ->
  `update_test_md` (append passing results only).
- **Validate steps:** walk all 8 checklist sections in `validate.md` without
  silently lowering the quality bar.
- **Hard gate:** do not start the next phase/step until the previous one is
  recorded as `completed` in `.cli-anything-progress.json`.
- **Resume:** on start, if a non-terminal progress file exists for this target
  and mode, resume from the first non-completed phase instead of redoing
  completed work (unless the user asks for a clean rebuild).
- **Completion:** set `"terminal": true` and `"terminal_status": "success"` or
  `"failed"` only when the run finishes or aborts permanently.
- **List mode** does not require a progress file.

Mirror active phase transitions with `update_steps` so the user sees live
progress in Antigravity.

## Cross-Platform Notes (Windows PowerShell & POSIX)

The vendored canonical docs in `references/` were authored primarily with Linux
bash examples. Adapt shell invocations cleanly to the host OS without altering
the generated harness contract:

- **Harness location:** derive `<software-root>/agent-harness/` from the
  supplied local path or cloned directory — never hardcode `/root/cli-anything/`.
- **Force-installed subprocess tests:**
  - Windows (`pwsh`): `$env:CLI_ANYTHING_FORCE_INSTALLED = "1"; python -m pytest cli_anything/<software>/tests/ -v -s`
  - macOS / Linux (`bash`/`zsh`): `CLI_ANYTHING_FORCE_INSTALLED=1 python3 -m pytest cli_anything/<software>/tests/ -v -s`
- **PATH verification:**
  - Windows (`pwsh`): `Get-Command cli-anything-<software>` or `where.exe cli-anything-<software>`
  - macOS / Linux: `command -v cli-anything-<software>`
- **Python executable:** use `python` on Windows (or active venv interpreter)
  and `python3` on macOS / Linux.
- **Session file locking:** follow `references/guides/session-locking.md`
  (`fcntl.flock` on POSIX). On Windows, where `fcntl` is unavailable, either
  retain the documented fallback or pair it with standard-library `msvcrt.locking`
  so concurrent session saves stay safe on both OS families.
- **UTF-8 I/O:** pass `encoding="utf-8"` when reading/writing JSON, XML,
  `TEST.md`, and `SKILL.md` so Windows codepages (CP1251/CP1252/GBK) never
  corrupt box-drawing characters or metadata.

## Condensed Fallback Rules (Offline / Emergency Only)

Use these only if `{PLUGIN_ROOT}/references/HARNESS.md` cannot be retrieved:

- **Layout:** `<software>/agent-harness/{<SOFTWARE>.md, setup.py, cli_anything/<software>/{__init__.py, __main__.py, README.md, <software>_cli.py, core/, utils/, tests/{TEST.md, test_core.py, test_full_e2e.py}}}`.
- **PEP 420 namespace:** `cli_anything/` MUST NOT contain `__init__.py`;
  `setup.py` uses `find_namespace_packages(include=["cli_anything.*"])`, exposes
  `cli-anything-<software>` in `console_scripts`, and ships `skills/*.md` via
  `package_data`.
- **Real backend rule:** invoke the real application CLI/API/MCP server; never
  reimplement rendering in Python or silently degrade when the software is
  missing.
- **CLI contract:** Click command groups + default REPL (`invoke_without_command=True`)
  using vendored `ReplSkin` + `--json` everywhere + session undo/redo with
  locked JSON saves + auto-save and `--dry-run` for one-shot mutations.
- **Preview contract:** when meaningful visual/inspection state exists, emit
  `preview-bundle/v1` via `cli-anything-<software> preview ...` (producer); keep
  `cli-hub previews ...` strictly read-only (consumer).
- **Testing:** write `TEST.md` plan before test code; include unit tests
  (`test_core.py`), real-file & real-backend E2E tests (`test_full_e2e.py`),
  programmatic output verification (magic bytes / frames / RMS / ZIP), and
  `TestCLISubprocess` using `_resolve_cli("cli-anything-<software>")` without
  hardcoding `cwd` or interpreter paths; append passing `pytest` output to
  `TEST.md`.
- **Skill generation:** run vendored `skill_generator.py` to write canonical
  `skills/cli-anything-<software>/SKILL.md` and packaged
  `cli_anything/<software>/skills/SKILL.md`.

## Output Expectations

When reporting progress or final results, always include:

- target software and resolved source / harness paths
- completed phases and `.cli-anything-progress.json` terminal state
- files created or modified
- exact validation / `pytest` / PATH verification commands run and real results
- generated `SKILL.md` paths and any open risks or backend limitations
