# GMP — exact-area trial without adoption

This isolated trial compares the existing `exact_area` function with two GMP paths.
The **110 cases** return exactly the same reduced `Fraction`. On the two
real rings, the integer path gains **1.097× and 1.125×** respectively; the
`mpq` path is slower, around **0.70×**. These measurements cover this
function alone. No gain for a complete builder or for a region is established.
The result does not justify a new production dependency.

The [documentary receipt](archive-summary.json) keeps the 110 exact values,
the 42 raw measurements, the medians, CPU, wall time, RSS, sources and
digests. Each method is measured seven times, in alternating order,
conversions to GMP and back included. The shared workstation was not isolated.
The benchmark uses 6.85 s CPU and 6.89 s wall time; its maximum RSS is
46.3 MB. The separate capture uses 5.27 s CPU and 128.1 MB maximum RSS.

## Trial inputs and software

A private instance of builder `81422bc8` captured its first area call
above 5,000 points: **5,878 points**, then stopped before evaluation.
The historical domain of **5,876 points**, linked to receipt `757b377d`, is a
second, distinct set. Each comparison reuses exactly the same
rational coordinates of its own set. The scalar reference is the
function extracted by AST from source `69b32aee`.

A separate Python 3.11.15 environment contains **gmpy2 2.3.2**,
licence **LGPL-3.0-or-later**, from the official ARM64 wheel of 712,466 bytes.
Its SHA-256 `287060194af46c3de0853a62e89e76acec7c211c40ac2c1d9fabb7216432b642`
matches the saved PyPI metadata. The bundled libraries
are GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1. The official sources consulted
are the [overview](https://gmpy2.readthedocs.io/en/stable/overview.html),
the [installation](https://gmpy2.readthedocs.io/en/stable/install.html), the
[integers](https://gmpy2.readthedocs.io/en/stable/mpz.html) and the
[PyPI metadata](https://pypi.org/pypi/gmpy2/json).

The capture sources and the GMP prefix were digested before/after.
No installation or write was made in the AM runtime; no
retrospective capture of a complete AM identity before this scalar trial
is claimed. The recipe, producers, consumers, checkers
and existing regional calculations are not modified.

## Scope of this archive

The [capture](capture.py), [benchmark](benchmark.py),
[plan](plan.json) and [wheel requirement](requirements.txt) scripts are exact
historical copies. They compute their paths from the original
layout under `work/` and **do not form a standalone launcher from here**.
The compact receipt contains the identities of the original evaluations; the
old absolute paths are metadata, not portable inputs.

The two rational rings, complete evaluations, downloaded documentation,
PyPI metadata, wheel and environment remain in
`work/carrier-process-20261017/gmp-exact-area-001/`. They are not duplicated
in Git. A new run would require these exact inputs and the
historical references, in addition to the separate environment described above.
No replay is launched by this archiving. This trial does not appear in the
carrier's manufacturing recipe.
