# Titanium manufacturing request — PART_ID / REVISION

Every field is answered by a value, by "to be supplied by the supplier", or by
"open" with the reason. A blank field is a defect of the request, not an
answer. Standards are cited by designation and source record only: their
tables (chemistry, interstitial limits, tensile minimums) are never copied
into the repository. The supplier works from a controlled copy and names the
clause, class and condition it certifies against.

## Definition

- Request identifier and revision:
- Governing decision record:
- STEP file and SHA-256 digest:
- PDF drawing and revision:
- Units: mm
- Quantity:
- Declared use:
- Safety class:

## Material and process

- Alloy: Ti-6Al-4V Grade 5 / other, to be justified
- Requested material standard: e.g. ASTM F2924 for PBF Ti-6Al-4V
  ([`SRC-ASTM-F2924-14R21`](../sources/src-astm-f2924-14r21.json)), ASTM F3001
  for Grade 23 ELI when justified
  ([`SRC-ASTM-F3001-14R21`](../sources/src-astm-f3001-14r21.json))
- Finished-part specification: e.g. ASTM F3302
  ([`SRC-ASTM-F3302-18`](../sources/src-astm-f3302-18.json)); class and
  condition to be stated
- Process: LPBF
- Machine model, serial number and qualification status: IQ/OQ/PQ per
  ISO/ASTM TS 52930
  ([`SRC-ISO-ASTM-TS-52930-2021`](../sources/src-iso-astm-ts-52930-2021.json))
- Production site quality system: e.g. ISO/ASTM 52920
  ([`SRC-ISO-ASTM-52920-2023`](../sources/src-iso-astm-52920-2023.json))
- Qualified parameter set identifier and version:
- Layer thickness of that parameter set:
- Material data reported per ISO/ASTM 52929
  ([`SRC-ISO-ASTM-52929-2025`](../sources/src-iso-astm-52929-2025.json)): yes / no

## Powder

- Powder manufacturer, designation and lot number(s):
- Certificate of analysis per lot: yes / no
- Chemistry, including the interstitials O, N and H: against the chemical
  composition requirements of the governing specification above, clause cited,
  measured value reported per lot and on as-built coupons; limits not copied here
- Particle size distribution, flow and density: method named; characterisation
  per the ASTM F3049 guide
  ([`SRC-ASTM-F3049-14R21`](../sources/src-astm-f3049-14r21.json))
- Virgin, reused or blended:
- Maximum reuse count and blend ratio, and the evidence that they are respected:
- Sieving, storage and handling:
- Powder life-cycle management per ISO/ASTM 52928
  ([`SRC-ISO-ASTM-52928-2024`](../sources/src-iso-astm-52928-2024.json)): yes / no

## Build

- Proposed orientation:
- Support-free zones:
- Machining allowances:
- Cavities and powder removal:
- Distortion compensation:

## Post-processing

- Stress relief:
- Heat treatment:
- HIP: required / not required / to be justified
- Support removal:
- Shot peening or polishing:
- Anti-galling protection:
- Planned galvanic isolation:

## Machining

| Surface | Operation | Tolerance | Roughness |
|---|---|---|---|
| | | | |

## Coupon plan

Coupons are built in the same job as the part, from the same powder lot, and
receive the same heat treatment and HIP as the part.

| Coupon | Count | Orientation | Location on the plate | Condition | Test standard | Acceptance |
|---|---:|---|---|---|---|---|
| tensile, room temperature | | X / Y / Z / 45° | | | ASTM E8/E8M ([`SRC-ASTM-E8-E8M-25`](../sources/src-astm-e8-e8m-25.json)) | minimums of the governing specification for the delivered condition |
| tensile, service temperature (if required) | | | | | ASTM E21 ([`SRC-ASTM-E21-20`](../sources/src-astm-e21-20.json)) | |
| chemistry including O, N, H | | — | | as built | method named by the supplier | limits of the governing specification |
| density or porosity | | | | | method named by the supplier | |
| microstructure | | | | | per the governing specification | |
| fatigue (if required) | | | | | | |

## Inspection

- Dimensional report:
- Dye penetrant testing:
- CT scan:
- Density:
- Mechanical coupons:
- Material certificate:
- Nonconformance report:

## Non-destructive testing

Each method is fixed with its standard and its acceptance limit before the
build, not after the result.

| Method | Standard | Zones | Detectability (voxel size, reference defect, POD) | Acceptance limit |
|---|---|---|---|---|
| computed tomography | ISO 15708 series ([`SRC-ISO-15708-CT-2025`](../sources/src-iso-15708-ct-2025.json)) | | | |
| liquid penetrant | ASTM E1417/E1417M ([`SRC-ASTM-E1417-E1417M-21E1`](../sources/src-astm-e1417-e1417m-21e1.json)) | | — | |
| visual or borescope | | | | |
| leak or pressure (if required) | | | | |

## Traceability

- Build (job) identifier and build-file SHA-256:
- Machine serial number:
- Parameter set identifier and version:
- Powder lot(s) and reuse count at build time:
- Build plate identifier and position of the part and of each coupon:
- Part serial number, marking method and location:
- Process monitoring data recorded per ISO/ASTM 52953
  ([`SRC-ISO-ASTM-52953-2025`](../sources/src-iso-astm-52953-2025.json)), and
  delivered: yes / no
- Heat-treatment and HIP furnace charts:
- Operator, dates and certificate of conformity:

## Acceptance

The part cannot be installed before the reports are reviewed, the revision is
identified and the nonconformances are closed.

| ID | Criterion | Requirement | Evidence expected | Status |
|---|---|---|---|---|
| AC-01 | | | | proposed |

| Reviewer | Role | Date | Decision |
|---|---|---|---|
| | | | |
