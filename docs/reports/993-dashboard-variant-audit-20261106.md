# Porsche 993 complete dashboard: variant identity audit

This report is a documentary identity gate for a proposed left-hand-drive M564 dashboard assembly. It does not establish measured geometry, fit, occupant safety, or manufacturing approval.

## Sources and rights

| Source | Reading used here | Rights and limit |
| --- | --- | --- |
| [Porsche PET KAT 017, English, 24 July 2017](https://files.porsche.com/f/332100/cfbfd366e3/kat017-e-911-98-katalog.pdf) | PDF reader pages 3, 16, 19, 500-513; SHA-256 `b67cf3586f9a92bee5ccc8e84462515231c84ddd23c610e4a2e739fedb1166aa`, retrieved 6 November 2026 | Porsche AG copyright, reference only. No PDF page or artwork is imported. The tables below paraphrase part identities and conditions. |
| [PorscheFanatics dashboard-trim case study](https://porschefanatics.com/projects/parts/993-int-dashboard-trim-0001/) | Earlier catalogue interpretation and concept images, read 6 November 2026 | Secondary project source. Its imported revision predates the current GitHub work; its images are not dimensional evidence or a reuse licence. |
| [Current dashboard-trim catalogue record](../../catalog/parts/993-int-dashboard-trim-0001.json) and [measurement plan](../../parts/993-int-dashboard-trim-0001/evidence/measurement-plan.md) | Existing project scope and D01-D14 intake requirements | The record is the repository source of truth; its earlier part-number grouping is refined below. The historical measurement plan is preserved, not edited in place. |
| [FVD carbon/Kevlar race dashboard listing](https://www.fvd.net/en-us/shop/race-dashboard-964-993-carbon-fiber-kevlar-left-hand-drive-without-a-c-vent-fvd55522005~p238149) | Seller offers a left-hand-drive racing dashboard for a broad 964/993 range, without a centre A/C vent | Vendor claim only. Its fit to the exact M564 dashboard, knee-strip anchors and restraint configuration is unverified. Vendor photographs are not reused. |

The [Porsche legal notice](https://www.porsche.com/international/legal/legal-notice/) governs the PET artwork. Page numbers in this report are PDF reader pages of the official KAT 017 file above, not the printed illustration sheet numbers. The original source remains with Porsche.

## Variant and part-number matrix

KAT 017 defines M561 as a driver airbag, M562 as driver and passenger airbags, and M564 as no airbag (page 19). It defines RS M002 and Clubsport M003 on page 16. The catalogue-wide 1994-1998 model-life heading does **not** prove that every configuration below was offered in every year. The RS model summary records 1995-1996 (page 3).

| Candidate vehicle configuration | Passenger-side state | Main trim, PET position 1 | Knee protection, PET position | Decision for the proposed M564 LHD assembly |
| --- | --- | --- | --- | --- |
| M564, left-hand drive, non-RS | No airbag by option definition; physical vehicle uninspected | **Unknown.** No non-RS M564 position-1 mapping was found in the inspected 809 plates. | **Unknown.** No exact non-RS M564 strip mapping was found. | Keep both identities `null`. |
| M561, left-hand drive, non-RS | Driver airbag only by option definition; physical vehicle uninspected | **Unknown.** No non-RS M561 position-1 mapping was found. | **Unknown.** No exact non-RS M561 strip mapping was found. | Separate variant; do not borrow M562 or RS rows. |
| M562, left-hand drive | Passenger airbag by option definition | 809-00, page 501: `993 552 055 00` leatherette or `993 552 055 01` leather, marked `/LL`. | 809-01, page 505: position 1 complete leatherette strip `964 552 053 00` `/LL`; other material/construction rows remain separate. | Excluded from the no-passenger-airbag concept. The plate title identifies the airbag-equipped assembly; the position-1 row itself does not print M562. |
| RS M002, left-hand drive | 809-02 explicitly without passenger airbag | 809-02, page 511: `993 552 055 00` `/LL` at position 1. | 809-02, pages 512-513: left strip `911 552 069 00` at position 30; right strip `911 552 070 00` at position 37. | A distinct RS assembly, not evidence of non-RS M564 fit. |
| RS M003, left-hand drive | 809-02 explicitly without passenger airbag | 809-02, page 511: `993 552 055 70` `/LL` at position 1. | 809-02, pages 512-513: left strip `964 552 077 70` at position 30; right strip `964 552 078 70` at position 37. | A distinct Clubsport assembly, not evidence of non-RS M564 fit. |

The corresponding right-hand-drive position-1 trim numbers are `993 552 056 00`, `056 01` and `056 70`. The 809-01 complete leatherette knee-strip row is `993 552 054 00` `/RL`. On 809-02, the M002 right-hand-drive knee strips are `911 552 069 01` and `070 01`; the M003 strips are `964 552 077 71` and `078 71`. These are catalogue identities, not a measured interface set. No inspected row states a supersession among `/00`, `/01` and `/70`: `/01` is a leather material row on 809-00, and `/70` identifies the M003 row on 809-02.

**Key conflict:** `993 552 055 00` and `056 00` appear at position 1 on both the passenger-airbag 809-00 plate and the RS no-passenger-airbag 809-02 plate. A number alone cannot classify the restraint configuration. Nor do these plates prove whether a deployment flap is integral to the position-1 trim: 809-00 draws the passenger airbag at position 11 and neighbouring lids at positions 13 and 14 as separate items. A real specimen and its complete assembly must be inspected before making that claim.

## Other dashboard positions and the limits of the drawings

- 809-00 page 502 lists a centre nozzle at position 17 (`964 572 051 00` `/LL` or `052 00` `/RL`) and side vents at position 21 (`964 572 261/262 00` for left-hand drive; `261/262 01` for right-hand drive). 809-02 pages 511-512 list a defroster vent at position 5 and a centre nozzle at position 16. Shared accessory numbers do not resolve the main trim or its variant.
- The airbag-equipped 809-00 assembly refers to a separate passenger airbag at position 11; PET plate 403-06 page 263 identifies the left- and right-hand-drive units. No restraint component is generated for the M564 study.
- The instrument-hood contour is visible on the position-1 trim illustration, while the gauge surround is separately drawn (809-00 position 25; 809-02 position 14). This is an unscaled exploded view, not proof that a separately modelled hood has an OEM part number or independent attachment.
- The [trim catalogue record](../../catalog/parts/993-int-dashboard-trim-0001.json) identifies body-shell panel `993 502 027 02` as distinct from visible trim. This report does not establish its exact host datums or mounting geometry.

The PET gives positions and some fastener descriptions or quantities. It does **not** provide hole centres, axes, mating faces, clearances, tolerances, installation deformation or a vehicle coordinate frame. The [PorscheFanatics case study](https://porschefanatics.com/projects/parts/993-int-dashboard-trim-0001/) likewise labels its CAD and images as concepts and calls for fitted and removed scanning. The FVD listing establishes that a carbon/Kevlar racing dashboard is offered; it does not establish that the exact M564 trim, original vents or knee protection are retained. The earlier blanket claim that no carbon dashboard exists is therefore too broad.

## Independent interface gate for the complete assembly

| Interface or boundary | Attachments and load path that must be established | Evidence still required |
| --- | --- | --- |
| Body-shell panel to vehicle | Structural host and its original body attachment path | Exact panel variant, host datums, mounting pattern, axes, mating faces, tolerances and structural review. |
| Visible trim to body-shell panel | Every clip nut, self-tapping screw and supporting face | Same-specimen fitted and removed scans, reverse-side attachment inventory, measured centres/axes, section and fastener data with uncertainty. |
| Instrument contour, cluster and gauges | Original cluster retention and wiring/service route | Exact variant, opening and bezel envelope, mounting and axis data, clearances and withheld independent checks. |
| Centre/side vents and defrost ducts | Retainers, seals, duct supports and airflow path | Apertures and duct interfaces measured on both host and component; no transfer from the F0 display geometry. |
| Glovebox, console, HVAC/radio and switches | Hinges, latches, controls, wiring and service access | Exact component variants, motion envelopes, mating faces, attachment points, tolerances and electrical clearance. |
| Original knee protection | Occupant-impact load path from retained strip and anchors into the body | Exact M564 strip identity, both original anchor patterns, substrate, impact requirement and independent professional safety review. |
| Steering and restraint boundaries | Original steering and airbag systems remain outside this redesign | Redacted option label, direct passenger-side reverse inspection, steering clearance and separate restraint review. |
| Windshield base and pillars | Installed gaps, thermal deformation and visibility | Body datums, repeated fitted/removed shape comparison, UV/heat and windshield reflection criteria. |

All physical interface coordinates, transforms and acceptance tolerances remain **unknown**. An assumed PicoGK scene, a watertight mesh, a supplier envelope or a PET drawing cannot close this gate. The material and construction of any occupant-facing replacement also need impact, fragment, fire, UV, glare and process-specific assessment before vehicle use.

## Same-specimen evidence intake and decision

The [project charter](../PROJECT_CHARTER.md) rules out owner-side purchase, dismantling, measurement, printing, fitting and physical testing under the current decision. A lawful outside contributor or a separately recorded charter change is required. The intake must assign an anonymous specimen ID shared by every file; retain a redacted option-label image and an independent passenger-side reverse inspection; identify model year, handedness and exact components; capture licensed fitted and removed scans with scale bars; measure D01-D14 and each *host* interface independently with calibration, repeats and uncertainty; and retain source hashes and publication rights without a VIN, personal data or proprietary manual in Git. An independent reviewer must check identity and the withheld interface readings before any functional CAD is accepted.

**Current verdict:** the proposed full dashboard remains an F0 reference scene. The target M564 left-hand-drive trim and knee-strip numbers are unresolved, the physical specimen is absent, and no measured attachment or load path has been admitted. Keep the [catalogue part](../../catalog/parts/993-int-dashboard-trim-0001.json) at `concept`; do not promote the F0 visual positions to measured assembly coordinates. The next documentary work is the per-interface contract in [issue #567](https://github.com/cluster2600/porscheparts/issues/567), followed by lawful same-specimen evidence under [issue #568](https://github.com/cluster2600/porscheparts/issues/568).
