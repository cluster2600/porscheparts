# 935 exact kernel-point cavity trial

All **26 source cells with exact Frobenius condition at least `1e16`** are now
replaced by independently checked cavities. The complete resulting census has
zero cells above that threshold and a maximum of approximately `8.45202e15`.
The represented calculation surface and every original source coordinate remain
bit-identical. Absolute quality still fails, and actual native Gmsh readback
still reports **996 nonpositive `minSICN` cells**. Engine physics, faithful CAD
and functional metal printing are not qualified by this result.

[Aggregate results](results.json) retain executed source hashes, controls,
terminal receipts, full numerical counts and the failed gates. Private capsule
`935-kernel-cavity-20261105-001` has 242 payload files / 1,114,108,349 bytes,
frozen read-only and rehashed after all computations terminate. Its manifest is
`0ee20b26d7096e24d8451160f52672eb590782576a46ece1d58c4803bc0d8454`.
Geometric bytes and rejected-cell indices remain outside Git.

## Source admission and the remaining centroid failure

The [previous centroid batch](../935-centroid-extreme-batch-20261105/README.md)
removes 24 of 26 extreme source cells. Read-only review finds four and three
source-admitted profiles containing the two uncovered targets. All seven
centroids fail strict inside-every-face admission; the targets are not omitted
merely by disjoint packing. This trial changes the point construction on those
seven profiles while keeping the same source geometry and acceptance contracts.

Both trials start from source mesh
`1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d`.
The gains must not be added as consecutive changes to different parents. The
previous complete source-admission bundle supplies 131 cavities, each already
screened for closed oriented topology, old-point retention, necessary fixed-face
quality, size limits and native boundary intersections. Its job SHA-256 is
`07f74999d6bd8232a25ddf36ab873ee28a176fb1fb0a7afda0557a6709030a53`;
all input hashes are checked before and after the new trial.

Exactly **seven** new head proposals execute. The other **124** case results are
reused byte-for-byte from the frozen Vast batch, not rerun or counted as new
cloud work. The new method admits five proposals and certifies that two other
profiles have no strict single-point kernel. Combined with the 45 retained
centroid proposals, 50 proposals are available to deterministic disjoint packing.
The two refused profiles do not imply that their target cells or the whole head
cannot be meshed; alternative admitted profiles cover both targets.

## Fixed numerical point construction and exact dual bound

For each outward cavity face, let `n` be its exact normal and `a` a face point.
Use an exact affine frame `x = origin + span*y` with positive power-of-two span,
then form rational normalized inequalities

```
u_i . y + r <= b_i
u_i = n_i / ||n_i||_1
b_i = n_i . (a_i - origin) / (span * ||n_i||_1)
```

The objective maximizes `r`, the normalized L-infinity ball radius. SciPy
`linprog(method="highs-ds")` supplies one floating proposal, with all four
variables explicitly free, a 10-second limit and 10,000-iteration limit;
defaults are otherwise retained. There is no tolerance or origin sweep.
The interface and marginal sign convention are documented by
[SciPy's HiGHS reference](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html).
This is an interior-node proposal service within `A-CAE`, not a replacement for
the prescribed CAD or physical solvers in the
[architecture](../../architecture/README.md).

The local affine coordinates are converted to exact rationals and mapped back
before one binary64 rounding of the proposed world point. All source coordinates
stay unchanged. Every face inequality is recomputed exactly for the **stored**
point. Floating optimization success, a positive proposed radius or a solver
infeasibility flag is never an admission certificate. Exact optimality of the
rounded point is not claimed.

When a usable dual support is returned, exact rational elimination recovers
nonnegative weights `mu` satisfying

```
sum(mu_i) = 1
sum(mu_i * u_i) = 0
r <= sum(mu_i * b_i)
```

The last inequality follows by multiplying and summing the face constraints.
A nonpositive exact upper bound excludes **every** strictly interior point for
that profile's single-point construction. It does not rely on the floating
solver's optimality report. A separate Fraction implementation re-derives face
normals, normalization, stored-point margins, weighted sums and upper bounds.
Six of seven new proposals supply a valid exact dual; two exclude a strict
kernel. The seventh has no recovered dual certificate but has an independently
verified positive stored-point margin and valid cone partition. No optimality
or impossibility claim is made from its missing dual.

## Literal control before head execution

The independently specified reference is a concave six-cell bipyramid with
notch height `7/8` and apex projection `7/8 + 2^-24`. Exact volume is `3/4` and
the volume centroid is `(0, 103/144 + 2^-26, 0)`, outside the strict kernel.
The independently chosen dyadic point `(0,61/64,0)` supplies a valid 12-cell
reference cone. Both this literal reference and the new solver proposal pass
exact domain/volume/quality checks, with 81 separate Fraction pair-plane
witnesses each and minimum mean ratio approximately `0.16266`.

Contradictory and zero-width halfspace controls have literal exact dual bounds
`-1/2` and `0`. Forged dual supports, weights and bounds are refused. The separate
cone verifier also refuses reversed and duplicate tetrahedra. These controls
run before selected head partitions are accepted.

The actual control passes on Mac arm64 Python 3.12.11 / NumPy 2.5.4 / SciPy
1.18.1 and Kali1 x86_64 Python 3.14.7 / NumPy 2.3.5 / SciPy 1.16.3. All literal
reference arrays are bit-identical, all analytic contract fields agree and the
proposed point bits also happen to agree. Cross-host bit identity of every head
proposal is not claimed: the seven new head cases execute only on the Mac.
Kali receives code and synthetic controls in a new task-only tmpfs directory;
recovered source hashes and control outputs are checked before that exact
directory is removed. No scan or head coordinates are transferred in this
increment, and no new Vast resource is rented.

## Independent packing and complete checks

The fixed policy visits exact worst-condition targets first, prefers candidates
covering more remaining targets, then fewer old cells, then lexical case ID.
It selects **24 source-row-disjoint cavities**, including two kernel-point
constructions and 22 retained centroid constructions: **242 old cells become
392**, with 24 numerical interior points. All original source points and every
complete boundary row are preserved; no hidden physical feature is inferred.

The separate verifier rejoins every selected coordinate and cell tuple to the
original full volume. It checks the complete oriented boundary, positive
Fraction signs, exact volume, once-rounded centroid construction where used,
strict stored kernel point where used, five quality counts, independent
condition counts and **4,427 Fraction separating-plane witnesses**. The
[signed-domain argument](../935-signed-partition-20261105/README.md) proves equal
closed domains; no convex hull is filled and sampled containment is not a proof.
Atomic integer predicates, cavity-boundary enumeration and source/domain
contracts are shared and disclosed; independent arithmetic has the stated scope.

The first packing verifier failed on a module variable shadowed by an output
path before emitting a candidate. Its source, partial witnesses and terminal
failure remain unchanged. Separate `verify_kernel_batch_v2.py` fixes the name
collision without changing geometry, thresholds or contracts; the complete
verification succeeds. The failed revision is not accepted evidence.

Candidate SHA-256:
`d618763474f2eeb7bf680ce18f6f2efce22795e538263b7dfc639ffb68be62c5`.

| Complete metric | Common parent | Centroid batch | Current kernel/centroid batch |
|---|---:|---:|---:|
| Cells with condition at least `1e12` | 15,285 | 15,256 | 15,251 |
| At least `1e15` | 109 | 84 | 82 |
| At least `2^52` | 42 | 17 | 15 |
| At least `1e16` | 26 | 2 | 0 |
| Approximate maximum condition | `4.65754e16` | `1.30938e16` | `8.45202e15` |
| Mean ratio below `0.01` | 233,070 | 233,041 | 233,036 |
| Minimum mean ratio | `1.291009351665788e-11` | unchanged | unchanged |

The current mesh has 4,181,323 nodes, 12,967,669 tetrahedra and the same 8,218,458
boundary faces. Every tetrahedron is positive (12,967,651 interval proofs and 18
Fraction fallbacks), every node is used and all 21,826,109 internal face pairs
are oppositely oriented. Whole-volume quality counts equal independent local
predictions. A fresh complete condition census matches every retained severe
exact source value and all eight predicted threshold counts. Every new cell has
condition below 1,000 in the exact census, with the separate quality-based upper
bound 12,000. These cell metrics do not establish PDE conditioning or accuracy.

Actual Gmsh 4.12.1 MSH 4.1 export/re-import preserves all coordinate, tetrahedron
and boundary arrays exactly, including complete node labels. All native
`minDetJac` and volume values are positive; `minSICN` remains nonpositive on
996 cells, minimum `-2.0245344338430406e-13`, versus 997 in the prior centroid
readback. The native shape gate therefore still fails. The private MSH is
915,500,277 bytes, SHA-256
`717fced5ace7fad76d366aa42ffc91c2fe483d96611860d1b753e4633c738462`.
The same unchanged exporter and literal positive/inverted controls are reused.
No native OpenFOAM/CalculiX field solve or operator admission is inferred from
successful export or a smaller failed-cell count.

## Reproduction, budget and remaining engineering work

[Executed sources](source/) and the machine-readable dossier identify exact
inputs, source hashes, case reuse and outcomes. CLI commands, private input
references, bounded-controller receipts, raw logs and rejected indices remain
in the capsule. Start from the literal control, then `run_kernel_cases.py`, then
the independent v2 verifier, full interval volume inspection, fresh complete
condition census and native exporter. Use new output directories. Executed
source bytes must not be edited in place. Some inherited JSON keys contain
`remote`; they identify the retained Vast case bundle, not new remote execution.
Package hashes observed after execution are labeled accordingly rather than
presented as a preexecution dependency lock.

All owned computations are terminal before freezing; source snapshots match the
published sources. Original OBJ, original printing-study master and unchanged
calculation 3MF are freshly rehashed. The previous identical-surface native 3MF
evidence still applies; exhaustive full-head tetrahedron intersections have not
been newly established. New paid compute is **$0**; prior conservative allocation
remains $13.84, not an invoice, within the unchanged $35 total / $30 compute /
$5 reserve plan. There is no recharge, supplier message or new cloud rental.

The 15,251 severe cells, unchanged poor minimum quality and 996-cell native gate
require source-relative audit before further operator work. Faithful editable
head CAD, specimen metrology/interfaces and hidden passages, operating loads,
converged/correlated physics, qualified alloy/machine/process, build supports and
machining, physical inspection and engine validation remain open. Qwen/CADAM and
PicoGK/STEP keep their documented roles; none of the prescribed physics or AM
tools is replaced by this proposal method. Existing printing-study exports are
not a released machine-specific metal build. All functional/manufacturing gates
remain false and the full engineering goal remains active.
