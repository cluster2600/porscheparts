# Exact source-facet CAD charts

Date: 2026-11-04. Result: three independently verified STEP chart sets and a
native FreeCAD review document, preserving 4,787 acquired triangles. **These are
22 open surface shells, with zero solids.** Source coverage is unchanged from
the [earlier wall references](../935-observed-wall-cad-20261104/README.md): 0.1941%
of the 2,466,040 acquired triangles. This is topology-aware reference geometry,
not completion of a functional or printable head.
The [aggregate receipt](source-shells.json) binds the sources, actual exports,
independent checks, native document and 48-file private manifest.

## Why this representation is needed

The [periodic freeform candidate](../935-freeform-wall-study-20261104/README.md)
lost too much observed detail. The exact faceted reference remains useful, but
its separate triangle faces do not represent shared edge topology. Inspecting
the original selected masks also finds incident-face fans meeting only at
vertices: 22 such vertices in region 1, 13 in region 2 and three in region 3.
These contacts can arise from selection of partial acquired surfaces; they are
not established defects or physical contacts in the complete specimen.

The new representation makes one native CAD vertex per edge-connected incident-
face fan and one native edge per original source edge. It creates exact planar
triangle faces and groups them by original edge-connected source components.
There is no proximity welding, sewing tolerance, smoothing or gap filling.
No source coordinate moves, triangle is deleted, normal is flipped, or new
surface is inferred. Local discontinuities remain visible.

**Original vertex point-contact topology is deliberately separated in the CAD
charts.** Thirty-eight original vertices have multiple fans, requiring 39 extra
coincident native vertices. This representation does not preserve the original
vertex-contact identifications. Private provenance maps every new corner and
vertex back to the unchanged original source IDs; collapsing that map recovers
the original triangle indexing. Original shared edge/face adjacency is preserved.
Chart components are not identified physical parts or manufactured components.

## Input admission and actual result

The registered source contract and partition hashes are checked before
construction. The source masks and their original face IDs remain fixed.
Coincident distinct source IDs, zero-area triangles, nonmanifold edges and
inconsistent edge winding are refused rather than automatically repaired.
The independent verifier reads the original acquired arrays and registered
partitions, not the builder's private chart arrays.

| Region | Source → native chart vertices | Edges | Original triangles | Open shells | Boundary edges |
|---|---:|---:|---:|---:|---:|
| 1 | 1,032 → 1,055 | 2,759 | 1,700 | 12 | 418 |
| 2 | 985 → 998 | 2,664 | 1,667 | 8 | 327 |
| 3 | 826 → 829 | 2,250 | 1,420 | 2 | 240 |

All three actual STEP files were reopened in native OCCT. The independent
verifier checks:

- Every original triangle appears exactly once, as a planar face with one
  triangular wire; original orientation is retained.
- Every native vertex matches its unique original coordinate: maximum recorded
  round-trip error is **0.0 mm**. Normal dot-product error is at most 4.45e-16.
- Every edge is straight and maps exactly once to an original source edge;
  its complete incident source-face list matches the acquired mesh.
- Every native vertex's incident source-face set equals one independently
  traversed original vertex fan, rather than merely matching a vertex count.
- Every native shell contains exactly one original edge-connected face group.
  Reopened shapes are valid and contain zero solids.

The geometric equality is within this selected digital scan and recorded
arithmetic. Owner-confirmed millimetres remain the scale input; independent
physical metrology, tolerances and anatomical identities remain unverified.
The 985 boundary edges remain open. No cap, port closure, hidden gallery or
missing attachment definition is supplied by these charts.

## Controls and retained attempt

A two-triangle square control reopens with four vertices, five edges and one
shell. A point-contact control reopens with six native vertices, six edges and
two shells, while retaining five original source vertex identities. This checks
that STEP does not weld coincident chart vertices back together. Four source
refusal controls check inconsistent winding, a nonmanifold edge, a degenerate
triangle and coincident distinct source IDs, including the expected reason.

An independent negative control substitutes the earlier **exact but unsewn**
region-1 STEP. It is rejected for duplicated native source edges before any
successful verification output. Correct coordinates and triangle counts alone
therefore cannot satisfy this topology check.

`build-001` remains retained. Its winding-refusal fixture was accidentally
degenerate, so it could fail for the wrong reason. `build-002` fixes that fixture,
adds the separate nonmanifold-edge refusal and checks the actual exception
reason. Source geometry and the construction policy are unchanged; only
`build-002` is forwarded to the delivered files.

## Native document, privacy and software position

Private delivery:
`~/Developer/PorschePartsArtifacts/935-source-shells-20261104/deliverables/`.
Open **`935-exact-source-charts.FCStd`** in FreeCAD 1.1.4. It contains three valid
Part features with the topology counts above and `ManufacturingAuthorized=false`.
It was saved, closed and reopened natively. A separate read-only native reopen
under outbound denial rechecked the same counts and left its hash unchanged.
Three region-specific `*-exact-source-charts.step` files are also delivered.
Python sources and private original-ID/fan arrays support regeneration; the
imported Part features are static reference geometry, not a fully parametric
functional-head master.

This is the existing scan-derived STEP/FreeCAD branch. PicoGK remains the new
engine geometry route; [CADAM/Qwen](../../architecture/cadam-local-qwen.md) remains
local proposal assistance. No model supplied its own inspection evidence here.
Gmsh, OpenFOAM, CalculiX and Adamantine receive no newly admitted complete domain
from these open charts. Earlier failed fits and hypothesis simulations retain
their recorded scopes.

Construction, actual STEP verification, the unsewn negative control and the
read-only FreeCAD reopen ran under the retained macOS policy denying non-loopback
outbound connections. Initial FreeCAD document creation is not claimed to have
used that sandbox. No external CAD/model service or supplier received geometry.
Previous native masters were rehashed unchanged. Geometry and provenance arrays
stay private; Git contains only code, aggregate results and hashes. No paid
rental, supplier message, fabrication order or new solver run occurred.

## Reproduction

Use the recorded local CAD runtime: Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1,
`cadquery-ocp-novtk` 7.9.3.1.1, and native FreeCAD 1.1.4. Replay from the repository
root into a fresh private directory, never inside a frozen bundle:

```sh
set -e
ARTIFACTS="$HOME/Developer/PorschePartsArtifacts"
SCAN="$ARTIFACTS/935-scan-tools-20261029"
CAD_PYTHON="$SCAN/engineering-20261029/cad-venv/bin/python"
ARRAYS="$SCAN/other-tools/exact-source-arrays.npz"
PAPER="$SCAN/paper-feature-section-pairs-20261029"
PREPARATION="$ARTIFACTS/935-observed-wall-cad-20261104/preparation-002"
SOURCE="$PWD/docs/research/935-source-shells-20261104/source"
POLICY="$PWD/docs/research/935-observed-wall-cad-20261104/source/local-only.sb"
REPLAY="$(mktemp -d "$ARTIFACTS/935-source-shells-replay.XXXXXX")"
/usr/bin/sandbox-exec -f "$POLICY" "$CAD_PYTHON" \
  "$SOURCE/build_source_shells.py" --preparation "$PREPARATION" \
  --paper "$PAPER" --output "$REPLAY/build"
/usr/bin/sandbox-exec -f "$POLICY" "$CAD_PYTHON" \
  "$SOURCE/verify_source_shells.py" --cad "$REPLAY/build" \
  --arrays "$ARRAYS" --paper "$PAPER" --output "$REPLAY/verification"
/usr/bin/sandbox-exec -f "$POLICY" "$CAD_PYTHON" \
  "$SOURCE/check_source_shell_refusal.py" --cad "$REPLAY/build" \
  --arrays "$ARRAYS" --paper "$PAPER" \
  --unsewn-reference "$ARTIFACTS/935-observed-wall-cad-20261104/cad-005/stud_passage_1_wall_candidate-reference.step" \
  --output "$REPLAY/unsewn-refusal"
```

For the native document, copy the retained non-secret `native-job.json` to the
replay directory. Point its items at the new STEP files, bind hashes/counts from
the independent verification, and choose new output/report paths. Run
`create_chart_document.py` with that job path in `PORSCHE_SOURCE_CHART_JOB`, using
the installed `FreeCADCmd`. Require its report and `SOURCE_CHART_DOCUMENT_OK`.
Then run `verify_saved_chart_document.py` under the same outbound-denial policy,
with a fresh report path in `PORSCHE_SOURCE_CHART_OFFLINE_REPORT`; require
`SOURCE_CHART_OFFLINE_REOPEN_OK`. Neither shell exit alone nor native validity
grants manufacturing acceptance. Changed geometry requires new verification.

The functional-metal goal remains active and incomplete: full observed geometry,
component identities, unknown internals, measured interfaces, specimen alloy and
loads, admitted meshes, calibrated physics, qualified metal process and actual
professional/physical acceptance remain necessary.
