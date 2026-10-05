# Actual CAD view: S1 assembly and V2 stock

[Study home](README.en.md) · [S1 dimensions and dossier](ASSEMBLY_MANUFACTURING_S1.en.md) · [Assembly STEP](results/assembly/S1/S1-assembly.step) · [V2 stock STEP](results/lpbf/V2-stock-scenario/V2-stock-scenario.step)

![Actual S1 assembly and V2 stock scenario, assumed dimensions](results/assembly/fan-S1-assembly-and-V2-stock-study.png)

The left view shows the nineteen solids of the published CAD assembly, including
the plenum, pulleys, belt path, shaft extension and support stocks. Coordinates
of the STL files derived from the STEP solids are retained. Housing and plenum
transparency reveals the rotor and right-angle drive. Colors identify components;
they do not represent computed stress, pressure or temperature fields.

The right view separately shows V2 stock, with an assumed 0.5 mm radial bore
stock and axial hub-face stock. This stock is not installed in the left assembly.
Axes are in millimeters. The 275 mm diameter, nine blades and plenum/drive
dimensions are study assumptions. No independent measurement confirms scale,
935/993 identity or mounting interfaces. The measurement sheet contains 52
physical features still blank, and the complete gate retains 55 unmet needs,
including catalogue identification and manufacturing/engineering validations.

The [render receipt](results/assembly/fan-S1-assembly-and-V2-stock-study.json)
links the image to twenty source STL files — nineteen S1 solids and V2 stock —
and to the geometry reports, script and dependencies by SHA256. The
[reproducible render](source/render_s1_delivery.py) projects those actual
tessellations with matplotlib; no geometry or calculation result is invented.
BRep and STEP checks, dimensional assumptions, six LPBF orientations and their
limits appear in the [S1 dossier](ASSEMBLY_MANUFACTURING_S1.en.md).

This view supports envelope review. It is neither proof of fit, a released
functional drawing nor a qualified process simulation. The
[S1 OpenUSD asset](omniverse/S1-layout.usda) retains its role as an evidence-linked
scene, without digital-twin validation or NVIDIA SimReady qualification.
Local CFD fields remain attached to their original geometries and conditions;
they are not attributed to this new envelope assembly.
