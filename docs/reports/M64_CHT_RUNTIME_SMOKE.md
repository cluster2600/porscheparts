# M64 — CHT software preflight, not a cylinder head simulation

Date: 2026-09-06. Status: **reference run succeeded after correcting the
tutorial; no physical or industrial validation of the M64**.

```mermaid
flowchart LR
    A["circuitBoardCooling tutorial<br/>OpenFOAM 14, 20 iterations"] --> B["First run: exit 136<br/>floating-point exception"]
    B --> C["Same relaxation factors moved<br/>into fields / equations"]
    C --> D["Full rerun: exit 0"]
    D --> E["Gas–solid energy chain runs"]
    E --> F["M64 cylinder head not simulated"]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
    class B,F stop;
    class D,E ok;
```

## Current scope — update of September 7, 2026

The current private body `four-seat-candidate.step` has **5,130 faces**,
SHA-256 `92640fd2ce03b1ffedf35b47063c50d150057ff2fdbac181b640236a0b5f596f`.
**It does not yet have approved thermal assignments or a computational volume
mesh.** The F53/F54 inventories and meshes concern other geometries and do not
transfer to its faces.

The result below remains strictly the historical software control case
`circuitBoardCooling`: neither this body nor its cooling has been simulated.
See the [cylinder head input status](M64_CHT_HEAD_INPUT_AUDIT.md) before preparing
a thermal case on the current geometry.

## Case and environment actually executed

- Kali, local amd64 image
  `sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17`.
- OpenFOAM Foundation 14, build `14-7b05503f98a8`.
- Tutorial shipped in the image:
  `/opt/openfoam14/tutorials/multiRegion/CHT/circuitBoardCooling`.
- `Allmesh-extrudeFromInternalFaces`, then sequential `foamMultiRun`.
- Air `perfectGas`, `Cp=1004.4 J/kg/K`, molar mass 28.96,
  viscosity 1.831e-5 Pa.s, Pr=0.705; solid `heSolidThermo` and heat source.
- Energy equations actually solved: `h` on the fluid side, `e` on the solid side.
- Fluid mesh 2,000 cells; solid `baffle3D` 800 cells.
  Both `checkMesh` runs return `Mesh OK`.
- Ephemeral Docker, network disabled, limit 2 CPU / 4 GB / 128 processes,
  `timeout 240`. No Vast rental, no other job modified.

The end control is reduced from 5,000 to **20 steady-state iterations**, with
a write at 20. The `Time = 20s` entries in the log therefore do not represent
20 physical seconds of transient cooling.

## Initial failure and justified correction

The first attempt is kept on Kali under
`/tmp/m64-cht-smoke.IQcI1i/case`: exit 136, floating-point exception at iteration 2
in `GAMGSolver::scale`, fluid region. From iteration 1, `k` is bounded after
a minimum value of -6987.92. The initial state is T=300 K, p=100000 Pa,
p_rgh=0 Pa: this is not a zero initial absolute pressure.

The log reports `Neither fields nor equations specified`. The tutorial
contains relaxation factors in a flat structure. The code of this
version, `src/OpenFOAM/matrices/solution/solution.C`, lines 50–71, expects the
sub-dictionaries `fields` and/or `equations`; these factors were not taken
into account.

A single numerical correction was tested in a separate copy: placing
the **same factors** in `fields` (rho=1, p_rgh=0.7) and `equations`
(U=0.3, h=0.7, turbulence=0.3). No convergence threshold or physical property
was made more permissive. The exception disappears and the 20 iterations
complete. The first wrapper also had an `^End` check that was too strict
for the indented output; this text check was corrected and a complete
repetition of the case returned **0**.

## Reproducible result and limits

Last repetition: `/tmp/m64-cht-smoke.kOKWNE/case` on Kali.

| Internal field at iteration 20 | Minimum | Maximum |
|---|---:|---:|
| T air, 2,000 cells | 300 K | 306.374 K |
| T solid, 800 cells | 317.168 K | 428.410 K |

The initial residuals of h (~0.00313) and e (~0.00105) at iteration 20 remain
above the tutorial's convergence criteria. **This result only establishes
that the gas–solid chain with energy runs**, not its global convergence,
its mesh independence or a qualified energy balance.

SHA-256 of the final log:
`656d92a4ffb393c2bc6c427ca36a561934b1e43f7e475a47a0d137d94d213cf2`.

SHA-256 of the fluid T field:
`3951e69bb308f001d4691b3f9792fa1ae5d7ca3e42c5ed5e3517e556463b6474`.

SHA-256 of the solid T field:
`d7c9fb57b0aa1b084fffbacaafdb1dd23ca192fb6f2b37d23821ec82ce6a3a5c`.

The script `twins/m64-cylinder-head/run_cht_runtime_smoke.sh`
runs in the image with a fresh directory mounted on `/output` and the argument
`repair-relaxation`. Without this argument it reproduces the initial failing
configuration. Local `bash -n` check passed; actual Docker run succeeded.

The cylinder head, its fins, its M64 interfaces, the turbo and the oil circuit
are **not** part of this case. No strength, fatigue, printing, Omniverse or
certification result follows from it. The next steps
remain the M64 geometry, its sourced boundary conditions, CHT convergence,
the flux balance and comparison against relevant references or tests.
