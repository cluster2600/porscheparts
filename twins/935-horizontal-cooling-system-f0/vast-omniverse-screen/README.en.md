# Vast / Omniverse screen for the horizontal 935 rotor

This campaign sends a **parametric screening model**, not the private scan.
It uses only the `226.94`-unit annular envelope from scale inference, provisionally
treated as `226.94 mm`, and ten visual blades. The 34 mm bore, fixed constraint
and all other details are model assumptions declared in `scenario.json`.

The Vast calculation produces a proxy CAD solid, tetrahedral mesh and ten
centrifugal CalculiX solutions at 8500 rpm; an unprestressed AlSi10Mg modal
calculation with elastic scaling for other cards; mass, inertia, tip speed,
energy and elastic extrapolations; a radial conduction indicator at 1 W per
blade; and USD with one variant per material card.

The set covers ten LPBF families in `materials.json`. The worldwide printable
alloy list remains open. Values compare material cards and are never design
allowables. WE43 yield strength remains `null`.

Each execution also loads the published input matrix of the
[neighbouring horizontal 935 system](../../935-horizontal-cooling-system/README.md).
It checks that six variant scopes stay separate, all 50 inputs are present and
no numerical 935 physical value is admitted. Report and USD receive evidence
hashes; proxy geometry remains an independent assumption.

No result proves flow, pressure, rotation strength, fatigue, balance, clearances,
interfaces, original material, 935 conformity or manufacturing fitness. Interface
dimensions, loads, selected-process coupons, balancing and tests remain required.
For titanium, the manufacturing dossier must document grade, machine,
orientation, treatment, machining, inspection, fatigue and galvanic isolation.
