"""Warp kernel for the synthetic geometry pilot; imported only at execution."""

import warp as wp


@wp.kernel
def point_surface_distances(
    mesh_id: wp.uint64,
    probes: wp.array(dtype=wp.vec3),
    distances: wp.array(dtype=wp.float32),
    hits: wp.array(dtype=wp.int32),
):
    index = wp.tid()
    point = probes[index]
    query = wp.mesh_query_point(mesh_id, point, 1000.0)
    distances[index] = -1.0
    hits[index] = 0
    if query.result:
        closest = wp.mesh_eval_position(mesh_id, query.face, query.u, query.v)
        distances[index] = wp.length(point - closest)
        hits[index] = 1
