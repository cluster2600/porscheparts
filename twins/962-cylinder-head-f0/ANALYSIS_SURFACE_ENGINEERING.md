# Separate analysis-surface trials

**Every candidate below is rejected. No solver mesh, thermal result, strength
result or manufacturing qualification is established.** The retained original
Ø95 study surface remains unchanged. The small public
[trial receipt](derived/engineering/analysis-surface-trials.json) binds executed
source snapshots, original receipts, candidate arrays and independent audits
by SHA-256. Large NPZ arrays and private runtime payloads are not published.

The original source uses a 0.5 mm voxel discretization. The first
[contract](engineering/analysis-mesh-contract.json) declares a two-sided
continuous surface-deviation budget of **0.25 mm**, half that voxel size. This
is an analysis discretization budget relative to the retained polygon surface,
not original Porsche dimensional accuracy or a manufacturing tolerance.
Tighter 0.125 and 0.0625 mm representations and volume-mesh convergence remain
required. The existing minimum tetrahedral SICN gate stays **0.1**.

| Operation | Actual result | Admission |
|---|---|---|
| First VTK preparation | 21.39 s; rejected at the closed oriented edge-manifold gate | Rejected; implementation did not preserve the failed candidate |
| Distinct diagnostic VTK preparation | 20.39 s; 56,844 vertices and 114,104 triangles; eight four-face edges, no boundary edges or orientation imbalance | Rejected; candidate arrays preserved |
| Exact generated-fin cancellation | 0.635 s; removed 16 triangles and eight unused tips; 56,836 vertices and 114,088 triangles | Independent gates still required |
| Independent continuous distance audit | Both intervals completed; maximum upper bound 2.533575716 mm | Rejected against unchanged 0.25 mm budget |
| Independent global CGAL audit | Complete: 24 intersecting face pairs; zero nonmanifold vertex links | Rejected against zero-intersection gate |
| One corrected VTK metric-input trial | 28.91 s; numeric `AbsoluteError=0.0625 mm²`; 56,909 vertices and 114,234 triangles; eight four-face edges | Rejected at the unchanged topology gate; candidate preserved |

The diagnostic candidate had eight exact opposite-oriented duplicate face
pairs, each with one tip incident only to those two faces and a four-face
attachment edge. A separate
[cancellation contract](engineering/analysis-flap-contract.json) admitted only
that exact generated artifact operation. It did not rerun decimation, weld
coordinates, fill holes or modify the original source. Every retained
triangle's coordinates and orientation remain exact; the private output stores
full before/after face and vertex maps. Cancellation restored a closed oriented
edge-manifold surface with one component and Euler characteristic −208. That
restoration alone did not establish feature preservation or admission.

The cancelled surface encloses 922,499.7337734705 mm³ versus
915,458.1053358027 mm³ for the retained source. Their difference is a geometric
approximation result. The separate 1 ppm tetrahedron-volume bookkeeping gate
would compare tetrahedra with their own accepted analysis surface, if one
were available.

The independent `cascading-upper-bounds` 1.0.0 audit produced these closed
intervals in millimetres, with each upper-minus-lower gap at most 0.0001 mm:

| Direction | Lower bound | Upper bound |
|---|---:|---:|
| Original source → analysis candidate | 2.2468408037053686 | 2.2468786007464416 |
| Analysis candidate → original source | 2.5335486641135008 | 2.5335757163647026 |

The provider reports no exact-arithmetic rounding certificate. Its results are
continuous numerical bounds, not vertex-only samples. Separate identical and
exactly 3 mm translated tetrahedron witnesses passed, confirming units and
bound handling. The pinned local libigl 2.6.3 CGAL audit passed five known-result
fixtures, including coplanar containment and shared-vertex overlap, before
checking every candidate triangle. All 24 reported pairs and the exact runtime
module hashes are retained in the public receipt. No intersection repair ran.

There is also a correction to the VTK parameter description: the frozen first
contract labels `AbsoluteError=0.25` as millimetres. VTK 9.7.1 queues squared
errors (`ComputeSimpleError` returns `dist * dist`) and compares them directly
with `AbsoluteError`; that old field label is misleading. The
[published VTK implementation](https://raw.githubusercontent.com/Kitware/VTK/v9.7.1/Filters/Core/vtkDecimatePro.cxx)
establishes this metric distinction. The independent 0.25 mm acceptance gate
was always separate and rejected the output. One explicitly authorised
[corrected-input trial](derived/engineering/analysis-squared-error-trial.json)
then used `0.25² = 0.0625 mm²` under a
[new frozen contract](engineering/analysis-squared-error-contract.json), with
focused unit-binding tests. It still produced eight nonmanifold four-face
edges, with no boundary edges or orientation imbalance, and was rejected.
No further VTK trials or heuristic parameter tuning are authorised by that
contract. The corrected case and all its hashes are a separate receipt; the
earlier failed receipts and source snapshots remain unchanged.

The source snapshots in [analysis-sources](derived/engineering/analysis-sources/)
preserve the actual first preparation, diagnostic preparation, incidence
diagnosis, exact cancellation and independent auditors. They are evidence
snapshots; their relative imports are not a standalone runtime distribution.
The next method must constrain collapse or remeshing against the original
surface envelope, retain independent two-sided distance and global
intersection checks, and separately establish channel/BCC/port preservation
before any volume-mesh admission. Unchanged fluid domains do not establish
a conforming metal/fluid interface or CHT validation.
