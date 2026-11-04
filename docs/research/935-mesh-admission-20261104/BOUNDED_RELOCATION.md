# Bounded vertex relocation on the whole study surface

Date: 2026-11-04. This is a new operation after the rejected
[bounded quad flips](BOUNDED_QUADS.md). It preserves triangle connectivity but
permits small tangent movements of unprotected vertices. The independently
checked surface passes the registered gate for a study-volume meshing trial.
It is not an acquired-scan repair, a complete bare head or a functional release.
The [surface and Kali checkpoint](bounded-relocation.json) retains aggregate
results and hashes. The subsequent paid retry is tracked separately.

## Input admission and fixed contract

The input is the same frozen coarse reconstructed assembly: 1,048,504 vertices
and 2,099,584 triangles, with attached hardware and inferred closures. Its source
NPZ, protection mask, immutable helper and native CGAL inspector are hash-checked
before execution. Native inspection of the actual parent OFF finds no degenerate
faces or intersection pairs and accepts its closed polygon mesh. No original
OBJ, source-supported CAD or earlier study artifact is modified.

All 111,463 protected triangles remain fixed. Edges adjacent to protected faces
and original dihedrals over 30 degrees have both endpoints locked. Independent
classifications agree on 492,169 locked edges and 342,090 locked vertices.
Of the original 8,489 triangles below shape quality 0.01, 1,338 have all three
vertices locked. With fixed connectivity, even an otherwise perfect relocation
could remove at most 84.24% of that category. This necessary bound allows the
registered 50% target; it does not assert that relocation will achieve it.

The [driver](source/trial_bounded_relocation.py) makes one deterministic
worst-first visit to the initially eligible vertices. Local triangle-quality
gradients are projected into the original area-weighted tangent plane. Candidate
steps are the fixed 0.0099 mm bound and half that bound. A move must preserve
orientation against every original incident-face normal, worsen no currently
bad face, create no newly bad face and decrease the local squared quality
deficit. Selection first minimizes bad-face count, then deficit. There is no
parameter sweep, edge split/collapse, diagonal flip or hidden-surface inference.

Seven software controls verify analytic triangle quality, the quality gradient
against finite differences, a genuinely changed skinny-fan witness, witness
quality improvement, locked coordinates, movement bound and tangent motion.
The initial controller used a local environment without libigl and failed
before creating a trial output. That preparation failure is retained. Reusing
the already installed repair environment succeeds with unchanged source and
parameters. No global package or existing runtime was modified.

## Executed and independently verified surface result

| Quantity | Parent | Relocated candidate |
|---|---:|---:|
| Triangle shape quality below 0.01 | 8,489 | 1,792 |
| Minimum triangle quality | 3.30356862 × 10⁻⁶ | 3.30356862 × 10⁻⁶ |
| Signed enclosed volume, mm³ | 1,106,103.0255224346 | 1,106,103.0255797373 |
| Degenerate faces / native intersection pairs | 0 / 0 | 0 / 0 |

The driver considers 13,273 free vertices and moves 6,296. It removes 6,697 bad
triangles, a **78.8903% reduction**, above the predeclared 50% requirement.
All connectivity, locked coordinates and protected triangles remain exact.
The worst triangle remains poor; meeting this surface-study target does not
qualify all boundary elements or any stress result.

Of the remaining 1,792 bad faces, 1,338 have all vertices locked and 454 have
at least one free vertex. There are 670 directly protected bad faces. The unique
minimum-quality face has all three vertices locked. These are constraint classes
on the study surface, not anatomical diagnoses or evidence of a specimen defect.

The [independent verifier](source/verify_bounded_relocation.py) reloads the actual
candidate NPZ and native OFF, reconstructs the locks from the parent, checks the
complete changed-vertex list and independently recomputes quality, winding
orientation, volume and displacement. All nine admission checks pass. Four
negative controls refuse changed connectivity, moved locked coordinates,
excess displacement and reversed triangles; a barycentric sample control also
passes. The reported maximum movement is 0.009900000000026199 mm, below 0.01 mm;
the final digits reflect binary floating-point coordinates.

For a point in any indexed parent triangle with barycentric weights λᵢ, use the
same triangle and weights in the candidate. Its displacement is Σ λᵢ Δvᵢ, whose
norm is at most Σ λᵢ ‖Δvᵢ‖, hence at most the largest vertex displacement. This
correspondence exists in both directions and covers every triangle, including
interiors. It gives a whole-surface bound against this exact study parent,
without relying on random distance samples. It is a double-precision coordinate
bound, not interval arithmetic, physical metrology, a surface-normal bound or a
minimum-thickness guarantee. The parent's unsupported closures remain unsupported.

## Native tetrahedral comparison

The [bounded native runner](source/run_relocated_tet.py) uses an isolated Kali1
runtime and the unchanged historical `mesh_solid.py`. It requires this independent
surface admission and a passing analytic cube before starting the head trial.
The fixed settings are 1.5 mm interior size, Gmsh algorithm 10, two CPU cores,
7 GiB child address space and a 900-second head deadline. It kills the task's
process group on timeout. No existing Docker permissions, packages or service
configuration are changed.

The [official Gmsh 4.12.1 package](https://pypi.org/project/gmsh/4.12.1/)
was downloaded without project data and installed offline only in the new private
task runtime. Its Linux wheel SHA-256 is
`a3f3b7f4ebd2d2b9e14f51ddbee708e5a54ba1035f41586b932e48b15a9bcb15`.
The actual API reports 4.12.1; existing Python 3.12.11 / NumPy 2.5.4 are reused.
This is separately recorded from the older container's distribution-version
string. The new cube passes positive-cell, unit-volume and shape checks.

The two-core head trial reached its registered 900-second deadline and returned
SIGTERM (`-15`) after 900.068 seconds. Its output directory is empty. A fresh
process check finds no remaining matching mesher. Sixteen terminal files were
recovered and hash-verified. **No new volume mesh was produced or accepted.**
The cube's actual 12 tetrahedra were independently checked: all volumes are
positive, total volume is one, its 18 interior faces cancel and its actual
oriented boundary matches the declared boundary. The
[tetrahedral verifier](source/verify_relocated_tet.py) checks actual cell-face
incidence, cancellation of interior winding, exact admitted boundary coordinates
and oriented facets, positive cell volumes, all-node use and surface-volume
agreement. The retained independent quality metric and its analytic controls
are reused; mean ratio is distinct from Gmsh minSICN. Neither metric alone grants
physics admission. This verifier has passed its analytic controls and real cube
checks; it has not validated a nonexistent head mesh from the timed-out trial.
No new physics solver case is authorized by this surface result.

After this verified CPU-bound timeout, a separate paid retry uses the unchanged
mesh-CFD image from the historical study, the same admitted surface and mesher,
up to 24 CPU threads, a 24 GiB child address-space limit and a 1,800-second head
deadline. The [cloud worker](source/run_cloud_relocated_tet.py) requires a fresh
cube control first. The [local billing guard](source/guard_mesh_rental.py) is
armed before creation, binds cleanup to the owned instance ID in the launch
receipt, and verifies absence. It does not destroy every instance with a matching
label. Its offline integration control destroys only fake ID 123 and preserves
unrelated fake ID 999; no real API is used by that test.

The paid attempt is capped at USD 1.50, network included, within the unchanged
USD 35 program / USD 30 compute allocation and USD 5 transfer-closeout reserve.
The hourly guard is USD 0.40 including the 120 GB disk, with a one-hour absolute
deadline and network rates capped at USD 0.005/GB for this selected offer.
The first offer was rejected before creation; a subsequent validated offer
created one task resource. As of this checkpoint, its runtime/cube and uploaded
hashes pass and its head meshing is active. This does not establish completion,
recovery, final billing or destruction; those require separate terminal evidence.
The guard depends on the controller/network/provider, so absence is checked
after cleanup rather than assumed from a timer.

## Private artifacts and replay

Private bundle: `~/Developer/PorschePartsArtifacts/935-bounded-relocation-20261104/`.
It retains source snapshots, both preparation attempts, actual argv/logs,
registered plans, parent/candidate OFF and NPZ, moved-vertex IDs and independent
reports. Geometry and native fields remain outside Git. Public aggregate metrics
and hashes are recorded in the companion receipt after terminal verification.

For replay, use the retained repair Python 3.12 environment and the hash-bound
solid/mask/inspector, with fresh output directories. Run the surface driver and
separate verifier under a 600-second outer controller; native inspections have
300-second child bounds. Only after independent admission, transfer the checked
candidate and report to a fresh private Linux task directory and run the native
tetrahedral control/trial with its recorded runtime and limits. Retrieve and
rehash terminal results before inspection; never overwrite the frozen bundle.

The surface work and initial tetrahedral attempt use local Mac/Kali resources;
the separately tracked retry rents one prepared Vast task. No external model
service, supplier contact, original-OBJ upload or manufacturing order is made.
The complete-head
goal, material/load/process requirements and all physical release gates remain
unfulfilled. The [completion review](../935-readiness-20261104/README.md) remains
the wider engineering context; its latest rejected-mesh finding describes the
earlier quad-flip operation, not this subsequent successful surface study.
