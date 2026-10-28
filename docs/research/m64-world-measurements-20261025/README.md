# Multilingual turbo and engine measurements, 2026-10-25

Thirty new grouped records extend the 993 Turbo research: 29 qualified
declarations and one signed catalogue value retained only to teach uncertainty.
Nineteen source representations were acquired and checked. The source material
is English, German and Japanese; searches also covered Chinese, Italian, French
and Spanish. This is a bounded research increment, not an exhaustive inventory
of the internet. No physical measurement was performed.

## Dimensions that add useful detail

| Named application | New detail | Evidence and limits |
|---|---|---|
| KTS MFS1606, listed for Porsche K16 6735/6736 and later 6726/6727 | Nose diameter 11.66 mm; overall height 27.00 mm; bore 5.41 mm; tip height 4.17 mm; blade height 25.39 mm | XLS row 1147 plus actually viewed maker datum diagram. Aftermarket wheel, no original K16 drawing or manufacturing tolerance. |
| KTS MFS1679 custom upgrade | Inducer/base exducer/tapered tip diameters 51.34 / 76.69 / 81.10 mm; tip height 4.82 mm | Row 1201 explicitly requires a Custom cover. No stock-housing fit, speed limit, map or power guarantee. |
| Turbosmart TS-0624-1072, 993 Turbo actuator | 169 mm rod-end-to-bracket axial span; separate 64 mm bracket-to-rear-reference axial span; body diameter 74 mm | Actual product drawing. The 169 mm label is not an overall actuator length. Generic IWG75 stud spacing and thread remain separately scoped. |
| CP-Carrillo SCR5468 / SCR5469, listed for 993/996 Turbo | Big-end bore 58.014 mm; big-end width 18.90 mm; pin-end width 19.51 mm; centre distance 127 mm | Maker catalogue p.99, checked against historical p.84. No original Porsche rod specification or installed bearing clearance. |
| Carrillo bolt-dependent masses | SCR5468 total/rotating/reciprocating 535 / 374 / 161 g; SCR5469 540 / 379 / 161 g | Distinct supplier products; reference masses. Historical ±1 g per end is set matching, not a dimensional machining tolerance. |
| NAPREC 930/964 spring kit | Maximum advertised lift 12 mm; 55 kgf set load; approximately 120 kgf at 11.7 mm lift; two 0.5 mm seat shims | Japanese maker source. Installed spring height is absent. No 993 M64/60 application established. |
| NAPREC oversized M64 3.6 inlet valve | Head 50.5 mm; stem 9 mm; overall length 110 mm; mass 119 g | 930/964-labelled aftermarket product. Its 9 mm stem must not be treated as an 8 mm 993 replacement. |
| Porsche 956, engine Type 935/76 | Bore 92.3 mm; stroke 66 mm | Official German Group C retrospective p.19, actually viewed. Does not apply to every 935, 962 or M64 engine. |

The [factual register](../../../catalog/reference/m64-world-measurements-20261025/facts.json)
also retains Molnar's own printed geometry, six generic IWG75 spring
identification pairs, and five complete grouped Web Cam timing-card declarations.
Grouped rows avoid counting every scalar as a separate discovery.

## Camshaft timing information

Web Cam publishes cards for its RUF BTR-labelled 644/645, Group B 238i/238e,
934 CIS 135, 935 233, and GT2 Twin Turbo EVO 563/564 offerings. The cards include
valve lift, advertised duration, duration at 0.050 inch valve lift, lobe centres,
and opening/closing events relative to TDC/BDC. For example, the GT2 EVO-labelled
supplier card declares 12.19 / 11.68 mm valve lift and 248 / 236 degrees duration
at its 0.050 inch checking threshold.

Timing events are checked with zero lash. The separate SET @ line uses 0.10 mm
lash and does not explicitly name its setpoint datum. The separately printed
.004 inch lash and millimetre lifts are rounded supplier declarations. They
must not replace exact unit conversion or become factory overlap settings.
Supplier model/RUF labels do not prove an original factory camshaft identity,
hydraulic-rocker compatibility or a complete lift-versus-angle curve.

## Identity, units and uncertainty

KTS row geometry is keyed to the maker diagram, including separate base and
tapered-tip exducer diameters. Binary workbook values are recorded at their
two-decimal display precision; hidden formula digits do not establish extra
accuracy. The ±0.50 mm catalogue search window is not a production tolerance.
The signed F value −0.02 mm is retained only as an unresolved declaration; it
does not establish material thickness, a negative clearance or an absolute
0.02 mm machining instruction.

Repeated values from Kinugawa remain reading evidence for a separate product.
A misprinted donor reference is preserved as an anomaly. The later MFS2402
K24 comparison is expressly a 996 application and cannot supply 993 K24 geometry.
Turbosmart's generic 32 mm stud spacing is an actuator-to-bracket interface,
not the bracket-to-turbo hole pattern. Spring identification lengths have no
published unloaded/installed-state definition and are not spring-rate data.

The CP flyer pin-wall and valve-relief figures lack explicit units in the
inspected headers and remain excluded leads. No original piston crown/skirt,
cylinder, head or port wall map, original K16 compressor map or maximum shaft
speed was established. Previously excluded FIA dimensions remain unresolved.

## Data and verification

- [Reference files and capture crosswalk](../../../catalog/reference/m64-world-measurements-20261025/README.md)
- [Prepared CPT/SFT data and split policy](../../../training/m64-world-measurements-20261025/README.md)
- [Documentary review](review.json) and [validation receipt](validation.json)

All five prior research/training packs and their partitions remain frozen.
Publisher families join manufacturer documents and their mirrors; the mirror
host is not treated as independent evidence. No model was trained, tokenized
or assigned a context-fit result in this increment. Supplied-record SFT assesses
record extraction, not independent engineering reasoning.

This increment implements evidence capture for B-VERIFY and attributed input
preparation for A-AI in the [M64 architecture](../../architecture/README.md),
following the [capture protocol](../../CAPTURE_PROTOCOL.md) and
[ADR 0012](../../decisions/0012-local-compute-gpu-last.md).
Independent documentary review does not grant physical engineering approval.

The validation receipt distinguishes the checks run here from the unchanged
Docker audit target omitted because its pinned image previously exhausted the
environment's storage. A full unmodified make check pass is not claimed.
