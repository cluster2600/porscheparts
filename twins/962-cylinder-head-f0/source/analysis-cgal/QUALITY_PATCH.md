# Original-source local quality pass: method and retained checkpoint

The new `quality_patch.cpp` is a separate analysis-representation experiment.
It does not repair the geometry master or admit a head to simulation.
The [fixture contract](../../engineering/analysis-quality-patch-contract.json) freezes
the inputs, synthetic fixtures, quality objective and prospective resources.
Its initial head-execution hold was later lifted for the single pass recorded
below, under a separate child contract; the fixture freeze remains unchanged.

The starting surface is the original inspected bore95 solid, SHA-256
`ba7a0e28dade659550705e9737177c64c7f6fecd8d86d01e31732d7e739cd906`.
Its exact indexed binary input is
`894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95`.
The larger collapsed surface is not the starting geometry.

The patch contains every original face incident to a vertex of a face with
triangle SICN below 2/29. Original-source inspection gives 744 seeds,
1,284 seed vertices, 4,704 patch faces and 3,858 patch vertices. Any vertex with
an incident exterior face is fixed: 2,556 patch vertices meet this rule.
Original vertices with x exactly −76 or +76 mm are also fixed, including 12 patch
vertices. Edges with both endpoints fixed are constrained. These conservative
rules contain no fitted weld tolerance or guessed crease angle. They are not
a complete port/channel/BCC feature map or a Porsche interface contract.

CGAL 5.6 performs one default atomic `isotropic_remeshing` pass at target 0:
flips, one tangential-relaxation step and projection. Split/collapse are
explicitly disabled; constraints cannot relax, and `protect_constraints` is
false. The projection functor queries an immutable AABB tree of the ORIGINAL
source, not a previously displaced candidate. No face quota or iteration
search is used. [Official API reference](https://doc.cgal.org/5.6/Polygon_mesh_processing/group__PMP__meshing__grp.html#gaa5cc92275df27f0baab2472ecbc4ea3f)

The full-surface incompatible-face count must strictly decrease AND the
full-surface minimum triangle SICN must not decrease. Fixed coordinates,
exterior oriented faces, vertex/face counts and closed validity must remain
unchanged. There is no objective tolerance. `proposed-surface.bin` always
retains a completed proposal; `quality-candidate.bin` is written only when
these preliminary conditions pass. A rejected/stagnant update is not promoted
and no automatic extra pass occurs. The [independent objective guard](../audit_quality_patch.py)
rejects nonfinite metrics, non-integer counts and contradictory native claims.

Native synthetic fixtures demonstrate a movable sliver improvement, fixed
anchor preservation, a constrained stagnant case correctly rejected, and
existing-output refusal. They verify API/control behaviour only. Their files,
pre-native freeze, full-array assessment and native receipts are retained in
`work/962-engineering/quality-patch-fixtures-001/`. Compilation used the
already-owned ARM64 CGAL5.6 toolchain; no dependency or image was installed.
The initial header-inspection attempt failed before reading because that
toolchain image has no `/usr/bin/python3`; its refusal remains separate.

Before interpreting any future head proposal, an independent reader must
recompute ALL before/after qualities and fixed/exterior coordinate and
connectivity checks from the actual binary arrays. Self-reported JSON alone
cannot establish this. The indexed input must also match every original STL
coordinate and oriented triangle; hashes alone are insufficient.

All original gates remain: two completed independent continuous distance
intervals against the source within 0.25 mm, gap at most 0.0001 mm each; zero
global self-intersections; positive volume, edge/vertex manifold, one component
and Euler characteristic −208; unchanged fluid domains, eight dry probes,
clearance and independent feature/channel/BCC review. A later tetrahedron
mesh needs the exact oriented analysis-surface boundary, positive Jacobians,
minimum SICN 0.1 and unchanged volume bookkeeping. Projection and the necessary
fixed-face screen establish none of these gates alone.

The head execution is limited to 2 CPUs, 4 GiB with no swap and 300 s,
with no network, paid resource or automatic retry. It requires the separately
frozen execution contract after root review. Head physics, material/process
calibration, convergence and manufacturing authorisation remain open.

## Single authorised original-head pass

The separate [head execution contract](../../engineering/analysis-quality-head-contract.json)
binds the reviewed source/binary, native fixtures and a complete original-STL
coordinate/oriented-triangle identity receipt. The native pass completed in
3.82 s without OOM or deadline expiry. No second pass or tetrahedron operation
was run. All bound inputs remain unchanged.

The frozen [independent array assessor](../audit_quality_head.py) reread every
source/proposed triangle. It confirms 744 to zero facets below 2/29, with minimum
triangle SICN improving from 2.2723905926649325e-6 to 0.06923322066867299.
All 900,845 fixed source coordinates and every exterior oriented face are exact;
the 902,145 vertices and 1,804,706 faces remain. Proposal SHA-256:
`7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43`.
The exact native reports, final container state, independent arrays assessment
and hashes are retained under `work/962-engineering/quality-patch-head-001/`.
This checkpoint passes the frozen quality objective only; its historical flags
remain unchanged. The later [quality/topology/scoped-feature capsule](../../derived/engineering/analysis-quality-candidate/README.md)
and [continuous-distance capsule](../../derived/engineering/analysis-quality-distance/README.md)
record separate checks. Full Porsche/CSG semantic coverage, conformal interfaces,
head physics and manufacturing authorisation remain unestablished.

The feature runner requires its retained local execution contract, which binds
a private interpreter path. Git contains the explicitly labelled safe
[feature-contract projection](../../derived/engineering/analysis-quality-candidate/contract-projections/feature.json),
not that raw local contract. The public source snapshots support review; full
native reproduction also needs the hash-bound local inputs and runtimes.
