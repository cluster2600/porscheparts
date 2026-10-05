# Dimensions and details: vertical 993 and horizontal 935 system

Documentary review on 3 October 2026. The [dimension registry](dimensions.json)
separates Porsche data, commercial fields and unknowns. None of the values below
currently calibrates either 935 scan.

## German, English and French research

Search terms include `Gebläserad`, `Flachgebläse`, `Gebläseantrieb`,
`liegendes Kühlgebläse`, `Luftführung`, `flat fan`, `fan drive`, `air guide`,
“ventilateur horizontal” (horizontal fan), “entraînement” (drive), “renvoi d'angle”
(right-angle drive) and “fiche d'homologation” (homologation form).
Rotor plane and axis are separate: horizontal plane and vertical axis for our 935
project. “Vertical” alone in an advertisement does not identify this orientation.

The [existing 993 corpus](../../../twins/993-engine-cooling-fan-system-f0/program/research/README.md)
already contains OEM/supplier research. Its provenance files remain intact.
Useful references are rechecked at primary sources; 993 dimensions are not
transferred to 935.

## What FIA actually supplies

The Porsche Turbo [form no. 645, Group 4](https://historicdb.fia.com/sites/default/files/car_attachment/1613059201/homologation_form_number_645_group_4.pdf)
was downloaded and **all nine pages examined**. Section 10 states air cooling.
Engine photos H–J on PDF page 6 show the base fan in a vertical plane. Extension
1/1V, pages 8–9, concerns dashboard, braking, hubs, axle guidance and tank among
other items. No dimensioned horizontal 935 rotor, support or right-angle drive
drawing was found in those nine pages. The PDF states validity on 1 January 1976;
the web index shows 2 January. Retain this discrepancy for precise historical dates.

[No. 3076 Group 3 index](https://historicdb.fia.com/car/porsche-911-turbo-2993-0)
lists eight Turbo extensions. Titles alone do not establish 935 system drawings.
The archived copy transferred to Group B does not become a 935 form. Complete
review of dossier 3076 and its extensions remains outstanding.

[1976 Appendix J, articles 268–269](https://argent.fia.com/web/fia-public.nsf/ABCF4550D7659360C12574A5003C6CA0/$FILE/Hist_App_J_76_Art_269_a.pdf)
defines Group 5 from cars recognized in Groups 1–4 and leaves other mechanical
elements free under article 269(d), subject to its conditions. **Documentary
inference:** a base-car form can be useful without manufacturing drawings for
the racing 935 installation. These regulations specify neither our interface
dimensions nor part performance.

Interactive FIA search encountered HTTP 403. Indexed pages and direct PDF 645
download are accessible; the complete archive was not traversed. This does not
prove that no other relevant FIA documentation exists.

## 993: initial cross-checked dimensions and references

The [German Porsche PET](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf),
plate 105-00, PDF pages 78–79, distinguishes:

| Element | Variant/reference | Documentary data |
|---|---|---|
| Turbo M64.60 rotor | `96410601521` / `96410601522` | PET application; undimensioned drawing |
| Standard Carrera rotor | `96410601531` | Application distinct from Turbo |
| RS M64.20 rotor | `96410601540` | Separate application; hub `99310605180` |
| Turbo M64.60 housing | `99310666750` | Verify before substituting Carrera housing |
| Position 13 belt, Turbo | `99919234350` | Nominal 9.5 × 760 mm |
| Position 14 belts, Turbo | `99919237350` / `99919237250` | 9.5 × 753 /9.5 × 757 mm; TI 7/97 reference for `.37350`, content unread |
| Position 13 belt, Carrera | `99919233850` | 9.5 × 776 mm |
| Position 16 shims | `96410626830` / `96410626832` | 0.5 /0.7 mm according to PET application |

For `96410601522`, [FVD](https://www.fvd.net/en-us/shop/engine-cooling-fan-alternator-impeller-965-993-turbo-993-gt2-96410601522~p252068)
publishes **245 × 245 × 87 mm and 0.9 kg** in commercial fields. These document an
order of magnitude for that Turbo/GT 2 reference without datum, tolerance or
weighing method. They are not measured tip diameter, bare rotor mass or 935 data.

## 935: construction details and missing dimensions

[Material review](MATERIALS.en.md) adds Jim Torres's account of factory metal
magnesium housings and aluminium reproductions. This concerns drive housings,
not material identification of the owner's 935 rotor.

[Jim Torres Racing](https://jimtorresracing.com/for-sale/reproduction-flat-fan)
describes cast aluminium housings, machined aluminium 7075 rotor, oil distribution
shaft, long banjo bolt and supply line. Alternator and belt are excluded. The
manufacturer reports 60–90 minutes running-in/testing between 2000 and 8500 rpm;
the associated shaft is unspecified. This advertised protocol defines no
allowable maximum speed. Diameter, tolerances,7075 condition and gear drawings
are unpublished. These details qualify neither scan material nor claimed
compatibility with all factory parts.

[EB Motorsport](https://eb-motorsport.com/shop/flat-fan-guibo/) lists flexible
coupling `0701403` without dimensions or torsional stiffness. Its exact specimen
location remains unidentified. Crankshaft pulleys target separate alternators:

| EB reproduction | Advertised material/finish | Commercial fields |
|---|---|---|
| [`0701504`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley/) | Machined, yellow zinc passivation; grade unspecified | 0.58 kg;20 × 12 × 3 cm |
| [`0701505`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley-titanium/) | Advertised grade 5 titanium | 0.34 kg;20 × 12 × 3 cm |

Sizes are commercial fields without geometric definitions: **20 cm is not an
established pitch diameter**. Masses are indicative manufacturer values. These
sheets supply neither titanium qualification, exact interfaces nor system mass.

[Design911 `93510610300R/1`](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)
pairs a GRP funnel/housing with an aluminium fan. Diameter is absent from the
read sheet. Nearby **225 mm** in a product list concerns `90110610300R/1`
RSR/906/914, another part; do not assign it to the horizontal 935 rotor.

Our 935 system still lacks rotor diameter/height, blade geometry, bore/hub,
mounting spacing, support axes/faces, shaft/bearing seats, teeth/ratio, pulley
pitch diameter, housing/rotor clearance and lubrication details. The
[interface contract](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
lists required evidence for each connection.

## From documents to usable dimensions

OBJ calibration needs a dimension of the **same part** on an identifiable
feature, with unit, datum, tolerance and provenance. A second independent
dimension in another direction checks scale and distortion. Connections then
need independent axis, seat, face, hole and stack measurements. A photograph
or another reference's diameter cannot calibrate this rotor.

Next sources are relevant FIA extensions, identified 935 variant instructions/
catalogues and rotor/drive manufacturing documents or metrology. Acquisition
leads remain documented; no paid document was bought or supplier contacted.
