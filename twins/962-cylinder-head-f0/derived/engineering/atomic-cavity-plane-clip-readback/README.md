# Clipped head: complete array census, quality still rejected

The separately completed read-only census confirms **3,112 poor triangles** in
the assumed z=0 clipped proposal: **2,396 cap faces, 716 mixed-plane faces and
zero faces with no plane vertex**. The strict **2/29** threshold is unchanged.
This identifies where the poor faces are; it supplies no repair or mesh admission.
Coordinates are millimetres.

| Complete readback quantity | Actual result |
| --- | ---: |
| Pre-clip source | 901,727 vertices / 1,803,870 triangles; zero poor faces |
| Clipped proposal | 869,355 vertices / 1,739,126 triangles |
| Exact retained coordinate matches | 865,847 |
| New UINT64_MAX-marked coordinates | 3,508, all exactly z=0 |
| Cap: all three vertices z=0 | 3,508 faces / 2,396 poor |
| Mixed plane/nonplane vertices | 5,260 faces / 716 poor |
| No plane vertices | 1,730,358 faces / zero poor |
| NumPy minimum surface quality | 3.582992623128203e-5 |
| Retained native CGAL minimum | 3.582992623128027e-5 |
| Strict poor-face seed vertices | 3,580 |
| All faces incident to those seeds | 9,872 |
| Exterior-fixed plus legacy exact x=±76 mask count | 865,429 |
| Signed surface volume | 915,453.1229484563 mm³ |
| Cap area | 8,678.423193507433 mm² |

The 9,872-face and 865,429-vertex counts are a **new numerical census**, not an
approved repair region or fixed-mask policy. No connected-patch, disk, component,
target-edge or keeper census was determined. No old 135-edge/228-disk assumption
is transferred. The report retains every poor-face ID in its exact plane class,
class minima and vertex counts, full array hashes, bounds and fresh mask hashes.

All non-sentinel IDs are unique, valid pre-clip local indices and reproduce every
coordinate byte, including signed zero. Sentinel IDs were filtered before any
indexing; new coordinates are on the plane and do not match an existing source
coordinate bit pattern. The entire clipped proposal has z≥0. IDs describe
coordinate matches, not construction history, original894 or OEM identities.
Both surfaces have no orphan vertex, repeated-index/degenerate triangle,
duplicate numeric coordinate or duplicate unoriented index triangle under this
reader. All cap normals point strictly toward −Z. The independent chunked signed
volume and cap area have zero recorded difference to the native report; a positive
signed-volume sum alone is not a closedness or global-topology certificate.

The independent NumPy minimum and retained native CGAL minimum above remain
separate observations, with no equality tolerance invented. Their complete poor
counts agree. The exact frozen helper's `read` and `qualities` definitions were
AST-extracted; its original module imports, caller and census were not executed.
No CGAL, Gmsh, VTK, mesh generation, optimization, geometry output or PDE was used
by this reader. The only actual tiny test checks the plane partition, including
signed zero; its source and return-code-0 record are retained.

## Execution and preserved provenance

The correctly bound readback returned **0** in **8.097497 s**, with no stop reason.
All **16 RSS samples** are preserved; the maximum observed worker RSS was
**588,070,912 bytes**. Controls were 120 s, a sampled 4 GiB RSS stop and two library
threads. These are not a hard OS memory limit, CPU quota or certified peak.
The unchanged e0e runner kills/waits its owned worker through protected cleanup;
no additional post-run OS PID-absence probe is claimed. All 24 actual child inputs
remained unchanged under the completed root/peer checks.

One earlier CLI digest mismatch was refused before a log, output or worker was
created. Its preserved record credits zero worker launches. The corrected exact
contract was then used for the single completed reader invocation; no geometry
operation or repair was retried. The runner retains its older generic
`one_stopped_atomic_mesh_read_only` scope string; the bound reader/report identify
this actual operation as a surface-array census. Historical preparation counters
inside the actual child describe preparation, not the later completed readback.

[original-records.json](original-records.json) identifies exact original copies
and the explicit child projection. Only the private interpreter location is
omitted from that projection: all 24 input pins, runtime hashes/version fields,
source identities and configured controls remain. The selected ARM64 interpreter
hash is bound; NumPy 2.0.2 is checked, while new NumPy extension-file hashes are
explicitly not claimed. Full BIN/coordinate-ID arrays are not included here.
The public helper is identified by whole-file SHA a298270a… and its existing
repository path in the preserved input map.

This is later evidence than the separately sealed
[fixed-plane clipping capsule](../atomic-cavity-plane-clip/README.md). Its original
statement that independent complete head arrays were not yet checked remains an
unchanged point-in-time record. The present census completes only that array and
coordinate-provenance scope. **Global independent topology, intersections,
cap-hole/features/openings and full two-sided CUB are still not completed** for
this clipped proposal. No fresh HXT or head PDE was invoked, and no clipped
volume-mesh quality pass, accepted surface, strength, thermal/material/process
qualification or manufacturing authorization is established.

Run only the standard-library sealed integrity check from this directory:

```sh
python3 -B verify.py
```

It verifies hashes and complete capsule closure. It does not reload head arrays,
rerun the classification test, invoke the reader or establish engineering validity.
