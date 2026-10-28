# Held one-call coupled cavity SICN diagnostic

Source preparation only. The input is the original immutable Netgen cavity:
19 nodes, 39 ordered TET4 cells, 16 fixed local shell nodes and free tags 27,
28 and 29. It is not the rejected isolated-apex proposal. The completed exact
fixed-triple screen `7ced0eae…` retained 28 one-free/three-fixed cells and all
126 same-apex pairs without an obstruction certificate; that was inconclusive,
not a feasibility pass. This caller adds all 39 simultaneous cell constraints,
including the 11 cells containing multiple free nodes.

The previous complete before-state/typed-array association and exact metric,
integer topology and signed-volume helpers from `88e7166f…` are copied
unchanged. Vector signed-SICN, tag indexing, coordinate assembly and the selected
NumPy/SciPy loader/inventory helpers from `e7d61ca1…` are copied unchanged. All
39 initial vector qualities must match their saved native values under the
existing combined `rel_tol=1e-11, abs_tol=1e-14` calibration. This initial floating
calibration is distinct from the final exact acceptance predicate.

One SLSQP invocation optimizes nine coordinates plus an epigraph t. The objective
is `-t`; all 39 signed constraints are `Q_i(x)-t>=0`. Coordinates have no bounds.
The existing epigraph bounds are initial vector minimum through 1. Settings are
unchanged from the tiny witness: maxiter 100, ftol 1e-10 and absolute finite-
difference eps 2^-26. There is no new coordinate box, grid, restart, derivative,
regularization or arbitrary quality tolerance. Negative vector qualities remain
violations; the unchanged vector helper refuses undefined/nonfinite or exactly
planar iterates. A failed call without a returned vector does not establish a
final point.

Every finite returned ten-vector is retained before success-based rejection.
The diagnostic retains all 19 resulting coordinates/hex rows and all 39 exact
Fraction native-order determinants/Q-squared values. Undefined or nonpositive
cells fail; exact quality feasibility means every determinant>0 and Q²>=1/100.
That predicate is independent of solver status. A feasible point with a false
solver-success flag is labelled `feasible_point_solver_not_converged`, retained
and returned RC2. A converged exact-feasible point returns RC0 but remains
unapproved for native application. Rejected finite points retain the same full
records. Displayed signed square roots and epigraph values are telemetry, not
native or interval certificates. Epigraph-bound telemetry is separate from
coordinate quality feasibility.

All 16 shell coordinate words, including signed zeros, must remain exact.
Connectivity is unchanged. Complete integer incidence and exact before/final
signed-volume bookkeeping are recorded against the frozen oriented shell.
Signed-volume cancellation can hold in an inverted candidate; it does not
replace the positive-cell gate. Embedding, non-overlap, containment and head
stitchability are unverified. Local fixed-shell nodes are not reclassified as
original global head boundary nodes.

The existing owned tiny controller `5b9c10be…` is reused with six reversible
label/environment/declaration substitutions only. Its 30-second deadline,
sampled 1 GiB RSS stop, sampled 16 MiB output stop, process-group kill/wait/reap,
SIGTERM handling and final deadline latch stay unchanged. Two software threads
are requested, now including the already-used Accelerate environment setting.
There is no hard OS CPU/RSS quota. It declares one SLSQP call and zero Gmsh,
mesh-write or solve calls; declarations are not observed counters. The prior
13 controller mocks remain reference evidence, not a new mock execution.

The compact root-only check is prepared and unrun. It AST-extracts actual
helpers and imports only the selected NumPy for synthetic vector/mapping rows;
no SciPy/optimizer/Gmsh or saved geometry is read by that check. It tests exact
orientation/quality, all-three-node assembly, raw fixed-bit drift including
signed zero, feasible-nonconverged status, one-call/no-coordinate-box policy and
truthful controller declarations. The author only read/wrote source/metadata,
compared ASTs and hashed project evidence. No prepared function, test, query or
scientific/native module was executed or imported by the author.

Registered runtime values are inherited: Python 3.12.11, NumPy 2.2.6, SciPy
1.17.1, with 32 selected file identities and no Gmsh runtime. They are not a
fresh current check or complete package/OS/ABI closure. Supplemental loaded-file
inventories before and after a returned point are observations of selected
packages, not environment attestation. Root must freshly hash all selected
inputs/runtime, review/run the compact check, and freeze a separate exact child
with explicit one-call authority, reviewed source/controller and fresh owned
output. Output and actual-child identities remain null while held.

The output is geometric analysis JSON, not a native coordinate application or
MSH export. There is no Gmsh, head operation, stitch, solver field, material or
physical qualification, general repair/impossibility claim, retry or fallback.
Solver success does not establish global optimality. All engineering, physics
and manufacturing acceptance flags remain false.
