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
SCRIPTS="${ROOT}/twins/reference-917-engine/source"

"${PYTHON}" "${SCRIPTS}/prepare_scan.py" "${SOURCE}" "${OUTPUT}"
LIGHT="${OUTPUT}/derived/917-engine-light-600k.ply"
DISPLAY_SOURCE="${OUTPUT}/components/component-01-main_engine_assembly.ply"
"${PYTHON}" "${SCRIPTS}/analyze_boundaries.py" "${LIGHT}" "${OUTPUT}/reports/boundaries.json"
"${PYTHON}" "${SCRIPTS}/extract_interfaces.py" "${LIGHT}" "${OUTPUT}/reports/interfaces.json"
"${PYTHON}" "${SCRIPTS}/segment_engine.py" "${LIGHT}" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/segmented"
"${PYTHON}" "${SCRIPTS}/build_interface_proxy.py" "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cad"

BLENDER="${BLENDER:-blender}"
"${BLENDER}" --background --python-exit-code 1 --python "${SCRIPTS}/voxel_remesh_display.py" -- \
  "${DISPLAY_SOURCE}" "${OUTPUT}/print/917-engine-display-master.stl" 2.0
"${BLENDER}" --background --python-exit-code 1 --python "${SCRIPTS}/voxel_remesh_display.py" -- \
  "${DISPLAY_SOURCE}" "${OUTPUT}/print/917-engine-display-1-4-raw.stl" 0.8 0.25
"${PYTHON}" "${SCRIPTS}/clean_print_model.py" \
  "${OUTPUT}/print/917-engine-display-1-4-raw.stl" \
  "${OUTPUT}/print/917-engine-display-only-scale-1-4.stl" \
  --scale-label 1:4 --voxel-size-mm 0.8 \
  --interfaces "${OUTPUT}/reports/interfaces.json" --source-scale 0.25
"${BLENDER}" --background --python-exit-code 1 --python "${SCRIPTS}/voxel_remesh_display.py" -- \
  "${DISPLAY_SOURCE}" "${OUTPUT}/print/917-engine-display-1-8-raw.stl" 0.8 0.125
"${PYTHON}" "${SCRIPTS}/clean_print_model.py" \
  "${OUTPUT}/print/917-engine-display-1-8-raw.stl" \
  "${OUTPUT}/print/917-engine-display-only-scale-1-8.stl" \
  --scale-label 1:8 --voxel-size-mm 0.8 \
  --interfaces "${OUTPUT}/reports/interfaces.json" --source-scale 0.125

"${PYTHON}" "${SCRIPTS}/prepare_external_cfd.py" \
  "${OUTPUT}/print/917-engine-display-master.stl" \
  "${OUTPUT}/reports/interfaces.json" "${OUTPUT}/cfd/external-cooling"
"${PYTHON}" "${SCRIPTS}/verify_outputs.py" "${OUTPUT}"

echo "917 F0/F1 pipeline complete: ${OUTPUT}"
