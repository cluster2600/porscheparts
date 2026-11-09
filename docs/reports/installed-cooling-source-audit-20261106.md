# Installed cooling: upstream surface admission audit

For [#452](https://github.com/cluster2600/porscheparts/issues/452), the retained
five-millimetre mesh still fails its extended check with three concave cells.
Before changing mesh settings, this audit reread the source-surface checks
using the exact pinned OpenCFD 2406 image on native linux/arm64 in Docker.
All 41 files named by the historical CFD receipt matched their recorded hashes.
No source, threshold, mesh or solver setting changed.

| Exact retained surface | Triangles | Units | `surfaceCheck` self-intersection flags |
|---|---:|---|---:|
| CFD duct, eight patches | 91,812 | m | 517 locations |
| Native delivery-fluid STL | 918,136 | mm | 9,922 locations |

Both checks also report a closed surface, one connected part, consistent
normal zones and no illegal triangles. Those checks alone therefore do not
establish admission. Both processes exit zero even though their diagnostic
text reports self-intersections; exit status must not be used as admission.
The flags are a tool finding, not independently established intersection
geometry or a physical-part verdict.

The [receipt](installed-cooling-source-audit-20261106/receipt.json) binds inputs,
runtime, constraints and the complete diagnostic logs. Each invocation used
two CPUs, 2 GiB, a 90-second timeout, no network and read-only source mounts.
The commands were `surfaceCheck -checkSelfIntersection -outputThreshold 0`
against the decompressed retained files. No remeshing or flow solver ran.

A copy converted from millimetres to metres by `surfaceTransformPoints`
reported 12,095 locations. This is retained as an unresolved precision/scale
sensitivity, not an additional accepted comparison: conversion also rewrites
coordinates. The exact native and CFD counts must not be compared as a
quantitative improvement. An earlier independent NumPy topology attempt under
amd64 emulation reached its 90-second timeout with no result; it supplies no
geometry verdict. Its script and failure receipt remain in the local audit
directory, and the script hash is recorded here.

Next, recover the flagged triangle witnesses and adjudicate them independently
with controlled units and serialisation precision. Only then choose a
traceable source correction, preserving the existing failures. The three
concave volume cells have not yet been localised or repaired, and mesh
independence remains unexecuted. Surface, mesh, physical and manufacturing
admission remain closed.

## Bounded independent witness search

The 517 flagged points were recovered in a new retained Docker volume. An
independent libigl 2.6.3 triangle-intersection search on the Mac found no
non-adjacent, non-coplanar interior-crossing witness before reaching its
10,000 candidate-pair limit (473 of 517 points visited; the last may be partial).
The [search receipt](installed-cooling-source-audit-20261106/independent-search.json)
records input and helper hashes, candidate bounds, synthetic self-checks and
exclusions. This incomplete search neither proves absence of intersections
nor independently confirms the OpenCFD flags. Adjacent/coplanar cases and
precision sensitivity remain unresolved. No geometry edit is justified yet.
