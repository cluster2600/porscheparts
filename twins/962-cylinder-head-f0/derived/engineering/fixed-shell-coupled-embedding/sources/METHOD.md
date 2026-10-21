# Held exact local-cavity intersection check

This is source preparation, not a completed geometric check. Its only candidate
is the stored coupled-SLSQP diagnostic `e9184514…`: 19 nodes and 39 unchanged
ordered tetrahedra. All 39 exact positive determinants and Q²≥1/100 are checked
again before intersections. The 16 local shell coordinate words remain fixed.
There is no native application, head containment, stitching or physical claim.

Each positive tetrahedron is the intersection of four exact closed inside
halfspaces. Every unordered pair supplies eight planes. The checker enumerates
all 56 plane triples, skips exactly singular 3×3 systems, solves the others by
Cramer's rule, and retains each distinct solution satisfying all eight exact
inequalities. Coordinates are `Fraction.from_float` values of the saved
binary64 words; no tolerance, geometry grid, perturbation or numerical backend
is introduced.

The intersection is a bounded polyhedron. Any nonempty bounded polyhedron has
vertices, including a lower-dimensional face, edge or point intersection. At
each vertex its active normals span ambient R³, so some enumerated independent
plane triple defines it. Hence the retained points are exactly its vertices.
The convex hull K of shared tagged nodes is automatically contained in both
tetrahedra. Their intersection equals K exactly when every retained vertex lies
in K. The checker uses exact equality, segment parameters, or coplanarity plus
triangle barycentrics for zero, one, two or three shared nodes. Duplicate
tetrahedron node sets are refused. Geometric contact between unshared tags is
an illegal contact, rather than invented shared provenance.

All 741 pair verdicts and counts are retained. Every illegal intersection vertex
is retained as an exact rational witness with its generating plane triple and
all eight nonnegative halfspace slacks. There is no first-failure shortcut or
witness sample. A complete pass concerns only the stored local tagged
tetrahedral complex. It does not establish containment in the head or authorize
a native mesh operation. A failure concerns this fixed candidate and does not
prove repair impossibility.

Five existing pure Fraction/vector/quality helpers are copied with exact AST
identity from the frozen coupled caller. The selfcheck is prepared and unrun:
it extracts only exact geometry helpers for synthetic disjoint tetrahedra,
proper face/edge/vertex contacts, illegal overlap, unshared contact, overlap
beyond a shared face, and singular/nonsingular Cramer systems. It reads no saved
candidate and imports no scientific package. No prepared function or test has
been executed by the author.

An eventual ordinary subprocess query can reuse the existing one-query
stdlib protocol: `check_embedding.py actual-contract.json exact-contract-sha256`.
The held metadata proposes a 60-second ordinary subprocess timeout, no retry
and no hard CPU/RSS quota; root must review these controls and freshly bind the
selected interpreter and all small inputs in a separate actual child. No new
controller is supplied. The output is created only after complete enumeration
and post-input checks. All authority remains false and output remains absent.
