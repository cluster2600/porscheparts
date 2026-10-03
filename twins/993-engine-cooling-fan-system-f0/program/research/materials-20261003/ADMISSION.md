# Material and process admission

[Original review](material_process_review.md) · [143 property records](material_evidence.csv) · [25 sources](source_manifest.csv) · [Process requirements](simulation_requirements.csv) · [Import hashes](import-manifest.json)

The eight delivered original files are preserved byte for byte. Their archive
SHA-256 is `1843d62eb456c5bc75406b12c470fe3616382af7522a086eac398ffc65b5ce1f`.
The import check compares every CSV field against its JSON original and checks
all source IDs, individual hashes and unresolved process requirements.

These records admit **comparisons and sensitivities**, not a qualified material
card or manufacturing route. The selected machine remains null. In particular,
the shared scenario name `EOS_M290_30_AB` occurs for both AlSi10Mg and AlF357:
join on material, scenario, source, orientation, temperature and property.
Never join on the scenario name alone.

## Route-specific screening

| Material / route | What the delivered evidence supports | What prevents adoption in the impeller calculations |
|---|---|---|
| AlSi10Mg / current EOS M290 30 µm | Distinct as-built, T6 and stress-relieved room-temperature coupon properties; conductivity and interval-specific CTE | No matching ZRapid recipe, complete hot constitutive card or positive-mean-stress blade fatigue basis |
| AlF357 / EOS M290 30 µm | Separate as-built and T6-like coupon states, elongation and conductivity | Hot elastic/plastic/fatigue data and actual supplier process remain missing |
| Scalmalloy / 3D Systems DMP350 | Stress-relieved coupon values for the specified 325 °C / four-hour route | Do not combine these with the different CLM2/HIP temperature-dependent study |
| Scalmalloy / CLM2 GEN2 + HIP | Separate study: yield changes from 466 MPa at 21 °C to 156 MPa at 200 °C; reported modulus is temperature dependent | This is not the DMP350 material card; hot service temperature and target route are unresolved |
| Al2139 AM / EOS M290 60 µm + T4 | High room-temperature coupon strength after the specified treatment; process-specific thermal context | An undigitized hot graph is not a numerical hot allowable; elastic, fatigue and target-route data remain incomplete |
| Ti-6Al-4V / EOS M290 30 µm + heat treatment | Specified treated room-temperature coupons; substantially higher density | Inertia, thermal performance, fatigue, surface/heat treatment and galvanic isolation require a new matched analysis |
| CP1 / Constellium vendor sheet | Separate preliminary comparison; treated room-temperature coupons and conductivity | Thermal-stability claims do not supply a hot fatigue/constitutive card or a qualified production route |

Published densities expressed as lower bounds are **not conservative upper
bounds for centrifugal demand**. Coupon means, nominal values and turned
surface fatigue points are not part-specific statistical allowables. Unknown
E(T), Poisson ratio, plastic curves or fatigue curves remain unknown. No curve
is invented from yield and ultimate strength. Housing magnesium references do
not identify the impeller's material.

The new rotation and eigenstrain runs retain the legacy **assumed** isotropic
card: E = 70 GPa, Poisson ratio 0.33, density 2670 kg/m³. It is not relabeled as
qualified AlSi10Mg, AlF357 or another vendor's route. The uncalibrated imposed
strain is not a measured alloy property.

## Inherited ZRapid scenario

The project's pinned ZRapid card remains unchanged. Its 500 W, 1300 mm/s,
0.10 mm hatch and 0.04 mm layer are inherited research inputs. The cited
rolling-study DOI concerns hot rolling after SLM; rolled properties cannot be
assigned to an unrolled impeller, and the claimed originating recipe has not
been independently recovered for production. One active laser, absorptivity,
recoating time, support topology and boundary conditions remain assumptions.

The [current ZRapid machine page](https://www.zrapid.com/en/slm420dn.html)
states 420 × 420 × 500 mm, with substrate included in the Z envelope. The older
pinned project card states 450 mm Z. This discrepancy remains open; neither
is treated as usable build height without the actual supplier configuration.

Fourteen target-route input groups remain unresolved: powder traceability;
temperature-dependent elasticity/density; plasticity; thermal/phase data; CTE
and reference state; scan schedule; heat calibration; plate/support contacts;
gas and thermal boundaries; post-processing; eigenstrain calibration; fatigue
and defects; actual operation; independent validation. A complete thermal or
mechanical process simulation is blocked by these inputs. Elastic support-
release sensitivities and geometric build screening can proceed and are
explicitly reported as such.

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/check_material_process_import.py
```
