# Dimensions and details: vertical 993 and horizontal 935 system

Documentary survey of October 3, 2026. The [dimension register](dimensions.json)
separates Porsche data, commercial fields and unknowns. No value
published below currently calibrates the two 935 scans.

## German, English and French search

The searches use `Gebläserad`, `Flachgebläse`, `Gebläseantrieb`,
`liegendes Kühlgebläse`, `Luftführung`, `flat fan`, `fan drive`, `air guide`,
« ventilateur horizontal » (horizontal fan), « entraînement » (drive),
« renvoi d'angle » (angle drive) and « fiche d'homologation » (homologation
form). The rotor plane and its axis are always described separately: for our
935 project, horizontal plane and vertical axis. An isolated word
"vertical" in a listing does not identify this orientation.

The [existing 993](../../../twins/993-engine-cooling-fan-system-f0/program/research/README.md)
corpus already contains the OEM and supplier searches. Its provenance files
remain intact. The useful references are re-checked in their primary
sources; the dimensions of a 993 are not transferred to a 935.

## What the FIA actually provides

The [form no. 645, Group 4](https://historicdb.fia.com/sites/default/files/car_attachment/1613059201/homologation_form_number_645_group_4.pdf)
of the Porsche Turbo was downloaded and its **nine pages examined**.
Item 10 states air cooling. The engine photos H–J
on PDF page 6 show the base fan in a vertical plane.
Extension 1/1V, pages 8–9, covers among other things the dashboard, braking,
hubs, axle guides and fuel tank. No dimensioned drawing of the horizontal rotor,
the mount or the 935 angle drive was found in these nine pages.
The PDF states validity from January 1, 1976; the web index shows
January 2. For a precise historical date, keep this discrepancy.

The [PDF no. 3076, Group 3](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf)
was downloaded, and its 28 pages and eight extensions examined on October 6.
PDF page 9, items 148–149, gives **245 mm, 11 blades and light alloy**.
Photos I–J on page 6 show the vertical base fan.
This data does not calibrate our horizontal rotor with nine blade regions.
The extensions, pages 17–28, contain no manufacturing drawing of the
horizontal angle drive in this copy. Its SHA-256 and the locators are
kept in the source register; the PDF stays in the private cache.
This check does not prove the absence of useful documents in the rest of
the FIA archive. The copy transferred to Group B remains a separate source.

The [1976 Appendix J, articles 268–269](https://argent.fia.com/web/fia-public.nsf/ABCF4550D7659360C12574A5003C6CA0/$FILE/Hist_App_J_76_Art_269_a.pdf)
defines Group 5 from cars recognized in Groups 1–4 and leaves the other
mechanical elements free under article 269(d), subject to its
conditions. **Documentary inference:** a form for the base car
can therefore be useful without containing the manufacturing drawings of the
935 assembly used in racing. These regulatory documents specify neither our
interface dimensions nor the performance of our part.

The interactive FIA search returned an HTTP 403 error. The indexed pages
and the direct download of PDF 645 are accessible; the full archive
was not browsed. This result does not prove the absence of any
other relevant FIA documentation.

## 993: first dimensions and cross-checked references

The [German Porsche PET](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf),
plate 105-00, PDF pages 78–79, distinguishes in particular:

| Item | Variant/reference | Documentary data |
|---|---|---|
| Turbo M64.60 rotor | `96410601521` / `96410601522` | PET application; undimensioned drawing |
| Standard Carrera rotor | `96410601531` | Application distinct from the Turbo |
| RS M64.20 rotor | `96410601540` | Distinct application; hub `99310605180` |
| Turbo M64.60 housing | `99310666750` | Do not substitute the Carrera housing without checking |
| Belt position 13, Turbo | `99919234350` | Nominal designation 9.5 × 760 mm |
| Belts position 14, Turbo | `99919237350` / `99919237250` | 9.5 × 753 / 9.5 × 757 mm; reference to TI 7/97 for `.37350`, content not read |
| Belt position 13, Carrera | `99919233850` | 9.5 × 776 mm |
| Shims position 16 | `96410626830` / `96410626832` | Thicknesses 0.5 / 0.7 mm, per PET application |

For rotor `96410601522`, [FVD](https://www.fvd.net/en-us/shop/engine-cooling-fan-alternator-impeller-965-993-turbo-993-gt2-96410601522~p252068)
publishes **245 × 245 × 87 mm and 0.9 kg** in its commercial fields.
This is a documented order of magnitude for this Turbo/GT2 reference,
without datum, tolerance or weighing method. It is not a measurement of the
tip diameter, of the bare rotor mass or of a 935 part.

## 935: construction details and dimensions still missing

The [materials survey](MATERIALS.en.md) complements this section: Jim Torres
describes the factory metal housings in magnesium, then his reproductions in
aluminum. This observation concerns the drive housings; it does not
give the material of the owner's 935 rotor.

[Jim Torres Racing](https://jimtorresracing.com/for-sale/reproduction-flat-fan)
describes its reproduction with cast aluminum housings, a rotor machined from
7075 aluminum, an oil distribution shaft, a long banjo bolt and a supply
line. Alternator and belt are excluded from the advertised assembly.
The manufacturer reports a 60–90 minute run-in/test, between 2,000 and
8,500 rpm; the shaft to which this speed refers is not stated.
This advertised protocol does not define a maximum allowable speed.
The diameter, tolerances, metallurgical temper of the 7075 and the gear-tooth
drawings are not published. This information does not qualify the material
of our scan nor the claimed compatibility with all factory parts.

[EB Motorsport](https://eb-motorsport.com/shop/flat-fan-guibo/) lists
the flexible coupling `0701403`, with no published dimensions or torsional stiffness.
Its exact location on the scanned specimen remains to be identified.
Its crankshaft pulleys are intended for configurations with a
separate alternator:

| EB reproduction | Advertised material/finish | Commercial fields |
|---|---|---|
| [`0701504`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley/) | Machined, yellow zinc passivation; grade not specified | 0.58 kg; 20 × 12 × 3 cm |
| [`0701505`](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley-titanium/) | Advertised grade 5 titanium | 0.34 kg; 20 × 12 × 3 cm |

The sizes are commercial fields without geometric definition:
**20 cm is not an established pitch diameter**. The masses are indicative
according to the manufacturer. These product pages do not provide the
qualification dossier for the titanium, nor the exact interfaces, nor the mass of the complete system.

The [Design911 `93510610300R/1`](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/) assembly
combines a GRP funnel/housing with an aluminum fan. Its diameter
is not advertised on the page read. The **225 mm** visible nearby in
a product list concerns the `90110610300R/1` RSR/906/914, a different
part: it must not be assigned to the horizontal 935 rotor.

For our 935 system, the following remain unknown: rotor diameter and height,
blade geometry, bore/hub, mounting hole spacings, mount axes and bearing
faces, shaft/bearing seats, gear teeth/ratio, pulley pitch
diameter, housing/rotor clearances and lubrication details.
The [interface contract](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
lists the evidence to obtain for each of these connections.

## From documents to usable dimensions

To calibrate an OBJ, a dimension of the **same part** is required, on an
identifiable feature, with unit, datum, tolerance and provenance. A second
independent dimension, in another direction, will check the scale and
the distortions of the scan. The connections must then be measured
independently: axis, seat, face, holes and stack-up. A rotor is not calibrated
from a diameter taken from a photo or from another reference.

The next sources to examine are the relevant FIA extensions,
the instructions/catalogs for the identified 935 variant and the
manufacturing documents or metrology surveys of the rotor and the drive.
The acquisition leads remain documented; no paid document has
been purchased and no supplier has been contacted.
