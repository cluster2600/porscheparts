#!/usr/bin/env bash
# Verify that every tool the image promises actually runs.
# Usage: smoke-test.sh [recon|cadsim|mesh-cfd|physicsml|simready|simready-workflow] (auto-detected when omitted)
#
# Version probes are matched on their output, not on their exit status: several
# of these tools report a version and then exit non-zero (CalculiX exits 201).
set -uo pipefail

MODE="${1:-auto}"
if [ "${MODE}" = "auto" ]; then
    if command -v colmap >/dev/null 2>&1; then
        MODE=recon
    elif python -c 'import physicsnemo' >/dev/null 2>&1; then
        MODE=physicsml
    else
        MODE=cadsim
    fi
fi

failures=0

report() {
    local status="$1" label="$2" detail="$3"
    printf '%-4s %-22s %s\n' "${status}" "${label}" "${detail:0:70}"
    [ "${status}" = "FAIL" ] && failures=$((failures + 1))
    return 0
}

first_line() {
    local text="$1" line
    while IFS= read -r line; do
        [ -n "${line// /}" ] && { printf '%s' "${line}"; return 0; }
    done <<< "${text}"
    printf '%s' "(no output)"
}

# check <label> <expected-pattern> <command...>
check() {
    local label="$1" pattern="$2"; shift 2
    local out
    out=$("$@" 2>&1)
    # A dynamic-loader failure prints the program name, which would otherwise
    # satisfy a lenient pattern and turn a broken binary into a pass.
    if printf '%s' "${out}" | grep -qiE "error while loading shared libraries|command not found|No such file or directory"; then
        report FAIL "${label}" "$(first_line "${out}")"
    elif printf '%s' "${out}" | grep -qiE "${pattern}"; then
        report OK "${label}" "$(first_line "${out}")"
    else
        report FAIL "${label}" "$(first_line "${out}")"
    fi
}

# check_python <label> <code>
check_python() {
    local label="$1" code="$2"
    local out rc
    out=$(python -c "${code}" 2>&1); rc=$?
    if [ "${rc}" -eq 0 ]; then
        report OK "${label}" "$(first_line "${out}")"
    else
        report FAIL "${label}" "$(first_line "${out}")"
    fi
}

echo "smoke test: ${MODE}"

if [ "${MODE}" = "recon" ]; then
    check colmap 'colmap|usage|command' colmap help
    check glomap 'Usage|Options|database_path' glomap -h
    check blender 'Blender' blender --version
    check ffmpeg 'ffmpeg version' ffmpeg -version
    check exiftool '^[0-9]+\.[0-9]+' exiftool -ver
    check_python open3d 'import open3d; print("open3d", open3d.__version__)'
    check_python pymeshlab 'import pymeshlab; pymeshlab.MeshSet(); print("pymeshlab", pymeshlab.pmeshlab.__version__)'
    check_python trimesh 'import trimesh; print("trimesh", trimesh.__version__)'
    check_python rtree 'import rtree; print("rtree", rtree.__version__)'
    check_python opencv 'import cv2; print("opencv", cv2.__version__)'
    # CUDA is reported, not required: the image must still start on a CPU host.
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
        report OK gpu "$(nvidia-smi -L | head -1)"
    else
        report WARN gpu "no CUDA device visible; dense reconstruction unavailable"
    fi
elif [ "${MODE}" = "physicsml" ]; then
    check ccx 'Version' ccx -v
    check openscad 'OpenSCAD' openscad --version
    check admesh 'ADMesh' admesh --version
    check_python build123d 'import build123d; print("build123d", build123d.__version__)'
    check_python cadquery 'import cadquery; print("cadquery", cadquery.__version__)'
    check_python gmsh 'import gmsh; gmsh.initialize(); print("gmsh", gmsh.GMSH_API_VERSION); gmsh.finalize()'
    check_python meshio 'import meshio; print("meshio", meshio.__version__)'
    check_python jax 'import jax; print("jax", jax.__version__, jax.devices())'
    check_python jax_fem 'import jax_fem; print("jax-fem", getattr(jax_fem, "__version__", "imported"))'
    check_python torch 'import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available())'
    check_python physicsnemo 'import physicsnemo; print("physicsnemo", getattr(physicsnemo, "__version__", "imported"))'
    check_python physicsnemo_sym 'import physicsnemo.sym; print("physicsnemo.sym imported")'
    check_python deepxde 'import deepxde; print("deepxde", deepxde.__version__)'
    check_python foamlib 'import foamlib; print("foamlib ok")'
    check openfoam 'blockMesh|Usage|OpenFOAM' \
        bash -lc "source /opt/openfoam${FOAM_VERSION:-13}/etc/bashrc && blockMesh -help"
    # GPU visibility is reported separately: the image is still inspectable
    # on a CPU-only CI runner, while a Vast.ai run should expose a device.
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
        report OK gpu "$(nvidia-smi -L | head -1)"
        check_python jax_gpu 'import jax; assert any(d.platform == "gpu" for d in jax.devices()); print("jax gpu", jax.devices())'
        check_python torch_gpu 'import torch; assert torch.cuda.is_available(); print("torch gpu", torch.cuda.get_device_name(0))'
    else
        report WARN gpu "no CUDA device visible; GPU acceleration not exercised"
    fi
elif [ "${MODE}" = "cadsim" ]; then
    check ccx 'Version' ccx -v
    check openscad 'OpenSCAD' openscad --version
    check prusa-slicer 'PrusaSlicer|Slic3r' prusa-slicer --help
    check admesh 'ADMesh' admesh --version
    check_python build123d 'import build123d; print("build123d", build123d.__version__)'
    check_python cadquery 'import cadquery; print("cadquery", cadquery.__version__)'
    check_python gmsh 'import gmsh; gmsh.initialize(); print("gmsh", gmsh.GMSH_API_VERSION); gmsh.finalize()'
    check_python meshio 'import meshio; print("meshio", meshio.__version__)'
    check_python foamlib 'import foamlib; print("foamlib ok")'
    check openfoam 'blockMesh|Usage|OpenFOAM' \
        bash -lc "source /opt/openfoam${FOAM_VERSION:-13}/etc/bashrc && blockMesh -help"
elif [ "${MODE}" = "mesh-cfd" ]; then
    check blender 'Blender' blender --version
    check admesh 'ADMesh' admesh --version
    check_python pymeshlab 'import pymeshlab; pymeshlab.MeshSet(); print("pymeshlab", pymeshlab.pmeshlab.__version__)'
    check_python trimesh 'import trimesh; print("trimesh", trimesh.__version__)'
    check_python manifold3d 'import manifold3d; print("manifold3d ok")'
    check_python build123d 'import build123d; print("build123d", build123d.__version__)'
    check_python gmsh 'import gmsh; gmsh.initialize(); print("gmsh", gmsh.GMSH_API_VERSION); gmsh.finalize()'
    check_python meshio 'import meshio; print("meshio", meshio.__version__)'
    check openfoam 'blockMesh|Usage|OpenFOAM' \
        bash -lc "source /opt/openfoam${FOAM_VERSION:-13}/etc/bashrc && blockMesh -help"
elif [ "${MODE}" = "simready" ] || [ "${MODE}" = "simready-workflow" ]; then
    /usr/local/bin/simready-smoke || failures=$((failures + 1))
elif [ "${MODE}" = "simready-local-ai" ] || [ "${MODE}" = "simready-m64-runtime" ]; then
    /usr/local/bin/simready-smoke || failures=$((failures + 1))
    /usr/local/bin/simready-local-ai-smoke --offline || failures=$((failures + 1))
    if [ "${MODE}" = "simready-m64-runtime" ]; then
        check m64-pinned-runtime 'm64 pinned runtime OK' /opt/m64-simready-validate/bin/python -I -c \
            'import importlib.metadata as md; import numpy, omni.asset_validator; from pxr import Usd, UsdGeom, UsdPhysics; expected={"simready-validate":"2026.4.8", "usd-exchange":"2.3.0", "omniverse-asset-validator":"1.18.0", "omniverse-usd-profiles":"1.10.22", "numpy":"1.26.4", "jinja2":"3.1.6", "markdown-it-py":"4.2.0", "markupsafe":"3.0.3", "mdurl":"0.1.2"}; assert all(md.version(k)==v for k,v in expected.items()); print("m64 pinned runtime OK")'
        check m64-foundation 'a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3' \
            git -C /opt/m64-simready-foundation rev-parse HEAD
        check m64-validation-cli 'usage:|Usage:' /opt/m64-simready-validate/bin/simready-validate --help
        check m64-preflight-yaml '6.0.2' /opt/m64-simready-validate/bin/python -I -c 'import yaml; assert yaml.__version__ == "6.0.2"; print(yaml.__version__)'
        check m64-cad-guide '208fe2c1cd71ae2bb7bd825daf712617000ae028' \
            git -C /opt/m64-usd-convert-cad-guide rev-parse HEAD
    fi
else
    report FAIL mode "unknown smoke-test mode: ${MODE}"
fi

if [ "${failures}" -gt 0 ]; then
    echo "smoke test: ${failures} failure(s)"
    exit 1
fi
echo "smoke test: all checks passed"
