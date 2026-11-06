# 935 head: current delivery and completion requirements

Review date: 2026-11-04. Reviewed source: `860d360589e9b41dec69b968ea4bbdc017a7f701`.
The objective remains a faithful replica of the scanned head, reproducible
simulation and a qualified functional-metal manufacturing file before design
optimisation. That objective is **not achieved**. CADAM is integrated and tested
for its bounded local coupon role; it does not close the head's release gates.

This review reconciles the [original contract](../935-faithful-replica-20261028/baseline-contract.json),
the [executed study](../935-hypothesis-study-20261029.md), the
[current source-chart CAD](../935-source-shells-20261104/README.md) and the
[CADAM/Qwen runbook](../../architecture/cadam-local-qwen.md).
The [receipt](readiness.json) contains fresh byte checks and coverage denominators.
It is a documentary audit, not a new geometry, solver or manufacturing acceptance.

## Inputs and preserved work

The original 104,598,077-byte OBJ was freshly hashed on the Mac and still matches
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
Its current private location is under the Mac project's
`raw-scans/wolfe-classics-935-cylinder-head/original/` directory. Kali1 responds,
but the old catalogue path under `/home/lolman/imports/mac-obj/` is absent.
Do not reuse that historical path as an available input or silently substitute
a repaired mesh for the original. The frozen historical records are unchanged.

**One original OBJ unit is one millimetre, by direct owner instruction.**
Earlier unknown-scale notes are superseded for digital processing. Scanner
accuracy, independently measured same-specimen dimensions and uncertainty
remain unverified. Another head's catalogue dimensions cannot supply these.

All **61 files / 4,519,570,222 bytes** listed by the private delivery manifest
were rehashed and match. This includes the two study 3MFs, neutral CLI, existing
editable references, reports and source snapshots. It does not revalidate
sibling recovered solver archives or repeat the original geometry/physics tests.
The three newer source-chart STEPs, source-chart FCStd and observed-wall FCStd
also match their respective frozen manifests.

## What each delivered file can support

These are private local artifacts. Their exact hashes are in the receipt and
original manifests; no geometry has been added to Git or sent to a supplier.

| Private artifact | Current purpose | Acceptance limit |
|---|---|---|
| `935-engineering-reference.FCStd` in the study delivery's `editable/` directory | Editable planes, datums and observed reference curves | Partial reference geometry; no complete bare head |
| `935-observed-wall-review.FCStd` in the observed-wall bundle's `deliverables/` | Native review of acquired wall masks and candidate analytic references | Physical identity of passages and interfaces unresolved |
| `935-exact-source-charts.FCStd` and three STEP files in the source-shell bundle's `deliverables/` | 4,787 exact acquired facets, 22 open shells, independently checked native round trip | Zero solids; vertex-only contacts explicitly separated; no new scan coverage |
| `935-head-scan-study-mm.3mf` | Closed fine study envelope, digital export checks passed | Includes attached hardware and inferred closures; not an identical bare head |
| `935-supported-composite-mm.3mf` | 1,202-resource support/base/coupon composite | Intentional overlaps need consumer union; supports and removal unqualified |
| `935-supported-30um.cli` | Fully read-back neutral contours at 30 µm | No hatch, laser exposure or qualified machine profile |

Bundle roots under the private local `PorschePartsArtifacts` directory are
`935-scan-tools-20261029/hypothesis-run-20261029/delivery/`,
`935-observed-wall-cad-20261104/` and `935-source-shells-20261104/`.
This index reuses those immutable files instead of duplicating gigabytes.

The fine study envelope's scan-to-envelope P95 is 0.02477 mm, but the reverse
P95 is 1.4974 mm and maximum is 11.0046 mm. A good one-way fit does not validate
added surfaces. The minimum among 500 thickness probes is 0.0954 mm; sampling
does not establish a global minimum or manufacturability. See the
[study's fidelity assessment](../935-hypothesis-study-20261029.md#fidelity-and-geometry-assumptions).

## Completion ledger

No one of the original twelve input packages is fully closed. This **0/12**
denominator describes complete evidence packages, not percentage of work done.
The existing CAD, exports, code, controls and exploratory fields are real partial
deliverables. The private interface contract accepts **0/8** required interfaces.

| Input package | Existing evidence | Concrete missing closure |
|---|---|---|
| Engine identity | Xtreme head family context | Exact target engine configuration, bore/stroke, compression, fuel, rpm and intended duty |
| Specimen identity | Correspondence supports Xtreme and cast-then-machined route | Reference/revision, selected options, specimen markings and provenance |
| Scale and metrology | Owner-confirmed mm units; exact digital hash | Same-specimen dimensional checks, datums, instrument uncertainty and scan accuracy |
| Interfaces | Observed planes, circles, sections and wall masks | Accepted mating geometry, axes, patterns, tolerances and inspection for all eight interfaces |
| Internal geometry | Acquired surface observations and conditional closures | Bare-head/hardware separation, chamber/port continuity, hidden oil passages, seals and wall evidence |
| Valvetrain | Catalogue ranges kept separate from scan measurements | Exact valves, guides, seats, springs/cam and clearances for this variant |
| Material | Generic aluminium used explicitly for studies | Specimen alloy/condition; justified AM substitute if needed; temperature, orientation and fatigue data |
| Operating loads | Explicit surrogate pressure, thermal and restraint cases | Pressure history, temperatures, preload/contact, valve dynamics, air/oil and port conditions |
| Reference tests | Numerical control problems and exploratory fields | Correlated specimen flow, heat, deformation and engine measurements |
| AM process | Provisional support composite and neutral contours | Accepted machine/powder/recipe, calibrated thermal-mechanical model and build/removal qualification |
| Finished-part inspection | Proposed inspection requirements | Accepted machining plan, metrology, CT/NDT, cleanliness, leak and dimensional results on a manufactured part |
| Replica engine validation | No accepted engine test | Approved validation plan, professional review, instrumented cycles and post-test inspection |

The eight interface IDs are cylinder register/deck, stud pattern, cam-housing
face, low-B flange, high-B flange, valve seats/guides, spark plug, and oil
passages/seals. Their attachments and load paths remain in the private contract.
In particular, three passage candidates are not an accepted four-stud pattern;
the intake/exhaust identity of the two observed flanges remains unresolved.

G0 identity, G1 faithful CAD, G2 reference-function correlation, G3 AM-process
qualification, G4 finished-replica inspection and G5 engine validation remain
unclosed. This review does not enable redesign, manufacturing or installation.

## Software and calculation state

| Chain element | Executed work | Next admissible use |
|---|---|---|
| Local Qwen / CADAM / OpenSCAD | Two synthetic coupon generations; 70 independent checks each; local outbound-denied runtime | Explicitly dimensioned auxiliary proposals, checked against a separately fixed contract; no automatic PicoGK/STEP/CAE bridge |
| PicoGK and existing STEP/FreeCAD | Prior PicoGK full-study candidate rejected; current source references and exact native charts retained | Source-supported reconstruction with acquired-face provenance; no invented internal passage |
| Gmsh | Three positive-volume study meshes; poor boundary conditioning retained | New volume solve only after upstream geometry and mesh-quality admission |
| OpenFOAM | External-envelope air/thermal study; conservation checks pass | Stationarity and spatial convergence still unresolved; no calibrated internal-port CFD or engine CHT |
| CalculiX | Independent cube controls, pressure/conduction and combined exploratory solves | Exact constraints, material laws and full field/stress convergence required; finest pressure case timed out |
| Adamantine | Whole-envelope cooldown and energy checks | Deposition/laser history, calibration and actual process inputs required; cooldown is not full-build validation |

The latest [bounded quad-flip trial](../935-mesh-admission-20261104/BOUNDED_QUADS.md)
kept coordinates and protected faces unchanged and independently bounded the
surface change below 0.01 mm. It reduced low-quality triangles by 19%, below the
predeclared 50% requirement. It is rejected for further volume-mesh admission.
Changing candidate ordering in that same one-pass family cannot reach the gate;
do not launch another identical sweep or a paid solve on this rejected candidate.

The [native Kali receipt](../935-kali-validation-20261104/README.md) records
4,762 passed tests and 410 skips at its stated earlier commit. Full native
`make check` stopped at Docker socket access; that limitation remains.
GitHub's validation step completed successfully for reviewed commit `860d36058`
in [run 41875624622](https://github.com/cluster2600/porscheparts/actions/runs/41875624622).
Repository validation does not accept the physical head.

## Data acquisition and process preparation

The [manufacturer matrix and unsent technical requests](PROCESS_DATA.md)
separate public capability from actual process data. Falcontech/Farsoon remain
the priority qualification enquiry; BLT remains a comparison candidate. No alloy,
machine or supplier is accepted for this head.

The known private three-message correspondence thread was reviewed. It supports
the cast/machined origin but provides no complete interface, internal-geometry,
material or manufacturing data package. A separate recent-mail search was
rate-limited, so this review makes no exhaustive mailbox-coverage claim.
The previously prepared specimen-data request remains unsent and unchanged,
as instructed. A question about access to the physical specimen or existing
drawings/CT/measurements is pending; silence supplies neither data nor approval.

Independent next work can prepare measurement and simulation inputs, preserve
source-supported CAD and qualify a new, explicitly bounded study operation.
Hidden surfaces cannot become a faithful replica through additional compute.
Before new reconstruction, use the verified Mac original or a hash-checked copy
to a fresh private Kali directory; do not restore historical paths by guesswork.

## Budget and release boundary

The original total cap remains USD 35, with USD 30 for compute and USD 5 reserved
for transfer/closure. Earlier study resources were destroyed and their absence
verified in the [closeout receipts](../935-hypothesis-study-20261029/reports/budget-and-closeout.json).
Those reservation ceilings are not final invoices. Exact remaining credit and
attributable final cost are unverified; this review does not reset the allowance.
Before another prepared paid job, reconcile earlier charges, disk/network costs
and the reserve using the approved scoped access.

No new paid resource, solver case, supplier message, scan transfer or fabrication
order was created for this review. The complete-head goal remains active and
unfinished. A qualified machine job, accepted engineering review and physical
inspection/testing remain required before calling the functional metal head
ready to print or released for engine use.
