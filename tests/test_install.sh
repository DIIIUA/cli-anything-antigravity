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
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
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

mkdir -p "${STALE_STAGING_DIR}" "${WORKSPACE_DIR}"
echo "left over from an interrupted install" > "${STALE_STAGING_DIR}/stale.txt"

ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh"

assert_file "${INSTALLED_DIR}/plugin.json"
assert_file "${INSTALLED_DIR}/README.md"
assert_file "${INSTALLED_DIR}/LICENSE"
assert_file "${INSTALLED_DIR}/NOTICE"
assert_file "${INSTALLED_DIR}/UPSTREAM_SYNC.json"
assert_file "${INSTALLED_DIR}/PLUGIN_ROOT.txt"
assert_file "${INSTALLED_DIR}/assets/logo.svg"
assert_file "${DISCOVERY_POINTER}"
assert_file "${INSTALLED_DIR}/skills/cli-anything/SKILL.md"
assert_file "${INSTALLED_DIR}/references/HARNESS.md"
assert_file "${INSTALLED_DIR}/references/commands/cli-anything.md"
assert_file "${INSTALLED_DIR}/references/commands/refine.md"
assert_file "${INSTALLED_DIR}/references/commands/test.md"
assert_file "${INSTALLED_DIR}/references/commands/validate.md"
assert_file "${INSTALLED_DIR}/references/commands/list.md"
assert_file "${INSTALLED_DIR}/references/guides/auto-save-dry-run.md"
assert_file "${INSTALLED_DIR}/references/guides/session-locking.md"
assert_file "${INSTALLED_DIR}/references/guides/preview-methodology.md"
assert_file "${INSTALLED_DIR}/scripts/repl_skin.py"
assert_file "${INSTALLED_DIR}/scripts/preview_bundle.py"
assert_file "${INSTALLED_DIR}/scripts/skill_generator.py"
assert_file "${INSTALLED_DIR}/scripts/templates/SKILL.md.template"
assert_file "${INSTALLED_DIR}/references/docs/PREVIEW_PROTOCOL.md"

STAMP="$(tr -d '\r\n' < "${INSTALLED_DIR}/PLUGIN_ROOT.txt")"
POINTER="$(tr -d '\r\n' < "${DISCOVERY_POINTER}")"
[[ -n "${STAMP}" ]] || fail "PLUGIN_ROOT.txt is empty"
[[ "${STAMP}" == "${POINTER}" ]] || fail "discovery pointer mismatch: ${POINTER} != ${STAMP}"

case "$(uname -s 2>/dev/null || true)" in
  MINGW*|MSYS*|CYGWIN*)
    [[ "${STAMP}" =~ ^[A-Za-z]:\\ ]] ||
      fail "Windows Git Bash install must stamp a drive path, got: ${STAMP}"
    ;;
  *)
    assert_file "${STAMP}/references/HARNESS.md"
    ;;
esac

[[ -d "${STALE_STAGING_DIR}" ]] || fail "installer touched stale staging dir"
[[ ! -d "${INSTALLED_DIR}/tests" ]] || fail "installer copied tests/"
[[ ! -d "${INSTALLED_DIR}/.github" ]] || fail "installer copied .github/"
[[ ! -e "${INSTALLED_DIR}/rules/AGENTS.md" ]] || fail "must not ship always-on rules/AGENTS.md"

assert_same "${PLUGIN_SRC}/references/HARNESS.md" "${INSTALLED_DIR}/references/HARNESS.md"
assert_same "${PLUGIN_SRC}/scripts/repl_skin.py" "${INSTALLED_DIR}/scripts/repl_skin.py"
assert_same "${PLUGIN_SRC}/scripts/preview_bundle.py" "${INSTALLED_DIR}/scripts/preview_bundle.py"
assert_same "${PLUGIN_SRC}/scripts/skill_generator.py" "${INSTALLED_DIR}/scripts/skill_generator.py"

"${PYTHON_BIN}" -m py_compile \
  "${INSTALLED_DIR}/scripts/repl_skin.py" \
  "${INSTALLED_DIR}/scripts/preview_bundle.py" \
  "${INSTALLED_DIR}/scripts/skill_generator.py"

"${PYTHON_BIN}" - <<'PY' "${INSTALLED_DIR}/plugin.json" "${INSTALLED_DIR}"
import json, os, sys
manifest_path, root = sys.argv[1], sys.argv[2]
data = json.load(open(manifest_path, encoding="utf-8"))
allowed = {
    "name", "displayName", "version", "description", "author",
    "homepage", "repository", "logo", "suggestedPrompts", "disabled",
}
unknown = set(data.keys()) - allowed
assert not unknown, f"Unknown top-level plugin.json fields: {unknown}"
assert data.get("name") == "cli-anything", data
assert isinstance(data.get("suggestedPrompts"), list) and len(data["suggestedPrompts"]) == 3, data
assert os.path.isfile(os.path.join(root, data["logo"])), data["logo"]
PY

if ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh" >/dev/null 2>&1; then
  fail "installer overwrote existing plugin without --force"
fi

MARKER="${INSTALLED_DIR}/.install-marker"
echo "first-install" > "${MARKER}"
ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh" --force
[[ ! -f "${MARKER}" ]] || fail "--force upgrade did not replace previous install"

# Workspace install preserves global discovery pointer
bash "${PLUGIN_SRC}/scripts/install.sh" --workspace "${WORKSPACE_DIR}"
assert_file "${WS_INSTALLED_DIR}/references/HARNESS.md"
POINTER_AFTER_WS="$(tr -d '\r\n' < "${DISCOVERY_POINTER}")"
[[ "${POINTER_AFTER_WS}" == "${STAMP}" ]] || fail "workspace install overwrote global pointer"
bash "${PLUGIN_SRC}/scripts/uninstall.sh" --workspace "${WORKSPACE_DIR}"
[[ ! -e "${WS_INSTALLED_DIR}" ]] || fail "workspace uninstall failed"
[[ -f "${DISCOVERY_POINTER}" ]] || fail "workspace uninstall removed global pointer"

# Reject non-plugins ANTIGRAVITY_PLUGINS_HOME
BAD_HOME="${TMP_DIR}/not-plugins"
if ANTIGRAVITY_PLUGINS_HOME="${BAD_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh" >/dev/null 2>&1; then
  fail "accepted non-plugins ANTIGRAVITY_PLUGINS_HOME"
fi
[[ ! -e "${BAD_HOME}" ]] || fail "created rejected plugins home"

# Uninstall & foreign pointer protection
ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/uninstall.sh"
[[ ! -e "${INSTALLED_DIR}" ]] || fail "uninstall left plugin dir"
[[ ! -e "${DISCOVERY_POINTER}" ]] || fail "uninstall left discovery pointer"

ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/install.sh"
FOREIGN_ROOT="${TMP_DIR}/other-root"
printf '%s\n' "${FOREIGN_ROOT}" > "${DISCOVERY_POINTER}"
ANTIGRAVITY_PLUGINS_HOME="${PLUGINS_HOME}" bash "${PLUGIN_SRC}/scripts/uninstall.sh"
[[ ! -e "${INSTALLED_DIR}" ]] || fail "uninstall left plugin dir"
[[ "$(tr -d '\r\n' < "${DISCOVERY_POINTER}")" == "${FOREIGN_ROOT}" ]] || fail "foreign pointer changed"

echo "PASS: Community Edition Antigravity plugin tests passed."
