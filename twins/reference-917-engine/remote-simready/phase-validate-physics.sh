#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"
. "${SCRIPT_DIR}/_validate-one.sh"
validate_one_main "validate-physics" "references/omni-asset-validate-physics/scripts/run.py" "validate-geometry" "$@"
