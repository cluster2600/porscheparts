# Porsche corpus preparation

This offline pipeline inventories immutable Git snapshots, records declared
technical metadata, and builds explicitly reviewed local derivatives. It does
not train, evaluate, download a model, crawl a forum, install dependencies or
change production. Catalogue records remain the authority for part status.

The tooling is suitable for a public pull request. **Mixed outputs from a
private repository remain local** in `data-engineering/private/`, which is
ignored. A `public/` directory inside a private repository proves neither public
availability nor reuse permission. Observed website pages and repository
versions are separate sources until an item-specific relationship is established.

## Reproducible workflow

Use Python 3.10+ and Git already available on the host. The inventory and
reconciliation commands use the standard library. Optional tokenization requires
an existing `transformers`, `tokenizers` and `jinja2` environment and the exact
local tokenizer assets; missing dependencies are a blocker, not an install step.

```sh
python3 data-engineering/porsche-corpus/pipeline.py build \
  --config /path/to/private-config.json --output /path/to/new-output
python3 data-engineering/porsche-corpus/pipeline.py audit \
  --output /path/to/new-output
python3 -m unittest discover -s data-engineering/porsche-corpus/tests -v
make check
```

The configuration records an observation timestamp, exact 40-character commits,
verified repository URLs, visibility, bounded JSON allowlists, excluded roots
and explicit reviewed items. `example-config.json` describes the schema with
placeholder paths and hashes. Supply an actual reviewed configuration before
running it. There is no default licence grant or automatically generated gold.
An existing output directory is rejected. Original checkouts are read only;
only frozen Git objects are read, with symlinks and submodules never followed.

The complete tracked tree is counted by source, file type, topic and bytes.
Only selected JSON records are projected into whitelisted technical fields.
Free prose, account/user/contact fields, session logs, credentials, raw scans,
ignored private trees and reserved evaluations are excluded from content reads.
Schema/API definitions, occurrences, source records, parameters and examples
are different quantities. Material/process tags are declared assertions; an
`unknown` process is an explicit unknown. File hashes establish integrity,
not scientific or physical truth. A source timestamp is not a file's unknown
last-modification time.

## Outputs and qualification

| Output | Purpose |
| --- | --- |
| `inventory.jsonl`, `coverage.json` | Tracked-file denominator, bytes, scope, disposition and read coverage |
| `structured-audit.jsonl` | Counts by field, source family and missing metadata; no full supplier/manual copy |
| `source-lineage.json`, `lineage.jsonl` | Original-source aliases, exact Git-blob duplicates and admitted-text proximity |
| `source-corpus.jsonl`, `split-ledger.json` | Explicit included texts, grants, hashes and connected source/project groups |
| `rag-references.jsonl` | Reference metadata for uncertain rights; no protected source bodies |
| `rag_context/` | Reviewed reusable passages, retaining provenance in the source corpus |
| `cpt_text/`, `code_text/` | Separate text and code continuation candidates |
| `sft_messages/` | Imported reviewed dialogues, canonical native messages |
| `quarantine.jsonl`, `readiness.json`, `manifest.json` | Explicit blockers, immutable integrity evidence and bounded readiness |

Only hash-pinned reviewed items with rights evidence, attribution where required,
source/project families and an explicit evidence state enter text exports.
The owner's request permits local preparation of their original project code
and prose. It does not grant rights over third-party works or publication of
private data. Item-specific CC BY notices keep their authors and transformation
history. Unknown licences remain references/quarantine. Hypotheses, forum claims,
supplier assertions and rejected/non-converged CFD stay qualified; this tool
does not turn them into factual SFT or numerical surrogate data.

Partitions follow connected source/article/project families, explicit anchors
and known lineage. Exact normalized copies and high-overlap lexical 5-grams are
linked before assigning splits. Conflicting anchors quarantine the entire group.
Already exposed historical tests become `dev`; validation families stay `valid`.
New sealed reserves are never read or produced. Missing reviewer boundary metadata
keeps new candidates in development. Protected prefixes cannot be overridden by
an allowlist. Lexical proximity is a limited detector; multilingual semantic
duplicates and unknown copying chains still need independent review. Forum and
site mirrors do not count as independent confirmation of their original sources.

## Existing prepared corpora

`reconcile.py` provides a narrow adapter for the existing metal-additive package.
It verifies the approved historical **train** roster, source/paragraph hashes,
article-specific CC BY 4.0 notices and the lead's source-family/retired-excerpt
contract. It reads no evaluation question, rubric or gold file. Validation and
old test families remain excluded; retired paragraphs are recorded by metadata
only. The original source metadata and authors are retained, and incomplete
scientific/translation review stays visible. These are conditional candidates
for a separately registered experiment, not automatic admission to an active
frozen experiment.

```sh
python3 data-engineering/porsche-corpus/reconcile.py \
  --root /path/to/frozen-porscheparts \
  --contract /path/to/model-and-exclusion-contract.json \
  --exclusions /path/to/historical-exclusion-metadata.json \
  --output /path/to/new-science-candidates
```

Historical dialogues are retained unchanged. If a historical release lacks
`raw_messages`, the field stays null; the tool does not reconstruct or invent
the lead's `task_routed_v14` expansion. New source-grounded conversations should
preserve both pre-expansion `raw_messages` and the exact bound `messages` with
the task-profile/helper hashes. Reasoning examples should state what evidence
is missing and what would resolve it; they must not invent measured values or
manufacturing approval. No answer generation is part of this pipeline.

For reviewed Python code that exceeds the whole-row token budget,
`code_units.py` attempts complete functions/classes with their transitive imports,
constants and helper definitions. It preserves original bodies, constraints,
comments, ordering, source ranges and range hashes. All units retain their
parent source family/split; repeated dependency context is not additional
independent evidence. Module initialization effects, rebound names, wildcard
imports and dynamic namespace access fail closed for manual review. Complete
units that still exceed the fixed budget remain quarantined. Syntax/dependency
checks do not claim portability beyond the original module/repository context.

```sh
/path/to/existing/python data-engineering/porsche-corpus/code_units.py \
  --corpus /path/to/verified-corpus --profile /path/to/exact-coder-profile.json \
  --tokenizer /path/to/pinned-local-snapshot --output /path/to/new-code-units
```

## Model-specific length and loss

Keep Qwen3 scientific and Qwen2.5-Coder profiles separate, with model ID,
revision, asset SHA-256 values and native chat-template SHA-256. A shared vocabulary
does not permit reusing another model's formatted arrays. `format_tokens.py`
loads local tokenizer assets only and verifies their exact hashes. It uses the
native template once, without hand-added thinking tags. Qwen3 Instruct-2507
supports non-thinking mode; its template does not take `enable_thinking`.
See the [official Qwen guide](https://qwen.readthedocs.io/en/latest/getting_started/quickstart.html).

```sh
/path/to/existing/python data-engineering/porsche-corpus/format_tokens.py \
  --corpus /path/to/verified-corpus --profile /path/to/exact-profile.json \
  --tokenizer /path/to/pinned-local-snapshot --output /path/to/new-token-audit
```

The initial preparation limits are 2,048 tokens for continuation and 1,024 for
SFT, configurable per profile. Each complete row is measured. Over-length rows
are quarantined without truncation, preserving equations, qualifiers and answers.
No padding or cross-example packing is performed. CPT supervises text and one EOS.
SFT supervises assistant content through EOS; role headers, system/user tokens
and trailing whitespace have `-100` labels. Offset boundaries, native transcript
identity, EOS and role-token injection are checked. Unsupported template expansions
fail closed and need a separately reviewed mask adapter.

Passing an integrity/token audit does not qualify scientific explanations,
manufacturing, fit, fatigue, CFD fields or model performance. Readiness remains
explicit until scientific/translation review and separate experiment registration
are complete. Prepared rows and actually trained rows must be reported separately.
