# D2 establishment and discriminating D3 trial

The [diagnosis of preserved fields and logs](results/cfd/D2-establishment-diagnostic.json)
is complete without a new solver, mesh modification or criteria change.
The initial 960 files downloaded read-only match the hashes of the executed
D2 preparation. States 1000/1020, tables and logs come from the already
verified native archives; they remain private.

## What motivates the next trial

At the 960 start, the fifty added layers repeat outlet-cell velocity, with
zero pressure throughout the extension. Fluxes at all 51 planes are identical.
This initialization retains flow; it does not establish momentum equilibrium
in the added domain.

From 960 to 1000, pressure RMS variation is 38.34 Pa in the core and 86.63 Pa
in the extension; from 1000 to 1020 it is still 10.35 / 14.40 Pa. Velocity RMS
variation from 1000→1020 is 0.382 / 3.056 m/s. These results indicate continuing
establishment, without causally isolating the initialization's effect.

The first initial p residual decreases from 0.241 to 0.00538 over the 60
complete iterations; over the last 20 it decreases by a factor of 1.985.
All 180 linear pressure solves meet their `relTol=0.01`: their maximum
final/initial ratio is 0.009979. Common-pressure extrema decrease with
iterations, but [D2 steadiness and admission fail](D2_COMPLETION_EXECUTION.en.md).
The matrix residual is not a physical pressure error.

At 1020, gross backflow represents 9.27 % of net flux at the common plane,
approximately 11.8 % midway along the extension and 10.82 % at the outlet.
Extension alone therefore did not remove backflow. Slip side walls and this
buffer's constant section do not represent an installed plenum.

## Why not launch a transient calculation directly

Added volume divided by net flow is 14.35 ms, or 1.435 revolutions at 6000 rpm.
This is a nominal transit time; backflow prevents interpreting it as a
residence-time bound. SIMPLE iterations have no physical duration. The solver
contains a time term whose role depends on the selected scheme; the current
calculation uses `steadyState`.
[OpenFOAM 13 solver source](https://github.com/OpenFOAM/OpenFOAM-13/blob/master/applications/modules/incompressibleFluid/momentumPredictor.C).

The diagnosis independently reconstructs volumes from native faces:
680596 positive volumes, with a maximum absolute core difference of
3.31×10⁻²² m³ against already checked volumes. For native MRF flux,
`Co=dt Σ|phi_face|/(2V)` gives a maximum rate of 3.15×10⁷ s⁻¹ and an indicative
`Co≤0.5` step of 1.59×10⁻⁸ s. This represents 630014 steps per revolution.
The limiting cell has a volume of 1.37×10⁻¹⁵ m³; the rate's 99th percentile
is also high, at 1.15×10⁷ s⁻¹. Passing the mesh check therefore does not
guarantee its cost or quality for a transient calculation. This estimate is
neither a selected time step nor evidence of physical unsteadiness. A relevant
transient calculation would first require study of small cells, the time
scheme and cost, followed by enough revolutions to measure establishment.

## D3: twenty iterations per branch, same 1020 state

The [two private cases are prepared and verified](parameters/D3-prepared-relaxation-protocol.json).
Each branch restarts the same 28 native fields and four time markers on the
four original partitions. No remeshing, decomposition or reconstruction was
launched. Fields, geometry, boundary conditions, MRF 6000 rpm, turbulence,
schemes and solvers remain identical.

| Branch | p relaxation | Planned work |
| --- | --- | --- |
| `control015` | 0.15, unchanged | 20 iterations 1021–1040 |
| `candidate005` | 0.05 | 20 iterations 1021–1040 |

Only `system/fvSolution` differs between branches, and only in this value.
Their identical time control requests exactly 20 steps and native tables at
every step. The 1020 identity is not rewritten to 0.

Compare at equal work: decay of the first p residual and maxima of every
residual, common-pressure mean/standard deviation, volumetric p/U variations
from 1020, flow, torque, backflow and extrema. Lower variance with a larger
residual or drift indicates only slower evolution; it justifies no admission.
A change in phase or amplitude with α would inform numerical sensitivity,
without proving a real transient phenomenon. Original numerical criteria and
steadiness thresholds are retained. A still-inconclusive result will be
archived without automatic extension or blind repetition.

**Budget to coordinate before launch:** two sequential solvers, at most four
CPU, RAM+swap 5 GiB, networking disabled, already available OpenFOAM 13 image.
The overall 360 s ceiling includes preparation 30 s, solvers 90 s each,
reconstruction 40 s, analysis 45 s, preservation 60 s and release 5 s.
The last 20-step batch consumed 110.5 s overall, including 67 s of solver time;
the budget is a bound, not a completion guarantee. Phase limits share one
global deadline. At the preparation stage described here, a checked D3
supervisor still requires assembly/admission before execution; protocol solver
commands are not an authorized launcher. No D3 job is launched and no server
slot is reserved.

## Reproduce preparations without launching a calculation

Private inputs are native D2/D2-completion archives, the 960 checkpoint and
common selections. `PRIVATE_FAN_WORKSPACE` denotes a private directory external
to published content. With dependencies already present:

```sh
python3 source/diagnose_d2_establishment.py "$PRIVATE_D2_CASES" "$PRIVATE_D2_COMPLETION/extended" "$PRIVATE_D2_SELECTIONS" "$PRIVATE_FAN_WORKSPACE/diagnostic.json" "$PRIVATE_FAN_WORKSPACE/centers.npz"
python3 source/prepare_d3_relaxation_pair.py . "$PRIVATE_D2_COMPLETION" "$PRIVATE_FAN_WORKSPACE/D3-pair"
```

The [diagnosis code](source/diagnose_d2_establishment.py) and
[D3 preparer](source/prepare_d3_relaxation_pair.py) record hashes.
Raw scan, native fields and CFD coordinates remain private.
[Assembly and manufacturing, pursued independently](ASSEMBLY_MANUFACTURING_S1.en.md).
