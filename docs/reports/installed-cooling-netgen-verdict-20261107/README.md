# Installed cooling: Netgen improves quality but remains rejected

Refs #452. This follows the [optimized HXT rejection](../installed-cooling-optimized-verdict-20261107/README.md).
No historical inputs, source coordinates, boundary triangles or acceptance
limits changed. The existing full-source audit remains the upstream basis.

Two imported-mesh cube controls failed independent checks: the first produced a
duplicate tetrahedron, and the second produced internal faces that did not
cancel. Neither route was used on the duct. Netgen optimization on the live GEO
volume passed the cube control: 12 positive tetrahedra, exact rational unit
volume, original boundary triangles and cancelling internal faces.

The duct used Gmsh 4.15.2 HXT with default optimization, followed by one Netgen
optimization call on that live volume (`force=False`, `niter=1`). Target sizing
remained 5 mm with two threads and a 900-second bound. The first attempt stopped
at its 4 GiB sampled-RSS limit without an export. A separate trial, after a host
resource check, raised only that bound to 8 GiB. It completed in 542.847 seconds
with peak sampled RSS 4,421,500,928 bytes. Both receipts remain recorded.

Independent readback of the corrected 17-digit MSH2 export verifies all original
source coordinates and eight boundary triangle sets exactly, no duplicate
tetrahedra, 918,136 boundary faces and cancellation of 3,275,152 internal faces.
All 1,867,110 float64 tetrahedral volumes are positive; their sum is
0.031980383314595046 m³. Connectivity checks are exact; full-mesh volume
arithmetic is float64, not a rational proof.

The pinned OpenCFD 2406 converter completed normally. Standard `checkMesh`
passes, but extended checks still fail:

| Gate | Optimized HXT | HXT plus Netgen |
|---|---:|---:|
| Cell determinant below 0.001 | 44,239 | 26,005 |
| Internal-face interpolation weight below 0.05 | 455 | 15 |

The minimum determinant is 1.2430106220918849e-5 and minimum interpolation
weight is 0.03485735581655538. Concavity, skewness, face-tet and cell-volume-ratio
checks pass. There are still 1,026 severe non-orthogonality warnings.

Owner/neighbour readback finds no remaining tetrahedron with only two internal
faces. Of the rejected cells, 25,377 have three internal faces and 628 have four.
Thus the remaining failures are not exclusively boundary-adjacent. All 15
low-weight faces are internal. These observations identify remaining defects;
they do not establish a geometry repair or justify relaxing either gate.

The [result](result.json) binds private receipts and the three retained native
logs by SHA-256. Raw meshes, fields and failed controls remain private. No duct
flow solver was started. This result grants no physical or manufacturing
qualification.
