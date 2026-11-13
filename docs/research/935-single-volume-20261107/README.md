# Single-volume delivery of the supported 935 hypothesis

This study converts the existing overlapping 1,120-resource 3MF into one mesh
resource without changing its declared construction hypotheses. It advances the
digital manufacturing input, while the functional metal cylinder-head target
remains open. The private original scan and acquired-surface reconstruction
remain separate, unchanged inputs; this study is not a newly measured replica.
The [acquired-surface continuation](../935-post-interwalk-continuation-20261106/README.md)
is still open and is not replaced by this closed hypothetical delivery.

The delivered study has 8,759,012 triangles, one positive material shell and
17 enclosed cavity shells (0.0194384241 mm³ total). Independent topology, full
intersection classification, every-triangle source checks and exact 3MF readback
pass. All 2,074 final 50 micrometre sections are valid and match the independent
composite contours; maximum symmetric difference is 5.473 × 10⁻¹¹ mm². These
are digital acceptance results under the declared hypotheses.

## Inputs and integration

The base is main `429deaef606277ba81f5e895ff26aebc088cb4a6`, which includes the
contributed-measurement policy and localhost setup work. The policy enables
reviewable external measurements; it does not supply missing specimen data.
See [ADR 0019](../../decisions/0019-accept-contributed-measurements.md) and
the [architecture](../../architecture/README.md).

The starting geometry is the
[closed bare-head hypothesis](../935-bare-head-hypothesis-20261105/README.md),
including its provisional supports, sacrificial plate and coupon. Every actual
coordinate and triangle index of all 1,120 resources is streamed from the old
3MF and checked against its frozen resource report. The head NPZ is separately
bound to the same report. No anatomy, scale, interface, wall or support is
redesigned in this operation.

The new optional Boolean helper is manifold3d 3.5.4 `Mesh64`, executed offline
in the already installed Kali1 native CPU reconstruction image. Its exact image
identity is in `results.json`; the runtime receipt source is commit
`5b2ed10228601db86e4abccd87c5efc6143fcff1`. That runtime's earlier import/version
witness is distinct from this actual head workload. Its unmerged stack branch
is not incorporated wholesale. Qwen/CADAM remain local assistance tools; this
helper does not replace the documented PicoGK/STEP, Gmsh, OpenFOAM, CalculiX and
Adamantine authority or complete their engineering gates. This increment follows
[ADR 0012](../../decisions/0012-local-compute-gpu-last.md) and the
[scan reconstruction workflow](../../architecture/scan-repair-workflow.md).
Requirement `R935-DIGITAL-UNION-1` is a portable single-resource delivery;
application element `A935-MESH64` implements its bounded Boolean operation.
Acceptance links the immutable input audit, independent predicates, source
containment, exact export and complete layer comparison in `results.json`.

## Numerical admission

Analytic overlap, separated-body and translated thin-box controls precede the
head. The thin box demonstrates float32 coordinate collapse; `Mesh64` retains
every exact float64 input triangle. The head and every auxiliary resource must
roundtrip all triangles, coordinates and winding exactly before Boolean union.
Per-face source identities are supplied explicitly. The complete source set is
united in two operations: auxiliary assembly, then auxiliary assembly with head.

The independent existing libigl validator checks the complete resulting mesh.
Its raw report is preserved, including its initially failed export verdict: one
reported contact prevents its automatic export. The existing exact-rational
contact classifier proves that complete finding list to contain only an indexed
shared-simplex contact. A companion export step reruns this proof, checks all
other geometry gates and independently classifies every shell before export.
It neither deletes a triangle nor suppresses a finding with a distance tolerance.

Every output triangle is also checked against its declared source triangle,
using the existing dominant-axis containment helper and a separate orientation
check. The reported floating-point containment bound is a numerical check,
not a formal exact-rational global error certificate. Missing boundary/Boolean
completeness is addressed separately by comparison with every frozen composite
section at the same exact-decimal 0.05 mm planes.

The 3MF writer is unchanged: float64 coordinates use 17 significant digits.
All coordinates, indices and millimetre units are read back and hashed, and the
ZIP CRC is checked. Binary float32 STL remains unsuitable for this geometry.

## Assumptions and remaining qualification

| Item | Declared status |
| --- | --- |
| Scale | Owner-declared 1 OBJ unit = 1 mm; independent specimen calibration missing |
| Head anatomy and closures | Inherited construction hypotheses; not accepted hidden galleries or an independently identified exact variant |
| Supports, plate and coupon | Existing provisional geometry; no machine/process acceptance inferred |
| Enclosed voids | Retained by the union; their existence is disclosed, not automatically repaired or declared removable |
| Source fidelity | This increment checks preservation against the frozen hypothesis inputs; earlier scan-deviation results and limitations still apply |
| Material | No new material selection; RR350 casting references do not identify the specimen or qualify an LPBF substitute |
| Layer height | Exploratory 50 micrometres; neutral contours do not establish exposure or machine compatibility |
| Loads and physics | No new qualified head CFD/CHT, mechanical, fatigue or Adamantine result; previous exploratory results do not qualify this geometry |
| Manufacturing release | Requires process/material data, wall and powder-removal review, supports/orientation/exposure, inspection, machining, calibrated coupons and physical validation |
| Engine release | Requires measured functional interfaces, a validation plan and professional engineering review |

No machine-specific job or exposure recipe is inferred from a geometrically
valid 3MF. The original functional target is neither replaced by a plastic
prototype nor marked complete by this digital export. Supplier enquiries remain
unsent; private geometry is not published in GitHub.

## Replay and resource control

Use a new private output root, the frozen input manifest and the source scripts
in this directory. `prepare_composite.py --help` verifies the actual composite
and extracts auxiliary arrays. `run_kali_union.py --help` accepts the admitted
inputs, bound analytic-control report and explicit owner-host SSH identity. It
uses four CPUs, 8 GiB RAM without additional swap, no network, a 600-second
deadline and an owned container/staging directory. Results and their complete
manifest are recovered and verified before staging removal. No secret is read
through a fallback path.

Run the unchanged full `validate_build_final.py` and `check_contacts.py` from
the earlier study, then `check_union_provenance.py --job ... --output ...` and
`export_union.py --job ... --output ...`. Each job binds every input/source hash;
do not promote a report detached from its mesh and complete finding list.
The original 4 GiB audit guard stopped the first full libigl check. On the
64 GiB Mac a derived copy of the existing controller changes only its RSS cap
and matching reason label to 12 GiB; the 600-second deadline and 4 GiB disk floor
remain. Both attempts and the two-literal derivation are retained privately.

For slicing, reuse the frozen CGAL `slice-hypothesis` binary and its exact-decimal
analytic/refusal controls. Export the admitted arrays as little-endian f64/i64,
verify the binary array readback, then run the existing native slicer at `0.05`.
Reuse the fixed-decimal formatter and complete CLI readback validator.
`compare_all_layers.py --job ... --output ...` compares every section with the
old independently united composite CLI, using the same contour-grid area bound.
The first full comparison and CLI readback both reject one section: at exactly
5 mm, the top of the plate, the native slicer returns 564 individually valid
positive rings nested inside the plate outline. Every other section passes.
The retained raw scalar integral double-counts this coplanar overlap.

`canonicalize_plate_section.py` applies the existing positive-fill union to
that one section. Admission requires that every ring is positive, simple and
covered by the actual 3MF plate rectangle, and that the rectangle itself is
present. This independently proves that their material union is the plate.
GEOS checks the emitted section against both that actual exported auxiliary geometry
and the frozen composite section. Every other serialized byte, including all
other layer coordinates, must remain identical under a complete file readback.
The 3D mesh and layer height are unchanged. A second complete layer comparison
checks the final CLI; no tolerance is relaxed and both failed raw reports remain
retained. This is material union of overlapping valid rings, not repair of a
self-intersecting contour.

Exact argv, source/runtime/input hashes, pre-execution phase ledgers, failures,
terminal receipts and recovered private results are retained in the new capsule.
`results.json` records terminal outcomes and deliverable hashes. This increment
uses existing Mac/Kali resources with **$0 new paid compute**. The original
$35 total / $30 compute / $5 transfer and closeout reserve is unchanged; it is
not reset by this run. No new Vast instance is created or claimed cleaned up.
