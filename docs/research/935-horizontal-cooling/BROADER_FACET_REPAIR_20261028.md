# Broader local rotor facet repair — 28 October 2026

This is an exploratory numerical surface repair, not a calibrated 935 part or
an approved CFD domain. The unchanged PicoGK rotor export and aligned scan
remain private. Dimensions below are in uncalibrated scan source units unless
explicitly described as conditional.

## Surface experiment

The previous local repair left 35 triangles below normalized quality 0.05.
Twenty-seven were missed by its needle/cap predicates. A new, separately
versioned CGAL experiment selects faces below 0.05 using needle threshold 25
and cap threshold cos(172°), while retaining the 0.020 edge-collapse limit,
three-ring local constraint and minimum 0.05 quality for newly created faces.
Its source and analytic regression control are in
`twins/935-horizontal-cooling-system-f0/source/surface-facet-broader-20261028/`.
Build with CMake, Boost 1.92.0 and CGAL 6.2.1, then run `ctest` in the build
directory. The original frozen recipe is unchanged.

The protected input has 439,365 vertices and 878,730 faces; the candidate has
439,306 vertices and 878,612 faces. Quality counts below 0.01 changed from 24
to 4, and counts below 0.05 from 113 to 10. Minimum quality increased from
0.0000541 to 0.00710. All retained candidate vertices coincide with input
vertices; 59 were removed. Independent checks found a closed genus-one surface
without self-intersections. The generator reports that its outside-patch
vertices and faces are unchanged; completion is not claimed by the algorithm.

The full conservative polyhedral envelope check rejected source face f489399.
Separately, the complete bidirectional CGAL bounded-error Hausdorff comparison
against the 1,319,474-face native PicoGK export gave estimates 0.0136621 and
0.0122925 with error bound 0.0025, both below the 0.0225 gate after adding
that error. This measures distance to the exported surface, not fidelity to
the original measured object. See the [CGAL distance documentation](https://doc.cgal.org/latest/Polygon_mesh_processing/group__PMP__distance__grp.html).
The two tests have different guarantees; the envelope rejection is retained.
The [private full-distance receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/broader-native-picogk-distance-20261028.tar.gz)
has SHA-256 `3536c2cedab35fa200718474f8b6c7128aa730d2064824db643e27e98bc9498b`.

Of 59 removed vertices, 27 are within 0.5 source unit of a sampled aligned scan
vertex, 5 are between 0.5 and 1, and 27 are farther than 1. This screening is
not a classification of measured or repaired surface, and is not a tolerance.
[Private location map](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/broader-facet-removed-vertices-20261028.png).
The [private surface checkpoint](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/broader-facet-checkpoint-20261028.tar.gz)
has SHA-256 `2f2408f1456bd1cf865fbc3ed143e757cc5fb92bdb7e204ac006f3eed632939e`.

## Provisional fluid mesh tests

Both trials use an exploratory, unmeasured duct and the conditional conversion
0.001 m per source unit. Neither proves engine fit or air performance.

* Gmsh 4.15.2 retained all 895,614 boundary triangles and produced 4,789,771
  positive tetrahedra. 1,222 have quality below 0.01. A precision-17 OpenFOAM
  import preserved all 1,009,234 points exactly, but `checkMesh` reported
  seven failed checks. The mesh is rejected for CFD. An earlier default
  precision import changed 1,009,144 points and was rejected as a transport
  error; its negative-cell results must not be attributed to the source mesh.
* Native cfMesh produced 995,358 cells and failed eight `checkMesh` checks,
  including six highly skew faces, 355 low-determinant cells and 62,983
  concave cells. It is also rejected for CFD. This trial does not establish
  boundary fidelity or validate an airflow solution.

The [private native Gmsh and precision-audit archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/broader-gmsh-native-precision-20261028.tar.zst)
has SHA-256 `74cf55ebd56931658348c66ce259709c2633767b3c2a60348e2eae3cc3a2714f`.
The full Gmsh generation archive has SHA-256
`d5649b2e3d72434c2f0a3925f68e24befc2b7dfa88dbd425ae6d9f393a471361`.
The [private cfMesh case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-cfmesh-broader-20261028.tar.zst)
has SHA-256 `98aaaf3bbb77feb36f29bf4dad5f3d464204cd835738e33dd3f025dd487e447b`.

The next work is to diagnose volume-mesh defects and achieve independent
surface fidelity and all mesh-quality gates before solving airflow. Scan scale,
mounting datums, hidden mechanism details and physical validation remain open.
