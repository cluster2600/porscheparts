#!/usr/bin/env bash
# Lance le validateur SimReady avec les trois racines documentaires requises.
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: simready-profile-validate <asset.usd> [simready-validate options...]" >&2
    exit 2
fi

SPEC_ROOT="${SIMREADY_SPEC_ROOT:-/opt/simready-foundation/nv_core/sr_specs/docs}"

exec /opt/simready-validation/bin/simready-validate "$@" \
    --rules-path "${SPEC_ROOT}/capabilities" \
    --features-path "${SPEC_ROOT}/features" \
    --profiles-path "${SPEC_ROOT}/profiles"
