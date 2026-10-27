# Cell refinement at constant solid fraction

## What this answers

The refinement study of 2026-10-22 reported that the periodic gyroid unit cell
does not converge: the full tensor change from N=48 to N=64 is **2.2369%**,
above the declared **2%** condition. That number is correct, and this study
does not dispute it. It asks a different question: what was being measured.

The earlier sequence held the gyroid level-set threshold fixed at
`0.6170021750539874` for every resolution. A fixed threshold resampled on a
different grid does not reproduce the same solid. Its actual solid fraction
moved as the grid changed:

| N | actual solid fraction | error against the 40% design point | full tensor change |
|---|---:|---:|---:|
| 16 | 0.4062500 | +1.560% | — |
| 24 | 0.4120370 | +3.007% | 2.434% |
| 32 | 0.3964844 | −0.881% | 4.271% |
| 48 | 0.3990162 | −0.248% | 1.605% |
| 64 | 0.4038086 | +0.950% | 2.237% |

Those five fractions are reproduced exactly, to seven decimal places, from the
published threshold and the cell-centre sampling of the earlier source. The
sequence of tensor changes is **not monotone** — 2.434, 4.271, 1.605, 2.237 —
which a refinement sequence approaching a limit would not do, and each change
tracks the fraction drift that precedes it. The 2% condition was therefore
charging a change of geometry to discretisation.

## What is changed

One thing. The threshold is solved per resolution so that the **actual** solid
fraction matches a declared target, instead of being inherited from another
grid. The target is the design point the earlier study itself declared: the
fraction its fixed threshold produces at the separate 96³ sampling,
**0.4000097**.

The formulation is otherwise untouched: the same C3D8 grid, the same periodic
equations, the same six strain modes, the same periodic-residual, energy,
reaction-work, reciprocity and positivity acceptance, and the same 2% spatial
and 1% void-floor conditions, with unchanged numerical tolerances.

Attainable fractions are multiples of 1/N³, so the target is met to within half
a cell: the residual error is 0.400% at N=16 and falls with resolution, against
the ±3% excursion of the fixed threshold.

## Result

Holding the actual solid fraction constant, both completed refinements pass
the unchanged 2% condition, where the fixed-threshold sequence failed both:

| comparison | actual fraction | fixed threshold | constant fraction |
|---|---:|---:|---:|
| 16 → 24 | 0.4016113 → 0.4008970 | 2.434% fail | **0.601% pass** |
| 24 → 32 | 0.4008970 → 0.4000854 | 4.271% fail | **1.418% pass** |
| 32 → 48 | — | 1.605% pass | refused, see below |

Void-floor sensitivity stays far inside its 1% condition at every resolution:
0.0852%, 0.0814%, 0.0788%. The residual fraction error falls as the grid
allows, 0.400% → 0.222% → 0.019%.

Two successive passing refinements is what the spatial condition asks for. It
is obtained here at N=16/24/32, which are coarser than the N=48/64 pair that
failed; this does not retroactively convert that pair into a pass. What it
shows is that the condition is satisfiable once the compared grids carry the
same solid, and that the earlier failures coincided with the fraction
excursions rather than with refinement.

## N=48 refused twice, for two different and recorded reasons

- **Single thread: time.** Return code 124, wall timeout at 1200.86 s on the
  first strain case, peak solver RSS 8,187,625,472 bytes, process reaped,
  inputs unchanged, no finished marker. Memory was never the constraint: that
  peak is 7.63 GiB against a 10 GiB allowance. The runner's hard ceiling is
  1200 s per solve.
- **Eight threads: a wrong solve, caught.** Re-running the sequence
  multithreaded to beat the clock failed at N=16, the very case that passes
  single-threaded. Strain mode 0 reproduced the single-thread energy residual
  exactly, 5.095e-10; mode 1 then failed the energy and reaction-work check.
  The solver returned 0 with a finished marker, so only the physical check
  detected it.

  This independently reproduces, on a Linux build, the SPOOLES dependency race
  the earlier work measured on the Mac binary at 142 wrong solves in 500. It
  is the reason this study is single-threaded, and the reason the refusal is
  recorded rather than the run being retried until it passed.

Completing 32 → 48 therefore needs either the separately built SPOOLES-fixed
binary of the earlier study, or a raised per-solve ceiling for the
single-threaded path. Both are owner decisions; neither is taken here.

## Declared differences from the earlier study

These are differences, not improvements, and results are not comparable to the
earlier tensors bit for bit.

- **Solver binary.** CalculiX 2.21 Linux, SHA-256
  `6adaabf5bf0382fc2bfd692b984320ed375dba777f7dc8297562f818043faa1b`, from the
  cadsim image. The earlier study used a separately built Mac `ccx_2.21`.
- **Threads.** One. This build does not carry the SPOOLES dependency-race fix
  of that Mac binary, and the earlier work established that unfixed
  multithreaded SPOOLES returns wrong solves.
- **N=64 is not attempted.** Its peak solver RSS was 16.81 GiB and this host
  has 15 GiB in total. It is excluded by declaration rather than attempted and
  refused.

## What this does not establish

No carrier convergence, no cellular geometry, no part, no strength or fatigue
allowable, and no manufacturing release. A unit-cell stiffness tensor that is
stable under refinement is a necessary condition for the homogenisation step,
never a qualification of the carrier.
