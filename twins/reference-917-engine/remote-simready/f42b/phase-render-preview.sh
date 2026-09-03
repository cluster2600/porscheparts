#!/usr/bin/env bash
# Valide SimReady sans réparation puis produit quatre photos et un film OVRTX.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_common.sh
. "${SCRIPT_DIR}/../_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
FAMILY=""
CONFORM_REPORT=""
PREVIOUS_VALIDATION_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --family) FAMILY="$2"; shift 2 ;;
        --conform-report) CONFORM_REPORT="$2"; shift 2 ;;
        --previous-validation-report) PREVIOUS_VALIDATION_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${FAMILY}" ] || { echo "--family requis" >&2; exit 2; }
[ -n "${CONFORM_REPORT}" ] || { echo "--conform-report requis" >&2; exit 2; }
[ -n "${PREVIOUS_VALIDATION_REPORT}" ] || { echo "--previous-validation-report requis" >&2; exit 2; }

CONTRACT="${PROJECT_ROOT}/twins/reference-917-engine/component-factory-f42b-gpu.json"
CONTRACT_HELPER="${SCRIPT_DIR}/_contract.py"
PHASE_ROOT="${OUTPUT_ROOT}/render-preview/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
FRAMES="${PHASE_ROOT}/turntable-frames"
PHOTOS="${PHASE_ROOT}/photos"
mkdir -p "${FRAMES}" "${PHOTOS}"

PNG="${PHASE_ROOT}/${FAMILY}-simready-preview.png"
PHOTO_FRONT="${PHOTOS}/${FAMILY}-front.png"
PHOTO_RIGHT="${PHOTOS}/${FAMILY}-right.png"
PHOTO_REAR="${PHOTOS}/${FAMILY}-rear.png"
PHOTO_LEFT="${PHOTOS}/${FAMILY}-left.png"
MOVIE="${PHASE_ROOT}/${FAMILY}-simready-turntable.mp4"
CHECKSUM="${PHASE_ROOT}/render-media.sha256"
SIMREADY_REPORT="${PHASE_ROOT}/simready-validate.json"
SIMREADY_MARKDOWN="${PHASE_ROOT}/simready-validate.md"
FINAL_AUDIT="${PHASE_ROOT}/f42b-final-audit.json"
REFERENCE_REPORT="${PHASE_ROOT}/ovrtx-render-service.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/ovrtx-render-service.md"
TURNTABLE_REPORT="${PHASE_ROOT}/ovrtx-turntable.json"
TURNTABLE_MARKDOWN="${PHASE_ROOT}/ovrtx-turntable.md"
FFPROBE_REPORT="${PHASE_ROOT}/turntable-video-ffprobe.json"
ATTESTATION="${PHASE_ROOT}/render-media-attestation.json"
FINAL_REPORT="${PHASE_ROOT}/f42b-family-report.json"
FINAL_MARKDOWN="${PHASE_ROOT}/f42b-family-report.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-render-preview.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-render-preview.log"

phase_init "render-preview" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
for input in "${CONTRACT}" "${CONFORM_REPORT}" "${PREVIOUS_VALIDATION_REPORT}"; do
    phase_add_input "${input}"
done
for output in \
    "${PNG}" "${PHOTO_FRONT}" "${PHOTO_RIGHT}" "${PHOTO_REAR}" \
    "${PHOTO_LEFT}" "${MOVIE}" "${CHECKSUM}"; do
    phase_add_output "${output}"
done
for child in \
    "${SIMREADY_REPORT}" "${SIMREADY_MARKDOWN}" "${FINAL_AUDIT}" \
    "${REFERENCE_REPORT}" "${REFERENCE_MARKDOWN}" \
    "${TURNTABLE_REPORT}" "${TURNTABLE_MARKDOWN}" \
    "${FFPROBE_REPORT}" "${ATTESTATION}" "${FINAL_REPORT}" "${FINAL_MARKDOWN}"; do
    phase_add_child_report "${child}"
done

require_job_control
require_file "${CONTRACT}"
require_file "${CONTRACT_HELPER}"
SOURCE_ASSET="$(${SYSTEM_PYTHON} "${CONTRACT_HELPER}" verify-control \
    --contract "${CONTRACT}" --control "${CONTROL_REPORT}" --family "${FAMILY}" \
    2>>"${PHASE_LOG}")"
require_passed_report "${CONFORM_REPORT}"
ASSET="$(report_output_path "${CONFORM_REPORT}")"
phase_add_input "${SOURCE_ASSET}"
phase_add_input "${ASSET}"
while IFS= read -r upstream; do
    [ -n "${upstream}" ] && phase_add_input "${upstream}"
done < <("${SYSTEM_PYTHON}" "${CONTRACT_HELPER}" verify-validation-chain \
    --latest "${PREVIOUS_VALIDATION_REPORT}" --asset "${ASSET}" 2>>"${PHASE_LOG}")

# Validation seulement: aucun rapport de validation n'est fourni au conformeur,
# aucun second passage et aucune réparation FET004/RB.MB.001 ou FET005/GSP.001.
SIMREADY_REFERENCE="$(require_skill_reference "references/simready-validate/scripts/run.py")"
set +e
run_logged "${USD_PYTHON}" "${SIMREADY_REFERENCE}" "${ASSET}" \
    --profile Prop-Robotics-Physx \
    --profile-version 1.0.0 \
    --foundation-root "${SIMREADY_FOUNDATION_ROOT:-/opt/simready-foundation}" \
    --report "${SIMREADY_REPORT}" \
    --markdown-report "${SIMREADY_MARKDOWN}"
SIMREADY_EXIT_CODE=$?
set -e
require_file "${SIMREADY_REPORT}"
require_file "${SIMREADY_MARKDOWN}"
if ! SIMREADY_STATUS="$(${SYSTEM_PYTHON} "${CONTRACT_HELPER}" classify-nvidia-validation \
    --report "${SIMREADY_REPORT}" --asset "${ASSET}" \
    --validator-skill simready-validate --exit-code "${SIMREADY_EXIT_CODE}" \
    2>>"${PHASE_LOG}")"; then
    phase_block "validation SimReady bloquée, interrompue ou sans findings structurés"
    exit 1
fi

# La conformance et chaque validateur doivent laisser intacte la géométrie F42a
# et respecter le sous-ensemble PhysX statique avant tout rendu.
run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" audit-usd \
    --contract "${CONTRACT}" --family "${FAMILY}" \
    --source-asset "${SOURCE_ASSET}" --asset "${ASSET}" \
    --stage final --report "${FINAL_AUDIT}"
require_passed_report "${FINAL_AUDIT}"
ASSET_SHA256_BEFORE="$(${SYSTEM_PYTHON} - "${ASSET}" <<'PY'
import hashlib
from pathlib import Path
import sys
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"

# Sans --endpoint explicite, OVRTX consomme uniquement le prévol attesté.
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

DISCLOSURE="Visualisation Omniverse - collider statique seulement - aucune simulation ni FEA"
run_logged ffmpeg -y -framerate 8 -start_number 0 \
    -i "${FRAMES}/frame_%03d.png" \
    -vf "drawbox=x=0:y=ih-54:w=iw:h=54:color=black@0.65:t=fill,drawtext=text='${DISCLOSURE}':fontcolor=white:fontsize=20:x=(w-text_w)/2:y=h-38" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "${MOVIE}"
activate_preflight_environment
refresh_budget
timeout --foreground "${PHASE_REMAINING_SECONDS}s" ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,pix_fmt,width,height,nb_frames \
    -show_entries format=duration -of json "${MOVIE}" \
    >"${FFPROBE_REPORT}" 2>>"${PHASE_LOG}"
require_file "${FFPROBE_REPORT}"

"${SYSTEM_PYTHON}" - \
    "${FAMILY}" "${PNG}" "${PHOTO_FRONT}" "${PHOTO_RIGHT}" "${PHOTO_REAR}" \
    "${PHOTO_LEFT}" "${MOVIE}" "${CHECKSUM}" "${ATTESTATION}" \
    "${ASSET}" "${SIMREADY_STATUS}" "${REFERENCE_REPORT}" \
    "${TURNTABLE_REPORT}" "${FFPROBE_REPORT}" "${FRAMES}" \
    "${ASSET_SHA256_BEFORE}" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

(
    family, preview_s, front_s, right_s, rear_s, left_s, movie_s, checksum_s,
    attestation_s, asset_s, validation_status, reference_s, turntable_s,
    ffprobe_s, frames_s, asset_sha256_before,
) = sys.argv[1:]
preview = Path(preview_s).resolve(strict=True)
photos = [Path(value).resolve(strict=True) for value in (front_s, right_s, rear_s, left_s)]
movie = Path(movie_s).resolve(strict=True)
checksum_path = Path(checksum_s).resolve()
attestation_path = Path(attestation_s).resolve()
asset = Path(asset_s).resolve(strict=True)
reference_path = Path(reference_s).resolve(strict=True)
turntable_path = Path(turntable_s).resolve(strict=True)
ffprobe_path = Path(ffprobe_s).resolve(strict=True)
frames_root = Path(frames_s).resolve(strict=True)

def load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"rapport objet attendu: {path.name}")
    return payload

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

if digest(asset) != asset_sha256_before:
    raise SystemExit("le rendu OVRTX a muté l'USD source")

reference = load(reference_path)
if reference.get("passed") is not True or reference.get("asset_path") != str(asset):
    raise SystemExit("rendu principal OVRTX non lié à l'USD final")
if reference.get("output_image_path") != str(preview) or reference.get("generated_files") != [str(preview)]:
    raise SystemExit("sortie du rendu principal OVRTX incohérente")

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

for photo, frame_index in zip(photos, (0, 6, 12, 18), strict=True):
    if digest(photo) != digest(expected_frames[frame_index]):
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

media_paths = [preview, *photos, movie]
media = [
    {
        "filename": path.name,
        "kind": "film" if path == movie else ("preview" if path == preview else "photo"),
        "sha256": digest(path),
        "size_bytes": path.stat().st_size,
    }
    for path in media_paths
]
checksum_path.write_text(
    "".join(f"{item['sha256']}  {item['filename']}\n" for item in media),
    encoding="utf-8",
)
attestation = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "workflow_profile": "f42b-six-usd-v1",
    "family_id": family,
    "claim_scope": "omniverse_visual_diagnostic_only",
    "source_asset": {"filename": asset.name, "sha256": digest(asset), "size_bytes": asset.stat().st_size},
    "media": media,
    "turntable_frame_count": 24,
    "photos_from_frame_indices": [0, 6, 12, 18],
    "checksum_manifest": {"filename": checksum_path.name, "sha256": digest(checksum_path)},
    "simready_validation_status": validation_status,
    "simready_auto_repair_attempted": False,
    "source_asset_mutated_by_render": False,
    "static_collision_diagnostic_only": True,
    "simulation_executed": False,
    "simulation_validated": False,
    "fea_executed": False,
    "fea_validated": False,
    "manufacturing_authorized": False,
    "disclosure": "Visualisation Omniverse: collider statique seulement; aucune simulation ni FEA.",
    "created_at": datetime.now(timezone.utc).isoformat(),
}
attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

run_logged "${SYSTEM_PYTHON}" "${CONTRACT_HELPER}" final-report \
    --contract "${CONTRACT}" --family "${FAMILY}" \
    --source-asset "${SOURCE_ASSET}" --asset "${ASSET}" \
    --audit-report "${FINAL_AUDIT}" --simready-report "${SIMREADY_REPORT}" \
    --render-report "${REFERENCE_REPORT}" --turntable-report "${TURNTABLE_REPORT}" \
    --media-attestation "${ATTESTATION}" \
    --report "${FINAL_REPORT}" --markdown-report "${FINAL_MARKDOWN}"
require_file "${FINAL_REPORT}"
require_file "${FINAL_MARKDOWN}"
phase_pass "photos et film OVRTX attestés; validation SimReady sans auto-réparation: ${SIMREADY_STATUS}; aucune simulation ni FEA"
