# Base-only natural-language pilot (NL8)

The original Qwen2.5-Coder base was rejected for this frozen pilot. Eight exposed, dependent development requests were compared with the existing deterministic labelled baseline. The model produced 0/8 correct raw responses versus 5/8 for the baseline, and 0/3 critical responses versus 3/3. Paired wins were 0 and losses 5. The baseline is retained; no model adoption follows.

The base-only generation completed in 14.325 seconds with recorded clean terminal supervision, eight EOS completions and 66 unchanged bindings. Peak sampled conservative memory was 2.4758 GiB. These are sampled measurements with soft timers, not hard OS limits or exhaustive Metal accounting. No adapter, training, retry, output repair, generated-code execution or CAD run was involved.

An independently reviewed offline diagnostic examined the same eight existing outputs. It removed only a complete outer fence pair and preserved the enclosed bytes. Internal strict JSON syntax passed 8/8; the frozen schema passed 0/8. All eight semantic comparisons stayed blocked by invalid schema, with null match values. No repaired semantic score was computed, and the original result is unchanged.

| Descriptive observation | Exposed case indices |
| --- | --- |
| Wrong clarification action for a determined or invalid request | 01–04, 07 |
| Numeric fields align, but the accepted status and missing unit violate the schema | 05 |
| Clarification action is compatible, but the compound reason is invalid | 06, 08 |

These observations are not replacement scores. Removing fences alone does not satisfy the contract. The diagnostic reviewer was independent of its author, while retaining prior knowledge of the intentions, preparation and raw results. The analysis attributes no defect to a particular training, prompt or decoding cause.

[Public metadata and evidence commitments](natural-language-results.json) accompany this report in [PR128](https://github.com/cluster2600/porscheparts/pull/128). Raw outputs, dataset, prompts/golds, generated code and weights are excluded. This metadata projection is not an end-to-end reproduction package. Earlier train006 results remain unchanged; scientific Qwen3 and the distinct PR117 Coder/MLX pilot keep separate data and metrics. Reserved evaluations and CAD gates remain closed. No generalization, scientific validity or Porsche part qualification is claimed.
