# ADR 0020: freeze data-only training corpora

## Status

Accepted by the project owner on 2026-11-06 for
[issue #424](https://github.com/cluster2600/porscheparts/issues/424):
“Freeze all pending a justified training need.”

## Decision

Preserve the following corpora without training, retirement or deletion. This
is a disposition decision, not an assessment that their data or models are
qualified. The two current `mezger-*` directories are listed explicitly.

| Corpus | Decision |
|---|---|
| `training/993-turbo-20261002` | freeze |
| `training/m64-dimensions-deep-20261024` | freeze |
| `training/m64-measurements-20261024` | freeze |
| `training/m64-precision-20261025` | freeze |
| `training/m64-world-measurements-20261025` | freeze |
| `training/mezger-german-sources-20261003` | freeze |
| `training/mezger-turbo-materials-20261003` | freeze |
| `training/qwen-source-extraction-preparation-20261004` | freeze |
| `training/m64-engineer` | freeze |

Coverage: all nine existing directories named individually or by the
`mezger-*` pattern in #424. No other training programme is reclassified.
The decision selects no corpus for training, so #424's conditional requirement
to register held-out splits for selected training runs is not activated.

## Reopening criteria

A future proposal must state the justified task, why existing retrieval or
models are insufficient, lawful data/model revisions, independently disjoint
evaluation data, acceptance metrics, runtime and bounded resources. Record a
new decision before training. A model result cannot approve engineering gates.

No corpus contents, frozen evidence, model weights or evaluation claims were
changed to implement this decision.
