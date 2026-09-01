#!/usr/bin/env bash
# Détruit l'instance seulement après récupération vérifiée et confirmation exacte du job.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

INSTANCE_ID=""
EXPECTED_IMAGE=""
JOB_ID=""
CONFIRM_JOB_ID=""
CONFIRM_INSTANCE_ID=""
CONFIRM_DIGEST=""
CONFIRM_NO_RETRIEVAL=""
RETRIEVAL_REPORT=""
MAX_DPH="${MAX_ACTUAL_DPH}"
CONTROL_ROOT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --job-id) JOB_ID="$2"; shift 2 ;;
        --confirm-job-id) CONFIRM_JOB_ID="$2"; shift 2 ;;
        --confirm-instance-id) CONFIRM_INSTANCE_ID="$2"; shift 2 ;;
        --confirm-digest) CONFIRM_DIGEST="$2"; shift 2 ;;
        --confirm-no-retrieval) CONFIRM_NO_RETRIEVAL="$2"; shift 2 ;;
        --retrieval-report) RETRIEVAL_REPORT="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --control-root) CONTROL_ROOT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${JOB_ID}" ] \
    || controller_die "paramètres requis absents"
[ "${CONFIRM_JOB_ID}" = "${JOB_ID}" ] || controller_die "confirmation du job différente"
[ "${CONFIRM_INSTANCE_ID}" = "${INSTANCE_ID}" ] || controller_die "confirmation de l'instance différente"
[ "${CONFIRM_DIGEST}" = "${EXPECTED_IMAGE}" ] || controller_die "confirmation du digest différente"
validate_controller_id "${JOB_ID}"
validate_pinned_image "${EXPECTED_IMAGE}"
require_vast_wrapper
CONTROL_ROOT="${CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/controller/${JOB_ID}}"
mkdir -p "${CONTROL_ROOT}"
RETRIEVAL_PROOF="${CONTROL_ROOT}/retrieval-proof-for-destroy.json"
if [ -n "${RETRIEVAL_REPORT}" ]; then
python3 - "${RETRIEVAL_REPORT}" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${RETRIEVAL_PROOF}" "${SCRIPT_DIR}/_summarize_retrieval.py" <<'PY'
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("job_id") != sys.argv[2] or report.get("instance_id") != int(sys.argv[3]) or report.get("expected_image") != sys.argv[4]:
    raise SystemExit("rapport de récupération différent du job/instance/digest")
if report.get("retrieval_attempted") is not True or report.get("artifact_archive_verified") is not True:
    raise SystemExit("archive de récupération non vérifiée")
archive = Path(report.get("archive_path", ""))
if not archive.is_file():
    raise SystemExit("archive récupérée absente")
digest = hashlib.sha256()
with archive.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != report.get("archive_sha256"):
    raise SystemExit("checksum de l'archive récupérée différent")
derived_simulation_validated = False
if report.get("simulation_validated") is True:
    try:
        spec = importlib.util.spec_from_file_location("vast_retrieval", sys.argv[6])
        if spec is None or spec.loader is None:
            raise RuntimeError("résumeur indisponible")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        recomputed = module.summarize(
            Path(report["extracted_root"]), archive, sys.argv[2], int(sys.argv[3]), sys.argv[4]
        )
        derived_simulation_validated = recomputed.get("simulation_validated") is True
    except Exception:
        # Le cleanup reste autorisé, mais la revendication est rabattue à faux.
        derived_simulation_validated = False
proof = {
    "retrieval_waived": False,
    "retrieval_report": str(Path(sys.argv[1]).resolve()),
    "artifact_archive_verified": True,
    "retrieval_complete": bool(report.get("retrieval_complete")),
    "simulation_validated": bool(derived_simulation_validated),
}
Path(sys.argv[5]).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
else
    EXPECTED_WAIVER="NO-RETRIEVAL:${JOB_ID}:${INSTANCE_ID}:${EXPECTED_IMAGE}"
    [ "${CONFIRM_NO_RETRIEVAL}" = "${EXPECTED_WAIVER}" ] \
        || controller_die "rapport de récupération absent; confirmation NO-RETRIEVAL exacte requise"
    python3 - "${RETRIEVAL_PROOF}" <<'PY'
import json
from pathlib import Path
import sys
proof = {
    "retrieval_waived": True,
    "retrieval_report": None,
    "artifact_archive_verified": False,
    "retrieval_complete": False,
    "simulation_validated": False,
    "reason": "récupération impossible ou aucun artefact distant disponible; cleanup explicitement confirmé",
}
Path(sys.argv[1]).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
fi
GUARD_REPORT="${CONTROL_ROOT}/instance-guard-destroy.json"
python3 "${INSTANCE_GUARD}" \
    --wrapper "${OPENBAO_VASTAI_BIN}" \
    --instance-id "${INSTANCE_ID}" \
    --expected-image "${EXPECTED_IMAGE}" \
    --expected-label "${EXPECTED_LABEL}" \
    --max-actual-dph "${MAX_DPH}" \
    --skip-cost-cap \
    --allowed-status running \
    --allowed-status stopped \
    --allowed-status loading \
    --allowed-status created \
    --allowed-status exited \
    --report "${GUARD_REPORT}" >/dev/null
DESTROY_OUTPUT="${CONTROL_ROOT}/destroy-wrapper-output.json"
"${OPENBAO_VASTAI_BIN}" destroy "${INSTANCE_ID}" --confirm >"${DESTROY_OUTPUT}"
python3 - "${DESTROY_OUTPUT}" "${CONTROL_ROOT}/destroy-report.json" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${RETRIEVAL_PROOF}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
wrapper = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if wrapper.get("instance_id") != int(sys.argv[4]) or wrapper.get("destroyed") is not True:
    raise SystemExit("le wrapper n'a pas confirmé la destruction")
retrieval = json.loads(Path(sys.argv[6]).read_text(encoding="utf-8"))
payload = {
    "schema_version": "1.0.0", "status": "passed", "passed": True,
    "job_id": sys.argv[3], "instance_id": int(sys.argv[4]), "expected_image": sys.argv[5],
    "retrieval_waived": retrieval["retrieval_waived"],
    "artifact_archive_verified": retrieval["artifact_archive_verified"],
    "retrieval_complete": retrieval["retrieval_complete"],
    "simulation_validated": retrieval["simulation_validated"],
    "destroyed_at": datetime.now(timezone.utc).isoformat(),
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
printf '%s\n' "${CONTROL_ROOT}/destroy-report.json"
