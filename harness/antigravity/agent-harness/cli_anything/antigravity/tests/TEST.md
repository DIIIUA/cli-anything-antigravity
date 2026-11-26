# Test Plan & Verification Report — `cli-anything-antigravity`

## Part 1: Test Plan

### 1. Test Inventory Plan

- `test_core.py`: 16 unit tests planned (synthetic data, zero external dependencies — runs on Linux, macOS, and Windows CI without needing Antigravity IDE installed)
- `test_full_e2e.py`: 10 end-to-end and installed-CLI subprocess tests planned (invoking real `antigravity-ide` binary, validating the live installed `cli-anything` plugin, and running `TestCLISubprocess` with `_resolve_cli("cli-anything-antigravity")`)

### 2. Unit Test Plan (`test_core.py`)

| Module | Functions Tested | Edge Cases & Assertions | Planned Count |
|---|---|---|---|
| `core/project.py` | `create_project`, `parse_yaml_frontmatter`, `set_plugin_meta`, `add_skill`, `add_rule`, `add_agent`, `add_command_hook`, `add_mcp_stdio`, `add_mcp_http`, `add_discovery_entry`, `configure_sdk`, `validate_project`, `import_from_dir`, `validate_plugin_directory` | Invalid slug/semver/scope, glob rule without `--globs`, 24 KB rule limit, agent `tools:` allowlist warning, MCP server name regex & URL scheme validation, round-trip import/validate of exported bundle | 9 |
| `core/export.py` | `export_project`, `render_sdk_python`, `EXPORT_PRESETS` | Dry-run produces zero files, conflict refusal without `--overwrite`, full plugin bundle materialization, AST-valid `LocalAgentConfig` / `LiteRTAgentConfig` Python generation | 3 |
| `core/session.py` | `Session`, `mutate`, `undo`, `redo`, `_locked_save_json` | Atomic rollback on mutation failure (zero undo/history pollution), locked JSON shrink overwrite | 2 |
| `utils/antigravity_backend.py` | `parse_extensions_output`, `redact_secrets` | Filtering diagnostic noise lines (`[createInstance] ...`), recursive secret redaction for tokens/keys | 2 |

### 3. E2E Test Plan (`test_full_e2e.py`)

- **Real `antigravity-ide` backend execution:** `get_ide_version()` returns live semver + arch; `list_ide_extensions(show_versions=True)` returns clean parsed extension records from the real installed Antigravity IDE binary.
- **Live dogfood validation:** `validate_plugin_directory` + `import_from_dir` against the real installed `cli-anything` plugin (`~/.gemini/config/plugins/cli-anything`), verifying 5 skills, 1 glob rule, 1 auditor agent, and 1 hook group with 0 schema errors.
- **Full bundle authoring -> export -> re-validate -> SDK codegen round-trip** in isolated `tmp_path` (never mutating real `~/.gemini/config/`).
- **Installed CLI Subprocess (`TestCLISubprocess` with `_resolve_cli("cli-anything-antigravity")`):**
  - `--help`, `--json ide detect`, `--json ide version`, `--json ide extensions`
  - One-shot auto-save + `--dry-run` suppression + Windows glob preservation (`**/agent-harness/**`)
  - Full plugin authoring, CLI-Hub `discovery bridge-clihub`, `project export`, `plugin validate-dir`, `sdk export-python`
  - Non-TTY REPL preserving `--json` and rolling back failed mutations cleanly.


## Part 2: Test Results

### Execution Environment

- **Date:** 2026-11-26
- **Host:** Windows (Python 3.14.0, pytest 9.0.3)
- **Live Antigravity IDE binary:** `C:\Users\HYPERPC\AppData\Local\Programs\Antigravity IDE\bin\antigravity-ide.CMD` (Antigravity IDE `1.107.0 x64`, 7 live extensions discovered)
- **Resolved CLI (from `$env:TEMP`):** `C:\Python314\Scripts\cli-anything-antigravity.EXE` (`CLI_ANYTHING_FORCE_INSTALLED=1`)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.3, pluggy-1.6.0 -- C:\Python314\python.exe
collected 26 items

cli_anything/antigravity/tests/test_core.py::test_create_project_and_validation_rejects_bad_inputs PASSED
cli_anything/antigravity/tests/test_core.py::test_parse_yaml_frontmatter_handles_folded_and_lists PASSED
cli_anything/antigravity/tests/test_core.py::test_set_plugin_meta_and_suggested_prompts PASSED
cli_anything/antigravity/tests/test_core.py::test_skill_crud_and_validation PASSED
cli_anything/antigravity/tests/test_core.py::test_rule_trigger_glob_and_24kb_cap PASSED
cli_anything/antigravity/tests/test_core.py::test_agent_and_tools_allowlist_warning PASSED
cli_anything/antigravity/tests/test_core.py::test_hooks_add_toggle_and_remove PASSED
cli_anything/antigravity/tests/test_core.py::test_mcp_stdio_http_and_secret_redaction PASSED
cli_anything/antigravity/tests/test_core.py::test_discovery_and_sdk_config_validation PASSED
cli_anything/antigravity/tests/test_core.py::test_export_dry_run_materialize_and_roundtrip_import PASSED
cli_anything/antigravity/tests/test_core.py::test_render_sdk_python_produces_valid_ast PASSED
cli_anything/antigravity/tests/test_core.py::test_export_presets_and_profiles_exist PASSED
cli_anything/antigravity/tests/test_core.py::test_session_atomic_mutate_rollback_and_undo_redo PASSED
cli_anything/antigravity/tests/test_core.py::test_locked_save_json_truncates_shorter_payload PASSED
cli_anything/antigravity/tests/test_core.py::test_parse_extensions_output_filters_diagnostic_noise PASSED
cli_anything/antigravity/tests/test_core.py::test_inspect_host_customizations_isolated_never_reads_config_json PASSED
cli_anything/antigravity/tests/test_full_e2e.py::test_e2e_real_antigravity_ide_version PASSED
cli_anything/antigravity/tests/test_full_e2e.py::test_e2e_real_antigravity_ide_extensions_list PASSED
cli_anything/antigravity/tests/test_full_e2e.py::test_e2e_dogfood_validate_installed_cli_anything_plugin PASSED
cli_anything/antigravity/tests/test_full_e2e.py::test_e2e_host_customization_inventory_finds_cli_anything PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_help PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_ide_detect_and_version_json PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_autosave_dry_run_and_windows_glob_preservation PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_full_plugin_authoring_export_validate_and_sdk_workflow PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_dogfood_validate_live_cli_anything_plugin PASSED
cli_anything/antigravity/tests/test_full_e2e.py::TestCLISubprocess::test_cli_repl_preserves_json_and_rolls_back_failed_mutation PASSED

============================= 26 passed in 4.64s ==============================
```

### Summary Statistics

- **Total tests:** 26 (16 unit, 4 real-backend E2E, 6 installed-CLI subprocess E2E)
- **Pass rate:** 100% (26/26 passed, 3-way PEP 420 coexistence verified with `cli_anything.gimp` and `cli_anything.sevenzip`)
- **Execution time:** 4.64s
