#!/usr/bin/env bash
set -euo pipefail

bundle_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
output="${1:-/workspace/output}"
expected='ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57'
test "${F41_RUNTIME_IMAGE_REF:-}" = "${expected}" || {
    printf 'F41 CAD job: F41_RUNTIME_IMAGE_REF doit être %s\n' "${expected}" >&2
    exit 2
}
python "${bundle_root}/twins/reference-917-engine/source/execute_component_factory_f41.py" \
    cad --project-root "${bundle_root}" \
    --contract "${bundle_root}/twins/reference-917-engine/component-factory-f41.json" \
    --output "${output}"
