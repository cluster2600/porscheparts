# Qwen2.5-Coder train006: completed training, rejected development output

Train006 completed its registered numerical training. Its adapter was rejected on one already exposed synthetic spacer task; the base output was also rejected. No utility gain or adoption is demonstrated.

The base is `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit`, revision `b3252a2f97102b1fb1571fec2c9b27219a8536be`. Training started from a fresh base and adapter: five exposed development rows in two dependent source groups, seed 42, 16 optimizer updates, and the predeclared final-step16 checkpoint. Recorded finiteness checks, strict reload and terminal supervision passed. Train005 remains quarantined. Train006 produced byte-identical adapter data under a clean recorded execution; this does not retroactively admit train005 or demonstrate another model improvement.

| Check | Observed result |
| --- | --- |
| Paired generation | One fresh generation per arm, identical 392-token input, greedy seed 0, maximum 2,048 tokens including EOS; no repair or retry |
| Completion and integrity | Base 368 tokens, adapter 465, both real EOS; 21.28 seconds, two explicit exit0 waits, 49 unchanged bindings |
| Source admission | Two independent blinded reviews reject both raw sources for source-only format |
| Compilation and native geometry | Not evaluated; generated code was not executed |

Both outputs contain incomplete numeric guards, unsupported API routes and geometry intent inconsistent with the contract. The adapter corrects the PicoGK imports and introduces an oversized cutter. These are manual source findings, not compiler diagnostics or measured geometry. Reviewers disagree on downstream failure scoring versus dependency-blocked non-evaluation; that disagreement is retained without a passing claim.

The final adapter SHA-256 is `93f4d64cde2567fa8cffb222360131338fac1f1b737f52584d3bd5c9288c845e`. [results.json](results.json) is an explicit public metadata projection, not an end-to-end reproduction package. It includes receipt/protocol/source commitments; weights, datasets, source bodies and raw receipts are excluded. Resource measurements are sampled, with overlapping conservative memory accounting, not hard OS limits or complete Metal-driver accounting. Reporting prose follows the repository licence and grants no additional rights to underlying training data or code.

One exposed case establishes no independent generalization, scientific validity or Porsche part qualification. Reserved evaluations stayed closed. Scientific Qwen3 and the distinct PR117 Coder/MLX pilot keep their own data and metrics; PR127 preserves earlier negative findings. The adapter is not selected, and the base remains only the comparison reference.

A separate base-only natural-language pilot and offline fence/content diagnostic are recorded in [NATURAL_LANGUAGE_PILOT.md](NATURAL_LANGUAGE_PILOT.md) and [natural-language-results.json](natural-language-results.json), alongside [PR128](https://github.com/cluster2600/porscheparts/pull/128). The train006 results above remain unchanged.
