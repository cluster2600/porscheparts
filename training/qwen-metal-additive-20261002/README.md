# Metal additive manufacturing data for Qwen

**For the new passage-grounded pilot, use [the v3 guide](GROUNDING.md) and
`grounded-v3/`.** It fixes a general Qwen Instruct model revision, expands to ten
licensed articles, supplies cited passages in prompts and adds review/evaluation
tools plus a future QLoRA configuration. Expert review remains pending.
The [v2 formatting guide](FORMATTING.md) and `formatted-v2/` remain historical
exports, including the correction to v1's Ti-6Al-4V snapshot/attribution.

The [compact Qwen3 trial](COMPACT_QWEN3.md) has been trained and evaluated;
its [raw final results](runs/qwen3-compact-001/RESULTS.md) are explicitly rejected
(10/12 primary, 7/8 supplemental). The [precision iteration](PRECISION_QWEN3.md)
was actually trained and rejected on development. The
[source-profile iteration](EVIDENCE_QWEN3.md) was rejected early on its primary
test. The [fidelity iteration](FIDELITY_QWEN3.md) retains the conservative trained
weights, separates factual extraction from scope questions and registers a
third test on unused paragraphs. The [verified final package](runs/qwen3-fidelity-001/RESULTS.md)
meets the registered prototype threshold: **11/12 primary, 7/8 supplemental**,
20/20 citations and all seven critical qualification boundaries. The paired
base obtains **12/12 primary**: no LoRA benefit is demonstrated. Retain the base
as the stronger primary benchmark control; the trained adapter is a research
artifact, not evidence of improved scientific accuracy. Human review remains pending.

Owner-requested preparation of the multilingual research corpus, 2 October 2026.
The v1/v2/v3 preparation releases remain historical, frozen inputs. A separate
[CPU BF16 LoRA pilot](CPU_PILOT.md) has now trained a new adapter against the
frozen v3 release. See its [measured results](runs/cpu-lora-001/RESULTS.md);
independent scientific review is pending.

This is a separate sibling of the existing engineering and Porsche-document
experiments. It covers metal additive manufacturing simulation, powder and alloy
quality, heat conduction and diffusivity, melt-pool flow, microstructure,
defects and validation. The model is intended to explain evidence and help
prepare simulations; text training is not a validated numerical surrogate.

## Contents and provenance

The research catalogue contains 79 notices (78 distinct URLs), with primary
source/page languages EN 36, ZH 17, FR 12, JA 5, DE 4, PT 3 and ES 2. Access
levels are explicit: some sources were read only through abstracts or metadata,
and Japanese articles may have been inspected through English abstracts.
The 314 additional HAL records are a discovery list, not a fully reviewed
corpus, and overlap with the catalogue is possible. Their raw abstracts and
restricted full texts are not committed.

Seven full-text English articles have explicit CC BY 4.0 licensing evidence.
Their cleaned text totals 293,547 Unicode characters. Original HTML snapshots,
authors, DOI, license notice, transformation and hashes are retained in
`input/`. Public access alone does not admit any other source to training.
The NIST WebBook compilation and the HAL authorization are not treated as
blanket open training licenses. See [LICENSES.md](LICENSES.md).

| Dataset | Train | Validation | Test | Purpose |
| --- | ---: | ---: | ---: | --- |
| CPT, `text` rows | 81 | 17 | 18 | Candidate domain language-model adaptation |
| SFT, `messages` rows | 47 | 5 | 6 | Technical explanations and metadata extraction |

The 58 SFT examples consist of 30 original synthetic explanations, including
generated translations, plus 28 bounded record-extraction cases (title, DOI,
license or an absent powder-conductivity field). Extraction references are
checked mechanically; that does not validate the scientific explanations.
All 30 original explanations retain their unreviewed status in provenance.
The small test is not a broad metallurgy or independent task-family benchmark.

The 24-term seven-language glossary aids search; it is not counted as additional
independent training evidence. Twelve prototype evaluation questions/rubrics
are preserved separately in `input/evaluation.jsonl`, never added to SFT.

## Frozen source partitions

Training: 316L review (`MET001`), copper review (`MET002`), powder thermal
conductivity (`thermal_en_prediction`), laser thermal-field validation
(`thermal_en_critical`) and melt-pool flow (`thermal_en_flow`).

Validation: IN718 microstructure (`MET003`). Test: Ti-6Al-4V microstructure
model (`MET004`). Every chunk, explanation, translation and metadata case
derived from an article stays in that article's partition. Multi-source cases
are rejected if they cross partitions. CPT and SFT share the same assignment:
pretraining on a held-out article would invalidate the SFT source holdout.

This gives only five training and two held-out publication groups. The source
holdout is useful, but tiny and confounded with alloy/topic. Prompt recipes are
shared; the data do not establish independent-task generalization. An external
expert-reviewed benchmark and experimental/solver campaigns remain necessary.

## Files and reproducibility

`data/cpt/{train,valid,test}.jsonl` contains text-only rows.
`data/sft/{train,valid,test}.jsonl` contains messages-only rows, compatible with
the existing project's training data convention. There are no research metadata
fields in trainer inputs. Attribution and review status remain in
`data/cpt-provenance.jsonl` and `data/sft-records.jsonl`.

The input allowlist is `input/documents.json`; bibliographic references are
`input/sources.json`. `manifest.json` records fixed source assignments, counts,
input/data/script SHA-256 values and limitations. File hashes prove integrity,
not scientific truth. Dataset preparation requires only standard Python:

```sh
python3 training/qwen-metal-additive-20261002/prepare.py prepare
python3 training/qwen-metal-additive-20261002/prepare.py audit
python3 -m unittest discover -s tests -p 'test_qwen_metal_additive.py' -v
```

`prepare` deliberately regenerates this package's derived JSONL and manifest;
it never edits the frozen inputs, prior experiments or adapters. Run `audit`
before any experiment to reject changed frozen data. Unknown-license texts
remain bibliographic references, not training rows.

## Before a training run

The existing repository uses an MLX Qwen2.5-Coder-1.5B instruct experiment on
Apple hardware. These datasets also support a separate Hugging Face Qwen
experiment, but no runtime, GPU or model revision is assumed here. Model license,
base revision, parent adapter, tool versions, seeds and configuration must be
registered for the actual experiment. Do not automatically resume or promote
an existing engineering adapter.

Use the exact local tokenizer and check every complete training example before
selecting sequence length. The research chunks use characters, not tokens;
silently truncating their equations or answers is not acceptable:

```sh
python3 training/qwen-metal-additive-20261002/audit_tokens.py \
  --tokenizer /absolute/local/model --dataset sft --max-length 1024
python3 training/qwen-metal-additive-20261002/audit_tokens.py \
  --tokenizer /absolute/local/model --dataset cpt --max-length 2048
```

This optional command requires `transformers` and `jinja2`, uses local files only
and loads no model weights. The [measured audit](token-audit.json) uses the
project's MLX Qwen2.5-Coder-1.5B tokenizer, revision
`b3252a2f97102b1fb1571fec2c9b27219a8536be`: maximum SFT length 191 tokens,
maximum CPT length 1,215 tokens, with no rows exceeding 1,024/2,048 respectively.
Total training tokens are 7,302 SFT and 51,622 CPT. These are tokenizer counts,
not tokens consumed by a training run. A different model/template needs its own audit.
SFT should use the selected model's chat template and prompt masking; CPT should
use text language modeling. Inspect the intended trainer's handling of `text`
before using CPT; the existing Porsche runner hardcodes different input paths.

Review quantitative claims, flattened HTML equations/tables and translations
before a substantive science training run. There is no human-expert approval
or claimed model performance. Compare the base model, retrieval and any adapted
model on the same registered evaluation, with citations and unit checks. Keep
validation/test examples out of all replay data, including translations.

## Practical limitations

The reusable full-text corpus is English despite seven-language discovery.
Source-conditioned metadata extraction measures reading a supplied record,
not metallurgical expertise. Synthetic explanations do not provide calibrated
temperature fields, distortion, porosity or fatigue predictions. Build those
surrogates from independently documented experiments/solver data, with machine,
material, geometry, process, units, uncertainty and campaign-level partitions.

No source summary, successful data check or generated answer qualifies a
Porsche component for manufacture. The existing independent-interface,
material-qualification and professional-review rules remain applicable.
