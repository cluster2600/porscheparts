#!/usr/bin/env bash
# Produit des photos et un film OVRTX de l'USD final, sans revendication physique.
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
FRAMES="${PHASE_ROOT}/turntable-frames"
PHOTOS="${PHASE_ROOT}/photos"
mkdir -p "${PHASE_ROOT}" "${FRAMES}" "${PHOTOS}"

PNG="${PHASE_ROOT}/917-engine-simready-preview.png"
PHOTO_FRONT="${PHOTOS}/917-engine-front.png"
PHOTO_RIGHT="${PHOTOS}/917-engine-right.png"
PHOTO_REAR="${PHOTOS}/917-engine-rear.png"
PHOTO_LEFT="${PHOTOS}/917-engine-left.png"
MOVIE="${PHASE_ROOT}/917-engine-simready-turntable.mp4"
CHECKSUM="${PHASE_ROOT}/render-media.sha256"
REFERENCE_REPORT="${PHASE_ROOT}/ovrtx-render-service.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/ovrtx-render-service.md"
TURNTABLE_REPORT="${PHASE_ROOT}/ovrtx-turntable.json"
TURNTABLE_MARKDOWN="${PHASE_ROOT}/ovrtx-turntable.md"
FFPROBE_REPORT="${PHASE_ROOT}/turntable-video-ffprobe.json"
ATTESTATION="${PHASE_ROOT}/render-media-attestation.json"
VIDEO_STATUS="${PHASE_ROOT}/video-f7-status.json"
FINAL_REPORT="${PHASE_ROOT}/omniverse-cad-to-simready-report.json"
FINAL_MARKDOWN="${PHASE_ROOT}/omniverse-cad-to-simready-report.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-render-preview.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-render-preview.log"
phase_init "render-preview" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${CONFORM_REPORT}"
phase_add_input "${PREVIOUS_VALIDATION_REPORT}"
for output in \
    "${PNG}" "${PHOTO_FRONT}" "${PHOTO_RIGHT}" "${PHOTO_REAR}" \
    "${PHOTO_LEFT}" "${MOVIE}" "${CHECKSUM}"; do
    phase_add_output "${output}"
done
for child in \
    "${REFERENCE_REPORT}" "${REFERENCE_MARKDOWN}" \
    "${TURNTABLE_REPORT}" "${TURNTABLE_MARKDOWN}" \
    "${FFPROBE_REPORT}" "${ATTESTATION}" "${VIDEO_STATUS}" \
    "${FINAL_REPORT}" "${FINAL_MARKDOWN}"; do
    phase_add_child_report "${child}"
done
require_job_control
require_passed_report "${CONFORM_REPORT}"
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
if report.get("passed") is not (status == "passed"):
    raise SystemExit("statut SimReady et booléen passed incohérents")
print(status)
PY
)"
ASSET="$(report_output_path "${PREVIOUS_VALIDATION_REPORT}")"
phase_add_input "${ASSET}"
F10_REPORT="${OUTPUT_ROOT}/f10/${RUN_ID}/phase-f10.json"
ASSET_CONTEXT_REPORT="$(${SYSTEM_PYTHON} - "${F10_REPORT}" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve()
if not path.is_file():
    raise SystemExit("rapport F10 absent")
report = json.loads(path.read_text(encoding="utf-8"))
matches = [
    Path(value).resolve()
    for value in report.get("child_reports", [])
    if Path(str(value)).name == "asset-context.json"
]
if len(matches) != 1 or not matches[0].is_file():
    raise SystemExit("contexte d'actif F10 absent ou ambigu")
print(matches[0])
PY
)"
phase_add_input "${F10_REPORT}"
phase_add_input "${ASSET_CONTEXT_REPORT}"

# L'absence de --endpoint est volontaire : le skill doit consommer le manifeste
# de prévol attesté et refuse ainsi tout endpoint explicite hors contrat.
REFERENCE="$(require_skill_reference "references/ovrtx-render-service/scripts/run.py")"
TURNTABLE_REFERENCE="$(require_skill_reference "references/ovrtx-render-service/scripts/turntable.py")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${ASSET}" "${PNG}" \
    --width 1024 --height 1024 \
    --fit-margin 1.2 --focal-length 50 --elevation 0.34 \
    --fail-on-uniform \
    --request-timeout 240 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
require_file "${PNG}"

run_logged "${USD_PYTHON}" "${TURNTABLE_REFERENCE}" "${ASSET}" "${FRAMES}" \
    --frames 24 --width 1280 --height 720 \
    --fit-margin 1.12 --focal-length 50 --elevation 0.34 \
    --request-timeout 240 \
    --report "${TURNTABLE_REPORT}" \
    --markdown-report "${TURNTABLE_MARKDOWN}"
require_passed_report "${TURNTABLE_REPORT}"

cp -- "${FRAMES}/frame_000.png" "${PHOTO_FRONT}"
cp -- "${FRAMES}/frame_006.png" "${PHOTO_RIGHT}"
cp -- "${FRAMES}/frame_012.png" "${PHOTO_REAR}"
cp -- "${FRAMES}/frame_018.png" "${PHOTO_LEFT}"

DISCLOSURE="Visualisation Omniverse - aucune combustion, charge, pression ou puissance simulee"
run_logged ffmpeg -y -framerate 8 -start_number 0 \
    -i "${FRAMES}/frame_%03d.png" \
    -vf "drawbox=x=0:y=h-54:w=w:h=54:color=black@0.65:t=fill,drawtext=text='${DISCLOSURE}':fontcolor=white:fontsize=20:x=(w-text_w)/2:y=h-38" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "${MOVIE}"
activate_preflight_environment
refresh_budget
timeout --foreground "${PHASE_REMAINING_SECONDS}s" ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,pix_fmt,width,height,nb_frames \
    -show_entries format=duration -of json "${MOVIE}" \
    >"${FFPROBE_REPORT}" 2>>"${PHASE_LOG}"
require_file "${FFPROBE_REPORT}"

"${SYSTEM_PYTHON}" - \
    "${PNG}" "${PHOTO_FRONT}" "${PHOTO_RIGHT}" "${PHOTO_REAR}" "${PHOTO_LEFT}" \
    "${MOVIE}" "${CHECKSUM}" "${ATTESTATION}" "${VIDEO_STATUS}" \
    "${ASSET}" "${VALIDATION_STATUS}" "${REFERENCE_REPORT}" \
    "${TURNTABLE_REPORT}" "${FFPROBE_REPORT}" "${FRAMES}" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

(
    preview_s, front_s, right_s, rear_s, left_s, movie_s, checksum_s,
    attestation_s, video_s, asset_s, validation_status, reference_s,
    turntable_s, ffprobe_s, frames_s,
) = sys.argv[1:]
preview = Path(preview_s).resolve(strict=True)
photos = [Path(value).resolve(strict=True) for value in (front_s, right_s, rear_s, left_s)]
movie = Path(movie_s).resolve(strict=True)
checksum_path = Path(checksum_s).resolve()
attestation_path = Path(attestation_s).resolve()
video_path = Path(video_s).resolve()
asset = Path(asset_s).resolve(strict=True)
reference_path = Path(reference_s).resolve(strict=True)
turntable_path = Path(turntable_s).resolve(strict=True)
ffprobe_path = Path(ffprobe_s).resolve(strict=True)
frames_root = Path(frames_s).resolve(strict=True)

def load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"rapport objet attendu: {path}")
    return payload

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

reference = load(reference_path)
if reference.get("passed") is not True:
    raise SystemExit("rendu principal OVRTX non validé")
if reference.get("asset_path") != str(asset):
    raise SystemExit("rendu principal appliqué à un autre USD")
if reference.get("output_image_path") != str(preview):
    raise SystemExit("rapport OVRTX rattaché à une autre image")
if reference.get("generated_files") != [str(preview)]:
    raise SystemExit("generated_files OVRTX incohérent")

turntable = load(turntable_path)
expected_frames = [(frames_root / f"frame_{index:03d}.png").resolve(strict=True) for index in range(24)]
if (
    turntable.get("passed") is not True
    or turntable.get("asset_path") != str(asset)
    or turntable.get("frames_requested") != 24
    or turntable.get("frames_rendered") != 24
    or turntable.get("generated_files") != [str(path) for path in expected_frames]
):
    raise SystemExit("rapport turntable OVRTX incohérent")
frame_reports = turntable.get("frame_reports")
if not isinstance(frame_reports, list) or len(frame_reports) != 24:
    raise SystemExit("rapports de frames turntable incomplets")
for index, (frame_report, expected) in enumerate(zip(frame_reports, expected_frames, strict=True)):
    if (
        not isinstance(frame_report, dict)
        or frame_report.get("frame") != index
        or frame_report.get("passed") is not True
        or Path(str(frame_report.get("output_image_path", ""))).resolve() != expected
        or frame_report.get("pixel_inspection", {}).get("uniform") is not False
    ):
        raise SystemExit(f"frame OVRTX {index} non attestée")

source_indices = (0, 6, 12, 18)
for photo, source_index in zip(photos, source_indices, strict=True):
    if digest(photo) != digest(expected_frames[source_index]):
        raise SystemExit("photo de contrôle différente de sa frame OVRTX")

probe = load(ffprobe_path)
streams = probe.get("streams")
if not isinstance(streams, list) or len(streams) != 1:
    raise SystemExit("stream vidéo unique absent")
stream = streams[0]
try:
    duration = float(probe.get("format", {}).get("duration", 0))
except (TypeError, ValueError) as exc:
    raise SystemExit("durée vidéo invalide") from exc
if (
    stream.get("codec_name") != "h264"
    or stream.get("pix_fmt") != "yuv420p"
    or stream.get("width") != 1280
    or stream.get("height") != 720
    or duration <= 0
    or movie.stat().st_size <= 0
):
    raise SystemExit("film MP4 hors contrat")

media = [preview, *photos, movie]
digests = {str(path): digest(path) for path in media}
checksum_path.write_text(
    "".join(f"{digests[str(path)]}  {path.name}\n" for path in media),
    encoding="utf-8",
)
attestation = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "claim_scope": "omniverse_visual_diagnostic_only",
    "source_asset_path": str(asset),
    "preview_path": str(preview),
    "photo_paths": [str(path) for path in photos],
    "diagnostic_video_path": str(movie),
    "turntable_frame_paths": [str(path) for path in expected_frames],
    "media_sha256": digests,
    "checksum_manifest_path": str(checksum_path),
    "ovrtx_render_report": str(reference_path),
    "ovrtx_turntable_report": str(turntable_path),
    "ffprobe_report": str(ffprobe_path),
    "upstream_simready_validation_status": validation_status,
    "simulation_validated": False,
    "physical_simulation_validated": False,
    "dyno_validated": False,
    "performance_1600hp_validated": False,
    "disclosure": "Visualisation Omniverse: aucune combustion, charge, pression ou puissance simulée.",
    "created_at": datetime.now(timezone.utc).isoformat(),
}
attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
video = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "phase": "turntable-diagnostic-film",
    "output_video_path": str(movie),
    "source_asset_path": str(asset),
    "disclosure_embedded": True,
    "kinematic_f7_engine_motion_status": "blocked_not_part_of_this_simready_run",
    "physical_simulation_claim_authorized": False,
    "reason": "ce MP4 fait tourner la caméra autour de l'USD final; il ne prouve pas un moteur en fonctionnement",
}
video_path.write_text(json.dumps(video, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

FINAL_HELPER="${SCRIPT_DIR}/_final_workflow_report.py"
require_file "${FINAL_HELPER}"
run_logged "${SYSTEM_PYTHON}" "${FINAL_HELPER}" \
    --output-root "${OUTPUT_ROOT}" \
    --job-id "$(${SYSTEM_PYTHON} - "${CONTROL_REPORT}" <<'PY'
import json
from pathlib import Path
import sys
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["job_id"])
PY
)" \
    --run-id "${RUN_ID}" \
    --asset-context-report "${ASSET_CONTEXT_REPORT}" \
    --render-reference-report "${REFERENCE_REPORT}" \
    --turntable-report "${TURNTABLE_REPORT}" \
    --render-attestation "${ATTESTATION}" \
    --preview "${PNG}" \
    --report "${FINAL_REPORT}" \
    --markdown-report "${FINAL_MARKDOWN}"
require_file "${FINAL_REPORT}"
require_file "${FINAL_MARKDOWN}"
phase_pass "photos et film OVRTX diagnostiques produits depuis l'USD final; statut SimReady amont: ${VALIDATION_STATUS}; mouvement moteur F7 distinct non revendiqué"
