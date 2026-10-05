# D2: prepare the twenty missing iterations

**Preparation history.** The [1001–1020 restart is now complete](D2_COMPLETION_EXECUTION.en.md)
after explicit approval, in 110.505 s overall. Pressure remains unadmitted,
the comparison inconclusive and resources released. The prepared protocol
below and its criteria are retained without changing its frozen artifacts.

**Verified preparation, no solver launched, no resource reserved.**
The [initial D2 batch](D2_EXECUTION.en.md) remains closed and its results unchanged.
The control completed 961–1020; only the extended branch concerns this proposal.
The objective is to finish the comparison truncated by its budget at **1020**,
without an automatic extension to obtain admission.

## Native state actually available

The [private checkpoint audit](results/runtime/D2-restart-checkpoint-audit.json),
performed on October 4, 2026 at 20:46:51 UTC without a solver or reconstruction,
verifies **980 and 1000 complete on all four partitions**. Each partition
contains `p`, `U`, `k`, `omega`, `nut`, `phi`, `Uf` and `uniform/time`.
Volumetric fields cover 680 596 cells, with 122 709 / 167 115 / 208 232 /
182 540 cells per rank. Face-field cardinalities are checked against the
native mesh; values are finite. The four indices and times saved at 1000 agree,
`deltaT = deltaT0 = 1`.

The selected checkpoint is **1000**, the latest complete one: 32 native files,
152 261 842 bytes. The serial root contains only 960; no 1001 or 1020 checkpoint
exists. The old log's incomplete start of iteration 1001 is not a restartable
state. The parallel restart will use existing 1000 fields, never a state
reconstructed from integrals.

The [preparer](source/prepare_d2_restart1000.py) actually created a separate
private copy of the mesh, configurations and four 1000 partitions.
The [preparation evidence](results/runtime/D2-restart-preparation-receipt.json)
checks SHAs and sizes before and after copying. Final portable code prepared
this copy in **0.580 s**; an earlier provisional copy was also retained.
No solver, `reconstructPar`, `decomposePar` or container was executed for this
preparation. Native files from the closed batch are preserved. The
`1000/uniform/time` marker at the copy's root is used only by the summary helper;
it is not presented as complete serial fields.

## Proposed fixed restart

The [completion protocol](parameters/D2-restart1000-protocol.json) requires
**one branch, four ranks, exactly 1001–1020**, one solver call. The complete
control is reused read-only. No new mesh, partitioning, geometry, MRF zone,
speed, boundary condition, scheme or threshold. The outlet remains extended
by 275 mm in fifty layers, with the same 453 496-cell core and common selections.

The [prepared controlDict](parameters/D2-restart1000-controlDict) is byte-identical
to the actually executed native control except `startFrom startTime` and
`startTime 1000`. `endTime 1020`, `deltaT 1`, saving every 20 steps,
`purgeWrite 0` and measurements every iteration are retained. The static
check reconstructs those two substitutions and recovers the original native
file's SHA. Restart effectiveness still requires verification in future
execution: first step 1001, twenty consecutive complete steps, `End`
termination, finite native tables and a complete 1020 checkpoint are mandatory.

Reproducible preparation, with private paths supplied explicitly:

```sh
python3 source/prepare_d2_restart1000.py \
  "$D2_NATIVE_EXTENDED" "$D2_NATIVE_CHECKPOINT_AUDIT" \
  parameters/D2-restart1000-protocol.json \
  parameters/D2-restart1000-controlDict "$D2_PRIVATE_PREPARED_CASE"
```

This command copies and verifies files; it launches no calculation.
The only planned numerical commands, **to be supervised in the existing
isolated runtime after explicit coordination**, are:

```sh
mpirun --bind-to none --use-hwthread-cpus -np 4 foamRun -parallel
reconstructPar -time 1000,1020
```

These two commands are not an authorized standalone launcher. The historical
`launch_d2.py` launcher prepares and reruns a pair, so it does not suit this
single restart. Before execution, this batch's supervisor must enforce the
overall ceiling below, preserve evidence and terminate only its own
process/container. It must use a **new deadline**, never the expired deadline
of the 720 s batch. No installation, image download, rental or service change
is necessary.

The [dedicated supervisor now tested and executed](source/launch_d2_completion.py)
applies this contract to one branch; its
[exact capsule](parameters/D2-completion-executed-capsule-manifest.json) and
evidence appear in the final report. Earlier passages about pending adaptation
describe the preparation state before the batch.

## Observed cost and proposed budget

The extended branch's native log gives `ExecutionTime = 81.138094 s` at 980,
then `155.099948 s` at 1000: **73.961854 s for twenty iterations**, or
approximately 3.70 s/iteration. Rounded `ClockTime` values give **75 s**.
This measurement includes saving 1000. The maximum increment in this window
is 4.869 s. Partition imbalance is retained; no linear estimate based only on
cell count replaces this measurement.

| Future stage | Estimate / evidence | Proposed ceiling |
|---|---|---:|
| Fresh admission, identity and isolated copy | Final copy measured 0.580 s; preceding complete audit 10.174 s | 30 s |
| Twenty iterations 1001–1020 | Estimated 75–80 s with restart, last 20 measured at 75 s | 110 s |
| Reconstruction 1000 and 1020 | Control: three checkpoints reconstructed in 11.480 s; extended estimate 15–25 s | 25 s |
| Summary, windows, fields and comparison | Estimate, no measurement of this future batch | 30 s |
| Archiving, verification and release | Previous final archiving/verification 6.389 s; increased reserve for this batch | 45 s |
| **Overall, without reset** | **Estimated nominal 120–180 s** | **240 s** |

This budget is **proposed, not started**: at most 4 CPU, RAM+swap 5 GiB,
no networking, niceness 10, same already available Foundation 13 image.
Load, RAM and coordination must be checked immediately before launch.
No implicit reservation is maintained during preparation. The budget
guarantees neither convergence nor archiving time; an overrun preserves the
partial state and ends the batch without another trial.

## Analysis and stop rule

The [original criteria](parameters/D2-executed-configurations/protocol.json)
are copied unchanged into the proposed protocol. The final window must contain
twenty consecutive measurements 1001–1020. It is compared to the native
981–1000 window; core RMS, local p99/max and backflow are evaluated on actual
1000 and 1020 checkpoints. Common pressure: dispersion ≤2 Pa, difference
between window means ≤2 Pa and core pressure RMS ≤1 Pa. Maximum initial p
residual ≤10⁻⁴; other numerical, velocity and stability thresholds remain
mandatory.

The previous pressure-steadiness failure remains documented.
**Even with twenty complete additional iterations, unsteady pressure rejects
admission.** The physical domain comparison remains inconclusive if any
numerical or steadiness prerequisite fails. The batch stops at 1020 in all
cases; no threshold is relaxed and no 1040 continuation is planned. Eventual
admission would qualify neither local fields, general domain independence nor
installed cooling.

Retain separately the old native log with 40 complete steps plus the start
of 1001, the new 20-step log and their tables. A composed analysis view, if
needed, must be identified as derived: remove only the incomplete 1001 block
from the old view, check equality of measurements at the 1000 checkpoint
before deduplication and retain both source SHAs. Never present that view as
one native log. Future fields and meshes remain private; only original scripts,
parameters and sanitized reports may be published.

Verification without a solver: `make fan-program-check`. Five new tests reject,
among other things, a missing surface field, nonfinite pressure, mixed times,
extra steps and control replay. Initial D2 results, their capsule, archives
and earlier validations remain unchanged.
