#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf '917 F41 component factory: %s\n' "$1" >&2
    exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
contract="${repo_root}/twins/reference-917-engine/component-factory-f41.json"
executor="${repo_root}/twins/reference-917-engine/source/execute_component_factory_f41.py"
planner="${repo_root}/twins/reference-917-engine/source/build_component_factory_f41.py"
cad_image_default='ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57'
usd_image_default='ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe'
cad_image="${F41_CAD_IMAGE_REF:-${cad_image_default}}"
usd_image="${F41_USD_IMAGE_REF:-${usd_image_default}}"
output="${F41_OUTPUT:-${repo_root}/work/917-component-factory-f41-execution}"
preflight_only=false

if [[ "${1:-}" == "--preflight-only" ]]; then
    preflight_only=true
elif [[ $# -ne 0 ]]; then
    fail "usage: $0 [--preflight-only]"
fi

command -v docker >/dev/null 2>&1 || fail "Docker est absent"
command -v python3 >/dev/null 2>&1 || fail "Python 3 est absent"
test -f "${contract}" || fail "contrat F41 absent"
test -f "${executor}" || fail "runner F41 absent"

validate_image() {
    local reference="$1"
    local repository="$2"
    case "${reference}" in
        "${repository}"@sha256:*) ;;
        *) fail "image hors dépôt ou sans digest immuable: ${reference}" ;;
    esac
    [[ "${reference#${repository}@sha256:}" =~ ^[0-9a-f]{64}$ ]] \
        || fail "digest OCI invalide: ${reference}"
    docker image inspect "${reference}" >/dev/null 2>&1 \
        || fail "image absente localement: docker pull ${reference}"
    test "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "${reference}")" = "linux/amd64" \
        || fail "image non linux/amd64: ${reference}"
    local repo_digests
    repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "${reference}")"
    python3 - "${reference}" "${repo_digests}" <<'PY'
import json
import sys

reference, encoded = sys.argv[1:]
digests = json.loads(encoded)
if not isinstance(digests, list) or reference not in digests:
    raise SystemExit("requested immutable reference absent from RepoDigests")
PY
}

validate_image "${cad_image}" 'ghcr.io/cluster2600/3dprinting993-cad-author-f28'
validate_image "${usd_image}" 'ghcr.io/cluster2600/3dprinting993-simready-workflow'

run_phase() {
    local image="$1"
    local runtime_ref="$2"
    local command_name="$3"
    docker run --rm --pull never --platform linux/amd64 \
        --user "$(id -u):$(id -g)" \
        --network none --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
        --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
        -e HOME=/tmp -e XDG_CACHE_HOME=/tmp/f41-cache \
        -e F41_RUNTIME_IMAGE_REF="${runtime_ref}" \
        --mount type=bind,src="${repo_root}",dst=/workspace,readonly \
        --mount type=bind,src="${output}",dst=/output \
        --workdir /workspace --entrypoint python "${image}" \
        /workspace/twins/reference-917-engine/source/execute_component_factory_f41.py \
        "${command_name}" --project-root /workspace \
        --contract /workspace/twins/reference-917-engine/component-factory-f41.json \
        --output /output
}

if [[ "${preflight_only}" == true ]]; then
    preflight_output="$(mktemp -d "${TMPDIR:-/tmp}/917-f41-preflight.XXXXXX")"
    output="${preflight_output}"
    run_phase "${cad_image}" "${cad_image}" preflight-cad
    run_phase "${usd_image}" "${usd_image}" preflight-usd
    printf '917 F41 preflight passed: CAD and USD immutable runtimes are ready\n'
    exit 0
fi

case "${output}" in
    */917-component-factory-f41-execution) ;;
    *) fail "le dossier de sortie doit se terminer par 917-component-factory-f41-execution" ;;
esac
test ! -e "${output}" || fail "sortie déjà présente, aucun écrasement: ${output}"
mkdir -p "${output}"
python3 "${planner}" --project-root "${repo_root}" --contract "${contract}" --output "${output}"
run_phase "${cad_image}" "${cad_image}" cad
run_phase "${usd_image}" "${usd_image}" usd
python3 "${executor}" finalize --project-root "${repo_root}" --contract "${contract}" --output "${output}"
