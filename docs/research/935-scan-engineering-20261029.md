# 935 scan — supported CAD and engineering preparation

Status: completed local partial-CAD study and analysis-input preparation.
The full functional head and part-specific physics remain blocked by unresolved
geometry, material and boundary-condition inputs. Physical and manufacturing
acceptance remain false; the catalogue source remains `F0_reference`.

This follows the [repair execution](935-scan-repair-20261029.md) and
[repair workflow](../architecture/scan-repair-workflow.md). The raw scan,
supplier screenshot, curves, CAD and geometry-bearing diagnostics remain private.

## Inputs and supplied specifications

The owner explicitly confirmed **1 original OBJ unit = 1 mm**. This is the
accepted project input; no second scale confirmation is required. The original
OBJ SHA-256 remains
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
Independent physical metrology remains unverified.

The screenshot supplies family ranges/options: intake ports 35–44 mm, exhaust
ports 35–41 mm, intake valves 49–53 mm, exhaust valves 41.5–42.5 mm, valve stems
8 mm, spark plugs 12 or 14 mm and chamber volume 86–90 cc. Intake-valve EV8
stainless, exhaust-valve Inconel and seat materials do not identify the head-body
alloy. No exact port/valve/plug variant or operating conditions are selected.
Passage diameters, valve stems, chamber diameter and chamber volume are distinct.

## Executed stages

| Stage | Result and scope |
|---|---|
| Observation support | Every one of 2,099,584 coarse reconstructed face centroids mapped to the original source; distance bands describe spatial support, not missing-surface truth |
| Excluded geometry | All 802 excluded fine-parent components, totaling 14,208 triangles, inventoried; their physical identity/deletion is unaccepted |
| Source partition | All 2,466,040 original triangles assigned exactly once to four geometric regions; region OBJ exports preserve original coordinates and triangle indexing |
| Plane extraction | Four plane candidates with held-out source-point residuals; physical datum acceptance remains false |
| Passage candidates | Three passage candidates retained at two section stations; a fourth remains unresolved and is not completed by symmetry |
| Shank-axis extraction | Two external shank-axis candidates retained; their anatomy is unresolved |
| Observed sections | 241 source-edge-connected paths at 17 nonempty stations: 85 open and 156 closed; no gaps bridged |
| Partial CAD | 13 valid source-supported trimmed planar faces, four reference datums and three constrained circle references; no full head solid |
| NativeCAD | Small supported-face import and FreeCAD export passed; complete-head mesh-to-BRep conversion failed |
| Solver preparation | CFD, CHT and FEA input contracts created; admission refuses all three incomplete cases |

The CAD faces are projected fits of explicitly masked observed triangles. They
preserve support-boundary loops and pass area checks; projection is a declared
geometric change. Circle radii are editable through native spreadsheet/sketch
constraints. The reconstructed head mesh is contextual geometry. Neither static
imported face fits nor three editable circles form a fully parametric head.

## Independent software checks

- Actual STEP faces were reopened with OCCT: 13 valid open faces, no solids.
  Each face passed sampled source-support checks in both directions, using
  4,000 area-weighted samples per direction and its recorded projection limit.
- The section STEP contains 20,465 source-supported straight edges. Its 61,395
  endpoint/midpoint samples have maximum distance approximately
  `1.505e-11 mm` to the immutable scan, below the exploratory `1e-6 mm` limit.
  This checks export support, not physical accuracy or complete port geometry.
- The final native FreeCAD document reopened, retained 241 actual section wires,
  and passed a constrained-radius edit-and-restore check. The separate NativeCAD
  native export reopened and matched the supported face's area.
- Two topology regressions cover open chains, coincident disconnected source
  components, branches and cycles. Four analysis-admission tests pass.

Held-out scan points remain observations from the same sensor dataset. Sampling
is not a Hausdorff bound, dimensional inspection or engineering release.

## Failures and adapter corrections

Trimesh `Path.discrete` follows closed paths and omitted open section chains in
the preliminary extraction. The final extractor identifies endpoints by original
source vertex/edge IDs, traces every retained segment exactly once, stops at
branches and preserves open endpoints. Spatial welding and gap completion are
not used. The preliminary extraction remains in the private attempt history.

Some STEP readers flatten wire compounds into loose edges. Native section wires
were rebuilt from their original ordered source points and checked for closure
and segment counts; the actual saved document is reopened after this correction.

Whole-head NativeCAD conversion failed with `E_GEOMETRY`, reporting 183
zero-thickness regions in its conversion. This is a conversion failure, not an
independent finding about the physical head. A separate 60,000-face simplification
contained 898 intersections and was rejected. Neither result supplied accepted
functional CAD. The supported small-face interoperability test passed with
FreeCAD 1.1.4; its result does not validate a complete-head conversion.

## Private package and replay

The engineering directory is:

```text
~/Developer/PorschePartsArtifacts/935-scan-tools-20261029/engineering-20261029/
```

Start with its `README.md`, `engineering-summary.json`, `interface-contract.json`
and `phase-ledger.json`. Open `deliverables/935-engineering-reference.FCStd` for
native editing, or `inspection/935-engineering-inspection.html` for an offline
inspection view. STEP faces, source section wires, source-region exports,
input contracts, independent reports, source scripts and hashes are retained.
The interactive display samples observations; full partition/support arrays
retain their complete denominators.

Drivers use the existing private source inventory and run-once output directories.
Replay in a new sibling artifact directory using the retained environment and
command order in the private README. Preserve the frozen repair parent and
previous receipts. Verification reads existing inputs; it must not regenerate a
repair, silently choose a nominal variant or overwrite accepted records.

## Remaining evidence gates

Complete port/solid geometry, seat/guide/plug identities and accepted attachment
interfaces are missing. The supplied ranges remain usable design inputs, but
cannot fill hidden geometry or establish specimen tolerances.

CFD needs complete fluid regions, valve positions, inlet/outlet/wall mappings and
flow/temperature conditions. CHT additionally needs the head-body alloy and
thermal properties, heat input and cooling/contact conditions. Structural work
needs accepted solid/load surfaces, temperature-dependent properties, combustion
pressure history, stud preload, contacts and a thermal field. These values remain
null. The guard launches no solver and claims no simulated result.
