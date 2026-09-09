#!/usr/bin/env bash
set -euo pipefail

BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${BENCHMARK_DIR}/../.." && pwd)"
CONTRACT="${BENCHMARK_DIR}/benchmark-contract-f25.json"
GENERATOR="${BENCHMARK_DIR}/generate_cases.py"
ANALYZER="${BENCHMARK_DIR}/analyze_results.py"
IMAGE="ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

if [[ $# -gt 1 ]]; then
    echo "usage: $0 [work/output-directory]" >&2
    exit 2
fi

OUTPUT_ARGUMENT="${1:-work/openfoam-poiseuille-f25}"
if [[ "${OUTPUT_ARGUMENT}" = /* ]]; then
    OUTPUT_DIR="${OUTPUT_ARGUMENT}"
else
    OUTPUT_DIR="${PROJECT_ROOT}/${OUTPUT_ARGUMENT}"
fi
OUTPUT_DIR="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${OUTPUT_DIR}")"

case "${OUTPUT_DIR}/" in
    "${PROJECT_ROOT}/work/"*) ;;
    *)
        echo "La sortie doit rester sous ${PROJECT_ROOT}/work/." >&2
        exit 2
        ;;
esac

if [[ -e "${OUTPUT_DIR}" ]]; then
    echo "La sortie existe déjà; aucun écrasement: ${OUTPUT_DIR}" >&2
    exit 2
fi

command -v docker >/dev/null
command -v python3 >/dev/null
mkdir -p "${OUTPUT_DIR}"

docker image inspect \
    --format '{"image_id":{{json .Id}},"repo_digests":{{json .RepoDigests}},"architecture":{{json .Architecture}},"os":{{json .Os}}}' \
    "${IMAGE}" > "${OUTPUT_DIR}/container-image.json"

for repetition in 1 2; do
    REPEAT_ID="repeat-${repetition}"
    REPEAT_DIR="${OUTPUT_DIR}/${REPEAT_ID}"
    CASES_DIR="${REPEAT_DIR}/cases"

    python3 -B "${GENERATOR}" \
        --contract "${CONTRACT}" \
        --output "${CASES_DIR}" \
        > "${OUTPUT_DIR}/${REPEAT_ID}-generation.json"

    for mesh_id in coarse medium fine; do
        CASE_DIR="${CASES_DIR}/${mesh_id}"
        docker run --rm \
            --platform linux/amd64 \
            --network none \
            --read-only \
            --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
            --user "${HOST_UID}:${HOST_GID}" \
            --pids-limit 128 \
            --cap-drop ALL \
            --security-opt no-new-privileges \
            --mount "type=bind,source=${CASE_DIR},target=/case" \
            --env CASE_PATH=/case \
            --env HOME=/tmp \
            --entrypoint /bin/bash \
            "${IMAGE}" \
            -lc '
                source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
                set -eo pipefail
                blockMesh -case "${CASE_PATH}" > "${CASE_PATH}/log.blockMesh" 2>&1
                checkMesh -case "${CASE_PATH}" -allGeometry -allTopology > "${CASE_PATH}/log.checkMesh" 2>&1
                simpleFoam -case "${CASE_PATH}" > "${CASE_PATH}/log.simpleFoam" 2>&1
                postProcess -case "${CASE_PATH}" -func writeCellCentres -latestTime > "${CASE_PATH}/log.writeCellCentres" 2>&1
            ' \
            > "${REPEAT_DIR}/${mesh_id}-container.log" 2>&1
    done

    python3 -B "${ANALYZER}" analyze \
        --contract "${CONTRACT}" \
        --cases "${CASES_DIR}" \
        --repeat-id "${REPEAT_ID}" \
        --output "${REPEAT_DIR}/metrics.json"
done

python3 -B "${ANALYZER}" aggregate \
    --contract "${CONTRACT}" \
    --repeat-report "${OUTPUT_DIR}/repeat-1/metrics.json" \
    --repeat-report "${OUTPUT_DIR}/repeat-2/metrics.json" \
    --image-metadata "${OUTPUT_DIR}/container-image.json" \
    --output "${OUTPUT_DIR}/report.json"

echo "Preuve F25 locale: ${OUTPUT_DIR}/report.json"
