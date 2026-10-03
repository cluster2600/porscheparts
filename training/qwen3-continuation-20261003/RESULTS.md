# Scientific continuation outcome

Candidate D completed native MLX training with clean runtime supervision.
Two independent blinded assistant graders reject D: base 14/20, historical
adapter 14/20, D 13/20, with no gain and one critical regression. The reserved
pool remains closed. D is not adopted; the training objective remains unmet.
The base control also has errors and is not scientifically qualified.

## Execution evidence

| Trial | Result | Admissibility |
|---|---|---|
| A | Non-finite training metric after step 5 | Rejected |
| B | Non-finite gradients before update 5; four updates completed | Rejected |
| C | Metal command-buffer error and subsequent stall | Quarantined, impact unknown |
| D | Twenty rows, ten updates, clean native MLX | Rejected after development review |

D uses the original historical adapter and pinned public Qwen3 base.
No rejected checkpoint was reused. Both the initial two-trial ceiling and
separate numerical recovery authorizations C and D remain recorded.
The exact conversion, finite gradients, checkpoint reload and all-base integrity
receipts are under [candidate-d-001](runs/candidate-d-001/training-receipt.json).

D training took 54.87 seconds in its worker and 56.45 seconds under supervision.
Peak worker RSS was 8,424,325,120 bytes; peak MLX allocation was 9,730,795,347
bytes. System swap growth was zero. The observed CPU peak was 279.6% with a
two-thread environment target and nice 10; this target is not a strict cap.
The log is empty, the process exited zero, and no resource stop or GPU error
was observed. All 398 BF16 base tensors retain their before/after hash.
The final 144 FP32 adapter arrays contain 2,949,120 parameters.

The three development arms generated sixty complete answers in 302.30 seconds
under the same native MLX policy, exact task profile, source messages and greedy
192-token bound. No answer hit the token budget, no runtime/resource failure
occurred, and base integrity passed in each arm. Historical PEFT scores cannot
be transferred to this runtime. Native MLX rounds the LoRA delta differently.

## Paired scientific development review

Both reviewers evaluated all sixty anonymized responses using the same supplied
source excerpts, without model roles or historical gold answers. All acceptance
judgments agree. These are assistant judgments, not human engineering review.

| Native MLX arm | Primary | Supplemental | Acceptable | Critical failures |
|---|---:|---:|---:|---:|
| Base | 9/12 | 5/8 | 14/20 | 1 |
| Initial adapter | 9/12 | 5/8 | 14/20 | 1 |
| D | 9/12 | 4/8 | 13/20 | 2 |

The paired D/base comparison has zero gains, one loss, thirteen pass ties and
six fail ties. The loss is critical: a correct fatigue refusal substitutes
**ductility** for the source's **toughness**. The descriptive exact two-sided
McNemar diagnostic is p=1; this exposed development set supports no independent
improvement claim. There are no generation-budget hits or runtime failures.
The judgments, source-specific reasons, family counts and input/response/run
hashes are in [development-summary.json](development-summary.json) and the
[two raw blinded reviews](reviews/development-d/reviewer-1.json),
[second review](reviews/development-d/reviewer-2.json).

Seven D answers fail for omitted endpoint qualifiers or reversed agreement
relationship; assigning a specific stress effect to a general clamping statement;
reversing a model's prediction target; upgrading an observation to causation;
transferring a median-size condition between distinct studies; inferring an
unsupported dominant influence; and substituting a mechanical property during
a correct refusal. The condition-transfer and dominance failures are identical
in all three arms. Numeric completion did not correct these scientific errors.

The [frozen rejection receipt](selection-receipt.json) binds protocol, runner,
final D bytes, both judgments and the unchanged reservation/amendment. No reserved
answer was generated, no alternative checkpoint selected, and no weight was
changed after review. Historical PEFT scores remain separate; their evaluator
and runtime do not provide comparable numbers here.

## Scope and limits

The twenty corrective examples are ten bilingual objectives from six licensed
training source families. They do not cover all project material. The
[coverage inventory](CORPUS_COVERAGE.md) distinguishes prepared datasets from
what was actually trained. No impeller research, forum claims, private Porsche
document, unknown measured value, or Qwen2.5-Coder data entered D.

The twenty development questions were already exposed. They support regression
checks and selection only, not an independent improvement claim. The unchanged
reserve commitment and amendments are under [reserved-public](reserved-public/registration.json).
Assistant grading is not human scientific or manufacturing validation.

## Repository validation

The frozen D source/data/weights/results/reviews snapshot passed native Linux
`make check`: 3,420 main unittest cases, 194 optional skips, all 49 new Qwen
control tests and zero broken links in 688 Markdown files. Runtime was 186.93
seconds and sampled peak check-group RSS 409.4 MiB, within registered resources.
See [the exact tested-snapshot receipt](checks/public-check-summary.json).
Three planning/README documents changed during that check; the final commit's
GitHub CI must also pass before review or merge. No merge is authorized here.
