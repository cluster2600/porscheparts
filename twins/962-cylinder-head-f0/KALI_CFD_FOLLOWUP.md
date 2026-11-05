# 4 L water circuit: checks actually executed on kali1

The OpenFOAM check has now been executed. **The tetrahedral mesh is
rejected; no hydraulic solve has started.** The two polyhedral derivatives
tried are also rejected. The SICN success described in the
[previous dossier](COOLANT_MESH_FOLLOWUP.md) remains valid within its scope,
but is not enough to admit the mesh into the solver.

The [execution receipt](derived/kali-cfd-20261025/execution-report.json) links
the inputs, the runtime, the native logs and the archive of the six attempts.
The PicoGK masters, the four valves and the twin ignition are unchanged.

## Execution and input

The IPv6 SSH connection over Thunderbolt to kali1 works, with verification
of the already known host key. Docker is not accessible to the compute account.
An official **OpenFOAM Foundation 13, build 13-cde978a97c93** package is therefore
extracted into the job directory, without a system installation. Its SHA-256
sum is verified against the foundation's signed APT index; the signature,
the index and the package are linked in the receipt. The package is the one of 11 September
2025, and is not presented as the latest available version.

Bubblewrap provides the standard paths `/opt/openfoam13`, a read-only
system, a separate network namespace and a user directory masked except for
the job. Temporary user units limit each attempt to 6 GiB
of memory, no swap, and one CPU core. The host's MPI launcher fails its
own version check; the calculation path retained is therefore sequential.
No system permissions were changed. The work units are terminated.

The input is exactly the saved MSH of 542,188 tetrahedra, in metres,
SHA-256 `b368f5971be2dc559a613175c8e383a86d6dd33a25de8834908cc812af57e903`.
The 18 digests of the prepared case are verified after transfer. Two calls
to `createPatch` actually give the wall the `wall` type, without changing
the boundary-condition names.

The exploratory case keeps **48.6236 L/min per cylinder head**, an assumed density
of 965 kg/m³ and an assumed dynamic viscosity of 0.000315 Pa·s.
The real end section of the mesh at x = −76 mm is **339 mm²**; the
imposed mean velocity would therefore be **2.39054 m/s**. The section at −75.5 mm used
previously is not this end section. The isothermal RANS k–ω SST case
is prepared, with kinematic pressure and first-order upwind schemes.
This flow rate comes from the exploratory SP95 budget and is not a measurement.

## Results kept

| Attempt | Cells | Actual result |
|---|---:|---|
| 001: MSH import and wall typing | 542,188 | Two checks fail: 252 cells below the determinant threshold of 0.001 and five faces below the interpolation weight of 0.05 |
| 002: `polyDualMesh 0 -concaveMultiCells` | 700,751 | Eight checks fail; derivative rejected |
| 003: preparation of the native merge | — | Wrong `-writeSets` syntax, then cell set missing; no merge |
| 004: corrected preparation of the sets | — | `patchToFace` requires `patch`, not `patches`; no merge |
| 005: `topoSet`, then `removeFaces mergeFaces -noFields` | — | Native stop on an illegal two-vertex face; no saved derivative admitted |
| 006: local merge preserving boundary faces | 541,931 | Determinant and interpolation corrected, but four other checks fail; derivative rejected |

In 001, the import contains a single region and the three non-empty patches.
The volume is 0.0001379370876514855 m³, the maximum non-orthogonality
81.9899° and the maximum skewness 2.34484. The two additional defects are
detected by `checkMesh -allGeometry -allTopology`: the SICN minimum above
0.1 does not predict them.

In 006, 257 internal faces are removed. All boundary points and all
oriented boundary faces are preserved exactly by construction.
The determinant minimum reaches 0.00100337 and the minimum interpolation
weight 0.0506967. However, OpenFOAM reports **106 concave cells**, four
faces with a wrongly oriented pyramid, five overly distorted faces and eight faces with
a deficient tetrahedral decomposition. These corrections are therefore not
an acceptable solution.

The native logs [001](derived/kali-cfd-20261025/case-001-log.checkMesh.txt),
[002](derived/kali-cfd-20261025/case-002-log.checkMesh.txt),
[006](derived/kali-cfd-20261025/case-006-log.checkMesh.txt) and
the [native stop of 005](derived/kali-cfd-20261025/case-005-log.removeFaces.txt)
are versioned with only the local path replaced by `<job>`. The originals
remain in the archive, with their own digests.

**The `checkMesh` exit code is not enough: it can be zero despite
`Failed … mesh checks`.** The existing guard `accept_mesh.py` explicitly
requires `Mesh OK.`, rejects failures and checks the patch types.
The sequential and MPI recipes place this guard before the solver.
There is no `serialFoam` or `simpleFoam` log in the attempts kept.

## Sources and preservation

- [Preparation of fields and dictionaries](source/coolant_flow/prepare_kali_case.py),
  then [receipt linking and time limit](source/coolant_flow/prepare_kali_bound_case.py).
- [Initial MPI recipe](source/coolant_flow/run_kali_case.sh) and
  [sequential recipe actually attempted](source/coolant_flow/run_kali_serial.sh).
- [Rejected local merge](source/coolant_flow/merge_flagged_cells.py), using
  the native sets `underdeterminedCells` and `lowWeightFaces`. This
  largest-face selection does not guarantee convex unions; the following
  OpenFOAM check is mandatory.

To reproduce the input, use the already documented native preparation
environment (`CAD_PY` with NumPy, trimesh and Gmsh), then a new output
directory. After a verified transfer, run the recipe in the isolated and bounded
Foundation 13 environment described above:

```sh
SRC=twins/962-cylinder-head-f0/source/coolant_flow
BASE=work/962-coolant-flow
"$CAD_PY" "$SRC/prepare_kali_bound_case.py" "$BASE/mesh-010" \
  "$BASE/surface-004" twins/962-cylinder-head-f0/derived/mezger-sp95-budget.json "$CASE"
# À l’intérieur de l’environnement Foundation 13 :
source /opt/openfoam13/etc/bashrc
bash "$SRC/run_kali_serial.sh" "$CASE"
```

(The comment in the block reads "Inside the Foundation 13 environment:".)

To review the rejection and reproduce the local merge, work on a fresh
copy: `checkMesh -writeSets` writes diagnostics and must therefore not be
rerun in a case already frozen by a receipt. The following variables designate
absolute paths, and `DIAGNOSTICS` as well as `MERGED` must not exist:

```sh
test ! -e "$DIAGNOSTICS" && cp -a "$CASE" "$DIAGNOSTICS"
checkMesh -case "$DIAGNOSTICS" -allGeometry -allTopology -writeSets -setFormat vtk
python3 "$SRC/merge_flagged_cells.py" "$CASE" "$DIAGNOSTICS" "$MERGED"
checkMesh -case "$MERGED" -allGeometry -allTopology
python3 "$MERGED/accept_mesh.py" "$MERGED"
```

The last command must reject the observed candidate; this sequence is not
an admission recipe and does not launch the solver.

The local archive `work/962-coolant-flow/kali-execution-001/kali-cfd-attempts-001.tar.gz`
contains **189 files**, for **166,697,668 bytes**, SHA-256
`49507e98c899a091ddf62887923207505045cc2019c1139f5a9254bd805171f9`.
The local copy is reread in full and the 188 payload digests
are compared with the manifest, itself verified separately. The initial MSH remains
in the previous delivery; its duplicates and the vendor runtime are
not added to this archive. Large files remain outside Git.

## Checks and remaining blocker

The **eight new targeted tests pass**, as does the shell syntax.
The full local `make check` run reaches 4,205 tests: two floating-point
failures in the unmodified fan modules, 29 errors including
SciPy/Pillow loading failures and `hashlib.file_digest` unavailable under Python 3.10,
and 260 skipped tests. It is not green. The cylinder-head run reaches 241 tests,
with two SciPy loading errors and seven skipped tests. These counts
include the tests executed, not only the successes.

CI for the previous commit `9f30cd90` succeeded in
[run 40190361113](https://github.com/cluster2600/porscheparts/actions/runs/40190361113).
This software success covers neither the new files nor CFD admission.

The concrete blocker is now the quality of the OpenFOAM stencil. The next
correction must select convex unions or produce a new
calculation mesh, then preserve the boundary and pass **all** the
checks again before any solve. The thresholds are not relaxed.
Pressure loss, flow distribution, convergence, CHT, SP95 knock,
mechanical strength, fitting on the donor and the 1,000 hp power remain open.
