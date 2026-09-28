#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 SOURCE_OBJ OUTPUT_DIRECTORY" >&2
    exit 2
fi

REFERENCE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$1"
OUTPUT="$2"
PYTHON="${PYTHON:-python3}"
SCRIPTS="${REFERENCE_DIR}/source"
CONTRACT="${CONTRACT:-${REFERENCE_DIR}/reengineering-contract.json}"
ENGINEERING_INPUTS="${ENGINEERING_INPUTS:-${REFERENCE_DIR}/engineering-inputs.template.json}"

"${PYTHON}" "${SCRIPTS}/prepare_scan.py" "${SOURCE}" "${OUTPUT}"
LIGHT="${OUTPUT}/derived/head-with-studs-light-300k.ply"
"${PYTHON}" "${SCRIPTS}/segment_hardware.py" "${LIGHT}" "${OUTPUT}/segmented"
"${PYTHON}" "${SCRIPTS}/extract_interfaces.py" "${LIGHT}" "${OUTPUT}/reports/interfaces.json"
"${PYTHON}" "${SCRIPTS}/build_cfd_stubs.py" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cfd"
"${PYTHON}" "${SCRIPTS}/build_interface_proxy.py" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cad"
"${PYTHON}" "${SCRIPTS}/build_valve_variants.py" "${OUTPUT}/cad/valves"
"${PYTHON}" "${SCRIPTS}/build_physics_readiness.py" \
    --pipeline "${OUTPUT}" \
    --contract "${CONTRACT}" \
    --inputs "${ENGINEERING_INPUTS}" \
    --output "${OUTPUT}/reports/physics-readiness.json"
"${PYTHON}" "${SCRIPTS}/verify_outputs.py" "${OUTPUT}"

echo "pipeline complete: ${OUTPUT}"
