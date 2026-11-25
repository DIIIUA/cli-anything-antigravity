#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d)"
export HOME="${TMP_DIR}/home"
mkdir -p "${HOME}"
PLUGINS_HOME="${TMP_DIR}/plugins"
INSTALLED_DIR="${PLUGINS_HOME}/cli-anything"
STALE_STAGING_DIR="${PLUGINS_HOME}/.cli-anything.tmp.stale"
DISCOVERY_POINTER="${HOME}/.gemini/cli-anything-generator.root"
WORKSPACE_DIR="${TMP_DIR}/sample-workspace"
WS_INSTALLED_DIR="${WORKSPACE_DIR}/.agents/plugins/cli-anything"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1 && python -c "import sys" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_file() {
  [[ -f "$1" ]] || fail "expected file: $1"
}

assert_same() {
  cmp -s "$1" "$2" || fail "files differ: $1 $2"
}

[[ -n "${PYTHON_BIN}" ]] || fail "python3/python not available"

mkdir -p "${WORKSPACE_DIR}"

# 1. Dry-run does not create directories
DRY_PLUGINS="${TMP_DIR}/dry-root/plugins"
ANTIGRAVITY_PLUGINS_HOME="${DRY_PLUGINS}" bash "${PLUGIN_SRC}/scripts/install.sh" --dry-run >/dev/null
[[ ! -e "${DRY_PLUGINS}" ]] || fail "--dry-run created plugins directory"

mkdir -p "${STALE_STAGING_DIR}"
echo "left over" > "${STALE_STAGING_DIR}/stale.txt"

# 2. Global install
ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh"

assert_file "${INSTALLED_DIR}/plugin.json"
assert_file "${INSTALLED_DIR}/README.md"
assert_file "${INSTALLED_DIR}/LICENSE"
assert_file "${INSTALLED_DIR}/NOTICE"
assert_file "${INSTALLED_DIR}/UPSTREAM_SYNC.json"
assert_file "${INSTALLED_DIR}/PLUGIN_ROOT.txt"
assert_file "${INSTALLED_DIR}/assets/logo.svg"
assert_file "${INSTALLED_DIR}/hooks.json"
assert_file "${INSTALLED_DIR}/rules/cli-anything-generator.md"
assert_file "${INSTALLED_DIR}/agents/cli-anything-auditor.md"
assert_file "${DISCOVERY_POINTER}"
for skill in cli-anything cli-anything-refine cli-anything-test cli-anything-validate cli-anything-list; do
  assert_file "${INSTALLED_DIR}/skills/${skill}/SKILL.md"
done
assert_file "${INSTALLED_DIR}/references/antigravity-tooling.md"
assert_file "${INSTALLED_DIR}/references/HARNESS.md"
assert_file "${INSTALLED_DIR}/references/commands/cli-anything.md"
assert_file "${INSTALLED_DIR}/references/docs/PREVIEW_PROTOCOL.md"
assert_file "${INSTALLED_DIR}/scripts/repl_skin.py"
assert_file "${INSTALLED_DIR}/scripts/preview_bundle.py"
assert_file "${INSTALLED_DIR}/scripts/skill_generator.py"
assert_file "${INSTALLED_DIR}/scripts/verify_harness.py"
assert_file "${INSTALLED_DIR}/scripts/list_harnesses.py"
assert_file "${INSTALLED_DIR}/scripts/pep420_guard.py"
assert_file "${INSTALLED_DIR}/scripts/templates/SKILL.md.template"
[[ ! -e "${PLUGINS_HOME}/.cli-anything.lock" ]] || fail "stale lock remained"

STAMP="$(tr -d '\r\n' < "${INSTALLED_DIR}/PLUGIN_ROOT.txt")"
POINTER="$(tr -d '\r\n' < "${DISCOVERY_POINTER}")"
[[ -n "${STAMP}" && "${STAMP}" == "${POINTER}" ]] || fail "pointer mismatch"

[[ -d "${STALE_STAGING_DIR}" ]] || fail "touched stale staging dir"
[[ ! -d "${INSTALLED_DIR}/tests" ]] || fail "copied tests/"
[[ ! -d "${INSTALLED_DIR}/.github" ]] || fail "copied .github/"
[[ ! -e "${INSTALLED_DIR}/rules/AGENTS.md" ]] || fail "must not ship always-on rules/AGENTS.md"

assert_same "${PLUGIN_SRC}/references/HARNESS.md" "${INSTALLED_DIR}/references/HARNESS.md"
assert_same "${PLUGIN_SRC}/scripts/repl_skin.py" "${INSTALLED_DIR}/scripts/repl_skin.py"
assert_same "${PLUGIN_SRC}/scripts/verify_harness.py" "${INSTALLED_DIR}/scripts/verify_harness.py"

"${PYTHON_BIN}" -B -m py_compile \
  "${INSTALLED_DIR}/scripts/repl_skin.py" \
  "${INSTALLED_DIR}/scripts/preview_bundle.py" \
  "${INSTALLED_DIR}/scripts/skill_generator.py" \
  "${INSTALLED_DIR}/scripts/verify_harness.py" \
  "${INSTALLED_DIR}/scripts/list_harnesses.py" \
  "${INSTALLED_DIR}/scripts/pep420_guard.py"

"${PYTHON_BIN}" - <<'PY' "${INSTALLED_DIR}"
import json, os, re, sys
root = sys.argv[1]
manifest = json.load(open(os.path.join(root, "plugin.json"), encoding="utf-8"))
allowed = {
    "$schema", "name", "displayName", "version", "description", "author",
    "homepage", "repository", "logo", "suggestedPrompts", "disabled",
    "license", "keywords", "skills", "extensions",
}
unknown = set(manifest.keys()) - allowed
assert not unknown, f"Unknown plugin.json fields: {unknown}"
assert manifest.get("name") == "cli-anything", manifest
assert manifest.get("$schema") == "https://antigravity.google/schemas/v1/plugin.json", manifest
assert manifest.get("license") == "Apache-2.0", manifest
assert isinstance(manifest.get("suggestedPrompts"), list) and len(manifest["suggestedPrompts"]) == 3
assert os.path.isfile(os.path.join(root, manifest["logo"]))
for sk in ["cli-anything", "cli-anything-refine", "cli-anything-test", "cli-anything-validate", "cli-anything-list"]:
    text = open(os.path.join(root, "skills", sk, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r"(?m)^name:\s*(\S+)\s*$", text)
    assert m and m.group(1) == sk, f"Skill mismatch for {sk}"
rule_text = open(os.path.join(root, "rules", "cli-anything-generator.md"), encoding="utf-8").read()
assert "trigger: glob" in rule_text
hooks = json.load(open(os.path.join(root, "hooks.json"), encoding="utf-8"))
assert hooks["pep420-namespace-guard"]["enabled"] is False
PY

# Simulate direct `agy plugin install` (no PLUGIN_ROOT.txt): installed scripts still run cleanly
rm -f "${INSTALLED_DIR}/PLUGIN_ROOT.txt"
"${PYTHON_BIN}" "${INSTALLED_DIR}/scripts/list_harnesses.py" --path "${TMP_DIR}" --json >/dev/null

if ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh" >/dev/null 2>&1; then
  fail "overwrote without --force"
fi

ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh" --force
bash "${PLUGIN_SRC}/scripts/install.sh" --workspace "${WORKSPACE_DIR}"
assert_file "${WS_INSTALLED_DIR}/references/HARNESS.md"
[[ "$(tr -d '\r\n' < "${DISCOVERY_POINTER}")" == "${STAMP}" ]] || fail "workspace install clobbered pointer"
bash "${PLUGIN_SRC}/scripts/uninstall.sh" --workspace "${WORKSPACE_DIR}"
[[ ! -e "${WS_INSTALLED_DIR}" && -f "${DISCOVERY_POINTER}" ]] || fail "workspace uninstall failed"

ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/uninstall.sh"
[[ ! -e "${INSTALLED_DIR}" && ! -e "${DISCOVERY_POINTER}" ]] || fail "uninstall failed"

ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh"
FOREIGN_ROOT="${TMP_DIR}/other-root"
printf '%s\n' "${FOREIGN_ROOT}" > "${DISCOVERY_POINTER}"
ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/uninstall.sh"
[[ ! -e "${INSTALLED_DIR}" && "$(tr -d '\r\n' < "${DISCOVERY_POINTER}")" == "${FOREIGN_ROOT}" ]] || fail "foreign pointer changed"

echo "PASS: Community Edition v2.0 Antigravity plugin tests passed."
