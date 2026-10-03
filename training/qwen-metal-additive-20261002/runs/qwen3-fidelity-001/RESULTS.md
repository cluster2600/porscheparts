# Third registered fidelity cycle: measured results

The selected Qwen3-4B adapter meets the registered prototype threshold: **11/12 primary and 7/8 supplemental**, with all 20 expected citations and all seven critical qualification boundaries correct. No answer reached the generation limit. These are assistant source-by-source assessments, not independent human expert validation.

The paired base control obtains **12/12 primary**, including all four primary critical boundaries and citations. Its answer includes the gradual transition omitted by the adapter on fidelity-01. Six primary responses are identical. **No scientific benefit from LoRA is demonstrated**; the base performed better on the only changed grade. The base supplemental benchmark was not run. Inference instructions and upgrading the base are confounded with earlier trials; improvement over those trials cannot be attributed to training.

## What was actually trained and selected

Qwen/Qwen3-4B-Instruct-2507 at cdbee75f17c01a7cc42f958dc650907174af0554; CPU BF16 LoRA rank 8 on q/v projections, 2,949,120 trainable parameters. Actual compact training used 24 FR/EN rows from six training article families, 1,388 assistant tokens, one epoch and 12 optimizer steps; 686.187 seconds and recorded mean loss 3.7396. The selected weights are unchanged: fb6ab78bf8868a1e77e3c1c5e156eeef63b0b3e42378aaa1410e8c7cfaf1d5cb.

The separately trained 59-row, 30-step precision adapter was rejected on development. Earlier failed inference profiles and the first rejected compact final test are preserved separately. A review erratum corrects an earlier mistaken fatigue claim without rewriting that archive.

The task-v14 inference profile routes by question wording alone between frozen factual and qualification-scope instructions. It supplies no case-specific answers. Selection used 15 retired development examples: 11 predictions were reused only after exact input, model, settings and prediction provenance checks; four were generated anew. Those development examples are not new test results.

## Evaluation and limitations

The third test was registered before generation and has 20 distinct unused source paragraphs. The 12 primary questions use two article families excluded from project SFT; those articles were seen during development and pretraining exposure is unknown. The eight supplemental questions use new paragraphs from training articles. This is evidence-conditioned question answering, not unseen scientific concepts, autonomous retrieval or a numerical solver.

Primary fidelity-01 fails for omitting the requested gradual transition. Supplemental fidelity-domain-03 correctly compares solid fraction and conductivity but adds an unsupported dominant-influence inference, so the root review conservatively fails it. The second assistant graded that answer as passing with a reserve; both decisions are retained. Some French terminology and study-condition summaries require editing. Training translations and scientific correctness still require human review.

All outputs, input expansions, source hashes, runtime inventory, frozen selection, raw control predictions and rejection archives are retained. The paired control disables the adapter in the same loaded pinned base, using identical prompts and greedy generation settings. No test result was used to switch checkpoints.

## Use and verification

Run `python training/qwen-metal-additive-20261002/verify_fidelity_package.py --output training/qwen-metal-additive-20261002/runs/qwen3-fidelity-001` to verify the package. Use `answer_metal.py` with this package's `adapter/`, a registered passage, an explicit question and a cache directory; the packaged profile is selected automatically. See FIDELITY_QWEN3.md for commands. Citation/completeness guards do not establish scientific truth or qualify manufactured parts.
