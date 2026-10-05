# Data preparation contract for further corpus work

This describes the current Qwen3 scientific format. It does not admit additional
sources into the frozen continuation experiment or its independently held reserve.
The larger corpus engineering task must pass provenance, content and split gates
before a separately registered training experiment.

## Source and claim gate

Every admitted excerpt needs a stable source ID, original URL/title/authors,
item-specific reuse licence and retained evidence hash, original artifact hash,
exact locator and excerpt hash, transformation notice, prior-exposure status,
source family and expert/translation review state. Record third-party figures,
forum posts, proprietary scans and uncertain rights separately; public visibility
alone is insufficient. Record unknown values, contradictions, variants and
measurement conditions explicitly. A parameter definition, equation or hypothesis
is not a measured value. Code compilation and tests do not validate physical facts.

Keep article families, near duplicates, translations, derived documents and
related question variants together for split assignment. Previously read data,
responses and prompts remain development/training. Do not recycle them as reserved
items. FR/EN versions are two language rows but one underlying learning objective.

## Current training JSONL

See [train-records.jsonl](data/train-records.jsonl). Each row contains `id`,
`source_id`, `passage_id`, `language`, `learning_objective`, `question`, `response`,
`excerpt`, `excerpt_sha256`, `provenance`, `prior_exposure`, `answer_origin`,
`authorship`, `expert_review`, `inference_task_route`, `raw_messages`, `messages`
and `correction_of_historical_rows` where applicable. Provenance includes source,
passages and licence paths/hashes and the exact paragraph locator. Messages are
ordered system/user/assistant. `raw_messages` retain the source-conditioned
conversation before expansion; `messages` are its exact frozen task_routed_v14
expansion. The assistant mask supervises its response through EOS, with other
tokens ignored. Keep short source-backed claims and their units, conditions,
qualifiers and citation together. Preserve distinctions between observation,
author interpretation and causal proof.

[manifest.json](data/manifest.json) binds ordered rows, hashes, source families,
licence notices and frozen profile inputs. [audit.py](audit.py) checks the format,
exact excerpts, historical train-only source boundary, retired paragraph exclusion
and deterministic expansion. This verifier is specific to the present six source
families; admitting new sources requires an explicit new boundary and independent
review, rather than bypassing its rejection.

## Evaluation separation

Development question JSONL uses `id`, `suite`, `source_id`, `source_family`,
`critical`, `question`, `language`, `passage_id`, `raw_messages`, exact expanded
`messages` and `input_sha256` of canonical sorted compact UTF-8 JSON. Registration
binds file bytes and ordered roster. Keep expected answers and claim rubrics
separate from generation inputs. Base and adapter must receive the same inputs,
runtime and decoding. Grade source support, factual usefulness, unit/condition
pairing, causal restraint and qualification separately from token loss.

The independent custodian holds the current 24-item reserve closed. Its public
counts and commitments may be recorded; its prompts, answers and author scripts
must not enter ingestion, tuning, retrieval or selection. Broader corpus work
must not alter this pool to compensate for incomplete training coverage.
