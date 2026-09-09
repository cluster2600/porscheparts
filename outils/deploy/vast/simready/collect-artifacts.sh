#!/usr/bin/env bash
# Récupère uniquement le répertoire de résultats du job, puis le vérifie localement.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

INSTANCE_ID=""
EXPECTED_IMAGE=""
JOB_ID=""
MAX_DPH="${MAX_ACTUAL_DPH}"
DESTINATION_ROOT=""
CONTROL_ROOT=""
KNOWN_HOSTS=""
WORKFLOW_PROFILE="legacy-f10"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --job-id) JOB_ID="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --destination-root) DESTINATION_ROOT="$2"; shift 2 ;;
        --control-root) CONTROL_ROOT="$2"; shift 2 ;;
        --known-hosts) KNOWN_HOSTS="$2"; shift 2 ;;
        --workflow-profile) WORKFLOW_PROFILE="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${JOB_ID}" ] || controller_die "paramètres requis absents"
validate_controller_id "${JOB_ID}"
validate_pinned_image "${EXPECTED_IMAGE}"
case "${WORKFLOW_PROFILE}" in
    legacy-f10) RETRIEVAL_SUMMARIZER="${SCRIPT_DIR}/_summarize_retrieval.py" ;;
    f42b-six-usd-v1)
        RETRIEVAL_SUMMARIZER="${SCRIPT_DIR}/_summarize_f42b_retrieval.py"
        [ -n "${DESTINATION_ROOT}" ] \
            || controller_die "--destination-root absolu hors de toute worktree Git requis pour F42b"
        PRIVATE_DESTINATION_HELPER="${SCRIPT_DIR}/_private_destination.py"
        [ -f "${PRIVATE_DESTINATION_HELPER}" ] || controller_die "helper de destination privée F42b absent"
        DESTINATION_ROOT="$(python3 "${PRIVATE_DESTINATION_HELPER}" prepare \
            --destination "${DESTINATION_ROOT}" --repository-root "${REPOSITORY_ROOT}")" \
            || controller_die "destination privée F42b refusée"
        ;;
    *) controller_die "--workflow-profile doit être legacy-f10 ou f42b-six-usd-v1" ;;
esac
CONTROL_ROOT="${CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/controller/${JOB_ID}}"
DESTINATION_ROOT="${DESTINATION_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/results}"
KNOWN_HOSTS="${KNOWN_HOSTS:-${CONTROL_ROOT}/known_hosts}"
mkdir -p "${CONTROL_ROOT}" "${DESTINATION_ROOT}"
GUARD_REPORT="${CONTROL_ROOT}/instance-guard-collect.json"
# La récupération de secours ne doit jamais être empêchée par un dépassement
# déjà subi. L'identité, le label, le digest, l'état et l'unique GPU restent
# obligatoires.
# GUARD_SKIP_COST_CAP est lu par guard_and_prepare_ssh dans la bibliothèque sourcée.
# shellcheck disable=SC2034
GUARD_SKIP_COST_CAP=1
# shellcheck disable=SC2034
GUARD_SKIP_CAPABILITY_FLOOR=1
guard_and_prepare_ssh "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${GUARD_REPORT}" "${KNOWN_HOSTS}" running

ARCHIVE="${DESTINATION_ROOT}/${JOB_ID}.tar.gz"
EXTRACTED="${DESTINATION_ROOT}/${JOB_ID}"
[ ! -e "${ARCHIVE}" ] && [ ! -e "${EXTRACTED}" ] || controller_die "destination de résultats déjà existante"
PARTIAL="${ARCHIVE}.partial"
trap 'rm -f "${PARTIAL}"' EXIT
if [ "${WORKFLOW_PROFILE}" = "f42b-six-usd-v1" ]; then
    controller_ssh "test -d '/workspace/results/${JOB_ID}' && tar -C /workspace/results -czf - '${JOB_ID}'" \
        | python3 "${PRIVATE_DESTINATION_HELPER}" copy-stdin-exclusive --path "${PARTIAL}"
    python3 "${PRIVATE_DESTINATION_HELPER}" extract-archive \
        --archive "${PARTIAL}" --destination "${DESTINATION_ROOT}" --job-id "${JOB_ID}" >/dev/null
else
    controller_ssh "test -d '/workspace/results/${JOB_ID}' && tar -C /workspace/results -czf - '${JOB_ID}'" >"${PARTIAL}"
    tar -tzf "${PARTIAL}" >/dev/null
    python3 - "${PARTIAL}" "${JOB_ID}" <<'PY'
import tarfile
from pathlib import PurePosixPath
import sys

archive, job_id = sys.argv[1:]
with tarfile.open(archive, "r:gz") as handle:
    members = handle.getmembers()
    if not members:
        raise SystemExit("archive vide")
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != job_id:
            raise SystemExit(f"membre d'archive interdit: {member.name}")
        if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
            raise SystemExit(f"type de membre interdit dans les résultats: {member.name}")
PY
    tar -xzf "${PARTIAL}" -C "${DESTINATION_ROOT}"
fi
mv "${PARTIAL}" "${ARCHIVE}"
trap - EXIT

RETRIEVAL_REPORT="${CONTROL_ROOT}/retrieval-report.json"
python3 "${RETRIEVAL_SUMMARIZER}" \
    --root "${EXTRACTED}" \
    --archive "${ARCHIVE}" \
    --output "${RETRIEVAL_REPORT}" \
    --job-id "${JOB_ID}" \
    --instance-id "${INSTANCE_ID}" \
    --expected-image "${EXPECTED_IMAGE}" >/dev/null
printf '%s\n' "${RETRIEVAL_REPORT}"
