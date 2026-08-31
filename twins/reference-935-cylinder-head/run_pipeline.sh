#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 SOURCE_OBJ OUTPUT_DIRECTORY" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOURCE="$1"
OUTPUT="$2"
PYTHON="${PYTHON:-python3}"
SCRIPTS="${ROOT}/twins/reference-935-cylinder-head/source"

"${PYTHON}" "${SCRIPTS}/prepare_scan.py" "${SOURCE}" "${OUTPUT}"
LIGHT="${OUTPUT}/derived/head-with-studs-light-300k.ply"
"${PYTHON}" "${SCRIPTS}/segment_hardware.py" "${LIGHT}" "${OUTPUT}/segmented"
"${PYTHON}" "${SCRIPTS}/extract_interfaces.py" "${LIGHT}" "${OUTPUT}/reports/interfaces.json"
"${PYTHON}" "${SCRIPTS}/build_cfd_stubs.py" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cfd"
"${PYTHON}" "${SCRIPTS}/build_interface_proxy.py" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cad"
"${PYTHON}" "${SCRIPTS}/verify_outputs.py" "${OUTPUT}"

echo "pipeline complete: ${OUTPUT}"
