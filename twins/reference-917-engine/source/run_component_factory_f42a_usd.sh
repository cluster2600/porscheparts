#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf '917 F42a USD: %s\n' "$1" >&2
    exit 1
}

usage() {
    printf 'usage: %s --archive F41.tar.gz --skill-root DIR --output DIR\n' "$0" >&2
    exit 2
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
contract="${repo_root}/twins/reference-917-engine/component-factory-f42a-usd.json"
executor="${repo_root}/twins/reference-917-engine/source/execute_component_factory_f42a_usd.py"
archive=''
skill_root=''
output=''

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archive) [[ $# -ge 2 ]] || usage; archive="$2"; shift 2 ;;
        --skill-root) [[ $# -ge 2 ]] || usage; skill_root="$2"; shift 2 ;;
        --output) [[ $# -ge 2 ]] || usage; output="$2"; shift 2 ;;
        *) usage ;;
    esac
done

[[ -n "${archive}" && -n "${skill_root}" && -n "${output}" ]] || usage
command -v python3 >/dev/null 2>&1 || fail 'Python 3 est absent'
[[ -f "${contract}" ]] || fail 'contrat F42a absent'
[[ -f "${executor}" ]] || fail 'exécuteur F42a absent'
[[ -f "${archive}" && ! -L "${archive}" ]] || fail 'archive F41 absente ou lien symbolique'
[[ -d "${skill_root}" && ! -L "${skill_root}" ]] || fail 'racine du skill absente ou lien symbolique'
[[ -f "${skill_root}/SKILL.md" && ! -L "${skill_root}/SKILL.md" ]] || fail 'SKILL.md absent'
[[ ! -e "${output}" ]] || fail 'sortie déjà présente, aucun écrasement'

runtime_status="$(python3 - "${contract}" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload["runtime"]["qualification_status"])
PY
)"
expected_image="$(python3 - "${contract}" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload["runtime"]["image_ref"] or "")
PY
)"
[[ "${runtime_status}" == 'qualified_public_linux_amd64_digest' ]] \
    || fail 'digest simready-workflow F42a encore en attente de qualification'
case "${expected_image}" in
    ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:*) ;;
    *) fail 'référence image F42a hors dépôt ou non immuable' ;;
esac
digest="${expected_image##*@sha256:}"
[[ "${digest}" =~ ^[0-9a-f]{64}$ ]] || fail 'digest OCI F42a invalide'
command -v docker >/dev/null 2>&1 || fail 'Docker est absent'

python3 "${executor}" inspect --contract "${contract}" --archive "${archive}" >/dev/null
docker image inspect "${expected_image}" >/dev/null 2>&1 \
    || fail "image absente localement: docker pull ${expected_image}"
[[ "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "${expected_image}")" == 'linux/amd64' ]] \
    || fail 'image F42a non linux/amd64'
repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "${expected_image}")"
python3 - "${expected_image}" "${repo_digests}" <<'PY'
import json
import sys

reference, encoded = sys.argv[1:]
digests = json.loads(encoded)
if not isinstance(digests, list) or reference not in digests:
    raise SystemExit("requested immutable reference absent from RepoDigests")
PY

archive="$(cd -- "$(dirname -- "${archive}")" && printf '%s/%s\n' "$PWD" "$(basename -- "${archive}")")"
skill_root="$(cd -- "${skill_root}" && pwd -P)"
output_parent="$(cd -- "$(dirname -- "${output}")" && pwd -P)"
output="${output_parent}/$(basename -- "${output}")"
mkdir "${output}"

docker run --rm --pull never --platform linux/amd64 \
    --user "$(id -u):$(id -g)" \
    --network none --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
    --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
    -e HOME=/tmp -e XDG_CACHE_HOME=/tmp/f42a-cache \
    -e F42A_RUNTIME_IMAGE_REF="${expected_image}" \
    -e USD_CONVERT_CAD_ROOT=/opt/usd-convert-cad-preflight \
    -e PHYSICAL_AI_SIMREADY_VALIDATE_VENV=/opt/simready-validation \
    --mount type=bind,src="${repo_root}",dst=/workspace,readonly \
    --mount type=bind,src="${archive}",dst=/input/f41.tar.gz,readonly \
    --mount type=bind,src="${skill_root}",dst=/opt/f42a-skill,readonly \
    --mount type=bind,src="${output}",dst=/output \
    --workdir /workspace \
    --entrypoint /opt/simready-validation/bin/python \
    "${expected_image}" \
    /workspace/twins/reference-917-engine/source/execute_component_factory_f42a_usd.py run \
    --archive /input/f41.tar.gz \
    --contract /workspace/twins/reference-917-engine/component-factory-f42a-usd.json \
    --skill-root /opt/f42a-skill \
    --converter-adapter /opt/usd-convert-cad-preflight/convert.py \
    --output /output
