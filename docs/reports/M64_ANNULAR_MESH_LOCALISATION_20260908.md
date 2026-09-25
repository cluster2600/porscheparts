# M64 — locating the rejected mesh, before a multi-zone rebuild

The latest mesh remains rejected: **five families of defects**, with no CFD and
no manufacturing authorization. The local diagnostic finds **4,655 of the 5,733
low-determinant cells in direct contact with the stem–guide bands** (81.2%).
But the single cell with an excessive aspect ratio and the eleven highly skewed
faces sit elsewhere: fixing the rings alone will not be enough.

This domain is the **intake gas pilot**, derived from the four-valve candidate,
not the metal of the full cylinder head nor an engine cycle. The 935 scan remains a
reference; the M64 interfaces are not measured and the assumed scale
"one scan unit = one millimeter" is not certified.

## What was actually executed

A read-only local analysis, in **7.982 s**, recomputed the indicators
on the cells of the [latest short-edge run](M64_SHORT_EDGE_REMESH_20260908.md).
The five counts exactly reproduce its OpenFOAM 14 log:

| Indicator | Count | Location by boundary incidence |
|---|---:|---|
| Aspect ratio > 1,000 | 1 cell | Port wall, native face 37 |
| Skewness > 4 | 11 faces | Seat 36: 5; ports 28: 4 and 29: 2 |
| Determinant < 0.001 | 5,733 cells | 4,655 touch the eight stem–guide bands |
| Interpolation weight < 0.05 | 535 faces | 834 adjacent cells, of which 30 touch these bands |
| Volume ratio < 0.01 | 141 faces | 254 adjacent cells, of which 4 touch these bands |

The numbers of adjacent cells and of selected faces are not
interchangeable. Counts by role may overlap. Among the low-determinant
cells, the number of internal faces is 1, 2, 3
and 4 for **1, 730, 4,868 and 134 cells** respectively. In the OF14 formula,
uncoupled wall faces do not enter the determinant tensor; it is therefore
not the tetrahedron Jacobian.
[OF14 primary code](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C#L424-L514).

## Traceability and scope of the evidence

The native domain `fab1338…` has 86 faces. The checked mesh is
`3b59b622…`, i.e. 401,854 tetrahedra. A one-to-one matching of the 112,632
points accounts for the two FOAM writes at twelve significant digits;
it does not claim binary identity of the MSH and FOAM coordinates.
The **186,364 boundary triangles**, their orientation and their native roles
are verified by bijective matching, without nearest-wall search.
All inputs read are unchanged after the analysis.

Faces 28 and 29 come from `raw_intake_face_7`, face 37 from
`raw_intake_face_8`; these are B-spline port walls. Face 36 is the
cylindrical wall of `intake_2_seat_face_4`. The SHAs of the four face exports
were re-read directly. This provenance is inherited from the reviewed manifest,
with no new overlap Boolean operation.

**The native label sets had not been exported in this latest
run.** This receipt proves that the formulas reproduce the counts and the
matching to the boundaries, not label-by-label identity with new
OpenFOAM sets. Eight targeted tests pass; they are not physical tests.

## Physical assumption kept: dry bench with plugged guides

The rings represent two air pockets connected to the port, closed at the top
by idealized plugs: faces **57 and 58**, role `fixture_stem_seals`, of the
manifest `58b8be…` linked in the [localisation receipt](../../twins/m64-cylinder-head/evidence/annular-mesh-localisation-20260908.json).
The [domain builder](../../twins/m64-cylinder-head/source/flowbench-intake/build_gas_domain.py)
adds the inner space of the guides then subtracts the twelve
valve/seat/guide components; these plugs are not designed mechanical seals.
The [boundary classification](../../twins/m64-cylinder-head/source/flowbench-intake/mesh_gas_domain.py)
assigns them to `walls`, with the [stationary `noSlip` velocity condition](../../twins/m64-cylinder-head/source/flowbench-intake/prepare_openfoam_case.py).

This assumption of a **dry bench, stationary valves and plugged guides** is kept
for the diagnostic. No real stem seal, oil film, camshaft-carrier-side
pressure or leakage law is modeled. It therefore qualifies neither the lubricated
stem–guide interface nor the leaks of a turbo engine. It does not authorize
filling the clearances, moving the plugs or silently modifying the domain.

## Decision for the next run — not executed

The current generator imposes an isotropic size on the bands, without building
radial layers. The next step to submit for review is **a multi-zone candidate**:
radially structured guide–stem bands and local treatment of the
seat–port transitions carrying the twelve extreme defects. The partitions must not
move the physical walls, widen the clearances or close the passages.
Conformity between blocks and core, the roles, the complete boundaries and the
eight interface curves will have to be proven; no implicit non-conforming
joint nor relaxation of the thresholds is authorized.

```mermaid
flowchart LR
    A[Short-edge mesh rejected] --> B[Counts and boundaries relocated]
    B --> C[Multi-zone preparation: rings and transitions]
    C --> D[Geometry review and conforming joints]
    D --> E[New checkMesh mandatory]
    E --> F[CFD prohibited while rejected]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    class A,F stop
```

The [localisation JSON](../../twins/m64-cylinder-head/evidence/annular-mesh-localisation-20260908.json)
receipt contains the digests. No new mesh, solver, container or Vast purchase
was launched for this localisation. No thermal, mechanical,
LPBF, convergence or print qualification simulation follows from it.
