# Printability — m64-cooling-fan-0001 (research assessment)

Candidate process: LPBF AlSi10Mg (repo lineage: 993 impeller/housing AlSi10Mg fiches).

| Feature | Config | Process check | Verdict |
|---|---|---|---|
| Blade thickness | 4.4 mm | LPBF AlSi10Mg self-supporting blades are printable ≥ ~1.5–2 mm; 4.4 mm is comfortable | OK |
| Blade cantilever | root chord 57 → tip 70 mm, no tip restraint | deflection under centrifugal + handling load unassessed; support-free printing means residual stress control needed (thin-wing distortion is the known failure mode for this geometry class) | printable, risk-flagged |
| Housing shell | 3 mm | fine for LPBF | OK |
| Radial clearance | 2.0 mm | above powder-bed minimum; no trapped-powder cavity in rotor; housing spokes leave open volumes | OK |
| Vent slots 22x14 mm | housing web | open, cleanable | OK |

Service-temperature caveat: engine-bay air side (< ~120 °C expected) keeps AlSi10Mg within strength limits, but the value is an assumption, not sourced (see provenance.json). The virtual bench (simulation/m64-virtual-bench/) shows the cooling-air side as the system bottleneck — printability of the fan is **not** the gating question; the airflow duty is.

Not covered: surface finish/roughness effect on airflow, creep under under-hood soak, balancing behaviour of printed rotor, burst speed. No printed part has been tested.
