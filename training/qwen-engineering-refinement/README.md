# Qwen engineering refinement

Owner-requested continuation toward high measured accuracy, 2 October 2026.
This builds on the [first four-domain pilot](../qwen-engineering-20261002/README.md)
without changing its frozen files or the selected default adapter.

The [runner](refine.py) uses private copies of the original four native graders.
It adds 512 paired PicoGK graphs with shuffled node identifiers/order, 288
three-object USD training scenes, 96 paired final variant selections, all
remaining old USD training rows, and 96 SI mechanical-calculation examples.
These are authored synthetic data. No thesis text or third-party dataset rows
are training targets. Twelve mechanical formulas add 24 validation and 24
fresh tests with independently generated parameters. Known formulas and shared
API recipes limit generalisation; no industrial qualification is claimed.

Continue pilot 001 for 600 iterations, batch 2, learning rate 0.00002, 16 LoRA
layers, rank 8, scale 20, masked prompts and 1,024-token limit. Sources/data
are frozen before scoring. Checkpoints 200/400/600 first face the eight original
graph tasks and the two USD regressions. Only a complete screen opens the full
126-case validation. Keep every passing selected-adapter case and require at
least 95% in each combined domain. Python uses complete variable coverage and
independent parameter perturbations, including dimensionless ratios. Fresh
model tests open only after eligibility. Default replacement is never automatic.

```sh
/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993/work/m64-qwen/venv/bin/python \
  training/qwen-engineering-refinement/refine.py --output "$PWD/work/qwen-engineering-002"
python3 -m unittest discover -s tests -p 'test_qwen_engineering_refinement.py' -v
```

The user's workflow photographs extend the research scope to CalculiX INP,
conjugate heat transfer, manufacturing supports and depowdering. These topics
need separate complete-case native benchmarks before capability claims.
OpenUSD stores scene/asset metadata; solver meshes, boundary conditions,
materials and loads require explicit transformations and checks. Simulation
feedback returns to design. Printing additionally requires independently
approved manufacturing and inspection evidence.

The completed [002 results](results-002.json) reject all three checkpoints.
Step 600 reaches Python 24/32, OpenFOAM 8/8, OpenUSD 38/38 and PicoGK 46/48
with no selected-adapter validation regressions. Python misses the registered
95% floor, so the 56 fresh tests remain unopened and the default is unchanged.

The [verified photo curriculum](photo_course.py) adds 1,416 training examples:
864 mechanical calculations, 48 USD mesh buffers, 480 engineering decisions
and 24 complete CalculiX axial-bar decks. It merges the prior 1,808 training
rows, giving 3,224 train and 266 validation cases. The 140 new fresh photo cases
remain sealed until selection; the prior 56 fresh cases stay unused.

The [photo runner](photo_run.py) continues checkpoint 002/600 for 1,200 iterations,
batch 2, learning rate 0.00002, 16 layers, inherited rank 8/scale 20, seed 42,
masked prompts and maximum 1,024 tokens. It freezes source/data/runtime hashes,
checks every authored new training reference and evaluates checkpoints
400/800/1200 against all six domains. Selection requires at least 95% in every
domain and preserves the union of passing parent and retained-adapter cases.
This union is a retention obligation, not a single-model baseline score.
Passing validation opens only the new 140-case test; default replacement is
never automatic. Source recipes are shared across sampled splits, so these
scores cannot establish general CAD mastery.

```sh
/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993/work/m64-qwen/venv/bin/python \
  training/qwen-engineering-refinement/photo_run.py --output "$PWD/work/qwen-engineering-003"
python3 -m unittest discover -s tests -p 'test_qwen*py' -v
```

Corrected photo lessons use [primary-source records](research.json). PicoGK
constructors and boolean copies replace conceptual placeholder APIs. Converted
mesh buffers replace generic OBJ layer references. PET drawings and shaders
do not establish measured mounting interfaces or alloy qualification. Fin,
intake and shroud claims require controlled thermal/flow comparisons; neither
surface area nor titanium alone proves improvement. Printing requires process,
support-removal, powder-exit, heat-treatment, machining and inspection evidence.
Rigid-body scenes do not establish flexible crankshaft modes or fatigue.

The [fin paper](https://doi.org/10.19206/CE-195440) reports a single-cylinder
6063-T6 study, not Porsche material data. Its claimed 250 cm³ conflicts with
50 mm bore and 70 mm stroke, which imply about 137.445 cm³. The curriculum
teaches requesting clarification and checking supplied dimensions. It also
separates a temperature difference from a measured heat rate. No article text,
manual or third-party benchmark rows are training targets.

CalculiX 2.23 is already installed on Kali2. Generated decks pass an independent
restricted comparison before native execution, with no includes and a fixed
solver executable hash. The analytical witness checks displacement FL/(EA),
consistent N-mm-MPa units and complete constraints. This is an axial T3D2
benchmark, not complex contact, fatigue, crankshaft FEA or part qualification.
OpenFOAM scoring still covers bounded dictionary tasks; complete CHT cases,
coupled energy balances and measured engine calibration remain to be added.
