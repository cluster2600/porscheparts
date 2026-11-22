# Cell refinement at constant solid fraction, finished on a GPU

## What this answers

The [constant-fraction study](../constant-fraction-20261026/README.md) held the
gyroid's actual solid fraction at 0.4000097 and passed the 2% condition from
N=16 to 24 and from 24 to 32. It declared N=48 as well and was refused there:
one CalculiX thread passed the runner's 1200 s ceiling, and multithreaded SPOOLES
returned a wrong solve. This study finishes that series and extends it to N=64
and N=80, under a [contract](contract.json) written before any GPU run.

**Result: the cell stiffness is converged at constant solid fraction, under the
unchanged 2% condition, in both series the contract names.**

| N | Actual solid fraction | Minimum stiffness ratio | Change from the previous N | Void-floor change |
|---:|---:|---:|---:|---:|
| 16 | 0.4016113 | 0.1600792 | | 0.085% |
| 24 | 0.4008970 | 0.1603254 | 0.601% | 0.081% |
| 32 | 0.4000854 | 0.1622004 | 1.418% | 0.079% |
| 48 | 0.4001646 | 0.1642047 | **1.129%** | 0.076% |
| 64 | 0.4000206 | 0.1648568 | **0.573%** | 0.074% |
| 80 | 0.4000391 | 0.1658318 | **0.591%** | 0.073% |

- **The declared study** (N = 16, 24, 32, 48) is converged: 24 to 32 and 32 to 48
  both pass.
- **The extension** (N = 64, 80) is converged: 48 to 64 and 64 to 80 both pass.
- **The fixed-threshold series is not rewritten.** Its 48 to 64 change was 2.237%
  with the fraction moving from 0.3990 to 0.4038; at constant fraction the same
  step is 0.573%. That supports the earlier diagnosis that the failure measured a
  change of solid, not of discretisation; the failed series stays as it was.
- **The stiffness still rises a little at each step.** The smallest normalised
  eigenvalue goes from 0.1622 to 0.1658 between N=32 and 80, by 0.4% to 1.2% a
  step. That is inside the declared 2% condition; a tighter condition would need
  its own declaration before any further run.

## How it was solved

[rve_c3d8.py](rve_c3d8.py) states the same discrete problem as
`run_constant_fraction_case.py`: the same cells (its geometry functions are
imported, not copied), C3D8 elements with 2 x 2 x 2 Gauss points, E = 107 GPa or
E x floor, nu = 0.31, six macro strains of 0.001, periodic fluctuation with node
(0,0,0) held. The deck's `*EQUATION` set is written as u = H x + w with w periodic,
which spans the same solutions. The six modes share one factorisation of the
assembled stiffness.

- **Qualification before use** ([qualification.json](results/a100-20261122/qualification.json)).
  At N = 16, 24 and 32 and both void floors, the GPU tensors differ from
  CalculiX's committed tensors by 4.3e-10 to 1.5e-9, against a limit of 1e-6 fixed
  in the contract. CalculiX prints seven significant digits; the differences sit there.
- **Every case passes the earlier study's checks:** one periodic solid component,
  energy residuals at most 1.1e-13 (limit 1e-4), antisymmetry at most 5.7e-14
  (limit 1e-4), positive eigenvalues under the Voigt bound. Two checks are added:
  the algebraic residual of the solve (at most 5.0e-14) and the energy of the
  assembled stiffness against the macro energy.
- **A closed form:** with the void as stiff as the solid, the cell returns the
  isotropic tensor to 2e-14 (`tests/test_993_carrier_cell_gpu.py`).

| N | Unknowns | Nonzeros | Factorise and solve, six modes | Wall time |
|---:|---:|---:|---:|---:|
| 48 | 331,773 | 26,873,379 | 4.5 to 4.9 s | 9 s |
| 64 | 786,429 | 63,700,515 | 15 s | 25 s |
| 80 | 1,535,997 | 124,415,523 | 43 s | 62 s |

**Machine:** one NVIDIA A100-SXM4-80GB rented on Vast.ai, AMD EPYC 7532 host
(30.7 CPUs and 242 GiB allowed), image `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`,
nvmath-python 1.0.1 with cuDSS ([receipts](results/a100-20261122/receipts/)). The
rental lasted about ten minutes, installation included, and cost USD 0.16.

## One refusal, kept

The first N=80 case stopped in the factorisation with `cuDSS ALLOC_FAILED`: its
factors do not fit in 80 GB of GPU memory
([refusal](results/a100-20261122/refusal-n80-cudss-alloc-failed.json)). Before any
N=80 tensor existed, an [addendum](n80-execution-addendum.json) declared one retry
with cuDSS's hybrid memory mode, which keeps the factors in host memory and leaves
the matrix, the factorisation and every check unchanged. Both N=80 cases then
passed; the GPU held 74 GB at its peak. The cases up to N=64 ran with
`rve_c3d8.py` at SHA-256 `8c149bb8…`, the N=80 cases with `f6e35e2e…`, which adds
only that backend switch; each assessment records its own hash.

## Reproduce

```text
pip install "nvmath-python[cu12]" nvidia-cudss-cu12 cupy-cuda12x scipy
python -I study.py OUT cudss            # N = 16 to 64; N=80 needs cudss-hybrid on an 80 GB GPU
python -I rve_c3d8.py 16 1e-6 0.4000097 scipy OUT/n16   # CPU check, about 15 s
```

## What this does not establish

No carrier convergence: the whole-carrier comparison still fails on its two stress
peaks ([report](../../../../../docs/reports/carrier-convergence-20261022/README.md)).
No cellular geometry, no part, no strength or fatigue allowable, no measured
interface and no manufacturing release. A converged cell tensor is a necessary
condition for the homogenisation step, never a qualification of the carrier.
