# Assumed material reference proposal

**qualification=false.** This is a provenance-only proposal for a possible, explicitly assumed sensitivity study. It selects no production alloy, changes no coupon/card/solver input and authorizes no run.

[proposal.json](proposal.json) is the structured numerical record. It uses only the [sealed two-lead report](../material-hot-properties-two-new-leads-001/report.md) and its [bindings](../material-hot-properties-two-new-leads-001/bindings.json). Their exact hashes are recorded in the JSON; nested provenance is not expanded. No new source access occurred.

The two records stay separate:

- [Materials 2023, 4920](https://www.mdpi.com/1996-1944/16/14/4920) is a measured AlSi10Mg thermal lead. The JSON retains its identified density observation and two conductivity prose values. Both conductivity temperature coordinates are `null`; the test-range endpoints do not supply those coordinates. Full k(T)/cp(T) arrays, build/heat-flow association and a separate post-build treatment are unresolved. No curve was reconstructed.
- [Crystals 2022, 1309](https://www.mdpi.com/2073-4352/12/9/1309) publishes the five 20–400 °C model-input rows transcribed in the JSON, with units and the density/Poisson scalars. They are not a newly acquired matched coupon dataset. Heat state, orientation, original property measurement provenance, expansion definition/reference temperature, yield criterion, rate/dwell association, scatter and full plastic curves remain unresolved. The reported nonmonotonic expansion row is preserved without smoothing.

All missing properties are represented as `null`, including hot fatigue, TMF, cyclic response, creep/relaxation, statistical life and LPBF powder/liquid/calibration inputs. The unknown density/scalar temperature references and the contradictory specimen-size context are not silently resolved.

A future reviewed proposal could consider the model-input table for a hypothetical solid AlSi10Mg thermal or elastic sensitivity within its tabulated range, with every additional assumption declared. Expansion cannot yet define thermal strain; yield values cannot define plastic hardening or life. Interpolation, extrapolation and the study temperature envelope remain `null`. The measured thermal lead remains a separate comparison, not a source of missing coordinates or a second half of a blended material.

The next useful step is to review provenance, units and these nulls before proposing any sensitivity calculation. Matched state/orientation and true stress–plastic-strain data are still needed for a constitutive study. Existing CP1/HT1/CuCrZr/EOS/Nikon records, HT1 Figure 6/S5 access requirements and prototype composition limitations remain unchanged. No qualification, calibrated LPBF, printing or manufacturing acceptance follows.
