# Parallel re-reading of the exact admissions

`build_cached_v6.py` keeps the private v5 builder, the declared authorities
943/5047 and the six checks of `admissions_v3.py`. Only the re-readings of the
planar units go into a pool of four processes, with at most eight futures.
Results and refusals are returned in their original order.
No generator, recipe or old evidence file is modified.

The parent captures its runtime identity before the pool; each worker requires
the same identity at its initialisation. After shutdown, the parent recomputes it.
The two digests must be identical and are required when the directory is
reused. This check computes no per-unit runtime hash. Shutdown
waits for tasks already launched and cancels tasks still pending; it
does not promise to interrupt immediately a rational computation in progress.

## Three results to distinguish

- The historical benchmark with class **814** processed the skin of
  5,876 vertices in **324.729 s**. Its receipt remains historical.
- The [isolated area-reuse trial](combinatorial-evidence/ring-area-reuse-experiment-001.json)
  measured **238.350 s**, with identical WKB, complete receipt and statistics.
  The machine's concurrent load was not controlled: this report guarantees
  no duration gain. Its `adopted=false` entry describes the state of this trial.
- The new v6 workers use the editable copy
  `incremental_combinatorial_interfaces_area.py`, SHA
  `2230847e5862b3d6668a900c2774ebb82cb3f12555486747fb06dfe8d5a90341`.
  It changes only one expression of 814: `ring_area=sum(areas)` reuses
  the rational areas already computed before the cycles are reordered.
  The hook and the execution receipt declare this implementation separately;
  they relabel no earlier authority or result.

Optional reuse is limited to the **four real results already
verified for regions 003/009**, produced by 814. Their receipt, plan, runtime,
producer checkpoints, data and results must match exactly.
A discrepancy refuses the reuse; it does not trigger a silent reconstruction.
This is not a general cache. The tests verify these four results
without submitting them to a worker.

## Commands and evidence

The CLI keeps the v5 arguments and adds only
`--proven-unit-replays CHEMIN_ASSESSMENT`. This optional path designates the exact
historical receipt SHA `62082815b2e78ee66c11f91818f2f63c46b180f75664ede6f7ef602f9a57a432`,
accompanied by `frozen-plan.json` and `runtime-before.json`. These three raw
files remain necessary to use these four historical results.
Without this option, the units are re-read by the new workers.

The new directory contains `exact-admission-replays.json`, linked to the six receipts
and to the checkpoint. The wrapper keeps and re-verifies this link after the copy
made by the CORE. `--reuse-support-stage` requires a complete v6 directory;
an old v5 directory and a combination with `--proven-unit-replays` are refused.

From the repository root, the targeted software witnesses are replayed with the
pinned PySLM runtime:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p test_carrier_parallel_exact_admissions.py -v
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p test_carrier_cached_build_v6.py -v
```

The [implementation receipt](combinatorial-evidence/parallel-admissions-implementation-002.json)
keeps the digests and the logs: **7 helper tests + 8 driver tests
pass**, including 21 small units actually re-read up to the six receipts of a
synthetic witness. The earlier regression of 34 driver tests is
identified as prior to the final runtime guard. The two JSON files associated
with this notice are exact copies of the kept receipts, without rewriting.

This verification concerns the software. No complete admission of the real
supports, no new generation and no costly benchmark were
run by the new driver for this checkpoint.
