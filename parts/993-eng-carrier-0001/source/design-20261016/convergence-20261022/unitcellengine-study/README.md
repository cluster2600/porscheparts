# Shared-factor periodic-cell experiment

This isolated Linux experiment uses
[UnitcellEngine](https://github.com/unitcellhub/unitcellengine/tree/57d64b58224953d9d3a4372618b4b8b50c1227e6)
commit `57d64b58224953d9d3a4372618b4b8b50c1227e6` (Apache-2.0).
It calls the upstream direct SPD solver with all six right-hand sides in one
call. It does not replace the carrier solver or generate a cellular part.

Use a private working directory. Download the codeload tarball for that commit;
its SHA-256 is
`d3352d0d5bcf0e88a420b5c535a883e06e46bef8fd8260c6e7538a75750c81d2`.
Verify it before extraction. Put the unmodified package under `source/`, with
`source/src/unitcellengine/analysis/internal.py` alongside these two scripts.
That file's SHA-256 must be
`429670160c00f7218cb19375e4ce081c9e35033e4ea773c98249d1f706da9e99`.
Retain the upstream licence. Do not import supplier meshes or examples.

The actual private environment uses Python **3.11.13**, NumPy 1.26.4, SciPy
1.14.1, numba 0.60.0, pandas 2.2.3, pyamg 5.2.1, pypardiso 0.4.6,
mkl-service 2.4.2, pyvista 0.44.1, scikit-image 0.24.0, vtk 9.3.1,
trimesh 4.5.1, plotly 5.24.1, tables 3.10.1, gmsh 4.13.1, dill 0.3.9,
unitcellsdf 0.0.2 and MKL 2025.2.0. Install these in a private virtual
environment, then install the pinned source with `pip install --no-deps ./source`.
The published environment receipt identifies actual module files; it is not a
portable lock of every transitive dependency.

Set `MKL_NUM_THREADS=8`, `MKL_THREADING_LAYER=GNU`, `MKL_DYNAMIC=FALSE`,
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`. Use Linux, at least 56 GiB
available quota and eight CPUs, with a 48 GiB per-process address-space cap.
Every command requires a fresh output directory. Bound each process externally
with `timeout --kill-after=10 600` and collect its actual exit status.

```bash
python run_shared.py 4 1e-6 solid upstream-soft original
python run_shared.py 4 1e-6 solid adapted-soft adapted
python run_shared.py 4 1 solid adapted-solid adapted
python run_shared.py 16 1e-6 gyroid adapted-n16 adapted
```

The original uniform soft-material control deliberately exposes the difference
between the assembly regularization and the upstream raw-density tensor
postprocessing. The adapted mode writes a separate operator copy and changes
only that postprocessing scale to match the assembled operator. Its SHA-256 is
`f71812c8a245a377a277320a66584306896a24700ca9d9237c5587fef904438c`.
The pinned original stays intact. This adaptation qualifies this ersatz
experiment, not every upstream geometry or density convention.

`run_shared.py` independently reconstructs the trilinear shape gradients,
all eight integration-point stress tensors for each of the six actual cases,
internal energies, physical nodal forces and periodic force balance. It also
records the actual six-RHS call and its full symmetric-matrix residual.
`stress-all-ip.npy` and `fields.npz` retain the full fields outside Git.
Unit macroscopic strain is a linear coefficient normalization; comparison to
the CCX reference scales it to amplitude 0.001.

Before any N=64 run, place the separately generated complete CCX N=16 fixture
in `n16-ccx-gold.npz` and run `python compare_gold.py`. Its published provenance
binds every original DAT file. The script explicitly maps both shear-component
order and Gauss-point order and compares **every physical node and all stress
integration points in all six cases**, using the unchanged U/S/RF limits.
The first comparison implementation mixed NumPy advanced indices and was
refused; the retained implementation uses explicit axis-preserving slices.

Only after those controls pass:

```bash
python run_shared.py 64 1e-4 gyroid adapted-n64-floor1e-4 adapted
python run_shared.py 64 1e-6 gyroid adapted-n64-floor1e-6 adapted
```

Compare the complete tensors against N=48 and each other under the existing
2% refinement / 1% void-floor conditions, with two successive passing spatial
comparisons. Backend repetitions do not count as mesh refinements. Preserve
all failed controls and resource refusals. See the
[English evidence report](../../../../../../docs/reports/carrier-convergence-20261022/README.md).
