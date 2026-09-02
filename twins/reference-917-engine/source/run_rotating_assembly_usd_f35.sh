#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf '917 F35 USD: %s\n' "$1" >&2
    exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
image_repository="ghcr.io/cluster2600/3dprinting993-simready-workflow"
default_image="${image_repository}@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe"
image_ref="${F35_SIMREADY_WORKFLOW_IMAGE_REF:-${default_image}}"

command -v docker >/dev/null 2>&1 || fail "Docker est absent"
command -v python3 >/dev/null 2>&1 || fail "Python 3 est absent"

case "${image_ref}" in
    "${image_repository}"@sha256:*) digest="${image_ref#${image_repository}@sha256:}" ;;
    *) fail "l'image doit utiliser le dépôt exact ${image_repository}" ;;
esac
[[ "${digest}" =~ ^[0-9a-f]{64}$ ]] || fail "l'image doit être référencée par digest OCI"

docker image inspect "${image_ref}" >/dev/null 2>&1 \
    || fail "image absente localement; effectuer un pull explicite du digest"
test "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "${image_ref}")" = "linux/amd64" \
    || fail "l'image locale n'est pas linux/amd64"
repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "${image_ref}")"
python3 - "${image_ref}" "${repo_digests}" <<'PY'
import json
import sys

reference, encoded = sys.argv[1:]
digests = json.loads(encoded)
if not isinstance(digests, list) or reference not in digests:
    raise SystemExit("le digest OCI demandé est absent de RepoDigests")
PY

variants=(type_912_4_5_na 917_30_turbo_5374)
families=(crankshaft main_bearing_pair connecting_rod piston piston_pin piston_ring)
for variant in "${variants[@]}"; do
    for family in "${families[@]}"; do
        source="${repo_root}/work/917-rotating-assembly-f35/${variant}/step/${family}.step"
        test -f "${source}" || fail "STEP F35 manquant: ${variant}/${family}"
    done
done

mkdir -p "${repo_root}/work/917-rotating-assembly-f35"

docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" \
    --network none --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
    --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
    -e HOME=/tmp -e XDG_CACHE_HOME=/tmp/simready-cache \
    --mount type=bind,src="${repo_root}/containers",dst=/workspace/containers,readonly \
    --mount type=bind,src="${repo_root}/twins",dst=/workspace/twins,readonly \
    --mount type=bind,src="${repo_root}/work",dst=/workspace/work \
    --workdir /workspace --entrypoint /bin/bash "${image_ref}" -euo pipefail -c '
variants=(type_912_4_5_na 917_30_turbo_5374)
families=(crankshaft main_bearing_pair connecting_rod piston piston_pin piston_ring)
for variant in "${variants[@]}"; do
  for family in "${families[@]}"; do
    source="/workspace/work/917-rotating-assembly-f35/${variant}/step/${family}.step"
    output_dir="/workspace/work/917-rotating-assembly-f35/usd-conversion/${variant}/prototypes/${family}"
    mkdir -p "${output_dir}"
    /opt/simready-validation/bin/python \
      /workspace/containers/simready-preflight/convert.py \
      "${source}" "${output_dir}/${family}.usd" \
      --report "${output_dir}/conversion-report.json" \
      --log "${output_dir}/conversion.log" --up-axis z --quiet
  done
done
/opt/simready-validation/bin/python \
  /workspace/twins/reference-917-engine/source/author_rotating_assembly_usd_f35.py
'
