# 935 original-export-bounded rotor: rejected annular edge split

This experiment subdivides long edges of the one-pass near-planar rotor
from the [ring-flip study](ORIGINAL_BOUND_RING_FLIP_20261028.md), SHA-256
`58991f3f74107dceaf64227a6034b7a700a92e4807e32ca188c0a0f4468f6476`.
The [CGAL source](../../../twins/935-horizontal-cooling-system-f0/source/surface-ring-split-20261028/split_ring_edges.cpp)
selects edges whose midpoint has conditional radius 83–87 mm and invokes
`split_long_edges` with a 1.0-source-unit target. These are numerical trial
settings. The source scale remains unverified and is not a historical 935
dimension.

The operation changes the rotor from 435,499 vertices and 871,018 faces to
506,330 vertices and 1,012,680 faces. A public-source replay reproduced
the surface SHA-256
`44ad8b87471004cd2c52f9f9eb2168b4e11649bed84d3363bb51d1a94eb9adb9`.
The mesh remains closed, consistently oriented, single-component, with
Euler characteristic −10 and the same computed volume. The complete
two-way 0.0225-source-unit envelope against the original PicoGK export
passed, including topology and self-intersection checks. This is a bound
to the export, not to the raw scan.

The four-patch fluid PLC has SHA-256
`5ea9c2b8c5a5964d1a7e57ca7041a87e92b43d3c72b6f7952438b5a7c5114c6c`.
Gmsh 4.15.2 wrote a 5,302,991-tetrahedron volume. The independent
numeric audit confirmed every boundary triangle coordinate set and patch
marker, but found degenerate and inverted tetrahedra:

| Volume | Mean ratio < 0.01 | Mean ratio < 0.05 | Zero signed volume | Negative signed volume | CFD decision |
|---|---:|---:|---:|---:|---|
| Prior one-pass ring flip plus relocation | 878 | 1,076 | 0 | 0 | rejected for quality |
| Edge split, Gmsh Delaunay | 578 | 3,747 | 43 | 1 | rejected |
| Edge split plus one `Relocate3D` | 428 | 2,569 | 43 | 20 | rejected |

The raw and relocated volume SHA-256 values are
`a19db57819dfd2d6aed18bb8de50dd59e3d4262b1dc4c61386e7e359342d4add`
and `a32ee01c27be982db4cd39fa5b5948b8323d5963a205264d55f06e91bad41f9a`.
The signs above are from the float64 independent audit. Gmsh also reported
deleted-tetrahedron cavity warnings during optimization. The lower count
of cells below 0.01 cannot compensate for nonpositive volumes; relocation
made the inversion count worse. **This candidate is rejected and has not
been sent to OpenFOAM for CFD.** No airflow, fitment or manufacturing claim
follows.

The [private trial archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-ring-edge-split-20261028.tar.zst)
contains the surface source and output, two-way certificate, PLC, both
volumes, independent audits and complete Gmsh logs. Its SHA-256 is
`da7c3cc32f323b00f66c6afca254f49ac1664c23fb1c87f82a6018203339eb18`,
matching the private release digest after a local archive integrity check.
The rejected output remains available for diagnosing the nonpositive
tetrahedra, while the one-pass ring-flip surface remains the best of these
bounded trials for further volume work.
