# Installed cooling: optimized tetrahedral mesh remains rejected

Refs #452. Follow-up to the [export correction](../installed-cooling-hxt-export-20261107/README.md)
and [complete native source audit](../installed-cooling-native-source-20261107/README.md).
No historical source, evidence, boundary geometry or acceptance limit changed.

The fresh HXT trial retained default optimization, two threads, 5 mm target
sizing and a 4 GiB sampled-RSS bound. Its declared time budget increased from the
completed 180-second attempt to 600 seconds. Meshing, corrected export and
in-memory checks completed normally in 540.062 seconds, with peak sampled RSS
3,003,432,960 bytes. The old 16-digit export remains private beside the corrected
17-digit file. Independent readback of the latter verifies all 459,068 original
vertices exactly, with zero changed coordinate components. In-memory checks
preserve the original eight boundary triangle sets and find 1,979,148 positive
tetrahedra, whose summed volume matches the source at 0.03198038331459504 m³.
These in-memory topology checks are not an independent exported-connectivity
qualification; no accepted-mesh claim relies on them.

The real OpenCFD 2406 conversion used the previously verified converter route
and 17-digit output. Standard `checkMesh` passes. Extended checks fail two gates:

| Gate | Native failure |
|---|---|
| Cell determinant < 0.001 | 44,239 cells |
| Face interpolation weight < 0.05 | 455 faces |

Concavity, skewness, face tets and cell-volume-ratio checks now pass. There are
still 1,138 severe non-orthogonality warnings. Improvement from the unoptimized
trial does not waive the two remaining failures or establish solver readiness.

## Independent readback of native failure fields

A bounded native `checkMesh -allTopology -allGeometry -writeAllFields` diagnostic
on a separate case copy reproduced the rejection. Reading its actual
`cellDeterminant` field independently reproduces all 44,239 rejected cell IDs:

| Internal faces per rejected tetrahedron | Count | Minimum determinant |
|---|---:|---:|
| 2 | 3,221 | 1.1628e-21 |
| 3 | 40,587 | 1.1178e-5 |
| 4 | 431 | 7.2349e-5 |

The 431 fully internal cells rule out a boundary-only explanation. Every cell
has four total faces, checked independently from owner/neighbour addressing.
The 455 low-weight faces are all internal. The initial hypothesis that a cell
weight field would reproduce both adjacent cells of every rejected face failed;
that failure remains recorded in the result, rather than silently overwritten.

The first surface export command failed because `-writeAllSurfaceFields`
requires `-writeFields` or `-writeAllFields`. The corrected native invocation
used `-noTopology -writeFields '(faceWeight)' -writeAllSurfaceFields` and completed
normally. Independent parsing of its 3,499,228 internal-face values reproduces
all 455 rejected face IDs exactly using `min(w, 1-w) < 0.05`; the minimum is
0.020635066236021307. Its standard-check pass does not supersede the extended
check rejection above.

The [machine-readable result](result.json) binds private receipts and field
hashes. The three native logs are retained verbatim. Raw meshes, quality fields,
failed sets and unsuccessful source-download responses remain private. The
version-specific source request returned a login page, so no source-code
identity claim is made from that response. No flow solver was started and no
physical or manufacturing qualification follows.
