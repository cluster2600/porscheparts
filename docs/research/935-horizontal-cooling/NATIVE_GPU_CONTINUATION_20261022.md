# 935 native GPU and complete-rotor continuation — October 22, 2026

The root README's software chain remains the order of work: retained scan
observations and explicit assumptions → native PicoGK geometry → independent
geometry and assembly checks → reference solvers → numerical acceptance.
The horizontal 935 reference installation remains the target; the 993 adaptation
is separate. This continuation adds actual CUDA queries, Omniverse assembly
views and independent complete-rotor material/speed comparisons. It does not
establish a fabrication release.

The geometry remains the corrected PicoGK rotor and four-component assembly
recorded in [the complete-system report](COMPLETE_SYSTEM_20261022.md).
The conforming volume and its limitations remain in
[the structural report](CONFORMING_ROTOR_20261022.md). Native commands, derived
study programs, inputs, failed attempts, fields and images are preserved privately.
No raw scan or derived private geometry is added to public Git.
The [machine-readable receipt](native-gpu-20261022.json) binds this continuation
to the source hashes and privately preserved results.

## Complete rotor on CUDA

The unchanged `benchmarks/warp-geometry/mesh_review.py`, `pilot.py` and `kernels.py`
run on an actual RTX 4090, CUDA device 0, with Warp 1.18.0 and NumPy 2.2.6.
The complete target contains 661,475 vertices and **1,322,970 triangles**.
All 6,000 probes are compared with the independently calculated complete-target
Trimesh point-to-triangle reference. There are no missing or invalid queries.
Maximum absolute error is **1.052491e-5 uncalibrated scan units**, against the
predeclared 1e-4-unit query tolerance. This verifies GPU geometry queries;
no application speedup, airflow or mechanical qualification is inferred.
The dedicated Warp image was not published or run. This job uses the previously
qualified PicoGK/Python image by digest, with separate task-local environments;
native PicoGK smoke checks pass again after dependency setup.

## OVRTX assembly inspection

The original 453,762,761-byte USD asset is transferred and checked against
SHA-256 `e13c758d2bc63d3ffab9c0fa6114a3afab94c415999f5be34dbc326a564bc928`.
Its **12,603,066 triangles**, four component identities and geometry are retained.
Presentation opinions are authored in separate USD layers: cameras, lights,
render settings and products. The source asset is unchanged.

The isolated runtime uses the repository's existing OVRTX **0.3.0.312915** pin.
The wheel matches the existing SHA-256
`a6b2b3c357f6487451c8d71e96cc4f83156c08fd9747d10e1b65f3866bed4b8f`;
all **7,324 installed payload files** are independently compared with it.
Python 3.11 uses matching NumPy 2.2.6 and Pillow 12.3.0 wheels; the original
Python 3.12 requirement file and image lock are not edited. USD authoring runs
in a separate environment from OVRTX.

Five render jobs finish successfully on device 0, with 64 accumulation steps
per view. The initial top/side framing is retained as rejected. The accepted
perspective and corrected orthographic top/side images are 1,200 × 1,000 RGBA
pixels, nonblank, hash-checked and visually inspected. The complete installation
fits the orthographic frames. The render worker corrects the earlier station
example's hard-coded device-index receipt and initializes cleanup variables
before entering its protected renderer scope.

The views show the rotor, observed drive, provisional shroud and six-cylinder
packaging context. They also expose remaining scan gaps in the drive. The engine
is still a packaging hypothesis. Colours identify components, not established
alloys. A rendered assembly is not an articulated mechanism, a verified mounting
arrangement or a validated digital twin. Physical calibration remains unresolved:
metre-valued USD coordinates use the declared hypothesis of one millimetre per
scan unit.

## Surface discretization experiments

Analysis-mesh proposals do not change the PicoGK design master. Each retains
its own lineage, rejected variants and declared limits. A watertight result with
similar volume/inertia does not automatically preserve the complete surface.

The independent CGAL 5.5.1 checker tests closure, valid triangle topology and
self-intersection before its continuous symmetric Hausdorff computation. An
identical tetrahedron, a tetrahedron translated by exactly 0.2 units and rejection
of nonpositive algorithm error provide independent controls. Its implementation
uses [CGAL's bounded-error distance API](https://doc.cgal.org/5.5.1/Polygon_mesh_processing/group__PMP__distance__grp.html).
The comparison budget is **0.025 scan units**, including a **0.0025-unit**
algorithm error bound. These are numerical discretization limits, not scanner
accuracy or machining tolerances.

| Proposal | Complete-surface result | Decision |
|---|---|---|
| VTK, 90% target reduction, 132,294 triangles after removing one exactly opposite duplicate face pair | Hausdorff upper bound 1.836783 units; relative volume difference 0.0428%, inertia difference 0.2470% | Rejected |
| VTK, 50% target reduction, 661,484 triangles | Hausdorff upper bound 1.534592 units; relative volume difference 0.1277%, inertia difference 0.0879% | Rejected |

Both original and tested candidate surfaces are closed, valid and free from
self-intersections in the CGAL checks. This does not rescue their failed distance
criterion. A smaller VTK filter-error parameter alone did not prevent the loss.
An envelope-filter simplification stops with `std::bad_alloc` under its explicit
8 GiB address-space limit; a separate 48 GiB attempt reaches its 420-second time
limit. Neither yields an accepted candidate. No rejected or incomplete proposal
is substituted into the reference FEA.

A feature-constrained CGAL proposal has **861,404 triangles**, 34.89% fewer than
the source. Its complete-surface approximation is checked with the new
[tiled envelope checker](../../../twins/935-horizontal-cooling-system-f0/source/analysis-envelope/).
It builds bounded local subsets of the reference envelope and checks every
query triangle, in both directions. Containment in a subset implies containment
in the complete envelope. CGAL documents that its polyhedral envelope is inside
the corresponding Minkowski envelope; a failed containment test alone does not
prove a distance violation. [CGAL 5.5.1 containment contract](https://doc.cgal.org/5.5.1/Polygon_mesh_processing/index.html#PMPEnvelope).

All 1,322,970 source triangles and 861,404 candidate triangles pass at **0.0225
units**, retaining the 0.0025-unit reserve within the original 0.025-unit budget.
Controls include identical/near/far triangles and an example whose vertices
are contained while its interior is not. The previously rejected complete VTK
mesh also fails this checker. Native CMake/CTest passes with CGAL 5.5.1.

After float32 export, the maximum vertex shift is 6.92215e-6 units. A second
complete check of the actual quantized surface runs independently on Kali1,
including topology and self-intersections, and passes the same **0.0225-unit**
bound in 271.04 seconds. Relative volume difference is **6.50142e-7** and
relative inertia-matrix difference **1.24439e-6**. A more aggressive 200,548-face
proposal fails conservative containment and remains unadmitted. The expensive
maximum-distance estimator is explicitly stopped after the complete conservative
bound is established; no maximum-distance estimate is credited to that job.

The validated approximation is an analysis surface, not a new CAD master or
an admitted volume mesh. Its tetrahedral quality and mechanical convergence
must be checked next. Reproduce the checker in the qualified Linux environment:

```bash
cmake -S twins/935-horizontal-cooling-system-f0/source/analysis-envelope \
  -B work/NEW-envelope-build -DCMAKE_BUILD_TYPE=Release
cmake --build work/NEW-envelope-build
ctest --test-dir work/NEW-envelope-build --output-on-failure
work/NEW-envelope-build/tiled_envelope ORIGINAL.off CANDIDATE.off
```

## Qualified native structural runtime

An isolated x86_64 CalculiX 2.23 build uses the pinned upstream archives and the
author's official large-deck SPOOLES correction, as in the previous Mac study.
Its binary SHA-256 is
`2efb8be48e0b175a322b73ad5feb603b8400185bcc2672ab516f44d6ef0069ea`.
All six existing bending witnesses pass their original formulation-specific
criteria. The complete C3D4 rotor then finishes in 138.28 seconds under a 32 GiB
address-space/RSS limit. Every output field is compared with the previous Linux
solve: displacement, printed RF and stress fields agree to output precision;
remaining reaction differences are at floating-point roundoff.

The existing independent assessor again checks all 661,495 nodes and 2,116,345
elements, including consistent centrifugal loads at constrained nodes. Force
and moment balance errors are below 1e-9. This is replication of a conditional
P1 result, not mesh convergence. The thin-cell quality and localized stress peaks
already documented remain unresolved.

The unchanged complete C3D10 deck has 4,100,825 nodes and 2,116,345 elements.
Its separate native execution receives a hard **88 GiB address-space limit**,
RSS monitoring and a 3,000-second wall-time limit. The independent complete-P1
field comparison must pass before this stage is released. It is stopped at its
wall-time bound after **3,001.77 seconds**, with a measured peak process-group
RSS of **69,312,240 KiB**. There are no accepted quadratic displacement/stress
fields. Its Linux stop is a time limit, distinct from the previous Mac memory
stops. No convergence or strength conclusion follows.

## Ten material families and four speeds

The existing ten screening cards remain unchanged. They assume homogeneous
isotropic elasticity, common Poisson ratio **0.33**, 20 °C, a fixed assumed bore
band and centrifugal loading only. For the same geometry and support, linear
elasticity gives the following relative factors:

- mass: `rho / rho_reference`;
- stress and force: `(rho / rho_reference) * (rpm / rpm_reference)^2`;
- displacement: the stress factor times `E_reference / E`.

Three independent native complete-P1 solves check these factors: WE43 and
Ti-6Al-4V at 6,000 rpm, and AlSi10Mg at 3,000 rpm. Every displacement, reaction,
printed RF and element-peak stress value is compared. The largest normalized
field error is **3.82e-7**, below the 2e-5 numerical comparison tolerance; all
three solves also pass the unchanged force/moment audit. The first material
attempt is preserved as rejected because an overlong density token is refused
by CalculiX. Its successor uses the existing bounded-width numeric codec;
no numerical or physical acceptance criterion is relaxed.

The resulting **40 rows** cover ten cards at 3,000, 6,000, 9,000 and 12,000 rpm.
They are verified linear-similarity projections, not forty separate solver runs.
At 6,000 rpm, under the assumed calibration:

| Screening card | Conditional rotor mass, kg | Conditional P1 maximum displacement, mm |
|---|---:|---:|
| AlSi10Mg | 1.14988 | 0.271811 |
| WE43 | 0.78812 | 0.295711 |
| Ti-6Al-4V | 1.89493 | 0.285046 |

These values describe this unconverged elastic model. WE43 density/modulus are
the existing surrogate card, not qualified printed properties. Actual Poisson
ratios, anisotropy, pressure loading, contacts, thermal effects, residual stress,
surface finish, fatigue, balancing and process allowables can change the result.
No safety factor, usable maximum speed, fatigue life or preferred production
alloy follows from the table. A change in alloy alone supplies no airflow gain
for an unchanged rigid geometry.

## Saved results and rental teardown

The [private release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/native-gpu-935-20261022)
retains three terminal-data checkpoints and a separate source/analysis archive.
All archive members are streamed and hash-verified on the Mac; archives are
mirrored and hash-checked on Kali1. The source archive depends on the earlier
complete-system and conforming-rotor core/delta releases. Original inputs,
rejected proposals, failed numeric tokens, interrupted calculations, software
sources and complete accepted fields remain identifiable.

Only after the three checkpoints are saved and checked on both machines is
Vast instance **57137803** destroyed. The wrapper verifies its absence and a
separate inventory is empty. The deadline guard is stopped afterward. The
remaining quantized-surface check runs on Kali1, without another rental.
The $4 attempt ceiling remains inside the $10 goal ceiling; conservative
reservations across the two actual rentals total $8. The final invoice remains
unreconciled, and account credit changes are not attributed to this job.

## Whole-system work still required

This continuation does not replace unresolved system requirements with solver
controls. The seventeen interfaces, two independent calibration dimensions per
scan, exact engine mounting datums, gears/ratio, bearings, coupling, axial
retention, lubrication and detailed BOM remain open. The observed-drive crossing
with the solid engine placeholder remains documented rather than cut away.

The next fluid reference is a Foundation 13 rotor/casing case after its geometric
boundary definition is accepted. The independently verified rootless F25 case
establishes a runtime witness, not a 935 curve. The old OpenCFD v2406 case files
cannot be relabelled as Foundation 13. Accepted fan CFD, structural h-convergence,
prestressed modes, process qualification and a physical bench remain necessary.
There is no accepted reference dataset for PhysicsNeMo yet, and no optimized or
fabricable complete installation is released.
