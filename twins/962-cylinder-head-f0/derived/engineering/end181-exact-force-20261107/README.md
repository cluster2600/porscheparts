# Exact integration of the saved END181 displacement field

This follow-up to the [residual diagnostic](../end181-residual-20261107/README.md)
addresses [#446](https://github.com/cluster2600/porscheparts/issues/446): is the
failed force balance present in the saved solution, or introduced only by
floating-point force assembly?

**The imbalance remains under exact rational integration.** With the frozen
assessor's linear-elastic coefficients, the END181 field produces a constrained
x-force of -2.25450e-6 N. The unchanged limit is 1e-7 N. The already-recorded
END182 field reduces this to -1.60501e-9 N. No solver was run or corrected here.

| Constrained resultant | Native END181 | Exact END181 | Exact END182 |
|---|---:|---:|---:|
| Fx, N | -2.25299e-6 | -2.25450e-6 | -1.60501e-9 |
| My, N m | -9.20598e-7 | -9.20334e-7 | -3.42606e-10 |
| Mz, N m | 9.78718e-7 | 9.78294e-7 | 3.04667e-10 |

The largest exact/native nodal-force difference is 1.32187e-8 N at END181 and
1.14823e-8 N at END182. This is a comparison of arithmetic evaluations, not a
new acceptance allowance. The original 12/36 failures remain recorded.

## Method and controls

The [source](../../../source/physics_witness/exact_end181_forces.py) integrates
the Q1 basis products analytically over each of the 256 Cartesian HEX8 cells.
On the unit interval, the same-corner basis-product integral is 1/3, the
opposite-corner product is 1/6, and a single basis integrates to 1/2. Products
across the three axes give the exact stiffness and thermal-load integrals.
No floating-point quadrature nodes or assembled nodal-force exports are used
to compute the diagnostic forces.

Saved binary64 displacement, temperature and birth-reference values are treated
as exact rational numbers. Their subtraction and all subsequent operations are
exact. Lamé coefficients and thermal expansion are the rational interpretations
of the **frozen assessor's binary64 constants**, not newly selected material
properties. This does not recover unrecorded internal solver precision or prove
that every native constitutive operation is identical to the assessor.

The existing published native-receipt hash binds the capture. Every consumed
CSV must match that receipt. The geometry/connectivity report is checked against
its publication manifest; current CSV coordinates must match it. Old and born
material references remain separate, including shared nodes.

Controls verify stiffness symmetry, zero force under rigid translation plus
free uniform thermal expansion, and the closed-form tractions for constant
extension and shear. Tests also reject an unbound capture before output. Exact
total force and moment are zero for both saved fields because of the integrated
basis identities; **that identity does not prove equilibrium of the free or
constrained subsets**, which are checked separately.

The [summary](summary.json) binds source, Python executable, inputs, execution
receipt and the private full rational-force table. The calculation completed
within a 60-second bound. Reproduce it with the retained three-update capture:

```sh
python3 -B twins/962-cylinder-head-f0/source/physics_witness/exact_end181_forces.py \
  /private/path/to/the/three-update-capture /private/path/new-exact-report.json
```

## Remaining work

Together with the native stopping witness, this supports testing an additional
reassembled correction within the release step. It does not establish that such
a trial would pass the complete 183-step history. The original assessor limits,
independent review, controller closure and held HEAD499 disposition remain open.
No frozen case, material value, raw scientific file or acceptance gate changed.

Affected phases are `lpbf_build` and `lpbf_release`, arithmetic diagnostic only.
The [instructions](../../../AGENTS.md), [workflow](../../../WORKFLOW.md) and
[nineteen-phase contract](../../../workflow-contract.json) apply. The fresh
diagnostic ledger accounts for all nineteen phases without promoting any;
the [historical phase ledger](../../phase-ledger-20261106/README.md) retains its
distinct states and blockers. Head/process/material/physical qualification and
manufacturing authorization remain ungranted.
