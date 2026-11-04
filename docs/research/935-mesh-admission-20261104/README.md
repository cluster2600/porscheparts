# 935 retained-mesh admission audit — 2026-11-04

This read-only audit resumes the [executed hypothesis study](../935-hypothesis-study-20261029.md).
It changes the next engineering action; it does not create a new head, run a
solver or admit the existing meshes to engineering release.

## Input admissibility and audit scope

The inputs are the recovered 2, 1.5 and 1 mm interior tetrahedral study meshes.
Their SHA-256 values were freshly checked against the recovered science manifest
before loading. They describe a closed reconstructed assembly with attached
hardware and inferred closures, not an accepted bare-head domain. Existing
unresolved thin regions and physical interfaces remain unresolved. The audit
is admissible as a diagnostic of those exact study meshes, not as proof of
functional geometry. No new parameter sweep or paid compute was run.

The [report](audit.json) records complete denominators, original input hashes,
the recovery-manifest digest and audit-source digest. The
[source](source/audit_retained_meshes.py) computes signed tetrahedral volumes,
a normalized tetrahedral mean-ratio metric, boundary triangle quality and
boundary-node incidence. This metric is **not** Gmsh minSICN. Its 0.01 and 0.1
bins are diagnostic thresholds, not engineering acceptance criteria.

## Executed results

| Interior sizing label | Tetrahedra | Mean ratio < 0.01 | Mean ratio < 0.1 | Minimum mean ratio |
|---|---:|---:|---:|---:|
| 2 mm | 3,098,918 | 22,259 | 263,081 | 1.069e-7 |
| 1.5 mm | 3,771,342 | 17,823 | 199,048 | 1.384e-7 |
| 1 mm | 6,624,763 | 13,258 | 141,748 | 2.440e-7 |

All three surfaces contain exactly 2,099,584 triangles, and the complete ordered
boundary XYZ bytes are identical across meshes. Triangle quality ranges from
3.304e-6 to 1; its first percentile is 0.02512. Every element in either bad-quality
bin touches at least one boundary node; no entirely interior element is in those
bins. This is a node-incidence classification, not exact boundary-face adjacency.
It supports investigating the fixed boundary discretization; it does not prove
the cause of each bad element or a defect in the physical specimen.

All volumes are positive and total 1,106,103.025522435 mm³ within floating-point
roundoff. Elements below 0.01 account for only 1.491e-6, 6.822e-7 and 2.435e-7 of
the absolute volume respectively. A small affected volume does not certify local
stress accuracy. Refinement improves median element quality, but the worst
quality remains very low. Existing stress-convergence and calibrated engineering
acceptance remain unproven.

Four analytic controls passed before execution: regular tetrahedron volume and
unit quality; inverted orientation; coplanar zero volume/quality; and translation/
scale invariance. Inputs were read only, with no existing artifact overwritten.
Negative controls also confirmed refusal of an existing output and an input
checksum mismatch, preservation of the existing report, and no output after
input rejection.
The public report contains no coordinates, connectivity or source scan.

## Reproduction and next experiment

The private result is `~/Developer/PorschePartsArtifacts/935-mesh-admission-20261104/`.
Use the retained local NumPy environment and a fresh output path:

```sh
PYTHON="$HOME/Developer/CADAM/local-calibration/.venv/bin/python"
"$PYTHON" docs/research/935-mesh-admission-20261104/source/audit_retained_meshes.py --self-test
"$PYTHON" docs/research/935-mesh-admission-20261104/source/audit_retained_meshes.py \
  --root "$HOME/Developer/PorschePartsArtifacts/935-scan-tools-20261029/hypothesis-run-20261029/science-recovery" \
  --output "$HOME/Developer/PorschePartsArtifacts/935-mesh-admission-REPLAY/audit.json"
```

The next candidate should treat the boundary triangulation, followed by explicit
projection/deviation checks, rather than vary interior sizing alone. Before that
candidate is accepted, check complete surface topology and intersections,
bidirectional deviations against its frozen parent and the acquired scan,
protected feature changes, inferred closures and thin-region exclusions.
Re-tetrahedralization then needs independent volume/quality checks and the same
physics convergence/balance requirements. A remesher cannot supply missing
functional surfaces, material properties or physical measurements.

This is a new experiment proposal, not an executed remesh. The
[local CADAM/Qwen branch](../../architecture/cadam-local-qwen.md) remains assistance
for editable proposals; its synthetic coupon cannot approve this domain or
replace this mesh audit. All functional and manufacturing release flags remain
false. No rental, supplier message or fabrication order was created.

The subsequent [full-surface planar-flip trial](PLANAR_FLIP.md) executes a
connectivity-only candidate. It passes its geometric screen but is not advanced
to volume meshing because the quality improvement is negligible. The original
meshes and this audit remain unchanged.

The [projected remeshing trials](PROJECTED_REMESH.md) then improve triangle
quality substantially, but both fail independent admission. The masked trial
eliminates intersections while still changing protected geometry and exceeding
the deviation limit. These rejections motivate an explicitly constrained patch
witness rather than further unconstrained remeshing or interior-size sweeps.

The subsequent [CGAL constraint witness and real-input preflight](CONSTRAINTS.md)
verify exact protection on a changed software patch. The installed 4/3
long-edge criterion rejects the full head's 0.5 mm uniform target before
remeshing. A 0.7 mm target passes that length check only; no head result is
produced or accepted. An independent constraint/quality audit bounds the next
sizing-field design.

The [variable-size trial](VARIABLE_SIZING.md) subsequently executes on the full
surface within its resource bounds. All 111,463 protected triangles are preserved
exactly, but 35 intersection pairs and excessive sampled deviations reject the
candidate. This verified failure returns the next admission work to
source-supported CAD regions and geometry diagnosis; no volume mesh or solver
case is launched from the rejected surface.

The subsequent [observed-wall CAD review](../935-observed-wall-cad-20261104/README.md)
returns to registered acquired-face masks. It delivers exact faceted references
and one independently checked partial cylindrical fit in STEP and a private
native FreeCAD companion. It creates no complete head solid and does not admit
the rejected remesh or a new solver case.
