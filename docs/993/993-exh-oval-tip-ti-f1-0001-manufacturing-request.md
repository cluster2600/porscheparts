# Titanium manufacturing request — 993-EXH-OVAL-TIP-TI-F1-0001 / draft A

Status: draft, not reviewed

> [!CAUTION]
> **Draft. PROPOSED, NOT REVIEWED.** This request must not be sent to a
> supplier, quoted against or used to order anything before a human review is
> recorded in the review table at the end, and before the conditions of
> [ADR 0014](../decisions/0014-exhaust-tip-route-matrix-conditional-titanium.md)
> are met. Today they are not: the deciding temperature is unsourced. Nothing in
> this document is qualified, approved or released, and no supplier quote is
> part of the repository.

Filled from the template
[`catalog/templates/manufacturing-request-titanium.md`](../../catalog/templates/manufacturing-request-titanium.md),
section by section. Every field carries a value with its source, **to be
supplied by the supplier**, **open** with the reason, or **proposed** when the
value is a project proposal. Standards are cited by designation; their tables
are not reproduced.

## Definition

- Request identifier and revision: `REQ-993-EXH-OVAL-TIP-TI-F1-0001`, draft A,
  2026-10-15 (project label).
- Governing decision record:
  [ADR 0014](../decisions/0014-exhaust-tip-route-matrix-conditional-titanium.md),
  which conditions
  [ADR 0007](../decisions/0007-premier-titane-embout-echappement.md).
- STEP file and SHA-256 digest:
  [`parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step`](../../parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step),
  `6dc3da8a65242471d0cd9d65b8b40f44660897b923d207e5b1cf1d1b2bc4f758`, the
  digest recorded by the step-03 geometry report and recomputed on 2026-10-15.
  The STL (`7a2a8e65aa7d0d7771cc49b8fa9aaf116ba6eb4d124b843a8584f9cf85bd265e`)
  is an analysis surface and has no dimensional authority.
- PDF drawing and revision: **open** — no drawing exists. Only the
  120 × 85 mm outlet is published
  ([`SRC-FVD-993-EXHAUST-TIPS-DIMENSIONS`](../../catalog/sources/src-fvd-993-exhaust-tips-dimensions.json),
  level C). The 120 mm length, the 66 mm round outer inlet, the 0.8 mm walls,
  the 2.7 mm annular gap and the eight ties are F0 assumptions
  ([`engineering-screen-ti64.json`](../../parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json)).
  Without a drawing no tolerance can be quoted.
- Units: mm
- Quantity: **open** — owner decision.
- Declared use: none authorized at this revision. The catalogue record allows
  screening only: no manufacturing for fitting and no vehicle installation.
- Safety class: `functional`
  ([record](../../catalog/parts/993-exh-oval-tip-ti-f1-0001.json)). Not
  `non_critical`; the owner's acceptance of that class is pending (ADR 0014).

## Material and process

- Alloy: Ti-6Al-4V Grade 5, **proposed and conditional** on the ADR 0014
  temperature rule. Ti-6242 is not requested: it has no LPBF supply route. Grade
  23 ELI is not requested; a supplier proposing it justifies it
  ([TITANIUM.md](../TITANIUM.md)).
- Requested material standard: ASTM F2924-14(2021), **proposed**
  ([`SRC-ASTM-F2924-14R21`](../../catalog/sources/src-astm-f2924-14r21.json)).
  The supplier states whether it certifies to it, and the class.
- Finished-part specification: ASTM F3302-18, **proposed**
  ([`SRC-ASTM-F3302-18`](../../catalog/sources/src-astm-f3302-18.json)). The
  supplier states which of the two governs the delivered part, and the
  condition.
- Process: LPBF
- Machine model, serial number and qualification status: **to be supplied by
  the supplier**, with IQ/OQ/PQ status per ISO/ASTM TS 52930
  ([`SRC-ISO-ASTM-TS-52930-2021`](../../catalog/sources/src-iso-astm-ts-52930-2021.json)).
  Screening reference only: EOS M 290, nominal 250 × 250 × 325 mm
  ([machine card](../../catalog/manufacturing/machines/eos-m290.json)); in the
  screening orientation the bare part measures 135.0 × 85.0 × 148.1 mm.
- Production site quality system: **to be supplied by the supplier** (ISO/ASTM
  52920, [`SRC-ISO-ASTM-52920-2023`](../../catalog/sources/src-iso-astm-52920-2023.json),
  or the system it holds).
- Qualified parameter set identifier and version: **to be supplied by the
  supplier**. The repository's route card leaves it empty.
- Layer thickness of that parameter set: **to be supplied by the supplier**.
  The screening sliced 4,936 layers at 30 µm, the published EOS Ti64 route
  ([process card](../../catalog/manufacturing/processes/eos-m290-ti64-30um.json)).
- Material data reported per ISO/ASTM 52929
  ([`SRC-ISO-ASTM-52929-2025`](../../catalog/sources/src-iso-astm-52929-2025.json)):
  **to be supplied by the supplier**.

## Powder

- Powder manufacturer, designation and lot number(s): **to be supplied by the
  supplier**.
- Certificate of analysis per lot: required (**proposed**).
- Chemistry, including the interstitials O, N and H: against the chemical
  composition requirements of ASTM F2924 for Grade 5, clause cited by the
  supplier, measured value reported per powder lot and on as-built chemistry
  coupons. The limits are not reproduced here.
- Particle size distribution, flow and density: **to be supplied by the
  supplier**, methods named, characterisation per the ASTM F3049 guide
  ([`SRC-ASTM-F3049-14R21`](../../catalog/sources/src-astm-f3049-14r21.json)).
- Virgin, reused or blended: **to be supplied by the supplier**.
- Maximum reuse count and blend ratio, and the evidence that they are
  respected: **to be supplied by the supplier**. The repository proposes no
  number: no source sets one.
- Sieving, storage and handling: **to be supplied by the supplier**.
- Powder life-cycle management per ISO/ASTM 52928
  ([`SRC-ISO-ASTM-52928-2024`](../../catalog/sources/src-iso-astm-52928-2024.json)):
  **to be supplied by the supplier**.

## Build

- Proposed orientation: **to be supplied by the supplier**, with its
  justification. Screening reference only: `roll_y_25`, chosen by an automated
  rule and not reviewed; 148.1 mm build height, 2 new islands, 1,044 layers
  with unsupported area (0.603 mm² at most), 7.24 cm³ conservative support
  envelope
  ([geometry report](../../twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json)).
- Support-free zones: **proposed** — no support inside the 2.7 mm annular
  channel or on the wetted inner duct, which cannot be reached for removal.
  The supplier confirms or contradicts.
- Machining allowances: **open** — none defined; the stage-04 gate
  `machining_stock_defined` fails. Candidate surface: the inlet slip-fit bore,
  itself an F0 assumption.
- Cavities and powder removal: one 2.7 mm annular channel, 120 mm long, open
  at the inlet. Depowdering is screened only at a 1 mm voxel, which detects no
  trapped volume and cannot conclude. The supplier states the method and the
  evidence it delivers (see non-destructive testing).
- Distortion compensation: **to be supplied by the supplier**. The repository
  has no distortion computation (stage 06 blocked).

## Post-processing

- Stress relief: **to be supplied by the supplier**, with the cycle and
  whether it is done on the plate. Screening reference only: 800 °C, 2 h under
  argon, the EOS coupon heat treatment (process card).
- Heat treatment: delivery condition **to be supplied by the supplier**.
- HIP: to be justified (record: `to_be_determined`). The supplier states
  whether HIP applies and its effect on 0.8 mm walls. The repository has no
  fatigue load case that would justify either choice
  ([SAFETY.md](../../SAFETY.md), section 3).
- Support removal: **to be supplied by the supplier**.
- Shot peening or polishing: **open** — the tip is visible and its finish is
  not defined. EOS reference: Ra 5 to 9 µm after shot peening (process card).
- Anti-galling protection: no thread in the design. The slip-fit and clamp
  interface is undefined: **open**.
- Planned galvanic isolation: **open** — titanium/stainless couple at the
  outlet mounting, recorded as "to be addressed".

## Machining

| Surface | Operation | Tolerance | Roughness |
|---|---|---|---|
| inlet slip-fit bore (assumed interface) | open | open — no drawing | open |
| outlet lip | none planned | — | open |

## Coupon plan

Coupons are built in the same job as the part, from the same powder lot, and
receive the same heat treatment and HIP. Orientations and locations
**proposed** after the plan the repository wrote for another LPBF part
([F49](../../twins/reference-917-engine/material-lpbf-qualification-f49.json):
X, Y, Z, 45°; plate centre, two near-edge positions, next to the part; three
replicates). Three replicates is a screening count, not a statistical basis.

| Coupon | Count | Orientation | Location on the plate | Condition | Test standard | Acceptance |
|---|---:|---|---|---|---|---|
| tensile, room temperature | 3 per orientation (proposed) | X / Y / Z / 45° | centre, near edges, next to the part | as delivered | ASTM E8/E8M ([`SRC-ASTM-E8-E8M-25`](../../catalog/sources/src-astm-e8-e8m-25.json)) | minimums of the governing specification for the delivered condition |
| tensile, service temperature | open | open | open | as delivered | ASTM E21 ([`SRC-ASTM-E21-20`](../../catalog/sources/src-astm-e21-20.json)) | open — only once a sourced T_max exists |
| chemistry including O, N, H | 1 per build (proposed) | — | next to the part | as built | to be supplied by the supplier | limits of ASTM F2924 for Grade 5 |
| density or porosity | to be supplied | to be supplied | to be supplied | as delivered | to be supplied by the supplier | open |
| microstructure | to be supplied | to be supplied | to be supplied | as delivered | per the governing specification | per the governing specification |
| fatigue | open | open | open | open | open | open — no load case exists |

## Inspection

- Dimensional report: outlet envelope, overall length and a wall-thickness map
  of the 0.8 mm walls; method **to be supplied by the supplier** (CT wall
  thickness proposed); tolerances **open** (no drawing). Screening reference,
  not a certified wall map: local thickness p01 0.600 mm, minimum 0.460 mm.
- Dye penetrant testing: accessible external surfaces, see below.
- CT scan: **proposed** for the whole part, see below.
- Density: **to be supplied by the supplier**.
- Mechanical coupons: per the coupon plan.
- Material certificate: per the governing specification, per powder lot.
- Nonconformance report: required for any deviation; an open report blocks
  acceptance.

## Non-destructive testing

| Method | Standard | Zones | Detectability (voxel size, reference defect, POD) | Acceptance limit |
|---|---|---|---|---|
| computed tomography | ISO 15708 series ([`SRC-ISO-15708-CT-2025`](../../catalog/sources/src-iso-15708-ct-2025.json)) | whole part; annular channel; ties; inner duct | to be supplied by the supplier and agreed before the build | proposed: no residual powder in the channel and no through-wall indication; defect size limit open |
| liquid penetrant | ASTM E1417/E1417M ([`SRC-ASTM-E1417-E1417M-21E1`](../../catalog/sources/src-astm-e1417-e1417m-21e1.json)) | external surfaces and inlet | — | open |
| visual or borescope | to be named by the supplier | annular channel from the inlet | to be supplied | proposed: no loose powder visible |
| leak or pressure | not proposed | — | — | no leak requirement is defined; the 30 kPa gauge pressure is synthetic |

## Traceability

- Build (job) identifier and build-file SHA-256: **to be supplied by the
  supplier**; required (**proposed**).
- Machine serial number: **to be supplied by the supplier**.
- Parameter set identifier and version: **to be supplied by the supplier**.
- Powder lot(s) and reuse count at build time: **to be supplied by the
  supplier**.
- Build plate identifier and position of the part and of each coupon: **to be
  supplied by the supplier**.
- Part serial number, marking method and location: **open** — the marking
  location must avoid the visible outlet; the owner decides.
- Process monitoring data recorded per ISO/ASTM 52953
  ([`SRC-ISO-ASTM-52953-2025`](../../catalog/sources/src-iso-astm-52953-2025.json)),
  and delivered: **to be supplied by the supplier**.
- Heat-treatment and HIP furnace charts: required (**proposed**).
- Operator, dates and certificate of conformity: required (**proposed**).

## Acceptance

The part cannot be installed before the reports are reviewed, the revision is
identified and the nonconformances are closed. No part from this request may
be installed on a vehicle at all at this revision.

**Prerequisites before the request may be sent** (from ADR 0014, not supplier
criteria): a sourced T_max at or under 350 °C, inner duct included; the owner's
written acceptance of the `functional` class; a defined galvanic isolation;
a defined inlet interface and clamp; a drawing with tolerances.

Acceptance criteria — **PROPOSED, NOT REVIEWED**:

| ID | Criterion | Requirement | Evidence expected | Status |
|---|---|---|---|---|
| AC-01 | identity | delivered part made from the STEP with SHA-256 `6dc3da8a…c4f758` and the reviewed drawing revision | build-file SHA-256, drawing revision on the certificate | proposed |
| AC-02 | material | chemistry including O, N, H within the governing specification, per powder lot and on as-built coupons | certificate of analysis, coupon chemistry report | proposed |
| AC-03 | process | machine qualified (IQ/OQ/PQ), parameter set identified and unchanged from the one quoted | qualification record, build record | proposed |
| AC-04 | powder | lot, reuse count and blend within the supplier's declared limits | powder records per ISO/ASTM 52928 | proposed |
| AC-05 | tensile coupons | room-temperature results at or above the governing specification's minimums for the delivered condition, every orientation | ASTM E8/E8M report | proposed |
| AC-06 | heat treatment and HIP | cycle as declared; HIP decision justified in writing | furnace charts, justification | proposed |
| AC-07 | depowdering | no residual powder in the annular channel | CT per ISO 15708 at the agreed detectability, borescope record | proposed |
| AC-08 | wall integrity | no through-wall indication; minimum local wall not below the supplier's declared minimum for the parameter set | CT wall-thickness map | proposed |
| AC-09 | dimensions | outlet envelope and length within drawing tolerances | dimensional report | open — no drawing |
| AC-10 | surface | penetrant indications within the agreed limit; finish as specified | ASTM E1417/E1417M report | open — limits and finish undefined |
| AC-11 | traceability | every traceability field filled; monitoring data delivered | build package | proposed |
| AC-12 | nonconformances | none open | nonconformance log | proposed |

The review table is filled only by named human reviewers, and only in the same
change that replaces the "Status: draft, not reviewed" line at the top of this
request.

| Reviewer | Role | Date | Decision |
|---|---|---|---|
| | | | |
| | | | |

## Note on the generated quote requests

The route-card generator also wrote two quote requests, in French, under
[`twins/993-exhaust-tip-ti-f0/evidence/`](../../twins/993-exhaust-tip-ti-f0/evidence/route-ti64/993-exh-oval-tip-ti-f1-0001-supplier-rfq.md).
They are frozen evidence and are not corrected in place. They contain
boilerplate that does not apply to this part: a dimensional check of "four
dimensions and the axial profile" and a "costed comparison with CNC turning",
both inherited from the trim ring, coupon values labelled "as-manufactured"
although the Ti64 coupons are heat treated, and, in the Ti-6242 variant,
"Rp0,2 vertical 0 MPa" for a value that is simply not published. Once
reviewed, this request supersedes them for any supplier-facing use.
