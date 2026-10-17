# Atomic bore95 raw volume: independent quality rejection

One raw HXT trial of the [repaired numerical surface](ATOMIC_CAVITY_ENGINEERING.md)
saves a tetrahedral mesh with positive reported Jacobians and volumes, but it
**fails the unchanged minimum SICN of 0.1**. A separate saved-file reader
confirms the rejection. This mesh is unsuitable for the requested head solves.

The [sealed volume and readback evidence](derived/engineering/atomic-cavity-volume-raw/README.md)
keeps the native result, subsequent inspection and their different acceptance
decisions traceable. Earlier rejected meshes and stopped trials remain intact.

The [rejected MSH review download](derived/engineering/atomic-cavity-volume-raw-review-delivery/README.md)
contains the exact saved mesh and sealed evidence in a 57,736,924-byte ZIP.
All 34 members passed complete independent byte, SHA-256, CRC and size checks.
GitHub digests and sizes match all three uploaded assets; all 36 preceding
asset records and the existing draft release identity remain unchanged.
Import coordinates explicitly as millimetres. This is a rejected numerical
mesh for inspection, with no accepted head simulation.

| Independent saved-file result | Value |
| --- | --- |
| Mesh nodes / linear tetrahedra | 979,076 / 3,058,267 |
| Referenced interior nodes / orphan nodes | 77,349 / 0 |
| Retained source vertices / explicit surface triangles | 901,727 / 1,803,870 |
| Minimum tetrahedral SICN | 1.234770950435885e-10 |
| Tetrahedra below SICN 0.1 | 283,853 |
| Nonpositive SICN, Jacobian or volume values | 0 |
| Independent signed-volume sum | 915,458.1131756522 mm³ |
| Reported relative volume-bookkeeping error | 0.0 |
| Saved MSH bytes | 211,385,374 |

The MSH SHA-256 is
`5092c22174f7dd085058cf414478a9600e5022653e609a6bf385df09e12c3fa7`.
Complete sorted node tags, coordinates, tetrahedron tags and connectivity match
the worker's saved-array digests. The reader independently verifies the exact
source boundary coordinates and explicit oriented surface connectivity. Full
tetrahedral exterior incidence and opposite internal-face orientation remain
the completed native worker's evidence; the reader does not repeat those sorts.

The necessary triangle-quality screen and two-sided 0.0625 mm representation
budget had already passed for this surface. Those results do not ensure good
tetrahedra. The 1.75 mm mesh-size request supplies interior insertion control;
it establishes neither a maximum actual edge length nor thermal resolution or
convergence. The reported volume error is numerical bookkeeping, without a
physical tolerance or exact-arithmetic certificate.

The actual worker uses the separately preserved version002 source, after nine
focused control tests. Its earlier version001 preparation was never executed.
The native trial finishes in a 124.7627025-second controller window, with no
resource stop, under a 300-second deadline and an 8 GiB sampled-RSS stop.
Maximum observed worker RSS is 5,766,807,552 bytes across 243 samples. Its return
code 2 records quality rejection; the worker is stopped and reaped.

The separate read-only controller passes eight focused control tests, then
finishes its actual inspection in 17.535398 seconds with return code 0 and no
resource stop. Maximum observed reader RSS is 1,764,589,568 bytes across 35
samples, below its 4 GiB sampled stop and 120-second deadline. Both experiments
use two requested software threads; these limits are not hard OS memory or CPU
quotas. Recorded before/after input and runtime bindings remain unchanged.

Reader success means completed inspection. Its SICN acceptance flag remains
false. The empty nonpositive-cell list makes the retained
`fixed_boundary_only_nonpositive_cells` flag vacuously true; it says nothing
about which positive cells below 0.1 use fixed
boundary nodes. No such classification is inferred.

A subsequent default post-export optimizer requires its own frozen inputs,
controlled execution, exact-boundary checks, actual quality decision and
independent saved-file review. The earlier 300-second optimizer timeout proves
neither stagnation nor a completion estimate for this new input.

Accepted volume quality, mesh convergence, head thermal and strength fields,
process-specific material qualification, whole-head LPBF simulation, computed
Omniverse fields, PhysicsNeMo evaluation and physical qualification remain open.
