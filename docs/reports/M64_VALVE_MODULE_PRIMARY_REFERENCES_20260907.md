# Four-valve module: seat and fit references

## Concrete contribution

The [MAHLE manufacturer catalog, Valve Train Components 2025, v002](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_valve_train_components_catalog_2025_screen_v002.pdf)
gives two real references for **M64.01–03 Carrera / Carrera 4, two
valves per cylinder**, PDF p.825 / printed page 823, line 14:

| Reference | Function | Head / stem / length, mm | Seat angle |
| --- | --- | --- | --- |
| 503 VE 32000 000 | Intake | 48.98 / 8.95 / 110.1 | 45° |
| 503 VA 32001 000 | Exhaust | 42.5 / 8.95 / 106.4 | 45° |

The columns and header drawings were checked visually following the
PDF skill. **45° refers to the valve seat face, not to the inclination of its axis.**
This line is neither Turbo nor four-valve. The catalog values do not
include manufacturing tolerances.

The same document distinguishes two fits:

| Interface | Manufacturer reference range | Locator |
| --- | --- | --- |
| Stem-to-guide, 6–7 mm stem | Intake 10–40 µm; exhaust 25–55 µm | PDF p.27 / printed 25 |
| Stem-to-guide, 8–9 mm stem | Intake 20–50 µm; exhaust 35–65 µm | Same table |
| Seat insert OD 30–40 mm in aluminum cylinder head | Interference 0.050–0.090 mm | PDF p.30 / printed 28 |
| Seat insert OD 40–50 mm in aluminum cylinder head | Interference 0.060–0.100 mm | Same table |

The stem-to-guide table does not literally state "radial/diametral" nor a
measurement temperature. The seat table does not settle which range applies to
a value lying exactly on the boundary between two ranges. **No automatic
transposition into CAD diameters, nor into LPBF/turbo-qualified fits.**

## Consequence for the reconstruction

A mechanical module can now be built with **two facing conical
surfaces**, an explicit contact band, a coaxial guide and distinct
clearances. Choosing 45° for its first candidate remains a **documented design
choice**; it does not make the conversion conform to a Porsche four-valve
definition that does not exist in this source.

Still to be chosen and sized: head/stem of the four valves, seat width and
position, blend angles, throat, valve margin, axis inclination and
layout, engaged guide length and guide interference. Hot clearances, seats
in the printed alloy, springs and valvetrain clearances must then be computed
with the selected materials and loads. The 2V references above are not
parts selected for purchase for the conversion.

The 993 Carrera workshop manual already referenced in the project remains
inaccessible at the known paths: its OCR values 152–157 were not reinterpreted.
This addition replaces that dead end with accessible manufacturer references,
without modifying the interface contract.

## Traceability and verification

The link was followed from the [official MAHLE catalogs page](https://www.mahle-aftermarket.com/eu/en/media-center/product-catalogs/).
The privately downloaded file has 1,161 pages and 15,373,822 bytes; SHA-256
`d9be89be7a5bb369f7bcf7d20477661f4e93355fc24c362734403c91b346e2c9`.
The old link `mahle_valves_catalog_2025_screen.pdf` returns 404; the file
re-read is `mahle_valve_train_components_catalog_2025_screen_v002.pdf`.
This PDF's metadata carry January 27, 2026; the printed copyright
remains 2025. PDF pages 27, 29, 30 and 825 checked visually.

The [structured facts](../../twins/m64-cylinder-head/valve-module-documentary-references-20260907.json)
keep the variants, locators and limits. No manufacturer PDF or figure
is added to the repository. **No manufacturing authorization.**
