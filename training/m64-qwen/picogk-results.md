# PicoGK code training and evaluation

A real local QLoRA run completed on 2026-09-30 using Qwen2.5-Coder-1.5B-Instruct
(4-bit). The adapter learned the requested C# syntax and familiar lattice
layouts, but failed to follow new edge arrangements. **Keep it experimental;
do not promote it as a general PicoGK code generator.**

| Frozen test metric | Base | Adapter |
|---|---:|---:|
| Compiles against the real PicoGK DLL | 0/16 | 16/16 |
| Produces nonempty native voxel/mesh geometry | 0/16 executed | 16/16 |
| Correct vertices, edges, end radii and caps | 0/16 under the output contract | 8/16 |
| Familiar layouts with held-out parameters | 0/8 | 8/8 |
| Unseen triangle / spatial-tripod layouts | 0/8 | 0/8 |

Compilation is not geometry correctness. For example, test-009 requests
A→B, B→C, C→A. The adapter emits A→B, B→C, C→D: a plausible-looking open
chain rather than the requested triangle. Spatial tripods similarly become
chains. Those failures count even though PicoGK produces a mesh.

## What ran

- New synthetic corpus: 64 train, 8 validation, 16 frozen test examples.
  Training layouts are struts, elbows, rectangular frames and diagonal braces.
  The test set contains eight parameter holdouts and eight composition holdouts.
  Prompts supply vertices, directed edges, endpoint diameters and cap style;
  answers must generate literal `lattice.AddBeam(...)` statements and halve
  diameters into radii. No engine scans, manuals or measurements were ingested.
- Training started from the pinned base checkpoint, **not** the earlier
  workflow adapter. One run, 100 iterations, batch 1, four adapted layers,
  default LoRA rank 8, learning rate 0.0001, seed 42, prompt masking and
  maximum sequence length 1024. All examples fit without truncation.
- MLX-LM 0.31.3 on the Mac. 11,408 completion tokens trained;
  final training loss 0.003, validation loss 0.002, reported peak training
  allocation 1.965 GB. Low loss did not predict composition generalization.
- Greedy generation, 512-token ceiling, identical frozen prompts for both
  models. No retries, repair prompts or selection among sampled answers.
- .NET SDK 9.0.317 and the real managed/native PicoGK installation, pinned
  upstream revision `0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3`.
  All 16 reference programs compiled and produced geometry before training.
- The first evaluator rejected all base responses at its literal-code boundary.
  A supplemental check then compiled **all unchanged saved responses**, including
  those rejects: the base still scored 0/16. This changed neither prompts,
  weights nor promotion criteria. The current runner includes that check.
  Base errors include unsuffixed double literals; additional observed errors
  include missing edges and diameter/radius confusion.

[Machine-readable results](picogk-results.json) contain raw responses, per-case
metrics, reference geometry metrics, model revision, DLL/native/data hashes,
training-source hash and the supplemental compiler results. Detailed compiler
and training logs remain in `work/m64-qwen/picogk-001/`.

The adapter is local at
`work/m64-qwen/picogk-001/adapter/adapters.safetensors`, SHA-256
`a50561618f4d17da5d4ea2c70014dc7d1af3e6d09eedf3f3b8c21d6395b06de4`.
Weights are neither committed nor published. The previous default inference
model is unchanged. No Vast GPU was rented.

## Reproduce

Use the existing [pinned Python environment](README.md), the pinned model cache,
and a matching PicoGK managed/native installation. On this Mac:

```sh
RUNTIME=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
MODEL=work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be
work/m64-qwen/venv/bin/python training/m64-qwen/picogk.py \
  --output work/m64-qwen/picogk-002 \
  --sdk "$RUNTIME/dotnet/dotnet" \
  --dll "$RUNTIME/picogk-bin/PicoGK.dll" --model "$MODEL"
work/m64-qwen/venv/bin/python -m unittest discover -s tests -p 'test_m64_qwen*.py' -v
```

Choose a new output directory. Downloads are disabled. The runner freezes the
corpus, checks the reference programs, evaluates the base, trains, and evaluates
the adapter. C# compilation uses a fixed project without model-supplied build
files. Execution requires a full-match allowlist of bounded literal beam calls;
other source is compiled only. There are no model tool calls or shell commands.
The initial exact training script is retained locally as
`work/m64-qwen/picogk-001/training-source.py`; the current version additionally
compiles rejected responses without executing them.

## Repository verification

The five focused offline checks passed. Full `make check` completed with exit
code 0 (3,247 main-suite tests, 159 optional-runtime skips), including the new
PicoGK test. Dataset/source/adapter hashes and score coverage were independently
checked against the saved run.

## Interpretation and next experiment

This is a small, synthetic, shared-format benchmark, not evidence of general
C# capability, engine design, material suitability, fitment or manufacturing
readiness. Native checks establish nonempty geometry; semantic checks establish
agreement with the supplied beam graph. No mechanical or physical tests ran.
The reference API is [LEAP 71's pinned Lattice implementation](https://github.com/leap71/PicoGK/blob/0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3/Base/Lattice.cs).

The next useful training experiment is diverse graph topology and edge-order
supervision, with a **new untouched composition test set**. More iterations on
these four layouts would not address the observed failure. General methods,
loops, boolean solids, hollows, mesh export and full engine parts remain outside
this experiment's scope.
