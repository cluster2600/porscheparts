#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACT="${PROJECT_ROOT}/twins/reference-917-engine/integrated-virtual-validation-f33.json"
PYTHON_RUNNER="${PROJECT_ROOT}/twins/reference-917-engine/source/run_integrated_virtual_validation_f33.py"
IMAGE="${F33_CAE_IMAGE:-3dprinting993-cae-integrated-f33:dev}"
OUTPUT_ARGUMENT="${1:-work/917-integrated-virtual-f33}"

if [[ "${OUTPUT_ARGUMENT}" = /* ]]; then
    OUTPUT="${OUTPUT_ARGUMENT}"
else
    OUTPUT="${PROJECT_ROOT}/${OUTPUT_ARGUMENT}"
fi
OUTPUT="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${OUTPUT}")"
case "${OUTPUT}/" in
    "${PROJECT_ROOT}/work/"*) ;;
    *) echo "La sortie F33 doit rester sous work/." >&2; exit 2 ;;
esac
if [[ -e "${OUTPUT}" ]]; then
    echo "La sortie existe déjà; aucun écrasement: ${OUTPUT}" >&2
    exit 2
fi

python3 -B "${PYTHON_RUNNER}" --contract "${CONTRACT}" --output "${OUTPUT}" --stage prepare
docker image inspect --format '{"image_id":{{json .Id}},"repo_digests":{{json .RepoDigests}},"architecture":{{json .Architecture}},"os":{{json .Os}}}' "${IMAGE}" > "${OUTPUT}/openfoam/container-image.json"

docker run --rm \
    --network none \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=128m \
    --user "$(id -u):$(id -g)" \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --mount "type=bind,source=${PROJECT_ROOT},target=/workspace" \
    --entrypoint python3 \
    "${IMAGE}" \
    /workspace/twins/reference-917-engine/source/build_functional_head_solver_cad_f33.py \
    --contract /workspace/twins/reference-917-engine/integrated-virtual-validation-f33.json \
    --design-study /workspace/twins/reference-917-engine/evidence/f29/design-study.json \
    --output /workspace/${OUTPUT#"${PROJECT_ROOT}/"}/functional-cad

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
for architecture in 2v 4v; do
    for mesh_id in coarse medium fine; do
        case_dir="${OUTPUT}/openfoam/${architecture}/${mesh_id}"
        set +e
        docker run --rm \
            --network none \
            --read-only \
            --tmpfs /tmp:rw,noexec,nosuid,nodev,size=128m \
            --user "${HOST_UID}:${HOST_GID}" \
            --pids-limit 256 \
            --cap-drop ALL \
            --security-opt no-new-privileges \
            --mount "type=bind,source=${case_dir},target=/case" \
            --env HOME=/tmp \
            --entrypoint /bin/bash \
            "${IMAGE}" \
            -lc 'source /opt/openfoam13/etc/bashrc >/dev/null 2>&1; set -eo pipefail; blockMesh -case /case > /case/log.blockMesh 2>&1; checkMesh -case /case -allGeometry -allTopology > /case/log.checkMesh 2>&1; foamRun -solver fluid -case /case > /case/log.fluid 2>&1' \
            > "${case_dir}/container.log" 2>&1
        returncode=$?
        set -e
        printf '{"returncode":%d}\n' "${returncode}" > "${case_dir}/run-status.json"
        if [[ "${returncode}" -ne 0 ]]; then
            echo "OpenFOAM a échoué: ${architecture}/${mesh_id}" >&2
            exit "${returncode}"
        fi
    done
done

python3 -B "${PYTHON_RUNNER}" --contract "${CONTRACT}" --output "${OUTPUT}" --stage finalize
