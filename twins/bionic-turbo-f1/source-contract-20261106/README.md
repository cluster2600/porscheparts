# Turbo interfaces and comparison basis

Issue #396 remains **blocked by missing physical evidence**. This documentary
increment indexes eight exact, bounded source excerpts and records 20 interface
or operating entries. Every measured value and uncertainty remains null in the
[interface ledger](interface-ledger.json). No turbo map, specimen identity,
measured attachment, thermal expansion or qualified running clearance exists
in this selected source set.

The [corpus](corpus.json) contains only owner-authored turbo repository text.
Each excerpt retains its whole-file hash, revision, exact one-based line span,
variant, units and rights. The carrier corpus is not imported. The
[plan](PLAN.md) and [prerequisite readback](prerequisites.json) precede indexing.
Historical sources, recovered data and the parent gate ledger remain unchanged.

## What the sources support

The assembly contract explicitly leaves bearing journals, rotor joint,
clearances, backplate retention, flanges, oil connections, wastegate, actuator,
fasteners and vehicle attachments unmeasured. The compressor nut needs thread,
seating, preload, torque and retention evidence. Design parameters are not
substitutes for these measurements.

The reference is the `radius_linear` volute with the conical chamber. The
candidate changes only the law to `area_affine`. The wheel and chamber remain
common. The tighter-shroud combined candidate is excluded by its unresolved
passage. The PR241 contact representation, native triangulations and the
complete physical assembly remain distinct.

The MRF cylinder and inlet/outlet conditions are computational assumptions.
The generator uses inlet total pressure 101325 Pa and total temperature
298.15 K; outlet static pressure is a prescribed multiple of inlet total
pressure. This multiple is **static/total**, not compressor total pressure
ratio. Speed is a generator input, not a measured operating map.

## Declared comparison conventions

These definitions prescribe a future comparison; they report no calculated or
measured performance. Both variants must use the same stations, operating
point, fluid model, frames, boundaries and qualified numerical route.

| Quantity | Definition and missing input |
|---|---|
| Mass flow | `mdot` in kg/s, positive outward at outlet and negative at inlet; compare balanced magnitudes at stations outside MRF. Native audit source: corpus `power`. |
| Corrected flow | `mdot_c = mdot * sqrt(Tt_in/T_ref) / (pt_in/p_ref)`. Declare project reference conditions `T_ref = 298.15 K`, `p_ref = 101325 Pa`; these are a comparison convention, not a claim of an industry standard. Actual inlet total state and flow remain unknown. |
| Corrected speed | `N_c = N / sqrt(Tt_in/T_ref)` in rpm, using the same reference state. Actual shaft speed remains unknown. |
| Total pressure ratio | `pt_out / pt_in`, with absolute pressures and matched total-state station averaging outside MRF. The outlet static boundary condition cannot supply `pt_out`. |
| Total temperatures | `Tt_in`, `Tt_out` in K at those same stations and averaging convention; actual values remain unknown. |
| Torque and power | Native moment `M_z` is fluid-on-rotor. Compressor shaft input torque is `-M_z`, so `P = omega * torque_input = -omega * M_z`, in W. `omega = N * 2*pi/60`, with declared signed axis. Pressure and viscous contributions are included. Native audit source: corpus `power`. |
| Energy check | Compare positive shaft input power with net outward total enthalpy flux `sum(phi*(h + abs(U_absolute)^2/2))` at ports outside MRF. Native audit source: corpus `power`. |
| Compressor efficiency | For a declared calorically perfect gas model only, `eta_tt = ((pt_out/pt_in)^((gamma-1)/gamma)-1)/(Tt_out/Tt_in-1)`. Otherwise use `(ht_out_isentropic-ht_in)/(ht_out-ht_in)` with the declared property model. No efficiency is evaluated without matched total states, positive compression/heating and model validity. |

No station averaging operator is yet qualified; its selection and uncertainty
must be prescribed before comparing performance. Bearing, seal and external
disc-friction losses are not added to the aerodynamic shaft result without
evidence. Turbine matching and engine power remain separate obligations.

## Missing-data gate and next action

Only a provisional synthetic comparison definition is justified. G03 cannot
pass until exact-variant interface measurements, running clearances, materials,
thermal state, operating map and uncertainties are sourced. A subsequent
measurement record must identify instrument/calibration, specimen, datums,
units, load/temperature state and uncertainty for the fields it fills.

Qwen was not used: source excerpts need no generated summary. CloudCompare was
not run: no admitted measured input pair with a frame/unit contract was supplied.
No source executable, historical proof, geometry, mesher or solver was run.

## Reproduce documentary retrieval

Use a new private output directory; the existing helper refuses overwrite:

```sh
python benchmarks/free-tools/knowledge.py build \
  --snapshot twins/bionic-turbo-f1/source-contract-20261106/corpus.json \
  --output "$HOME/Developer/PorschePartsArtifacts/turbo-source-index-new"
python benchmarks/free-tools/knowledge.py context \
  --snapshot twins/bionic-turbo-f1/source-contract-20261106/corpus.json \
  --database "$HOME/Developer/PorschePartsArtifacts/turbo-source-index-new/index.sqlite" \
  --question 'bearing_journals_and_oil_clearances' \
  --output "$HOME/Developer/PorschePartsArtifacts/turbo-source-context-new.json"
```

The [retrieval cases](retrieval-cases.json) test eight known citations through
the existing `context` function. They are a turbo-specific source check, not a
replacement for the carrier's frozen 30-case evaluation or an answer-quality
benchmark. Focused tests also verify source spans and hashes, stale-corpus
rejection, unknown queries and the authority boundary under hostile query text.

The [executed receipt](retrieval-receipt.json) records all eight expected
citations found, stale-corpus rejection, an unresolved unknown query and a
false authority flag for hostile query text. The actual private SQLite index
and control data occupied 100,855 bytes. Retrieval passed; G03 remains blocked.
