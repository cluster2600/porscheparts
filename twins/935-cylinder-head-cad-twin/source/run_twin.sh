#!/usr/bin/env bash
# Replay the 935 CAD twin chain.
# Usage: run_twin.sh SCAN.obj PRIVATE_DIR PYTHON
#   PYTHON: interpreter with numpy, scipy, trimesh, libigl, scikit-image,
#           shapely, warp-lang, build123d, manifold3d and usd-core (see README).
#   SIM (optional, environment): directory holding the two NVIDIA tool venvs.
# Heavy steps run in memory-capped scopes so WSL is not exhausted; the
# decimation runs in the recon image and the thermal screen in cadsim.
set -euo pipefail
SCAN=$(realpath "$1"); PRIV=$(realpath "$2"); PY=$3
HERE=$(cd "$(dirname "$0")" && pwd); TWIN=$(dirname "$HERE"); PARAMS=$TWIN/params
cap() { systemd-run --user --scope -q -p MemoryMax="${MEM:-11G}" "$@"; }
STAMP=$(date +%Y%m%d-%H%M%S)   # new private directories for the steps that refuse an existing one

cap "$PY" -I "$HERE/fit_frame.py" "$SCAN" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/occupancy.py" "$PRIV" "$PARAMS" 0.25
cap "$PY" -I "$HERE/surface_mesh.py" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/score_twin.py" "$SCAN" "$PARAMS/frame.json" "$PRIV/t1-bare-head.stl" "$PARAMS/scorecard-t1.json" T1

# T1s: snap observed vertices onto the scan, then revert the few that fold (recon image).
cap "$PY" -I "$HERE/snap_surface.py" "$PRIV" "$PARAMS"
docker run --rm --memory=10g --user "$(id -u):$(id -g)" -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
  3dprinting993-recon:dev -I /src/unsnap_intersections.py /p/t1-bare-head.ply /p/t1s-bare-head.ply /p/t1s-clean.ply /p/unsnap.json
cap "$PY" -I "$HERE/assemble_records.py" t1s "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/score_twin.py" "$SCAN" "$PARAMS/frame.json" "$PRIV/t1s-clean.stl" "$PARAMS/scorecard-t1s.json" T1s

# T3 thermal screen on marching-cubes surfaces of the occupancy at 1.0 and 0.75 mm
# (cadsim image). The decimated surface and fTetWild were tried first and are
# measured negative results: see README.
for lv in 4:mc100 3:mc075; do
  n=${lv#*:}
  cap "$PY" -I "$HERE/sim_surface_mc.py" "$PRIV" "$PRIV/t1-sim-$n.stl" "$PRIV/t1-sim-$n.json" "${lv%:*}"
  docker run --rm --memory=10g -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
    3dprinting993-cadsim:dev -I /src/sim_thermal.py "/p/t1-sim-$n.stl" "/p/thermal-$n" 3.0 "T1-$n-thermal"
  cap "$PY" -I "$HERE/check_thermal_balance.py" "$PRIV/thermal-$n" "$PRIV/balance-$n.json"
done
cp "$PRIV/t1-sim-mc075.json" "$PARAMS/sim-surface-mc075-summary.json"
"$PY" -I "$HERE/assemble_records.py" thermal "$PRIV" "$PARAMS" surface_1p0mm=mc100 surface_0p75mm=mc075

# T4 and T5 from T1s: a 600,000-triangle display surface for the stage, the full surface for the 3MF.
docker run --rm --memory=10g --user "$(id -u):$(id -g)" -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
  3dprinting993-recon:dev -I /src/decimate.py /p/t1s-clean.stl /p/t1s-display.stl 600000 /p/decimate-display.json
cap "$PY" -I "$HERE/export_print.py" "$PRIV/t1s-clean.stl" "$PRIV/935-bare-head-twin-study.3mf" "$PARAMS/print-summary.json"
cap "$PY" -I "$HERE/export_usd.py" "$PRIV" "$PARAMS" "$PRIV/t1s-display.stl" "$PRIV/935-head-twin.usdc"
# T2 (build_brep.py) is a measured negative result on this host; see README.

# v1 body stack: run d (fin faces, tilted tops), the port lofts checked against
# it, then run f with the lofts and the chamber dome cut in. Each run needs a
# new label; scores are taken on the outer shell.
cap "$PY" -I "$HERE/fit_fins.py" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/fit_ports.py" "$PRIV" "$PARAMS"
cap "$PY" -I "$HERE/fin_stack.py" "$PRIV" "$PARAMS" d --tilt --workers 8
cap "$PY" -I "$HERE/port_loft.py" "$PRIV" "$PARAMS" d
cap "$PY" -I "$HERE/fin_stack.py" "$PRIV" "$PARAMS" f --tilt --ports --dome --split-thick --workers 12
for run in d f; do
  cap "$PY" -I "$HERE/score_twin.py" "$SCAN" "$PARAMS/frame.json" "$PRIV/v1-body-stack-$run-shell.stl" "$PARAMS/scorecard-v1-stack-$run-shell.json" "v1-stack-$run-shell"
done
cap "$PY" -I "$HERE/error_breakdown.py" "$PRIV" "$PRIV/v1-body-stack-f-shell.stl" "$PARAMS/error-breakdown-v1-stack-f-shell.json"

# v2 body: section loft closed with Manifold, at three section steps. Each run
# needs a label whose private directory does not exist yet. s025 is the
# reference CAD body.
for run in 1.00:s100 0.50:s050 0.25:s025; do
  label=${run#*:}
  MEM=7G cap "$PY" -I "$HERE/loft_stack.py" "$PRIV" "$PARAMS" "$label" --step "${run%:*}" --workers 8
  cap "$PY" -I "$HERE/score_twin.py" "$SCAN" "$PARAMS/frame.json" "$PRIV/v2-loft-$label.stl" "$PARAMS/scorecard-v2-loft-$label.json" "v2-loft-$label"
done
cap "$PY" -I "$HERE/error_breakdown.py" "$PRIV" "$PRIV/v2-loft-s025.stl" "$PARAMS/error-breakdown-v2-loft-s025.json"
cap "$PY" -I "$HERE/plot_scorecards.py" "$PARAMS" "$TWIN/media/scorecard-bodies.png"

# Tiers from the CAD body: occupancy, 1.0 mm surface (iso-level between two
# attainable block means of a binary grid), thermal screen, balance, comparison.
cap "$PY" -I "$HERE/loft_occupancy.py" "$PRIV" "$PRIV/v2-loft-s025.npz" "$PRIV/v2-loft-s025-occ" "$PARAMS/v2-loft-s025-occupancy.json"
cap "$PY" -I "$HERE/sim_surface_mc.py" "$PRIV/v2-loft-s025-occ" "$PRIV/v2-loft-sim-mc100.stl" "$PRIV/v2-loft-sim-mc100.json" 4 0.4921875
docker run --rm --memory=10g -v "$PRIV:/p" -v "$HERE:/src:ro" --entrypoint /opt/venv/bin/python \
  3dprinting993-cadsim:dev -I /src/sim_thermal.py /p/v2-loft-sim-mc100.stl /p/thermal-v2-loft-mc100 3.0 v2-loft-mc100-thermal
cap "$PY" -I "$HERE/check_thermal_balance.py" "$PRIV/thermal-v2-loft-mc100" "$PRIV/balance-v2-loft-mc100.json"
cap "$PY" -I "$HERE/thermal_summary.py" "$PRIV/thermal-v2-loft-mc100/result.json" "$PRIV/v2-loft-sim-mc100.json" \
  "$PRIV/balance-v2-loft-mc100.json" "$PARAMS/thermal-screen-cad.json" "$PARAMS/thermal-screen.json" surface_1p0mm
cap "$PY" -I "$HERE/export_usd.py" "$PRIV" "$PARAMS" "$PRIV/v2-loft-s025.npz" "$PRIV/935-head-twin-cad.usdc" \
  usd-cad-summary.json "v2 loft body, sections at most 0.25 mm apart"
cap "$PY" -I "$HERE/export_print.py" "$PRIV/v2-loft-s025.npz" "$PRIV/935-head-cad-twin-study.3mf" "$PARAMS/print-cad-summary.json"

# Alloy screens (cadsim image). Bare head: the deck of the CAD-body screen with each
# candidate conductivity. Assembly: valves, guides and plugs as hypothesis solids
# united with the body, then every variant of the case file (a variant may scale its
# gas-side coefficients to a published wall loading). Last, published strength beside
# the computed peaks, and the chart of the page.
docker run --rm --memory=10g --user "$(id -u):$(id -g)" -v "$PRIV:/p" -v "$HERE:/src:ro" -v "$PARAMS:/params:ro" \
  --entrypoint /opt/venv/bin/python 3dprinting993-cadsim:dev -I /src/alloy_thermal.py /p/thermal-v2-loft-mc100 \
  /params/alloy-candidates.json "/p/alloy-thermal-$STAMP" /p/alloy-thermal-summary.json
cp "$PRIV/alloy-thermal-summary.json" "$PARAMS/alloy-thermal.json"
MEM=8G cap "$PY" -I "$HERE/assembly_thermal.py" occupancy "$PRIV/v2-loft-s025-occ" "$PARAMS" "$PRIV/assembly-occ-$STAMP"
MEM=8G cap "$PY" -I "$HERE/sim_surface_mc.py" "$PRIV/assembly-occ-$STAMP" "$PRIV/assembly-sim-mc100.stl" "$PRIV/assembly-sim-mc100.json" 4 0.4921875
docker run --rm --memory=8g --user "$(id -u):$(id -g)" -v "$PRIV:/p" -v "$HERE:/src:ro" -v "$PARAMS:/params:ro" \
  --entrypoint /opt/venv/bin/python 3dprinting993-cadsim:dev -I /src/assembly_thermal.py solve /p/assembly-sim-mc100.stl \
  /params /p/v2-loft-s025-occ "/p/assembly-thermal-$STAMP" /p/assembly-thermal-summary.json
cp "$PRIV/assembly-thermal-summary.json" "$PARAMS/assembly-thermal.json"
"$PY" -I "$HERE/alloy_tradeoff.py" "$PARAMS" "$TWIN/media"

# Port CFD: the audit only. It finds no admissible fluid domain, so no solver runs.
"$PY" -I "$HERE/audit_port_domain.py" "$PARAMS" "$TWIN/hypotheses.json" "$PARAMS/port-cfd-audit.json"

# AM screen (Adamantine runs in rombur/adamantine:1.1, capped at 4 GiB).
MEM=4G cap "$PY" -I "$HERE/am_supports.py" "$PRIV" "$PARAMS"
"$PY" -I "$HERE/am_cooldown.py" all "$PRIV" "$PARAMS"

# Print body (a study object derived from the CAD body), its orientation screen, and the
# deposition witness of the build simulation. The witness directory must be new.
MEM=8G cap "$PY" -I "$HERE/print_body.py" "$PRIV/v2-loft-s025-occ" "$PARAMS" "$PRIV/print-occ-$STAMP"
MEM=8G cap "$PY" -I "$HERE/sim_surface_mc.py" "$PRIV/print-occ-$STAMP" "$PRIV/print-body-mc050.stl" "$PRIV/print-body-mc050.json" 2 0.4375
MEM=6G cap "$PY" -I "$HERE/print_body.py" check "$PRIV/print-body-mc050.stl" "$PRIV/print-occ-$STAMP/print-body-occupancy.json" "$PARAMS/print-body.json"
mkdir "$PRIV/print-supports-$STAMP" && cp "$PARAMS/frame.json" "$PRIV/print-supports-$STAMP/"
MEM=4G cap "$PY" -I "$HERE/am_supports.py" "$PRIV/print-occ-$STAMP" "$PRIV/print-supports-$STAMP"
cp "$PRIV/print-supports-$STAMP/am-supports.json" "$PARAMS/print-body-supports.json"
"$PY" -I "$HERE/am_build.py" witness "$PRIV/am-build-witness-$STAMP" "$PARAMS/am-build-witness.json"

# Thin walls of the print body on the occupancy grid (beside the layer screen's thickness probe).
MEM=10G cap "$PY" -I "$HERE/wall_check.py" "$PRIV/print-occ-$STAMP" "$PARAMS/print-body-wall-check.json"
# Layer screen in bounded memory (cadsim image; PYLIB holds shapely, rtree and networkx). The
# committed record params/print-body-layer-screen.json is assembled from its output folder:
#   docker run --rm --memory=14g --memory-swap=14g -e PYTHONPATH=/pylib -v "$REPO:/repo" -v "$PYLIB:/pylib:ro" -w /repo \
#     --entrypoint python3 3dprinting993-cadsim:dev twins/935-cylinder-head-cad-twin/source/layer_screen.py \
#     --slice-chunk 64 --thickness-batch 25 --part-id 935-HEAD-PRINT-BODY-F0 --master ... --surface ... --output ...

# Build screen in CalculiX (cadsim image, one thread): witnesses, then each level of
# params/build-sim-case.json. A level's thermal run comes before its mechanical run; the 2 mm
# level is thermal only (its mechanical model is out of reach of a direct solver here).
BS="$PRIV/build-sim-$STAMP"; mkdir "$BS"
"$PY" -I "$HERE/build_sim.py" witness "$BS/witness" "$PARAMS/build-sim-witness.json"
for level in c4-l8 c4-l4 c2-l8; do
  MEM=8G cap "$PY" -I "$HERE/build_sim.py" prepare "$PRIV/print-occ-$STAMP" "$PARAMS/build-sim-case.json" "$level" "$BS/$level"
  "$PY" -I "$HERE/build_sim.py" thermal "$BS/$level"
done
"$PY" -I "$HERE/build_sim.py" mechanics "$BS/c4-l8"
"$PY" -I "$HERE/build_sim.py" mechanics "$BS/c4-l8" --variant yield-stress-relieved
"$PY" -I "$HERE/build_sim.py" mechanics "$BS/c4-l8" --variant stress-free-673K
"$PY" -I "$HERE/build_sim.py" mechanics "$BS/c4-l4"
"$PY" -I "$HERE/build_sim.py" summarize "$BS" "$PARAMS/build-sim-case.json" "$PARAMS/build-sim-witness.json" "$PARAMS/build-sim.json"
# Software OpenGL in a sandbox without /dev/dxg, on purpose: with GALLIUM_DRIVER=d3d12 this render
# took the WSL VM down twice (docs/LOCAL_HOST_SETUP.md, section 3).
GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1 bwrap --dev-bind / / --dev /dev --proc /proc \
  xvfb-run -a "$PY" -I "$HERE/render_build_sim.py" "$BS/c4-l8" "$TWIN/media"

# Revolved machined features, with the assigned fitting tool and its own environment
# (docs/LOCAL_HOST_SETUP.md, "Tool environments under work/"), then CloudCompare on the
# held-out half of each window and on the v2 body. FIT and CC_IMAGE are optional:
#   FIT=work/scan-primitive-fitting-venv/bin/python  CC_IMAGE=free-tools-cloudcompare:local
# check_features.py refuses an existing --work directory: name a new one for each run.
REPO=$(cd "$TWIN/../.." && pwd)
if [ -n "${FIT:-}" ] && [ -n "${CC_IMAGE:-}" ]; then
  MEM=4G cap "$FIT" -I "$HERE/fit_features.py" --bare-scan "$PRIV/bare-scan-twin.npz" --rois "$PARAMS/feature-rois.json" \
    --tool "$REPO/benchmarks/scan-primitive-fitting/primitive_fit.py" --frame "$PARAMS/frame.json" \
    --private-out "$PRIV/feature-split.npz" --out "$PARAMS/feature-fits.json"
  "$PY" -I "$HERE/check_features.py" --bare-scan "$PRIV/bare-scan-twin.npz" --image "$CC_IMAGE" \
    --work "$PRIV/feature-check-$STAMP" --fits "$PARAMS/feature-fits.json" --split "$PRIV/feature-split.npz" \
    --out "$PARAMS/feature-check.json"
  "$PY" -I "$HERE/check_features.py" --bare-scan "$PRIV/bare-scan-twin.npz" --image "$CC_IMAGE" \
    --work "$PRIV/body-cloudcompare-$STAMP" --body "$PRIV/v2-loft-s025.npz" \
    --scorecard "$PARAMS/scorecard-v2-loft-s025.json" --out "$PARAMS/cloudcompare-v2-body.json"
fi

# The CAD-body stage packaged with a collider and a display material. The output
# directory must be new. The NVIDIA validation of both forms follows below when SIM is set.
"$PY" -I "$HERE/export_simready.py" "$PRIV/935-head-twin-cad.usdc" "$PRIV/v2-loft-sim-mc100.stl" \
  "$PRIV/simready-asset-$STAMP" "$PARAMS/simready-asset.json"

# NVIDIA tools live in two environments of their own, never in $PY:
#   uv venv --python 3.12 "$SIM/convert";  uv pip install --python "$SIM/convert/bin/python" \
#     --extra-index-url https://pypi.nvidia.com "usd-convert-cad==0.2.0"
#   uv venv --python 3.12 "$SIM/validate"; uv pip install --python "$SIM/validate/bin/python" \
#     "usd-validation-nvidia==1.21.0" "usd-core==26.8" "numpy>=1.24,<3"
# Exit status 3 means the validator reported findings; the summary is still written.
if [ -n "${SIM:-}" ]; then
  MEM=4G cap "$SIM/validate/bin/python" -I "$HERE/simready_convert.py" --converter "$SIM/convert/bin/usd-convert-cad" \
    --out-dir "$PRIV/simready" --summary "$PARAMS/simready-deck-plate.json" \
    --existing-stage "$PRIV/935-head-twin.usdc" --existing-stage-summary "$PARAMS/simready-validate-t4-stage.json" \
    "$PRIV/v1-deck-plate.step"
  MEM=4G cap "$SIM/validate/bin/python" -I "$HERE/simready_convert.py" --converter "$SIM/convert/bin/usd-convert-cad" \
    --out-dir "$PRIV/simready" --summary "$PARAMS/simready-ports.json" \
    "$PRIV/simready/step/v1-port_y_minus.step" "$PRIV/simready/step/v1-port_y_plus.step"
  MEM=4G cap "$SIM/validate/bin/python" -I "$HERE/simready_convert.py" --converter "$SIM/convert/bin/usd-convert-cad" \
    --out-dir "$PRIV/simready" --existing-stage "$PRIV/935-head-twin-cad.usdc" \
    --existing-stage-summary "$PARAMS/simready-validate-cad-stage.json" || [ $? -eq 3 ]
  for form in usda usdz; do
    MEM=4G cap "$SIM/validate/bin/python" -I "$HERE/simready_convert.py" --out-dir "$PRIV/simready-asset-$STAMP" \
      --existing-stage "$PRIV/simready-asset-$STAMP/part.$form" \
      --existing-stage-summary "$PARAMS/simready-validate-asset-$form.json" || [ $? -eq 3 ]
  done
  for part in v1-deck-plate:v1_deck_plate:simready-deck-plate simready/step/v1-port_y_minus:v1_port_y_minus:simready-ports \
              simready/step/v1-port_y_plus:v1_port_y_plus:simready-ports; do
    IFS=: read -r step stage summary <<<"$part"
    cap "$PY" -I "$HERE/simready_check.py" "$PRIV/$step.step" "$PRIV/simready/$stage.usdc" "$PARAMS/$summary.json"
  done
fi
