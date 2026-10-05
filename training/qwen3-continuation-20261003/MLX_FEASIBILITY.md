# Static MLX-LM feasibility audit

The installed MLX-LM source supports this exact Qwen3 architecture and accepts
its local Hugging Face safetensors directly. The original PEFT adapter has a
well-defined mapping to official `LoRALinear`. Runtime loading, numerical parity
and stable optimization remain untested. No model, MLX operation, conversion,
GPU command or optimizer step was executed for this audit.

The existing environment is `work/m64-qwen/venv/bin/python` in the original
`m64-local-architecture-qwen` checkout: Python 3.12.11, MLX 0.32.3, MLX-LM
0.31.3, Transformers 5.17.0, NumPy 2.5.3 and safetensors 0.8.0.
The [machine-readable audit](mlx-feasibility.json) gives the exact installed
source paths relative to `venv/lib/python3.12/site-packages`, SHA-256 hashes,
configuration, header observations and bounded proposals. No Qwen2.5-Coder
weight, candidate A/B/C checkpoint, reserved question or reviewer pool was read.

## Direct base loading and tied embeddings

Use the existing local snapshot under the continuation work directory:

```text
cache/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/cdbee75f17c01a7cc42f958dc650907174af0554
```

`mlx_lm/utils.py:218` returns an existing local path without downloading.
`load_model` at line 282 reads `model*.safetensors` with `mx.load` and selects
`mlx_lm.models.qwen3` from `model_type=qwen3`. Its strict base load is followed
by `mx.eval` unless `lazy=True`; lazy loading alone is not a CPU-device or
memory guarantee. This source path requires no base serialization conversion.
Passing a repository name instead of the existing path can trigger a download,
so a future probe must use the exact path and offline settings.

The three header inspections found 398 BF16 tensors, 4,022,468,096 elements,
36 layers, hidden size 2,560, 32 attention heads and eight key/value heads.
Native base storage is about 8.04 GB; this is not a peak-memory estimate.
`load_model` performs no explicit dtype cast. An optional `convert()` defaults
to `torch_dtype=bfloat16` and supports explicit FP32; invoking it is unnecessary
for this base and would write a new serialization. Quantization is excluded.

The exact config sets `tie_word_embeddings=true`. `qwen3.py:163` therefore
creates no separate `lm_head`; line 179 calls
`model.embed_tokens.as_linear(out)`. Line 185 removes an optional duplicate
`lm_head.weight`. The snapshot contains `[151936,2560]`
`model.embed_tokens.weight` and no separate head tensor. Preserve this tie;
do not synthesize, duplicate or unfreeze an output head.

Base payload hashes were **not recomputed** in this light audit. Cache blob
names match the three hashes in the original executed receipt; headers and
configuration were inspected independently. This is a scoped consistency
observation, not a fresh eight-gigabyte payload-integrity attestation.

## Original adapter mapping

The sole adapter source is
`runs/qwen3-fidelity-001/adapter/adapter_model.safetensors` in the historical
Qwen3 package, SHA-256
`fb6ab78bf8868a1e77e3c1c5e156eeef63b0b3e42378aaa1410e8c7cfaf1d5cb`.
Its current file hash was verified. Headers exactly cover 144 FP32 tensors,
72 q/v modules across all 36 layers, and 2,949,120 elements.

| Projection | Original PEFT A | Original PEFT B | MLX `lora_a` | MLX `lora_b` |
|---|---|---|---|---|
| q | `[8,2560]` | `[4096,8]` | A transpose: `[2560,8]` | B transpose: `[8,4096]` |
| v | `[8,2560]` | `[1024,8]` | A transpose: `[2560,8]` | B transpose: `[8,1024]` |

Strip the `base_model.model.` prefix and replace `.lora_A.weight` with
`.lora_a`, or `.lora_B.weight` with `.lora_b`. For example:

```text
base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight
→ model.layers.0.self_attn.q_proj.lora_a
```

Official `mlx_lm/tuner/lora.py:11` stores A as `[input_dims,r]` and B as
`[r,output_dims]`. Its line 95 computes `x @ A @ B`, multiplied by `scale`.
Thus PEFT alpha/rank = 16/8 requires **scale=2**, not the installed default 20.
No scale should be baked into converted tensor values.

The native adapter filename is `adapters.safetensors`. Its explicit config is:

```json
{
  "fine_tune_type": "lora",
  "num_layers": 36,
  "lora_parameters": {
    "rank": 8,
    "scale": 2.0,
    "dropout": 0.05,
    "keys": ["self_attn.q_proj", "self_attn.v_proj"]
  }
}
```

`tuner/utils.py:113` loads this format with `strict=False`. Independently reject
missing or extra keys, wrong shapes/dtypes, other projections, partial layer
coverage or any count other than 144 arrays / 72 wrappers / 2,949,120 trainable
elements. Official `mlx_lm/lora.py:224` freezes the base before adding LoRA
wrappers. Inference must call `eval()` again after attachment: MLX dropout
preserves p=0.05 but becomes the identity only outside training. Matching
dropout probability does not imply identical cross-framework random masks.

## Numerical limitations

There is a concrete difference beyond tensor names. PEFT 0.17.1
`peft/tuners/lora/layer.py:758` casts the LoRA input to the adapter's FP32 dtype,
adds the scaled FP32 delta, then casts the combined result back to the base
output dtype. MLX `LoRALinear` line 98 casts the scaled delta to `x.dtype`
**before** adding it to the base result. Native BF16 can therefore introduce a
different rounding point. Exact tensor conversion does not prove equivalent
forward results.

Explicitly promoting the original BF16 base values to FP32 for a separately
registered MLX experiment removes this particular BF16 rounding point but
changes the execution profile and doubles base tensor storage to about
16.09 GB. Matmul, normalization, RoPE, attention kernels and tokenizer/profile
inputs still require comparison. Neither runtime stability nor scientific gain
can be inferred from architecture support or a tiny projection probe.

## Bounded next steps — proposals only

1. **CPU adapter format conversion:** at most 300 seconds, two CPU threads,
   1 GiB memory and zero optimizer steps. Use existing NumPy/safetensors only;
   import neither MLX nor Torch and load no base model. Transpose the original
   144 FP32 arrays into a new directory, check finiteness and exact key/shape
   coverage, and require byte-equal original values after inverse transpose.
   Record original and destination hashes; stop on any mismatch or limit.
2. **Light numerical probe:** only after the owner verifies that candidate C's
   stalled worker has exited and resources are free. At most 300 seconds,
   1 GiB GPU memory and zero optimizer steps. Test one q and one v projection
   with a fixed synthetic two-token input, the pinned original base tensors and
   original adapter. Compare official unquantized MLX FP32 `LoRALinear` in eval
   mode against a PEFT CPU FP32 projection reference and base-only output.
   Compare base output, adapter-only delta and combined output separately, so
   the base cannot hide a wrong adapter scale. Register `atol=1e-5`,
   `rtol=1e-4` and relative L2 error <=1e-4 on each pair before running, with
   relative error defined as `norm(actual-reference)/max(norm(reference),1e-12)`.
   Retain finite raw outputs and hashes. Load no full model and generate no
   answers in this probe.

The parent reports a candidate C MPS command-buffer fault/stall with unresolved
termination. This audit did not inspect or resolve that worker. No GPU probe is
authorized to run from this document, and the A/B/C checkpoints are excluded.
Any subsequent MLX training would be a new backend experiment with its own
registration, receipts, scientific evaluation and acceptance decision.
