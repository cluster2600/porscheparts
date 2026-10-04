# Local research LoRA continuation: pilot 002

Pilot 002 trained a separate Qwen adapter for 480 additional steps. On the new,
bounded synthetic validation it improved from **0/32 to 30/32**, under both the
pre-registered coverage rubric and the unchanged exact JSON metric. The gate
failed because two categories reached only 7/8. Both new and original final
tests remain closed, and the adapter is not selected or made the default.

The earlier ten-case development diagnostic regressed from 6/10 to 5/10; its
temperature/duty contradiction persists. Native coding retention stayed at
16/16. These results support a narrow improvement in the new extraction tasks,
with insufficient transfer to the earlier reasoning cases or useful retrieval
answers. The [machine-readable metadata](results-002.json) records settings,
scores, hashes and limitations. [Pilot 001](results-001.md) is preserved.

## What was added to training

The new private dataset is
`private/training-002`.
It replays all 82 admitted training cases from pilot 001 unchanged and adds
192 original synthetic cases: 48 for each of four evidence-coverage tasks.
The new observations are hypothetical exercises, not measurements of a Porsche
or experimental material results.

| Task | Training purpose |
| --- | --- |
| Temperature | Quote the actual test condition and identify missing evidence for a different requested condition. Matching temperature alone does not qualify a component. |
| Variant | Distinguish the supplied original, aftermarket or prototype identity from the requested component. Supplied variant coverage does not establish fitment. |
| Independence | Separate measurements used for fitting from measured points withheld from fitting. These fixtures do not establish physical validation. |
| Citation | Retrieve the named observation, copy its exact opaque ID and preserve a runout as a stopped test without failure. Refuse a genuinely absent observation. |

Each new prompt contains three shuffled records: the relevant observation,
an unrelated observation and a source note that asks for an invented citation
and approval. Source extracts remain untrusted data. The correct record slot,
identifier shape, values and named scenario vary. The system asks for the
observed finding verbatim and its supplied ID.

The new active split is **274 training / 32 validation / 16 test**. The new
scenarios, prompts and identifiers are disjoint, but task recipes are shared.
The original ten validation and eight test cases are retained separately under
`legacy-evaluation/`; neither enters the new training input. Only the old
validation is used for the separate development diagnostic below.

The inherited index still contains 4,939 research records. Its original rights
and reading boundaries remain in force: the 658 excluded candidates, raw PDF
pages, third-party figures and unreviewed spreadsheet cells are outside SFT.
All 36 admitted NIMS fatigue observations remain in training, so no held-out
fatigue-transcription generalisation is measured. The 142-file frozen dataset
passed integrity verification before and after the run; the longest active
sequence is 669 tokens.

## How the model was trained

The model is the cached MLX four-bit conversion of
`Qwen2.5-Coder-1.5B-Instruct`. The parent is pilot 001's adapter, SHA-256
`5086fc5cf5d9c2de05cc87b1d7efed5036f5b2431c62c13368955501c1810ec8`.
The new adapter is
`b702886b119f53ca94ad9294fddbd85891e806b4dcd18c53a537808c1e9a6c90`.
The base model and all previous adapters remain unchanged.

| Setting | Value |
| --- | --- |
| MLX-LM | 0.31.3, existing local runtime, offline model cache |
| Fixed training length | 480 additional steps; only the final checkpoint is evaluated |
| Learning rate / batch / seed | 0.000005 / 2 / 1042 |
| LoRA | 16 layers, rank 8, scale 20, dropout 0 |
| Trainable parameters | 5.276 million, approximately 0.342% of the loaded model |
| Loss | Prompt masked; assistant response tokens contribute to training |
| Maximum sequence length | 1,024 tokens |
| Assistant tokens trained | 66,182, including repeated passes through examples |
| Validation loss | 0.459 initially; 0.001 at step 480 |
| Final reported training loss / peak MLX memory | 0.002 / 5.654 GB |

The preserved runner is reused with the continuation parent, a fixed 480-step
command and the new rubric. These substitutions and the continuation source
hash are recorded before baseline inference. Dataset, model, parent, code,
selected native cases and runtime hashes are checked after evaluation. The
citation-schema helper matches the registered Git commit; its separate hash
witness was taken during training, before candidate evaluation, and is labelled
as supplementary rather than a separately pre-registered file hash.

Private receipts, native witnesses and weights are in
`private/pilot-002`.
Only documentation, helper code and non-sensitive result metadata are in Git.

## What the registered evaluation measures

The coverage rubric requires the supplied finding and exact record ID, followed
by the correct evidence-coverage conclusion. It normalises case, Unicode and
whitespace and accepts a finite list of missing-evidence phrases authored
before inference. Duplicate JSON keys, unknown citations, unsupported quotes,
wrong conditions, missing required uncertainty and extra fields fail. The
unchanged exact metric is reported alongside it; both give 30/32 here.

This rubric is not a general semantic scientific-answer grader. The experiment
is adaptive to the observed failures of pilot 001, with shared synthetic
recipes. Its scenario separation does not create independent engineering task
families or evidence of component qualification.

| New validation category | Parent | Candidate |
| --- | ---: | ---: |
| Temperature | 0/8 | 8/8 |
| Variant | 0/8 | 7/8 |
| Independent measurements | 0/8 | 7/8 |
| Citation | 0/8 | 8/8 |
| **Total** | **0/32** | **30/32** |

The selection rule was at least 95% in **each** category and no lost baseline
pass. With eight cases per category, all eight must pass. The candidate has no
new-category baseline regression, but fails the per-category threshold. No new
final-test inference occurred; the original eight tests also remain unopened.
The lower validation loss does not override this result.

Both failures are contradictions rather than wording differences. In one case,
the model quotes supplied maps for the matching prototype variant, then says
those maps are missing. In the other, it quotes five independent withheld
measurement points, then says no withheld points are supplied. Scores and the
rubric were not changed after inspecting these answers.

## Retention and transfer diagnostics

Eight previously used OpenUSD and eight PicoGK development cases were selected
deterministically. All 16 reference answers passed their native checkers. Parent
and candidate each passed 8/8 OpenUSD and 8/8 PicoGK: parsed scene checks and
bounded, compiled/native-executed geometry checks. The existing USD
shader-property checker exclusion remains. This is a coding smoke test;
Python, CFD, FEA and general engineering competence were not evaluated.

The original ten validation cases were then compared separately with their
original exact metric and fixed generation settings. Parent scored **6/10**;
candidate scored **5/10**. The lost pass retains the main creep finding but
replaces its specific heat/ductility limitation with a generic statement. More
seriously, the earlier material reasoning case still falsely combines
room-temperature fatigue tests with 600-degree component duty. Original Turbo
cam data and valvetrain masses also remain absent from the variant refusal.
This previously seen development diagnostic is not a new held-out benchmark.

One matched, previously used retrieval question supplied five training-side
NIMS records. The parent invents an absent PDF page ID and fails attribution
syntax. The candidate passes the schema with **zero claims**, incorrectly
saying that the test conditions are unsupported although a retrieved summary
contains them. Its structural pass therefore does not establish a useful
answer or a RAG improvement. No citation was repaired automatically and no
semantic benchmark score was assigned.

## What to improve next

Prioritise useful evidence handling over further reduction of token loss. Add
balanced present/missing-evidence cases with varied question wording and source
layouts, including correctly answering available conditions while refusing
unsupported component qualification. The present mix makes matching conditions
only one quarter of the temperature, variant and independence fixtures; balance
is a testable next change, not an established explanation for these failures.

Then curate actual licensed, read passages and numerical observations with
explicit alloy/process/orientation, test temperature, stress convention,
cycles/runout and component identity. Keep research findings, source limitations
and proposed project applications distinct. Extend the earlier summary and
multi-record reasoning tasks to measure transfer, while retaining native coding
checks. The training corpus still needs source-specific rights and reading
review before excluded material can enter it.

Before another run, register a factual rubric covering both unsupported claims
and false abstention, create fresh article/task-family evaluation data and keep
final cases untouched. Use the failures above as development evidence, preserve
the old metrics, and compare the same baseline and candidate prompts. A larger
model or a longer run should follow a measured need; neither closes the missing
M64 interfaces, original K16 maps, cam/valvetrain or fan measurement gates.

The continuation self-checks and local document links pass without adding
dependencies. Full local repository checks still have the separately recorded
environment failures from pilot 001. Its publication commit passed GitHub's
`make check` workflow; the continuation's current PR head must be checked
separately. No merge, deployment, default replacement or manufacturing release
is claimed.
