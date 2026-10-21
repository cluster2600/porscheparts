# PicoGK rounded surface with nominal pad restoration

`surface.mesh64.gz` is the complete 617,023-vertex / 1,234,122-triangle study.
The text format starts with vertex/triangle counts, then XYZ coordinates in
millimetres, then zero-based triangle vertex indices. Gzip is lossless.
`changed-vertices.json.gz` records every moved vertex and its exact rational cost.

PicoGK closing uses 0.2 mm voxels and R1 mm, followed by MeshLib's 0.04 mm
estimated-error request. The pad restoration maps a declared neighbourhood to
nominal Z = ±4 mm. It changes no face indices. Its complete two-way edit
bound is 0.041844 mm relative to the preceding simplified mesh; it does not
certify the preceding voxelization or its distance to native CAD.

The complete surface audit passes. Six nominal shank gauges pass. The original
closed-set tool-column test remains refused because of planar contact at Z=4.
A separate exact full-facet certificate proves exclusion from all four open
nominal tool-column interiors (radius < 12.5 mm, 4 < Z < 40 mm).

This is an editable indexed surface study. It is not the catalogue-selected
geometry. New mechanics and full print preparation are separate stages.

[Report and actual section image](../../../../../../docs/reports/carrier-resume-20261020/README.md#nominal-pad-restoration-and-exact-tool-column-exclusion).
