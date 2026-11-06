# Exact-boundary physics preparation and fixed-face audit

Date: 2026-11-05. The [local reconstruction](../935-bare-head-hypothesis-20261105/README.md)
and [normal-chord screen](../935-local-wall-screen-20261105/README.md) are the
inputs. The head and supported 3MF files are unchanged. This increment executes
one bounded Gmsh diagnostic on the actual delivered surface; **no new head
physics result or accepted volume mesh is produced**.

## Admission and actual execution

The source is the exact 8,219,310-triangle build mesh, SHA-256
`05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594`.
Its prior full geometry receipt and actual thin-feature report are checked
before loading Gmsh. The predeclared verdict admits a closed manifold boundary
for a diagnostic meshing attempt only; wall adequacy, sharp-feature behaviour,
physical interfaces and solver admission remain open. There is no coarsening,
parameter sweep or geometry modification.

A new isolated Mac environment uses the official Gmsh 4.12.1 arm64 wheel,
SHA-256 `eaf48bbed0f09c6f731e47ed0dbd184fef0dd8cf3b9b534222229a2b910d4c6a`.
The verified wheel is installed offline without dependencies. Actual module
origins are checked; NumPy 2.5.4 is reused from the existing scientific runtime,
which is not modified. Python is 3.12.11. The original mesher helper is unchanged.

The cube control completes first. A separate inspector verifies all 41 cells,
all 76 interior face pairs, exact source-boundary coordinates/orientation and
unit volume. Its analytic tetrahedron and inverted/missing-boundary controls
also pass through the actual command-line path.

The head attempt uses algorithm 10, 2 mm interior target and eight threads,
with predeclared limits of 900 seconds, 40 GiB child RSS and 4 GiB remaining
disk. The mesher continues internal optimisation until the controller stops it
at 900.928 s with SIGTERM. Peak observed child RSS is 27,318,240 KiB, about
26.05 GiB. The child is reaped; the terminal receipt is `bounded_limit_reached`,
exit −15. Intermediate log counts are not a recovered final mesh. No complete
head NPZ/MSH is accepted and the independent head-volume inspector is not run.
No timeout is described as convergence or successful meshing.

## A fixed-face bound determines the next action

The [earlier derivation](../935-mesh-admission-20261104/CLOUD_VOLUME.md)
applies to this new, independently rehashed surface. For a fixed triangular
face, let S be its three squared edge lengths summed and A₂ twice its area.
Its normalized shape quality is `q_f = 2 sqrt(3) A₂ / S`.
For any tetrahedron incident to that unchanged face,
`q_t <= q_f^(2/3)` for normalized tetrahedron mean ratio. The maximum is above
the face centroid at height squared `2S/9`. Changing interior sizing or apex
placement cannot exceed this face-specific ceiling.

[audit_face_ceiling.py](source/audit_face_ceiling.py) evaluates every actual
source triangle and separately counts retained skin and new cut caps. Analytic
optimal-apex controls pass. This is a double-precision analytic calculation,
not an interval certificate or physical dimensional measurement.

| Diagnostic mean ratio | Faces with lower ceilings | Retained skin | Assumed caps | At least this many forced subthreshold cells |
|---|---:|---:|---:|---:|
| 0.0001 | 2 | 2 | 0 | 1 |
| 0.001 | 74 | 74 | 0 | 19 |
| 0.01 | 3,269 | 3,238 | 31 | 818 |
| 0.05 | 37,666 | 37,347 | 319 | 9,417 |
| 0.1 | 106,215 | 105,377 | 838 | 26,554 |

A tetrahedron has at most four boundary faces, hence the loose lower bound
`ceil(face_count/4)`, independent of a particular volume connectivity.
The worst face quality is 6.61064 × 10⁻⁷ and its incident tetrahedron cannot
exceed approximately 7.58861 × 10⁻⁵ while that exact face remains. The reporting
bins are not an approved solver-quality specification or material allowable.
The result does not prove physical unmanufacturability; it identifies a
discretisation constraint. Another interior-size sweep or larger rental cannot
remove that constraint.

The next admissible geometry work is a separately declared surface
retriangulation/conditioning study with feature protection, a complete surface
deviation bound and independent geometry checks. The frozen print candidate
must be preserved. Any changed candidate requires new export, slice, support
and physics admission; this audit does not silently replace it.

## Kali runtime follow-up

Current Docker access on owner Kali1 works again. A read-only, network-disabled,
512 MiB version probe pins the existing local image by full content ID
`sha256:1ae1a454429ed155bfecae63a25f90889aabb7981705ef688c46328ba2acad36`.
Actual CalculiX reports 2.23. The historical OpenFOAM 13 path is absent in that
updated image; a separate probe confirms OpenFOAM 14. The image has no recorded
registry digest/source-revision label in the inspected metadata, so its local
content identity is not a source-rebuild or deployment attestation.

These probes transfer no scan and execute no head solver. OpenFOAM 14 needs its
own case/analytic controls before replacing historical version-13 runs.
Adamantine is not found at the three explicitly checked paths; no exhaustive
host search or claim of complete installation absence is made. The scoped
OpenBao/Vast wrapper check and auth check both succeed; only their success
statuses are returned. The wrapper uses its existing authorised identity
internally. No new Vast resource or paid charge is created.

## Evidence and replay

The [aggregate receipt](results.json) and [phase ledger](phase-ledger.json)
separate completed controls, the stopped diagnostic and pending head physics.
[run_gmsh_diagnostic.py](source/run_gmsh_diagnostic.py) documents explicit
runtime, source, admission and new-root arguments. It checks inputs/module
origins, runs the cube control, arms resource limits and records terminal
status without overwriting prior output. The unchanged mesher helper is
`../935-hypothesis-study-20261029/source/mesh_solid.py`.

[inspect_tetrahedra.py](source/inspect_tetrahedra.py) independently recomputes
cell volumes/shape, all face incidence/orientation and actual source boundary.
It passes the actual native cube; its head path remains prepared and unexecuted.
The checker does not exhaustively test tetrahedron-pair intersections or grant
physical acceptance. Source hashes, controls, official wheel, runtime bytes,
native logs, terminal receipt and fixed-face IDs remain private under
`~/Developer/PorschePartsArtifacts/935-local-head-physics-20261105-001/`.

The original scan, earlier source references and both delivered 3MFs remain
unchanged. No head OpenFOAM, CalculiX or Adamantine solve is credited to this
increment. The goal remains active, and the original budget is unchanged.

Primary distribution reference: [Gmsh 4.12.1](https://pypi.org/project/gmsh/4.12.1/).
