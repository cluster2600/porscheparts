# OpenUSD Python continuation pilot

Executed locally on 2026-10-01 on the Apple Silicon Mac. This continues the
existing PicoGK adapter for the pinned **Qwen2.5-Coder-1.5B-Instruct 4-bit** model.
It does not train the proposed CUDA 7B/32B models or rent a Vast GPU.

**Outcome: USD task accuracy improved from 0/12 to 3/12. PicoGK remains 8/16,
with no per-case regression. Keep the new adapter experimental.** The default
inference model is unchanged. [Machine-readable evidence](openusd-results.json)
contains both models' responses, native results, configuration and hashes.

| Frozen check | Previous PicoGK adapter | New USD + PicoGK adapter |
|---|---:|---:|
| USD parameter tasks, complete contract | 0/6 | 3/6 |
| USD combined-scene tasks, complete contract | 0/6 | 0/6 |
| USD native validation, before checking requested semantics | 0/12 | 5/12 |
| PicoGK C# compilation and nonempty native geometry | 16/16 | 16/16 |
| PicoGK requested geometry, complete contract | 8/16 | 8/16 |

The three successful USD tasks cover transformed cubes, triangle meshes and
Preview Surface material binding. Failures include invented methods such as
`SetInstanceReference`, incorrect variant values, calling stage-unit APIs on the
wrong object and repetitive/truncated combined-scene output. Two valid USD scenes
still failed their requested semantics. Low validation loss did not predict these
failures. This run does not demonstrate general composition ability.

## Corpus and training

- OpenUSD: 48 train / 6 validation / 12 test examples; all 66 reference scenes
  passed native authoring, topology, composition, binding and USDA/USDC round-trip
  checks using Pixar `usd-core==25.5.1`.
- PicoGK replay: the previous 64 training and 8 validation examples. Its 16
  existing test cases remain excluded from training and serve as a regression
  suite. This is not a new independent PicoGK benchmark.
- Six USD tests change parameters; six combine a taught recipe with an additional
  sphere. Shared templates make this a narrow authoring experiment, not evidence
  of arbitrary Python, C++ USD or complete engine-assembly competence.
- 160 additional LoRA steps, batch 1, last 4 layers, rank 8, MLX scale 20,
  learning rate `1e-4`, seed 42, prompt loss masked, maximum sequence 1,024.
  Actual longest complete sequence: 440 tokens; no truncation needed.
- MLX-LM 0.31.3; 1.319 million trainable parameters. Validation loss decreased
  from 0.529 to 0.007; reported peak training memory was 1.965 GB.
- New adapter: `work/m64-qwen/openusd-001/adapter/adapters.safetensors`.
  Inputs, configurations, hashes, logs and raw responses are retained in that run
  directory. Training starts from previous adapter weights with a fresh optimizer;
  it is continuation training, not a bit-exact optimizer-state resume.

Adapter SHA-256: `c7d62072762ceafdf79c76d39aeccdefd8f5371196784f409417725cec0ae434`.

Repository verification: `make check` passed (3,250 main-suite tests, 160 optional
runtime skips, plus the additional repository checks). The two focused OpenUSD
tests also passed separately in the actual Pixar runtime, including all 66
reference scenes and rejected file/import operations. Both guide Mermaid diagrams
rendered, and strict link checking found no broken links in 641 Markdown files.

## Validation scope

The scorer checks real USD stages through a bounded API interpreter. It compares
units/up-axis/default prim, prim and attribute types, values, time samples,
bindings, reference arcs and variant alternatives. Python variable names are
irrelevant. Outputs outside this limited interpreter are recorded as unsupported;
they are not necessarily invalid general Python programs.

The installed wheel omits shader discovery resources. Compliance checks explicitly
exclude `ShaderPropertyTypeConformanceChecker`; every receipt records this.
Binding rules and requested shader attribute types/values are still checked.
Full shader-registry conformance, rendering, external asset portability and
Omniverse import remain untested. Visual materials are not engineering properties.

## Reproduce

Run from the repository root, with the existing pinned MLX and Pixar environments.
Use fresh output names; the commands refuse to replace evidence files. The first
PicoGK run supplies the replay corpus and initial adapter.

```sh
MLX=work/m64-qwen/venv/bin/python
USD=/Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python
MODEL=work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be
RUN=work/m64-qwen/openusd-reproduction

"$MLX" training/m64-engineer/openusd.py generate \
  --output work/m64-engineer/usd-reproduction-candidates.jsonl
"$USD" training/m64-engineer/openusd.py verify \
  --input work/m64-engineer/usd-reproduction-candidates.jsonl \
  --output work/m64-engineer/usd-reproduction-reviewed.jsonl
"$MLX" training/m64-engineer/openusd.py prepare-pilot \
  --input work/m64-engineer/usd-reproduction-reviewed.jsonl \
  --replay work/m64-qwen/picogk-001/cases.json --output "$RUN"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
"$MLX" -m mlx_lm lora --model "$MODEL" --data "$RUN/data" \
  --train --iters 160 --batch-size 1 --num-layers 4 \
  --learning-rate 0.0001 --max-seq-length 1024 --mask-prompt --seed 42 \
  --steps-per-report 10 --steps-per-eval 80 --val-batches -1 --save-every 160 \
  --resume-adapter-file work/m64-qwen/picogk-001/adapter/adapters.safetensors \
  --adapter-path "$RUN/adapter" > "$RUN/training.log" 2>&1

"$MLX" training/m64-engineer/openusd.py infer --input "$RUN/usd-cases.jsonl" \
  --model "$MODEL" --adapter work/m64-qwen/picogk-001/adapter \
  --output "$RUN/usd-before-responses.jsonl"
"$USD" training/m64-engineer/openusd.py score --input "$RUN/usd-cases.jsonl" \
  --responses "$RUN/usd-before-responses.jsonl" --output "$RUN/usd-before-scores.jsonl"
"$MLX" training/m64-engineer/openusd.py infer --input "$RUN/usd-cases.jsonl" \
  --model "$MODEL" --adapter "$RUN/adapter" --output "$RUN/usd-after-responses.jsonl"
"$USD" training/m64-engineer/openusd.py score --input "$RUN/usd-cases.jsonl" \
  --responses "$RUN/usd-after-responses.jsonl" --output "$RUN/usd-after-scores.jsonl"
```

Both evaluations use the same frozen USD prompts, greedy decoding and 1,024 output
token limit. “Before” means the previous **PicoGK adapter**, not the pretrained
base model. Both are evaluated after training; their weights are distinct and
the previous adapter remains unchanged. Test outputs do not select the number
of steps or any subsequent checkpoint.

Recheck PicoGK with the same native toolchain and frozen cases:

```sh
PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
mkdir "$RUN/picogk-before" "$RUN/picogk-after"
cp "$RUN/picogk-cases.json" "$RUN/picogk-before/cases.json"
cp "$RUN/picogk-cases.json" "$RUN/picogk-after/cases.json"
"$MLX" training/m64-qwen/picogk.py --evaluate --output "$RUN/picogk-before" \
  --model "$MODEL" --adapter work/m64-qwen/picogk-001/adapter \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"
"$MLX" training/m64-qwen/picogk.py --evaluate --output "$RUN/picogk-after" \
  --model "$MODEL" --adapter "$RUN/adapter" \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"

"$USD" -m unittest discover -s tests -p test_m64_openusd.py -v
```

Keep this local experiment separate from the family-split, independently authored
benchmark required by the [larger-model guide](../m64-engineer/README.md).
