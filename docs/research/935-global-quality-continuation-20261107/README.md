# 935 correction continuation and fixed-face source admissibility

Three independently inspected batches remove **277** severely conditioned cells.
The full severe-cell count falls from **716 to 439** and native nonpositive
Gmsh shape indicators from **108 to 83**. The unchanged peel operation now has
zero admissible successors. Absolute quality still fails.

A new exact source audit identifies a separate structural restriction: one
protected construction-cap triangle limits every adjacent tetrahedron to mean
ratio at most approximately **0.00639761**, below the current **0.01** floor.
Keeping that literal triangle cannot satisfy this tetrahedral quality criterion,
regardless of the choice of apex or available compute. The criterion is not
lowered. The next geometry work must examine the cap's source and admissible
retessellation, rather than repeat point-only cavity trials with that face fixed.

The domain remains the hypothetical bare-head calculation mesh. This increment
does not complete the faithful acquired-surface CAD, change the
[supported printing assembly](../935-single-volume-20261107/README.md), qualify
engine fields or release a functional metal head. The complete original goal
remains open. [Results](results.json) and the [phase ledger](phase-ledger.json)
bind actual files, source versions, controls and private evidence.

## Current source and unchanged correction

The [preceding increment](../935-residual-surface-audit-20261107/README.md)
prepared 228 current proposals on mesh
`d7609b83b208930b2e2792f9e30eac85025af6dda60e71ac3c72e6731886f0e3`.
Their admission is reused only after consumed inputs are rehashed against its
frozen manifest
`3529958f01a36c1f5578b2faa1255c4f6c91c9fef30caca5a69db65bc95528be`.
No historical geometry case is silently restarted.

The exact global-quality policy is unchanged: new faces must exceed the existing
warning threshold, and an unchanged below-warning cap witness proves that the
global surface minimum cannot decrease. Per-patch minimum monotonicity remains
explicitly unnecessary under that previously documented policy. Exact positive
volume, convex projection, normal agreement, fixed graph-displacement bound,
cap-incident vertex and marked-curve protection, complete edge incidence,
alternate-edge absence and cycle-link restrictions are all retained.

Each batch has separate direct Fraction verification, complete actual surface
intersections/topology and 3MF readback, every-cell interval/exact signs and full
oriented boundary pairing, a fresh complete conditioning census checked against
an independent exact deletion prediction, and actual Gmsh export/re-import of
all coordinates/connectivity and native metrics. A fresh source audit precedes
each subsequent batch. Controls run before head acceptance. Exhaustive full
tetrahedron-pair intersection status is inherited, not newly established.

| Stage | Removed | Tetrahedra | Condition at least 1e12 | Nonpositive native minSICN |
| --- | ---: | ---: | ---: | ---: |
| Current parent | — | 12,953,134 | 716 | 108 |
| Batch 1 | 228 | 12,952,906 | 488 | 88 |
| Batch 2 | 45 | 12,952,861 | 443 | 84 |
| Batch 3 | 4 | 12,952,857 | 439 | 83 |

The final candidate is
`d00f2807ed32f4fd3c92f9e825fe691ef57a42b449f9dda020326ecdfc817aaa`.
Its complete numerical correspondence bound is **0.009643215374673374 nominal
mm**, relative to the frozen hypothesis, not a measured manufacturing tolerance.
All source coordinate bits remain. The calculation surface and microscopic
material volume change under the certified operation; an identical original
surface is not claimed. Every protected cap face remains unchanged.

The final audit covers all 439 remaining severe cells: 227 lack exactly two
boundary faces, 211 encounter cap constraints and one has a nonconvex projected
patch. There is no empty candidate or identical native rerun. This fixed point
applies to this operation, not to every possible reconstruction or mesh method.

The unchanged cumulative checker joins all nine accepted batches to the one
immutable kernel parent. It checks every node bit and retained cell tuple,
confines changed surface rows to certified patches, cross-checks actual MSH/3MF
and report identities, and independently recomputes the exact removed volume
from original coordinates. Cumulative removal is **14,812** cells, including
the previous 14,535. These are numerical identities, not physical validation.

## Sharp fixed-face bound

The [earlier corner-provenance audit](../935-corner-provenance-20261105/README.md)
already recorded 60 forcing boundary faces on its predecessor. This increment
recertifies an actual surviving cap triangle on the current mesh; it does not
claim a new count of all forcing faces or a newly discovered quality theorem.

For base vertices `a,b,c` and any apex `x`, define
`u=b-a`, `v=c-a`, `w=x-a`, `n=u cross v`, `D=n dot w`,
`L=|u|²+|v|²+|u-v|²`, and `T=|w-(u+v)/3|²`.
The sum of all six squared edge lengths is `S=4L/3+3T`.
The project's tet mean-ratio definition, independently checked against the
existing volume inspector, gives

```
q_tet³ = 432 D² / S³
q_face² = 12 |n|² / L²
```

The base-centroid offset has the same normal component as `w`, so
`D² <= |n|² T` by Cauchy–Schwarz. With `r=9T/(2L) >= 0`,

```
(r+2)³ - 27r = (r-1)²(r+8) >= 0
S³ >= 36 T L²
q_tet³ <= q_face²
```

This is a universal algebraic bound for any apex, not a sampled optimization.
A regular tetrahedron attains equality. Literal regular and right-tetrahedron
controls, scale/translation, collinear-base refusal and orientation independence
exercise the implementation. The direct Fraction vector primitives are shared
with the frozen verifier and are disclosed as such; the analytic bound is a
separate argument. The existing independent Gram/Heron witness value must agree.

On the actual final mesh, the certificate rechecks the complete boundary and
all coordinate bits, scans all 12,952,857 cells, and finds exactly one incident
tetrahedron for the private cap witness. Its exact squared face quality is
approximately 2.6185e-7, strictly less than `binary64(0.01)^3`. The actual stored
tetrahedron obeys the bound and the expected outward-face/inward-apex orientation.
Thus **any conforming tetrahedral partition retaining this literal boundary
triangle fails the current all-cell mean-ratio floor**.

The conclusion does not exclude retessellating the represented cap surface or
using another independently admitted cell formulation. It does not prove that
such a retessellation exists, that cap vertices are coplanar, or that a physical
interface has been measured. No face, point, floor or material assumption is
changed by the certificate. Further work must trace the cap's source, geometric
support, boundary and marked curves before choosing a new construction.

## Complete remaining-source attribution

The existing source-attribution implementation is reused with current input
layout/cohort bindings. Its entire numerical classification and private-array
construction block remains byte-identical. Both cohorts scan all 8,218,458
surface triangles and repeat the literal join controls. The native cohort is
verified to be a subset of the complete severe set.

| Actual source property | All 439 severe cells | All 83 native shape-refused cells |
| --- | ---: | ---: |
| Zero actual boundary faces | 206 | 47 |
| One actual boundary face | 21 | 3 |
| Two actual boundary faces | 212 | 33 |
| Zero strictly interior vertices | 436 | 83 |
| One strictly interior vertex | 3 | 0 |
| At least one cap-incident vertex | 215 | 33 |
| At least one cap face | 7 | 1 |
| All four vertices share one cap tag | 7 | 1 |

All current native shape-refused cells have four boundary vertices, even though
47 have no boundary face. Moving only strictly interior nodes while retaining
connectivity leaves those cell geometries unchanged. Connectivity or boundary
representation changes require separate admission. Cap membership does not
establish exact coplanarity or physical interface identity; tag zero denotes
the inherited envelope, not acquired-scan identity. Overlapping cap properties
are not disjoint refusal counts.

## Immediate cap-neighborhood admission

A separate read-only probe examines all three witness edges. Every adjacent
face has the same construction-cap tag, every old diagonal is unmarked, and
the three alternate edges are absent from the complete source volume and
surface. The old volume edge valences are 4, 2 and 2; two neighborhoods have
the combinatorics of a two-tetrahedron pyramid.

However, **all three four-point patches fail exact stored-coordinate
coplanarity**. Consequently no same-surface diagonal change is admitted.
New-face and replacement-tetrahedron quality are not evaluated after that
geometric refusal; false admission predicates in the raw record must not be
read as measured quality failures. No surface or volume candidate is exported.
The source's literal square and lifted/nonconvex-quad controls pass before
head inspection. Complete global edge incidence is reused from the frozen
operator, not inferred from a sampled neighborhood.

This does not establish why the coordinates are noncoplanar or classify the
discrepancy as rounding noise. Cap-plane intent and its provenance must be
retrieved before proposing a plane reconstruction or a bounded surface change.
The audit covers these three neighbors, not every possible cap retessellation.
Any new operation must separately address the literal cap-face preservation
contract, source fidelity, marked curves and independent volume-domain proof.

## Execution, replay and full-goal limits

Requirement `R935-GQC-1` links this continuation and source audit to `A-CAE` on
`T-MAC`, the [scan workflow](../../architecture/scan-repair-workflow.md), and
[ADR 0012](../../decisions/0012-local-compute-gpu-last.md). Qwen/CADAM, PicoGK/STEP,
Gmsh, OpenFOAM, CalculiX and Adamantine retain their documented roles. This
diagnostic does not replace those tools or grant engineering approval.

Replay source patches against their exact frozen predecessors; use new private
output directories and checksum-bound jobs. Peel/condition/witness patches
change input identities and complete denominators, with identical loop and
comprehension ASTs. Cohort adapters change input layout and report schema while
retaining the numerical classification block exactly. Every patch is independently
replayed with system `patch` and compared to the executed bytes. The new
`certify_face_floor.py --job PRIVATE_JOB --output NEW_DIRECTORY` has its own
literal controls and portable tests. The separate `audit_cap_witness.py` uses
checksum-bound jobs and its own literal controls; it exports source diagnostics
only. Geometry, cell IDs and solver byte dumps
remain private; Git contains English source, scalar outcomes and hashes.

Existing isolated runtimes and controllers are reused: 600 seconds per ledger,
4 GiB sampled direct-child RSS for local proofs/audits, 12 GiB for complete/native
checks, and a 4 GiB disk floor. No package is installed or upgraded. New paid
compute is **$0**. The original $35 total / $30 compute / $5 reserve and previous
conservative allocation of $15.67884277510534 remain unchanged. No new Vast
resource, supplier message, or scan submission is created.

The original scan and supported printing master remain separate from this
calculation mesh. Same-specimen metrology, exact interfaces, hidden passages,
faithful editable CAD, case-specific engine operators, converged/correlated
physics, qualified material/machine/exposure recipe, physical inspection and
professional engine validation remain open. No engine field solve or qualified
functional metal build is released by these results.
