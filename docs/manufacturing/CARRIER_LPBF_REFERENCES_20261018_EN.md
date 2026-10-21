# Carrier: published LPBF material and machine references

Retrieved **18 October 2026**. These references support comparison of the
carrier's retained stress results with documented process data. The active
[material card](../../parts/993-eng-carrier-0001/source/design-20261016/bounded-webs.json)
retains its original elastic model: E = 107,000 MPa, Poisson ratio 0.31 and
density 4,420 kg/m³. Its strength allowable and fatigue curve remain unassigned.

## Material comparisons

| Published route | Reported yield strength Rp0.2 | Reported tensile strength | Source scope |
| --- | ---: | ---: | --- |
| Eplus3D Ti64 Grade 5 | 980 MPa | 1,080 MPa | Typical part properties; the page does not identify the machine, layer thickness or heat treatment for these values |
| EOS Ti64 Grade 5, M 290, 40 µm | Horizontal 970 MPa; vertical 1,010 MPa | 1,080 MPa | Heat-treated specimen results, 72 horizontal and 84 vertical samples |

Sources: [Eplus3D titanium materials](https://www.eplus3d.com/products/titanium-additive-manufacturing/)
and [EOS Ti64 Grade 5 data sheet, pages 4–8](https://www.eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_Titanium_Ti64_Grade5/material_datasheet_eos_titanium_ti64_grade5_en_web.pdf).
The EOS document has status **01/2024**. Its 40 µm route specifies approximately
120 minutes at 800 °C under vacuum, followed by vacuum cooling or argon
quenching. It reports a heat-treated fatigue strength of 595 MPa at 10⁷ cycles;
that single point supplies neither a complete S–N curve nor a stated loading
ratio in the cited fatigue section. These specimen results are comparison
references, rather than design allowables for a different printing process.

Keep alloy grade, machine, layer thickness, orientation, heat treatment and
surface condition attached to each reference. A later stress/reference ratio
must identify its exact source and remain separate from mesh convergence,
fatigue life and an accepted strength criterion.

## Build-envelope reference

The [Eplus3D EP-M650 specification](https://www.eplus3d.com/products/ep-m650-metal-3d-printer/)
lists a 650 × 650 × 800 mm build volume, with build plate included in the height,
titanium-alloy capability, a 20–120 µm layer range, and STL input through
EPControl/EPHatch.

The stock carrier's nominal unposed CAD bounds are 592 × 73 × 52 mm. Its
[closed process-input run](../reports/carrier-stock-process-links-20261018/root-terminal-review-001.json)
retains a 45° rotation about Z and a 32 mm Z translation. The actual posed STL
bounds are approximately **451.134 × 451.134 × 52 mm**, with Z from **10 to
62 mm**. These values belong to BREP `42da92cc` and surface `433c85bf`.
The current recipe uses a **500 × 500 mm reference plate**, declared 20 mm
thick, and 60 µm layers. Centring the posed part on that plate leaves about
**24.43 mm on each XY side**, before support extensions.

**Layout inference:** centring that posed part on a 650 mm square leaves
approximately **99.43 mm on each XY side**, before support extensions and
process allowances. Complete support and plate bounds remain to be calculated.
This comparison supplies no machine build file, laser parameters or simulated
distortion result.

The manufacturer's [EPHatch description](https://www.eplus3d.com/eplus3d-printing-software-for-high-productivity-metal-3d-printing.html) also identifies SLC and CLI slice import, with separate upper-surface, lower-surface and body parameters. This documents a vendor import route for later checked slice/support data; it does not provide a carrier machine job, scan strategy, laser parameters or process qualification. Whole-layer and support admission must precede a new format export.

The retained reference pages belong to their manufacturers; this note contains
links and summarized facts. No manufacturer PDF is redistributed here.
