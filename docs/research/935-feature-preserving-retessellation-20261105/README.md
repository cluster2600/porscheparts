# Feature-preserving retessellation and geometric admission limits

One bounded local retessellation preserves every required feature edge but
fails its predeclared quality target. The candidate is retained as rejected
evidence and is **not** sent to another volume meshing run. Two upstream audits
then rule out a simple short-edge pass meeting the same target and identify
acute fixed planar sectors incompatible with a uniform shape floor. The
printing master and the previously checked raw volume remain unchanged.

## Why this is a different construction

The [first conditioning](../935-local-conditioning-20261105/README.md)
protects complete face rows near creases. The
[raw volume](../935-unoptimized-volume-20261105/README.md) subsequently passes
complete cell/boundary consistency but fails its shape criterion. Its input
still has 633 triangles forcing incident tetrahedra below diagnostic mean
ratio 0.01. More interior nodes cannot remove that fixed-face bound.

This trial instead protects the exact edge graph: every edge above a
30-degree dihedral in the printing baseline or conditioned input, and every
construction-tag boundary. All endpoint coordinates stay exact. These are
geometrically detected features, not measured functional interfaces. The
independent verifier reconstructs the graph from both frozen inputs, using
interleaved unique-edge incidence and an atan2 angle test; it does not adopt
the producer's mask as its contract.

Only a same-tag face pair sharing an unprotected diagonal can change. All
vertices stay fixed, and the frozen independent quad verifier proves complete
bidirectional patch correspondence. The input is the conditioned hypothesis
surface with SHA-256
`7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f`.
Inferred closures, provisional hardware cuts and the unmeasured scale persist.
Its upstream verdict admits only a diagnostic numerical surface study.

## Fixed plan and actual result

Before execution the plan fixes one pass, a 0.0029 mm new patch budget, a
0.01 mm cumulative correspondence limit relative to the hypothetical printing
baseline, relative volume change below 0.0001, no increase in triangles below
shape 0.01, and at least **50% fewer forced faces** in the 0.01 tetrahedron bin.
There is no parameter sweep or new paid resource.

| Check | Independent result |
|---|---:|
| Candidate edges / qualified flips | 1,150 / 49 |
| Changed face rows | 98 |
| Previously face-protected rows now retriangulated | 51 |
| Required baseline / input feature edges | 701,980 / 702,636 |
| Required union preserved exactly | 702,636 |
| New independent correspondence bound | 0.0012478532 mm |
| Cumulative correspondence bound | 0.0083139575 mm |
| Forced faces before → after | 633 → 584 |
| Reduction / required reduction | 7.7409% / 50% |
| Faces below shape 0.01 before → after | 3,469 → 3,467 |
| Relative volume change | 3.10 × 10⁻¹² |
| Minimum face shape | unchanged, 6.61064 × 10⁻⁷ |

All 98 changed rows lie on retained parent skin, not new caps. All coordinates
are identical, all changed face pairs preserve their construction tag, and
every required edge remains with the same exact endpoints. Complete native
checks find one positive manifold shell with zero open, nonmanifold, winding,
degenerate or intersection findings. Known-quad, forged-bound and overlapping
patch controls pass. The correspondence certificate uses double-precision
analytical patch calculations, not physical metrology or interval arithmetic.

Topology and preservation pass, but quality fails. No field from the producer
or native checker overrides that rejection. The new numerical 3MF is retained
only as a checker artifact; it does not replace head/support exports or neutral
contours, and no new supports or machine job are claimed.

## Short-edge feasibility before another operator

On the unchanged **input**, a fresh independently reconstructed feature graph
has 614,036 fixed vertices. Among the 633 forcing triangles, 602 belong to
retained parent skin and 31 to assumed caps. They have respectively 12, 86,
245 and 290 faces with zero, one, two and three fixed vertices.

A single pass removing only free vertices along existing edges by at most
0.0029 mm has 131 eligible source vertices and 230 directed short edges.
Even ignoring link-condition, collision, quality and disjointness rejection,
their incident faces cover only **160** of the forcing faces. At least 317
would have to improve to meet the fixed 50% target. This optimistic bound
rejects that proposed one-pass operator **before** implementing or meshing it.
It does not rule out larger patches, multiple changed neighbourhoods or a
different explicitly justified geometric contract.

The first audit execution completed its numerical work but failed JSON
serialization of a NumPy boolean. Its exact source snapshot and failed receipt
are retained. The corrected execution uses a new output directory; it changes
only serialization and does not alter input geometry, thresholds or results.

## Fixed acute-sector bound

For a triangle with fixed corner angle alpha, its best normalized shape over
the adjacent edge-length ratio is
`sqrt(3) * sin(alpha) / (2 - cos(alpha))`. For alpha below 60 degrees this
increases with alpha. A planar fan confined to that same acute sector therefore
cannot create a corner triangle above that bound; the incident tetrahedron
mean ratio is additionally bounded by the two-thirds power of triangle shape.
Analytic equilateral and fixed-angle length-ratio controls pass.

The complete forcing-face audit finds 170 distinct fixed corner sectors whose
best planar-fan incident-tetrahedron ceiling is below 0.01. The smallest sector
angle is approximately 0.00002187 degrees and the smallest best ceiling is
0.0000758862. Of the forcing triangles, 139 have no marked edge, 292 have one,
161 have two, and 41 have all three marked edges.

This bound is conditional on retaining the existing planar sector between its
two fixed straight edges and their common vertex. It is **not** a proof that
the head cannot be meshed, printed or simulated. It does not cover arbitrary
nonplanar changes, feature regularization or a separately justified anisotropic
solver-admission criterion. It shows why a universal shape threshold cannot be
promised under the present exact planar-sector contract. The 0.01 bin remains a
diagnostic, not an engine allowable.

[Shewchuk's primary finite-element study](https://people.eecs.berkeley.edu/~jrs/papers/elemj.pdf)
(2002 preprint, sections 2–6) distinguishes interpolation, matrix conditioning
and discretization requirements; their preferred shape measures need not agree.
That motivates a separate method-specific admission study, rather than treating
this dimensionless bin as a universal engineering allowable. It supplies no
validation of this head, its loads or any proposed anisotropic solve.

The next construction must address that incompatibility explicitly before more
volume trials: either justify a bounded numerical feature regularization, or
establish appropriate interpolation, conditioning and convergence checks for
anisotropic cells. Neither approach automatically identifies a physical ridge,
calibrates the scan, admits head physics or qualifies metal manufacturing.

## Executed phase ledger and replay

| Phase | Input / executable | Output and state |
|---|---|---|
| Admission | Frozen conditioned surface, baseline, tags, native receipt | Numerical study only |
| Retessellation | `trial_feature_flips.py`, fixed one-pass plan | 49 flips; quality target failed |
| Preservation | `verify_feature_flips.py`, independent frozen quad helper | All edges/vertices and correspondence passed |
| Native geometry | Frozen `validate_build_final.py` | Complete geometry passed; no release |
| Short-edge admission | `audit_short_edge_admission.py`, initial edge set | Optimistic coverage 160 < 317; no collapse performed |
| Corner admission | `audit_feature_corners.py`, fixed input feature graph | 170 conditional planar-sector limitations |
| Head volume and physics | Rejected candidate | Not executed |
| Metal manufacturing | Unchanged previous conditional files | Not qualified |

[results.json](results.json) binds source hashes, aggregate checks, the private
capsule and its terminal verdict. Sources are in
[source/](source/trial_feature_flips.py); each provides `--help`. Replay into a
new private directory with the recorded scientific runtime. Never write into a
frozen capsule. Private geometry, face/vertex IDs, raw meshes and checker
exports remain outside Git. The full engineering goal stays active.
