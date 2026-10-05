# Reserved paired evaluation rubric

This is an assistant-authored research pilot. It does not validate an experiment, a manufacturing recipe, a component, a fit, or a release. New questions and gold criteria are held outside the training checkout. Familiar historical articles, possible full-text exposure and unknown base pretraining exposure preclude a claim of unseen-source generalization.

## Registration and separation

The reservation contains 24 questions: 16 primary and 8 supplemental, including 10 critical cases; 12 are in French and 12 in English across four source families. French and English coverage does not imply 24 independent scientific concepts. Article families must be reported alongside overall counts.

Only `registration.json`, `coverage-and-commitment.json` and this rubric may be read by the training lead before candidate freeze. Their roster contains identifiers, family/suite/critical metadata and input commitments, without prompts or gold. The private pool, its authoring script and every excerpt/question/gold are excluded from training, retrieval preparation, prompt tuning and checkpoint selection. None may be copied into the lead checkout. The independent custodian retains the private pool for the final run.

Freeze the selected adapter bytes and their SHA-256, protocol SHA-256 and registration SHA-256 in a selection receipt before opening reserved inputs. Selection must use development evidence only. Use the unchanged `task_routed_v14` expanded messages for both arms, with the same pinned model revision, runtime and tokenizer, greedy decoding and a 192-token ceiling. Log identical per-item input hashes, response hashes, output token counts, any budget hit, model/adapter/runtime identities and failures. The registration binds the raw file bytes; input hashes use canonical JSON with sorted keys, UTF-8, `ensure_ascii=False` and separators `(',', ':')`.

All historical published questions and outputs remain development material. Generate the reserved base and selected candidate once in one paired run after freezing; do not train, select a different checkpoint, change a prompt or repair an answer after inspecting reserved outputs. A failed or interrupted run is recorded and requires a justified technical recovery that preserves selection and inputs. Never count an uncompleted row as a pass.

## Per-answer grading

Two independent assistant graders receive anonymous answers in shuffled order with the supplied evidence and sealed gold criteria. They score each arm separately before receiving arm identities or aggregate results. They must record an evidence location and a short explanation for each failure. Assistant grading is not human engineering review. A disagreement is conservatively scored as a failure; retain both original judgments.

A pass requires all requested facts and their material qualifications, an appropriately useful answer in the requested language, an exact supporting reference, and no substantive unsupported addition. Accept faithful paraphrases and explicitly justified equivalent unit conversions. Do not require a literal template, extra facts that were not requested, or stylistic preferences. A generic refusal fails when the excerpt supplies a supported answer; an invented answer fails when evidence is absent.

Grade the following dimensions independently:

- **Evidence and citations:** the reference exists in the supplied evidence and supports the exact associated claim. Reference-label presence is insufficient. A citation to a true source does not license an unsupported inference or merge conditions from different studies.
- **Quantities and conditions:** preserve quantity identity, dimension, unit, scale, sign, temperature, rate, process, alloy/material, specimen orientation, test type, treatment, sample/statistical scope and applicable reported conditions. Do not turn a rate into a temperature, machine speed into strain rate, or an omitted value into zero.
- **Scientific meaning and translation:** retain modal words, uncertainty, comparison direction, qualifiers, exceptions and the subject of a reported trend. Preserve the difference between an observation, proposed explanation and established cause in both languages.
- **Causality and scope:** do not infer dominance, sufficiency, universality, causality or a numerical optimum that is not supported. A source's measurement or statement does not establish a new part's property or qualification.
- **Engineering boundaries:** distinguish evidence records and parameter definitions from admissible measurements; preserve conflicts, missing inputs, provenance, rights and uncertainty. Refuse qualification or release when required component-specific measurements and review are absent, while stating what the evidence can support.
- **Completion:** an exhausted generation budget, truncation, missing requested fact, unsupported substantive addition or failed generation prevents a pass. A valid concise answer may omit unrelated source details.

Failure tags are `citation`, `unsupported_addition`, `unit`, `condition`, `translation_or_qualifier`, `causality`, `scope_or_qualification`, `missing_requested_fact`, `unhelpful_refusal`, `budget_or_generation`, and `grader_disagreement`. A row can receive more than one tag. Primary and supplemental suites are scored separately as well as jointly.

## Registered pilot decision

The selected candidate passes this limited gate only if it obtains at least 22/24 acceptable responses, at least two net paired gains over the base, all 10 critical cases pass, and there are zero critical regressions, unsupported citations, unit/condition failures, causal failures or generation-budget hits. These zero-tolerance conditions apply even when the overall count would otherwise pass.

Report the paired 2-by-2 table, gains and losses with failure tags, results per family and language, and exact McNemar discordance statistics with uncertainty. The acceptance threshold is an operational pilot rule; two wins and zero losses have an exact two-sided discordance p-value of 0.5 and do not establish a reliable scientific gain. Related source-family cases are not independent replications. Do not transfer results from the separate PR117 Qwen2.5-Coder/MLX experiment.

Allowed conclusions include `pilot_gate_passed_with_limited_evidence`, `inconclusive_base_retained`, and `candidate_rejected`. None licenses fabrication, engineering qualification, general capability claims or release. Report every remaining blocker and retain all frozen inputs and raw outputs for the final independent review.
