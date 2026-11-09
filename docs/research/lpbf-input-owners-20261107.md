# LPBF inputs and responsibility matrix for five F0/F1 parts

Refs #479. Snapshot: `5efface17959068eee9de2bd80e5a876b4bc8c26`,
7 November 2026. This is an intake and responsibility plan, not a process
qualification or an instruction to manufacture.

The [AM policy](../../catalog/manufacturing/am-validation-policy.json) remains
authoritative for recorded stage states. All five stage 04 gates are
`blocked_missing_input`. Existing screening cards are retained without
rewriting their evidence. The [pipeline](../AM_VALIDATION_PIPELINE.md) defines
the acceptance gates; the [charter](../PROJECT_CHARTER.md) permits lawful
external contributions but no owner-side purchase, measurement or test.

## Responsibility and acceptance

These are **required roles, not appointed people or supplier commitments**.
Every external assignee is currently unassigned. The repository owner must
identify a willing provider and an independent reviewer before a gate can
close. A manufacturer named in a source is not an engaged supplier.

| Role | Required responsibility |
|---|---|
| Process provider | Exact machine/parameter revision, powder supplier and lot, certificate, reuse/sieving/blending history, gas/oxygen controls, build records and rights to use the data |
| DfAM engineer | Part revision, orientation, supports, plate, powder escape, heat treatment, removal sequence, machining stock and surface state |
| Materials/calibration laboratory | Traceable, orientation- and temperature-dependent material data, coupons, uncertainty and independent holdout observations |
| Simulation operator | Bound sources/runtime, convergence, balances and reproducible results; cannot approve their own assumptions |
| Specimen contributor | Lawful same-specimen interface/load/operating evidence under the capture protocol |
| Independent engineering reviewer | Accept input applicability and numerical criteria before execution; review correlation and sign any bounded release |
| Repository maintainer | Preserve provenance, hashes, failures and status; coordinate intake without assigning measurements to the owner |

For every part below, stages 04–11 require the following acceptance evidence.
Numeric limits must be set by the responsible reviewer for the exact route;
this matrix invents none.

| Stage | Required acceptance evidence | Responsible roles |
|---|---|---|
| 04 | One consistent alloy/powder/machine/parameter/orientation/treatment route, lot traceability, hot constitutive data and part allowables | Process provider, DfAM engineer, materials laboratory; independent reviewer |
| 05 | Exact laser/hatch/contour/time schedule, optical and solid/liquid thermal properties; space/time convergence and same-route melt-pool coupon correlation | Process provider, laboratory, simulation operator; independent reviewer |
| 06 | Layer activation, plate/support geometry, calibrated plasticity/thermal laws, treatment/release sequence; converged distortion and independent comparison | DfAM engineer, laboratory, simulation operator; independent reviewer |
| 07 | Deformed build, recoater clearance/compliance, supplier supports, removal access and sequence; checked collision/removal margins | Process provider and DfAM engineer; independent reviewer |
| 08 | Exact-revision USD, sourced properties, full profile validation and inspected OVRTX render; retain isolated-asset scope | Simulation operator; independent reviewer |
| 09 | Same-specimen interfaces, tolerances, contacts, loads, motion and failure cases; independently accepted functional margins | Specimen contributor and simulation operator; independent reviewer |
| 10 | Approved external coupon/first-article plan, calibrated inspection/CT/NDT/metrology and functional/fatigue correlation, with uncertainty | Laboratory and specimen contributor; independent reviewer |
| 11 | Signed review naming the precise part/process revision, intended use, evidence and limits | Independent engineering reviewer; repository maintainer records the decision |

## Exact variants and route boundaries

| Key | Part record | Candidate route and upstream blocker |
|---|---|---|
| Hook | [993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001](../../catalog/parts/993-elec-headlamp-spring-hook-f0-0001.json) | EOS M 290 / AlSi10Mg / 30 µm screening; all F0 interfaces are unmeasured; functional lamp retention is unauthorized |
| Lever | [993-INT-DOOR-OPENER-LEVER-F0-0001](../../catalog/parts/993-int-door-opener-lever-f0-0001.json) | EOS M 290 / AlSi10Mg / 30 µm screening; commercial envelope is not a measured pivot/linkage; egress use is unauthorized |
| Tip | [993-EXH-OVAL-TIP-IN625-F0-0001](../../catalog/parts/993-exh-oval-tip-in625-f0-0001.json) | EOS M 290 / IN625 / 40 µm candidate; process remains undecided and only the outlet envelope is published |
| Piston | [993-ENG-PISTON-CP1-GALLERY-F0-0001](../../catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json) | CP1 / Velo3D Sapphire / 50 µm screening; synthetic geometry, rejected mechanical/manifold candidates, prohibited pending engineering |
| Ring | [993-INT-SWITCH-TRIM-RING-F1-0001](../../catalog/parts/993-int-switch-trim-ring-f1-0001.json) | EOS M 290 / AlSi10Mg / 30 µm is an alternative screening route; preferred route remains turned 6063 T6, with profile/tolerances unmeasured |

Hook, lever and tip are functional concepts, not noncritical releases. Only the
ring is classified noncritical. The piston and head routes must not inherit a
small-part screening approval; the head is outside these five rows. Titanium
qualification remains the separate #6 dossier.

## Part-specific stage 04–11 inputs

Each row inherits the responsible roles and acceptance rule above. All missing
inputs remain outstanding; the owner of their acquisition is unassigned.
Stages marked screened or passed below retain only their existing evidence
scope. Stages 10 are not started.

| Part | Stage | Exact missing input or retained evidence boundary |
|---|---|---|
| Hook | 04 | Powder lot/reuse/certificate; reviewed arm orientation, heat treatment, machining stock, hot material card and part allowables |
| Hook | 05 | Same-route powder optics/thermal data, laser schedule and correlated arm-orientation coupons |
| Hook | 06 | Actual arm/root supports and plate, activation/treatment history, calibrated distortion; synthetic service CalculiX is insufficient |
| Hook | 07 | Deformed arm/root clearance to recoater, blade compliance and access to remove supports outside the cavity |
| Hook | 08 | Existing minimal asset/rigid checks are screening; full SimReady profile and exact-revision OVRTX render remain missing |
| Hook | 09 | Stub/socket, bond line, adhesive/preparation and hot shear/peel allowables; spring force/stroke/contact; lamp temperature, vibration and beam-position tolerances |
| Hook | 10 | Independent root CT/NDT and dimensions, bond qualification, thermal/vibration/retention and fatigue results |
| Hook | 11 | Signed revision-specific review of lamp retention and bonding evidence; no fitting permission follows from this plan |
| Lever | 04 | Powder lot/reuse/certificate; reviewed lever orientation, heat treatment, pivot machining/coating stock, hot card and allowables |
| Lever | 05 | Same-route powder optics/thermal data, laser schedule and critical-orientation coupons |
| Lever | 06 | Clevis/pocket supports, plate, activation and treatment, calibrated distortion; six synthetic service cases establish no build history |
| Lever | 07 | Deformed clevis/pocket clearance to recoater and accessible support-removal sequence |
| Lever | 08 | Minimal USD/rigid screening exists; Content Agents preflight, full profile and OVRTX remain incomplete |
| Lever | 09 | Mount/pivot/bushing/fastener datums and preload; linkage, latch force, travel/stops; hand/trim clearance, misuse and emergency egress cases |
| Lever | 10 | Independent dimensional/CT/penetrant checks, static/cyclic, corrosion, aging, temperature and egress correlation |
| Lever | 11 | Signed review for the exact door-release assembly and intended use |
| Tip | 04 | Exact IN625 coupon-property block is absent, so route-card generation fails closed; also need powder lot/reuse/certificate, hot card, treatment, machining and orientation/support review |
| Tip | 05 | Same IN625/M 290 route laser schedule, powder properties and correlated melt-pool coupons; no generic IN625 substitution |
| Tip | 06 | Temperature-dependent constitutive law, inherent-strain calibration, double-wall supports/plate and cut-off distortion |
| Tip | 07 | Deformed double wall, recoater clearance/compliance and supplier support geometry/removal access |
| Tip | 08 | Existing isolated-prop SimReady stage is recorded passed; it supplies no assembly or thermal acceptance |
| Tip | 09 | Inlet/slip fit/clamp/sealing datums, tolerances, exhaust pulses/temperature/flow, bumper limits, motion and vibration spectrum; preserve unresolved CFD convergence |
| Tip | 10 | Connection/ovality metrology, double-wall CT/NDT, leak, thermal-cycle, vibration and rear-valance temperature correlation |
| Tip | 11 | Signed exact-route review; no manufacturing for fitting or installation |
| Piston | 04 | Exact Sapphire 50 µm machine settings, CP1 lot/reuse/certificate and complete hot card; published 400 °C/4 h treatment requires part-specific qualification |
| Piston | 05 | Calibrated CP1 Sapphire powder/laser/melt-pool data; neither AlSi10Mg nor EOS CP1 60 µm is transferable |
| Piston | 06 | Hot CP1 plasticity and orientation/support calibration, crown/gallery/boss/ring-groove distortion and treatment/closure history |
| Piston | 07 | Predicted deformation, actual recoater clearance/stiffness, supplier supports and gallery depowdering/removal access |
| Piston | 08 | Existing isolated-prop SimReady stage is recorded passed; engine function remains untested |
| Piston | 09 | All five twin interfaces: cylinder clearance, ring/groove stack, pin/boss/rod, crown/chamber/valve motion and oil-jet/gallery map, with hot loads and tolerances |
| Piston | 10 | Approved external CT before/after machining and port closure, metrology, proof/thermal-cycle/full-scale fatigue and engine correlation; historical precedent is not this piston |
| Piston | 11 | Professional review and approved validation plan remain mandatory; no manufacture, installation or engine start |
| Ring | 04 | LPBF alternative needs powder lot/reuse/certificate, DfAM review, hot card, treatment, machining stock and allowables; no switch from the preferred CNC route is selected |
| Ring | 05 | Exact alternative-route powder optics/thermal data, laser schedule and correlated coupons; no part-specific stage-05 evidence is recorded |
| Ring | 06 | Orientation/support/plate/treatment model and calibrated distortion for the thin ring; no part-specific stage-06 evidence is recorded |
| Ring | 07 | Distortion field, recoater clearance and supplier supports/removal access remain absent |
| Ring | 08 | No part-specific stage-08 override/evidence is recorded in the AM policy; do not borrow the dashboard switch blank's twin |
| Ring | 09 | Same-specimen inner profile, OEM opening, outer fit, axial contact, tolerances and finish/coating growth; no part-specific stage-09 override is recorded |
| Ring | 10 | Lawful external profile/diameter/finish measurements and fit correlation for the selected route; no part-specific stage-10 evidence is recorded |
| Ring | 11 | Independent revision-specific review, including whether LPBF is justified against turning; no part-specific stage-11 evidence is recorded |

The four registered functional twins enumerate the interface requirements:
[hook](../../catalog/twins/twin-993-headlamp-spring-hook-alsi10mg-f0.json),
[lever](../../catalog/twins/twin-993-door-opener-lever-alsi10mg-f0.json),
[tip](../../catalog/twins/twin-993-oval-exhaust-tip-in625-f0.json), and
[piston](../../catalog/twins/twin-993-m64-60-piston-gallery-f0.json).
The ring's catalogue record and route evidence remain its sources; a similarly
named dashboard switch blank is a different part.

## Stage 04 card already available

The [hook's retained process-route card](../../twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/route-f0/993-elec-headlamp-spring-hook-f0-0001-process-route-card.json)
binds published EOS M 290 / AlSi10Mg_FlexM291 2.01 / 30 µm inputs to the
screened hook. It records five consistency checks passed and six gates closed:
orientation review, hot constitutive card, heat treatment, machining stock,
part allowables and powder traceability. Its classification explicitly says
it is **not a qualified process route**, and `metal_print_authorized` is false.

This existing card satisfies the existence of a source-backed screening
artifact; it does not satisfy stage 04 acceptance. Reuse it and its
[unsent supplier intake draft](../../twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/route-f0/993-elec-headlamp-spring-hook-f0-0001-supplier-rfq.md)
when a provider is appointed. Do not regenerate pinned evidence merely to
change its language. No new card is manufactured from missing IN625 coupon
data or incomplete CP1 properties.

Issue #479 remains open for actual owner/provider assignment and source-backed
completion of its requested process input. No supplier was contacted, no test
was commissioned, and no policy status, geometry or release gate changes here.
