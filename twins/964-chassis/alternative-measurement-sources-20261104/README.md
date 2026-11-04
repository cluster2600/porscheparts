# Alternative body measurements — 4 November 2026

The owner confirmed that the scanned 964 Carrera 2 is **not available for a
further survey**. Its year and gearbox remain unknown. The acquisition path
therefore needs another reference body or an existing dataset with usable rights.
This changes the source of evidence, not the required interface coverage.

**Result:** a provider's published 964 chassis scan has been located and visually
reviewed. No scan bytes, nominal XYZ coordinates or new functional geometry have
been acquired. Engineering admission remains the
[30 October scalar contract](../interface-exploitation-20261030/contract.json).
The 18 manual identities and 19 span observations are already held; obtaining
another copy of those drawings would not close the remaining gaps.

## First acquisition route: TetraVision's existing 964 scan

TetraVision's [video, published 22 November 2024](https://www.youtube.com/watch?v=9x_SR-ZGiCs),
describes a Porsche 964 chassis scan made for a client. A live browser review
inspected the side view near 0 seconds, the exposed underside near 5 seconds,
and a front structural detail near 10 seconds. The views show a stripped body
with door openings, sill/floor structures and front wheelhouse structure. They
do not establish full interior coverage, hidden sheet layers or metrological
accuracy. No dimensions were taken from video pixels.

The provider's [public announcement](https://www.linkedin.com/posts/jurgenvandonink_3dscanning-opticalscanning-porsche-activity-7302945992708898816-9tyJ)
corroborates the project. Its [official contact page](https://tetravision.be/en/contact/)
lists **info@tetravision.be** and **+32 16 91 04 20** in Belgium.

This is the strongest new **availability enquiry**, not an available licensed
download. The client may own the files. Model year, C2/C4, gearbox, modifications,
coverage, registration checks and reuse rights remain unconfirmed. The
[prepared request](tetravision-request.md) asks for those facts before a purchase
or engineering use. It has **not been sent**.

A cropped browser screenshot is retained privately at
`work/964-acquisition-packet-20261104/tetravision-source-review.jpg`.
Its digest and inspection timestamps are recorded in [the receipt](review.json).
It is the supplier's visualization, not our reconstruction, a measured photograph
or a new Omniverse result. Neither the screenshot nor the video is redistributed
in Git. No model or training licence is inferred from public visibility.

## Other routes screened

| Route | What was actually observed | Decision for this project |
|---|---|---|
| [Celette WebTools](https://app.celette.com/) | Live browser reached login/registration; the public Cameleon manual describes point photographs, assembly state and contact offsets | Seek the exact 964 C2 and 993 nominal sheets and contact definitions through an authorised provider; coverage and values are not yet obtained |
| [3D Dataworld 964 A-surface scan](https://www.3d-dataworld.com/car-scans/complete-surfaces/) | Vendor explicitly excludes wall thickness and mounting geometry | Does not close the structural interface/interior requirement; no purchase proposed |
| [AST 964 RWD coupe cage](https://astrollcages.com/tienda/de/inicio/27778-ArcodeSeguridadPORSCHE9642-doorCoupeRWDMULTIPOINTWELDINV1.html) | Manufacturer's indexed page says laser scanning supported the cage design; full page retrieval failed | Secondary interior-data lead only; no source scan, body coordinates or licence obtained |
| [PistonHeads reference-body offer](https://www.pistonheads.com/gassing/topic.asp?f=233&h=0&t=2060393) | A January 2024 reply offers a stripped 964 rolling body for scanning | Historical owner statement, not current availability; no member contacted or identity copied here |
| [RaceCarScans 964 chassis filter](https://racecarscans.com/files/scan/?rcs_area=chassis-subframe&rcs_car=911-964) | The inspected filter returned no matching files | No acquisition from this route; this is not a claim about the whole site |
| [Tripo page labelled as a 964 chassis scan](https://studio.tripo3d.ai/3d-model/3D-scan-of-a-Porsche-964-chassis-showing-the-detailed-structure-and-de-07533450-3a55-47c1-b295-92209b59fdd6) | Search result describes an image/prompt-generated model | Excluded as measurement evidence; no download or dimensional use |

The existing [30 October research](../body-reference-research-20261030/README.md)
already covers Autorobot, Car-O-Data and the public Celette setup sheets. Generic
database coverage does not prove a particular 964/993 entry exists. This review
is a bounded source search, not exhaustive internet coverage.

## Data package to request

Use the [nominal data request](nominal-data-request.md) for a measuring-system
provider or workshop. The [interface capture CSV](donor-interfaces.csv) contains
36 blank point/side rows, covering the existing 18 manual IDs. It contains no
nominal coordinates, inferred axes or fabricated uncertainty. It is only the
manual subset: seat, restraint, pedal, steering, hinge and service interfaces
still need their own measured definitions.

The Celette [Cameleon manual](https://www.celette.com/wp-content/uploads/2025/10/Cameleon-Webtools-GB.pdf)
explains variant/assembly-state selection (pp. 6–7), contact photographs and
offsets (pp. 10–11), and drawing/report outputs (pp. 14–16). Its sample drawing
is not Porsche data. An assembled bolt-head contact, a hole centre and a bare
body seating face are different references. The
[Eagle manual](https://www.celette.com/wp-content/uploads/2025/10/Eagle-User-Manual-EN.pdf)
is another provider workflow reference, not a 964/993 dimension table.

The privately held Porsche 964 Body manual, PDF page 10 / printed 50-07,
also identifies checking gauges P852 (windshield), P853 (rear window), P854
(rear side windows) and P856 (Targa rear opening). These are tool identities;
no gauge coordinates or dimensions have been acquired. P856 is not evidence
for a coupe opening.

## Acceptance and continuation

1. Confirm lawful availability, exact vehicle configuration and a coverage
   preview before committing to a dataset. A different donor is recorded as a
   different specimen, never relabelled as the current scan.
2. Inspect original data, units, scale checks, registration and surface gaps.
   Identify physical datum contacts and preserve nominal-versus-measured values.
   Reconcile the existing span observations only where variant applicability
   has been established; keep both P14 year families until resolved.
3. Reconstruct the central cell from admitted surfaces and measured interfaces.
   Keep the body tunnel, detachable cover, linkage/service envelope and any C4
   driveline envelope separate. C2 evidence does not automatically qualify C4
   or the 993 rear structure.
4. Then evaluate the applicable laminate, joints, torsion/bending, local loads,
   buckling/fatigue and manufacturing/mould studies, with explicit material and
   process inputs and an independent review/correlation plan.
5. Package that admitted revision and its results into OpenUSD, then execute
   native Omniverse review, captures and video. The historical whole-body render
   remains a rejected design baseline and cannot substitute for this cell.

The complete goal remains open. A scan would resolve only part of the geometry
problem; it would not provide composite allowables, manufacturing validation,
physical correlation or road/circuit approval. No rental, purchase, external
message, new structural solve or manufacturing operation was performed here.
