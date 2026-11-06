# Chamber chart projection and trim-domain audit

Date: 2026-11-04. Status: executed and independently checked. The previous
[connected-mask trial](../935-chamber-connected-20261104/README.md) rejected
all sixteen plane/quadratic fits and explicitly left projection and trim
admission unresolved. This increment checks that upstream domain before any
higher-flexibility fit; no spline, hidden passage or native smooth face is made.

## Fixed inputs and exact-predicate scope

The [plan](plan.json) predates the computation. Use all eight unchanged
greatest-acquired-area selections, their frozen training frames/origins/scales
and the original source arrays. There is no new crop, normal filter, source-ID
split, principal frame, degree or tolerance search. All 14,023 selected acquired
faces remain included. The parent manifest and every consumed file are checked
by SHA-256. All other parent observations remain in their earlier bundle.

The [producer](source/audit_charts.py) projects actual original vertices with
those fixed transforms. Each computed binary64 UV value is represented exactly
on a common integer grid. Integer orientation predicates and convex-triangle
separating axes classify every closed-AABB-overlapping pair. The broad phase
uses coordinate minima/maxima only. No predicate epsilon is introduced.

This is exact arithmetic on the **rounded computed UV chart**, not interval
bounds on the real-valued matrix product, a claim of scanner uncertainty or
physical metrology. It checks zero projected area, winding counts, positive-area
overlaps and closed contacts between faces with no original shared vertex.
Boundary incidence is counted from original indexed edges, without fan splitting
or coordinate welding. These are selected-mask boundaries, not identified
physical holes, casting defects, valves or attached components.

## Results

All **79,610** candidate pairs are independently classified. There are no
zero-area projected triangles, positive-area overlaps or closed contacts between
faces lacking an original shared vertex. Each chart has a uniform winding sign;
different frame orientations between charts are harmless.

| Historical region | Acquired faces | Candidate pairs | Original boundary edges | Boundary vertices of degree 4 / 6 |
|---|---:|---:|---:|---:|
| 0 | 2,697 | 14,524 | 1,241 | 99 / 4 |
| 1 | 1,884 | 10,766 | 676 | 36 / 0 |
| 2 | 2,086 | 12,763 | 504 | 25 / 0 |
| 3 | 509 | 2,679 | 231 | 8 / 0 |
| 4 | 820 | 4,842 | 222 | 2 / 0 |
| 5 | 2,653 | 15,343 | 957 | 84 / 6 |
| 6 | 1,674 | 8,283 | 872 | 17 / 0 |
| 7 | 1,700 | 10,410 | 448 | 13 / 2 |

The **5,151** original indexed boundary edges meet at 4,547 degree-two vertices
and **296 branching vertices** (284 of degree four, 12 of degree six).
There are no selected edges with multiplicity above two. Thus edge-connected
selection alone does not give a boundary composed of disjoint degree-two cycles.
The inherited native-chart helper had already separated point contacts in
source references; that fan splitting is not silently applied to this audit.

These results remove projected fold/positive-area-overlap concerns for the
specific fixed charts, within the stated numerical scope. They do **not** grant
complete projection injectivity or a valid single trimmed CAD-face domain.
Contacts between faces already sharing an original vertex, loop topology and
any proposed multiple-chart trim decomposition still need their own complete
classification. No domain is filled, merged or discarded because a smoother
surface would be easier to construct.

The next admissible reconstruction step is an explicit boundary/contact atlas
with original membership retained, followed by fitting only on admitted trim
domains and independent complete-domain deviation/export checks. Raising the
polynomial degree on the current pinched masks would leave the upstream
representation problem unresolved. The original rejection limit remains 0.01 mm
as a digital study screen, not a physical manufacturing tolerance.

## Independent checks and refusals

The [verifier](source/verify_charts.py) imports no producer code. It re-reads
original arrays and pinned parent selections, reproduces all UV coordinates
exactly, rebuilds topology using a separate edge dictionary, and enumerates
candidate pairs with a sweep rather than the producer's vectorised pair loop.
All pair predicates are independently evaluated with Python Fraction rationals.
Positive-area pairs would also require rational polygon-clipping area above
zero; there are **zero actual positive pairs**, so actual clipping is vacuous.
Two separate synthetic clipping controls exercise positive area and edge-only
contact.

Four producer controls distinguish a valid shared-edge square, nested unshared
overlap, a folded shared edge and a collapsed projection. The
[refusal runner](source/check_refusals.py) then checks five reason-specific
failures: changed original membership, changed UV, a lost candidate pair, a
forged boundary count and a forged admission flag. Each fails with the intended
reason and publishes no successful verification file.

[Aggregate audit](audit.json), [independent verification](verification.json) and
[refusal results](refusals.json) are public numerical receipts. Original IDs,
coordinates and the complete per-region pair ledgers remain private.
Both final audit and verification, and all refusal controls, run in the existing
Mac CAD Python 3.12.11 / NumPy 2.5.4 environment under the retained local-only
sandbox with 600-second command bounds. Invocations are retained; elapsed
runtimes were not instrumented. No external service or paid compute is used.

## Reproduction and preservation

Use fresh output paths with the existing CAD Python environment:

```sh
"$CAD_PYTHON" source/audit_charts.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_CONNECTED_BUNDLE" --plan plan.json --output "$NEW_AUDIT"
"$CAD_PYTHON" source/verify_charts.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_CONNECTED_BUNDLE" --plan plan.json --audit "$NEW_AUDIT" \
  --output "$NEW_VERIFICATION_JSON"
"$CAD_PYTHON" source/check_refusals.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_CONNECTED_BUNDLE" --plan plan.json --audit "$NEW_AUDIT" \
  --verifier source/verify_charts.py --output "$NEW_REFUSAL_DIRECTORY"
```

Actual invocations wrap these commands with gtimeout and sandbox-exec; the
retained profile denies non-loopback outbound connections. Do not run writers
in a completed private bundle. The [private receipt](private-receipt.json) pins
source snapshots, actual invocation records, all observations and checks.
Private root: `~/Developer/PorschePartsArtifacts/935-chamber-chart-audit-20261104`.

Original OBJ, frozen parent bundle and latest source-reference FreeCAD document
are rehashed unchanged. This increment creates no new part geometry, native CAD,
solid, solver domain or fabrication job. The [documented chain](../../architecture/cadam-local-qwen.md)
and all physical, material, process and manufacturing gates remain unchanged.
The full faithful functional-metal-head goal remains active.
