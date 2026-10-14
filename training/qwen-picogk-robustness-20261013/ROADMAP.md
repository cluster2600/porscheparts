# PicoGK model roadmap: from 19/60 to a qualified 50/60 milestone

Assessment date: **14 October 2026**. This is a proposed next protocol and
implementation plan; it does not register an experiment or change inference.

[PR 255](https://github.com/cluster2600/porscheparts/pull/255) is merged into
`main` as `4f93d375bb140dabeec9f0b9a7b82086dafebbe3`; its
[post-merge Linux check](https://github.com/cluster2600/porscheparts/actions/runs/38520063163)
passes. The requested **50/60 development milestone is already exceeded** by
the paired corrective candidate, which reaches **57/60** and retains all
**64/64 previous native tasks**. The serving command still uses the retained
r3 adapter, which scores **19/60** on this development set. The corrective
candidate did not satisfy its original promotion protocol.

The next objective is to verify this improvement on independent requests,
preserve the previous capabilities, and provide a compatible inference profile.
The [experiment report](README.md) and [hashed result record](results.json)
remain the authority for the completed runs. No historical threshold, result,
frozen executable or serving default is modified by this plan.

## What has actually improved

| Adapter | New development plans | Previous native plans | Previous native code | Current decision |
|---|---:|---:|---:|---|
| Retained r3, currently served | 19/60 | 48/48 | 16/16 | Keep as rollback baseline |
| First 480-step continuation | 58/60 | 43/48; 47/48 semantic | 8/16 | Rejected: regression and native timeouts |
| Paired 240-step correction | 57/60 | 48/48 | 16/16 | Best candidate for a fresh comparison; not promoted |

The first candidate's slightly higher aggregate score does not compensate for
its lost old thread case and failed native checks. The paired candidate gains
38 development passes over the retained baseline without losing a baseline
pass. It passes all ten refusal requests for missing or unverified interfaces.

| Language | Serving r3 | Paired candidate |
|---|---:|---:|
| English | 6/12 | 12/12 |
| French | 2/12 | 12/12 |
| German | 3/12 | 11/12 |
| Japanese | 3/12 | 11/12 |
| Chinese | 5/12 | 11/12 |

Reaching 50/60 from the serving baseline requires at least 31 additional
passes. The existing candidate already supplies 38 on these development
requests. This makes a new evaluation more useful than an immediate change
of model size or another unrestricted training run.

The audit of the baseline's `valid-before-scores.json` finds:

- 20 failures against independently expected parameters;
- 18 numeric or geometric constraint failures: eight bore-order, four thread,
  four lattice and two general numeric-bound errors;
- three JSON syntax failures;
- zero incomplete responses and zero native execution timeouts.

That receipt's SHA-256 is
`f9820b11b855746d6ec23187c207b95026deda165146c8f872d4ce07dfec2950`,
already recorded in [results.json](results.json). All three remaining paired
candidate failures are parameter mismatches, blocked before geometry execution.
They involve explicit radii in a German washer, Japanese pipe and Chinese
thread. Some values are halved and others drift numerically. Increasing the
token limit would not address these measured failures.

## Why 57/60 did not promote the candidate

The completed course requires at least 95% in **every** recipe/language/status
category. Its 35 categories have only one or two examples each, so that rule
requires **60/60**, together with complete retention. An overall 57/60 does not
pass those gates. The original sixty reserved final requests remain uninferred.

There are two valid next paths:

1. Continue under the original criteria until every development category passes,
   then open the original reserved final set once as originally specified.
2. Register a **separate prospective 50/60 milestone**, using new development
   and reserved final sets, while preserving the original rejected outcomes.

This plan recommends the second path for the owner's new milestone, with the
first remaining the stricter numerical-correctness goal. A new protocol must
exist before inference; this document alone is not that registration. A 50/60
score would describe this bounded course, not 95% general reliability or
unrestricted engineering competence.

## Hugging Face: related work and what we can reuse

Public repository-identifier searches checked at **2026-10-14 06:12:51 UTC**
return zero entries in each of the nine queries below. These searches do not
cover private repositories, every README mention or work hosted elsewhere;
they do not establish that no PicoGK training work exists.

| Search term | Models | Datasets | Spaces |
|---|---|---|---|
| PicoGK | [0 results](https://huggingface.co/api/models?search=PicoGK&limit=20) | [0 results](https://huggingface.co/api/datasets?search=PicoGK&limit=20) | [0 results](https://huggingface.co/api/spaces?search=PicoGK&limit=20) |
| ShapeKernel | [0 results](https://huggingface.co/api/models?search=ShapeKernel&limit=20) | [0 results](https://huggingface.co/api/datasets?search=ShapeKernel&limit=20) | [0 results](https://huggingface.co/api/spaces?search=ShapeKernel&limit=20) |
| LEAP71 | [0 results](https://huggingface.co/api/models?search=LEAP71&limit=20) | [0 results](https://huggingface.co/api/datasets?search=LEAP71&limit=20) | [0 results](https://huggingface.co/api/spaces?search=LEAP71&limit=20) |

The closest public work targets **CadQuery Python/B-rep geometry**, whereas
our course selects trusted **PicoGK C#/voxel recipes through bounded JSON**.
The following figures are publisher reports, not local reproductions or scores
comparable to our 60 requests. Only cards and metadata were retrieved; no
external weights or training archives were downloaded. Code examples were
read as source text and never executed.

| Work | Evidence from its card | Use for this project | Boundary |
|---|---|---|---|
| [Qwen2.5-Coder-7B CadQuery MLX](https://huggingface.co/yuvit-batra/qwen2.5-coder-7b-cadquery-mlx-4bit) | Apple M4 Max, MLX LoRA, 12,477 validated pairs. Reports 80% executable/valid solids but 45% bounding-box accuracy on its small test evaluation. | Closest Mac training precedent; borrow geometric validation and explicit unit contracts. | CC-BY-NC-SA-4.0; mixed normalized-coordinate lineage; single-part CadQuery. No direct PicoGK adapter compatibility. |
| [Zero-To-CAD-100k](https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k) | Autodesk synthetic construction programs, operation metadata, eight rendered views and STEP/STL. Declared splits total 100,516 records: 81,015 train, 9,734 validation, 9,767 test. | Best dataset lead for a later reviewed geometry curriculum or reconstruction experiment. | Apache-2.0 declared. Not ready-made five-language request/PicoGK-plan pairs; unit semantics and asset provenance still need inspection. |
| [CAD-Coder](https://huggingface.co/gudo7208/CAD-Coder) | Qwen2.5-7B, supervised training then GRPO with geometric Chamfer-distance and format rewards; 110K triplets and 1.5K reasoning samples reported. | Use independent requested-geometry checks when designing future training rewards. | Model metadata declares Apache-2.0; Text2CAD-derived training lineage needs separate rights review. Published multi-GPU training is unnecessary for the immediate milestone. |
| [cad-qw35-2b-0.1](https://huggingface.co/raspbfox/cad-qw35-2b-0.1) | Small Qwen3.5-2B LoRA course, roughly 1,000 teacher-generated examples; author reports 98% valid generation on 100 prompts. | Evidence for trying a compact validated curriculum before enlarging training. | Apache-2.0 declared. Protocol and dimensional accuracy are insufficiently detailed; incompatible base architecture. |
| [Zero-To-CAD Qwen3-VL-2B](https://huggingface.co/ADSKAILab/Zero-To-CAD-Qwen3-VL-2B) | Eight rendered views to CadQuery; reports 82.1% success on its synthetic test and 61.0% on out-of-distribution ABC geometry. | Later image-to-CAD comparison for reconstruction proposals. | Apache-2.0; different multimodal input and model. Render reconstruction cannot supply measured Porsche interfaces. |
| [CAD-Recode v1.5](https://huggingface.co/filapro/cad-recode-v1.5) | Qwen2-1.5B with a point-cloud projection layer generates CadQuery code; [matching dataset](https://huggingface.co/datasets/filapro/cad-recode-v1.5) exists. | Later scan-to-editable-CAD research. | Model and dataset declare CC-BY-NC-4.0. Custom point-cloud architecture; cannot replace the text-only adapter. |

There is also a [ThomasTheMaker CadQuery dataset](https://huggingface.co/datasets/ThomasTheMaker/cadquery).
Its API metadata has no declared license at the check date. Keep it as a lead,
without importing it into training until rights and provenance are established.
A permissive model-card tag alone does not settle every upstream dataset's
rights. Non-commercial models should remain outside the project's default
reusable training assets unless the intended use and permission allow them.

The checked repository revisions make later changes distinguishable:

| Repository | Checked revision |
|---|---|
| yuvit-batra/qwen2.5-coder-7b-cadquery-mlx-4bit | `223cb1d6b287acc5152849b773cc3e0b3d62a895` |
| ADSKAILab/Zero-To-CAD-100k | `48bcf0a8c6fbfb47a27f5662007c24dff8d754ae` |
| gudo7208/CAD-Coder | `958288771567413ff8688d49e43db7ccc21980d0` |
| raspbfox/cad-qw35-2b-0.1 | `40267f93597802acfa075dc772ed294cccc99707` |
| ADSKAILab/Zero-To-CAD-Qwen3-VL-2B | `8cf9260904aa6eb29f0826e3585f25b7df61ff89` |
| filapro/cad-recode-v1.5, model | `765e8cc315a1a77bd8c69ccd0b403bad20ce35e8` |
| filapro/cad-recode-v1.5, dataset | `4696421935de9e9a71f1e092d8eee8b341d04619` |
| ThomasTheMaker/cadquery | `046629ca699e87927bedc178714a0289e94dbb2d` |

## Ordered implementation plan

### 1. Freeze a fresh comparison before any new training

Create a new private experiment directory and a pre-inference protocol. Pin
the base model, both adapter hashes, tokenizer/template, MLX packages, source,
native runtime, decoding and scorer. The proposed candidates are:

- serving r3:
  `2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f`;
- completed paired correction:
  `f51ea1acbfee302303cd617d87f515f747d569830f148a7dcee7a56092960260`.

Author 60 new development and 60 separately reserved final requests. Keep
12 per language, the six existing recipes and ten refusal cases per partition.
Use independently reviewed expected plans and trusted native reference runs.
Vary phrasing and field order beyond the old grammar; include explicit radii
and diameters, mixed units, French/German decimal commas, bore ordering and
plausible but unverified supplier dimensions.

Check disjoint numeric intents and prompt families against previous training
and evaluation partitions. Do not copy the three failed requests into training
or inspect the original reserved final requests. Historical development cases
can remain a labelled regression suite, never an independent final benchmark.
The new partition still covers these six recipes rather than new API families.

Compare the two fixed adapters with identical raw prompts, runtime, greedy
decoding and EOS requirements. The paired candidate should be evaluated first
as an existing complete checkpoint; no checkpoint sweep is needed.

**Deliverable:** frozen protocol, partition/provenance audit and matched raw
development results, including native retention and per-language counts.

### 2. Put numeric correctness in a request-derived contract

Start with the existing JSON schema and trusted recipe host. Review supplied
values into named fields with explicit quantity roles and units. Convert
unambiguous `cm`/`m` values to `mm` deterministically; divide by two only when
the supplied quantity is explicitly a diameter and the recipe requires a
radius. For example, a supplied outer **radius** of `0.85 cm` means `8.5 mm`,
while an outer **diameter** of `0.85 cm` means a radius of `4.25 mm`.

The contract must come from the request or verified input record independently
of the model's answer. The model proposes a recipe and fields; mismatched,
missing, ambiguous or out-of-bounds values block execution. Unknown OEM
attachments still require measurement. Never repair a response using a hidden
expected test answer, guessed dimensions or another unverified model response.

Keep the first implementation limited to structured inputs and reviewed,
unambiguous phrasing. A general multilingual parser is unnecessary for this
milestone. When natural-language extraction is ambiguous, request explicit
structured fields instead of silently choosing a meaning.

Compare four conditions: r3 raw, paired candidate raw, r3 with canonical
request inputs and paired candidate with canonical request inputs. Report
**raw-model accuracy** and **assisted-pipeline accuracy** separately. Compare
adapters on the same canonical inputs; preprocessing gains do not count as raw
model improvement. If r3 plus this small boundary meets the operational goal,
it may be preferable to another training run.

**Deliverable:** a small request-contract boundary with focused checks for
unit/role conversion, locale commas, rejection and invariance under field order;
a separate assisted comparison. Historical graders remain unchanged.

### 3. Train once more only if the fresh comparison warrants it

If the paired candidate misses the prospective raw milestone or loses retention,
build new contrast pairs for the measured failure families. Pair radius and
diameter descriptions of the same geometry, retain explicit named fields,
and vary language, units, locale notation and distractor order. Add reviewed
valid/invalid JSON contrast examples if fresh syntax errors recur. Split by
geometric intent and phrasing family before weighting or augmentation.

Use owner-authored examples first. Keep verified old replay, including OpenUSD
and graph tasks, and audit duplicate weighting separately from unique examples.
All old/fresh evaluation requests and numeric intents stay out of training.
External CAD examples need a reviewed license, source revision, unit mapping
and independently checked reference geometry before inclusion.

One bounded continuation is a reasonable initial budget: the existing 1.5B
MLX base, a fixed final checkpoint, up to 240 steps at the previously used
0.0000025 learning rate. Register that choice before starting; it is a proposed
budget, not a proven optimal setting. Low loss and more epochs alone have not
eliminated the radius errors. Reject the run if semantic or native retention
regresses; retain its failed receipts. No paid/cloud compute is needed now.

**Deliverable:** one frozen local trial and a candid development/retention
comparison, or an explicit decision to skip training because the fixed
candidate already meets the new milestone.

### 4. Qualify once on a fresh reserved final set

Proposed gates for the new 50/60 milestone, to register before inference:

| Gate | Proposed requirement |
|---|---|
| Raw plans, fresh development and then fresh final | At least 50/60 in each; full intent and native checks, not JSON syntax alone |
| Language coverage | At least 8/12 in each language in each partition |
| Missing/unverified interfaces | 10/10 refusals in each partition; no geometry execution |
| Previous capabilities | 48/48 old native plans and 16/16 old native code tasks |
| Regression control | Preserve every retained-baseline pass on the matched comparison and the labelled historical development suite |
| Response/integrity boundaries | EOS, strict schema/bounds, finite tensors, unchanged frozen inputs and protocol |
| Numeric execution | No execution when the independent request contract fails |

The ten refusal cases are included in each sixty-case score. Language floors
prevent the aggregate from hiding a weak language; they are engineering choices
for this new proposal, not a statistical reliability estimate. Numerical
correctness should continue toward 60/60 even after passing the milestone.

Choose one candidate using development only, then open the new final set once
with matched baseline inference. A failed final ends that trial. Any subsequent
selection needs another independently reserved final set. Keep the original
experiment's reserved sixty closed unless its original gates are satisfied.

**Deliverable:** a result record with raw/assisted scores, failures, native
receipts, hashes and a promotion decision. No new final score exists yet.

### 5. Add the qualified profile, then expand library coverage

The [current inference loader](../qwen-picogk-20261012/ask.py) pins the retained
adapter and requires the legacy `validation`/`retention`/`test` eligibility
schema. The corrective experiment's result schema differs. Copying its weights
over the retained adapter would both break integrity and bypass qualification.

After the new gates pass, add a separate compatible inference profile using
the selected adapter/base hashes and verified new result schema. Preserve
manifest verification, package checks, path containment, EOS and exclusive
runtime locking. Test refusal, tampered-input rejection and rollback to r3.
Start with an explicit profile selection; changing the default follows a
verified qualification record. Do not rewrite the legacy profile or results.

Then introduce separate source-pinned curricula for scalar/vector VDB,
QuasiCrystals, ShapeKernel and the installed Geometry APIs. Each needs its own
native reference examples, independent semantic witnesses, disjoint evaluation
and retention checks. Keep broad C# graph generation separate from this bounded
plan course. Use the installed standalone suite only through a new frozen
experiment copy; leave historical SDK/source inputs untouched.

**Deliverable:** a verified inference profile with rollback, followed by distinct
library-specific training/evaluation records. None is implemented by this page.

## Verification and engineering boundaries

The 14 October assessment rechecks all ten paired-run receipt hashes, the
paired adapter hash and the serving r3 adapter hash against the recorded values.
The completed paired run already verifies all 4,898 input bindings; this
assessment does not claim a fresh rehash of every binding or new model inference.
PR 255's merged commit and post-merge CI are confirmed independently of its
experimental model qualification.

The shortest next action is **a fresh registered comparison of the existing
paired candidate and r3**, followed by the request-contract boundary if needed.
Hugging Face resources inform the curriculum and later reconstruction work;
replacing the base model or importing a large dataset is not required to prove
the requested 50/60 milestone.

All current scores concern synthetic software geometry. Strict raw-mesh/VDB
qualification, exact Porsche interfaces, fitment, fatigue, CFD/CHT, calibrated
metal printing and professional engineering release remain separate evidence
gates. A generated or reconstructed part cannot provide its own inspection
evidence or manufacturing authorization.
