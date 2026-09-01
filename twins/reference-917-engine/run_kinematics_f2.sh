#!/usr/bin/env bash
# Ajoute une couche cinématique F2 à un USD déjà enrichi en matériaux/physique.
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 INPUT_USD [OUTPUT_DIR]" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_USD="$1"
OUTPUT_DIR="${2:-${ROOT}/work/917-omniverse-f2/kinematics}"
PYTHON="${PYTHON:-/opt/simready-validation/bin/python}"
CONFIG="${ROOT}/twins/reference-917-engine/kinematics-f2.json"
OUTPUT_USD="${OUTPUT_DIR}/917-engine-kinematic-f2.usda"

mkdir -p "${OUTPUT_DIR}"
"${PYTHON}" "${ROOT}/twins/reference-917-engine/source/author_kinematics_f2.py" \
    "${INPUT_USD}" "${OUTPUT_USD}" \
    --config "${CONFIG}" \
    --report "${OUTPUT_DIR}/author-kinematics-f2.json"
"${PYTHON}" "${ROOT}/twins/reference-917-engine/source/validate_kinematics_f2.py" \
    "${OUTPUT_USD}" \
    --config "${CONFIG}" \
    --report "${OUTPUT_DIR}/validate-kinematics-f2.json"

printf '%s\n' "${OUTPUT_USD}"
