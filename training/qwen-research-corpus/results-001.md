# Local Qwen research pilot: 2 October 2026

The local LoRA run completed 320 steps. Exact research validation improved
from **0/10 to 6/10**, while the small native OpenUSD/PicoGK retention sample
remained **16/16**. The candidate **failed its registered research gate** and
remains experimental. The final eight research tests were not evaluated.

The [metadata receipt](results-001.json) records hashes, settings, scores and
limitations. The private run directory is
`private/pilot-001`;
it retains answers, native witnesses, training logs and the separate adapter.
Raw articles, training exports, answer text and weights are outside Git.

## Model and actual training

This experiment continues **Qwen2.5-Coder-1.5B-Instruct**, using the cached
four-bit MLX conversion and the existing engineering-005 step-1200 adapter.
The parent was selected as the available engineering baseline, not by tuning
on this pilot's final tests. Its hash and the base model hash were verified
before and after the run. Existing adapters were preserved.

| Setting | Executed value |
| --- | --- |
| Runtime | MLX-LM 0.31.3, offline |
| Iterations | 320, one fixed final checkpoint |
| Batch / learning rate | 2 / 0.000005 |
| LoRA | 16 layers, rank 8, scale 20, dropout 0 |
| Loss | Assistant content with prompt masking |
| Sequence limit / seed | 1,024 tokens / 1042 |
| Generation | Greedy, 256 research tokens; 1,024 coding tokens |
| Trainable parameters | Approximately 5.276 million |
| Actual assistant tokens trained | 35,633 |
| Peak MLX memory | 4.141 GB |

Training loss ended at 0.001; validation loss went from 1.362 to 0.580.
These losses describe the supplied targets and do not establish scientific
accuracy. No cloud instance or new model download was needed.

The separate [metal-AM CPU pilot](../qwen-metal-additive-20261002/CPU_PILOT.md)
uses Qwen2.5-1.5B-Instruct and a passage-grounded dataset. Its model, data,
format and evaluation differ. Scores and adapters from these experiments
must not be treated as interchangeable or combined without a new protocol.

## Data that reached the optimiser

The frozen private package has 4,939 indexed records and 758 candidate cases.
Only **82 admitted training cases** reached the optimiser; ten validation
cases were used for loss and generation assessment. The other eight admitted
cases remained outside the training input folder as final tests. The 658
blocked candidates were excluded, as were full PDF page text and figures.

The 100 admitted cases contain 44 bounded summary/missing-information tasks,
36 reviewed NIMS fatigue observations and 20 original evidence fixtures.
Source-derived tasks use attributed inventory summaries with observed CC BY
notices and recorded reading scopes. They are not independently reproduced
scientific findings. Source identities, aliases, identical files,
cross-references and declared related studies were grouped before splitting.

The NIMS rows preserve stress amplitude in MPa, specimen identity, cycles,
failure/runout and missing origins. All 36 belong to training, including 13
right-censored runouts. This experiment does not measure fatigue numerical
generalisation or establish component allowables. The whole collection's
five research languages do not constitute a five-language model benchmark.

See the [preparation documentation](README.md) for admission, extraction,
partition and integrity checks. All 139 frozen dataset files passed integrity
verification again after the model run; the research collection was preserved.

## Matched evaluation and failure analysis

The protocol was written before baseline inference. It required at least
95% exact JSON accuracy in **each** validation category and no lost baseline
pass. With three, three and four cases respectively, every case must pass.
No checkpoint search, grader adjustment or semantic rescoring followed the
result. JSON key order and an outer code fence are ignored; answer values,
citation IDs, types and missing-information wording must match the targets.

| Research validation | Parent | Candidate |
| --- | --- | --- |
| Bounded summary | 0/3 | 3/3 |
| Missing interface | 0/3 | 3/3 |
| Evidence reasoning | 0/4 | 0/4 |
| Total | 0/10 | 6/10 |

The parent often returned the source object's fields rather than the requested
`claims` and `missing_information` structure. The candidate learned the six
summary/missing-interface contracts. This is a measured gain on the bounded
task, not a 60% general scientific accuracy claim.

Manual inspection of the four remaining failures found:

- Registration and independent-validation cases: reasonable refusals phrased
  differently from the exact targets. The registration answer also omitted
  the explicit distinction between registration residual and complete accuracy.
- Original Turbo valve-curve case: a confused identity statement and missing
  recognition of the absent original cam curve and valvetrain masses.
- Material-temperature case: a false claim combining room-temperature coupon
  tests with the supplied 600 °C component duty. It then identified a missing
  record ID instead of missing fatigue evidence at the relevant temperature.

The temperature contradiction is a substantive failure. The candidate would
still require correction even if a future grader accepted suitable paraphrases.
The current scores and selection were retained unchanged.

## Native retention and retrieval

Before inference, 16 reference programs passed the existing bounded evaluator.
Eight OpenUSD and eight PicoGK cases were sampled deterministically from
previously used development cases. Both parent and candidate passed all 16.
OpenUSD authoring used Pixar USD 25.5.1, semantic scene snapshots and native
USDA/USDC validation; PicoGK answers were parsed, compiled with .NET 9.0.317
and executed to check nonempty native geometry. USD's existing shader-property
checker exclusion remains explicit.

These shared synthetic recipes are a **retention smoke test**. Python,
OpenFOAM, CalculiX and broad engineering retention were not assessed here.
Successful code or geometry does not demonstrate physical interfaces or fit.

The existing retrieval helper was also exercised on one matched question
using five records from the training-side NIMS fatigue source. Both outputs
were rejected by its citation validator: the parent emitted strings in place
of cited claim objects; the candidate supplied a page-3 ID that was absent
from the five retrieved records. The rejected response was not repaired by
silently substituting a citation. The corpus is searchable, but this run does
not establish a reliable free-answer research assistant.

## Next experiment

1. Author more training cases that distinguish measurement conditions from
   component duty, original parts from aftermarket parts, calibration from
   independent validation, and missing evidence from a missing citation field.
   Vary phrasing, units and record-ID shapes; include multiple conflicting
   source records and correctly attributed refusals.
2. Define and freeze a semantic rubric before the next run: faithful supplied
   facts, exact supplied citation IDs, correct variant/temperature/units and
   explicit missing evidence. Use independent review and new evaluation cases;
   do not convert these reviewed validation failures into fresh-test claims.
3. Extend the admitted corpus through the existing rights/reading review queue.
   Keep whole sources and translation families together; prepare a new version
   rather than modifying this frozen package or mixing held-out material.
4. Re-run a matched pilot and expand native retention before considering any
   default change. The protected eight research tests remain available only
   under a registered eligibility rule.

Original M64 interfaces, cam/valvetrain data, K16 maps and fan measurements
remain open acquisition gates. Additional training cannot supply those
measurements or authorize manufacture.

## Repository verification

Curation/selection self-checks, the CI wrapper test, the existing source-collision
regression, strict Markdown links and registered input hashes pass. Full local
`make check` was attempted twice. Default Python ran 3,339 tests with 184 skips
and 14 errors from an existing SciPy binary in mesh/topology tests. Those
affected checks pass in the already-installed CAD Python environment.

The CAD Python rerun ran 3,329 tests with 45 skips and two remaining environment
errors: missing Matplotlib for the existing LPBF voxel audit, and an installed
Trimesh version without `util.random_generator` required by a checkpoint test.
No dependency or unrelated source was modified. Full local `make check` is
therefore not reported as passing; repository CI is a separate verification.
