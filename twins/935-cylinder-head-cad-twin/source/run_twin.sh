#!/usr/bin/env bash
# Replay the 935 CAD twin chain.
# Usage: run_twin.sh SCAN.obj PRIVATE_DIR PYTHON
#   PYTHON: interpreter with numpy, scipy, trimesh, libigl, scikit-image,
#           shapely, warp-lang, build123d and usd-core (see README).
# Heavy steps run in memory-capped scopes so WSL is not exhausted; the
# decimation runs in the recon image and the thermal screen in cadsim.
set -euo pipefail
SCAN=$(realpath "$1"); PRIV=$(realpath "$2"); PY=$3
HERE=$(cd "$(dirname "$0")" && pwd); TWIN=$(dirname "$HERE"); PARAMS=$TWIN/params
cap() { systemd-run --user --scope -q -p MemoryMax="${MEM:-11G}" "$@"; }

cap "$PY" -I "$HERE/fit_frame.py" "$SCAN" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/occupancy.py" "$PRIV" "$PARAMS" 0.25
cap "$PY" -I "$HERE/surface_mesh.py" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/score_twin.py" "$SCAN" "$PARAMS/frame.json" "$PRIV/t1-bare-head.stl" "$PARAMS/scorecard-t1.json" T1

docker run --rm --memory=10g -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
  3dprinting993-recon:dev -I /src/decimate.py /p/t1-bare-head.stl /p/t1-sim-surface.stl 400000 /p/decimate.json
cp "$PRIV/decimate.json" "$PARAMS/sim-surface-summary.json"
MEM=12G cap "$PY" -I "$HERE/tetmesh.py" "$PRIV/t1-sim-surface.stl" "$PRIV/t1-tets.npz" 1.5 0.1 "$PRIV/tetmesh.json"
cp "$PRIV/tetmesh.json" "$PARAMS/tetmesh-summary.json"
docker run --rm --memory=10g -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
  3dprinting993-cadsim:dev -I /src/sim_thermal.py /p/t1-tets.npz /p/thermal 1.5 T1-thermal
cp "$PRIV/thermal/result.json" "$PARAMS/thermal-screen.json"

cap "$PY" -I "$HERE/export_print.py" "$PRIV/t1-bare-head.stl" "$PRIV/935-bare-head-twin-study.3mf" "$PARAMS/print-summary.json"
cap "$PY" -I "$HERE/export_usd.py" "$PRIV" "$PARAMS" "$PRIV/t1-sim-surface.stl" "$PRIV/935-head-twin.usdc"
# T2 (build_brep.py) is a measured negative result on this host; see README.
