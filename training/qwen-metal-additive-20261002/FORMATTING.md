# Qwen training exports, version 2

Use **`formatted-v2/` for subsequent training**, rather than the historical
character-based `data/` export. Formatting is optimized for the project's
Qwen2.5-Coder-1.5B tokenizer/template; it is not a universal optimum or a
measured learning improvement. No model training is performed.

## What changed

- Scientific prose is extracted again from DOI/title-verified licensed snapshots.
  Paragraphs remain whole and in order, with no overlap or repeated tail text.
  Contiguous paragraphs of one source are grouped up to 2,048 tokens including
  one EOS. Formula/image-bearing paragraphs, tables, figure captions, references,
  administrative text and short labels are conservatively excluded; reason,
  source paragraph number and original hash remain in `quarantine.jsonl`.
- Unicode normalization is NFC, preserving scientific superscripts and symbols;
  whitespace and numeric bibliography markers are cleaned. This is an automated
  quality filter, not scientific review. Some unrecognized math may remain.
- Technical SFT is separate from optional metadata extraction. The default has
  30 explanations (27 train, one validation, two test); the optional set has
  28 metadata cases (20/4/4). Their source partitions match CPT.
- Native `system/user/assistant` messages stay the portable canonical format.
  Technical prompts include the reference identifiers cited by their targets.
  These references are bibliographic context, not paragraph-level evidence.
- Tokenized SFT uses the actual native chat template exactly once. Labels are
  `-100` for system/user tokens, role headers and the final trailing newline.
  Only assistant content and its EOS contribute to loss. CPT predicts all tokens
  including one EOS and uses no chat wrapper.
- Rows are unpadded. No SFT examples are concatenated, and no sequence is silently
  truncated. Exact duplicates are rejected; whole sources stay in one partition.

## Provenance correction

The v1 export accidentally associated the Ti-6Al-4V article (`MET004`) with an
unrelated UFU repository-page snapshot. Its cleaned Ti-6Al-4V body and DOI/title
were correct, but that attached snapshot and derived author attribution were
wrong. V2 uses `format-input/met004-correct-article.html`, checks the DOI
`10.3390/met8080633` and article title, restores Salsi/Chiumenti/Cervera attribution,
and retains the article's explicit CC BY 4.0 notice. The correction is documented
in `format-input/corrections.json`.

Frozen v1 inputs remain historical records. **Do not use v1's MET004 snapshot or
attribution as evidence for the article.** V2's `sources.json` is the corrected
attribution registry for the new trainer files. No article is promoted to
expert-reviewed status by this correction.

## Exports

| Directory | Schema | Use |
| --- | --- | --- |
| `cpt_text/` | `{"text": "…"}` | Domain language-model text; tokenize with the selected model |
| `cpt_tokens/` | `input_ids`, `attention_mask`, `labels` | HF causal-LM inputs with a registered EOS |
| `sft_messages/` | `{"messages": [...]}` | Default technical SFT for MLX/HF/LLaMA-Factory |
| `sft_tokens/` | `input_ids`, `attention_mask`, `labels` | HF technical SFT with assistant-only loss |
| `metadata_messages/`, `metadata_tokens/` | Same conversation/token schemas | Optional metadata exercise set |

Each directory has `train.jsonl`, `valid.jsonl` and `test.jsonl`. CPT contains
49 sequences (36/5/8). The tokenized exports are bound to the exact tokenizer
files and template hash in `formatted-v2/manifest.json`; never feed them to a
different Qwen vocabulary. Raw message/text exports can be retokenized for a
different model after auditing its native template and sequence lengths.

The maximum registered lengths are 2,042 tokens for CPT, 370 for technical SFT
and 191 for metadata SFT. Small validation/test partitions remain a limitation;
the source holdout is confounded with alloy/topic. No model score is claimed.

## Loading and loss handling

**MLX:** use `sft_messages/` with the selected tokenizer's native chat template
and prompt masking. For `cpt_text/`, verify the installed trainer's plain-text
support and EOS policy. Do not add a second EOS when loading `cpt_tokens/`.

**Hugging Face:** `datasets.load_dataset("json", data_files={...})` reads either
form. Tokenized rows already contain labels; use dynamic padding preserving
them (for example `DataCollatorForSeq2Seq` with `label_pad_token_id=-100` and
`padding=True`). Do not use a collator that recreates labels from `input_ids`,
or system/user masking will be lost. Padding must have attention mask zero and
label `-100`. Register the exact model/template and use `AutoModelForCausalLM`.

**LLaMA-Factory:** point `dataset_dir` to `formatted-v2/`. Its
`dataset_info.json` registers `metal_sft_train`, `metal_sft_valid`,
`metal_sft_test` and the optional metadata datasets using native messages with
explicit ShareGPT role/content mappings. Select the correct Qwen template,
`cutoff_len: 1024`, `train_on_prompt: false` and `packing: false` for technical
SFT. Confirm these options against the installed version; the trainer has not
been run here. Do not include test data in training or validation selection.

No balanced-language duplication or automatic mixing with the 28 metadata
cases is performed. These are only 30 synthetic scientific examples; formatting
does not turn them into a complete specialist dataset. Review targets,
quantitative claims and translations before a substantive training experiment.

## Reproduction and verification

For generation, install the versions recorded in the manifest (`transformers`,
`tokenizers`, `beautifulsoup4`, `jinja2`) and supply the exact local tokenizer.
No model weights or network are required by the formatter:

```sh
python3 training/qwen-metal-additive-20261002/format_qwen.py \
  --tokenizer /absolute/local/model-tokenizer \
  --output work/qwen-metal-new-export --cpt-limit 2048 --sft-limit 1024
python3 training/qwen-metal-additive-20261002/verify_formatted.py
python3 -m unittest discover -s tests -p 'test_qwen_metal_format.py' -v
```

Generation refuses to overwrite an existing export. The verifier needs only
standard Python and checks hashes, attribution coverage, source partitions,
token limits, EOS, raw/tokenized correspondence and assistant loss spans.
The generator additionally validates native tokenization and snapshot DOI/title.
