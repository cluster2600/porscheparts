#!/usr/bin/env bash
set -euo pipefail

bundle_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
output="${1:-/workspace/output}"
expected='ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe'
test "${F41_RUNTIME_IMAGE_REF:-}" = "${expected}" || {
    printf 'F41 USD job: F41_RUNTIME_IMAGE_REF doit être %s\n' "${expected}" >&2
    exit 2
}
python "${bundle_root}/twins/reference-917-engine/source/execute_component_factory_f41.py" \
    usd --project-root "${bundle_root}" \
    --contract "${bundle_root}/twins/reference-917-engine/component-factory-f41.json" \
    --output "${output}"
