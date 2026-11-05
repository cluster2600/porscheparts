# Acquired chamber disk atlas and native references

Date: 2026-11-04. Status: source atlas and native BREP/FreeCAD reference checks
pass; **STEP shared-topology round-trip remains rejected**. The complete faithful
functional-metal head remains incomplete.

This follows the [chart admission audit](../935-chamber-chart-audit-20261104/README.md).
It retains every face in the same eight fixed selections and resolves their
pinched boundaries into explicit source-edge domains. It makes acquired-facet
references, not smooth fitted surfaces or inferred anatomy.

## Fixed construction and independent domain checks

The [initial plan](plan.json) precedes execution. Use the checksum-bound original
arrays and frozen chart bundle, without changing masks, projections, source-ID
splits, coordinates or tolerances. Complete shared-simplex contact checks extend
the earlier audit: when two triangles share an original vertex, any additional
projected segment contact is also forbidden. All **79,610** candidate pairs pass
on the inherited rounded binary64 charts, using exact dyadic integer predicates
and independent Fraction arithmetic. This is not interval physical metrology.

The [producer](source/build_atlas.py) seeds each domain with the remaining face
of minimum original ID. It repeatedly takes the first admissible source-ID-
ordered frontier face. A new face must meet the current disk along one connected
boundary arc of one or two existing edges; every already-present candidate
vertex must belong to that arc. No smoothing or new boundary edge is inserted.

The [independent verifier](source/verify_atlas.py) replays the growth and priority
rules, checks exact original membership, connectivity, Euler characteristic one,
one oriented degree-two boundary cycle and one incident face fan per domain
vertex. It also independently checks every cut against existing original edges.
All original observations are retained; chart boundaries are authoring cuts,
not identified physical holes or component interfaces.

| Historical region | Original faces retained | Verified disk domains | Existing source edges used as cuts |
|---|---:|---:|---:|
| 0 | 2,697 | 129 | 405 |
| 1 | 1,884 | 46 | 220 |
| 2 | 2,086 | 43 | 361 |
| 3 | 509 | 14 | 37 |
| 4 | 820 | 11 | 67 |
| 5 | 2,653 | 101 | 471 |
| 6 | 1,674 | 22 | 44 |
| 7 | 1,700 | 39 | 285 |
| Total | **14,023** | **405** | **1,890** |

The [atlas receipt](atlas.json) and [independent domain verification](verification.json)
retain aggregate results. Original IDs, growth traces, loops and cut ledgers
remain private. No original face is removed or assigned twice.

## STEP failure retained, native BREP follow-up

The exact triangle constructor is the unchanged SHA-pinned
[retained native helper](../935-source-shells-20261104/source/build_source_shells.py).
It uses original vertices and edges globally within each region and puts each
disk in a separate open shell. No vertex-fan split or coordinate welding occurs.

The default STEP route fails the independent unit-square control: two shells
sharing an original edge reopen with **6 vertices / 6 edges**, rather than
**4 / 5**. The source shapes have not moved; topological sharing is lost.
Enabling the documented nonmanifold settings produces STEP entity graphs with
4 vertex points and 5 edge curves, but the inspected reader still reopens 6 / 6.
Disabling assembly export and SplitCommonVertex in a separate synthetic profile
does not close the reader gate. All these trials remain rejected and retained.
They are software interchange probes, not head parameter tuning.

The relevant settings and default shape processing are documented in
[OCCT's STEP guide](https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html)
and the [7.9.3 controller source](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_9_3/src/STEPControl/STEPControl_Controller.cxx).
These sources explain available controls; the local actual-file checks determine
acceptance. No arbitrary coordinate welding is used to make the reader pass.

The separate [native BREP follow-up plan](native-brep-plan.json) records this
failure before execution and **leaves the STEP gate unaccepted**. It writes the
same original-source compounds in OCCT's native BREP format. BREP is unitless:
each file has a SHA-bound sidecar recording owner-confirmed millimetres, not
independent specimen measurements.

The [native adapter](source/native_reference.py) independently reopens each
actual BREP, checks global original vertex/edge uniqueness and coverage, counts
zero solids, identifies every disk shell, then re-exports that actual shell for
the unchanged [independent source inspector](../935-source-shells-20261104/source/verify_source_shells.py).
Every original triangle, orientation, straight edge, incident face relation and
shell membership passes. The shared-edge unit-square fixture now measures 4
vertices, 5 edges, 2 faces and 2 shells after native reload.

Across all eight actual source references, vertex round-trip discrepancy is
**0.0 mm recorded**; the greatest native-plane/corner discrepancy is
**1.131e-13 mm**. These are numerical export checks, not scanner accuracy,
physical tolerance, strength or manufacturing validation.

## Saved FreeCAD document and source coverage

The new private editable document is:

`~/Developer/PorschePartsArtifacts/935-chamber-disk-atlas-20261104/deliverables/935-acquired-chamber-disk-reference.FCStd`

It has eight source-reference objects, 14,023 acquired facets, 405 open disk
shells and zero solids. The [creator](source/create_native_document.py) imports
only the admitted BREP files, saves and reopens the document, and exports each
**actual saved feature** again as BREP. Independent original-source inspection
of all those exports passes with global source sharing preserved and the same
0.0 mm recorded vertex discrepancy. The fixture copied into the inspection
directory is not a document feature.

[Native inspection](native.json), [saved-document receipt](document.json) and
[saved-feature inspection](saved-feature-verification.json) are aggregate
receipts. The adapter's private legacy key named step_sha256 hashes the actual
BREP bytes in BREP mode; public receipts label it native_brep_sha256.

The earlier five-object reference remains unchanged and separate. Direct
original-ID comparison finds no overlap: these 14,023 native reference facets
add to the previous 21,472, for **35,495 distinct acquired faces represented**
across the separate documents. The [coverage receipt](coverage.json) is a source
triangle-ID count, **not a head-completion percentage or accepted body domain**.
It does not establish physical identity, hidden galleries or functional fit.

## Controls, reproduction and preservation

Five producer fixtures check point contacts, deterministic seed choice,
unshared collinear overlap, legal shared-vertex contact and complete square
coverage. [Seven reason-specific refusals](refusals.json) reject changed source
membership, a broken boundary cycle, a changed growth seed, a forged cut edge,
an admission flag, a wrong units sidecar and a wrong actual native file.
No rejected case publishes a successful verification result.

The Mac uses Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1 and OCP module 7.9.3.1
(distribution 7.9.3.1.1); the native document uses FreeCAD 1.1.4. Acquired-data
construction, independent checks, refusals and document stages run with the
retained local-only sandbox and 600-second command bounds. Separate synthetic
STEP serialisation probes have no sandbox claim. No model service, paid
compute, scan upload, supplier contact or fabrication order is used.

Use fresh output directories and the pinned helpers:

```sh
"$CAD_PYTHON" -B source/build_atlas.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_CHART_BUNDLE" --plan plan.json --output "$NEW_ATLAS"
"$CAD_PYTHON" -B source/verify_atlas.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_CHART_BUNDLE" --plan plan.json --atlas "$NEW_ATLAS" \
  --output "$NEW_VERIFICATION_JSON"
"$CAD_PYTHON" -B source/native_reference.py build --format brep \
  --arrays "$EXACT_ARRAYS" --plan plan.json --atlas "$NEW_ATLAS" \
  --verification "$NEW_VERIFICATION_JSON" --helper "$FROZEN_NATIVE_BUILDER" \
  --output "$NEW_BREP_DIRECTORY"
"$CAD_PYTHON" -B source/native_reference.py verify --format brep \
  --arrays "$EXACT_ARRAYS" --plan plan.json --atlas "$NEW_ATLAS" \
  --verification "$NEW_VERIFICATION_JSON" --helper "$FROZEN_SOURCE_INSPECTOR" \
  --steps "$NEW_BREP_DIRECTORY" --output "$NEW_NATIVE_INSPECTION"
```

The private bundle retains the FreeCAD job, actual invocations, source versions,
failed STEP profiles, raw references, actual saved-feature exports and complete
inspection files. Its [manifest receipt](private-receipt.json) pins the files.
Original OBJ, previous reference, all 84 parent-bundle files and frozen helpers
are rehashed unchanged. Elapsed stage runtimes were not instrumented.

The next reconstruction work can use these explicitly admitted source domains.
No smooth feature, valve axis, hidden passage, complete bare-head solid,
qualified solver mesh or manufacturing job follows automatically. The
[engineering chain](../../architecture/cadam-local-qwen.md) retains all specimen,
physics, process and physical-release requirements; the full goal remains active.
