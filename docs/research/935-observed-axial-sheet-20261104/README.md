# Acquired axial-facing sheet: exact native CAD reference

Date: 2026-11-04. A new STEP reference preserves **13,895 additional acquired
triangles**. A new FreeCAD document combines this open sheet with the three
earlier acquired regions. The actual saved/reopened feature is exported and
independently checked against the original scan arrays. No complete head solid,
physical interface acceptance or manufacturing release is claimed.

The [receipt](observed-sheet.json) contains aggregate measurements, controls,
source and artifact hashes. Geometry, source-ID masks, complete candidate
inventory and native documents remain private. This resumes acquired-surface
reconstruction after the [closed-study mesh investigation](../935-mesh-admission-20261104/CLOUD_VOLUME.md);
it does not use the inferred envelope as new scan evidence.

## Registered input and selection

The original OBJ remains unchanged, SHA-256
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
The decoded acquired arrays contain 1,281,608 vertices and 2,466,040 triangles.
Their SHA-256 is
`dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a`.
Units remain owner-confirmed millimetres; independent physical metrology is
unverified. No dimension from another head is used.

The [selector](source/select_observed_sheet.py) fixes the rule before the CAD
trial: original geometric partition 0, whole acquired triangles with normals
within 20 degrees of either existing frame-C direction, inside the existing two
end-face search references with a 2 mm search margin. It selects the largest-area
source-edge-connected component, with ties resolved by smallest original face ID.
The frame and search references are geometric aids, not accepted physical datums.
The margin selects observations; it does not create a wall or alter coordinates.

All 395,964 eligible triangles and 21,380 edge components are inventoried privately.
The selected component contains 13,895 faces / 7,473 original vertices and
1,524.6640 mm² of observed triangle area. It has no coincident distinct source
vertices and no face implicated in the original intersection index. Eight zero-area
faces remain retained in the original data, outside the normal-eligibility rule.
No source face is deleted, welded, capped or completed. This component's identity
as a physical fin, interface, bare-head surface or attached hardware is unaccepted.

The registration is frozen before native construction. A source-hash mismatch,
an existing output, excessive candidate size or an indexed defect refuses the
trial; the builder does not silently choose another mask. The component controls
distinguish a shared source edge from a vertex-only contact.

## Single-plane proposal rejected

A diagnostic plane is fitted to 5,999 original vertices; 1,474 disjoint source
vertices are held out by a deterministic source-ID split. The all-vertex maximum
projection is **1.003563 mm**, and held-out P95 is **0.516208 mm**, exceeding the
registered 0.01 mm digital projection screen. This plane is not exported or adopted.

The result describes approximation of the acquired patch, not physical warpage
or scanner accuracy. Mask selection uses the complete acquisition, including
normal eligibility; this within-scan holdout is not blind physical validation.
The native reference retains the acquired nonplanar shape as exact triangular
faces instead of replacing it with that plane.

## Actual STEP and saved FreeCAD checks

The [builder](source/build_observed_sheet.py) reuses the immutable qualified
source-chart constructor. It compares coordinates/connectivity with the original
arrays, then makes one native edge per original edge and one vertex per original
edge-connected incident-face fan. It applies no healing or projection.

| Representation | Vertices | Edges | Original triangle faces | Shells | Solids |
|---|---:|---:|---:|---:|---:|
| Original selected patch | 7,473 | 21,486 | 13,895 | One source edge component | — |
| Native chart / actual STEP | 7,504 | 21,486 | 13,895 | 1 open shell | 0 |

Thirty-one original vertex-only contacts are represented by additional coincident
native vertices. Original vertex-contact identification is therefore separated;
original face/edge adjacency, coordinates and private source-ID provenance remain.
This representation is not a physical part separation or a new contact model.

The [independent verifier](source/verify_observed_sheet.py) loads the actual STEP
and the original arrays, separately from the builder. It checks every triangle
exactly once, orientation, straight source edges, complete edge-to-face adjacency,
original vertex fans, shell grouping, native validity and zero solids. Vertex
round-trip error is 0.0 mm; normal dot-product error is at most 4.44 × 10⁻¹⁶.
Every native triangular support plane is also checked against its corner vertices;
the maximum distance is 9.09 × 10⁻¹² mm. These are digital consistency results,
not specimen tolerances.

The new **`935-observed-axial-sheet-reference.FCStd`** has four reference objects:
the unchanged three previous regions and the new open sheet. Native FreeCAD
1.1.4 saves, closes and reopens it with matching counts, valid shapes and zero
solids. Its SHA-256 is
`040ac78f598ba1bfaf0eed33f06ac3434466fe00c83ae6201726c38b8652fd22`.

A second [read-only native reopen](source/export_saved_observed_sheet.py) checks
counts, identity placements, source-STEP hashes and manufacturing flags. It exports
the **actual saved feature**, which is independently reloaded and subjected to the
same full source comparison. All checks pass again, with 0.0 mm vertex error and
the same topology/normal/plane results. The original FreeCAD file hash is unchanged.
This checks serialisation geometry as well as counts; shell exit alone is not
the acceptance evidence. The creation and verification completion markers and
their reports are retained.

The original OBJ and the engineering, observed-wall and previous exact-chart
FreeCAD masters were freshly rehashed unchanged. No previous master is overwritten.

## Coverage and scope in the chain

The new acquired-face mask has zero overlap with the earlier 4,787 exact-reference
triangles. Their union now represents **18,682 unique acquired triangles in 23
open native shells**, 0.75757% of acquired triangle identities. This is a reference
coverage denominator, **not a head-completion percentage**. No new scan observation
or physical measurement has been acquired. These faceted references are editable
native geometry with reproducible source masks; they are not a complete parametric
head, reconstructed hidden passages or a machine build file.

The [CADAM/Qwen branch](../../architecture/cadam-local-qwen.md) remains local
proposal assistance. It did not generate or accept this patch. The existing
STEP/FreeCAD observation branch retains its role; PicoGK remains the new engine
geometry route. Gmsh, OpenFOAM, CalculiX and Adamantine retain their separate
geometry/material/load/process admission requirements. This reference does not
advance the previous inferred assembly to functional solver acceptance.

Two native topology controls and four reason-specific source refusals pass.
Additional controls reject an existing CAD output, a wrong original-array hash
before output, and an independently substituted wrong STEP before output, while
preserving the verified file. Selection, native construction, both actual STEP
checks and both FreeCAD stages retain their actual commands/logs. The successful
native construction, complete STEP verifications and FreeCAD stages run under
the unchanged outbound-denial profile.

## Private delivery and replay

Private root:
`~/Developer/PorschePartsArtifacts/935-observed-axial-sheet-20261104/`.
Open `deliverables/935-observed-axial-sheet-reference.FCStd` for native inspection.
The exact new reference STEP is
`cad-001/observed-axial-sheet-source-charts.step`; its hash is
`b11e1dda5138e2546883e2b941a2780911a7e032ac128eb416c80fd009506af7`.
The actual saved-feature round-trip STEP and its verification are also retained.

Replay the published selector, builder and verifier with the registered acquired
arrays, partition, frame, end-plane references and original intersection index.
The adapters require the frozen constructor/verifier hashes and this registered
selection. Use the retained CAD Python environment and fresh output directories;
do not run writers inside a frozen bundle. The private job records supply exact
argv and bindings. The installed `FreeCADCmd` runs the retained generic document
creator with `PORSCHE_SOURCE_CHART_JOB`, then the read-only export script with
`PORSCHE_OBSERVED_SHEET_ROUNDTRIP_DIR`; require markers **and** reports before the
independent STEP checks. Outer deadlines are 600 seconds per stage.

Runtime: Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1, OCP module 7.9.3.1 / distribution
`cadquery-ocp-novtk` 7.9.3.1.1, FreeCAD 1.1.4. The 51-file private manifest binds
source snapshots, registered masks, component inventory, held-out plane diagnostic,
actual commands/logs, controls and delivered native files. Public files contain
methods, aggregate results and hashes only. No new paid resource, external
CAD/inference service, supplier message, fabrication order or release occurred.
The [full completion requirements](../935-readiness-20261104/README.md) remain open.
