# Installed subsystems: separate dimensions and variables

The [parametric contract](parameters/qualitative-subsystem-contract.json)
describes the installed plenum, pulley/belt drive, ribbed support and observed
central envelope. Inspection of the
[video attributed to Patrick Motorsports](https://www.instagram.com/patrickmotorsports/reel/DeC4x04yjNP/)
is qualitative. Its pixels remain local; no third-party image is published.
The caption 935 3.5L Flat Fan / 993 6spd Transaxle does not demonstrate a
993 engine base, a four-valve cylinder head or equivalence between two fans.

**No documented installed dimension is available.** The
`documented_dimensions` lists are empty. Each variable has a symbol and a unit,
with null value/bounds; its measured interfaces remain null. The analytical
R0 diameter of 275 mm, its nine blades and relative clearance 0.008 appear
separately as study assumptions. They supply no documented dimension of the
filmed installation. No new functional CAD is generated.

| Subsystem | Design variables to fill in | Required measured dependencies |
| --- | --- | --- |
| Installed plenum | lip profile, depth H, extent R, sections Aᵢ, thickness t, clearance g | engine planes, holes, rotor datums, intake/control clearances, flow and losses per outlet |
| Pulleys/belt | pitch diameters D_driver / D_driven, center distance C, belt specification, grooves, ratio, tensioner travel | each pulley's role, axes and attachments, alignment, load path, bearings and tensions |
| Ribbed support | rib sections, thicknesses, span, screw patterns, bearing seats, material/condition | engine attachments, belt reactions, masses, preloads, vibration and temperature |
| Central envelope | profile and height, shaft/bore fit, axial clearances, web sections | fit and axial retention, bearing layout, speed/torque and thermal expansion |

Contract relations remain symbolic and conditional:
Q_total = ΣQᵢ without leakage in a steady incompressible regime;
Aᵢ = Qᵢ/vᵢ and Δpᵢ = KᵢQᵢ² only after the regime and Kᵢ are defined.
Existing screening resistances are not plenum measurements.

For an established belt transmission, without another stage and with measured
pitch diameters, n_driven/n_driver = D_driver/D_driven × (1 − slip).
Slip, pulley roles and the internal right-angle drive are unknown. Ideal
open-belt length is valid only for two coplanar pulleys without a tensioner;
no belt reference is selected.
T = (F_tight − F_slack) D_pitch/2 and P = Tω define a possible load path,
without supplying actual tensions or bearing loads.

Design order follows the interfaces: measured datums/attachments, axes and
assembly planes, clearances, sections, then loads and tolerances. Current
reconstructions do not provide their own fit evidence. Software guards refuse
to promote an unmeasured variable to a documented dimension, functionally
complete part or physical qualification.
