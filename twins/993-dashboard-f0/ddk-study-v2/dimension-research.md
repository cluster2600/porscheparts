# Dashboard dimensional research, 2026-11-06

Reproduction dashboard pieces exist, and suppliers publish a few dimensions.
The inspected sources do not provide a public dimensioned survey, qualified scan
or editable CAD of the complete target M564 LHD assembly. They support component
identification, visual proportions and further measurement planning. None supplies
an admitted reading for the [independent interface contract](../interface-contracts.json).

All web pages below were accessed or access-attempted on **2026-11-06**. Product
dimensions are supplier declarations without stated datums, measurement methods,
uncertainties or tolerances. A seller's fitment list does not establish the exact
target variant. This memo records research leads; existing source records and
measurement contracts are unchanged.

## New or rechecked dimensional leads

| Source and exact item | Published information | Interpretation for this project |
| --- | --- | --- |
| [FVD FVD55522005](https://www.fvd.net/en-us/shop/race-dashboard-964-993-carbon-fiber-kevlar-left-hand-drive-without-a-c-vent-fvd55522005~p238149), Carbon/Kevlar race dashboard, 964/993 LHD, without centre A/C vent | Product length **129 cm**, width **16 cm**, height **16.5 cm**; 1.5 kg. | Nominal product envelope **1290 × 160 × 165 mm**, in the seller's L/W/H order. An upper race shell, not the complete dashboard or an OEM surface survey. Defrost opening is included; composite preparation and possible modifications are acknowledged. Useful as a broad envelope comparison, not as fit geometry. |
| [FVD FVD552964040](https://www.fvd.net/de-ch/shop/abdeckung-radio-schalttafel-delete-kit-0-schalter-oeffnungen-964-993-911-85-fvd552964040~p310749), radio blanking plate, no switch holes; manufacturer identified as Rennline | Product length **18.7 cm**, width **5.8 cm**, height **2.8 cm**; 0.13 kg. | **187 × 58 × 28 mm** is the commercial product envelope. It does not establish the radio aperture, face thickness, bracket position or mounting pattern. Listing includes brackets and hardware. The catalogue's earlier lead is confirmed; no independent fit test is supplied. |
| [F-S-H classic-radio Singer-style fascia](https://www.f-s-h.com/964-993-Armaturenbrett-Zierleiste-Singer-Style-mit-klassischem-Radioschacht) | Radio-knob hole centres **13 cm** apart; rectangular opening approximately **9.5 × 4.2 cm**; optional ignition ring **Ø55 mm**. | **130 mm** centres and approximately **95 × 42 mm** belong to this custom classic-radio fascia. The page specifically describes the profiled HVAC surround as designed for the 964 and discusses individual adaptation. They are not OEM 993 radio/HVAC or ignition opening dimensions. |
| [OCParts 964/993 aluminium fascia](https://ocparts.com/product/964-993-aluminum-dashboard/) | LHD/RHD and PCCM/standard-radio/no-radio variants. Supplier states that **3–5 mm** must be trimmed from the original opening. | This is a modification allowance for the supplier's one-piece fascia, not the opening size or a tolerance. No dimensioned drawing is provided. Do not combine it with the F-S-H custom-radio dimensions to reconstruct a fictitious OEM opening. |

FVD's labels explicitly call the values product dimensions, rather than shipping
dimensions; the endpoints and inclusion of installed accessories remain undefined.
The race-shell dimensions also differ from the previously recorded standard upper
trim envelope of 1270 × 190 × 120 mm in [the reference register](references.json).
These describe different products: averaging them or treating their spread as an
OEM manufacturing tolerance would be unjustified.

The F-S-H variant's description was checked in its public German HTML because
the web text extractor omitted that section. Its canonical
[parent product page](https://www.f-s-h.com/Armaturenbrett-Zierleiste-Singer-Style-964-993-911-1986-1989)
describes a two-piece milled aluminium replacement for the foam fascia. The
variant page is the source of the radio dimensions. No source HTML was saved here.

## Reproduction and photo leads

- [Sierra Madre SMC-552-055-05](https://sierramadrecollection.com/products/porsche-dashboard-911-964-993-87-98-smc-552-055-05)
  is explicitly catalogued as a reproduction plastic dashboard core for
  911/964/993, 1987–1998, with bare-core, vinyl and leather choices. Its gallery
  can inform visible shape and component segmentation. The inspected listing
  gives no measured overall dimensions or mounting drawing; the broad model
  listing does not resolve M564 LHD applicability.
- [dp motorsport's 964 racing category](https://www.dp-motorsport.de/produkt-kategorie/dp64/rennspecials-dp64/)
  lists lightweight 911–993 dashboards, instrument covers and separate knee
  strips. This is a manufacturer lead, not a verified dimensional source:
  direct access returned HTTP 429, and an alternate category timed out. Only
  indexed manufacturer catalogue information was available in this pass.
- FVD's race-shell gallery contains several product views; OCP and F-S-H show
  fascia products. These are distinct aftermarket shapes and should remain
  separately labelled when visually compared with an installed 993 interior.

No open reuse licence was identified for these commercial galleries. Image
creators are not individually identified. This memo links the publishers and
records factual observations only; it includes no downloaded images, copied CAD,
raw scans or permission to redistribute source pixels. Manufacturing a product
implies access to some design or tooling, but does **not** establish a public or
licensable scan or a measured OEM dataset.

## What DDK adds

[912Flyer's upper-dashboard post, 21 July 2020](https://www.ddk-online.com/phpBB2/viewtopic.php?p=614313)
describes the removable pad, defroster grille, end covers, centre vent and concealed
attachments. [The lower-dashboard post, 22 July 2020](https://www.ddk-online.com/phpBB2/viewtopic.php?p=614416)
reports four lower-dashboard studs: the outer pair near the side vents and the
inner pair beside the radio/HVAC. It also describes four clips retaining each side
vent. These are useful attachment-inventory candidates and explain the assembly's
segmentation. The reported 8 mm and 10 mm values are tool sizes, not hole diameters,
thread sizes, pitch or coordinates.

The owner describes a **1994 RHD 993**, with a driver airbag discussed in the
removal sequence. It is not an admitted M564 LHD specimen. Some thread images are
explicitly borrowed from other sites, so attribution and rights must be resolved
per image. No scaled drawing or attachment coordinates were found in these posts.
Topic [t57742](https://www.ddk-online.com/phpBB2/viewtopic.php?t=57742) returned a
verification page in this pass; its unavailable contents support no new claim.

The separately recorded [Rennlist dashboard-lighting lead](https://rennlist.com/forums/993-forum/1202129-dashboard-lighting-question.html)
could not be reread directly (HTTP 403). The existing catalogue record describes
19 × 31 mm inferred from a window switch and approximately 17 × 28 mm for an old
switch bezel opening. They remain an unconfirmed local switch/light lead, not a
new measurement of the dashboard or proof of the target aperture.

## Measurements that would change the next model

1. **Identify the specimen and body frame.** Resolve the target option/drive
   configuration, then independently establish the A-pillar faces,
   windshield-base flange and tunnel centreline required by `VEH-993` and
   `IF_AIRBAG_CONFIGURATION`. A model-derived frame cannot replace this.
2. **Capture the pad and brow profiles.** Obtain overall span, depth, height,
   front-edge sweep and cross-sections, including installed windshield/pillar
   gaps. Use same-specimen scaled views or a permitted scan with uncertainty;
   supplier bounding boxes do not constrain these curves.
3. **Locate the five instrument openings.** Measure aperture profiles, centre
   positions, axes, depth and retaining interfaces for `IF_CLUSTER_TO_HOOD_PANEL`.
   Replacement dial-face and bezel diameters remain distinct quantities.
4. **Measure vents and controls independently.** Record centre/side vent cutouts,
   radii, duct depth, seal faces and clip locations; then radio/HVAC/switch
   apertures and host retainers. Custom fascia sizes cannot fill these values.
5. **Survey every attachment on part and host.** Check DDK's four-stud candidate
   against the exact specimen, then measure all stud/screw/clip axes, mating
   faces, fastener identities and tolerances. Do not mirror RHD coordinates.
6. **Capture the remaining assembly interfaces.** Glovebox hinges/latch/sweep,
   knee-strip mounts, console connections and documented steering/restraint
   clearances complete the full-dashboard scope. Each reading needs provenance,
   repetitions and bounding uncertainty under the existing intake contract.

This is a bounded search result: no qualifying full-dashboard dimensional dataset
was found on the inspected pages. It does not claim that no owner, restorer or
manufacturer has measured one. Public images can improve the F0 silhouette and
component relationships while all functional interfaces remain unmeasured.
