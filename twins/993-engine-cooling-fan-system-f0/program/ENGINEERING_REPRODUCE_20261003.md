# Reproduce the engineering iteration

[Criteria](ENGINEERING_ITERATION_20261003.md) · [Actual results](ENGINEERING_RESULTS_20261003.md) · [Public receipts](../results/engineering-iteration-20261003/)

Use a clean branch/work directory. Existing dirty user checkouts and old
evidence must remain intact. The exact two compressed inputs are **original
parametric project outputs**, not the private scan. Their unpacked digests are
checked against the intake, modal and manufacturing preparation records.
The original full-resolution input's archived audit is preserved separately;
the supplied 50,000-face analysis surface is the input for these new runs.

## Existing runtimes

The runs used installed Python 3.12.11, NumPy, trimesh, PyMeshLab
2025.7.post1 and OpenUSD 0.26.8 on the Mac. Gmsh 4.12.1 and OpenFOAM
Foundation 13 were native amd64 in the existing image:

```text
ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f
local image ID sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696
```

CalculiX 2.17 used the existing engineering-worker image:

```text
sha256:1dc508c2bfab4d9911707fbfd9cacdf43faf84956a1502805194e3e70e18ae68
```

The independent benchmark also ran in native CalculiX 2.23, then in the same
2.17 container as the part. No new package, image pull, GPU access or paid
worker is part of this reproduction. Use an already available compatible
runtime; report an unavailable dependency instead of silently substituting it.
Qwen shares these machines. At most one heavy engineering job on Kali2,
four CPUs / 6 GiB, with local diagnostics limited to two threads.

## Prepare exact inputs and modal decks

Run from the repository root. `PYTHON` must name the appropriate existing
Python environment for each stage; the preparation/parser uses NumPy only.

```sh
FAN=twins/993-engine-cooling-fan-system-f0
RUN=work/impeller-reproduction
mkdir -p "$RUN/input"
gzip -dc "$FAN/results/engineering-iteration-20261003/inputs/candidate-centrifugal.inp.gz" > "$RUN/input/rotor.inp"
gzip -dc "$FAN/results/engineering-iteration-20261003/inputs/candidate-analysis-mm.stl.gz" > "$RUN/input/rotor-mm.stl"
"$PYTHON" "$FAN/source/prepare_engineering_sensitivities.py" modes \
  "$RUN/input/rotor.inp" "$RUN/modes" --rpm 0 3000 6000 10000
```

Solve each case sequentially in the existing worker, with no network, image
pull, ports or persistent services:

```sh
docker run --rm --pull never --network none --user "$(id -u):$(id -g)" \
  --cpus 4 --memory 6g --cap-drop ALL --security-opt no-new-privileges \
  -e OMP_NUM_THREADS=4 -e CCX_NPROC_EQUATION_SOLVER=4 -e CCX_NPROC_RESULTS=4 \
  -v "$ABSOLUTE_RUN:/work" --entrypoint /bin/bash "$CCX_IMAGE" \
  -c 'set -e; for rpm in 0 3000 6000 10000; do cd /work/modes/rpm-$rpm; test ! -e log.ccx; ccx rotor > log.ccx 2>&1; done'
"$PYTHON" "$FAN/source/summarize_engineering_sensitivities.py" modes "$RUN/modes" "$RUN/modes-summary.json"
"$PYTHON" "$FAN/source/render_rotating_frequency_samples.py" "$RUN/modes-summary.json" "$RUN/modes.png"
```

`ABSOLUTE_RUN`, `CCX_IMAGE` and `MESH_IMAGE` are explicitly chosen from the
existing authorized runtime/work directory. Private hostnames, keys and
addresses are not embedded in the project. Container directories use the
current host user so mode-700 private run directories can be read without
additional container capabilities.

## Manufacturing sensitivity and checks

```sh
"$PYTHON" "$FAN/source/prepare_engineering_sensitivities.py" eigenstrain \
  "$RUN/input/rotor.inp" "$RUN/flat-zero" --strain 0 --direction 0 0 1
"$PYTHON" "$FAN/source/prepare_engineering_sensitivities.py" eigenstrain \
  "$RUN/input/rotor.inp" "$RUN/flat" --strain .001 --direction 0 0 1
"$PYTHON" "$FAN/source/prepare_engineering_sensitivities.py" eigenstrain \
  "$RUN/input/rotor.inp" "$RUN/edge" --strain .001 --direction 1 0 0
"$PYTHON" "$FAN/source/prepare_engineering_sensitivities.py" eigenstrain \
  "$RUN/input/rotor.inp" "$RUN/flat-half" --strain .0005 --direction 0 0 1
```

Use the same bounded container and run `ccx rotor` once in each new case.
Run the published `lpbf/unit-eigenstrain.inp` benchmark in a new directory
before accepting this API; its released solution must equal `U=-0.001*x` and
zero stress within the declared limits. Summarize **both** attached and
released fields, never just the final nodal extrapolation:

```sh
"$PYTHON" "$FAN/source/summarize_engineering_sensitivities.py" eigenstrain "$RUN/flat" "$RUN/flat-summary.json"
"$PYTHON" "$FAN/source/export_eigenstrain_fields.py" "$RUN/flat" "$RUN/flat.usdc" "$RUN/flat.png" "$RUN/flat-usd.json"
```

The USD command uses actual native nodes, boundary subtriangles and released
vectors at scale one. It checks generic USD validators and writes an explicit
unqualified report. It does not invoke an NVIDIA physics solver or SimReady
property assignment. Keep native `.dat`, `.frd`, `.eig`, input and solver logs
in the private run archive even when only summary receipts are committed.

## Geometry and mesh experiments

Strict regularization and E-R1 design revision are distinct commands and
criteria. Neither advances physical fit:

```sh
"$PYTHON" "$FAN/source/prepare_quality_fluid_mesh.py" surface \
  "$RUN/input/rotor-mm.stl" "$RUN/strict" --edge-mm 1.5 --distance-mm .1 --iterations 1
"$PYTHON" "$FAN/source/prepare_quality_fluid_mesh.py" design-surface \
  "$RUN/input/rotor-mm.stl" "$RUN/er1" --edge-mm 1.5 --distance-mm .25 --iterations 5
```

In the existing native OpenFOAM/Gmsh container, first run
`surfaceCheck -checkSelfIntersection` on the corresponding **meter** surface.
Reject intersections. Generate a new volume and test the actual standard and
extended gates; all listed volumes were rejected, so there is deliberately no
flow-solver command:

```sh
python3 /source/prepare_quality_fluid_mesh.py volume /work/strict/rotor-mm.stl /work/strict-volume --algorithm 1
bash /source/run_quality_mesh_qa.sh /work/strict-volume/fluid.msh /work/strict-qa
python3 /source/prepare_quality_fluid_mesh.py volume /work/er1/rotor-mm.stl /work/er1-volume --algorithm 1 --relocate
bash /source/run_quality_mesh_qa.sh /work/er1-volume/fluid.msh /work/er1-qa
python3 /source/split_boundary_tetrahedra.py /work/er1-volume/fluid.msh /work/er1-split
bash /source/run_quality_mesh_qa.sh /work/er1-split/fluid.msh /work/er1-split-qa
```

`/source` is a read-only mount of the project source directory; `/work` is the
authorized run directory. Use the same no-network, no-pull, four-CPU/6-GiB
container flags. Netgen was tried and found unavailable in this build; its
failure is preserved instead of claiming its optimization was performed.
The internal centroid split preserves boundary triangles but still fails QA.
The experimental polyhedral dual and stale-zone correction are separately
recorded as rejected alternatives, not part of an accepted flow workflow.

## Review checks

```sh
python3 "$FAN/source/check_material_process_import.py"
python3 "$FAN/source/check_engineering_iteration.py"
make fan-program-check
make check
```

The new iteration requires a draft PR review. No merge, hardware release,
printing, order or physical operation is authorized by successful checks.
