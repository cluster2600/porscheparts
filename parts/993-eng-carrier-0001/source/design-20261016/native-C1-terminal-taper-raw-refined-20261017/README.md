# Preserved raw-refined taper diagnostic: numerical evidence

This dependent capsule retains the original raw-refined terminal-taper mesh and two closed linear-static cases (rigid and K1000 total per eye/axis). The independent case closure is ROOT9e0dd. The original strict refinement-volume refusal and post-Build law refusal remain. h2_qualified=false, candidate_qualified=false, no stress convergence, strength allowable or physical qualification is asserted.

The three archives preserve201 added original paths. The495 existing original paths are supplied by the adjacent native-C1-terminal-taper-20261017 capsule, manifest17d285 and complete durable inventoryf55206. No old mesh/field archives are copied into these three archives; there are no path overwrites. Each new case retains all29 original output files including its complete DAT/FRD/NPZ/INP, native receipts and whole energy/peak reports. The common delta retains the source, all original pass proofs, strict volume refusal, paired serialized-volume comparison and independent mesh measurements. Runtime packages/binaries remain external.

Use the exact manifest digest recorded by the actual assembly:

```sh
python3 -I -B restore.py verify --manifest-sha256 MANIFEST_SHA --base-capsule ../native-C1-terminal-taper-20261017
python3 -I -B restore.py restore /fresh/output --manifest-sha256 MANIFEST_SHA --base-capsule ../native-C1-terminal-taper-20261017
```

The analysis entrypoint restores the696 inherited/new original paths once, uses the unchanged base audit_energy/locate/binding/simulate sources, and compares the complete four energy/peak reports both as objects and as serialized bytes. It requires the separately attested Python/NumPy runtime, cwd=/, nice10 once and one BLAS thread; it runs no solver, mesher or CAD import. Its150-second alarm/CPU140–141 are additional to a separately reviewed180-second owned supervisor.

```sh
EXACT_PYTHON -I -B replay_analysis.py /fresh/reanalysis --manifest-sha256 MANIFEST_SHA --base-capsule ../native-C1-terminal-taper-20261017 --numpy-site EXACT_ATTESTED_NUMPY_SITE
```

Stored byte verification, report analysis, figure replay and a new native solve are separate operations. The published actual-reproduction companion records completed operations and receipts; command availability alone is not a successful execution. No archive name or captured source is relabelled as a qualified h2 result.
