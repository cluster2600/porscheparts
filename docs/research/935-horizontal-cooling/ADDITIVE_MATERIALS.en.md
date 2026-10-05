# Aluminium, magnesium and titanium for printed versions

On 3 October 2026, the owner set three candidate families for improved parts
in both programmes: **aluminium, magnesium or titanium in metal additive
manufacturing**. Each part needs its own material/process selection.
Historical material remains documented in [MATERIALS.md](MATERIALS.en.md).

## Three initial candidates

| Candidate | Process to study | Available data and remaining work |
|---|---|---|
| Aluminium AlSi10Mg | Laser powder bed fusion, LPBF | Industrial EOS data by machine and parameter set. Proposed basis for the first printable rotor, support and housing study; no final selection. |
| Magnesium WE43 | LPBF with equipment/process suitable for magnesium | Printing demonstrated in experimental studies and documented additive powder. Identify a workshop accepting our dimensions and supplying results for its own process. |
| Titanium Ti- 6Al-4V, Ti64 | LPBF | Industrial EOS data available. Compare rotor and support parts with resized geometry; strength does not guarantee a mass gain. |

Primary sources: [EOS AlSi10Mg process data](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg),
[EOS Ti64 process data](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-titanium-ti64),
[Julmi et al., 2021, WE43 LPBF experiments](https://pmc.ncbi.nlm.nih.gov/articles/PMC7918529/),
[Luxfer Elektron MAP+43 powder, 2018 sheet](https://luxfermagtech.com/wp-content/uploads/2020/03/Luxfer-Data-Sheets-Elektron-MAP43.pdf).
The powder sheet establishes a described offer, not current stock, a supplier
or a qualified process for this rotor. Research coupons do not qualify a
rotating fan.

## Compare mass without assuming the outcome

EOS M 290 sheets at 30 µm layers give mean densities at least 2.67 g/cm³ for
AlSi10Mg and 4.4 g/cm³ for Ti64. Reference density for magnesium
[WE43C / Elektron 43](https://www.luxfermeltechnologies.com/elektron-43/) is about
1.83 g/cm³ for wrought material; this is not a measurement of our printed part.
Powder apparent/tap densities differ from consolidated metal density.

At equal volume these references make magnesium lighter and titanium heavier
than aluminium. This compares densities, without claiming system gains.
Then compare common geometry to isolate material effects and resized geometry
meeting the same loads, clearances, stiffness and fatigue criteria. Inserts,
coatings, fasteners and bearings belong in the complete mass balance.

## Printing dossier and calculations per variant

Studies must link each result to geometry, alloy, machine, parameters,
orientation, layer thickness, supports, powder and treatments. Material data
must describe the actual process. Cast magnesium or machined aluminium 7075
properties are not properties of our LPBF part.

Compare mass, inertia, centrifugal stresses, blade deformation, modes and
fatigue, then flow–pressure–power for each geometry. Final selection must
include temperatures, blade roughness, seat/bore finishing, inspection,
balancing and tests.

Titanium dossiers must explicitly include grade, process, orientation, heat
treatment, machining, inspection, fatigue assumptions and galvanic isolation
at aluminium/magnesium interfaces. Magnesium variants must document surface
protection and dissimilar metal interfaces. No supplier or quotation is selected.

Aluminium is an initial recommendation based on industrial data and the existing
AlSi10Mg scenario. Comparison remains open to magnesium and titanium. The
[executed comparison report](../../../twins/fan-alloy-comparison-f0/README.en.md)
documents three centrifugal calculations on the parametric 993 model and blocked
volumetric reconstruction of the 935 scan. No variant is printed or qualified on
the engine.
