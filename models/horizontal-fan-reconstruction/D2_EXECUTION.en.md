# D2: extended outlet, closed batch and inconclusive comparison

**Control completed; extended outlet partial; resources released.** The
[prepared protocol](OUTLET_SENSITIVITY_PREPARATION.en.md) was retained: same V2
rotor, `SIMPLE.consistent yes`, 275 mm extension towards −Z, 50 uniform 5.5 mm
layers, no distance or iteration increase after observing results. The
[audited comparison](results/cfd/D2-partial-pair-analysis.json) rejects steady
admission of the pair. No airflow gain, domain independence, qualified local
field or installed validation is established.

## What actually ran

Five preliminary geometry tests pass: core connectivity/volumes, added prism
volume, flux, orientation, written zones and field mappings. Native vector
table checks and partial-window rejection then bring the suite to seven tests,
explicitly rejecting partial admission or missing fields.

The [mesher](source/append_outlet_prisms.py) adds 227100 prisms: 680596 cells
against 453496. Rotor, its faces, core points and IDs, neighbours and MRF
membership are retained. Added volume is 0.016591727271 m³, equal to outlet
area × length; minimum added volume is 4.37078e−8 m³. Maximum core volume
difference is 6.35275e−22 m³. [Preparation evidence](results/cfd/D2-mesh-preparation.json)
links mesh, initial field and private selection hashes.

**Both meshes pass independent standard and extended checks, zero failures,
unchanged thresholds**: [control](results/cfd/D2-current-independent-mesh-gate.json)
and [extended](results/cfd/D2-extended-independent-mesh-gate.json).
[Observables at 960](results/cfd/D2-seed-observables-verification.json), calculated
without another iteration, reproduce the three zone pressures and original
oriented flow to output precision. The functionObjects fragment syntax was
corrected before launch: Foundation13 uses `faceZone` and `cellZone`, rather
than `regionType/name`.

A first preparation stopped **before any CFD iteration**: manual decomposition
`dataFile` required a quoted string. This [first attempt](results/runtime/D2-first-execution-receipt.json),
its capsule and archive are retained. Syntax correction and the `faceZoneList`
header were frozen in a second capsule. The original timer was not reset.
Manual assignment follows [Foundation13 code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/parallel/decompose/decompositionMethods/manual/manual.C).

Original core partition across four ranks is verified exactly in both cases.
Columns belong to the owner rank of their former outlet face.
[Extended counts](results/cfd/D2-extended-partition-verification.json) are
122709 / 167115 / 208232 / 182540 cells: preserving ownership induces imbalance
without redistributing the core.

The [runner](source/run_d2_in_container.py) then executes two sequential
branches from the same private `consistent yes/960` state:

| Case | Complete iterations | Native tables including state 960 | Final state |
|---|---:|---:|---|
| Current outlet | 60, 961–1020 | 61 rows per table | `End`, complete fields, reconstruction 980/1000/1020 |
| Extended outlet | 40, 961–1000 | 41 rows per table | 1001 started then interrupted; no `End` or field 1020 |

The control uses 118.731 s solver time. The extended branch actually has
**159 s** until the closure reserve of the original deadline; it stops cleanly
with timeout code 124 after 160.030 s including signaling/stopping. The 300 s
limit was a maximum subordinate to the global timer. No missing iteration is
extrapolated or added.

## Steadiness criteria and common differences

The [control1020 summary](results/cfd/D2-current1020-flow-summary.json) passes
**ten original criteria**; window 1001–1020 contains twenty consecutive
measurements. Its **seven additional checks** also pass: flow and band pressure,
window differences, field RMS from 1000→1020. Volume-weighted Δp RMS is
0.28765 Pa, ΔU 0.04178 m/s. Local maxima nevertheless reach 122.284 Pa and
48.196 m/s: passing global criteria still does not qualify local fields.

The extended branch entirely lacks the required 1001–1020 window and final
fields. At 981–1000 its maximum initial p residual is **0.0277275** against
0.0001; U reaches 0.00409826 against 0.00001, k 0.00797796 against 0.0001.
Band pressure standard deviation is **11.795 Pa** against 2 Pa, and its mean
changes from 138.957 to 97.745 Pa between available windows. It remains
numerically unadmitted and unsteady under planned checks. Residuals normalized
on different domains do not measure a physical domain effect.

The only paired twenty-measurement comparison available, **981–1000**, is
**descriptive**:

| Quantity in the common region | Current outlet | Extended outlet | Difference |
|---|---:|---:|---:|
| Mean oriented flow [m³/s] | 1.152299531 | 1.149390387 | −0.25246% symmetric relative |
| Mean fluid torque on rotor [N·m] | −3.867153957 | −3.842874987 | 0.62783% in absolute magnitude |
| Volume-weighted mean static pressure [Pa] | 85.644954 | 97.744930 | +12.099976 Pa |

Power follows the same relative change as torque at fixed speed. Pressure is
from the **same 5825 cells**, not a port pressure rise. Its difference exceeds
the 5 Pa screening band, but pair steadiness prerequisites fail. Domain
comparison gates **are therefore not evaluated as an admission**.

Actual saved fields at 1000 show common Δp RMS 38.337 Pa, ΔU 1.284 m/s and
maximum Δp 514.162 Pa. These describe an unconverged iterative state, not a
qualified steady outlet effect or experimental uncertainty.

![Native traces: control60 and extended40](results/cfd/D2-native-traces.png)

The [script](source/plot_d2_native_trace.py) and
[provenance hashes](results/cfd/D2-native-traces.json) retain every actually
complete point. The axis shows steady solver iterations without a physical
frequency or duration; no extended curve continues after 1000.

## Actual backflow retained at 1000

Extended MPI1000 fields are read by global IDs without another solver or
`reconstructPar`. Five fields cover 680596 cells exactly once. The 4542 common
plane faces are covered once and their phi reproduces the native functionObject
sum.

| Location in saved state 1000 | Net flow [m³/s] | Gross backflow [m³/s] | Backflow / net |
|---|---:|---:|---:|
| Control, current outlet plane | 1.152299642 | 0.123988412 | 10.7601% |
| Extended, same plane now internal | 1.151545816 | 0.104273570 | 9.0551% |
| Extended, distant boundary | 1.151530127 | 0.129404559 | 11.2376% |

Moving the outlet has not eliminated backflow in the available state. This one
partial extension proves neither sufficient distance nor domain independence.
The constant-section buffer with `slip` sides retains confinement and mixing;
it is not a measured engine plenum.

## Closure, preservation and reproduction

Verified limits: **4 CPU, RAM + swap 5 GiB, no network, private sources read
only**. [Native global time](results/runtime/D2-native-archive-verification.json)
is **627.669 s**, including first preparation, correction under the original
timer, restarts, stopping, audit and archiving, below 720 s. The container is
released at **20:09:21 UTC**; [existing services are unchanged](results/runtime/D2-release-confirmation.json).
No additional calculation, installation, persistent access or service change.

Final private archive: 99 verified members, 189782229 bytes; the first attempt
archive was also transferred and verified. Complete tables, meshes and fields
remain private. The launcher excludes `processor*` replicas from its archive;
extended fields1000 and mappings were therefore recovered **separately after
release** as file preservation without another native phase. The
[supplementary certificate](results/runtime/D2-partial1000-preservation-verification.json)
covers 44 verified private files. Their assembly by IDs supports diagnosis1000;
it does not reconstruct missing checkpoint1020.

[Exact capsules](parameters/D2-executed-capsule-manifest.json) and
[first preparation](parameters/D2-first-preparation-capsule-manifest.json) retain
frozen configurations and sources. Complete pair analysis was never reached.
Native force vector table reading was subsequently corrected and tested in the
current helper without modifying the executed capsule. Partial-batch analysis
uses [a separate script](source/analyze_d2_partial_result.py).

Verification without a solver: `make fan-program-check`. Reproduce statistics
and figures using the same scripts with extracted private native archives.
The launcher requires explicit coordination and must not rerun against its
expired original deadline. **This report neither authorizes nor starts a
continuation.** Any new study requires a budget and protocol defined before
calculation. 935/993 identity, installed interfaces, compressibility, walls,
fatigue and physical validation remain open.

Follow-up: native checkpoints980 and1000 are now audited and a
[fixed twenty-step completion](D2_COMPLETION_PREPARATION.en.md) is prepared. That
preparation launched no solver and does not change this closed batch's results.

Later follow-up: after explicit agreement, the
[single1001–1020 restart completed](D2_COMPLETION_EXECUTION.en.md) in110.505 s
including archiving and release. The missing window now exists, but pressure
remains unadmitted and comparison remains inconclusive. Partial results and the
first batch capsule remain preserved.
