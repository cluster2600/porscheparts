# Temperature-dependent constitutive software witnesses

**HYPOTHETICAL SOFTWARE VERIFICATION ONLY.** This card represents no physical
alloy. Neither witness contains a cylinder head, deposition, a heat equation,
process calibration or manufacturing qualification.

The first input uses a 1 × 2 × 10 mm bar with both axial ends blocked, free
lateral faces and three in-plane point constraints removing rigid motion.
Four HEX8 elements admit the homogeneous analytical solution. E(T), ν(T) and
mean CTE(T) all vary. The CTE reference is 250 K; the stress-free state is 300 K.
Writing δ(T) = ᾱ(T)(T − 250), the independent thermal strain is
`θ = [δ(T) − δ(300)] / [1 + δ(300)]`. Thus `σzz = −E(T)θ` and
`εxx = εyy = (1 + ν(T))θ`. Integrating ᾱ as an instantaneous CTE would describe
a different law and fails this reference.

The second input is an override with incremental perfect J2 plasticity and
`Y(T) = 300 − 0.25(T − 300) MPa`. Its independent uniaxial return map recomputes
the trial stress from current E(T), current θ and old plastic strain, then clips
to ±Y(T). It verifies reversed plastic loading during cooling, without claiming
temperature-indexed hardening curves or release of the axial restraints.

All tolerances and both reference histories were recorded before native execution
in `work/962-engineering/moose-variable-laws-001/predeclared-contract.json`.
The elastic run passes 140 field comparisons and the plastic run 154, at all
seven times, including domain extrema of six stress components and three
displacements. Each run completes six equilibrium solves. Native logs, inputs,
CSV/Exodus fields, execution commands and hashes remain in separate fresh
`elastic-001` and `plastic-001` folders. Their durations are 3.23 s and 2.98 s.

MOOSE binary SHA-256 is
`c49e2c368799d80edf9ff858dd8960bd22f5430f48229ab49dcc0afd27afcc5b`, source
`167ee97da204df5e8643695e18b9b28910f0014b`, distribution
`idaholab/moose@sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452`.
The existing Kali1 installation is mounted read-only. Each isolated work folder
has no network, 2 GiB memory, 2 CPU quota and a 100 s native deadline. The exact
bounded command is retained with the result; no installation or image pull is
needed. Run `variable-thermoelastic.i`, then in a separate fresh folder run
`-i variable-thermoelastic.i variable-yield.i`.

The native `.i` inputs, hypothetical card, fields and execution receipts remain
unchanged. The checker was hardened after execution: it now enforces the frozen
histories and tolerances, checks native input hashes against that contract, and
refuses to overwrite an assessment. Its current source digest is recorded
separately from the assessor digest retained in the original contract.

`native-capture-manifest.json` binds all six elastic and seven plastic artifacts
to their original SSH capture. The capture command returned their bytes as
base64 in JSON. Reconstructing that JSON in its original artifact order exactly
matches the retained SSH stdout digest, including the CSV and Exodus files.
This is verification of retained outputs; neither native solve was repeated.

A [small public evidence bundle](../../derived/engineering/constitutive-witnesses/README.md)
contains the frozen contract, native CSVs and clean logs, input/card copies,
hardened assessments, capture hashes and whitelisted runtime metadata. Its
example reproduces field/reference comparisons without the private bundle or
a native solver. Raw command and execution receipts remain local because they
contain host paths. Their hashes are published; reconstructing the complete
original SSH capture requires those retained local receipts. Public projected
metadata alone cannot reproduce that complete capture check.

Verify retained results into a fresh directory with:

```sh
audit_dir="$(mktemp -d work/962-engineering/witness-check-XXXXXX)"
python3 -B twins/962-cylinder-head-f0/source/physics_witness/assess.py \
  work/962-engineering/moose-variable-laws-001/elastic-001/variable-thermoelastic_out.csv \
  --output "$audit_dir/elastic-assessment.json"
python3 -B twins/962-cylinder-head-f0/source/physics_witness/assess.py \
  work/962-engineering/moose-variable-laws-001/plastic-001/variable-yield_out.csv \
  --plastic --output "$audit_dir/plastic-assessment.json"
python3 -m unittest discover -s tests -p test_962_physics_witness.py
```

The checker rejects incomplete histories, nonfinite or incorrect fields, changed
inputs or captured outputs, changed frozen references or tolerances, wrong
runtime hashes and missing equilibrium solves. Scalar comparisons
cover the exported field extrema; this is not an independent audit of every
quadrature value or an engineering mesh-convergence study.

Pinned primary-source semantics:
[variable elasticity](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ADComputeVariableIsotropicElasticityTensor.C),
[mean CTE and reference-length normalization](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ComputeMeanThermalExpansionEigenstrainBase.C),
[CTE function argument](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ComputeMeanThermalExpansionFunctionEigenstrain.C),
[temperature-dependent yield and plastic history](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/IsotropicPlasticityStressUpdate.C).
