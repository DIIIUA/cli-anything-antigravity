#!/usr/bin/env bash

set -euo pipefail

FORCE=0
DRY_RUN=0
WORKSPACE_PATH=""

while [[ $# -gt 0 ]]; do
  case "${1}" in
    --force|-f)
      FORCE=1
      shift
      ;;
    --dry-run|-n)
      DRY_RUN=1
      shift
      ;;
    --workspace|-w)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for ${1}" >&2
        exit 2
      fi
      WORKSPACE_PATH="${2}"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--force] [--dry-run] [--workspace <path>]"
      echo "Install CLI-Anything for Google Antigravity (Community Edition)."
      echo "Global destination:    \${ANTIGRAVITY_PLUGINS_HOME:-~/.gemini/config/plugins}/cli-anything"
      echo "Workspace destination: <workspace>/.agents/plugins/cli-anything"
      exit 0
      ;;
    *)
      echo "Unknown argument: ${1}" >&2
      echo "Usage: $0 [--force] [--dry-run] [--workspace <path>]" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

PLUGIN_SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"

for req in \
  "plugin.json" \
  "hooks.json" \
  "rules/cli-anything-generator.md" \
  "agents/cli-anything-auditor.md" \
  "skills/cli-anything/SKILL.md" \
  "skills/cli-anything-refine/SKILL.md" \
  "skills/cli-anything-test/SKILL.md" \
  "skills/cli-anything-validate/SKILL.md" \
  "skills/cli-anything-list/SKILL.md" \
  "references/antigravity-tooling.md" \
  "references/HARNESS.md" \
  "references/commands/cli-anything.md" \
  "references/docs/PREVIEW_PROTOCOL.md" \
  "scripts/repl_skin.py" \
  "scripts/preview_bundle.py" \
  "scripts/skill_generator.py" \
  "scripts/verify_harness.py" \
  "scripts/list_harnesses.py" \
  "scripts/pep420_guard.py" \
  "scripts/templates/SKILL.md.template"; do
  if [[ ! -f "${PLUGIN_SRC}/${req}" ]]; then
    echo "Missing required plugin resource: ${PLUGIN_SRC}/${req}" >&2
    echo "Run scripts/sync-upstream.sh or re-clone the complete repository." >&2
    exit 1
  fi
done

IS_GLOBAL=1
if [[ -n "${WORKSPACE_PATH}" ]]; then
  IS_GLOBAL=0
  WS_ROOT="$(resolve_workspace_root "${WORKSPACE_PATH}")"
  PLUGINS_HOME="${WS_ROOT}/.agents/plugins"
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    mkdir -p "${PLUGINS_HOME}"
  fi
else
  CREATE_MODE="create"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    CREATE_MODE=""
  fi
  if [[ -n "${ANTIGRAVITY_PLUGINS_HOME:-}" ]]; then
    PLUGINS_HOME="$(resolve_plugins_home "${ANTIGRAVITY_PLUGINS_HOME}" "${CREATE_MODE}")"
  else
    PLUGINS_HOME="$(resolve_plugins_home "${HOME}/.gemini/config/plugins" "${CREATE_MODE}")"
  fi
fi

DEST_DIR="${PLUGINS_HOME}/cli-anything"
DISCOVERY_POINTER="$(discovery_pointer_path)"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[dry-run] Source:            ${PLUGIN_SRC}"
  echo "[dry-run] Destination:       ${DEST_DIR}"
  if [[ "${IS_GLOBAL}" -eq 1 ]]; then
    echo "[dry-run] Discovery pointer: ${DISCOVERY_POINTER}"
  else
    echo "[dry-run] Discovery pointer: (unchanged for workspace install)"
  fi
  exit 0
fi

LOCK_DIR="${PLUGINS_HOME}/.cli-anything.lock"
LOCK_HELD=0
STAGING_DIR=""

cleanup() {
  if [[ -n "${STAGING_DIR}" && -d "${STAGING_DIR}" ]]; then
    rm -rf "${STAGING_DIR}"
  fi
  if [[ "${LOCK_HELD}" -eq 1 ]]; then
    release_install_lock "${LOCK_DIR}"
  fi
}
trap cleanup EXIT

acquire_install_lock "${LOCK_DIR}"
LOCK_HELD=1

if [[ -e "${DEST_DIR}" && "${FORCE}" -ne 1 ]]; then
  echo "Refusing to overwrite existing plugin: ${DEST_DIR}" >&2
  echo "Re-run with --force to upgrade, or remove it manually." >&2
  exit 1
fi

STAGING_DIR="$(mktemp -d "${PLUGINS_HOME}/.cli-anything.tmp.XXXXXX")"

while IFS= read -r -d '' entry; do
  base="$(basename "${entry}")"
  case "${base}" in
    tests|.git|.github|.gitignore|.gitattributes|__pycache__)
      continue
      ;;
  esac
  cp -R "${entry}" "${STAGING_DIR}/"
done < <(find "${PLUGIN_SRC}" -mindepth 1 -maxdepth 1 -print0)

PYBIN="$(detect_python_bin 2>/dev/null || true)"
if [[ -n "${PYBIN}" ]]; then
  "${PYBIN}" -B -m py_compile \
    "${STAGING_DIR}/scripts/repl_skin.py" \
    "${STAGING_DIR}/scripts/preview_bundle.py" \
    "${STAGING_DIR}/scripts/skill_generator.py" \
    "${STAGING_DIR}/scripts/verify_harness.py" \
    "${STAGING_DIR}/scripts/list_harnesses.py" \
    "${STAGING_DIR}/scripts/pep420_guard.py"
fi

if [[ -e "${DEST_DIR}" ]]; then
  BACKUP_DIR="${PLUGINS_HOME}/.cli-anything.bak.$(date +%s).$$"
  mv "${DEST_DIR}" "${BACKUP_DIR}"
  if ! mv "${STAGING_DIR}" "${DEST_DIR}"; then
    mv "${BACKUP_DIR}" "${DEST_DIR}"
    echo "Failed to install plugin; previous install restored." >&2
    exit 1
  fi
  rm -rf "${BACKUP_DIR}"
else
  mv "${STAGING_DIR}" "${DEST_DIR}"
fi
STAGING_DIR=""

PLUGIN_ROOT="$(to_host_path "$(cd "${DEST_DIR}" && pwd -P)")"
printf '%s\n' "${PLUGIN_ROOT}" > "${DEST_DIR}/PLUGIN_ROOT.txt"

if [[ "${IS_GLOBAL}" -eq 1 ]]; then
  mkdir -p "$(dirname "${DISCOVERY_POINTER}")"
  printf '%s\n' "${PLUGIN_ROOT}" > "${DISCOVERY_POINTER}"
fi

echo "Installed CLI-Anything (Community Edition) for Antigravity to: ${DEST_DIR}"
echo "PLUGIN_ROOT stamp: ${PLUGIN_ROOT}"
if [[ "${IS_GLOBAL}" -eq 1 ]]; then
  echo "Discovery pointer: ${DISCOVERY_POINTER}"
else
  echo "Workspace-scoped install (global discovery pointer left unchanged)."
fi
echo "Slash commands ready on next turn: /cli-anything, /cli-anything-refine, /cli-anything-test, /cli-anything-validate, /cli-anything-list"
echo "Consumer Hub/skills are separate: npx skills add HKUDS/CLI-Anything --skill cli-hub-meta-skill -g -y"
