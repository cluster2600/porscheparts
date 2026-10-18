# 962 head: native volume-meshing trials

The [public numerical receipt](derived/engineering/meshing-trials.json)
separates two actual native trials from the later saved-mesh audits.
The original Ø95 study surface remains unchanged: **902,145 exact vertices,
1,804,706 oriented triangles and 915,458.1053358027 mm³**.
No tolerance welding, surface repair or surface remeshing was applied.

| Trial | Actual result | Acceptance |
| --- | --- | --- |
| Delaunay, Gmsh algorithm 1, 2 threads | Stopped at the 300 s native deadline during refinement; controller wall time 300.084 s includes process cleanup | No completed volume result or quality gate |
| HXT, algorithm 10, 4 threads | Meshing finished in 18.328 s; original controller failed its surface element-tag assertion, total 31.007 s | Original failure retained; separate geometric audit below |

Both used native ARM64 Gmsh 4.15.2, linear tetrahedra, `Mesh.MeshOnlyEmpty=1`,
disabled surface-to-volume size extension and no mesh optimizer.
Each trial has its own fresh directory, source snapshot, deadline and receipt.
The public controller now also requires a one-time source-bound worker claim;
direct hidden-worker invocation cannot overwrite prior results.

## What the independent HXT audit established

The original post-mesh assertion required the original triangle element tags.
HXT changed those tags. It preserved every original coordinate, all triangle
rows, their vertex order and their orientation. The independent audit compares
the exact oriented triangle set, allowing element permutations and cyclic
vertex rotations while rejecting reversals, lost faces and changed connections.
This changes a bookkeeping assertion, not a geometry or quality threshold.
The original failed receipt is not rewritten.

- **3,096,302 tetrahedra**, with three added interior nodes.
- **Zero missing and zero new oriented surface triangles.** The actual tetra
  boundary matches the same source surface, with no nonmanifold volume faces.
- All sampled native minimum Jacobians, volumes and SICN values are finite and
  positive; independently calculated signed tetra volumes are also positive.
- Summed volume: **915,458.1053358029 mm³**, a relative difference of
  **2.22 × 10⁻¹⁶** from the retained source volume. The predeclared **1 ppm**
  limit is numerical bookkeeping, not a manufacturing tolerance.

| Metric | Minimum | 1st percentile | 5th percentile | Median |
| --- | ---: | ---: | ---: | ---: |
| SICN | 1.464 × 10⁻¹⁶ | 0.0001921 | 0.009780 | 0.1052 |
| Jacobian determinant, mm³ | 1.615 × 10⁻¹⁶ | 0.00001621 | 0.0008763 | 0.7687 |
| Signed tetra volume, mm³ | 2.692 × 10⁻¹⁷ | 0.000002702 | 0.0001460 | 0.1281 |

The saved mesh passes the declared **geometric** gate. Nearly singular elements
and its size prevent accepting it as an engineering analysis mesh. There is
no thermal or structural solve, mesh-convergence result, strength claim or
manufacturing authorization.

## Evidence and reproduction

The 210,471,830-byte HXT MSH stays local at
`work/962-engineering/indexed-volume-hxt-001/failed-current-mesh.msh`, with
SHA-256 `4f902544f34ab6d083ca2719bd6e7d731392a8514299d4d9b3afb21520a4fdf4`.
The public receipt records the immutable hashes of local meshes, logs and raw
receipts, plus the full quality distributions. No large MSH is committed.

Small [executed-source snapshots](derived/engineering/meshing-sources/) preserve
the exact Delaunay, HXT and audit implementations. They are provenance records
for their original execution locations, not standalone scripts to run from
the archive directory. In particular, the later corrected
[calculator](source/mesh_head.py) is not falsely attributed to the original
Delaunay or HXT execution. The two historical source snapshots remain intact.

The current implementation supports a distinct fresh trial in the verified
native runtime; no success or byte-identical mesh is promised:

```sh
/path/to/verified-geometry/bin/python -B \
  twins/962-cylinder-head-f0/source/mesh_head.py \
  --algorithm hxt --bore 95 --deadline-s 300 \
  --output work/962-engineering/new-hxt-trial
```

Eleven source-independent tests pass, including exact indexing, preservation
of near-distinct coordinates, malformed/nonfinite/degenerate input rejection,
surface orientation, independent signed volume, canonical triangle identity,
deadline bounds and worker/output reuse refusal.

The next stage is a separate topology-preserving analysis representation with
a predeclared two-sided source-deviation budget and stricter solver-mesh quality
gates. It must preserve feature/channel topology and existing clearance checks.
The original meshes remain the reference; a derived mesh does not improve
their historical fidelity or establish physical qualification.
