# Optional USD BRep and LPBF research tools

Decision date: 2026-10-28. Owner requested installation and integration into the
existing [toolchain](../TOOLCHAIN.md). These are software witnesses on synthetic
inputs, not accepted Porsche geometry or qualified manufacturing processes.

## Requirements, allocation and acceptance

| Requirement | Application service and deployment | Acceptance command | Scope |
|---|---|---|---|
| R-BREP: reproducible solid operations and USD exchange | A-BREP: NVIDIA USD BRep 1.0.1; local Linux container | `make container-usd-brep container-smoke-usd-brep` | Analytic primitive volumes, Boolean difference, export/import volume and output hash |
| R-LPBF-FE: evaluate multilevel thermal tooling | A-LPBF-FE: GO-MELT; isolated Python 3.10 CPU environment | `make go-melt-smoke` | Upstream FE kernel: partition of unity, unit volume, equilibrium, prescribed heating and source-free energy conservation |
| R-LPBF-DEM: evaluate particle thermal tooling | A-LPBF-DEM: Simulation-of-LPBF-using-CUDA; local C++ compiler | `make lpbf-cuda-cpu-smoke` | Rebuild CPU thermal/deposition programs; check equilibrium, heat-flow sign, pairwise conservation and disconnected particles |

PicoGK remains A-CAD for new engine geometry. Existing build123d/STEP masters
remain authoritative for their own revisions. A-BREP is an optional exact-solid
service alongside A-USD preparation, not a voxel-to-BRep converter. None of the
new tests converts a PicoGK mesh or a catalogue part into a qualified solid.

A-LPBF-FE and A-LPBF-DEM are optional research services under manufacturing
preparation. They do not replace OpenFOAM/CalculiX, AdditiveFOAM, the material
cards, independent geometry inspection or the approved qualification plan.
No automatic exchange adapter between these tools is provided: USD geometry,
GO-MELT structured meshes/toolpaths, and particle positions/radii have different
contracts. New adapters require a separately verified units and provenance map.

Before any real LPBF run, register the exact source revision, geometry or
particle bed, units, material/phase laws, laser/toolpath, boundary conditions,
mesh/time convergence and coupon correlation. Keep thermal fields in the
solver format and link hashes to review layers. Missing inputs block a part run.

## NVIDIA USD BRep

- Upstream: <https://github.com/NVIDIA-Omniverse/usd-brep>, Apache-2.0.
- Version 1.0.1, CPython 3.12; Linux ARM64 and AMD64 wheel hashes are pinned in
  `containers/usd-brep.requirements.txt`. Base image is pinned by digest.
- The wheel embeds OpenUSD 25.11. Keep it separate from other USD Python
  runtimes; upstream explicitly warns against loading `usd-core==25.11` in
  the same process. Do not add it to the existing Omniverse image.
- macOS has no official wheel. Docker uses Linux ARM64 on Apple Silicon.

```sh
make container-usd-brep
make container-smoke-usd-brep
# Preserve earlier receipts when repeating:
make container-smoke-usd-brep USD_BREP_RUN=usd-brep-second-run
```

The image accepts Python arguments. To run a reviewed script:

```sh
docker run --rm --network none --read-only --tmpfs /tmp \
  -v "$PWD/work:/work" 3dprinting993-usd-brep:1.0.1 /work/my_script.py
```

The witness subtracts one octant from a unit sphere. Expected volume is 7π/6;
integration accuracy is 1e-7 and relative acceptance tolerance is 1e-6.
It exports `cut.usda`, reloads it and checks the volume again. Its modeling
units are synthetic, not millimeters from a measured part. The output is not
a SimReady review bundle: unit/axis/default-prim and relocated semantic checks
remain required before that handoff.

The wheel logs missing `pxr` Python modules during USD operations on the local
installation; the round-trip still passes. The optional NVIDIA validation
extra is unavailable on Linux ARM64. No visual or SimReady validation is claimed.

## GO-MELT

- Upstream: <https://github.com/JLnorthwestern/GO-MELT>, MIT.
- Source revision: `7dafdd8593711cf8ac6ccb18a1f475744610ea3d`.
- CPU profile preserves JAX/jaxlib 0.4.16, NumPy 1.24.1 and SciPy 1.9.0;
  all dependencies and distribution hashes are in
  `benchmarks/go-melt/requirements.lock.txt`.
- `ml-dtypes==0.2.0` is explicitly pinned for this historical JAX release.
  Old jaxlib wheels require the official JAX archive below.

Fresh installation (the Mac installation already uses these default paths):

```sh
git clone https://github.com/JLnorthwestern/GO-MELT "$HOME/Developer/GO-MELT"
git -C "$HOME/Developer/GO-MELT" checkout --detach 7dafdd8593711cf8ac6ccb18a1f475744610ea3d
uv venv --python 3.10 "$HOME/Developer/GO-MELT/.venv"
uv pip sync --python "$HOME/Developer/GO-MELT/.venv/bin/python" \
  --require-hashes --find-links https://storage.googleapis.com/jax-releases/jax_releases.html \
  benchmarks/go-melt/requirements.lock.txt
make go-melt-smoke
```

Override `GO_MELT_SOURCE`, `GO_MELT_PYTHON` and `GO_MELT_OUTPUT` for other
locations. The witness verifies the imported kernel hash and forces CPU/x64.
An insulated unit cube at 300 stays at 300; a uniform source of 4 with heat
capacity 2 and time step 0.01 yields 300.02. A nonuniform field diffuses while
preserving the total nodal temperature for this equal-mass cube.

This does not exercise the multilevel moving meshes, G-code reader, phase
transitions or full laser scan. Upstream's CUDA dependency list is a different
profile, not installed or qualified by these commands. Do not claim GPU speedup
from the CPU witness or install its historical CUDA stack into Qwen/MLX.

## Simulation-of-LPBF-using-CUDA

- Upstream: <https://github.com/zhangyaqi1989/Simulation-of-LPBF-using-CUDA>, MIT.
- Source revision: `b81c9a0d8abae302c9a4eeacf384502d2220d360`.
- Research code for particle deposition and single-pass particle heating,
  originally documented with GCC 6.4 and CUDA 9.0.

```sh
git clone https://github.com/zhangyaqi1989/Simulation-of-LPBF-using-CUDA \
  "$HOME/Developer/Simulation-of-LPBF-using-CUDA"
git -C "$HOME/Developer/Simulation-of-LPBF-using-CUDA" checkout --detach \
  b81c9a0d8abae302c9a4eeacf384502d2220d360
make lpbf-cuda-cpu-smoke
```

Override `LPBF_CUDA_SOURCE` and `LPBF_CUDA_OUTPUT` as needed. The test compiles
from source into a fresh output directory, never runs bundled upstream binaries
or overwrites upstream result files. It verifies the revision and rejects tracked
source changes. `report.json` records compiler and binary hashes.

Only CPU builds and the small thermal control are exercised. Full deposition,
100,000-step laser scans, CUDA builds and CPU/GPU agreement remain unexecuted.
Source inspection also finds floor conduction disabled in the CPU scan and a
high-temperature capacity branch returning the transition capacity above boiling.
Those model choices need review before a physical application; no patch or
qualification of that model is implied by installation.

## Receipts, CI and boundaries

All witnesses require a fresh output directory. A failed or interrupted run
must not be relabeled as success; retain its logs and use a new output name.
The success report is written only after the numerical controls complete.
`make check` remains the repository gate. The separate
`.github/workflows/geometry-lpbf-tools.yml` runs actual optional runtimes on Linux
and uploads their reports; ordinary catalogue checks need no optional packages.

Local execution on 2026-10-28 passed USD BRep under Linux ARM64 Docker, GO-MELT
on the Mac CPU, and LPBF-CUDA's CPU builds under Apple Clang 21. Logs and reports
are kept under ignored `work/`, and the durable local installation receipt root
is `$HOME/Developer/PorschePartsArtifacts/geometry-lpbf-20261028`.
CI is separate evidence for Linux AMD64, not evidence of a CUDA run.

No GPU rental, image publication, real-part calculation, material approval or
manufacturing release is part of this integration. NativeCAD remains a separate
local evaluation pending an export-capable research key; it is not a required
dependency of any of these three routes.
