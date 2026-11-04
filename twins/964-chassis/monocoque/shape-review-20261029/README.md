# Geometry rejected: rebuild the central monocoque

**Decision, 29 October 2026: the retained whole-body envelope is not an
acceptable geometry baseline for the requested ZESAD/RUF-style product.**
Native RTX execution proved that the supplied scene renders; it did not resolve
this architecture mismatch. Correct camera framing would still show the wrong
design. Continue with central-cell reconstruction before another paid rendering
or structural-parameter study of the product.

This is a design-review decision, not a new CAD revision or an implemented
runtime interlock. The historical geometry, calculations and capture receipts
remain unchanged. [review.json](review.json) identifies the reviewed inputs and
the outstanding acceptance criteria.

## Direct comparison

The two images linked from the [ZESAD product page](https://zesad.com/product/porsche-964-and-993-carbon-fiber-monocoque-for-restomods/)
were downloaded and inspected at their original resolution:
[front detail](https://zesad.com/wp-content/uploads/2025/09/DMC_964-993_Carbon_Fiber_Monocoque_1.jpg)
and [complete assembly](https://zesad.com/wp-content/uploads/2025/09/DMC_964-993_Carbon_Fiber_Monocoque_2.jpg).
They depict a central cell with substantial sills, shaped interior surfaces,
front and rear walls, a central raised volume, exposed attachment plates and an
upper frame. They do not depict the complete outer body envelope used by our
current model. This is a visual observation, not a dimensional reconstruction
or verification of the vendor's product claims.

The [VELA RUF CTR/SCR reference](https://www.vela-group.com/en/performance-vehicles)
shows the central cell within a complete chassis, with separate front/rear
structures and suspension assemblies. Its original
[chassis image](https://static.wixstatic.com/media/7f6314_a710be091e81457caef17a203678fc6f~mv2.png)
was also inspected. [RUF's German description](https://www.ruf-automobile.de/de/modelle/serie/)
identifies the carbon monocoque, steel-tube front structure and safety cage,
and a rear structure using steel tubes and machined light-alloy supports.
These are architecture precedents, not interchangeable 964/993 assemblies.
They do not establish that ZESAD supplies RUF.

Vendor images remain private reference copies under `work/`; only their source
URLs and hashes are recorded. No redistribution licence has been established.
They are not traced, scaled or committed as source geometry.

Our inspected views are the [local full-body view](../omniverse/media/local-001/front.png)
and [native interior view](../omniverse/native-review-20261029/rtx/interior.png).
The discrepancy is visible in both, so it is not caused solely by the RTX
camera or materials.

| Zone | Current construction, confirmed in source/report | Required correction |
|---|---|---|
| Product boundary | A complete 911-shaped exterior envelope; structural rings also surround lids and wheel arches | Model the central load-bearing cell explicitly. Keep exterior bodywork and front/rear assemblies separately identifiable; define how their loads enter the cell. Hiding `OuterSkin` alone does not change the remaining architecture. |
| Cabin floor and walls | A nominal 25 mm panel and two simplified cross-plane walls | Reconstruct footwells, seat-support regions, front bulkhead and rear transition from applicable measured surfaces. Identify cabin space, access and service routes before closing volumes. |
| Sills and door entry | Assumed 210 mm-wide boxes extending 270 mm above the floor | Develop continuous sill/door-entry sections around the real apertures and occupant package, with deliberate junctions to the front and rear walls. |
| Central tunnel | Constant assumed 200 mm width and 240 mm height between the bulkheads | Establish the installed C2 shift mechanism, its motion and access. Design a varying tunnel section only from the resulting package; keep C4 shaft/differential accommodation as a separate variant. |
| Upper load path | Deep rims derived from the exterior openings and a generic B-ring | Define the windshield, roof and door-opening load paths independently of exterior styling. Preserve the requested carbon structural intent; RUF's steel cage is not an instruction to substitute steel in this project. |
| Front/rear attachments | Generic longitudinal boxes; no measured suspension, powertrain or restraint attachments | Define the mounting axes, mating faces, bolt patterns, reinforcement and force transfer for each actual assembly. Visible plates in vendor images do not provide these dimensions. |
| Surface and manufacturing detail | Stepped edges and apparent overlapping surfaces visible in the rendered assembly; no released mould geometry | Resolve junction topology, intended wall/core construction, radii and demoulding access on the reconstructed surfaces. Do not disguise defects with smoothing or a carbon shader. |

The dimension examples above are **existing modelling assumptions**, not
replacement design dimensions. They are retained to explain the failure, not
to prescribe the next part.

## Why the model diverged

[`build_shell.section()`](../source/build_shell.py) interpolates a generic
cross-section from a traced outline, using assumed curvature and bulge.
`opening_fields()` combines drawing contours with assumed clipping fields.
The [PicoGK generator](../picogk/src/Program.cs) then offsets those fields into
deep rims and adds fixed-size sill, tunnel and rail volumes. The
[report](../derived/zesad-monocoque.report.json) explicitly records their
hypothetical dimensions.

That construction is useful for exploratory questions about closed sections.
It is not a reconstruction of the central tub shown by the reference product.
The workflow should have rejected it against the requested architecture before
promoting its rendering to the next product milestone. Increasing mesh density,
training Qwen further or renting a larger GPU cannot correct that input error.

## What the existing data can support

The [body-control register and survey](../../interface-measurement-plan.md)
already exist; the owner does not need to supply those documents again. They
contain useful documentary spans and a longitudinal chain. The
[latest scan review](../../model-year-review-20261029/README.md) retains the
original underbody scan, exact registered-array hashes, 18 interface identities
and ten projected XY pairs. It establishes **zero validated XYZ anchors**.

The private scan view inspected here shows an assembled underside. It supports
inspection of visible underbody surfaces; it is not a complete survey of the
interior footwells, tunnel, door apertures or upper cell. Occluded surfaces
must stay unobserved. Do not infer an interior plane from a flat underside, or
fill the missing upper structure by reproducing the current shell assumptions.

Working donor scope remains the owner's Carrera 2 identification. Gearbox and
model year remain unresolved; C4 and 993 interfaces require separate evidence.
The requested approximately 1,200 kg vehicle mass is a programme input, not a
measured shell mass or a complete structural load specification.

## Reconstruction order and acceptance

1. **Map observed structure and missing coverage.** Reuse the immutable scan
   and existing datum ledger. Identify surface patches and separate body,
   suspension and drivetrain observations. Record original triangle IDs,
   transforms, uncertainty and unobserved regions. Preserve the
   [scan reconstruction rules](../../../../docs/architecture/scan-repair-workflow.md).
2. **Establish the central-cell package.** Model floor/footwells, sills, tunnel,
   front wall, rear wall and upper load paths as explicit components. Link each
   controlling dimension to acquired geometry, documentary input or an openly
   labelled design assumption. The assumption label does not grant fitment.
   Missing mating geometry blocks a functional interface; it must not be
   populated with convenient coordinates.
3. **Review geometry locally before solving.** Provide front, rear, side, plan
   and interior views with the exterior body hidden, plus transverse and
   longitudinal cuts. Show the source-to-model comparison in a justified common
   frame, open interfaces and access envelopes. Reject intersecting junctions,
   unexplained closures and an exterior-shell substitute for the central cell.
   Vendor pictures support a qualitative architecture comparison only.
4. **Build the analysis and manufacturing representations from that revision.**
   Define laminate/core, joints, inserts, physical thickness, mould splits and
   access. Check geometry-to-analysis correspondence and numerical convergence
   before interpreting stiffness, stress, buckling or manufacturing results.
   Historical S6 numbers do not transfer to a redesigned tub.
5. **Return to Omniverse with the admitted assembly.** Reuse the established
   renderer and streaming workflow, with a fresh bounded compute session when
   appropriate. Verify the actual cell and its interfaces in the editor. This
   remains separate from structural qualification and road/track approval.

The next deliverable is a traceable central-cell reconstruction and coverage
review. This change supplies the comparison and corrected scope only; it does
not claim that reconstruction has already been completed.
