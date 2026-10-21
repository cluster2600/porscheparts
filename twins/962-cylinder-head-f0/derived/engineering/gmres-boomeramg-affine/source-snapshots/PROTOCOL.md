# GMRES and BoomerAMG harmonic diffusion witness

Prepared for root review only. No native solver is authorised or executed.
This is a synthetic installed-runtime test, with no head geometry, material,
service temperature, strength, LPBF or physical qualification.

Solve −Δw=0 in the dimensionless cube [1,2]³ with w=x+2y+3z on every
boundary. The 3×3×3 HEX8 mesh has 64 scalar Q1 nodes, 56 boundary nodes and
eight genuine interior unknowns. The boundary data range from 6 to 12 and
are nonzero everywhere. The zero initial field is not the solution. Unit
diffusivity is a software coefficient, not a candidate head material.

One steady NEWTON invocation and exactly one linear solve use assembled SMP, GMRES and PETSc HYPRE
BoomerAMG. BoomerAMG has one V-cycle per application and zero internal
tolerance; GMRES retains its independent stopping criteria. No CG/SPD claim,
solver installation, settings sweep, fallback or retry is authorised. Actual
PC setup must be visible in the native KSP report; compiled HYPRE support
alone does not pass the witness.

## Frozen proposed checks

All numeric tolerances below are software-research choices, not physical
allowables. A missing, partial, nonfinite or ambiguous export fails closed.

- Exactly 64 unique finite spatial samples must cover the complete declared
  4×4×4 node grid, with coordinate consistency ≤1e−12. Every node is checked
  against the affine reference. Relative maximum and unweighted nodal RMS
  errors must each be ≤1e−10; boundary absolute error must be ≤1e−10. All eight
  interior samples must exist. No row=node assumption is made.
- Native diffusive flux −∇w·n integrated separately over the six faces must
  agree with (+1,−1,+2,−2,+3,−3) for left/right/bottom/top/back/front, each
  within absolute 1e−9. Net-flux cancellation alone cannot pass. Independently
  reconstruct all 54 outer Q1 cell-face integrals from the complete nodal
  field on the declared structured mesh, using exact face-average derivatives;
  require the same face criteria and native-versus-independent agreement.
  This reconstruction uses the frozen GeneratedMesh topology, not a general
  imported-head mesh or a mesh-convergence demonstration.
- Export the actual KSP operator A, preconditioner matrix P, right-hand side b
  and Newton correction y from that same single linear solve, in PETSc MATLAB ASCII
  format. Require complete finite 64×64 matrices and length-64 vectors,
  with exactly one matching block in each file. More than one solve/block fails
  this frozen witness; exports must never be selected merely by filename or
  mixed across solves. PETSc v3.25.2 KSPSolve_Private lines 958–967 retrieve
  A/P and view both together with its own vec_rhs and vec_sol; these
  correction vectors are not the final
  spatial w field. Check each true residual ||Ay−b||₂/||b||₂≤1e−10, with finite
  nonzero denominator; record native true-residual history and convergence
  reason, and require successful native convergence with no divergence.
- Bind every consumed export, log, CSV and source snapshot to the stopped
  native artifact manifest. Reject missing, changed, symlink or torn files.
  Recheck the receipt and complete manifest after assessment. Check current
  assessor/input identity against the same frozen contract; finite inputs
  whose derived arithmetic overflows also fail.
- Inspect the actual constrained matrix: exactly 56 identity rows within
  1e−12, leaving eight free rows; report the off-diagonal Dirichlet-column
  couplings and full/free-subspace symmetry defects. Require the actual free
  block symmetry defect ≤1e−12 and A/P relative Frobenius difference ≤1e−12.
  These observations are not positive-definiteness or preconditioner-SPD
  certificates. The native free matrix versus independently assembled
  geometric P1 stiffness comparison remains **unestablished**; node↔DOF
  mapping and tetrahedral head import remain later obligations.

The configured numeric matrix/viewer route is supported by the exact
installed PETSc library's option strings and PETSc v3.25.2 source. Its
successful use by this particular MOOSE input remains untested until the
single authorised witness is run. If an actual numeric operator is unavailable,
retain the exact diagnostic and stop; do not replace it with a guessed matrix.

## Execution boundary

Reuse the owned read-only MOOSE rootfs, bwrap user/PID/network isolation and
explicit clean environment. Proposed per-invocation limits: 30 s soft timeout,
5 s kill grace, systemd scope RuntimeMaxSec=45, MemoryMax=2 GiB, no swap,
CPUQuota=200%, TasksMax=128; one MPI rank and one OpenMP/BLAS thread. These
are witness limits, not a head budget. Fresh outputs only; preserve logs and
failed exports; never overwrite the frozen input or shared runtime. The
contract and all source/input/runtime hashes must match before launch and
after completion. Source preparation is not launch authorization.

## Primary provenance

- PETSc v3.25.2: https://gitlab.com/petsc/petsc/-/blob/v3.25.2/src/ksp/ksp/interface/itfunc.c
  (`KSPSolve_Private`, lines 958–967, views A/P, `vec_rhs` and `vec_sol` from
  that same KSP; `KSPViewFinalResidual_Internal`, lines 747–770, recomputes
  the residual from that operator and those vectors).
- PETSc v3.25.2 HYPRE adapter:
  https://gitlab.com/petsc/petsc/-/blob/v3.25.2/src/ksp/pc/impls/hypre/impl/ihypre.c
  (options at lines 997–1007; actual V/iteration/tolerance report at
  lines 1388–1392). These source bytes are primary API evidence, not an
  attestation that the installed binary was built from this exact checkout.
- PETSc viewer syntax: https://petsc.org/release/manual/other/#viewing-from-options
- HYPRE options: https://petsc.org/release/manualpages/PC/PCHYPRE/
- MOOSE field samples: https://mooseframework.inl.gov/source/vectorpostprocessors/NodalValueSampler.html
- Boundary function: https://mooseframework.inl.gov/source/bcs/FunctionDirichletBC.html
- Flux convention: https://mooseframework.inl.gov/source/postprocessors/SideDiffusiveFluxIntegral.html
- DOFMapOutput lists variable/subdomain DOFs; its output is not a node↔DOF map:
  https://mooseframework.inl.gov/docs/doxygen/moose/classDOFMapOutput.html

The normalized head protocol/addendum remains unchanged. This witness cannot
satisfy its representation refinement, actual head import, field convergence,
material, CHT, strength or manufacturing obligations.
