# Moving heat, variable capacity and thermal material birth

**HYPOTHETICAL SOFTWARE VERIFICATION ONLY.** These are synthetic SI-unit
thermal laws and a numerical fixture. They describe no physical alloy, head,
laser recipe or calibrated LPBF process. Whole-head LPBF execution remains open.

The installed MOOSE runtime contains `FunctionPathEllipsoidHeatSource` and
`ADMatHeatSource`. Their combination moves a volumetric Gaussian along three
functions. It requires no MALAMUTE extension. In the pinned implementation,
the full-space integral is **2 f η P**, and a centered half-space contains
**f η P**. A finite workpiece contains a further error-function fraction; the
parameter named `power` is therefore not automatically absorbed part power.

## Frozen case and independent checks

A 2 × 1 × 1 m synthetic box uses 256 HEX8 elements. Initially, the left half is
active at 400 K. At 0.2 s the right half is born, with genuinely new nodes at
350 K and existing shared nodes retaining their previous temperatures. All
external boundaries are adiabatic. A separate zero-valued placeholder equation
on the inactive block maintains kernel coverage and contributes no heat.
The moving source and linear-in-temperature k and cp are in [card.json](card.json).

The independent checker reads every nodal snapshot and exported cell-property
average. It checks active node counts, all old-node values at every step,
new-node temperatures, every cell's k(T), cp(T) and Gaussian source, and its
finite-box power integral. Nonlinear enthalpy is integrated from the full
trilinear temperature field with the declared Gauss rule, rather than inferred
from average temperature. Birth energy follows the declared shared-node
interpolation rule; a conforming new region is not uniformly 350 K at its shared
interface. This state-dependent birth reference is frozen as an invariant,
without fitting the thermal solution.

For linear cp, backward Euler obeys the independently derived identity

`H_end − H_begin = Δt ∫Q_h dV − ρ cp′/2 ∫(T_end − T_begin)² dV`.

The capacity correction is checked explicitly. Continuous-time deposited
energy is independently integrated from the finite-box Gaussian, splitting at
the birth event. Event activation occurs at the beginning of an ending-time
labelled step; its finite-step timing error is included in the refinement test.

Before native execution, the card, input, checker hash, refinement levels,
reference rules and tolerances were frozen. The passing contract is
`work/962-engineering/moose-thermal-birth-001/frozen-contract-003.json`, SHA-256
`099ca030b523d43ca8a666c3e7f3a23cdc139077fe6d2e3531c051372d5a0ee2`.
Earlier contracts and two native setup refusals remain preserved: incorrect
quadrature section, then missing kernel coverage on the inactive block. The
corrections changed input wiring only; thermal laws, geometry, references,
time levels and tolerances stayed unchanged.

| Δt (s) | Native steps | Runtime | Independent checks | Maximum continuous energy error |
| ---: | ---: | ---: | ---: | ---: |
| 0.0100 | 40 | 2.23 s | 23 588 | 1.3048% |
| 0.0050 | 80 | 3.84 s | 46 788 | 0.6794% |
| 0.0025 | 160 | 6.40 s | 93 189 | 0.3481% |

Successive error ratios are **1.920 and 1.952**, above the predeclared 1.4 gate.
The finest error is below its predeclared 1% limit. The corrected discrete
energy-identity error is at most **9.3 × 10⁻¹² J**; Gaussian power quadrature
error stays below **6.55 × 10⁻⁵ relative**. Old-node history and new-node birth
errors are zero. The finest final temperature range is 350.066–402.598 K.
These are numerical verification tolerances, not a head/process accuracy claim.

## Reproduction and receipts

On an existing Linux host with the pinned extracted runtime, `bwrap`, a working
user systemd instance and coreutils `timeout`:

```sh
python3 -B twins/962-cylinder-head-f0/source/physics_witness/thermal_birth/run_local.py \
  --rootfs /path/to/existing/moose/runtime/rootfs \
  --output /path/to/fresh/thermal-birth-run
python3 -B -m unittest discover -s tests -p test_962_thermal_birth.py -v
```

The runner creates a new frozen contract, executes the three levels and applies
both checkers. It never installs or downloads anything. Each native command has
100 s, 2 GiB RAM, no swap, two CPU quota, a read-only runtime and no network.
It refuses reused output directories. Inputs, binary identity, native logs and
all output hashes are retained. Checkers require the native-bound contract and
artifact manifest and refuse to overwrite assessment files. The retained
original SSH runs also include the complete compressed stdout capture and its
hash. Native source revision is `167ee97da204df5e8643695e18b9b28910f0014b`;
binary SHA-256 is
`c49e2c368799d80edf9ff858dd8960bd22f5430f48229ab49dcc0afd27afcc5b`.

The local retained result is
`work/962-engineering/moose-thermal-birth-001/refinement-assessment-001.json`.
All eleven focused reference/rejection tests pass. The portable runner was
prepared from the exact successful native command; its `--help` was checked,
without repeating the passed native runs.

## Next whole-head execution

1. Admit the actual head volume mesh and its geometry-deviation evidence. Add
   explicit plate/support regions and interfaces; preserve source identity and
   the CAD-to-solver unit transform.
2. Bind material curves, orientation, treatment and temperature ranges to the
   chosen recipe. Explicit assumptions permit a conditional study. Powder,
   melting/latent heat and stress-free/annealing resets need declared models.
3. Map the declared build orientation, scan history and absorption into source
   functions and activation groups. Integrate absorbed power on the actual
   active volume. Report grouped-layer coarsening and its energy/time checks;
   a structural mesh does not resolve individual powder layers automatically.
4. Solve the whole declared thermal build/cooldown history, then use the same
   mapped temperature states for verified variable-law elastoplastic mechanics,
   supports and release. Preserve the continuous material/plastic history.
5. Audit energy, force balance, mesh/time sensitivity, field mappings and
   residual distortion. Keep conditional predictions separate from calibrated
   process and physical manufacturing qualification.

Primary pinned semantics:
[source shape and normalization](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/heat_transfer/src/materials/FunctionPathEllipsoidHeatSource.C),
[thermal source sign](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/heat_transfer/src/kernels/ADMatHeatSource.C),
[variable thermal properties](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/heat_transfer/src/materials/HeatConductionMaterial.C),
[capacity discretization](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/heat_transfer/src/kernels/ADHeatConductionTimeDerivative.C),
[activation and restored DOFs](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/framework/src/meshmodifiers/ElementSubdomainModifierBase.C).
