# What is archived

A repository that keeps everything ends up no longer saying what it does. This
document separates what is **active** from what is **kept without being
pursued**, so that the distinction does not depend on the memory of whoever
wrote it.

Nothing here is deleted. Work retired as a product remains useful as a numerical
regression, as a test case and as a record of what did not work.

## Archived — 917 cylinder head and 935 scan

| directory | files | what it is |
|---|---:|---|
| `twins/reference-917-engine/` | 891 | air-cooled 917 cylinder head, iterations F1 to F50 |
| `twins/reference-935-cylinder-head/` | 13 | 935 cylinder head scan, reference morphology |
| `archive/917/docs/` | 112 | the written dossiers for these iterations |
| `docs/media/videos/` | 48 | two rendering projects, F38 and F39 |
| `containers/917-*` | ~40 | dedicated compute images |

**Status.** Retired as a product, kept as a numerical regression. The
rectangular F34 geometry combines parametric CAD, OpenFOAM/FluidX3D, CalculiX
and Cantera **without evidence transferable to a real cylinder head**. F36 keeps
the morphology of the 935 scan. F37 adds the functional STEP files and their
SHA-256 evidence, **metal printing and engine start remaining prohibited**. The
Omniverse audit keeps the NVIDIA topology warning as a blocker.

**What it can be used for**: replaying the calculations, reusing the test cases,
reading what was attempted. **What it cannot be used for**: a part.

## Why these directories were not moved

The question came up on 2026-09-09, and the answer is measured, not aesthetic.

The 917 directory carries **2,014 SHA-256 digests recorded in 275 files**,
verified by 139 test files. Moving it forces a rewrite of the paths it contains;
but those paths live in files that are themselves hashed. The attempt was made:
**142 tests fail, including 40 digest assertions in 31 files**.

Three outcomes, and none of them is good:

- moving without rewriting leaves ~2,260 dead references and the directory is no
  longer executable;
- moving and recomputing the digests amounts to redoing the evidence yourself
  after modifying the parts — a digest recomputed after the fact no longer
  proves anything;
- not moving leaves an imperfect layout.

**The third was chosen.** Evidence is worth more than a tidy directory. This
file exists so that the imperfect layout stops being misleading.

What was moved, because it had no effect on the evidence: the 112 917
documents, taken out of `docs/`, where they made up 60% of the files.

## What can be moved, and what cannot

The rule applies beyond the 917 directory, and it was established by trying.

**This repository binds paths to digests.** Manifests record a path and the
SHA-256 of the file found there; container locks record the path and digest of
embedded scripts; contracts record the digest of their parent. Moving a
directory forces a rewrite of the paths **inside** those files, which changes
their digest and breaks the chain.

Four attempts, four measurements:

| attempted move | result |
|---|---|
| `twins/reference-917-engine/` | 142 tests fail, 40 digest assertions |
| `containers/` | 11 digest assertions, image locks invalidated |
| `scripts/` | `parent_sha_mismatch`, F34 contracts invalidated |
| `catalog/` | the 917 files point to it through `catalog_path`; excluding it from the replacement breaks source resolution |
| `deploy/` | apparently compliant, **then caught**: the F46 readiness report binds the digest of the moved scripts |
| `outils/benchmarks/` | **compliant**, no test lost |

Only the last one could move, because no hashed file names it.

**The `deploy/` case is worth reading**, because it nearly went unnoticed. The
tests were compliant after the move — but `make check` then stopped at the
`test` target and never reached the 37 targets after it. It was when the suite
was made green that the breakage appeared, three targets further on. A red suite
does not only hide its own failures: it hides everything that comes after it.

**The practical rule**: a directory can be moved only if its name appears in no
file whose digest is recorded. Otherwise the tidying would be paid for in
evidence, and evidence is worth more.

Two traps come with any move, which a plain string search does not see: paths
built from segments — `ROOT / "deploy" / ...`, `joinpath("catalog", "sources")`
— and `parents[N]` depths, which assume the number of levels above the file and
silently point to the wrong directory as soon as it is nested one level deeper.

## Duplicate dossiers resolved

Two parts each carried two F0 dossiers, written on different dates: a first
draft with no grade in the name, then the twin dossier suffixed with the
material route. The latter are the only ones referenced by
`docs/AM_VALIDATION_PIPELINE.md` and the only ones carrying the executed
results, the digests and the release refusal.

| removed | kept |
|---|---|
| `docs/993_DOOR_OPENER_LEVER_F0.md` | `docs/993/993_DOOR_OPENER_LEVER_ALSI10MG_F0.md` |
| `docs/993_HEADLAMP_SPRING_HOOK_F0.md` | `docs/993/993_HEADLAMP_SPRING_HOOK_ALSI10MG_F0.md` |

Nothing was lost: the first drafts were contained in the later dossiers, except
for the lever's ordered gates, which were carried over into the kept dossier. No
hashed file named the removed ones, and git history keeps them readable.

## Active

| directory | what it is |
|---|---|
| `twins/964-chassis/` | structural calculation on the 964 body shell, design-of-experiments corpus |
| `twins/993-*` | 993 functional zones: cooling, intercooler bracket, dashboard |
| `catalog/` | 383 source records, 31 part records, measurements and schemas |
| `parts/` | geometries, measurement plans and deliverables per part |
| `docs/993/` | design dossiers for the parts made by additive manufacturing |
| `simulation/` | calculation cases for the forced-induction circuit |

## The rule that applies to both

No part in this repository is declared printable or validated. The 31 records
are all at status `concept`, 17 of them `prohibited_pending_engineering`. A
render is not evidence, neither in the archive nor in the active tree.
