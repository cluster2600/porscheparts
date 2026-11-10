# Installed cooling: complete surface check and local-refinement rejection

For [issue #452](https://github.com/cluster2600/porscheparts/issues/452), the
retained CFD duct now has a complete independent intersection check. Its
unchanged five-millimetre volume mesh was reproduced and its three failed cells
localised. One targeted refinement was executed and rejected. **No volume mesh
is admitted, and no flow solver ran.**

This continues the bounded search in
[PR #612](https://github.com/cluster2600/porscheparts/pull/612); the old results
remain unchanged. The [result and execution identities](result.json) bind the
new inputs, runtimes, logs and private collection manifests. The
[installed-cooling study](../../../twins/993-installed-cooling-f1/README.md)
remains an uncalibrated layout, not a measured engine assembly.

## Complete surface audit

The exact retained ASCII STL contains 91,812 triangles. Decoding its coordinates
as binary64 and indexing only exactly equal coordinates produces 45,906 vertices;
reconstructing every triangle reproduces all decoded coordinates exactly. No
triangle was removed, no tolerance used, and no coordinate moved.

The existing read-only
[CGAL auditor](../../../twins/m64-cylinder-head/source/wholebody/surface_intersections_cgal.cpp)
was compiled unchanged in the retained CGAL 6.2.1 image on native Linux/amd64.
It returned **zero intersection pairs with `complete=true`**, below its unchanged
100,001-pair cap. Crossing, separated, shared-edge, coplanar-overlap-with-a-shared-
edge and coplanar-disjoint controls give the expected results. Thus the earlier
10,000-pair search cap and adjacent/coplanar exclusions no longer limit this
independent predicate check.

Separate indexed-topology checks find one component, 137,718 edges, exactly two
oppositely oriented uses per edge, and a single circular link at every vertex.
The signed volume is 0.031969668783959265 m³. These results do not establish
physical dimensions or the quality of a volume mesh.

The historical OpenCFD `surfaceCheck` finding of 517 locations is retained as a
disagreement, not independently confirmed crossings. Its exact numerical
mechanism has not been established. The retained VTP export stores Float32
coordinates and is not substituted for the ASCII STL in this comparison.

## Exact baseline replay and one rejected correction

All 41 historical receipt files were hash-verified. The replay uses the exact
OpenCFD 2406 linux/arm64 image, unchanged dictionaries and source STL, and a
fresh native Linux Docker volume. Both mesh runs use four CPUs, 8 GiB, no network,
a read-only container root and a 600-second timeout. No flow command is present.

| Run | Cells | Standard check | Extended check | Native elapsed time |
|---|---:|---|---|---:|
| Unchanged 5 mm | 254,917 | Pass | 3 concave cells; 1 failed check | 19.917 s |
| Three local refinement boxes | 256,594 | Pass | 173 concave cells; 1 failed check | 23.850 s |

The original failed cells are 1011, 209765 and 238179. Each is an eight-vertex
hexahedron touching the wall patch. Original face, owner and neighbour records
independently match the VTK cell point identities. VTK's Float32 point output
was rejected as the coordinate authority; localisation instead reads the
original ASCII mesh coordinates directly into binary64.

The sole correction trial adds one refinement level inside each failed cell's
bounding box plus 5 mm padding in each direction. Only `snappyHexMeshDict`
changes. Surface coordinates, boundary fields, snapping controls, quality
thresholds and global cell caps remain unchanged. No further parameter sweep
was run.

All **173** rejected cells in the new mesh are level-0 polyhedral cells adjacent
to level-1 cells. Forty-four touch a boundary; the others are internal. This
localises the new failure to the coarse/fine transition. It does not demonstrate
the detailed numerical cause or justify relaxing the concavity check. The
trial is not adopted.

The [baseline standard](unchanged-5mm-standard.log) and
[extended](unchanged-5mm-extended.log) checks, and the
[refinement standard](local-refinement-standard.log) and
[extended](local-refinement-extended.log) checks retain the native findings.
Both runs returned zero despite failing the extended mesh criteria: exit status
alone is not admission.

## Remaining gate

Address the original wall-cell deformation without introducing inadmissible
refinement transitions, then repeat both mesh checks under unchanged quality
limits. The [experiment plan](../../../twins/993-installed-cooling-f1/experiment-plan.json)
still requires at least three admitted resolutions with port-flow/pressure
sensitivity, mass balance, stability and residual checks. None of those flow
or mesh-independence results is supplied here. Physical correlation, installed
heat rejection and manufacturing remain unqualified.

Raw meshes, exact cell coordinates and complete trial directories are retained
outside Git with collection hashes. The failed binary-STL assumption and the
rejected Float32 localisation attempt are also preserved. No source repair,
paid compute, original-evidence rewrite or engineering release occurred.
