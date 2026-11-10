# Residual source audit and global-quality correction of the 935 study mesh

Two globally inspected batches remove **12,095** severely conditioned cells.
The complete severe-cell count falls from **12,811 to 716**, and nonpositive
native Gmsh shape indicators fall from **868 to 108**. Absolute quality still
fails; no engine field solve or metal release is admitted.

The previous [four-batch continuation](../935-current-peel-admission-20261107/README.md)
reached a fixed point of its local-quality rule. This increment first examines
every refusal, then introduces a separately justified surface-quality contract.
It does not turn the old operator's refusal into a pass.

The domain is still the hypothetical bare-head calculation mesh. The original
scan, conservative acquired-surface reconstruction, editable-CAD objective and
[supported printing assembly](../935-single-volume-20261107/README.md) retain
their separate identities. A numerical mesh correction is not a new measured
interface, a metal machine job or professional engine qualification.

## Complete source census before changing the operation

The immutable input is mesh
`fdce160bc7ec2456ab339de09733d00cd2f3cd4c6a1327e03b44c838000e0db6`.
The read-only audit repeats the complete join of all 12,811 severely conditioned
cells to all 8,218,458 boundary triangles. Every matched face, tag and cap-vertex
membership agrees with the frozen predecessor attribution. The unchanged
operator reproduces its complete refusal counts:

| First refusal | All severe cells | Nonpositive native Gmsh shape indicators |
| --- | ---: | ---: |
| Local triangle-quality minimum decreases | 11,625 | 690 |
| Construction-cap constraint | 211 | 32 |
| Fewer than two boundary faces | 975 | 146 |
| Total | 12,811 | 868 |

All 868 native shape refusals belong to the severe-cell census. Of the 211 cap
refusals, 205 touch a cap vertex without having a cap boundary face; six have a
cap boundary face. Their protection is retained.

The audit evaluates the four local triangle qualities using exact binary-input
Fractions and two algebraic identities, Gram and Heron. These are arithmetic
cross-checks, not independent physical measurements. All 11,625 quality-refused
exchanges have new faces above the inherited absolute floor, do not increase
the number of faces below the existing warning threshold and pass the full
local edge-incidence/link restrictions. Approximate diagnostic new minimum
quality squared ranges from 0.3599999999997223 to 0.7499999999999916. The median
new/old squared-quality minimum ratio is approximately 0.9999999999998994;
the worst ratio is approximately 0.64. These summaries do not replace exact
per-case acceptance or prove a global quality property.

## Explicit policy change and global proof

For a triangle, squared mean-ratio quality is
`q² = 12 * |(b-a) cross (c-a)|² / (|b-a|²+|c-b|²+|a-c|²)²`.
The old rule required the new patch minimum to be no smaller than the old
patch minimum and required new `q² >= binary64(0.01)^3` (approximately
`q >= 0.001`). The new rule permits the local patch minimum to decrease,
requires every new `q² >= binary64(0.01)^2` (approximately `q >= 0.01`), and
additionally proves that the global surface minimum cannot decrease. This is
a documented tradeoff, not a claim that every quality statistic improves.

A separate read-only scan finds an actual protected cap face. Its exact
squared quality is approximately 2.6185e-7, strictly below the existing warning
threshold. Its private row, node IDs, surface/tag hashes and exact rational
value are bound before correction. Approximate ranking only locates a face;
acceptance uses exact arithmetic. It is not necessary to claim that this face
is the global minimum.

Let `m` be the old global minimum squared quality, `w` this retained witness
and `t` the existing warning threshold. Since `m <= w < t`, every new face
has quality at least `t > m`, and every retained face already has quality at
least `m`. Thus the new global minimum is at least `m`. New faces also cannot
increase the count below `t`. The independent verifier recomputes the witness
using direct Fraction cross products, checks its literal cap row and confirms
that the actual candidate leaves it unchanged. Every new face must separately
pass the stronger absolute threshold in that verifier.

All geometric restrictions remain: exact positive source volume, convex common
projection, the fixed `512 * 2^-52 * extent` graph-displacement budget, normal
agreement, cap-incident vertex protection, mapped marked curves, complete old
diagonal incidence, absent alternate surface diagonal and complete simple-cycle
link. Patches remain vertex-disjoint. No vertex coordinate moves. The represented
calculation surface and a microscopic material volume change; preservation of
the identical old surface is not claimed. The cumulative numerical correspondence
limit remains 0.01 nominal mm relative to the frozen hypothesis, not a specimen
or manufacturing tolerance.

## Actual candidates and remaining work

[Scalar results](results.json) and the [phase ledger](phase-ledger.json) bind the
executed source, report and private-manifest identities.

| Stage | Removed in batch | Tetrahedra | Condition at least 1e12 | Nonpositive native minSICN |
| --- | ---: | ---: | ---: | ---: |
| Frozen local-quality fixed point | — | 12,965,229 | 12,811 | 868 |
| Global-quality batch 1 | 10,531 | 12,954,698 | 2,280 | 210 |
| Global-quality batch 2 | 1,564 | 12,953,134 | 716 | 108 |

Both batches pass the complete surface, volume, fresh condition-census and
native readback checks. All native determinant and volume metrics remain
positive; native shape refusals remain. The worst exact-derived approximate
Frobenius condition improves from 8.452019e15 to 6.047921e15. The global minimum
mean ratio remains 1.291009351665788e-11. These absolute failures are retained;
relative progress does not admit the mesh for engine fields.

The final complete numerical correspondence bound is 0.009643215374425574
nominal mm. The unchanged cumulative checker joins the four historical batches
and both new batches to the one immutable kernel parent. Every coordinate bit
and retained cell tuple matches that parent; every other surface row remains
unchanged; the removed volume is independently recomputed from original
coordinates with exact determinants. The six-batch cumulative removal is
14,535 cells, including the historical 2,440.

A fresh read-only source audit of all 716 remaining severe cells finds 248
locally/topologically eligible exchanges and packs 228 vertex-disjoint proposals.
The other first refusals are 256 cells without two boundary faces, 211 cap
constraints and one nonconvex projected patch; 20 eligible patches conflict
with the packing. No third corrected candidate is exported. The next action is
independent verification of these frozen proposals in a new private capsule,
followed by the same complete checks. This operation has not reached a fixed
point, and fields must not be launched on the current quality-rejected mesh.

## Reproduction and acceptance boundaries

The new scripts take `--job PRIVATE_JOB --output NEW_DIRECTORY`. The
published source patches derive the versioned constructor, distinct Fraction
verifier, current-input wrappers and complete condition census from the linked
frozen predecessors. The first four explicitly include the policy and witness
changes; they are not described as identity-only patches. The condition-census
and successor patches change input identities/schema only. System `patch` replay must reproduce
the executed bytes exactly. No frozen predecessor is edited.

Controls precede the head workload. Literal 3-4-5 and right triangles check
quality, orientation, scale, collinearity and coincident-point refusal. A
binary-coordinate perturbation remains exact rather than being rounded flat.
Both peel arithmetic paths exercise a convex patch with a decreasing local
minimum and a high-aspect patch that must fail the new absolute threshold.
The prior geometric/topological refusals remain exercised. An intentionally
forged witness with recomputed input hashes is refused at its exact-quality
comparison, before proposal or candidate export.

The initial read-only launch refused an obsolete condition-report field before
mesh loading. Its nonzero receipt is retained; a versioned source uses the
actual current report schema. An initial literal-control expected value was
also corrected by the independent area formula before any head execution.
System Python lacked `hashlib.file_digest`; preparation switched to the existing
scientific runtime without installing or upgrading anything.

Actual correction requires separate Fraction verification, every-coordinate and
retained-cell readback, full native surface intersections/topology and exact
3MF readback, every-cell interval/exact signs and complete oriented boundary,
a fresh complete conditioning census compared to an exact deletion prediction,
and native Gmsh export/re-import with complete metric counts. A zero exit from
a mesh tool does not override any failed geometric or quality criterion.
Exhaustive volume tetrahedron-pair intersection status is inherited, not upgraded
by these checks. No head field solve is admitted by a relative improvement.

Requirement `R935-GLOBAL-QUALITY-1` links this increment to `A-CAE` on `T-MAC`,
the [scan workflow](../../architecture/scan-repair-workflow.md) and
[ADR 0012](../../decisions/0012-local-compute-gpu-last.md). Qwen/CADAM assistance,
PicoGK/STEP geometry, Gmsh, OpenFOAM, CalculiX and Adamantine retain their
documented roles. No model output supplies its own engineering acceptance.

Existing isolated runtimes and bounded controllers are reused: 600 seconds per
ledger, 4 GiB sampled direct-child RSS for admission/verification, 12 GiB for
global/native checks and a 4 GiB disk floor. Raw geometry and cell IDs remain in
the private evidence capsule. New Vast charges are $0; the original $35 total,
$30 compute, $5 reserve and previous conservative allocation of
$15.67884277510534 are unchanged. No supplier message or scan submission is sent.

A read-only Kali1 refresh confirms Linux/x86_64, 16,454,295,552 bytes of RAM
and the exact existing pinned solver image. Home storage has 4,199,882,752
bytes free at observation, below the existing 4 GiB (4,294,967,296-byte) job
floor. Further Kali head jobs therefore remain unadmitted until capacity
recovers. The refresh creates no container, transfers no scan and deletes no
files. It does not execute or qualify a new solver utility.

Measured specimen identity/interfaces, physical scale calibration, hidden
passages, faithful editable CAD, correlated engine physics, a qualified alloy,
machine/exposure recipe, powder removal, machining, inspection and professional
engine validation remain open. This increment cannot qualify a functional
metal cylinder head.
