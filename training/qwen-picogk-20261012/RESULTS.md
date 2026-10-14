# PicoGK optimisation outcome — 12 October 2026

The second local adapter passes the registered bounded plan, native software
geometry and coding-retention gates. New plan validation improves **0/48 to
48/48**, and the final plan comparison improves **0/24 to 24/24**. Old coding
retention improves **14/16 to 16/16**, preserving all previous passing cases.
The candidate is eligible for this experimental recipe interface. Serving
defaults and physical engineering qualification remain unchanged.

Raw STL quality is a separate result: **16/20 final geometry exports pass the
raw mesh screen**. All four final thread-cutter meshes fail that screen. Their
correct parameters, positive volume and native execution do not make those
meshes usable for manufacturing. Four final requests concern missing measured
interfaces and correctly produce no geometry.

See [the reproducible interface and source profile](README.md),
[result metadata and hashes](results.json) and
[the compiled API catalogue](api-catalog.json).

## What changed

The model now translates bounded French/English requests into strict JSON
recipes and millimetre parameters. A fixed C# host executes owner-authored
calls to PicoGK, ShapeKernel, LatticeLibrary, Fasteners and HelixHeatX.
The learned distinctions include mm/cm conversion, radius versus diameter,
the diameter expected by ConstantBeamThickness, explicit washer bore/outer
dimensions, and unavailable original 993 interfaces. Responses are neither
repaired nor turned into executable model-authored C#.

The host compiles 88 source files against the existing PicoGK 2.3.0/native
26.2 runtime. Reflection records 263 public types and 1,247 declared methods.
The new model course exercises five native geometry recipes and one
missing-interface category. The catalogue supports API lookup; it does not
demonstrate mastery of every inventoried symbol.

## Two preserved training trials

| Trial | Data / additional steps | New validation | Old retention | Final evaluation |
| --- | --- | ---: | ---: | --- |
| Original coding-008 control | Same prompts/runtime, unchanged weights | 0/48 | USD 8/8, PicoGK 6/8 | 0/24 under the new interface |
| First candidate | 432 rows / 480 steps, learning rate 0.000005 | 48/48 | USD 8/8, PicoGK 7/8 | Closed at this outcome |
| Second candidate | 688 rows / 240 steps, learning rate 0.0000025 | 48/48 | USD 8/8, PicoGK 8/8 | 24/24 after passing both gates |

Both use the existing MLX four-bit Qwen2.5-Coder-1.5B-Instruct conversion,
16 LoRA layers, rank eight, scale 20, batch two, masked prompts and seed
9931212. The cached base and original coding-008 adapter remain unchanged.
Training trained 96,688 and 73,620 assistant tokens respectively, including
repeated examples. Peak reported MLX allocation was 5.000 GB in each run.
Final logged validation losses were 0.002 and 0.001; loss alone never selected
a candidate. Each final adapter has 224 finite arrays and 5,275,648 parameters.

The first candidate's one remaining graph error duplicated C→B instead of
including C→A. Compilation and a nonempty native mesh still passed, while the
independent requested-edge contract rejected it. A second protocol was fixed
before execution: add 256 original training graphs with shared/nearby coordinate
components and unequal endpoint diameters, continue from the finite first
candidate, and keep the same per-category/no-regression threshold. This is an
adaptive development correction; the comparison does not isolate the causal
contribution of data, extra updates or warm start.

The first preparation's tokenizer mapping-key count is preserved as an invalid
preparation audit, with no model run. The corrected package reuses the existing
token-ID length helper, measures 547 maximum sequence tokens and prohibits
truncation beyond 1,024. Only training/validation JSONL enters the trainer.
No final cases were trained on or used to choose a checkpoint.

## Final category results

| Category | Original control | Second candidate |
| --- | ---: | ---: |
| ShapeKernel cylinder | 0/4 | 4/4 |
| ShapeKernel pipe | 0/4 | 4/4 |
| Fasteners washer | 0/4 | 4/4 |
| LatticeLibrary BCC cell | 0/4 | 4/4 |
| HelixHeatX ThreadCutter | 0/4 | 4/4 |
| Unavailable measured interfaces | 0/4 | 4/4 |

A pass requires raw strict JSON, genuine generation completion, correct
recipe/ordered parameters and missing evidence, plus native volume, bounds
availability, inside/outside samples, explicit-mm STL roundtrip and analytic
volume screens where applicable. Every category meets the registered 95%
threshold; no original passing obligation is lost. These screens concern
software geometry and intent, with a separate raw export audit below.

Final scenarios have disjoint positive recipe/parameter tuples and prompts,
but share the trained task grammar. They establish bounded source-conditioned
recipe performance, not independent engineering-family generalisation.
The final cases are now exposed and may serve only as regression evidence for
future work. Scientific Qwen/research pilots keep separate models and scores.

## Raw geometry and remaining coverage

The ten independent reference probes at 0.5 and 1.0 mm pass eight raw mesh
screens; both thread-cutter probes fail. The first candidate's 40 validation
geometry exports pass 34 screens, with the six failures again in ThreadCutter.
The second candidate's twenty final geometry exports pass sixteen screens,
with all four ThreadCutter outputs failing. The existing exact-coordinate raw
STL auditor is reused without face deletion, rounding, welding tolerances,
smoothing or repair. These are finite topology screens, not exhaustive
self-intersection, tolerance or physical inspection proofs.

Full HelixHeatX thermal behaviour, the other Fasteners/lattice/implicit APIs,
new OpenVDB roundtrips, editable STEP, CFD, FEA and coupled simulation were not
evaluated. Source profiles distinguish compiled, inventoried and model-tested
coverage. No inferred geometry closes missing original engine interfaces,
maps, cam data or fan measurements.

## Using the new adapter

The eligible experimental adapter is private at
`/Users/maxime/Documents/PicoGK-Model-Optimization/2026-10-12-r3/run-001/adapter`.
Its SHA-256 is
`2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f`.
The first candidate remains separately preserved with SHA-256
`b4d74b0894ea53c8cc0251a86d43bedfda992bba4a5df1877212211a689c07ff`.

The local [ask command](ask.py) verifies the bounded gates and candidate hash,
then returns a strict plan receipt. A separate usage smoke request correctly
converts a 1.4 cm pipe length, 1.8 cm outer diameter and 1.0 cm bore diameter
to `[14,9,5]` mm. It executes no geometry. New requests require intent review;
schema acceptance alone cannot establish that the model understood a request.

The private packages retain full protocols, source notices, input hashes,
unaltered answers, native witnesses, raw meshes, audits and weights. Public
files contain owner-authored helpers, API metadata and summary commitments.
No raw scan, manual, personal vehicle identifier or model weights are published.

Targeted contract/inference checks pass. A full local `make check` ran 3,780
tests and failed with two pre-existing exact floating-result assertions and
26 errors involving existing SciPy loading and Python-3.10 hash API usage;
228 tests skipped. The existing CAD Python fixes the hash-API test but retains
the two floating-result failures. Dependencies and unrelated tests were not
changed. The registered main commit passed Linux GitHub CI; this new head's
full CI is checked separately before any merge decision.
