# 935 exact centroid cavities on Mac, Kali1 and Vast

This increment removes **24 of the 26 source cells with exact Frobenius
condition at least `1e16`** from the inherited hypothetical calculation mesh.
The worst condition falls from approximately `4.65754e16` to `1.30938e16`.
Every old coordinate and the entire calculation boundary remain bit-identical.
Absolute element quality still fails, and this is not a functional or
manufacturing qualification.

The [machine-readable results](results.json) contain source hashes, aggregate
admission results, runtime and rental receipts, full numerical counts and open
gates. The private read-only capsule `935-centroid-extreme-batch-20261105-001`
contains 416 payload files (198,458,915 bytes), all rehashed after freezing;
manifest SHA-256:
`699cc762a0448f31e44099d34274dcfa7af938c33e1012b0669eaa896ec7b082`.
No raw scan, derived mesh, coordinates, private correspondence or credential is
committed.

## Requirement, source admission and method

The requirement is to improve exact local conditioning without altering the
calculation domain. This implements numerical verification service `A-CAE` on
`T-MAC`, `T-K1` and temporary `T-VAST` in the
[architecture](../../architecture/README.md). The existing Qwen/CADAM/PicoGK
proposal/geometry roles, STEP masters and Gmsh/OpenFOAM/CalculiX/Adamantine
authorities are unchanged. Adding numerical interior points is not a replacement
for faithful editable CAD or missing acquired internal geometry.

The parent is the [source-admitted 660-flip mesh](../935-residual-source-admission-20261105/README.md),
SHA-256 `1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d`.
Its full boundary, positive tetrahedra and exact condition census were checked
before preparing trials. The [signed-domain benchmark](../935-signed-partition-20261105/README.md)
establishes the nonconvex partition proof and a literal analytic reference.
Both increments start from this same parent; their gains are not cumulative.

The parent has 26 cells at or above `1e16`, with 98 distinct vertices, all on the
actual calculation boundary. Each vertex supplies two fixed source profiles:
the complete vertex star and exactly one complete face-neighbor ring. Before
candidate calculation, all 196 profiles are screened for manifold oriented
boundary topology, old-point retention, necessary fixed-face quality, size
limits and native boundary self-intersections. Of those, 60 intersection cases
and five nonclosed/oriented boundaries are refused. The remaining **131**
source-admitted cavities form a compact portable job.

The worker computes each exact volume centroid from the actual old cells,
rounds it once to binary64 and cones every oriented cavity boundary face to it.
Its certificate requires positive cells, pairwise exact interior separation,
identical oriented boundary chains and exact total volume. A strict kernel
failure or insufficient new quality rejects the proposal. Each new mean ratio
must be at least binary64 `0.01`; five fixed quality counts and all eight exact
condition-threshold counts must not regress. No source coordinate, fixed face,
quality floor or physical assumption is adjusted to admit a result.

This finite source profile does not exhaust every possible valid cavity or
remeshing method. A refusal is retained as a bounded trial outcome, not a proof
that the source defect is impossible to repair.

## Actual execution and independent verification

The portable worker uses only Python's standard library and exact integer/
Fraction predicates. Before its case queue, it executes the literal concave
control and the previously independently verified 37-to-44-cell head benchmark.
The synthetic reference centroid is `(0, 27/56 + 2^-26, 0)`, exact volume `7/6`.
The known head benchmark must match expected point bits, cell-byte digest and
quality counts.

| Host | Actual runtime | Work executed | Kernel time |
|---|---|---|---:|
| Mac | Python 3.12.11, arm64 | Control, known benchmark and one case | 0.243 s |
| Kali1 | Python 3.14.7, x86_64 | Identical benchmark path | 0.200 s |
| Vast | Python 3.12.3, x86_64 | Controls/benchmark, all 131 cases, eight CPU workers | 1.093 s |

All nontiming benchmark output fields agree exactly across the three hosts.
These small jobs do **not** demonstrate a cloud speed advantage over the Mac;
the paid run exercises the prepared parallel path and produces the full batch.
The GPU is not used. Kali1's main filesystem lacks the required reserve, so its
77,097-byte compressed input bundle is tested in a new private `/dev/shm`
directory. Outputs are recovered/hash-verified before removing that exact
temporary directory. No unrelated storage is cleaned.

Vast admits 45 proposals and refuses 86. The deterministic packing policy visits
source targets in exact worst-condition order, chooses the compatible proposal
covering the most target rows, then the fewest old cells, then lexical case ID.
Already selected old-cell rows cannot overlap. This selects **22 cavities**,
replacing **212 old cells with 350**, with 22 distinct numerical interior nodes.

A separate Mac verifier joins every selected local coordinate and cell tuple
back to the full original volume. It reruns analytic/forged-cell controls and
independently recomputes Fraction centroids, once-rounding, signs, volumes,
quality thresholds, complete oriented triangle chains and **3,763 Fraction
separating-plane witnesses**. A separate Fraction adjugate implementation
recomputes all eight condition counts and matches the remote integer results.
Source admission, atomic integer predicates and the signed-domain contract are
shared and disclosed; independence is claimed only for the stated checks.

## Complete resulting mesh checks

Candidate SHA-256:
`7e4f514b548c5d215a78735c506bca5933d3d69a617a9bcd9c5d70322cfff156`.

| Quantity | Parent | Verified batch candidate |
|---|---:|---:|
| Nodes | 4,181,299 | 4,181,321 |
| Tetrahedra | 12,967,519 | 12,967,657 |
| Exact boundary faces | 8,218,458 | 8,218,458, unchanged |
| Cells with condition at least `1e3` | 291,988 | 291,959 |
| At least `1e6` | 15,596 | 15,567 |
| At least `1e12` | 15,285 | 15,256 |
| At least `1e15` | 109 | 84 |
| At least `2^52` | 42 | 17 |
| At least `1e16` | 26 | 2 |
| At least `3 * 2^52` | 6 | 0 |
| Mean ratio below `0.01` | 233,070 | 233,041 |
| Minimum mean ratio | `1.291009351665788e-11` | unchanged |

Every resulting tetrahedron is positive: 12,967,637 interval proofs and 20 exact
Fraction fallbacks. Every node is used; all 21,826,085 internal face pairs have
opposite orientations. The entire boundary is exact. Full quality counts agree
with the independently verified local replacement predictions. A fresh complete
condition census classifies all 12,967,657 cells; every retained severe exact
value equals its mapped parent value. All 350 new cells have condition below
1,000 in the exact census; their quality certificate independently bounds it
below 12,000. Cell conditioning alone does not establish PDE conditioning,
accuracy, thermal performance or strength.

The original OBJ, original printing-study 3MF and unchanged calculation 3MF are
freshly rehashed. Surface/native export evidence remains applicable to the
identical boundary; native **volume** readback and solver/operator admission
must be repeated for the new cell connectivity. Exhaustive global tetrahedron
intersection status is inherited and has not been upgraded.

## Rental, budget and closure

Two creation calls were explicitly refused with `no_such_ask`; unchanged
inventories and terminal guards confirm no instance was created. The unavailable
ask was excluded from the successful selection. Instance **59320440** is then
created from the pinned mesh/CFD image with 120 GB of storage on a German offer
advertising 14 effective CPU cores. Its observed all-in hourly rate is
**$0.228**, including the allocated storage. Only compact cavity inputs are
transferred; the full scan and volume are unnecessary for this kernel.

Before creation, a self-tested local guard is armed for the exact launch receipt
ID, one-hour maximum, $0.40/hour and $0.014/GB rate ceilings, 20 GB network
allowance and **$1.50 attempt allocation**. The worker has a 600-second deadline,
eight processes, 2 GiB per-child address-space bound and 4 GiB free-disk floor.
This local guard is not a provider-side hard billing cap. The 20 GB allowance is
budgeted, not an enforced or independently metered traffic-volume limit;
controller/network failure can delay deletion.

All worker children join, all returned files are recovered and hash-verified,
then the controller deletes only the created ID. A separate guard and current
inventory confirm absence. Foreign resources are untouched. The launch-to-
confirmed-absence rate estimate is approximately **$0.016**, excluding network;
it is not an invoice. The conservative attempt allocation remains **$1.50**,
covering compute, storage and the budgeted network allowance. With historical conservative
allocation, the tracked ceiling is **$13.84**, within the original $30 compute
limit and protected $5 reserve. Live post-run credit was $22.38; account changes
cannot be attributed solely to this run because another pre-existing resource
is outside this task. No recharge or budget reset occurs.

All local stages and three guards are terminal before freezing. Executed source
snapshots match [published sources](source/). Exact commands, runtime metadata,
private inputs, logs, outcomes, recovery checks, closure and immutable source
copies are retained in the private capsule. Do not alter executed bytes in
place; make a new source revision for a further trial.

## What remains

Two extreme cells, 15,256 severe cells and the unchanged poor minimum quality
remain. The mesh is admitted only for further numerical work. Native volume
and operator checks, converged/correlated physics, faithful editable head CAD,
specimen metrology and interfaces, hidden passages, material/machine/process
qualification, machining/supports/build strategy, physical inspection and engine
validation remain open. Existing printing-study exports are not machine-ready
metal files. All functional/manufacturing release gates stay false, no supplier
message is sent, and the full engineering goal remains active.
