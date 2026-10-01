# Expanded OpenUSD and PicoGK training

This follows the [first OpenUSD pilot](openusd-results.md), using the same local
Qwen2.5-Coder-1.5B 4-bit base and existing Mac environments. Larger CUDA models,
OpenFOAM training and Omniverse validation are outside this experiment.

## Measured result — 1 October 2026

Training and evaluation completed on the existing Mac. The selected adapter
improves OpenUSD authoring and slightly improves the original PicoGK cases.
Fresh PicoGK graph accuracy remains poor. It stays **experimental**, with no
default-model replacement. The [machine-readable report](coding-results.json)
contains per-case outcomes, response hashes, frozen manifests and receipt hashes.

| Test partition | Previous adapter | Selected adapter | Previously passing cases lost |
|---|---:|---:|---:|
| OpenUSD original regression cases | 3/12 (25%) | **12/12 (100%)** | 0 |
| OpenUSD fresh instances | 1/24 (4.2%) | **16/24 (66.7%)** | 0 |
| PicoGK original regression cases | 8/16 (50%) | **9/16 (56.3%)** | 0 |
| PicoGK fresh graph instances | 1/16 (6.3%) | **1/16 (6.3%)** | 0 |

Across all test cases, OpenUSD rises from 4/36 to 28/36 and PicoGK from 9/32
to 10/32. These domains are not combined into a misleading engineering grade.
USD composition passes rise from 0/6 to 6/6 on the old cases and from 0/12 to
5/12 on the fresh three-object scenes. Fresh single-object USD cases reach 11/12.
The eight original PicoGK parameter cases still pass; original composition
improves from 0/8 to 1/8.

All 32 selected-model C# outputs compile, and 31 produce nonempty native geometry,
but only 10 meet the requested beam semantics and full acceptance contract.
Likewise, 29 USD scenes pass the available native checks, while only 28 match the
requested authoring contract. Compilation or loadability alone is not accuracy.
Remaining USD failures include incomplete syntax, unsupported operations, a wrong
binding API call and one wrong scene contract. Complex composition and PicoGK edge
semantics remain the main limits visible in these tests.

The selected adapter SHA-256 is
`a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a`.
The final training stage reports 2.116 GB peak memory, 88,353 trained tokens and
validation loss 0.022. Loss is diagnostic; native task results determine the score.

## Dataset and evaluation protocol

The expanded USD curriculum adds 288 training examples, 24 validation cases and
24 fresh test cases. It varies part paths, sizes, transforms, references, variant
selection and animation. Training includes single objects and two-object scenes;
the additional validation/test composition cases require three objects. All 336
new reference answers passed the same bounded Pixar checks as the original pilot.

The PicoGK curriculum adds 128 training examples, 16 validation and 16 fresh test
cases. Each specifies four vertices and one to six directed edges, with independently
varied endpoint diameters and arbitrary connectivity. Every new reference program
compiled and produced nonempty geometry in the pinned native PicoGK runtime.

Original training and validation examples are retained. The combined unique splits
contain 528 training records (336 USD, 192 PicoGK), 54 validation records (30/24),
and 68 test records (36/32). No validation or test targets enter training.
The longest complete sequence is 547 tokens, below the fixed 1,024-token limit.

The original 12 USD and 16 PicoGK tests are now **development-informed regression
cases**: their earlier failure patterns motivated the curriculum. The additional
24 USD and 16 PicoGK tests are frozen before training and evaluated only after
checkpoint selection. They still share API recipes and task grammar with training;
they are fresh instances, not a family-independent engineering benchmark.

Selection uses validation only: increase USD pass count, preserve every previously
passed PicoGK validation case, then break ties with PicoGK count and fewer steps.
The scorer, original prompts and semantic acceptance criteria remain unchanged.
Only the native runtime launch/preflight was corrected, as described below.
AST fingerprints confirm that the USD authoring, snapshot and validation functions,
and PicoGK parser, semantic signature and native witness are unchanged from commit
`f3e51d0`. The saved grading contract records the later CLI/runtime correction
separately from the source hashes frozen when training started.

## Validation-based selection

| Adapter | USD validation | PicoGK validation | Decision |
|---|---:|---:|---|
| Original OpenUSD pilot | 7/30 | 8/24 | Baseline |
| Expanded curriculum, step 400 | 27/30 | 4/24 | Reject PicoGK regressions |
| Expanded curriculum, step 800 | 23/30 | 4/24 | Reject PicoGK regressions |
| Retention continuation, step 300 | 15/30 | 11/24 | Eligible |
| Retention continuation, step 600 | 22/30 | 8/24 | Selected by the predefined USD-first rule |

The selected weights are in `work/m64-qwen/coding-003/checkpoint-600/`.
All eight baseline PicoGK validation passes are retained. The step-300 checkpoint
has more PicoGK passes, while step 600 has more USD passes; this tradeoff is visible
rather than hidden by an aggregate score. Both adapters remain experimental.
The chosen path adds 400 + 600 training steps beyond the original USD pilot;
1,400 steps were actually computed across the two full training attempts.

## Training attempts and an evaluator correction

`coding-002` continues the first USD adapter for 800 steps, evaluating checkpoints
400 and 800. Batch 1, last four layers, rank 8, MLX scale 20, learning rate `1e-4`,
seed 42 and prompt masking match the first pilot. Corrected USD validation scores
are 7/30 before training, 27/30 at step 400 and 23/30 at step 800. PicoGK drops
from 8/24 to 4/24 at both checkpoints, so neither meets the selection rule.

The initial runner resolved the USD Python executable's symlink, bypassing its
virtual environment. This caused `ModuleNotFoundError: pxr` to be recorded as model
failures. Those USD scores are invalid. The exact saved answers were rescored using
the real USD interpreter; inference was not repeated and no targets were changed.
The runner now preserves the interpreter path and checks its USD version before
starting. The scorer also fails before writing results when USD is unavailable.
Original failed receipts and corrected results remain separate under `work/`.

A later native test run stalled in USD's TBB stage cleanup while training was
active. Its process sample was retained and that test process was stopped. The
same 402 reference scenes and boundary checks then passed in 2.184 seconds with
`PXR_WORK_THREAD_LIMIT=1`. The USD CLI now defaults these tiny witness jobs to
serial execution, using Pixar's documented
[thread limit](https://openusd.org/25.05/api/thread_limits_8h.html). This changes
runtime concurrency, not model responses or scene acceptance criteria.

`coding-003` starts from the better USD checkpoint at step 400 and adds 600 steps
at learning rate `5e-5`. The 64 original PicoGK training records receive weight 8,
making 976 effective training records while retaining 528 unique records. Only
training rows are repeated. Checkpoints 300 and 600 are compared using the same
validation rule and frozen final test sets. This explicitly tests whether replay
can recover PicoGK behavior while retaining the USD improvement.

## Verification and retained evidence

`make check` exits 0: 3,253 main-suite tests, including 160 optional-runtime skips,
plus the additional repository checks. The separate native USD suite passes all
three tests and exercises 402 reference scenes. All 160 new PicoGK reference
programs compile and run in the pinned native runtime. Strict documentation links
and staged whitespace checks pass.

Raw model answers, native scene files, compiler/runtime logs, manifests and the
selected weights are retained under `work/m64-qwen/coding-003/`; the first attempt
and infrastructure diagnostics remain in `coding-002/` and `coding-002-prep/`.
The tracked JSON records their hashes without committing models or generated
build directories. The runner rechecked frozen dataset and original-adapter hashes
after final evaluation. There was no new model download or cloud GPU rental.

## Reproduce

Use fresh output paths. Existing source/model hashes, original adapters and native
verification receipts are checked before training. The runner freezes case files,
records parameters and hashes, runs native reference witnesses, trains, selects on
validation, and opens the final test partition only if selection succeeds.

```sh
MLX=work/m64-qwen/venv/bin/python
USD=/Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python
MODEL=work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be
PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
PREP=work/m64-qwen/coding-reproduction-prep
RUN=work/m64-qwen/coding-reproduction
mkdir "$PREP"
"$MLX" training/m64-engineer/openusd.py generate --expanded \
  --output "$PREP/candidates.jsonl"
"$USD" training/m64-engineer/openusd.py verify --input "$PREP/candidates.jsonl" \
  --output "$PREP/verified.jsonl"
"$MLX" training/m64-qwen/improve.py --previous work/m64-qwen/openusd-001 \
  --usd-reviewed "$PREP/verified.jsonl" --output "$RUN" --model "$MODEL" \
  --usd-python "$USD" --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"

# Retention continuation, chosen from validation evidence only.
"$MLX" training/m64-qwen/improve.py --previous work/m64-qwen/openusd-001 \
  --usd-reviewed "$PREP/verified.jsonl" --output "${RUN}-retention" --model "$MODEL" \
  --usd-python "$USD" --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll" \
  --warm-start "$RUN/checkpoint-400" --iterations 600 \
  --learning-rate 0.00005 --replay-weight 8
```

Do not choose a checkpoint or tune parameters from the final-test results.
New experiments after inspecting those results need another untouched test set.
The default inference model is not automatically replaced. A better narrow score
does not establish arbitrary code correctness, CFD expertise or engineering release.
The `usd-core` shader-registry check remains explicitly excluded; visual rendering,
external asset portability and physical validation remain separate work.
