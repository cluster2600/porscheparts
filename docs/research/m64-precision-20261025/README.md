# M64 guide, clearance and interface measurements, 2026-10-25

This increment adds **20 grouped records**: 17 qualified declarations and three
explicit uncertainty records. Ten reviewed source representations link seven
new and three frozen canonical sources. English, German and a multilingual
Italian-maker catalogue supply the accepted data. No physical measurement,
part fabrication or model-training job was performed.

## Useful new dimensions and conditions

| Exact application | Declared data | Qualification |
|---|---|---|
| Porsche Type3 rod category, M64/60 only from the printed booklet applicability point | Maximum complete-rod mass difference in one engine: 6 g | Weigh without bearing shells. Set-wide difference, not ±6 g per rod or an end-specific balancing target. |
| Metelli guide 01-2620, exact M64.60 application/cross-reference | ID8.00 / OD13.05 / length45.4 mm; material codeB1 means phosphor-bronze | No normalized alloy grade, factory interference fit or production tolerance. Valve-side assignment is unresolved. |
| Metelli guide 01-2621, exact M64.60 application/cross-reference | ID8.00 / OD13.05 / length55.2 mm | CodeB is not identified as bronze by the inspected legend. Valve-side assignment remains unresolved. |
| Factory PET993 turbo oil collection interfaces | PlugM18×1.5 with sealing ringA18×24; O-rings18.65×2.45 and63×2 mm; studM8×26 | Nominal catalogue callouts and exact component associations. No flange-hole coordinates or implied thread pitch for the M8 stud. |
| Würth replacement plug matching Porsche90021900930 | Catalogue designationM18×1.50×12, internal hex8 mm, aluminium | Supplier product declaration;12 mm is the catalogue length designation with no detailed end-face datum. No original Porsche material inferred. |
| Würth seal matching90012310630 | Nominal18×24; declared geometryd1=18.2,d2=24,h1=1.5 mm | The supplier ID differs from the nominal name. This does not change the factory catalogue designation. |
| Carrillo RSR/964 replacement rods, historical2013 catalogue | Big-end width21.74 mm; complete geometry and bolt-dependent masses retained together | Related aftermarket race application. No transfer to the993 rod's18.90 mm width. |
| LN reference labelled RSR3.8 case O-ringing | GrooveOD115.4±0.1 mm; labelled depth2.9 mm; deck-to-start17 mm | Generation/engine suffix and groove-depth axis are unspecified. Reference text is insufficient for a complete machining drawing. |
| ARP204-6005 exact aftermarket PorscheM9 kit | Loaded stretch0.0100–0.0105in; calculated0.254–0.2667 mm; separately declared40ft-lb alternative withARP Ultra-Torque | Historical kit sheet plus current2026 table unit confirmation. No exact993/M64/60 fit established. |

The [full factual register](../../../catalog/reference/m64-precision-20261025/facts.json)
also records related Carrera/RS crankshaft seat intervals, intermediate-shaft
sprocket construction distances98.07/43.27 mm, and the conditional ±0.25 mm
alignment check. No Turbo identity was established for those booklet spreads.
The crank table's WearDimension numbers also occur as conditional grinding
references for deeply scored oil-seal surfaces; they are not generalized into
universal rejection minima. WidthA is distinct from axial endplay and from the
separately scoped Glyco crank-web-distance record.

## Preserve the discrepancies

Metelli lists both01-2620 and01-2621 as A (inlet) in its M64.60 row, while other
application rows list01-2620 as S (exhaust). The dimensional tuple and OE
cross-reference remain attributed to the exact product. No assumed typo is
silently repaired into a definitive valve-side assignment. The B1 material
legend is explicit; plain B does not provide a named bronze or alloy grade.

LN's964/993 ring-groove table prints4.176–4.178in alongside106.045–106.121mm
for inside diameter. Its911/930 smaller-bore table prints4.215–4.217in alongside
107.061–107.137mm for outside diameter. Exact conversions expose disagreement.
Both remain uncertainty targets with no machining value selected. An additional
964/993 outer-diameter conflict is retained in the reading register. Consistent
rounded inch/mm values elsewhere are retained as separately printed units,
with no radial/diametral convention invented for generic register clearances.

ARP's loaded extension target is separate from its unloaded replacement rule:
any permanent deformation OR growth of more than0.001in from the individual
bolt's original non-torqued length. The strict > condition is retained; the
calculated0.0254mm threshold is an explicit unit conversion. No torque or limit
is transferred to factory Porsche, Pauter or Carrillo bolts. The historical
sheet literally prints933; this is not repaired into a993 fitment claim.

TurboKraft's current NiResist-labelled ring product describes high-nickel
stainless steel. Its product name is not evidence for a generic Ni-Resist
cast-iron alloy or for original Porsche metallurgy. No unspecified material
grade, heat treatment or dimension is filled in from another product.

## What remains unresolved

Original M64/60 piston, cylinder and head/port wall maps, original K16 flange
hole coordinates, original compressor maps and maximum shaft-speed limits
remain missing. The MAHLE0.035 mm clearance retailer field, indexed9m87cc
chamber announcement and FVD material snippets remain unaccepted leads until
their source identity and required conditions are established.

## Reproducibility and project integration

- [Reference files and capture crosswalk](../../../catalog/reference/m64-precision-20261025/README.md)
- [Prepared CPT/SFT data](../../../training/m64-precision-20261025/README.md)
- [Independent documentary review](review.json) and [validation receipt](validation.json)

Twenty CPT passages and twenty supplied-record SFT conversations preserve all
measurement metadata. All six earlier packs and their evaluation partitions
remain frozen; no new evaluation set is claimed. The data are not a test of
unaided recall or independent engineering reasoning.

This increment supports B-VERIFY evidence capture and A-AI attributed inputs in
the [M64 architecture](../../architecture/README.md), under the
[capture protocol](../../CAPTURE_PROTOCOL.md) and
[ADR0012](../../decisions/0012-local-compute-gpu-last.md). Documentary review does
not grant physical engineering approval. The validation receipt explicitly
records the unchanged Docker audit omission; a full unmodified make check pass
is not claimed.
