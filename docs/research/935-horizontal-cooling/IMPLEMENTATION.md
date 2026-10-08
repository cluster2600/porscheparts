# Reconstruction executed October 5–7, 2026

The coordinator reconstructs surfaces that were actually acquired and produces
editable blade zones, PicoGK exports and an independent review. **The
full rotor and the mechanism are not yet reconstructed or validated.**
The former proxies remain excluded from this reference. The vertical 993
program remains separate.

## Status of the plan steps

| Step | Execution and limit |
|---|---|
| 0 — Environment | Kali2 access, Python computations, .NET 9/PicoGK compilation and FreeCAD exports verified. Kali1 unavailable during the check. No installation or rental. |
| 1 — Geometry | Two originals checked by SHA-256; transformations and inverses kept. Nine blade regions detected without imposing a count. Periodic sections, nine contiguous ranges, three PicoGK resolutions and editable CAD executed. Two acquired zones of the hub now produce open analytic FreeCAD/STEP surfaces: inner cylinder and outer cone. Roots, tips, solid hub and registered back remain to be reconstructed. |
| 2 — Mechanism | The 17 interfaces and the existing load paths are reused. An outer portion of the shaft shows 22 periodic lobes, reconstructed as an open FreeCAD/STEP surface. The October 7 continuation adds a local inspection plane of the support and an acquired portion of bore wall. The other parts, the functional axes and the assembly remain open. No assumed internal gearing. |
| 3 — Air | No reference computation launched: full rotor, housing, clearances, frames/directions and pilot conditions not qualified. |
| 4 — Mechanics | No reference computation launched: solids, connections, loads and properties matching the process not qualified. |
| 5 — Optimization | Waits for a computed reference and the mounting constraints. |
| 6 — PhysicsNeMo | No training: no accepted set of computations. |
| 7 — Twin | The existing functional graph remains a basis; no complete SimReady assembly delivered. The bench protocol is written. |

The suffixes `0.5mm` and `0.21mm` denote the acquisition precisions
declared by the owner. They define neither the OBJ units nor the
machining tolerances. The dimensional values of this campaign remain
in source units or explicitly conditional.

## Environment actually used

Kali2: Linux on ext4, 12 logical processors, about 16 GiB of RAM,
Python 3.14.7, NumPy 2.4.6, SciPy 1.17.1, trimesh 5.1.0,
PyMeshLab 2025.7.post1 and Gmsh module 4.15.2. CalculiX 2.23 responds; its
`-v` option returns 201, which is not a mechanical computation result.
The host's .NET 6 is not sufficient for the `net9.0` program.

The local image already installed is pinned by its **image identifier**:

```text
sha256:fd50c61399fd8b419b8f63b1eaf33dc5bfaeb5e8df5182ff68c3db45dc600c6a
```

It provides .NET SDK 9.0.317, PicoGK Core 26.2.0 and FreeCAD 1.0.2.
The PicoGK runtime reports build `2026-06-05 21:31:47 picogk`.
Its native library requires
`LD_LIBRARY_PATH=/opt/picogk-native/lib:/app`. FreeCAD uses
`/opt/freecad/usr/bin/python`, `QT_QPA_PLATFORM=offscreen` and
`LD_LIBRARY_PATH=/opt/freecad/usr/lib`.
The Python `/opt/geometry-qa/bin/python` contains USD 25.11; this does not qualify
a physical assembly or a complete Omniverse installation.

The other computation image already present contains OpenFOAM 13; its local
identifier is `sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696`.
After loading `/opt/openfoam13/etc/bashrc`, `foamRun -help` works.
This CLI check is not an accepted computation. This distribution uses
`momentumTransport`, with `simulationType RAS` and `model kOmegaSST` for the
chosen model. [OpenFOAM 13 documentation](https://doc.cfd.direct/openfoam/user-guide-v13/turbulence).

The preflight distinguishes the presence of a package, a working import, a
command path and actual execution. OpenMDAO and PhysicsNeMo are not installed
in the Python environments examined. No earlier lock, pinned recipe
or evidence file is modified for this campaign.

## Reproducible commands

The [template case](../../../twins/935-horizontal-cooling-system-f0/reconstruction-case.template.json)
contains empty fields; the coordinates, selection windows and actual paths
are filled in a private copy, after inspection of the scan.

```sh
SOURCE=twins/935-horizontal-cooling-system-f0/source
python3 "$SOURCE/run_reconstruction.py" PRIVATE_CASE.json preflight work/NEW-preflight
python3 "$SOURCE/run_reconstruction.py" PRIVATE_CASE.json surfaces work/NEW-surfaces
```

`surfaces` reuses the repository's readers and preparers: removal of only the
faces that are exactly null, reversible PCA inspection pose, then fitting of
observed cylinders. PCA does not provide the mechanical axes. The receipt keeps
each selected face, the fitted axis and the deviation between the two candidate axes.
All boundary contours and fragments remain available.

The radial cuts are ordered, then fitted with a SciPy periodic spline.
A short gap can be interpolated within the explicitly provided limit,
and each link is recorded. An open, branched or insufficient cut
is rejected. **A rejected cut splits the loft ranges.** This rule
removed two overly long interpolations detected by the deviation map.
The range caps are artificial limits, not measured roots or
tips. The curves and these labels remain in `sections.json`.

Compile the C# program in the local image, with private outputs:

```sh
IMAGE=sha256:fd50c61399fd8b419b8f63b1eaf33dc5bfaeb5e8df5182ff68c3db45dc600c6a
docker run --rm --pull=never --user "$(id -u):$(id -g)" \
  -v "$PRIVATE_ROOT:/data" --entrypoint /usr/share/dotnet/dotnet "$IMAGE" \
  build /data/repo/twins/935-horizontal-cooling-system-f0/source/picogk-section-loft/SectionLoft.csproj \
  -p:PicoGKAssembly=/app/PicoGK.dll \
  -p:BaseIntermediateOutputPath=/data/PRIVATE-obj/ -o /data/PRIVATE-bin
```

The project compiles only `Program.cs`; old `obj` directories
cannot introduce duplicate assembly attributes.
Then fill in the digests of the sections and of the DLL, the private root,
the image identifier and the **hypothetical** mm/source-unit factor.

```sh
python3 "$SOURCE/run_reconstruction.py" PRIVATE-080.json picogk work/NEW-080
python3 "$SOURCE/run_reconstruction.py" PRIVATE-040.json picogk work/NEW-040
python3 "$SOURCE/run_reconstruction.py" PRIVATE-020.json picogk work/NEW-020
python3 "$SOURCE/run_reconstruction.py" PRIVATE-020.json cad work/NEW-cad
python3 "$SOURCE/run_reconstruction.py" PRIVATE-REVIEW.json review work/NEW-review
python3 -m unittest discover -s tests -p test_935_scan_reconstruction.py -v
make check
```

The three PicoGK cases must share the same sections and the same conditional
scale; their resolutions are divided by two. The review case
references the three `artifacts` directories and the SHA-256 of their receipts.
The `cad` step creates ruled BRep lofts from the sampled contours,
in native FreeCAD and STEP; it reopens the files and checks the volume.
It does not turn voxels into analytic machined interfaces.

### Observed analytic surfaces of the hub

The `hub` step takes up the faces of the existing candidate fits. An
axial window and a limit on the axial component of the normals, inspected
and kept in the private case, isolate each range from the transitions and
fragments. No face of the original scan is deleted. The selected
and excluded faces, the two models and their parameters are recorded.

```sh
python3 "$SOURCE/run_reconstruction.py" PRIVATE-HUB.json hub work/NEW-hub
python3 "$SOURCE/run_reconstruction.py" PRIVATE-HUB-CAD.json cad-hub work/NEW-hub-cad
```

The `hub` case references `sections.json`, its digest and that of the surfaces
receipt; it fills in `hub_surface_selections`, `hub_normal_weight` and
`hub_robust_scale_source_units`. The `cad-hub` case then references the new
`hub-surfaces.json` and its digest, with the same qualified FreeCAD image and
an explicitly conditional scale.

One 10° angular sector out of four is held out in the initial frame
common to both fits. SciPy fits a cylinder, then a cone, with
distances and normals, on the other sectors. The cone is kept only
if RMS **and** the 95th percentile improve on the held-out sectors. The distance
is normal to the infinite analytic surface; it excludes the cut edges.
This split serves exploratory model selection within the same scan.
It provides neither an independent measurement nor a dimensional validation.

On the two inspected ranges, the inner cylinder is kept, and the outer
cone reduces RMS by about **34%** and the 95th percentile by about
**29%** relative to the cylinder. A global conical fit including the
transitions did not improve both criteria; it is kept as a
rejected diagnostic. The candidate axes remain distinct, with no coaxiality
imposed and no functional seat identity declared.

FreeCAD produces two open lateral analytic BRep faces, with the
angular interpolations explicitly labeled. No cap and no complete solid
is exported. The re-read STEP preserves their area; the native files
reopen. A tessellation of the **STEP actually exported**, overlaid on the
scan in four private views, checks the transfer of frames. The bounds
of the surfaces are acquisition limits, not measured machined faces.
The two topological components of the rotor are also inventoried:
they do not define two parts, and the small component does not correspond
to the whole back. No arbitrary registration of the back is applied.

The coordinator refuses an existing directory. Each step publishes its receipt
before continuing. On failure, the partial outputs and `failure.json`
are kept. To resume, reuse the verified inputs and choose a
new directory; no resumption replaces a previous attempt.
The CFD, FEA, optimization and training steps are not simulated by
empty receipts: a request for them is rejected as long as they are not implemented.

## First geometric milestone reached, with reservations

The private directory contains four overlaid scan/loft views, the sections of the
nine blades, the cylindrical cuts of the hub, the bidirectional deviations and the
location of all unresolved edges. It also keeps the rejected cuts
and any interpolations. The source files are unchanged.

The independent review uses 18,000 points drawn by area, compared against the
**triangles**, in both directions, with seeds and points saved.
It excludes a margin around the artificial caps. High deviations
remain; the 95th percentile alone therefore does not settle geometric fidelity.
The uncalibrated distances are not compared to a tolerance in mm.

The nine closed ranges show zero self-intersecting faces, zero faces
incident to a non-manifold edge and zero non-manifold vertices in the
MeshLab audit. For the discretization of **these ranges only**, the two final
resolutions give **0.1204%** volume variation and **0.1412%** for the
largest variation of the principal inertias. The inertia is transported to
the origin of the candidate frame, not left at the center of mass.
These results give neither the mass of the full rotor nor its strength.

The rejected attempts are kept: historical Poisson closure and visual
proxy; lofts crossing missing cuts; second FreeCAD B-spline
interpolation giving an invalid BRep. The retained version uses the
sampled contours without a second interpolation. No earlier receipt is
rewritten to present these attempts as accepted.

## Mechanism continuation toward manufacturing, October 6

The multi-view inspection of the Fan Drive keeps the acquired surfaces and the
reversible pose. The large open ring visible in the
[supplier's view](https://www.wolfeclassics.com/shop/p/porsche-935-fan-drive-3d-scan)
belongs to the outer support. Its provisional identification as a pulley
is rejected: it defines neither a pitch diameter nor a drive ratio.
The global fits of the ribbed tube and of this ring remain rejected
trials, with their residuals, selections and programs in the private archive.

An outer zone of the shaft shows **22 repeated lobes**, not a smooth
cylindrical surface. The count results from a comparison of periods
6 to 40 in three distinct axial bands; all three bands retain 22.
This number does not define the gear teeth of the internal angle drive. The cylindrical
envelope serves only to propose the local frame. It is not an accepted
machined seat. The standard, the mating profile, the fits and the actual dimension
of the splines remain unknown.

The final computation examines all faces of the prepared scan; 11,341 faces
satisfy the inspected selection. The profile keeps the coefficients of the
measured harmonics in each band, the training and test faces,
as well as the angular intervals without samples. The largest
gaps in these bands reach about 15–20°. The corresponding surfaces
are explicit periodic interpolations. The held-out sectors are
whole lobes, one out of four, in the same scan. The RMS radial error is
0.107–0.122 source unit; this internal check is neither independent
metrology nor a manufacturing tolerance.

```sh
python3 "$SOURCE/run_reconstruction.py" PRIVATE-DRIVE.json drive work/NEW-drive
python3 "$SOURCE/run_reconstruction.py" PRIVATE-DRIVE-CAD.json cad-drive work/NEW-drive-cad
```

The private case contains the digest of the prepared scan and of its receipt, the
inspected rigid frame, the windows, the bands, the candidate periods and the
sampling. The first partial run remains archived; the final run uses
all faces and three bands fully present in the retained zone.
The second case references the digest of the profile and the same qualified
FreeCAD image. It exports an editable `Part::Loft` and a STEP, **without caps or
complete solid**. The files are reopened; validity, openness and area
are checked. The 1 mm/source-unit factor remains an explicit assumption.

The review actually reads the STEP, tessellates it and overlays it on the scan in
four views. It reuses the existing point–triangle distance computation:
3,000 independent points per direction, uniform in area, with a margin at the
ends of the loft. Scan to STEP: RMS 0.102, P95 0.189 and maximum 0.452
source unit. STEP to scan, keeping the interpolated regions: RMS
0.288, P95 0.398 and maximum 2.138. **The large reverse deviations locate the
missing coverage; they are not removed to accept an interface.**
No mass or strength of a complete shaft is deduced from this surface.

The [check of the 28 pages of FIA record 3076](DIMENSIONS_AND_DETAILS.en.md#what-the-fia-actually-provides)
adds a documentary dimension explicitly excluded from the 935 calibration:
a 245 mm vertical fan with 11 blades. The eight extensions examined do not
resolve the internal interfaces of the horizontal specimen.

### What is actually missing for a manufacturable system

The contract of the 17 interfaces remains incomplete. The acquisitions to obtain
are grouped by what they unlock, without inventing coordinates:

| Independent acquisition | Definition unlocked |
|---|---|
| Two identifiable, non-parallel dimensions per scan, with unit, datum and uncertainty; documented export unit | Physical scale, distortion check and dimensioned drawings. The precision suffixes are not sufficient. |
| Rotor/hub/shaft: seat, face, mating spline profile, retention and stack-up | Rotor mounting and torque transmission; the observed repetition of 22 lobes does not specify the mating pair of parts. |
| Disassembled angle drive or drawings of the same variant: gear teeth, bearing/seal references, seats, preload/clearance, oil supply and return | Internal shafts, gears, bearings, housing machining, lubrication and transmission computations. The scanned exterior does not observe this information. |
| Faces, holes and datums of the support and of its receiver; housing/air guide and clearances, exact engine version for integration | Assembly, fastening, interferences, air passage and installed conditions. The two available OBJ files do not cover this whole set. |
| Speeds/loads and data of the printing process chosen for each part | Strength, fatigue, treatments, machining allowances, inspection and balancing. AlSi10Mg, WE43 and Ti64 remain candidates. |

The program can use these measurements in the private cases and the existing
contracts. At this stage, it does not produce dimensioned manufacturing drawings
or a bill of materials of arbitrary internal elements. The mechanical review and the
documented computations precede the release of loaded parts, then the
measurements of the [bench protocol](BENCH_PROTOCOL.md) establish actual
operation. Complete manufacturing and validation of the system remain open.

## Next steps, dependencies and acceptance criteria

The [independent contract of the 17 interfaces](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
and the [existing input matrix](../../../twins/935-horizontal-cooling-system/data/input-matrix.json)
remain the references. The consolidated research distinguishes historical variant,
commercial kit, generic data and specimen data. An exterior scan
does not provide gear teeth, bearing references, preloads or seals.

1. Finish the rotor regions and segment the drive; classify the
   acquisitions of the back before a justified rigid registration. Obtain two
   independent dimensions per scan to calibrate, with uncertainty and provenance.
   Reconstruct the seats, axes and machined faces as analytic/BRep; close
   missing surfaces only with evidence or an explicitly localized
   interpolation. Volume/inertia convergence < 1% does not replace
   the deviation from the scan or the measurement of the interfaces.
2. Establish axes, directions as viewed, signed ratios, retentions, clearances and load paths.
   Identify the internal components before detailed computation; check
   interferences over a full turn and at the defined temperatures.
3. Prepare an OpenFOAM MRF pilot, k–ω SST, with speed/air/pressure stations
   stated explicitly; no imposed flow value is a predicted flow. Three
   meshes, quality without blocking error, mass imbalance < 0.1%,
   final variation of the averages < 1%, difference between the two finest meshes
   < 3%. Then use a transient computation for the rotor/housing
   interactions. The engine network is added only with its passages/resistances.
4. Gmsh/CalculiX: centrifugal, pressure from CFD, transmission, contacts
   and available thermal. Verify equilibrium and analytical computations,
   convergence of non-singular stresses/displacements < 5% and prestressed
   frequencies < 2%. AlSi10Mg, WE43 and Ti64 remain the first three
   cards; the existing generic WE43 card is a wrought surrogate,
   insufficient for an LPBF limit. Fatigue or property missing: the corresponding
   conclusion is impossible, with no invented value.
5. SciPy optimizes with the reference solvers; OpenMDAO coordinates once
   these calls are available. No automatic differentiation through PicoGK.
   Keep the interfaces and compare useful air at comparable power,
   mass and inertia under the same conditions.
6. PhysicsNeMo 2.2.1, [FullyConnected](https://raw.githubusercontent.com/NVIDIA/physicsnemo/v2.2.1/physicsnemo/models/mlp/fully_connected.py): pressure and torque from parameters
   and conditions. Separate whole geometries between training/test,
   declare the normalization and obtain a normalized error < 5% on each
   of the two outputs. Prohibit extrapolation; recompute the retained
   candidates with the solvers. A failure of the model does not block the solvers.
7. Compose the parts and connections in SI USD with checked conversions,
   results and digests. Deliver bill of materials, drawings and comparison only
   when their inputs are established. The [bench protocol](BENCH_PROTOCOL.md)
   covers speed, torque, flow, pressure, vibration, temperature and oil.

The thresholds above qualify the computations. Allowable speeds, strength
limits, fatigue and balancing come from the part data and from
the mechanical review. **No physical validation and no manufacturing authorization.**

The scans, their derivatives and the parameters that allow their reconstruction
remain private under `work/`. Git receives only programs, tests,
documentation and summaries compatible with the available rights. The private
report keeps versions, digests, transformations, states and limitations.

## Software verification and backup

The eight targeted tests pass with the scientific dependencies of Kali2:
synthetic tilted axis, local gaps, periodic spline, splitting of the
lofts at missing cuts, protections of digests/outputs, scaling laws
of volume/inertia and preservation of failures on resumption. The new
test recovers a synthetic tilted cylinder and cone on disjoint held-out
sectors; it refuses non-finite computation scales and an insufficient angular
split.
Native C# compilation: zero errors, zero warnings. FreeCAD CAD and STEP
reopened; three PicoGK runs and independent reviews executed.

The shaft continuation adds a check of a synthetic 22-lobe periodicity,
with a recorded gap and rejection of incompatible bands:
**nine targeted tests pass**. Its `make check` on ext4 discovers **3,555 tests,
181 skipped**, then all complementary checks pass. The 6,772
tracked files are compared by digest with the control copy.

`make check` passes on an ext4 copy of the files actually tracked by
Git, with `PYTHONNOUSERSITE=1` and `umask 022`: a discovered suite of 3,554 tests
during the October 6 continuation,
of which 181 skipped for optional dependencies, then the complementary checks
of the Makefile. The targeted test is run separately with SciPy/trimesh available.
This separation avoids the host's incompatible personal OCP bindings.
The first October 6 check detected an unnecessary trimesh import when
loading the new test. This import is now limited to reading the
scan; the analytic test uses NumPy/SciPy. The failure and the final accepted log
are kept separately. The geometric parameters before/after this fix
are byte-for-byte identical.
The control archive keeps tracked files even if their path is
ignored by default; the AppleDouble transfer metadata are removed from
this control copy only. No domain file is modified to make
the checks pass. The documentation check finds zero broken links in
804 Markdown files; `git diff --check` passes.

The 80 private files of surfaces, exports and reviews are copied to the Mac and
Kali2 with comparison of all digests. The two original scans
keep their SHA-256. The logs, receipts and previous attempts are kept.
No Vast spending and no physical validation in this campaign.

The [private GitHub archives](https://github.com/cluster2600/porscheparts-935-private)
keep the two originals, all scientific results and earlier attempts,
parameters, CAD, meshes and logs. The October 5 capture is
published in [its archive release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/reconstruction-20261005);
the hub continuation has a
[separate capture](https://github.com/cluster2600/porscheparts-935-private/releases/tag/hub-surfaces-20261006).
The manifests give the digests per file and per archive. The
SHA-256 digests returned by GitHub are compared to the local archives
after publication. The full copies of the public repository are excluded from the
result archives since they are already in Git; the commit of the sources
and their snapshots are kept. These archives do not constitute a
manufacturing qualification. The code and summaries remain in
[public PR #132](https://github.com/cluster2600/porscheparts/pull/132).

## Support: October 7 continuation

The new global trials on the outer ring are kept and rejected
as references: the mixture of two cylinders keeps an RMS of 5.58
source units on its held-out sample; the outer and inner elliptical
selections keep 4.60 and 2.75 units respectively.
These domains and distance definitions differ; these figures are not
a precision comparison on one and the same part. No mounting axis or
diameter is accepted from these trials.

A local window of 28,870 faces of the support provides an **inspection plane**,
with RMS 0.450 and P95 0.863 source unit on held-out spatial tiles.
Its exported rectangle is an artificial inspection limit; it
reconstructs neither a material outline, nor holes, nor a complete mounting face.
The selection keeps the excluded faces. The transformations and their inverses
remain tied to the original receipt of the scan.

This frame makes it possible to select **859 faces of a portion of bore
wall**. On the held-out angular sectors, the candidate cylinder gives
RMS 0.118 and P95 0.221 source unit; the cone does not improve on it. In the fitted
frame, the arc covered by this selection measures 130.20°: the remaining 229.80°
are excluded from the STEP. This does not demonstrate their absence in the complete scan.
The shallow acquired depth and the partial arc do not qualify an axis, a
nominal diameter or a functional fit. The axial limits remain
selection cuts, and no cap is added.

The `support` and `cad-support` steps reuse the existing coordinator and analytic
exporter. The [template case](../../../twins/935-horizontal-cooling-system-f0/reconstruction-case.template.json)
leaves the private selections empty. After inspection, fill in the private
copy, then place the produced JSON and its SHA-256 in `sections` and
`sections_sha256` before the native export:

```sh
SOURCE=twins/935-horizontal-cooling-system-f0/source
python3 "$SOURCE/run_reconstruction.py" PRIVATE_SUPPORT_CASE.json support work/NEW-support
python3 "$SOURCE/run_reconstruction.py" PRIVATE_SUPPORT_CAD_CASE.json cad-support work/NEW-support-cad
```

FreeCAD and STEP are reopened: two open faces, no solid and area
preserved. The BRep arc is checked at three interior points computed in its
source frame and by its independent area formula. The export of the two hub
surfaces is replayed with the same exporter and keeps its checks.
The choice of 1 mm per unit for the export remains **conditional**, and does not
calibrate the scan. The held-out sets come from the same acquisition; they are
not independent metrology or a mounting validation.

A recentered trial keeps RMS 0.109 source unit but shifts the candidate
radius by about 1.8%. This sensitivity to the window reinforces the need
for independent measurements before defining a seat or a fit.
The attempt is kept; it does not silently replace the export.
The ten targeted scientific tests pass with SciPy available.
`make check` passes on ext4: 3,556 tests discovered, of which 181 skipped for
optional dependencies, then the complementary checks of the Makefile.

The programs, cases, figures, FreeCAD/STEP outputs, rejected attempts and receipts
are kept in a [separate private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/support-surfaces-20261007).
The originals remain unchanged, checked by SHA-256. The next inputs
needed for exact mounting remain the independent calibration dimensions,
the references and internal interfaces of the angle drive, then the housing and air
guides of the retained 935 variant. No manufacturing validation is granted.
