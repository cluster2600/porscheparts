# Apex 1435493: retained cavity and existing mesher reuse

This is planning-only saved-data/source reconnaissance. The proposed exact single-apex obstruction remains a separate, pending certificate. No geometry was edited, no mesher or optimizer ran, and no repair or native application is authorized.

## Retained 28-cell complex

The first complete-star census, SHA256 `5946ffbd9f2f127306673d967b583b11d8906793e2079971bc0430d65ae65f88`, contains exactly 28 native ordered tetrahedra incident to interior apex `1435493`. The only initially poor cells in this star are `28946957` and `31225364`. Their original rows, tags, coordinate words and binary64 hex values are retained in [saved-star-observation.json](saved-star-observation.json); coordinate/hex joins were checked byte for byte.

The tetrahedral complex has **17 vertices, 58 edges, 70 faces and 28 cells**, Euler 1. All 42 internal faces contain the apex and occur twice with opposite winding. The 28 remaining faces are exactly the faces opposite the apex. Their shell has **16 vertices, 42 edges and 28 triangles**, one component and Euler 2. Every shell edge has two opposite incidences; every shell vertex link is one simple cycle. Thus this retained complex is a cone over a combinatorial 2-sphere and supplies a closed, conforming cavity shell after its apex and 28 cells are removed.

All 28 signed volumes are strictly positive using exact Fractions of the stored binary64 coordinates. The tetrahedral and oriented-shell volume sums agree exactly at

`1450956179458166404046894365859946143854307 / 522673715590561479879743397015195972796416 mm³`

(approximately **2.776026680084251 mm³**). The shell contains **9 original boundary nodes and 7 other interior nodes**. All 16 would become fixed cavity-interface nodes under a new cavity-only policy; that policy is distinct from their original whole-head classification.

Global completeness is attributed to the frozen census reader, not a fresh native or full-MSH incidence proof. No outside neighbor of these 28 shell facets appears in the selected 5,355-cell report. That omission cannot distinguish physical head boundary from neighbors outside that report. The shell can nevertheless be frozen in its entirety without inventing those labels. Global geometric non-overlap and any replacement-to-head join remain separate checks.

## Smallest existing source route

- `twins/962-cylinder-head-f0/source/mesh_head.py:268` already imports an exact discrete triangle shell, audits its roundtrip, creates a surface loop and volume, and calls `mesh.generate(3)`. Its options include Algorithm3D 1, MeshOnlyEmpty 1, Renumber 0 and both optimization options off. Its `surface_roundtrip`, `volume_arrays`, `tetra_boundary` and `tetra_volumes` are the relevant small kernels.
- `work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py:179` retains that construction and adds tagged arrays, full metric lengths, opposite internal-face checks and saved-file readback. Its caller is specialized to the whole admitted head; it is not a ready-made 16-node/28-face cavity runner.
- `work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py:80` provides the already tested volume-only `createGeometry([(3,1)])` identity check, one `optimize(method='Netgen', force=True)`, `rebuildElementCache(False)`, dynamic interior counts, full tiny audits and saved/reopened identity. Its inspector hardcodes the existing cube geometry and cannot be called unchanged for this cavity. It optimizes an existing volume; it does not itself generate a volume from a shell.

The least new software path is therefore a fixed shell-to-volume caller using the existing discrete-shell construction and audit kernels, followed, only if separately selected, by the existing one-call Netgen/cache-refresh sequence. Do not run surface `createGeometry` or reclassify/retriangulate the shell. Require all 16 coordinate byte strings, including signed zero, and all 28 oriented triangles to survive. Compact local indexing needs an explicit local-to-global map; newly generated interior tags and cell tags need a collision-free global assignment. Existing nodes and cells outside the removed star must remain byte-identical. A later joined full-head readback must check complete face incidence, orientation, saved identity and all native SICN values against the unchanged 0.1 gate.

## Minimal proposed software test and limits

Use the existing nine-node / 12-tetrahedron literal in `direct-sicn-cube-prep-002/direct_sicn_cube.py`, but give the new caller only its eight exact boundary nodes and 12 oriented shell triangles. This tests the new shell-to-volume operation, rather than repeating the completed saved-volume optimization witness. Require exact shell coordinates/connectivity, complete positive TET4 metrics, no orphan or duplicate cells, opposite internal faces, volume 8 mm³ and exact saved/reopened arrays. A missing shell face and a reversed shell face must refuse before meshing. An altered boundary coordinate bit must refuse on readback. Any optional Netgen stage needs its own recorded single-call and before/after/cache checks under the existing owned tiny controller.

A closed cavity does **not** establish quality feasibility. First apply the existing fixed-face necessary screen to the 28 frozen shell triangles; that screen was not recomputed here. Even a necessary pass does not guarantee a SICN-0.1 tetrahedralization. Meshing may retain poor cells, introduce new interior points or fail. Geometry-dependent sizing, any optional optimizer, fresh bounds and the full-head stitch each need an explicit frozen policy and independent result review. No shell retessellation, tolerance relaxation, arbitrary face quota, accepted repair or head-quality conclusion is proposed by this note.
