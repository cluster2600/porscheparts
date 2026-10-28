# New producer-source leads for the mechanical-data gaps

17 October 2026. The current publisher material record and its source register
were read unchanged. This research found useful new source associations, but no
complete matched mechanical card. Details, search scope and exact original
record hashes are in `research.json` (`4e23f72d…`).

EOS now identifies separate CP1 processes for [M290 / AlCP1_060_M291](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-290-60um)
and [M400-4 / AlCP1_060_M404](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-400-4-60um),
both argon / 60 µm with 400 °C / 4 h treatment. Their heat-treated yield tables
are associated with named processes, but label testing only as room temperature;
the numeric temperature stays null. E cells are blank and ν is absent.

Those pages also publish interval expansion values of 19, 21 and 22 × 10⁻⁶ K⁻¹
over 25–100, 25–200 and 25–300 °C. The table does not explicitly bind treatment
and orientation or define the reference-length/strain convention. These are
new expansion-source leads, not an instantaneous α(T) law or a justified fill
for the original unspecified-machine CP1 recipe. No interpolation was made.

[3D Systems' CP1 sheet](https://es.3dsystems.com/sites/default/files/2023-12/3d-systems-aheadd-cp1a-mds-letter-us-reva-web.pdf),
page 1 and footnotes 1–3, names DMP Flex350Triple / 60 µm, machined H/V coupons
and 400 °C / 4 h in air with air cooling. It supplies no missing E, ν or
expansion data. Keep that process separate from both EOS and the retained
Constellium coupon row.

The [current CuCrZr process sheet](https://www.eos.info/metal-solutions/data-sheets/copper/pds-eos-copperalloy-cucrzr-eos-m-400-80um)
adds an explicit room-temperature label and modulus test method. It still has
no numeric test temperature, ν, α(T) or new elevated-temperature mechanical law.
Its M400 label is not silently equated with the retained M400-1 identity.
Bounded producer-only HT1 searches found no new matched constants or disclosed
treatment schedules.

The useful next data request can name an exact CP1 process rather than an
unspecified machine, and ask for matched E/ν plus the expansion-table state and
reference convention. No request was sent, material selected, solver input
filled, source body redistributed or physical qualification granted. Sources
were accessed through web HTML/PDF parsing; no downloaded byte hashes or visual
PDF-table verification are claimed. No native run, geometry read or Git change
occurred.
