# PicoGK parameter-plan robustness continuation

For the current 19/60-to-50/60 assessment, ordered next steps and related
Hugging Face work, see the [14 October roadmap](ROADMAP.md).

This experiment continues the retained r3 adapter after the runtime repair
in [PR 205](https://github.com/cluster2600/porscheparts/pull/205). That PR was
already merged into `main` as `39bb313f3a33d02c6ab58dd227616ed980a51c15` when
this work began; its post-merge Linux validation passed. The standalone Mac
installation and the retained adapter remain available.
[Post-merge CI receipt](https://github.com/cluster2600/porscheparts/actions/runs/38400825625).

The objective is precise interpretation of explicit synthetic geometry
requests: distinguish radius from diameter, convert mixed millimetres,
centimetres and metres, preserve named parameters despite reordered fields,
and decline unavailable or unverified original Porsche mounting interfaces.
English, French, German, Japanese and Chinese field labels are included.
This extends the existing bounded JSON-plan course. General C# generation
and coverage of all PicoGK APIs remain outside this experiment.

## Why another experiment was needed

The retained adapter passes all 48 previous validation plans and all 16
retention code cases, but scores only **19/60** on this new development set:

| Language | Retained r3 | First continuation | Paired correction |
|---|---:|---:|---:|
| English | 6/12 | 12/12 | 12/12 |
| French | 2/12 | 12/12 | 12/12 |
| German | 3/12 | 11/12 | 11/12 |
| Japanese | 3/12 | 12/12 | 11/12 |
| Chinese | 5/12 | 11/12 | 11/12 |

For example, an explicit synthetic cylinder with length 7.5 mm and radius
0.625 cm requires `[7.5,6.25]` mm. The baseline returns `[7.5,3.125]`, halving
a supplied radius. A model can produce a valid JSON object and nonempty
geometry while missing this requested dimension. The independent expected
plan therefore precedes and controls native execution.

## Data and separation

The [course generator](run.py) creates 840 owner-authored synthetic records:
720 training, 60 validation and 60 reserved test records. The six existing
recipes are cylinder, pipe, washer, BCC cell, thread cutter and
`needs_measurement`. Positive dimensions remain within the original strict
bounds. Each explicit positive parameter tuple occurs in only one partition.
Field order, unit assignment and radius/diameter wording vary. French/German
decimal-comma forms occur in training; the development and reserved sets use
decimal points, so comma handling has no measured held-out score here.
BCC beam thickness remains a diameter.

The refusal cases cover both absent measurements and supplier estimates
that have not been independently verified. The example supplier values are
fictional, not sourced Porsche dimensions. Query references are opaque;
they do not contain the target recipe. Each language has separate refusal
categories for missing and unverified interfaces.

The new training records are combined with the exact **688-row** r3 training
file, including its graph and OpenUSD replay. Its original continuation hash
was checked, as were the prior validation and retention data hashes. No
previous validation/test prompt is intentionally added to training. The
maximum observed training/validation sequence is **547 tokens**, below the
unchanged 1,024-token limit; truncation is forbidden.

The development and reserved test sets each have 35 categories: 25
recipe/language combinations for positive geometry, plus ten
language/interface-status refusal categories. Categories have only one or
two examples. Passing a 95% floor here requires every example to pass; it
does not establish a population-level 95% reliability claim.

These are parameter-disjoint cases sharing recipe and grammar families.
The interface-refusal wording is also shared across partitions. This is
not an unseen task-family benchmark or broad natural-language coverage.

An initial preparation was rejected **before any model inference or training**:
its refusal reference identifiers contained the target recipe and its other
queries contained irrelevant BCC noise text. The rejected preparation and
source were retained privately. Only the corrected preparation is used in
the registered comparison.

## Fixed runtime and training protocol

- Base: the same pinned 4-bit Qwen2.5-Coder-1.5B-Instruct conversion at
  `b3252a2f97102b1fb1571fec2c9b27219a8536be`.
- Base weights: `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58`.
- Parent: retained r3 adapter
  `2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f`.
- Runtime: MLX 0.32.3, MLX-LM 0.31.3, Transformers 5.17.0 on Apple Silicon.
- Training: 480 fixed steps, batch size two, 16 adapter layers, learning
  rate 0.000005, prompt masking and seed 9931312.
- Selection: only the final step 480, with no intermediate-checkpoint search.
- Decoding: greedy, seed 9931312, 192 tokens for plans and 1,024 for retained
  code requests; complete responses must reach EOS.

There are **1,408 training rows** in total. The experiment copies the original
native SDK/runtime and geometry host into its private directory. This keeps
the comparison independent of updates to the installed workbench; it does
not downgrade the canonical Mac installation. The base, parent, source,
data and copied native inputs are hash-frozen before inference.

The protocol is written before the reference, baseline and training phases.
All sixteen authored code references and all sixty new authored validation
plans pass their software checks before the baseline comparison. The two
unavailable historical coding-008 parent files are not required: this
continuation resumes the completed retained r3 adapter, without claiming
reproduction of its entire earlier training history.

## Evaluation and acceptance

Plans must satisfy the unchanged literal JSON schema, finite positive
numeric bounds, EOS and the separately authored expected parameters.
Mismatched plans do not execute geometry. Matching positive plans execute
the trusted library recipes in the native host; missing/unverified
interfaces execute no geometry. Native checks include positive volume,
STL export/import, point witnesses and analytic-volume comparison for
the cylinder, pipe and washer.

These are the original **software geometry screens**, not the separate
strict raw-mesh/VDB gate from PR 195. Raw STL topology, voxel-resolution
accuracy, full API coverage, physical fitment and manufacturing remain
unqualified by this course. Synthetic thread cutters have no asserted
thread standard.

The candidate must pass every recipe/language/status development category
at the unchanged 95% floor, preserve every baseline pass, and pass all
48 old plans plus the sixteen retained code tasks. The latter include eight
OpenUSD and eight PicoGK graph requests, checked through the existing
native scorer and independent semantic signatures. The driver also
requires complete code responses to reach EOS.

Only a candidate meeting these gates may open the sixty fresh test requests
once, under matched decoding and runtime conditions. Those final cases are
not used to change the scorer or select another checkpoint. An unsuccessful
candidate stays experimental and does not replace the standalone command's
retained adapter.

## Reproduction and records

On the existing project Mac, using a new private output directory:

```sh
python3 training/qwen-picogk-robustness-20261013/run.py self-check
~/Developer/Qwen993/venv/bin/python \
  training/qwen-picogk-robustness-20261013/run.py prepare \
  --work /path/to/new/private/experiment
~/Developer/Qwen993/venv/bin/python \
  training/qwen-picogk-robustness-20261013/run.py run \
  --work /path/to/new/private/experiment
```

This is an experiment runner for the already recovered project runtime and
archived source data, not a fresh-machine installer. The preparation requires
three GiB free and the native reference environment. The active trial is
under `~/Documents/PicoGK-Model-Optimization/2026-10-13-robustness-r2`.
Inputs, raw responses, logs, meshes and weights stay private. Public records
contain reviewed scripts, method and non-sensitive aggregated results.

The [shareable result record](results.json) distinguishes measured model
progress, retention, eligibility and verification status. Neither lower
loss nor compilation alone qualifies a candidate. No serving-default
replacement, CFD solve, physical measurement or manufacturing approval
follows from this experiment.

## First candidate and corrective continuation

The first 480-step continuation raises development performance from **19/60
to 58/60**. The remaining errors concern a German thread core radius and
Chinese washer diameters. It also misinterprets one old English thread
diameter: semantic plan retention is **47/48**. The registered software score
is **43/48**, because four correctly interpreted BCC plans time out during
native execution. Code retention is **8/16**: all eight OpenUSD cases pass,
and all eight C# builds time out. These timeouts remain recorded failures.
Their cause has not been established.

Training reaches the fixed checkpoint, its adapter tensors are finite and its
reported final validation loss is 0.003. That loss does not override the
independent geometry and retention failures. The candidate is rejected for
promotion; the final sixty requests remain unevaluated.

The original runner also stalls while reading a copied SDK file during its
final frozen-input verification. It is interrupted after the score receipts
have been written, so its normal `run-001/results.json` is absent. Recovery
checks and their own receipts are separate; an interrupted run is not reported
as a successful driver completion.

The separate recovery subsequently verifies **all 4,888 registered input
files**, with two bounded individual rereads and no hash mismatch. The
original native failures and interrupted-run status are preserved. The
corrective run rechecks all 4,898 inherited and added bindings before model
loading; that check passes without fallback reads. Its matched baseline
reproduces 19/60 new plans, 48/48 old plans and 16/16 retained code cases.

The [corrective driver](correction.py) reuses the same course, grader, baseline
and acceptance gates. It adds 200 prompts for 100 new synthetic geometries:
each cylinder, pipe, washer and thread appears once with radii and once with
diameters, across the five languages. Their numeric intents exclude every
original course partition and old validation plan. The new paired prompts
are weighted twice, and the original 688 replay rows appear twice, giving
**2,496 rows**: 720 original new examples, 1,376 old replay rows and 400 paired
rows. Repeated rows are weighting, not additional unique examples.

The correction resumes the first candidate for **240 fixed steps at
0.0000025**, while its matched baseline stays the retained r3 adapter. It
keeps the same EOS, native deadlines, per-category floors and old-task
requirements. It may start only after the prior frozen inputs are verified.
Its integrity verifier uses four workers with separate bounded file reads;
each batch of up to 64 files has a 15-second deadline. A batch timeout permits
one individual read per file, also bounded at 15 seconds, with the same expected
hashes. Fallback reads are reported. Hash mismatches or an individual timeout
fail closed. Batching avoids thousands of Python launches. This
addresses verification hangs without changing model acceptance thresholds.

The corrective driver specifically uses this archived first trial and its
verified `completion-recovery.json` and `replay-provenance-audit.json` receipts.
Those recovery receipts are private prerequisites, not outputs automatically
produced by a fresh successful `run.py` run. This is a project experiment
driver rather than a general continuation or installation tool.

```sh
python3 training/qwen-picogk-robustness-20261013/correction.py self-check
~/Developer/Qwen993/venv/bin/python \
  training/qwen-picogk-robustness-20261013/correction.py prepare \
  --previous /path/to/first/private/experiment --work /path/to/new/correction
~/Developer/Qwen993/venv/bin/python \
  training/qwen-picogk-robustness-20261013/correction.py run \
  --work /path/to/new/correction
```

## Corrective result and next decision

The corrective run completes normally at its registered step 240. Its final
development score is **57/60**, compared with the retained baseline's 19/60;
the native checks preserve **48/48 old plans and 16/16 old code tasks**.
There are no lost passes relative to that retained baseline. It fixes the
first candidate's German thread, Chinese washer and old English thread
errors, but introduces three different development errors:

| Request | Independently expected parameters, mm | Candidate parameters, mm |
|---|---|---|
| German washer, explicit radii | `[3.25,8.5,3.25]` | `[3.25,4.25,1.5]` |
| Japanese pipe, explicit radii | `[17.75,9.5,3.25]` | `[17.75,4.75,1.5]` |
| Chinese thread, explicit radii | `[9.5,8.5,2.25,2.75]` | `[9.5,4.25,1.025,2.75]` |

The reported final validation loss is 0.004 and peak training memory is
4.999 GB. All adapter tensors are finite. The final adapter hash is
`f51ea1acbfee302303cd617d87f515f747d569830f148a7dcee7a56092960260`.
Every one of the 4,898 frozen input bindings passes the post-run check without
fallback reads; the protocol hash also remains unchanged. These are complete
software receipts for this second run, unlike the interrupted first driver.

Although 57/60 is 95% overall, three recipe/language categories fail their
registered floor. **Both candidates remain ineligible, all sixty final
requests remain uninferred, and the serving adapter stays unchanged.**
The first candidate's 58/60 should not be selected solely for its larger
aggregate score: it loses an old semantic pass and has failed native receipts.

Further training should first separate language interpretation from numerical
normalisation: reviewed inputs should supply authoritative millimetre values
and explicit radius/diameter roles, with deterministic conversions and an
independent semantic contract. The model can then learn recipe selection and
parameter extraction without being the sole source of numerical correctness.
Future experiments need genuinely different phrasing and larger category
samples. Additional epochs alone have not solved this measured failure mode.
The reserved final cases must remain out of training and checkpoint selection.

The next coverage expansion should introduce separate source-pinned cases
for QuasiCrystals and scalar/vector VDB operations after this parameter
interpretation is reliable. The installed early-development Geometry API
remains a separate software project; it has not been taught to this adapter.
