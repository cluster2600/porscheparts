# Faithful replica of the Wolfe/Xtreme 935 cylinder head

Research and execution: 28 October 2026. **The seller identified the manufacturer;
the exact donor engine remains unidentified. No functional or manufacturing
qualification has been achieved.**

Start with the [execution report](EXECUTION.md), the [validation plan](PREPARATION.md)
and the [Chinese supplier assessment](CHINA_MANUFACTURING.md). The machine-readable
[evidence](execution-20261028.json), [facts](facts.json), [sources](sources.json) and
[baseline contract](baseline-contract.json) retain uncertainty and scope.

## Programme decision

Reproduce the head actually scanned: interfaces, ports, chamber, fins and separate
hardware. Establish faithful geometry, reference-function correlation and a qualified
printing process before design optimisation. M64 conversion, four-valve conversion,
cooling changes, lightweighting and new forms are excluded from this baseline.

“Identical” requires an agreed dimensional definition and tolerances. It does not
mean copying wear, inventing invisible surfaces or imposing a universal scan tolerance.
Keep the observed and nominal models separate and document each correction. Moving
from casting to additive manufacturing is already a process change: unchanged shape
does not establish material equivalence.

## Corrected identification

The [Wolfe listing](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan)
claims a 935 application and possible adaptation to 1970s–1980s 911s. It does not
identify the engine variant, bore, stroke, modifications or dynamometer curves.

Seller correspondence dated 11 October 2026 identifies **Xtreme, cast then machined**
and corrects the listing's “billet” description. The private evidence reference
`PRIVATE-WOLFE-20261011` stays outside Git; no message body, personal address or
attachment is published. A separate K33 correspondence mentions a modified 3.5-litre
engine but does **not** link that engine to this head. Its displacement is not admitted.

Original OBJ SHA-256:
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
The execution phase rehashed and inspected the full source on Kali1; see
[EXECUTION.md](EXECUTION.md). Physical units and metrological accuracy remain unknown.

## Manufacturer catalogue data

[Xtreme](https://www.xtremecylinderheads.com/programs) describes its current heads as
US lost-wax castings in RR350, with HIP. This makes RR350 a research lead; it does not
identify the scanned specimen's batch, date or treatment.

All four published families were reviewed. None is selected by default. These are
catalogue ranges, not specimen measurements or uncertainty intervals. Sizes are in
mm; chamber volumes are in cm³.

| Parameter | [2.0–2.9 L](https://www.xtremecylinderheads.com/castings-1) | [3.0–3.5 L](https://www.xtremecylinderheads.com/castings-2) | [3.6–4.0 L NA](https://www.xtremecylinderheads.com/castings-3) | [3.6–4.0 L turbo](https://www.xtremecylinderheads.com/castings-4) |
|---|---:|---:|---:|---:|
| Published intake-port size | 35–42 | 35–44 | 40–47 | 40–47 |
| Published exhaust-port size | 35–39 | 35–41 | 36–41.5 | 36–41.5 |
| Intake valve diameter | 45–49 | 49–53 | 49–53 | 49–53 |
| Exhaust valve diameter | 38–41.5 | 41.5–42.5 | 41.5–42.5 | 41.5–42.5 |
| Intake / exhaust stem | 8 / 8 | 8 / 8 | 8 / 8 | 8 / 8 |
| Published spark-plug size | 12 or 14 | 12 or 14 | 12 or 14 | 12 or 14 |
| Chamber volume | 68–73 | 86–90 | 86–90 | 86–90 |

Port measurement planes, spark-plug thread pitch/profile and chamber-volume test
procedures are not specified. These numbers cannot define toleranced interfaces.
All four families list EV8 stainless intake valves and Inconel exhaust valves without
an exact Inconel grade; Inconel 751 must not be assumed.

The two smaller families list hardened ductile-iron seats, optional B5 copper exhaust
seats and optional MFI. The two larger families list ductile-iron intake seats and
B5 copper exhaust seats. The 3.0–3.5 L family lists 930 or Carrera intake flanges and
optional “Nirist” fire rings; the larger families list optional fire rings and ceramic
coating on request. None of these options has been identified on the scanned specimen.

The [Xtreme shop](https://www.xtremecylinderheads.com/ourshop) describes five-axis Rottler
machining/probing for ports and chambers and a SuperFlow SF750 flow/velocity/swirl bench.
These are leads for CAD and comparable test data, not proof that this head's results exist.

## Distinct 935 engine references

None of the following has been identified as the scanned head's donor. Published
power units and rounding are retained; hp, bhp and PS are not silently merged.

| Reference | Source-supported description | Permitted use |
|---|---|---|
| 1976 935 | Flat-six, 2.85 L, single turbo, 434 kW / 590 PS | Historical context only |
| Factory 935/77 | Twin turbo, 463 kW / 630 PS | Separate from customer-car specifications |
| 935 “Baby” | 1.4 L turbo, 279 kW / 380 PS | Separate variant |
| 935/78 “Moby Dick” | 3,211 cm³, twin turbo, four-valve water-cooled heads and air-cooled cylinders; up to 621 kW / 845 in the source's power unit | Different architecture; not adopted for Xtreme |
| Wera's documented K3 | Engine type 930/80, 3.2 L twin turbo, 760 PS | One example, not every K3 |
| Retro Sport rebuilt engine | 935 components, mechanical injection, twin ignition, horizontal fan, K27 turbos, 98 mm RUF pistons/cylinders, 7.5:1 compression, heads based on 3.2 L parts | Composite build; no transfer to this donor |
| Modern 935 introduced in 2018 | GT2 RS-derived 3.8 L twin turbo | Outside the historical baseline |

Sources: [Porsche turbo history](https://newsroom.porsche.it/de/pressemappen/50-Jahre-Porsche-Turbo-36122/Die-Anf%C3%A4nge-und-die-Turbo-Technologie-im-Motorsport.html),
[Porsche/Singer interview](https://newsroom.porsche.com/en/2026/history/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42018.html),
[Porsche Museum](https://newsroom.porsche.com/en/press-kits/Porsche-Museum/Porsche-935-78-%E2%80%9EMoby-Dick%E2%80%9C.html),
[Wera](https://www.wera.de/de/wera-erleben/tool-rebels/ein-stueck-rennsportgeschichte),
[Retro Sport](https://retro-sport.com/complete-935-engine),
[modern Porsche 935](https://www.porsche.com/usa/aboutporsche/pressreleases/pag/?id=513450&pool=international-de).

[Kremer's history](https://www.kremer-racing.com/en/heritage/) supplies K3 context.
[FIA Turbo Group 4 form 645](https://historicdb.fia.com/sites/default/files/car_attachment/1613059201/homologation_form_number_645_group_4.pdf)
is a related 930 archival lead, not an Xtreme drawing. It was acquired but not
transcribed. Vehicle designations such as 935/76 or 935/79 must not be conflated with
later Group C engine codes.

## Other head and material references

[Retro Sport's restored head set](https://retro-sport.com/products/porsche-race-cars/porsche-934-935/porsche-935-cylinder-heads-with-new-trw-valves-set-of-6)
uses reference 930 104 048 01: 41 mm intake ports, 40 mm exhaust ports, restored
height 84.20–84.21 mm, oil-cooled exhaust guides and twelve TRW valves described as
sodium-filled. Hardness and spark-plug-area crack checks are mentioned. These data
suggest inspection targets but cannot calibrate the Xtreme scan or identify its hardware.

The [Rheinfelden SDS](https://rheinfelden-alloys.eu/wp-content/uploads/2015/08/Alufont-60_RR350_AlCu5NiCoSbZr_GB_V2.pdf)
links RR350, Alufont-60 and AlCu5NiCoSbZr. The [manufacturer's Alufont page](https://rheinfelden-alloys.eu/legierungen/alufont/)
includes thermally loaded castings such as heads. Casting data and an SDS do not
constitute an LPBF material card.

The [2016 alloy handbook](https://rheinfelden-alloys.eu/wp-content/uploads/2017/01/Handbook-Primary-Aluminium-Casting-Alloys_RHEINFELDEN-ALLOYS_2016_EN.pdf)
was acquired for controlled extraction; its tables are not automatically admitted to
solvers. An [ORNL 2023 publication](https://impact.ornl.gov/en/publications/progression-of-creep-deformation-from-grain-boundaries-to-grain-i/)
studies RR350 creep at 300 and 350 °C. Only its abstract was consulted; those test
temperatures are not allowable head operating temperatures.

No qualified RR350 printing route for this head has been established. Do not silently
substitute AlSi10Mg, AlF357 or another alloy. Qualification must cover composition,
metallurgy, defects, anisotropy, treatments, machined surfaces, fatigue and hot properties.

## Coverage and remaining requirements

The research register contains 21 public sources, 94 scoped facts and all four
published Xtreme families. Relevant seller correspondence was reviewed privately.
One manufacturer is identified, but no exact donor, accepted specimen dimensions,
specimen-specific operating curves or physical manufacturing qualification is available.
The [China assessment](CHINA_MANUFACTURING.md) adds separately cited supplier leads.

This is a reproducible collection of accessible evidence, not an exhaustive worldwide
archive search. Private Xtreme drawings, the customer's engine record, bench curves
and foundry data remain outstanding. Complete videos, handbook tables and the FIA
form are not claimed as fully reviewed. Forum figures are not admitted as specimen inputs.

The baseline contract is documentary and does not retrofit controls into older runners.
The new audit verifies source identity and preserves observed surfaces; it deliberately
does not promote the result to a qualified CAD master, solver-ready solid or print-ready part.

## Published implementation and acceptance status

The runnable [scan auditor](../../../scripts/audit_935_faithful_scan.py) verifies the
frozen source, preserves its observed surfaces and reports open geometry and sampled
deviations. The [renderer](../../../scripts/render_935_scan_audit.py) produces inspection
views. The [dedicated CI workflow](../../../.github/workflows/935-faithful-audit.yml)
installs the geometry dependencies and runs the four synthetic regression tests without
requiring the private scan. [Publication checks](publication-validation.json) are kept
separate from the earlier execution receipts.

| Requested stage | Delivered | Remaining acceptance |
|---|---|---|
| Freeze inputs and provenance | Original hash verified twice; source/fact register; observed-surface exports | Verified units, scan accuracy, semantic hardware separation and hidden geometry |
| Resume the selected chain | Qwen admission attempt, PicoGK native check, Gmsh version, repeated OpenFOAM benchmark | Admitted head reconstruction; head-specific solver cases; current CalculiX/Adamantine execution |
| Faithful reconstruction | Exact-coordinate surface references; open-edge map; comparison with prior simplified mesh | Editable CAD, complete interfaces/chamber/ports/fins/internal passages and approved tolerances |
| Independent validation | Surface round-trip checks, topology counts, sampled distances and synthetic runtime checks | Self-intersections, complete wall-thickness analysis, head meshes, convergence, conservation and physical correlation |
| Chinese manufacturing data | Falcontech/Farsoon/BLT comparison, evidence gaps and unsent technical enquiry | Supplier responses, process-specific data, coupons and finished-part qualification |
| Vast and delivery | Kali1 executed the prepared checks; hashes and receipts collected; USD 0 spent | A justified prepared paid workload, then metered execution, retrieval and teardown; no rental currently exists |

There is no STEP/BRep head, closed printable STL/3MF, validated head CFD/FEA or
qualified metal build file in this delivery. Those stages are blocked by the
identified physical inputs, not completed by the software checks above.

The historical source-catalogue JSON is hash-pinned by the 917 morphology contract
and is preserved byte for byte. Its obsolete “billet” description and unverified
unit suggestion are superseded for this task by this dated dossier and baseline
contract; the frozen record is not silently rewritten.
