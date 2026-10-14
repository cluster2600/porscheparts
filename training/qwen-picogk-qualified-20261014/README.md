# Independent PicoGK 50/60 qualification and request contracts

This implements the [14 October roadmap](../qwen-picogk-robustness-20261013/ROADMAP.md).
It compares the retained r3 and completed paired adapters on fresh five-language
requests, separates raw-model and canonical-input accuracy, and resumes local
MLX training only if the paired candidate misses development or retention gates.
The historical experiment's rejected results and closed final set stay unchanged.

## Scope and registered gates

The course covers cylinder, pipe, washer, BCC cell, synthetic thread cutter and
missing/unverified-interface refusal. Its 60 development and 60 reserved final
requests each contain 12 examples per language and ten refusal cases. Selection
requires 50/60 raw passes, at least 8/12 in each language, all ten refusals,
48/48 old native plans, 16/16 old native code tasks and no lost retained-baseline
pass on fresh or labelled historical development requests. A canonical-input
score cannot substitute for a raw score.

Owner-authored dimensional intents are disjoint from old course/paired/legacy
intents and across new partitions. Training contains 300 new geometric intents
with radius/diameter pairs, 120 refusals, and the verified 688-row old replay
twice: 2,096 rows in total. Phrase wrappers and field presentation differ across
training, development and reserved final; recipes and some field vocabulary
remain shared. This is bounded synthetic evaluation, not unseen API-family
generalisation or Porsche inspection evidence.

At most one fixed 240-step continuation at 0.0000025 is allowed, from the paired
adapter. It retains the same base, context, greedy decoding and EOS boundary.
One candidate is selected on development before the new final set is opened
once. Failed scores, preparation directories and native timeouts are preserved.

## Running on the existing recovered Mac

The scripts depend on the archived prior experiments and hash-pinned local MLX
runtime. They are not a fresh-machine installer. Use a new private directory;
weights, queries, raw responses, meshes and logs remain outside Git.

```sh
~/Developer/Qwen993/venv/bin/python \
  training/qwen-picogk-qualified-20261014/qualify.py prepare \
  --work ~/Developer/Qwen993/qualified-20261014
~/Developer/Qwen993/venv/bin/python \
  ~/Developer/Qwen993/qualified-20261014/source/training/qwen-picogk-qualified-20261014/qualify.py run \
  --work ~/Developer/Qwen993/qualified-20261014
```

Preparation verifies the old frozen inputs and recovered base, then copies code,
native dependencies, adapter inputs and data into this new experiment. macOS
uses APFS copy-on-write clones for the native runtime to limit disk consumption.
The protocol is written and hash-frozen before inference. Execution uses the
copied scripts; later repository edits cannot silently change this trial.
Each registered file is reverified through the existing bounded integrity
checker before and after evaluation. A failed driver does not produce a
qualified profile. Re-running into an existing output directory is forbidden.

Old SDK files under Documents may be iCloud placeholders. Preparation records
every such SDK relocation and verifies the exact historical expected hash
against the corresponding retained local SDK file. Other input types receive
no substitute. The new native copy lives under Developer rather than iCloud
Documents. This restores available bytes without rewriting historical hashes
or asserting that the original placeholder paths were readable.

## Numeric boundary

[request_contract.py](request_contract.py) requires explicit named fields,
units (`mm`, `cm`, `m`) and quantity types (`length`, `radius`, `diameter`).
French/German decimal commas are supported; grouping, ambiguous quantity types,
missing fields, booleans, nonfinite values and out-of-bounds recipes fail closed.
Only requests marked synthetic can generate a geometry proposal. Missing or
unverified interfaces return `needs_measurement` without calling the model.

For a pipe, named `length`, `outer` and `inner` fields map to
`[length, outerRadius, innerRadius]`. A value's quantity describes the supplied
measurement, not its final stored role. BCC `beam` stores a diameter, so an
explicit beam radius is doubled. Field order has no effect.

Example request file:

```json
{
  "recipe": "pipe",
  "language": "fr",
  "interface_status": "synthetic",
  "fields": {
    "outer": {"value": "0,85", "unit": "cm", "quantity": "radius"},
    "inner": {"value": "0,4", "unit": "cm", "quantity": "diameter"},
    "length": {"value": "0.012", "unit": "m", "quantity": "length"}
  }
}
```

Its independently required parameters are `[12,8.5,2]` mm. The canonical prompt
is derived only from this request. It never reads evaluation gold answers.
The returned model plan must match the independently converted request and
reach EOS; plausible but different values are rejected. This assisted mode
does not establish raw multilingual understanding.

## Qualified inference and rollback

Only a successful raw development, native retention and fresh final result
creates `qualified-profile.json`. Install after qualification:

```sh
~/Developer/Qwen993/venv/bin/python \
  ~/Developer/Qwen993/qualified-20261014/source/training/qwen-picogk-qualified-20261014/qualify.py install \
  --work ~/Developer/Qwen993/qualified-20261014
qwen-picogk-qualified --request ./synthetic.json --output ./proposal.json
```

The installed command pins its profile hash. The loader checks raw thresholds,
retention, receipt hashes, path containment, selected weights, frozen inputs,
runtime packages and protocol before inference. It preserves exclusive runtime
locking and rejects existing output files. It returns a contract-verified plan;
it executes no geometry or model-generated code. The existing `qwen-picogk`
command remains available with its exact retained r3 adapter and interface.

No external Hugging Face model or dataset is imported. The roadmap's related
CAD research informs the method; licenses and incompatible architectures remain
as recorded. Broader library curricula are separate from this six-recipe profile.
