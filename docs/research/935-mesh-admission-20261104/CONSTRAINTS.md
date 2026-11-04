# Explicit CGAL constraints — witness and real-input preflight

Date: 2026-11-04. This follows the
[rejected projected remeshes](PROJECTED_REMESH.md).
**Exact protection passed on a software witness. No complete head remesh was
executed or accepted in this increment.** The
[aggregate receipt](constraints.json) binds source, runtime and private outputs.

## Decision and scope

The previous selected-face flag did not preserve protected geometry on the full
study surface. The replacement witness uses CGAL's explicit constrained-edge
and constrained-vertex property maps, `protect_constraints(true)` and
`relax_constraints(false)`. Protected faces are excluded from the remeshed face
range. Their edges, the 30-degree sharp edges and boundary edges are locked;
all endpoints of those edges are constrained vertices. This follows the
[CGAL 6.2 API](https://doc.cgal.org/6.2/PMP_Remeshing/group__PMP__local__remeshing__grp.html).
Native preconditions remain enabled. The actual installed headers are separately
hashed; a documentation-level warning is not a substitute for the compiled
implementation's admission rule.

The input remains the coarse reconstructed assembly, with inferred closures and
unresolved anatomical/physical identity. These constraints do not classify
functional interfaces, restore missing observations, establish dimensions of
the physical specimen or admit a manufacturing job.

## Executed software witness

The slightly warped 5 × 5 vertex grid has 32 triangles and two protected central
triangles. With a 0.7 mm uniform target and three native iterations:

- 22 unprotected original oriented triangles change;
- the two protected oriented triangles remain exact, including coordinates;
- native inspection finds no self-intersections or degenerate faces and accepts
  the polygon mesh. The control is intentionally an open patch.

The independent comparison uses canonical triangle geometry, not vertex/face
array order. Counts remain 25 vertices / 32 triangles; those unchanged counts
alone would not establish that remeshing actually changed anything.

A negative run at 0.2 mm returns the explicit length-rejection code and writes
no mesh. This checks that the runtime refuses incompatible protected edges
before remeshing rather than suppressing its precondition.

## Full-input length admission

The full model's OFF input was independently reloaded and compared with the
hash-bound parent NPZ: all 1,048,504 vertices and 2,099,584 triangle index rows
are exactly equal. The protected mask contains 111,463 original faces.
Native classification locks 492,169 edges and 342,090 vertices; an independent
NumPy normal/edge classification reproduces both totals.

| Uniform target | Native long-edge threshold | Oversize locked edges | Result |
|---|---:|---:|---|
| 0.5 mm | 4/3 × 0.5 = 0.66667 mm | 102,444 | Rejected before remeshing |
| 0.7 mm | 4/3 × 0.7 = 0.93333 mm | 0 | Length check passes; preflight only |

The maximum constrained edge is 0.86580353 mm, requiring a uniform target of at
least 0.64935265 mm for this installed check. The installed
`Uniform_sizing_field` uses the **4/3** factor for splitting/preflight. Do not
apply only the looser twice-target warning from prose documentation, disable
native checks, or silently split locked edges to bypass it.

A passing length check at 0.7 mm does not prove surface fidelity, adequate
quality, computational cost or complete job readiness. There is no head output
mesh for either preflight invocation.

## Independent quality-feasibility bound

Under this isotropic edge-operation route, 132,519 original triangles have all
three edges locked. Of the 8,489 triangles below shape quality 0.01, 708 lie in
that set and cannot be changed while preserving these constraints. Even an
otherwise perfect result could therefore remove at most 91.66% of that bad
triangle category. The predeclared 50% improvement target is not ruled out by
this necessary bound; it has **not** been achieved by a CGAL head run.

## Next engineering action

A fine uniform target conflicts with the exact locks. Design and qualify a
spatial sizing field that respects locked-edge lengths while resolving curved
unprotected regions; benchmark its resource use before applying it to the full
model. Qualification needs an actual changed witness, protected-face identity
and native precondition checks. A later full candidate must still pass the same
independent surface-deviation, topology, intersection, volume and quality gates.
Do not turn this runtime witness into head acceptance or repeat a uniform-sizing
sweep to fill a table.

Source-supported CAD reconstruction and unresolved specimen/material/process
requirements remain upstream work. The inferred assembly envelope cannot supply
those observations through remeshing. No rental, external inference, supplier
message or manufacturing order was created for this checkpoint.

## Reproduction and retained evidence

Private bundle:
`~/Developer/PorschePartsArtifacts/935-cgal-constraints-20261104/`.
It contains native source/binary, installed-header hashes, compiler/runtime
metadata, actual argv, controls, full-input preflight reports, parent round trip,
independent feasibility audit and a complete manifest. Model/mask bytes stay
private. CGAL 6.2.1 and the retained repair-trial Python environment were used.
The outer controller bound was 600 seconds; each native call had a 180-second
bound. Execution completed with exit code zero and no timeout.

The runnable sources are the [native witness](source/constrained_patch_witness.cpp),
[controller](source/run_constraint_controls.py),
[order-independent assessor](source/verify_constraint_witness.py) and
[constraint-feasibility assessor](source/audit_constraint_feasibility.py).
Use their CLI arguments shown in source with the retained hash-bound inputs and
fresh output paths. Compile the native source with the same Homebrew CGAL/GMP/MPFR
flags as the preceding inspectors. Do not rerun a writer inside the frozen
private bundle. The JSON property `remeshing_requested_after_preflight` records
intent after length admission; actual execution and resulting mesh checks are
recorded separately. This prevents preparation from masquerading as execution.
