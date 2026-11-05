# 935 — comparison with the scan and numerical refinement

[Dossier](README.md) · [Candidate and solvers](CONTINUATION_20261012.md) ·
[Plan](RECONSTRUCTION_PLAN.md) · [Bench](BENCH_PROTOCOL.md)

The previous delivery is merged by
[PR #173](https://github.com/cluster2600/porscheparts/pull/173).
This campaign reveals two limits: repeating one blade does not yet reproduce
all the acquired surfaces; the maximum stresses remain
mesh-sensitive. It characterises the candidate under assumptions, without
qualifying a fitted replica or its manufacture.

## Geometric comparison

The existing functions of `review_reconstruction.py` sample the
surfaces uniformly by area and compute distances to the triangles.
Each blade provides **2,000 acquired points towards the candidate** and **1,000 points
from the candidate towards the acquired region**, with recorded seeds.
The radial ranges are 98–136 source units for the scan, 100–134 for the
candidate. This guard reduces the effect of artificial trimming edges.
The acquired phases define the sectors. Roots, tips and hub
are not evaluated; their gaps do not become observations.

| Blade | RMS scan → candidate | P95 scan → candidate | RMS candidate → acquired zone |
|---|---:|---:|---:|
| 00, used for construction | 0.386 | 0.881 | 0.225 |
| 01 | 0.954 | 1.595 | 0.838 |
| 02 | 1.562 | 2.099 | 1.608 |
| 03 | 1.721 | 2.763 | 1.674 |
| 04 | 1.142 | 2.184 | 1.157 |
| 05 | 1.049 | 1.344 | 0.423 |
| 06 | 0.971 | 1.925 | 0.979 |
| 07 | 0.883 | 1.775 | 0.679 |
| 08 | 0.818 | 1.539 | 0.735 |

Distances are in **uncalibrated source units**. The scenario assumes
1 mm per unit; this assumption does not certify the metrology. The eight
other blades were not used for the periodic fit, but belong
to the same acquisition: they do not independently verify the scale.

The multi-view map is inspected visually and kept privately with the
points, distances and digests. The deviations extend across the acquired
surfaces. They justify redoing the registration of the acquisitions and
the common fit of the blades before retaining periodicity for an
exact replica. No arbitrary registration masks these deviations.

A first comparison by sector included small unclassified fragments
and gave up to 2.251 units RMS. It is kept separately.
The table above uses the nine significant components identified
by the existing segmentation: radial cut at 94 and at least 5,000 vertices.
The three small groups of 433, 196 and 22 vertices remain in the scan and
are explicitly excluded from this blade comparison; no hole
or fragment is modified. Their mechanical functions remain unknown.

## Centrifugal refinement

These three grids use the **same PicoGK signed field at 0.2 mm**, the
same STL, isotropic AlSi10Mg, 6,000 rpm and an assumed Poisson's ratio of 0.33.
They are connected, keep the nominal bore, pass the Gmsh
Jacobians and stay within 5 % of the CAD volume. CalculiX 2.21 runs serially,
in a new directory per deck.

| Step, mm | C3D8 | Volume, mm³ | Maximum stress, MPa | P95, MPa | Maximum displacement, mm |
|---|---:|---:|---:|---:|---:|
| 1.40 | 155,702 | 427,246 | 150.60 | 28.92 | 0.13991 |
| 1.25 | 215,328 | 420,563 | 133.83 | 28.80 | 0.13845 |
| 1.20 | 241,327 | 417,013 | 147.18 | 29.03 | 0.13437 |

Between the two final grids, the variations relative to the fine grid
are **9.07 % for the maximum**, **0.81 % for the P95** and **3.04 % for the
displacement**. The P95 describes all integration points; it does not replace
a check of non-singular local stresses or of fatigue.
The maximum and its location vary at the unqualified junctions.
Full convergence remains open.

The bore reactions are compared with the centrifugal resultant computed
independently from the cell centres and volumes. The relative error
stays below **6 × 10⁻⁸** for these three cases. This equilibrium verifies the applied
loads, without qualifying the contacts or supports of the real system.

The selection tolerance of the fixed support equals the grid step: the
boundary and the nodal selection change with refinement. Analytical
interfaces and defined blends remain necessary. Pressure, thermal,
prestressed modes, fatigue, transmission and admissible speed remain open.

A calculation at 1.4 mm on the 0.4 mm field gives 131.45 MPa and 0.14395 mm.
This sensitivity diagnostic is separate from the common-field comparison.
The rejections are kept: volume overrun at 1.3 mm and disconnected
elements at 1.2 mm on the 0.4 mm field.

The PicoGK sampling ceiling goes from two to four million
candidate cells after checking the **Mac's 64 GB**. This grid is
traversed without allocating one solid per assumption. The limit of 300,000 kept
elements and the geometric checks remain unchanged.

## Check of the air calculation

The case remains a hypothetical square duct: imposed flow of 0.6 m³/s,
6,000 rpm. The preparation now uses `relTol 0`, `tolerance 1e-9`
for pressure/velocity/turbulence and two non-orthogonal corrections.
The steady campaign is extended to 1,800 iterations.

It finishes without solver or mesh-quality errors. Over the
last 100 iterations, the maximum volumetric imbalance is
**2.11 × 10⁻⁸** relative, that is **0.00000211 %**. The strict solve
improves this balance, but the pilot remains **refused for performance**:

| Quantity | Final conditional mean | Final relative range | Difference between the means of the two windows |
|---|---:|---:|---:|
| Area-averaged total pressure | 137.94 Pa | 10.93 % | 3.03 % |
| Axial resisting torque | 2.548 N·m | 2.71 % | 0.35 % |

These means describe an unsteady calculation in the hypothetical duct.
They define neither the engine flow rate, nor an accepted curve, nor an
efficiency. The two other meshes remain prepared with no calculation run.
Moving to a transient calculation must be studied after correcting
the geometry; extending this steady calculation alone is not enough.

`assess_candidate_cfd.py` checks the digests of the prepared inputs,
the mesh, the end of the solver and the synchronised histories. It computes
the area-averaged total pressure in Pa from the kinematic pressure
and `|U|²`, then the resisting torque from the fluid moment.
Two successive windows of 100 iterations are required: final range
and difference of means below 1 % for pressure/torque, volumetric imbalance
and deviation from the imposed flow below 0.1 %.

Oscillation, drift, leakage, incomplete/non-finite data or modified inputs
prevent acceptance. A point accepted on one mesh never becomes
a validated 935 curve: three meshes, walls, housing and real conditions
remain necessary.

```sh
python twins/935-horizontal-cooling-system-f0/source/assess_candidate_cfd.py \
  work/new-cfd/artifacts/coarse work/new-cfd-assessment
```

The output must be new and private under `work/`. The report keeps series
and digests. The input files of this run were compared
byte for byte with an independent preparation during the calculation; this
chronology is recorded in the metadata.

## Preservation, verification and next steps

Analysis scripts, parameters, raw results, maps and rejections are kept
in the [private repository](https://github.com/cluster2600/porscheparts-935-private).
The [archived refinement campaign](https://github.com/cluster2600/porscheparts-935-private/releases/tag/convergence-20261012)
separates the geometric/mechanical results from the final CFD output.
The original scans, transforms and earlier evidence are preserved.
Public Git receives the numerical checks and their documentation.
The 935 checks pass: **78 tests**, including **18 tests of the candidate and of
the CFD analysis**. `make check` is run by Linux CI before merging.

The [CI for the code and the first report](https://github.com/cluster2600/porscheparts/actions/runs/38272868407)
completes `make check` with **3,776 main tests and 205 optional tests
skipped**. These software tests do not constitute fan tests.
The exploratory comparison of ten material maps keeps the grid masses
and applies the linearity laws to stresses/displacements,
with a common Poisson's ratio. This law is compared with the three direct
AlSi10Mg/WE43/Ti64 calculations of the previous delivery. Only AlSi10Mg is directly
solved on the final grid of this campaign; the other maps do not
constitute nine additional simulations or qualified materials.

The geometric priority is the registration of the back and the blades, then their
measured blends. A transient calculation must be evaluated if the steady
pilot remains unstable. The 17 mounting interfaces, the mechanism,
the processes and the bench remain to be established. The contracts and authorisations for
manufacture/physical validation remain unchanged at `false`. No Vast instance
is launched for this batch.
