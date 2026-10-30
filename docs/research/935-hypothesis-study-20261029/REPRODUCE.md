# Reproduction and phase ledger

This is an executed hypothesis study. The public package contains auxiliary
source code and aggregate results. The purchased scan, derived geometry,
native fields and exact boundary masks are private prerequisites. A public
checkout alone cannot reproduce those confidential inputs.

Use new output directories. The geometry drivers deliberately refuse an
existing output directory. Keep the original OBJ, both frozen reconstruction
arrays and the source-frame array unchanged. Use millimetres for geometry and
CalculiX; the OpenFOAM and Adamantine adapters explicitly convert to metres.
`source-frame-ABC.npy` stores axes as rows: `source @ frame.T` is intentional.

## Runtime

- Mesh/CFD container:
  `ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
- Gmsh reports runtime 4.12.1. Its installed Python distribution reports
  4.12.1.dev1; these are separate version strings.
- OpenFOAM 13, build `13-18870c24d21c`.
- CalculiX 2.23, direct SPOOLES solver. The retained package SHA-256 values are
  `709b2d994699168f2754bd16117d51cef3241e268a7dfab185b8f78c98bd02aa`
  and `e82c4173706d831a490439bf5b31dae5194dca07482ac8632bc219514372ac3c`.
- CGAL 5.6 exact-predicate/exact-construction kernel, GMP and MPFR; compile
  `exact_union.cpp` and `slice_exact.cpp` with C++17 and `-lmpfr -lgmp`.
- PicoGK was invoked from the existing Kali witness assembly in a .NET 9
  console project. `Program.cs` is the executed construction/slicing driver.
- Adamantine uses the existing native Kali build. Its executable SHA-256 is
  `e7637a1a3729f82c0b11a9a1864fd96b7fbdee9408ede0aad5b59e573699b959`.
  The retained build provenance refers to baseline
  `3990489a10902912889617856f6e2e097d52a412` and author runtime image
  `rombur/adamantine@sha256:a7c394fb9075ea8343f0ed1734574a5d158563e6f2b71894cdcc9f5f75d6e4d9`.
  The deployed build directory is not a Git checkout; the executable hash,
  native input decks and retained build provenance identify this run.
- Qwen's coupon proposal records adapter SHA-256
  `2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f`
  and base SHA-256
  `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58`.
- Independent contour checks use Shapely 2.1.2 / GEOS 3.13.1. The optional
  component-layer union uses Pyclipper 1.3.0.post6 (Clipper 6.4.2).

The private archives retain native inputs, logs, installation receipts and
runtime details. No software version or successful exit establishes physical
qualification.

## Phase ledger

| Phase / requirement | Concrete inputs and runtime | Command or retained native case | Outputs and independent checks | State / remaining limit |
|---|---|---|---|---|
| H01 — preserve identity | Original OBJ; frozen fine/coarse NPZ; owner-confirmed mm scale | Rehash original and compare source arrays using the existing scan-repair workflow | Frozen hashes; two-direction observed-surface distance samples | Preserved; unobserved geometry and specimen identity are not established |
| H02 — retain functional interfaces | Existing partial FreeCAD sources and observation ledger | Existing native CAD verification receipt | Planes, curves, datums, observed feature inventory | Partial; clamping, seals, seats, guides, threads and port interfaces have no complete measured tolerance contract |
| H03 — Qwen/PicoGK trial | Bounded coupon prompt; fine envelope; fixture hypotheses; .NET 9/PicoGK | `dotnet run --project BuildCandidate.csproj -- INPUT_STL HYPOTHESES NEW_OUTPUT` | Native VDB/STL/CLI and independently counted defects | Executed; PicoGK output rejected for degenerate/nonmanifold geometry; Qwen did not reconstruct the whole head |
| H04 — precise reference export | Frozen fine NPZ and rigid frame; NumPy/libigl | `python source/validate_build_final.py ALIGNED_HEAD_NPZ NEW_OUTPUT` | Independent intersections, edge/winding/vertex checks, complete 3MF coordinate/index round trip | Reference geometry checks pass; physical fidelity is still conditional |
| H05 — support geometry | Validated head, fixture hypotheses, independent rays | `python source/build_component_3mf.py HEAD_NPZ HEAD_REPORT HYPOTHESES NEW_OUTPUT` | 1,202 checked resources; positive axial contact for every support; connected union graph; full 3MF readback | Composite export passes; removal, minimum walls and process support adequacy remain unqualified |
| H06 — merged Boolean trial | Exact source and 48-sided provisional fixtures; CGAL | `python source/prepare_exact_union.py SOURCE FRAME HYPOTHESES NEW_OUTPUT --fixtures-world`; then `exact_union` | Native union logs and analytic overlapping/contained-cube controls | Both 2,400 s trials timed out; no merged output accepted; validated composite retained |
| H07 — contours | Validated aligned head; 0.03 mm slice spacing; CGAL/GEOS | `slice_exact HEAD_OFF .03 HEAD_CLI REPORT`; `python source/validate_cli.py HEAD_CLI REPORT --volume-mm3 1106441.267102852 --layer-mm .03` | Every layer, orientation, closure, disjoint contour boundary, and independent integrated-volume comparison | All head contours pass; supported unions and full file readback pass; no machine exposure/hatch profile |
| H08 — volume meshing | Same frozen coarse boundary; Gmsh | `python source/mesh_solid.py COARSE_NPZ NEW_OUTPUT --size SIZE --threads 16` for 2, 1.5, 1 mm | Positive tetrahedra, volume and SICN distributions | All three generated; very poor boundary elements prevent an engineering-quality claim |
| H09 — elastic and conduction controls | Independent cube; CalculiX direct solver | Retained `cube-fea` input decks and assessment | Analytical displacement and ±15 W conduction checks | Controls pass; iterative elastic trial was rejected |
| H10 — head mechanics/thermal | Tetrahedral arrays, frame and explicit surrogate loads/material | `prepare_fea.py`; native `pressure-direct.inp`, `thermal-direct.inp`; `assess_fea.py` | Native FRD/DAT, force/heat balances, actual field statistics | Pressure 2/1.5 mm and thermal 2/1.5/1 mm complete; 1 mm pressure timed out with no accepted solution |
| H11 — combined loading | Completed pressure/thermal cases | `python source/prepare_thermomechanical.py CASE`; native `thermomechanical.inp` | Actual displacement/stress fields and common-boundary comparison | 2/1.5 mm complete; stress maxima and spatial convergence are unresolved |
| H12 — external air | Centre-sampled 4 mm obstacle; refined uniform 2 mm fluid grid; OpenFOAM 13 | Retained `0/`, `constant/`, `system/`; `checkMesh -allTopology -allGeometry`; 28-rank `foamRun -parallel` | 6,593,936 cells; all physical-boundary fluxes and between-checkpoint field changes | Strict mesh check passes; conservation and stationarity are separate gates; no engine CHT |
| H13 — additive thermal/mechanical hypothesis | 4/2 mm solid voxels; 500 K initial, 300 K ambient; Adamantine | `prepare_adamantine.py`; native `cooldown.info`; `assess_cooldown.py` / `assess_cooldown_mpi.py` | 20 s native VTU fields; independent volume, exterior area and energy integration | Three complete cooldown cases; no laser, deposition, calibrated LPBF or full build simulation |
| H14 — recovery/publication | Owned cloud outputs, file manifests, native Kali checkout | Fresh archive extraction, per-file SHA-256 checks and repository checks | Private deliverables, public aggregates/sources, closeout receipts | Qualification flags remain false; no supplier mail, scan transfer to a supplier or fabrication order |

## Supported contour replay

After the validated head-only CLI is generated, run the layer unions in bounded
parallel batches. Each layer is clipped with integer Clipper geometry and
compared with an independent GEOS union of the original head cross-section and
analytic fixture sections. The private serial prefix is optional; when supplied,
all its complete layers must match byte for byte.

```sh
python source/union_component_layers_parallel.py HEAD_CLI HYPOTHESES NEW_OUTPUT --workers 8
python source/validate_cli_readback.py NEW_OUTPUT/935-supported-30um.cli READBACK_JSON \
  --volume-mm3 INDEPENDENT_LAYER_VOLUME_FROM_REPORT --layer-mm .03 \
  --volume-reference-kind independent-layer-integral
```

The second volume reference is explicitly a layer integral, not an exact 3D
Boolean volume. This reader reparses every coordinate written to disk, rejects
intersecting or touching contours, and uses a 10⁻¹⁰ relative volume-readback
limit. The separate head-only surface-volume check uses the declared 0.2%
limit. Successful export does not add exposure or hatching parameters.

## Replaying the numerical cases

The native recovered case is authoritative for the final solver settings.
Some early preparation drivers intentionally generated candidates that were
subsequently rejected or changed. In particular, `prepare_fea.py` originally
wrote iterative decks; the retained `*-direct.inp` files select the direct
solver. `prepare_foam.py` describes the earlier snappy candidate; the accepted
mesh instead starts with `uniform_air_mesh.py --pitch-mm 4`, uses `gmshToFoam`
and global `refineMesh -overwrite`, and retains the strict mesh check. Do not
substitute a freshly generated initial candidate for a verified final case.

For each retained CalculiX case, run `ccx pressure-direct`, `ccx thermal-direct`
and, when present, `ccx thermomechanical`, then:

```sh
python source/assess_fea.py TETRAHEDRAL_ARRAYS CASE_DIRECTORY
```

Pressure, force and conduction units are defined in the input decks. The
thermal adapter uses conductivity in W/(mm K), while the hypothesis table
states W/(m K). Do not change one without the explicit factor of 1,000.

For OpenFOAM, source the pinned runtime's `etc/bashrc`, use the retained
decomposition/configuration and compare the two recorded checkpoints:

```sh
checkMesh -allTopology -allGeometry > checkMesh-replay.log 2>&1
mpirun -np 28 foamRun -parallel > solver-replay.log 2>&1
python source/assess_cfd.py CASE_DIRECTORY assessment-replay.json \
  --time 600 --previous 550 --mesh-check ORIGINAL_STRICT_CHECK_LOG
```

The independent integrator checks the uniform face/cell metrics and field
dimensions before calculating fluxes. Its predeclared gates require relative
mass imbalance below 0.001, heat imbalance below 0.01, velocity L2 change below
0.001, temperature RMS change divided by 100 K below 0.001 and temperature
bounds of 300–400 K. A balance pass does not override a stationarity failure.

Adamantine ran in the existing rootless runtime with four MPI ranks,
`--mca btl self,vader`, one OpenMP/OpenBLAS thread per rank, and the task bound
to `/tmp/935`. Run the native executable with
`--input-file cooldown.info --output-dir output`, then its matching independent
VTU assessor. Preserve the absolute task paths in the deck through that bind,
or explicitly relocate them. Use volume 1,100,608 mm³ for the 4 mm grid and
1,110,200 mm³ for the 2 mm grid. These are discrete numerical solids, not new
measurements of the specimen.

The coupon, supports, material and loads are replaceable hypotheses. Changing
them requires new outputs and checks; it does not alter the frozen scan or
retroactively qualify the existing results.

## Interpretation

Consult the [main report](../935-hypothesis-study-20261029.md) for measured
results and failures. The attached hardware remains merged into a homogeneous
study body. Full internal geometry, machining allowances, support removal,
powder evacuation, actual alloy/high-temperature laws, fatigue, machine build
parameters and professional engineering acceptance remain separate work.

The architecture follows the existing
[scan-repair workflow](../../architecture/scan-repair-workflow.md) and
[architecture governance](../../architecture/README.md). H01–H07 address
geometry/export reproducibility; H08–H13 address explicitly scoped numerical
cases; H14 binds their evidence and recovery. None grants engine release.
