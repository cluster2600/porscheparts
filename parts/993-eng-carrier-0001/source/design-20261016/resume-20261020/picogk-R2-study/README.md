# R2 closing with certified tool-clearance correction

This separate study uses PicoGK closing R2 mm / 0.2 mm voxels and MeshLib's
0.04 mm estimated-error request, then the declared nominal-pad restoration.
The first open-column certificate refused genuine interference. The design
therefore caps the complete 231 intruding source facets to Z=4, moving 125
vertices downwards by at most 0.284809 mm. This is an intentional clearance
edit; no mesh-error threshold was relaxed. XY and all face indices remain
unchanged, and fresh surface/column checks pass.

- `surface.mesh64.gz`: complete 609,140-vertex / 1,218,348-triangle surface.
- `pad-changed-vertices.json.gz`: complete first nominal-pad edit ledger.
- `cap-changed-vertices.json.gz`: complete second clearance-design ledger.

The exact nominal dense mass is **1.29819981344 kg** at 4,420 kg/m³, leaving
**1.80019 g** below the requested 1.30 kg ceiling. Independent integer surface
and rational tetrahedron sums produce exactly the same complete volume.
All 2,645,661 tetrahedra have positive exact orientation; their boundary is
identical to this surface. Six shank gauges pass, and the exact full-facet
certificate excludes all four open nominal tool columns. The original
polygonal closed-set gauge refusals are retained separately.

The first combined-load C3D4 case completes with equilibrium checks passing:
2.246491 mm displacement maximum and 1,008.611 MPa unconverged elastic peak.
Stress convergence and strength acceptance remain open; this surface has not
replaced the selected catalogue geometry.

[Detailed workflow and actual comparison image](../../../../../../docs/reports/carrier-resume-20261020/README.md#r2-closing-and-local-clearance-design-edit).
