# M64 — native size field: remeshing still incomplete

Follow-up run: [hybrid assembly and OpenFOAM check](M64_HYBRID_OPENFOAM_20260909.md).
The historical result described below remains unchanged.

**Replacing the Python callback with native Gmsh fields does not complete
the remeshing within the set budget. No new candidate and no quality
gain is established. The Porsche contour and the master remain unchanged.**

This trial follows the [incomplete callback](M64_LOCAL_SIZE_TRIAL_20260909.md).
The inputs are the same, with a native helper added and pinned by SHA.
A single launch on Kali: four CPUs, 4 GiB, no new Vast rental.

## What changed

The size law is expressed by five Gmsh 4.15.2 fields:
two `MathEval`, two `Restrict`, then one `Min`. It limits the size
around vertex 51 on faces 30/37 and around the two segments of
edge 99 on face 37 only. The distance to the segments is analytic,
not a distance to the continuous CAD curve.

The 0.25 slope, the profile of edge 82 and the size floor are
kept. It is the same intended mathematical law; the order of the floating-point
operations differs, so no binary identity with the callback is
claimed. No Python size callback is installed.
These parameters describe the mesh, not manufacturing dimensions.

The code checks the fields before generation and plans their removal
afterwards. It now logs the phases and the native Gmsh output.
The software tests alone do not prove the native evaluation of the field.

## Observed result

| Step | Wall time since worker start |
|---|---:|
| Temporary 1D profile verified | 1.100 s |
| Source mesh reinjection verified | 7.584 s |
| Replacement of 82 conforming to the reference records | 9.521 s |
| Field installation and re-reading reached before 2D generation | 9.531 s |

The reinjection produces exactly the source SHA `7af7f207…`.
The log then confirms the remeshing of faces 30 and 37. On 37,
Gmsh successively reports **8, 18, 12 then 6 invalid elements**,
self-intersections of the 1D mesh and retries with refinement of the bounding
edges. These numbers are intermediate states, not a final result
nor a demonstrated convergence. The log does not prove physical
intersections of the cylinder head.

The process exits with **code 137**, after **250.146 s including cleanup**.
This is consistent with `SIGKILL` under the hard CPU limit of 250 s; it is
not an independent receipt identifying the cause of the signal. The soft limit
is 240 s of cumulative CPU; the Python signal handler can be delayed
during a native call. No wall-clock timeout or OOM is reported.

The exact container was deleted and its absence re-verified.
The twelve inputs, the worker and the launcher are unchanged.
**No raw/candidate MSH and no final worker report was saved.**
Field removal, final edge preservation, contacts and
final quality are therefore not attested. The counter-reader is not
run without a candidate. No speed-up factor can be computed
from these two unfinished trials.

## Decision and useful next step

Do not repeat this same trial with more CPUs while promising a gain.
The native path still hits the face 37 meshing retries:
the cost cannot be attributed to the Python callback alone.

The historical bound minimum `0.888285…` on face 30 is **not**
a physical requirement for 700 hp. The theoretical bound and the diagnostic
threshold `0.1` remain tracking indicators; they replace
neither the conformity of the domain nor the checks of a finite-volume mesh.
Earlier rejections remain on record, with no silent lowering of a guard.

The next step is a diagnosis of the **complete hybrid domain**:

1. Reassemble on a copy the core `e873b8ae…` with the 67,200 hexes and
   384 pyramids kept, checking the connections and the labels.
   The 1,536 lateral triangles of the pyramids must become internal,
   never artificial walls.
   Do not incorporate the surface drivers `7af7f207…` or `2de5fd52…`:
   they no longer match the fixed boundary of core `e873b8ae…`.
2. Export the complete domain as MSH 2.2 ASCII and assign the groups
   `inlet`, `receiver_outlet`, `walls`, `air` from the source evidence.
   The core alone does not represent this domain.
3. Use the existing `check_openfoam_mesh.py` path, without a solver:
   conversion, hypothetical scale 0.001 m/unit applied only once,
   patches, then `checkMesh -allTopology -allGeometry`.
   Its receipt must attest this exact mesh and its boundaries, without inventing
   a CFD authorization. The supervisor must limit the total time.

These three steps are not run by this batch. A possible
`Mesh OK.` would remain a numerical diagnosis, not a validation of the
M64 interfaces, the twin-turbo loads, the strength or the printing.

The **42 distinct software tests** pass: 21 worker, 11 native fields,
10 launcher. `make check` ends with code 0; optional tests are
skipped depending on the available dependencies.
The [evidence register](../../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json),
entry `gas_native_2D_size_trial`, keeps the digests and the unknowns.
The [stack in the photo](M64_MULTIPHYSICS_EXECUTION.md) does not change these limits:
Ditto/MQTT await bench measurements; PhysicsNeMo awaits computations
eligible for its training and evaluation.

```mermaid
flowchart LR
    A["Reference unchanged"] --> B["Native fields installed"]
    B --> C["Repeated retries on face 37"]
    C --> D["Exit 137; no candidate"]
    D --> E["Trial archived; no gain credited"]
    E --> F["To do: reassemble<br/>the hybrid domain"]
    F --> G["To do: OpenFOAM check<br/>without solver"]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
    class D,E stop;
    class F,G open;
```
