# Research-grounded Qwen engineering continuation

Owner-requested on 2 October 2026: continue the existing local Qwen for
OpenFOAM, OpenUSD, Python and PicoGK using current scientific research.
The [source register](sources.json) separates papers, API references and
candidate datasets, with reuse limits. Run receipts determine actual results;
this recipe alone does not establish a weight update or a better model.

## Change in hypothesis

The previous coding-004/005/006 continuations failed their combined retention
gate. Coding-006 scored USD 19/30 versus 22/30 and PicoGK 7/40 versus 9/40.
The selected adapter remains coding-003/checkpoint-600. Repeating more replay
or relaxing its gate is not the new experiment.

The new pilot supplies task-specific API contracts, explicit graph dependencies,
node-associated radii and execution-checked answers. Scientific calculations
must remain expressions in their supplied parameters; perturbing inputs rejects
literal-answer memorisation. OpenFOAM examples distinguish a failed mesh from
permission to run, and a control dictionary from a validated CFD result.
The PicoGK task remains bounded literal C#; this is not arbitrary parametric
C# function generation. The four Python recipes are parameterised kernels.

## Research decisions

| Primary source | Date/status | Consequence for this pilot |
|---|---|---|
| [CAE harness study](https://arxiv.org/abs/2609.03718v1) | 3 September 2026, preprint | Use tutorial context and observed errors; distinguish completion from physics. Its stronger backbones, single runs and historical comparison limit transfer to 1.5B. |
| [IteraSim RAG](https://arxiv.org/abs/2607.20346v1) | 22 July 2026, preprint | Keep solver version and deck dependencies explicit; its v2506 cases are not v2312 cases. |
| [Graph-CAD](https://arxiv.org/abs/2604.10075) | April 2026, ICLR 2026 | Supply the dependency graph before code; later curricula should add structural edits rather than only more coordinates. |
| [FutureCAD](https://openreview.net/forum?id=jfOhTGs5G5) | April 2026, ICML 2026 | Ground advanced face/edge selection. Its grounding parent-model overlaps require regrouping, despite disjoint row IDs. |
| [CADBench](https://arxiv.org/abs/2605.10873v2) | June 2026 revision, preprint | Reserve benchmarks for evaluation and inspect geometry separately from executable code. |
| [CAD-Coder](https://arxiv.org/abs/2505.19713v3) | NeurIPS 2025 | Begin with verified SFT targets; geometry-based RL is a later, measured experiment. No GRPO is claimed here. |
| [rStar-Coder](https://arxiv.org/abs/2505.21297) | NeurIPS 2025 | Retain independent input/output verification and reject unverified solutions. |

[CAD-Recode](https://github.com/filaPro/cad-recode/blob/main/LICENSE.md) is
CC-BY-NC-4.0 and is excluded from this pilot. The official
[GenCAD-Code dataset](https://huggingface.co/datasets/CADCODER/GenCAD-Code)
declares no dataset licence; its image-conditioned targets cannot simply be
treated as text instructions. FutureCAD dataset rights still need confirmation.
[rStar-Coder](https://huggingface.co/datasets/microsoft/rStar-Coder) declares
CC-BY-4.0; a future filtered, attributed stream is suitable for consideration,
with contamination checks and actual test execution. Its full download exceeds
480 GB. No third-party rows or raw paper text enter the present corpus.

## Frozen protocol

The [curriculum](curriculum.py) authors 384 training, 32 validation and 32 fresh
test rows across four domains. Add 96 previously verified training rows from
each of USD/PicoGK, and their 70 existing validation cases for retention.
No previous validation or final-test answer is a training target. Fixture
names are disjoint, but task recipes are shared; this is a narrow contract
benchmark, not independent task-family or industrial generalisation.

The [runner](run.py) reuses the pinned Qwen/MLX and the existing bounded
OpenUSD/PicoGK evaluators. It freezes sources/data/model hashes before baseline
evaluation, holds the existing training lock, and records actual native/runtime
versions. USD is scored serially; PicoGK has four bounded compiler workers.
Every authored Python/USD target and all held-out PicoGK targets are checked.
Twenty-four training PicoGK answers receive native witnesses; every remaining
training answer is parsed against its independently supplied graph.

Continue coding-003 for 480 iterations: batch 1, last 16 LoRA layers, rank 8,
scale 20, learning rate 0.00005, seed 42, masked prompts and maximum 1,024
tokens. Oversized sequences stop rather than truncate. Compare identical greedy
decoding before/after. Keep every passing new/old validation case, require at
least 85% in each new domain, one gain and all failed-mesh gates. Fresh tests
open only after eligibility. Default inference and engineering approval are
never changed by this runner.

```sh
TRAIN=/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993
PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
"$TRAIN/work/m64-qwen/venv/bin/python" training/qwen-engineering-20261002/run.py train \
  --training-checkout "$TRAIN" --output "$PWD/work/qwen-engineering-new" \
  --usd-python /Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"
python3 -m unittest discover -s tests -p 'test_qwen_engineering_curriculum.py' -v
```

Use a new output directory. No new model download, package installation,
GPU rental, model-hub upload or default-adapter replacement is part of this run.

## OpenFOAM boundary and next increment

Native OpenFOAM witnesses use the installed **ESI v2312** cavity in Kali2's
existing engineering image, pinned by observed image ID. Foundation 14 now uses
`foamRun`/solver modules for most flows; these distributions must not be mixed.
Control-dictionary and failed-mesh JSON scores alone do not demonstrate a solver
run, convergence, conservation, mesh independence or correct field predictions.
Record the native witness separately from model validation.

The next broader corpus should include dimensioned CAD programs with holes,
parameter perturbations and independent interface inspection; complete versioned
CFD case bundles with reference fields, conservation and mesh-refinement checks;
USD composition/asset-boundary tasks; and test-verified Python repair traces.
Use actual errors from training/development tasks, not exposed final tests, to
author the next increment. Maintain the carrier's existing attachment gate.
Model weights never supply dimensions, material evidence or release authority.
