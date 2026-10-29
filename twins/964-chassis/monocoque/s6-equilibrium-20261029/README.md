# S6 force and moment equilibrium — 29 October 2026

**Executed numerical audit of the retained torsion and bending cases.** Both
cases now pass a global force-and-moment balance using the expanded 3D force
field. The complete printed displacements, original-node forces and
integration-point stresses are byte-identical to the 28 October replays.
Only output requests changed. This adds a numerical check, not stiffness,
strength, fitment or manufacturing qualification.

## Upstream admissibility

[admissibility.json](admissibility.json) was written **before** either full-size
solver launch. The retained input and DAT files were admitted by their frozen
SHA-256 digests. The geometry remains a drawing-derived envelope with modeled
sections, an isotropic carbon surrogate and synthetic load/support patches.
The audit is admissible for checking the existing solver's output completeness.
It does not admit a geometry/mesh parameter sweep or vehicle load validation.

The [model-year review](../../model-year-review-20261029/README.md) leaves two
P14 families open. The [interface survey](../../interface-measurement-plan.md)
still has zero validated XYZ anchors. Tunnel internal surfaces, moving and
removal envelopes, material allowables and complete 1,200 kg vehicle loads
remain absent. No missing interface was filled with a plausible coordinate.

## Why the original force balance was insufficient

CalculiX RF includes applied loads as well as reactions. It must be summed over
the complete selected force field; adding the applied forces again would count
them twice. The [CalculiX 2.21 manual](https://www.dhondt.de/ccx_2.21.pdf),
sections 7.96, 7.98 and 10.3.5, documents RF, expanded shell output and how shell
rotational constraints are transferred to the expanded structure. Expanded
node identifiers differ from input-deck identifiers.

The original DAT contains three force components at each of 173,420 original
nodes. Taking only `r × RF` there leaves a torsion moment residual of
`[3.084755, -0.231416, -2.579413] N.m`, despite a small force residual.
Those three components alone do not establish the encastre reaction moment.
This was an output-completeness gap, not evidence that changing the shell
shape would correct it.

[cantilever_witness.py](cantilever_witness.py) tests that distinction on an
explicit synthetic 100 × 10 × 2 mm S6 cantilever under a 1 N tip load. Its known
tip moment about the origin is `[-5, 100, 0] N.mm`. The 2D force field leaves
100 N.mm about Y; the expanded field recovers balance within its printed
precision. Both runs have identical DAT bytes. The
[witness receipt](witness.json) retains input/output hashes. These assumed
dimensions and isotropic properties are solver-test data, not Porsche data.

## Full-size results

[audit.py](audit.py) changes exactly the original `NODE FILE` and `EL FILE`
output block from 2D to 3D and adds RF. Every mechanical input and every DAT
request is preserved. Each new run is compared against the **complete** original
DAT digest, including all 790,200 integration-point records per case.

| Expanded-force result | Torsion | Bending |
|---|---:|---:|
| Expanded nodes carrying coordinates and RF | 474,449 | 474,449 |
| Norm of summed forces | 0.058850 N | 0.013940 N |
| Norm of summed moments | 0.034759 N.m | 0.008078 N.m |
| Relative force residual, before printing allowance | 2.9425e-5 | 6.9702e-6 |
| Relative moment residual, before printing allowance | 1.3472e-5 | 5.5211e-6 |
| Full DAT identical to the retained run | Yes | Yes |

Both force and moment residuals are below the **1e-4 numerical screen even
before using the printing allowance**. The executable audit and publication
test both require this unadjusted residual criterion. The [aggregate audit](audit.json) contains all three
components, reference scales, origins, uncertainty bounds and file hashes.

The origin is the mean of the original input coordinates. Force normalization
uses the sum of the magnitudes of the applied nodal forces; moment normalization
uses the sum of their individual moment magnitudes about that origin. They are
2,000.000056 N / 2,580,080.524 N.mm in torsion and 2,000.000002 N /
1,463,155.983 N.mm in bending. The small differences from 2,000 N come from
the six-decimal CLOAD serialization. These scales are documented numerical
references, not vehicle design loads or safety factors.

The FRD fields have fewer significant digits than DAT. Half-last-digit bounds
are propagated through each cross product, including the product of coordinate
and force bounds. They describe **serialization uncertainty only**. Worst-case
component bounds are deliberately conservative; they are reported without
claiming measurement accuracy. The unadjusted residuals above pass independently.
External work is reported as `sum(F · u)`; no independent strain-energy output
was requested, so energy correlation explicitly remains unverified.

## Reproduce and retain

Run from a checkout with NumPy, Docker and the existing CalculiX 2.21 ARM64
image `sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4`:

```sh
python twins/964-chassis/monocoque/s6-equilibrium-20261029/cantilever_witness.py \
  --output /private/path/new-cantilever-witness
python twins/964-chassis/monocoque/s6-equilibrium-20261029/audit.py \
  --torsion-source /private/path/964-monocoque-s6-replay-20261028 \
  --bending-source /private/path/964-monocoque-s6-bending-replay-20261028 \
  --output /private/path/new-s6-equilibrium
python -m unittest discover -s tests -p 'test_964_s6_equilibrium.py'
```

The source roots must contain the original `run-1/shell.inp` and `shell.dat`.
Output directories must not exist. Both sources are checked before execution
and again after execution. Each local container has one solver thread, two CPU
equivalents, a 12 GiB memory/swap ceiling, no network and a 900-second solver
deadline. Both full-size runs completed. No paid compute was used.

Raw solver fields, decks, meshes and logs stay in the private evidence release.
Only the executed scripts, numerical aggregates and their hashes enter Git.
The original replays, pinned sources and historical receipts are unchanged.

## Engineering consequence

The retained stiffnesses remain 19,899.782469 N.m/deg in torsion and
8,828.496848 N/mm in bending; identical DAT bytes make this a check of the same
solutions. This closes their global moment-output check. It does not establish
mesh or stress convergence, a laminate failure criterion, joints/inserts,
fatigue, crash performance or process qualification.

The next geometry step remains measured interface identification and tunnel
interior acquisition, retaining both P14 families. A subsequent composite
analysis needs a specified layup, material/process data and load transfer at
those interfaces. The completed numerical audit supplies no road, circuit or
TÜV acceptance.
