#!/usr/bin/env bash
# Produit un aperçu PNG OVRTX après la dernière validation, sans revendiquer F7.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
CONFORM_REPORT=""
PREVIOUS_VALIDATION_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --conform-report) CONFORM_REPORT="$2"; shift 2 ;;
        --previous-validation-report) PREVIOUS_VALIDATION_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${CONFORM_REPORT}" ] || { echo "--conform-report requis" >&2; exit 2; }
[ -n "${PREVIOUS_VALIDATION_REPORT}" ] || { echo "--previous-validation-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/render-preview/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}"
PNG="${PHASE_ROOT}/917-engine-simready-preview.png"
CHECKSUM="${PNG}.sha256"
REFERENCE_REPORT="${PHASE_ROOT}/ovrtx-render-service.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/ovrtx-render-service.md"
ATTESTATION="${PHASE_ROOT}/render-preview-attestation.json"
VIDEO_STATUS="${PHASE_ROOT}/video-f7-status.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-render-preview.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-render-preview.log"
phase_init "render-preview" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${CONFORM_REPORT}"
phase_add_input "${PREVIOUS_VALIDATION_REPORT}"
phase_add_output "${PNG}"
phase_add_output "${CHECKSUM}"
phase_add_child_report "${REFERENCE_REPORT}"
phase_add_child_report "${ATTESTATION}"
phase_add_child_report "${VIDEO_STATUS}"
require_job_control
require_passed_report "${CONFORM_REPORT}"
ASSET="$(report_output_path "${CONFORM_REPORT}")"
phase_add_input "${ASSET}"
VALIDATION_STATUS="$(${SYSTEM_PYTHON} - "${PREVIOUS_VALIDATION_REPORT}" <<'PY'
import json
from pathlib import Path
import sys
path = Path(sys.argv[1]).resolve()
if not path.is_file():
    raise SystemExit("rapport SimReady final absent")
report = json.loads(path.read_text(encoding="utf-8"))
if report.get("phase") != "validate-simready":
    raise SystemExit("la phase précédente doit être validate-simready")
status = report.get("status")
if status not in {"passed", "needs_rerun"}:
    raise SystemExit("validation SimReady non terminée")
print(status)
PY
)"
REFERENCE="$(require_skill_reference "references/ovrtx-render-service/scripts/run.py")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${ASSET}" "${PNG}" \
    --endpoint http://127.0.0.1:8001 \
    --width 1024 --height 1024 \
    --fit-margin 1.2 --focal-length 50 --elevation 0.34 \
    --fail-on-uniform \
    --request-timeout 180 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
require_file "${PNG}"
"${SYSTEM_PYTHON}" - "${PNG}" "${CHECKSUM}" "${ATTESTATION}" "${VIDEO_STATUS}" "${ASSET}" "${VALIDATION_STATUS}" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

png = Path(sys.argv[1])
checksum_path = Path(sys.argv[2])
attestation_path = Path(sys.argv[3])
video_path = Path(sys.argv[4])
asset = Path(sys.argv[5])
validation_status = sys.argv[6]
digest = hashlib.sha256(png.read_bytes()).hexdigest()
checksum_path.write_text(f"{digest}  {png.name}\n", encoding="utf-8")
attestation = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "claim_scope": "diagnostic_preview_only",
    "output_image_path": str(png.resolve()),
    "output_image_sha256": digest,
    "source_asset_path": str(asset.resolve()),
    "upstream_simready_validation_status": validation_status,
    # Ce rapport atteste uniquement le rendu. La validation globale est
    # recalculée lors de la récupération à partir des quatre validateurs.
    "simulation_validated": False,
    "validation_claim_source": "retrieval-report-after-all-four-validators",
    "fixed_render_parameters": {
        "renderer": "OVRTX", "width": 1024, "height": 1024,
        "fit_margin": 1.2, "focal_length": 50.0, "elevation": 0.34,
        "fail_on_uniform": True,
    },
    "created_at": datetime.now(timezone.utc).isoformat(),
}
attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
video = {
    "schema_version": "1.0.0",
    "status": "blocked",
    "passed": False,
    "phase": "f7-video",
    "reason": "une vidéo F7 temporelle est une phase distincte; ce job ne produit qu'un aperçu OVRTX statique",
    "still_preview_path": str(png.resolve()),
}
video_path.write_text(json.dumps(video, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
phase_pass "aperçu OVRTX diagnostique produit après validations; statut SimReady amont: ${VALIDATION_STATUS}; vidéo F7 distincte bloquée"
