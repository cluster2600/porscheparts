#!/usr/bin/env bash
# Verify that every tool the image promises actually runs.
# Usage: smoke-test.sh [recon|cadsim]   (auto-detected when omitted)
#
# Version probes are matched on their output, not on their exit status: several
# of these tools report a version and then exit non-zero (CalculiX exits 201).
set -uo pipefail

MODE="${1:-auto}"
if [ "${MODE}" = "auto" ]; then
    if command -v colmap >/dev/null 2>&1; then MODE=recon; else MODE=cadsim; fi
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
    check_python opencv 'import cv2; print("opencv", cv2.__version__)'
    # CUDA is reported, not required: the image must still start on a CPU host.
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
        report OK gpu "$(nvidia-smi -L | head -1)"
    else
        report WARN gpu "no CUDA device visible; dense reconstruction unavailable"
    fi
else
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
fi

if [ "${failures}" -gt 0 ]; then
    echo "smoke test: ${failures} failure(s)"
    exit 1
fi
echo "smoke test: all checks passed"
