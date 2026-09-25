# Local Porsche Fanatics audit - 993 Turbo

Audit of the local repository `C:/Users/MaximeGrenu/porschefanatic.com`, done
on 2026-08-30. The local repository is the site project and contains the
structured data used for the public OEM pages.

## Data found

| Public group | Function | Exposed PET lines | Distinct references in the local transcription | Result for the twin |
| --- | --- | ---: | ---: | --- |
| [`202-16`](https://porschefanatics.com/oem/993/202-16/) | Turbocharger | 71 | 40 | Bill of materials of the two turbochargers, oil lines, covers, housings and fasteners |
| [`107-20`](https://porschefanatics.com/oem/993/107-20/) | Turbocharging | 65 | 38 | Bill of materials of the manifolds, hoses, valves, sensors and clamps |
| [`107-45`](https://porschefanatics.com/oem/993/107-45/) | Charge air cooler | 49 | 28 | Bill of materials of the intercooler, ducts, brackets, seals, sensors and hoses |

The differences between lines and distinct references come from revisions,
left/right variants and the presence of two PET catalogs in the local site:
the KAT 17 transcription and the Porsche Classic 993 catalog. The
machine-transcribed data are kept by the site in `data/oem-listed.json`.

## K16 references confirmed by the transcription

Group `202-16` includes the four Porsche references already associated with
the K16 pair in the twin's catalog:

- `993 123 013 51` and `993 123 013 52`;
- `993 123 014 51` and `993 123 014 52`.

The same group also documents the interfaces and sub-assemblies to look for,
notably the oil lines `993 107 125 53` / `993 107 126 53`, the vent lines, the
brackets `993 107 005 52` / `993 107 005 53`, the control housings and the
seals. Groups `107-20` and `107-45` complete the context of compressed air and
charge cooling.

## Adjacent part measurements found in German

The FVD pages added to the registry give envelope and mass bounds for the
following replacement or upgrade parts:

| Part | Declared value | Status |
| --- | --- | --- |
| Right hose `993 110 632 56` | `430 x 70 x 90 mm`, `0.42 kg` | FVD in-house developed replacement |
| Left hose `993 110 633 56` | `430 x 70 x 115 mm`, `0.42 kg` | FVD in-house developed replacement |
| Air duct `993 110 340 54` | `600 x 280 x 50 mm`, `0.9 kg` | FVD in-house developed product |
| Reinforced bracket FVD11011050 | `255 x 80 x 23 mm`, `0.2 kg` | Aftermarket upgrade |
| Left heat shield `993 123 113 51` | `160 x 110 x 105 mm`, `0.23 kg` | Replacement listing, interface details unknown |
| AKS DASIS 177020T intercooler core for `993 110 330 53` | `260 x 270 x 60 mm` core, `7.06 kg` | Aftermarket replacement, core only |
| Motorsport intercooler FVD110330 | `870 x 410 x 190 mm`, `10.1 kg` | Upgrade with advertised modifications |

The FVD pages sometimes give a different mass for the `EQ`-suffixed variant of
the same hose (`0.52 kg` on the right and `0.44 kg` on the left). This
variation is kept as a supplier caveat in the source records; the mass must
not be used as an OEM identity criterion.

The dimensions and masses above are commercial declarations, not instrumented
measurements. They do not authorize manufacturing nor allow a flow
cross-section, a wall thickness, radii or center distances to be deduced.
The seven source records and the corresponding entries are in
`catalog/sources/` and `catalog/reference/993-declared-part-data.json`.

## Measurements and masses already available in the project

The project already has part dimensions and masses. They are
recorded in the reference registry and the source records, with an explicit
confidence level. A few examples useful to the twin:

| Part or assembly | Available data | Nature of the data |
| --- | --- | --- |
| Turbo engine carrier `993 115 021 53` | `600 x 50 x 50 mm`, `1.96 kg` | Product listing declaration, already structured in `catalog/reference/993-declared-part-data.json` |
| PAUTER 993/993 Turbo connecting rod | length `127.00 mm`, pin `23.01 mm`, bore `58.01 mm`, mass `535 g` | Manufacturer dimensions and mass, highly loaded part |
| 993 Turbo intake valve | stem `8 mm`, head `49 mm`, about `120 g` | Product declaration, to be distinguished from the commercial envelope `50 x 110 x 50 mm` |
| 993 Turbo exhaust valve | `108.9 x 43.5 x 8 mm` | Product declaration, with no tolerances or drawing |
| 993 Bi-Turbo rear spoiler | `145 x 63 x 27 cm`, `6.7 kg` | Aftermarket envelope and mass |
| Complete 993 Turbo | about `1,500 kg` | Variant curb weight, not the mass of a part |

These values are already in `catalog/sources/` and, for the selected masses
and envelopes, in `catalog/reference/`. They can feed bounds, priors and
consistency checks of the twin. They must not be silently converted into
metrological measurements: most are supplier declarations or community
transcriptions, with no repeats, datums or complete protocol.

## What the turbo PET pages do not provide

This PET collection produces no new manufacturing dimension for the K16 nor
for its interfaces. The added German listings produce envelopes and masses of
commercial products, but not an OEM definition.
The pages themselves state that the lines are "transcribed, not read": a
reference, a manufacturer description, a position and a PET page constitute
neither a measurement, nor a tolerance, nor a definition drawing.

In particular, no reliable public weight of the K16 turbocharger itself,
no CHRA mass and no dimensioned wheel or housing geometry were found in the
three PET groups. The masses of the engine carrier, the valves, the connecting
rod or the spoiler cannot be attributed to the K16.

Still missing for a reconstruction of the K16:

- diameters, center distances, flange profiles and axis datums measured on a
  real part;
- surfaces of the wheels, volutes, diffusers, housings and oil passages;
- radial/axial clearances, tolerances, roughness and wall thicknesses;
- materials, heat treatments, balancing and speed limits;
- flow/pressure/efficiency maps and test boundary conditions.

The site data are therefore integrated as a bill-of-materials and
interface-location source in
`catalog/parts/993-turbocharger-k16-pair-0001.json`. The geometry stays
`estimated`, with no master file and no fit claim.

## Next useful action

The first object to measure or scan under license must be a non-rotating,
non-structural part: cold duct, intercooler bracket or connection adapter.
The wheels, the shaft, the bearings, the hot housing and the CHRA stay
excluded from any additive manufacturing until a dedicated engineering review,
material characterization, balancing and validation.
