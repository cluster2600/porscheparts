# Local training results — 2026-09-30

**Training completed; the adapter is experimental and is not selected by default.**
The local helper keeps the base model because the adapter regressed on two unit
conversions and both models failed two rental-gate questions.

| Measure | Base | QLoRA adapter |
|---|---:|---:|
| Strict JSON exact matches | 0/20 | 16/20 |
| Content matches ignoring Markdown fences | 18/20 | 16/20 |
| Held-out completion loss | 1.500 | 0.016 |
| Mean completion time | 0.287 s | 0.280 s |
| Peak inference allocation reported by MLX | 1.138 GB | 1.195 GB |

The adapter improves formatting but worsens content: it returned 0.31 m for
31 mm and 0.38 m for 38 mm. Both models incorrectly allowed rental in two cases
with incomplete prerequisites. No model controls spending; no rental occurred.
The lower loss is not a reason to promote a model that fails these checks.

## Actual execution

- Apple M1 Max, 64 GiB unified memory; Python 3.12.11; MLX-LM 0.31.3.
- Pinned Qwen2.5-Coder-1.5B-Instruct MLX 4-bit weights, verified SHA-256.
- 40 training, 10 validation and 20 test examples; disjoint fixture families.
- 60 iterations, batch 1, last 4 layers, rank 8, learning rate 0.0001,
  seed 42, prompt masking, maximum sequence 512 tokens.
- Training log: 1.319 million trainable parameters, 1,333 trained completion
  tokens, peak allocation 1.330 GB. This is a small adaptation pilot.
- Final complete pipeline: 31.53 seconds with the model already cached.
  This excludes initial download and environment installation.
- Adapter SHA-256: `b6c198a29251025309cd7d50397c87655e239137dd5199d675f4752e9e28a953`.
- Local output directory: `work/m64-qwen/run-003/`; weights and adapters are
  ignored by Git and were not uploaded to a model hub.

[Machine-readable receipt](results.json) includes case responses, scores,
source/data hashes, model revision and artifact hashes. Raw logs and adapter
weights remain in the local output directory. MLX reports loss rounded to three
decimal places. These are synthetic instruction-compliance metrics, not engine,
material or general coding performance.

## Diagnostics and reproducibility

Run 001 exposed a checkpoint integration issue: model config declared end-of-text
151643, while the chat tokenizer uses 151645. Responses continued beyond chat
boundaries. The inference helper now adds `<|im_end|>` to the stopping set for
both models; an offline regression check covers that setup.

Run 002 used the corrected stopping behavior. Inspection showed that strict
format improvement hid content regressions. Promotion was therefore tightened
to require no content regressions and all safety cases passing. Run 003 reran the
complete pipeline with unchanged examples and training hyperparameters; the
adapter hash is identical across all three runs. Earlier logs are retained.
The updated gate is an engineering correction, not an independently preregistered
acceptance claim. No tuning was performed to improve the exposed test cases.

The offline inference smoke routed structural analysis to CalculiX on kali2
using the default base selection. Neither base nor adapter is trusted to make
unit conversions or approval decisions without deterministic validation.

## Verification

- Four focused offline tests pass: corpus integrity, strict comparison and
  promotion, chat stopping, source/model pins.
- Five Mermaid diagrams render with Mermaid CLI 11.12.0 and local Chrome.
- Full `make check` exits 0: 3,246 main-suite tests, 159 optional-runtime
  skips, and all subsequent catalogue/generated-document checks pass.
- Documentation link check: zero broken links across 638 tracked Markdown files.
- The original working directory remains unchanged; implementation is isolated
  on `codex/m64-local-architecture-qwen`.

## Next step

Collect reviewed corrections from real PicoGK/OpenFOAM/USD tasks, then create a
new independently authored holdout before another training experiment. Keep
this test set as a regression suite. Compare a larger model only after providing
sufficient disk space; this pilot does not justify replacing the base.
