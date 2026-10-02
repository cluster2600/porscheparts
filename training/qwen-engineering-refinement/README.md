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
