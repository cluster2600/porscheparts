#!/usr/bin/env bash
# One installed NVIDIA reference per invocation; never a monolithic workflow.
set -euo pipefail
: "${SIMREADY_SKILL_ROOT:?Point to the installed omniverse-cad-to-simready skill}"
stage="${1:?Specify a stage}"; shift
case "$stage" in
  preflight) script=references/preflight/scripts/preflight.py ;;
  identify-asset-context|convert-to-usd|validate-usd-minimum|content-agents|simready-conform-profile|omni-asset-validate|omni-asset-validate-geometry|omni-asset-validate-physics|simready-validate|ovrtx-render-service|assemble-package-source|nv-core-package-sample|nv-core-package-sample-validation)
    : "${PHYSICAL_AI_PREFLIGHT_MANIFEST:?Run and source preflight first}"
    test -f "$PHYSICAL_AI_PREFLIGHT_MANIFEST"
    export PHYSICAL_AI_REQUIRE_PREFLIGHT=1
    script="references/$stage/scripts/run.py" ;;
  *) echo 'Unsupported SimReady stage' >&2; exit 2 ;;
esac
exec "${SIMREADY_PYTHON:-python3}" "$SIMREADY_SKILL_ROOT/$script" "$@"
