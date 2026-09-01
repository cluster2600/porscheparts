#!/usr/bin/env bash
set -euo pipefail

failures=0

check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        printf 'OK   %s\n' "${label}"
    else
        printf 'FAIL %s\n' "${label}" >&2
        failures=$((failures + 1))
    fi
}

check python-3.12 python3.12 -c 'import sys; assert sys.version_info[:2] == (3, 12)'
check ovrtx-import env PYTHONPATH=/opt/content-agents:/opt/content-agents/apps/ovrtx_rendering_api \
    WU_OVRTX_VENV_DIR=/opt/ovrtx-runtime WU_OVRTX_AUTO_PROVISION=0 \
    /opt/ovrtx-app/bin/python -c 'from service.main import app; assert app'
check material-agent-import env PYTHONPATH=/opt/content-agents:/opt/content-agents/apps:/opt/content-agents/apps/material_agent_service \
    /opt/material-agent/bin/python -c 'from service.main import app; assert app'
check physics-agent-import env PYTHONPATH=/opt/content-agents:/opt/content-agents/apps:/opt/content-agents/apps/physics_agent_service \
    WU_OVPHYSX_VENV_DIR=/opt/ovphysx-runtime \
    /opt/physics-agent/bin/python -c 'from service.main import app; assert app'
check openusd /opt/simready-validation/bin/python -c 'from pxr import Usd, UsdGeom, UsdPhysics; assert Usd.GetVersion()'
check png-pixel-inspection /opt/simready-validation/bin/python -c 'from PIL import Image, ImageStat; assert Image and ImageStat'
check asset-validator /opt/simready-validation/bin/python -c 'import omni.asset_validator'
check simready-validate /opt/simready-validation/bin/simready-validate --help
check usd-convert-cad /opt/usd-convert-cad/bin/usd-convert-cad --help
check scene-optimizer test -d /opt/content-agents/.build-resources/scene_optimizer_core/usdpy

if [ "${failures}" -ne 0 ]; then
    echo "simready smoke: ${failures} failure(s)" >&2
    exit 1
fi
echo "simready smoke: all image checks passed"
