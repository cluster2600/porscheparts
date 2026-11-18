#!/usr/bin/env bash
# Smoke check of the cae image on the GPU it runs on. Writes one receipt; exits non-zero on the first
# failed gate. Run inside the image:  docker compose run --rm cae
# A pass qualifies the software path on this GPU and driver: imports, CUDA PETSc, the template's
# three witnesses on both backends, Warp and Newton on the device, and an EGL render. Nothing more.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
# SMOKE_OUT is set by onstart-cae.sh, which writes the pulled image's digest (image.json) there first.
OUT=${SMOKE_OUT:-/twin/work/receipts/smoke-cae-$(date -u +%Y%m%dT%H%M%SZ)}
mkdir -p "$OUT"
exec > >(tee "$OUT/smoke.log") 2>&1

nvidia-smi --query-gpu=name,driver_version,compute_cap,memory.total --format=csv | tee "$OUT/gpu.csv"

python3 - "$OUT" <<'PY'
import json, sys, importlib
from pathlib import Path
out = Path(sys.argv[1])
from petsc4py import PETSc
import dolfinx
rec = {"dolfinx": dolfinx.__version__, "petsc": ".".join(map(str, PETSc.Sys.getVersion())),
       "petsc_has_cuda": bool(PETSc.Sys.hasExternalPackage("cuda")),
       "petsc_has_hypre": bool(PETSc.Sys.hasExternalPackage("hypre"))}
for name in ("warp", "newton", "gmsh", "build123d", "trimesh", "manifold3d", "igl", "pyvista", "vtk", "pxr", "pylife"):
    mod = importlib.import_module(name)
    rec[name] = str(getattr(mod, "__version__", getattr(mod, "VTK_VERSION", "imported")))
import warp as wp
wp.init()
rec["warp_cuda_devices"] = [str(d) for d in wp.get_cuda_devices()]
# Warp on the device: a kernel whose answer is known.
@wp.kernel
def square(a: wp.array(dtype=float)):
    i = wp.tid()
    a[i] = float(i) * float(i)
a = wp.zeros(1000, dtype=float, device="cuda:0")
wp.launch(square, dim=1000, inputs=[a], device="cuda:0")
rec["warp_kernel_sum"] = float(a.numpy().sum())
rec["warp_kernel_ok"] = rec["warp_kernel_sum"] == float(sum(i * i for i in range(1000)))
# Newton: one free body falls for 0.5 s under gravity; compare with g t^2 / 2.
import newton
builder = newton.ModelBuilder()
body = builder.add_body(xform=wp.transform((0.0, 0.0, 10.0), wp.quat_identity()))
builder.add_shape_sphere(body, radius=0.1)
model = builder.finalize(device="cuda:0")
solver = newton.solvers.SolverXPBD(model)
s0, s1, control = model.state(), model.state(), model.control()
dt, steps = 1.0e-3, 500
for _ in range(steps):
    s0.clear_forces()
    solver.step(s0, s1, control, None, dt)
    s0, s1 = s1, s0
z = float(s0.body_q.numpy()[0][2])
drop, expected = 10.0 - z, 0.5 * 9.81 * (dt * steps) ** 2
rec["newton_free_fall"] = {"drop_m": drop, "expected_m": expected, "rel_error": abs(drop - expected) / expected}
rec["newton_ok"] = rec["newton_free_fall"]["rel_error"] < 0.01
# PyVista through EGL: a picture with something in it.
import pyvista as pv
import numpy as np
p = pv.Plotter(off_screen=True, window_size=(400, 300))
p.add_mesh(pv.Sphere(), color="orange")
img = p.screenshot(str(out / "egl-sphere.png"), return_img=True)
p.close()
rec["render_window"] = type(p.ren_win).__name__ if hasattr(p, "ren_win") and p.ren_win is not None else "closed"
rec["render_nonblank"] = bool(np.asarray(img).std() > 1.0)
(out / "imports.json").write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps(rec, indent=1))
gates = ["petsc_has_cuda", "warp_kernel_ok", "newton_ok", "render_nonblank"]
failed = [g for g in gates if not rec[g]]
if failed:
    raise SystemExit(f"smoke gates failed: {failed}")
PY

T="$HERE/dolfinx_thermal_mech_template.py"
python3 "$T" witness "$OUT/witness-cpu" --backend cpu
python3 "$T" witness "$OUT/witness-cuda" --backend cuda
mpirun -n 2 python3 "$T" witness "$OUT/witness-cpu-mpi2" --backend cpu
python3 "$T" demo-case "$OUT/demo"
python3 "$T" solve "$OUT/demo/demo-case.json" "$OUT/demo/demo-block.msh" "$OUT/demo/run-cuda" --backend cuda
python3 "$T" render "$OUT/demo/run-cuda"

python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
w = {k: json.loads((out / k / "witness.json").read_text())["passed"] for k in ("witness-cpu", "witness-cuda", "witness-cpu-mpi2")}
r = json.loads((out / "demo" / "run-cuda" / "record.json").read_text())
receipt = {"schema": "935-cae-smoke-receipt/1", "dir": str(out), "witnesses_passed": w,
           "demo_cuda_mat_type": r["heat"]["solver"]["mat_type"],
           "demo_solve_seconds": {"heat": r["heat"]["solver"]["seconds"], "elasticity": r["mechanics"]["solver"]["seconds"]},
           "passed": all(w.values()) and "cusparse" in r["heat"]["solver"]["mat_type"],
           "claims": "the image's software path on this GPU and driver; no head result, no speed claim"}
(out / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
print(json.dumps(receipt, indent=1))
if not receipt["passed"]:
    raise SystemExit("smoke failed")
PY
echo "SMOKE PASSED: $OUT (read every PNG under it before \`vast_deploy.sh admit\`)"
