# Qwen3.8 natural-language development pilot — 2026-10-04

The pinned `mlx-community/Qwen3.8-27B-4bit` base correctly handled 8/8 exposed synthetic spacer requests, compared with 6/8 for the unchanged deterministic parser. The two additional complete proposals concerned a relative reduction and a bore change. Four proposals and all four critical requests passed the frozen schema and intent checks, with zero required response corrections or recorded format, semantic, unit or quantity errors.

These are project-owner-authored fictional development fixtures, not measured Porsche interfaces or manufacturing instructions. The allowed final tuples are only 40/20/3 mm and 45/20/3 mm. The existing parser is retained for its complete labelled grammar; automatic adoption is not authorized.

| Measure | Deterministic baseline | Base model with clarified interface |
|---|---:|---:|
| Correct requests | 6/8 | 8/8 |
| Complete proposals | 2/4 | 4/4 |
| Critical requests | 4/4 | 4/4 |
| Paired wins / losses | — | 2 / 0 |

The two-sided exact discordance calculation is **p = 0.5**, reported descriptively. Eight exposed, curated requests with familiar values and families do not establish reliable broad superiority. Independent outcome reviews were documentary and non-blind; they did not independently rerun the model. The result concerns the clarified interface, community quantization and installed runtime together. Model-size causality and upstream numerical/conversion parity remain unknown. No adapter or optimizer was used, so this is **not evidence of fine-tuning gain**.

One call per request used greedy decoding, seed 0, a fresh KV cache, non-thinking mode and a 512-token maximum including EOS. All eight responses reached native EOS 248046, totaling 464 tokens. No retry, repair, fence removal or truncation was applied. The owner receipt measured **213.327 s**; individual cases took **8.589–12.520 s**. Automatic validation took **0.195 s**. Required response corrections were zero; actual human correction time was **not measured** (`null`), rather than zero.

The observed rolling CPU maximum was **2.468 core equivalents**, exceeding the target of 2 while remaining below the authorized sampled ceiling of 4 over windows of at least one second. The conservative overlapping memory maximum was **32,244,814,228 bytes** against a 36 GiB ceiling; the minimum available-memory proxy was **17,870,143,488 bytes** against a 16 GiB requirement. These sampled, soft guards do not establish an OS CPU cap, strict thread count or exhaustive physical Metal memory accounting. The measured owner interval precedes final receipt durability.

The original 001 CPU rejection and 002 JSON-startup rejection are preserved; each produced zero model generations. Attempt 003 added atomic READY/GO publication and completed the bounded run. Those failures and earlier Qwen/Coder scores are not rewritten.

[cases.json](cases.json) contains the exact frozen request strings, generic system prompt and raw UTF-8 responses, together with per-case hashes, token counts and timings. [results.json](results.json) contains aggregate scores, runtime identity, resource observations and sanitized provenance hashes. Full private paths, authorization records, user/thread identifiers, logs, model weights and reserved material are omitted. The public hashes identify retained records; this compact publication does not replace the full private receipts or provide a complete executable runtime package.

The model revision is `10c35caafbb80f7dc6a7a432cdd11af10a6d4818`, using native affine 4-bit/group-64 MLX with untied input/output weights. The installed MLX policy preserved the observed mixed BF16/U32 native signature before and after inference. No generated code, CAD, native geometry, fit, safety, manufacturing qualification or release was assessed or authorized by this pilot.

From the repository root, verify the published responses offline with:

```sh
python3 -B training/qwen38-natural-language-pilot-20261004/check_publication.py
```

The check uses the byte-exact owner-authored pure `parameter_verifier.py` and frozen exposed expected intents. It rejects duplicate keys, nonfinite values, schema/intent mismatches, altered counts, private-path or credential leaks, and blurred CPU target/ceiling claims. It regrades the published strings and checks reported metadata; it does **not** rerun the model or baseline, authenticate a new independent review, prove historical runtime execution/EOS telemetry, or authorize a builder.
