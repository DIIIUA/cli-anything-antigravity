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

SRC_KEY="$(normalize_path_key "$(resolve_real_path "${PLUGIN_SRC}")")"
DEST_CHECK_KEY="$(normalize_path_key "$(resolve_real_path "${DEST_DIR}")")"
if [[ "${SRC_KEY}" == "${DEST_CHECK_KEY}" || "${SRC_KEY}" == "${DEST_CHECK_KEY}/"* ]]; then
  echo "Refusing to install into source directory or an ancestor of it: ${DEST_DIR}" >&2
  exit 1
fi

LOCK_PATH="${PLUGINS_HOME}/.cli-anything.lock"
LOCK_HELD=0
STAGING_DIR=""
MAIN_PID="${BASHPID:-$$}"

cleanup() {
  if [[ "${BASHPID:-$$}" != "${MAIN_PID}" ]]; then
    return 0
  fi
  if [[ -n "${STAGING_DIR}" && -d "${STAGING_DIR}" ]]; then
    rm -rf "${STAGING_DIR}"
  fi
  if [[ "${LOCK_HELD}" -eq 1 ]]; then
    release_install_lock "${LOCK_PATH}"
  fi
}
trap cleanup EXIT

acquire_install_lock "${LOCK_PATH}"
LOCK_HELD=1

if [[ -e "${DEST_DIR}" && "${FORCE}" -ne 1 ]]; then
  echo "Refusing to overwrite existing plugin: ${DEST_DIR}" >&2
  echo "Re-run with --force to upgrade, or remove it manually." >&2
  exit 1
fi

STAGING_DIR="$(mktemp -d "${PLUGINS_HOME}/.cli-anything.tmp.XXXXXX")"
PLUGINS_HOME_KEY="$(normalize_path_key "$(resolve_real_path "${PLUGINS_HOME}")")"
LOCK_KEY="$(normalize_path_key "$(resolve_real_path "${LOCK_PATH}")")"
STAGING_KEY="$(normalize_path_key "$(resolve_real_path "${STAGING_DIR}")")"
DEST_KEY="$(normalize_path_key "$(resolve_real_path "${DEST_DIR}")")"

copy_plugin_tree() {
  local src_dir="$1"
  local dst_dir="$2"
  local is_root="$3"
  mkdir -p "${dst_dir}"
  local entry base entry_key
  while IFS= read -r -d '' entry; do
    base="$(basename "${entry}")"
    if [[ "${is_root}" -eq 1 ]]; then
      case "${base}" in
        tests|harness|.git|.github|.gitignore|.gitattributes|.agents|__pycache__)
          continue
          ;;
      esac
    else
      case "${base}" in
        .git|.agents|__pycache__)
          continue
          ;;
      esac
    fi
    entry_key="$(normalize_path_key "$(resolve_real_path "${entry}")")"
    if [[ "${entry_key}" == "${PLUGINS_HOME_KEY}" || "${entry_key}" == "${STAGING_KEY}" || "${entry_key}" == "${DEST_KEY}" || "${entry_key}" == "${LOCK_KEY}" ]]; then
      continue
    fi
    if [[ -d "${entry}" && ( "${PLUGINS_HOME_KEY}" == "${entry_key}/"* || "${STAGING_KEY}" == "${entry_key}/"* || "${DEST_KEY}" == "${entry_key}/"* || "${LOCK_KEY}" == "${entry_key}/"* ) ]]; then
      copy_plugin_tree "${entry}" "${dst_dir}/${base}" 0
      continue
    fi
    cp -R "${entry}" "${dst_dir}/"
  done < <(find "${src_dir}" -mindepth 1 -maxdepth 1 -print0)
}

copy_plugin_tree "${PLUGIN_SRC}" "${STAGING_DIR}" 1

for req_staged in \
  "plugin.json" \
  "hooks.json" \
  "rules/cli-anything-generator.md" \
  "agents/cli-anything-auditor.md" \
  "skills/cli-anything/SKILL.md" \
  "skills/cli-anything-refine/SKILL.md" \
  "skills/cli-anything-test/SKILL.md" \
  "skills/cli-anything-validate/SKILL.md" \
  "skills/cli-anything-list/SKILL.md" \
  "references/HARNESS.md" \
  "references/docs/PREVIEW_PROTOCOL.md" \
  "scripts/verify_harness.py" \
  "scripts/list_harnesses.py" \
  "scripts/pep420_guard.py" \
  "scripts/_toml_fallback.py" \
  "scripts/repl_skin.py" \
  "scripts/preview_bundle.py" \
  "scripts/skill_generator.py"; do
  if [[ ! -f "${STAGING_DIR}/${req_staged}" ]]; then
    echo "Staged plugin is missing required file: ${req_staged}" >&2
    exit 1
  fi
done

PYBIN="$(detect_python_bin 2>/dev/null || true)"
if [[ -n "${PYBIN}" ]]; then
  if [[ "${PYBIN}" == "python3" && -f "${STAGING_DIR}/hooks.json" ]] && ! command -v python >/dev/null 2>&1; then
    "${PYBIN}" -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding="utf-8").replace("python -S ./scripts/pep420_guard.py", "python3 -S ./scripts/pep420_guard.py"), encoding="utf-8")
' "${STAGING_DIR}/hooks.json"
  fi
  "${PYBIN}" -B -m py_compile \
    "${STAGING_DIR}/scripts/repl_skin.py" \
    "${STAGING_DIR}/scripts/preview_bundle.py" \
    "${STAGING_DIR}/scripts/skill_generator.py" \
    "${STAGING_DIR}/scripts/_toml_fallback.py" \
    "${STAGING_DIR}/scripts/verify_harness.py" \
    "${STAGING_DIR}/scripts/list_harnesses.py" \
    "${STAGING_DIR}/scripts/pep420_guard.py"
fi

if [[ -e "${DEST_DIR}" ]]; then
  if [[ "${FORCE}" -ne 1 ]]; then
    echo "Refusing to overwrite existing plugin: ${DEST_DIR}" >&2
    echo "Re-run with --force to upgrade, or remove it manually." >&2
    exit 1
  fi
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
  write_discovery_pointer "${DISCOVERY_POINTER}" "${PLUGIN_ROOT}"
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
