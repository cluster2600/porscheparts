# Qwen3 compact trial: rejected on registered final test

The first Qwen3 candidate passes 10/12 source-held-out questions and 7/8
additional unseen-paragraph questions under strict assistant passage review.
All 20 expected references and all seven qualification boundaries are correct,
but this does not meet the registered primary threshold of at least 11/12.
Independent scientific and translation review remains pending.

Failures are recorded in `assistant-final-assessment.json`: an unsupported
causal addition, deposited beads mistranslated as droplets, and recoil pressure
rendered as reaction pressure. These are not repaired in the saved outputs.
The paired base scores 10/12 on the primary set; no LoRA accuracy improvement
is established. This trial is not the recommended model.

## Actual training

Qwen/Qwen3-4B-Instruct-2507, revision cdbee75f17c01a7cc42f958dc650907174af0554,
Apache 2.0, 4,022,468,096 base parameters. CPU BF16 q/v rank-8 LoRA trained
2,949,120 parameters for one epoch, 12 optimizer steps, on 24 French/English
factual examples. Training took 686 seconds; mean training loss was 3.7396.
The 144 saved tensors are finite and all 72 LoRA B tensors are nonzero.
Adapter SHA-256: fb6ab78bf8868a1e77e3c1c5e156eeef63b0b3e42378aaa1410e8c7cfaf1d5cb.

## Test scope and provenance

The primary set has 12 questions on eight new paragraphs from two articles
excluded from SFT (Ti6Al4V and WAAM), in FR/EN/DE/ZH. The eight supplemental
French questions use five unseen paragraphs from training-source families;
they are paragraph transfer tests, not article-held-out evaluation.
The source corpus is licensed CC BY 4.0; attribution is in the parent
`grounded-v3/sources.json` and linked license evidence.

Training, inference-profile selection and scientific assessment are separate.
Rejected development attempts remain in `rejected-development/`. The v7 routing
fix yields exact original v6 development inputs; the equivalence receipt labels
reused generations honestly. Final inference used v7. An environment restart
interrupted final evaluation after 11 base answers; the resume script retained
those predictions and generated only the missing base answer, then adapter
tests with the frozen candidate. Interruption and executed-code hashes are saved.

All expert score/reviewer fields remain blank. Neither references, a small
benchmark nor this text model validates a physical simulator or qualifies any
manufactured Porsche part. The registered final set is now retired and may
be used for development, never reported again as untouched final evidence.
