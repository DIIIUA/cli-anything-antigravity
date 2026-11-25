#!/usr/bin/env bash
# Sync canonical methodology and helper scripts from HKUDS/CLI-Anything.

set -euo pipefail

UPSTREAM_URL="https://github.com/HKUDS/CLI-Anything.git"
SOURCE_DIR=""

while [[ $# -gt 0 ]]; do
  case "${1}" in
    --source|-s)
      SOURCE_DIR="${2}"
      shift 2
      ;;
    --repo)
      UPSTREAM_URL="${2}"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--source <local-cli-anything-repo>] [--repo <git-url>]"
      exit 0
      ;;
    *)
      echo "Unknown argument: ${1}" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR=""

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

if [[ -z "${SOURCE_DIR}" ]]; then
  TMP_DIR="$(mktemp -d)"
  git clone --depth 1 "${UPSTREAM_URL}" "${TMP_DIR}/upstream"
  SOURCE_DIR="${TMP_DIR}/upstream"
fi

CANONICAL="${SOURCE_DIR}/cli-anything-plugin"
PREVIEW="${SOURCE_DIR}/docs/PREVIEW_PROTOCOL.md"

[[ -f "${CANONICAL}/HARNESS.md" ]] || { echo "Missing ${CANONICAL}/HARNESS.md" >&2; exit 1; }
[[ -f "${PREVIEW}" ]] || { echo "Missing ${PREVIEW}" >&2; exit 1; }

rm -rf "${REPO_ROOT}/references" "${REPO_ROOT}/scripts/templates"
mkdir -p \
  "${REPO_ROOT}/references/commands" \
  "${REPO_ROOT}/references/guides" \
  "${REPO_ROOT}/references/docs" \
  "${REPO_ROOT}/scripts/templates"

cp "${CANONICAL}/HARNESS.md" "${REPO_ROOT}/references/HARNESS.md"
cp "${CANONICAL}/commands/"*.md "${REPO_ROOT}/references/commands/"
cp "${CANONICAL}/guides/"*.md "${REPO_ROOT}/references/guides/"
cp "${PREVIEW}" "${REPO_ROOT}/references/docs/PREVIEW_PROTOCOL.md"
cp "${CANONICAL}/repl_skin.py" "${REPO_ROOT}/scripts/repl_skin.py"
cp "${CANONICAL}/preview_bundle.py" "${REPO_ROOT}/scripts/preview_bundle.py"
cp "${CANONICAL}/skill_generator.py" "${REPO_ROOT}/scripts/skill_generator.py"
cp "${CANONICAL}/templates/"* "${REPO_ROOT}/scripts/templates/"

UPSTREAM_COMMIT="$(git -C "${SOURCE_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
UPSTREAM_SHORT="$(git -C "${SOURCE_DIR}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
SYNCED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "${REPO_ROOT}/UPSTREAM_SYNC.json" <<EOF
{
  "upstream_repo": "HKUDS/CLI-Anything",
  "upstream_commit": "${UPSTREAM_COMMIT}",
  "upstream_short": "${UPSTREAM_SHORT}",
  "synced_at_utc": "${SYNCED_AT}"
}
EOF

echo "Synced canonical resources from HKUDS/CLI-Anything@${UPSTREAM_SHORT}."
