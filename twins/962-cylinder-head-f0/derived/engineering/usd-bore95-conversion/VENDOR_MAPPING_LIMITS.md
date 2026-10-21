# Why another vendor flag is not yet an exact-preservation remedy

The pinned NVIDIA guidance describes three relevant behaviors: removal of
degenerate triangles, float32 mesh points recentered at the representation
item's bounding-box centroid, and optional welding of repeated position/normal
pairs. These are distinct operations. See the official [mapping description at
the pinned commit](https://github.com/NVIDIA-Omniverse/usd-convert-cad/blob/208fe2c1cd71ae2bb7bd825daf712617000ae028/docs/concept_mapping.md#b-rep-poly-brep-and-meshes).

`--no-dedup` disables welding and reindexing; the documentation does not say it
disables triangle removal or centroid recentering. The documented global-frame,
instancing and tessellation options do not promise preservation of every source
triangle, coordinate and pivot. Native inspection of the installed 0.2.0
`Parameters` interface found no exposed preservation or disable-recenter/cull
control. The pinned public repository supplies guidance, not the native
implementation or its numerical degeneracy threshold.

The documented behavior is consistent with the rejected derivative's face
loss and recentering. It does not independently identify all 254 omitted source
triangles. No additional vendor conversion or tolerance change was performed.

The smallest proposed next route is explicitly separate OpenUSD authoring of
the original indexed mesh using the existing source reader and `UsdGeom.Mesh`.
It would keep every triangle, winding and original float32 coordinate, use
millimeter/Z-up stage metadata and the original pivot, set subdivision to
`none`, and introduce no material, physics schema or solver field. The same
strict complete-mesh comparison and genuine minimum validation would apply.
This is a proposal; it has not been implemented or run by this evidence set.
