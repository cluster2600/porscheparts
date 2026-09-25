# M64 — incomplete local size trial

Next trial: [native fields and detailed log](M64_NATIVE_SIZE_TRIAL_20260909.md).
This document keeps the historical result of the Python callback.

**The native computation stops with no new candidate mesh and no final report.
No quality gain is established and no geometry is promoted.**
The Porsche contour and the master remain unchanged.

This batch tests the avenue announced after the
[previous joint remesh](M64_EDGE82_JOINT_REMESH_20260909.md): same edge 82
recipe, then a 2D size field limited to faces 30/37, around vertex 51 and the
two small segments of edge 99.

## What is established

- A single native launch on Kali, four CPUs, 4 GiB; no Vast rental.
- Temporary 1D generation checkpoint reached at 1.098 s from the start of the
  worker. Same 64-node profile, last segment 82 / neighboring segment 93 =
  0.96736.
- Reinjection verified at 7.587 s from the start of the worker. The reinjected
  file is byte-for-byte identical to the reference `7af7f207…`.
- Process ended with code **152**, after **239.935 s including cleanup**.
  This code is consistent with `SIGXCPU` (`128 + 24`) under the CPU limit
  configured at 240 s soft / 250 s hard of cumulative process CPU time,
  distinct from the wall-clock timeout. This is a consistent attribution, not
  an independent receipt of the signal. No wall-clock timeout overrun and no
  OOM is reported.
- Exact container deleted; absence rechecked. Inputs and launcher unchanged.

## What is missing

The last checkpoint precedes the installation of the callback and the 2D call.
It still reads `generate2_calls = 0`: this is its state at that moment, not
evidence that the call never started afterward. There is no raw/candidate
MSH, no final report, and no saved callback call counter. The final removal of
the callback is therefore not attested, even though its `finally` path is
tested in software; the process was stopped.

The final qualities, final preservation and contacts are **unknown**, not
zero. The independent cross-reader is ready, but is not run without a
candidate. No three-state numerical comparison is possible for this batch.

The prepared field uses a size growth of 0.25 per unit of distance and lowers
the floor to the smallest source segment of 99. These numbers are mesh
settings, **not manufacturing dimensions**. The code restores the 63 line IDs
of 82 from the previous candidate through a bijection of records; this
restoration is checked by pure reading before the trial, but no final output
allows confirming it here after the computation.

## Next steps and limits

Before a rerun, explicitly instrument the entry into 2D generation and save a
bounded progress record of the size calls. The cost must be located before
choosing between a native field, a different setting and a higher CPU budget.
The absence of a result proves neither a memory shortfall nor that a GPU would
solve the problem. Do not rerun the same unchanged inputs while claiming that
a quality gain has already been obtained.

The **52 distinct software tests** pass: 22 worker, 10 launcher, 7 cross-reader
extension and 13 frozen parent. They check the software, not the strength of
the cylinder head. The digests and explicit unknowns are in the
[evidence register](../../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json),
entry `gas_local_2D_size_trial`. `make check` ends with code 0; optional tests
are skipped depending on the available dependencies.

The [engine stack in the photo](M64_MULTIPHYSICS_EXECUTION.md) remains
relevant, but is not an already validated coupled chain: Elmer is a candidate
for cross-computation, PhysicsNeMo a model to train/evaluate and Ditto/MQTT a
future link to measurements. No CFD, thermal, mechanical, LPBF, engine power
or manufacturing result is credited by this batch.

```mermaid
flowchart LR
    A["Unchanged reference"] --> B["1D completed, then identical reinjection"]
    B --> C["Next phase with no intermediate trace"]
    C --> D["Stop with code 152; no candidate"]
    D --> E["Cleanup verified; incomplete result"]
    E --> F["Instrument and profile before rerun"]
```
