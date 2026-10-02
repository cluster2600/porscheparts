"""GPU ray queries for projected blockage; rays are not fluid trajectories."""
import warp as wp


@wp.kernel
def axial_hits(mesh: wp.uint64, origins: wp.array(dtype=wp.vec3), hits: wp.array(dtype=wp.int32)):
    i = wp.tid()
    query = wp.mesh_query_ray(mesh, origins[i], wp.vec3(0.0, 0.0, 1.0), 200.0)
    if query.result:
        hits[i] = 1
