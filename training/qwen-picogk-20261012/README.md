# PicoGK library-aware model optimisation

This experiment specialises the existing local coding adapter in a small,
strict interface: a request becomes a recipe and millimetre parameters; an
owner-authored C# host calls pinned geometry libraries. Model responses never
become executable C#, MSBuild, package names or file paths. Original adapters,
research experiments and frozen evaluations are preserved.

The scope is useful software geometry and evidence handling. Synthetic training
dimensions are not measured Porsche interfaces, material allowables or a
manufacturing release. Library compilation and geometry screens have separate
meaning from model accuracy and raw export topology.

## Library coverage

| Library/interface | What this experiment covers |
| --- | --- |
| PicoGK 2.3.0 / native `picogk.26.2` | Library lifetime, lattices, voxels, volume/bounds, inside/outside samples and explicit-mm STL export/import |
| LEAP71 ShapeKernel | LocalFrame, BaseCylinder and BasePipe |
| LEAP71 LatticeLibrary | One zero-noise RegularUnitCell, BodyCentreLattice and ConstantBeamThickness; the thickness API receives a diameter |
| PicoGK-Fasteners | Washer with explicit outer/bore dimensions; actual namespace `PicoGK_Fasteners` |
| LEAP71 HelixHeatX | ThreadCutter geometry; full exchanger or thermal performance is outside this experiment |
| PicoGK SimulationExample | Four source files with CC0 notices inventoried; no solver or model training on this example |
| .NET / C# | Existing .NET 9.0.317, System.Numerics, System.Text.Json, strict numeric/schema guards and headless execution |
| OpenUSD | Eight previously used development cases in a joint native coding-retention check |
| OpenVDB / FreeCAD STEP / CFD / FEA | API inventory or existing project routes only; new VDB, STEP and solver executions remain untested |

The source revisions and observed licences are in [library-profile.json](library-profile.json).
PicoGK, ShapeKernel, LatticeLibrary, HelixHeatX and Fasteners have Apache-2.0
notices. Complete third-party source checkouts and their notices remain in the
private working collection. Owner-authored code and fixtures follow the
repository licence; this report grants no additional rights to model weights
or unrelated material.

The managed host compiles 88 source files, including its own entry point.
Reflection inventories 263 public types and 1,247 declared methods. That is
documentation coverage, not evidence that the model has mastered every method.
Upstream obsolete-method warnings are retained rather than patched in place.
The [reflected API catalogue](api-catalog.json) records the actual namespaces,
constructor overloads and method signatures of the compiled profile. For example:

```sh
jq '.[] | select(.name == "PicoGK.Voxels")' training/qwen-picogk-20261012/api-catalog.json
```

## Training and evaluation

The new curriculum has six categories: cylinder, pipe, washer, BCC cell,
thread cutter and refusal of unavailable measured interfaces. Complete geometry
requests are fictional. Prompts alternate French and English and include mm/cm
conversions and diameter/radius distinctions. Washer fit defaults are explicitly
overridden. Unknown original 993 attachment coordinates stay unknown.

There are 240 new training cases, 48 validation cases and 24 final cases.
Another 192 admitted old training cases replay PicoGK and OpenUSD coding tasks,
giving **432 training rows**. Only train/validation JSONL enters MLX. Sixteen
previously used development coding cases form a separate retention check.
Instance prompts and positive recipe/parameter tuples are disjoint; task
recipes are shared, so this is not an independent task-family benchmark.

The first preparation incorrectly counted tokenizer mapping keys. It is
preserved without a model run. The corrected preparation reuses the existing
`sequence_length` helper and checks an actual maximum of **547 tokens**, below
the 1,024-token training limit. Neither tokenizer nor model weights changed to
correct that audit.

The cached base is `Qwen2.5-Coder-1.5B-Instruct-4bit`, revision
`b3252a2f97102b1fb1571fec2c9b27219a8536be`. The parent is the retained coding-008
step-400 adapter, SHA-256
`09024cfb346f3dd7f8994e5fe1cd89e11976db5354b8dac9c0167d57ee7aacb6`.
The registered continuation uses MLX-LM 0.31.3, 480 additional steps, learning
rate 0.000005, batch two, 16 LoRA layers and seed 9931212. Prompt masking and the
parent's rank-eight/scale-20 configuration are preserved. Only final step 480
is assessed; the candidate never becomes a default automatically.

Before model inference, data, source, host, runtime, parent and model inputs
are SHA-256-bound. Forty positive validation references execute natively and
all old coding reference answers pass their native checkers. After training,
every adapter tensor must be finite and input hashes must still match.

New responses require raw JSON with exactly `recipe`, `parameters_mm` and
`missing`. There is no fence stripping, repair or retry. Duplicate keys, bools
as numbers, nonfinite values, unsafe bounds, invalid bores, absent required
uncertainty and unknown recipes fail. An accepted numeric plan runs in the
fixed host; matching requested units/intent, native completion, positive volume,
material/void samples, STL roundtrip and analytic volume checks where applicable
are separate obligations. These are bounded screens, not exhaustive topology
or continuous tolerance proofs.

Every validation category must reach at least 95%, with no lost baseline pass;
with eight cases this requires 8/8. Old retention must also meet its registered
gate before the new final cases may open. Previously exposed tests from older
experiments are not reused as new final evidence.

The first candidate reaches 48/48 new validation and 15/16 old retention,
with no baseline regression. Its remaining raw C# graph error duplicates one
connection and omits another despite successful compilation and native volume.
The fresh final cases therefore stay closed at this first outcome.

A separately registered second trial adds 256 original training graphs with
shared/nearby coordinate components and unequal endpoint diameters. It uses
688 training rows, starts from the finite first candidate and trains for exactly
240 further steps at 0.0000025. The baseline remains the original coding-008
adapter, regenerated under identical settings. Source exclusions and actual
token lengths are checked before predictions. The validation and retention
cases are now exposed development diagnostics; the final set stays untouched
unless the unchanged per-category/no-regression gates pass.

The continuation reuses the frozen runner and records its data, warm-start and
command substitutions before baseline inference. Neither the first dataset
nor the first run is overwritten.

```sh
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-picogk-20261012/continue.py prepare \
  --previous /absolute/path/to/completed-first-work --work /absolute/path/to/new-work
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-picogk-20261012/continue.py run --work /absolute/path/to/new-work
```

## Run the local experiment

Use a new private work directory containing the pinned source checkouts and
their `retrieved.json` metadata. Existing runtime paths are specific to this
Mac. Changing those paths, model bytes or source revisions requires a new
registration, not modification of an existing frozen run.

```sh
python3 training/qwen-picogk-20261012/pilot.py self-check
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-picogk-20261012/pilot.py prepare --work /absolute/path/to/new-work
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-picogk-20261012/pilot.py run --work /absolute/path/to/new-work
```

Preparation refuses an existing dataset and execution refuses an existing run.
The host-wide MLX lock serialises this experiment with the existing coding
trainer. Model access is offline; no dependency, GPU rental or model download
is added. The evaluation process applies an 8-GiB MLX allocation policy; that
policy is not inherited by the separate CLI trainer and is not a hard physical
memory or CPU cap. Actual training allocation is reported by MLX separately.

The private work retains the source notices, reflected API catalogue, reference
meshes, exact model answers, scores, training log, adapter and protocol. Public
metadata and [the outcome report](RESULTS.md) record what actually passed and
what remains untested. No raw scan, proprietary manual or vehicle identifier
is part of this course.

## Use the eligible plan adapter locally

The [inference command](ask.py) verifies the registered gates and adapter hash,
uses the same fixed recipe cards and saves an unrepaired response receipt. It
proposes parameters; it does not execute model code or grant engineering
approval. Each new request still needs intent review.

```sh
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-picogk-20261012/ask.py \
  --work /absolute/path/to/completed-continuation \
  --prompt 'Create a synthetic ShapeKernel pipe: length 1.4 cm, outer diameter 1.8 cm, bore diameter 1.0 cm.' \
  --output /absolute/path/to/new-answer.json
```

The separate smoke request returns `pipe` with `[14,9,5]` millimetres and no
missing inputs: length, outer radius and bore radius. It is a usage check, not
another independent benchmark. Inference refuses an existing receipt and an
adapter whose bounded gates or bytes differ. No serving default is replaced.
