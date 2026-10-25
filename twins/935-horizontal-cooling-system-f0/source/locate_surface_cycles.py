"""Locate a tree-cotree homology basis without modifying a closed surface.

Method: https://jeffe.cs.illinois.edu/teaching/comptop/2023/notes/22a-homology.html
Cycles identify topological passages, not their mechanical purpose or validity.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra, minimum_spanning_tree


def surface_cycles(vertices, faces):
    """Return vertex-index cycles and counts; refuse non-manifold surface maps."""
    v, f = np.asarray(vertices), np.asarray(faces)
    if (v.ndim != 2 or v.shape[1] != 3 or len(v) < 4 or not np.isfinite(v).all()
            or f.ndim != 2 or f.shape[1] != 3 or len(f) < 4
            or not np.issubdtype(f.dtype, np.integer) or f.min() < 0 or f.max() >= len(v)):
        raise ValueError('Finite indexed triangle surface required')
    # Edge identities multiply indices by the vertex count; mesh index widths can overflow.
    f = f.astype(np.int64, copy=False)
    if len(np.unique(np.sort(f, axis=1), axis=0)) != len(f):
        raise ValueError('Repeated triangles refused')
    tri = v[f]
    if np.any(np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) == 0):
        raise ValueError('Degenerate triangles refused')
    origin, target = f.ravel(), np.roll(f, -1, axis=1).ravel()
    keys, inverse, counts = np.unique(np.minimum(origin, target)*len(v) + np.maximum(origin, target),
                                      return_inverse=True, return_counts=True)
    if np.any(counts != 2) or len(np.unique(origin)) != len(v):
        raise ValueError('Closed surface with every vertex used required')
    pairs = np.argsort(inverse, kind='stable').reshape(-1, 2)
    if not np.array_equal(origin[pairs[:, 0]], target[pairs[:, 1]]):
        raise ValueError('Opposite edge orientations required')
    opposite = np.empty(len(origin), dtype=np.int64)
    opposite[pairs[:, 0]], opposite[pairs[:, 1]] = pairs[:, 1], pairs[:, 0]
    rotation = 3*(opposite//3) + (opposite+1)%3
    if not np.array_equal(origin[rotation], origin):
        raise ValueError('Invalid vertex-link permutation')
    _, representatives = np.unique(origin, return_index=True)
    current, starts = representatives.copy(), representatives.copy()
    visited = np.zeros(len(origin), dtype=bool)
    while len(current):
        visited[current] = True
        current = rotation[current]
        active = current != starts
        current, starts = current[active], starts[active]
    if not visited.all():
        raise ValueError('Each vertex must have one circular link')

    a, b = keys//len(v), keys%len(v)
    lengths = np.linalg.norm(v[a]-v[b], axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths <= 0):
        raise ValueError('Finite positive edge lengths required')
    graph = coo_matrix((lengths, (a, b)), shape=(len(v), len(v))).tocsr()
    distance, parent = dijkstra(graph, directed=False, indices=0, return_predecessors=True)
    if not np.isfinite(distance).all():
        raise ValueError('One connected surface required')
    children = np.arange(1, len(v))
    tree_keys = np.minimum(children, parent[children])*len(v) + np.maximum(children, parent[children])
    tree = np.zeros(len(keys), dtype=bool)
    tree[np.searchsorted(keys, tree_keys)] = True
    if tree.sum() != len(v)-1:
        raise ValueError('Invalid primal spanning tree')
    available = np.flatnonzero(~tree)
    face_pair = pairs[available]//3
    weights = -(distance[a[available]] + lengths[available] + distance[b[available]])
    dual = coo_matrix((weights, (face_pair[:, 0], face_pair[:, 1])), shape=(len(f), len(f))).tocsr()
    cotree = minimum_spanning_tree(dual).tocoo()
    if cotree.nnz != len(f)-1:
        raise ValueError('Invalid dual spanning tree')
    dual_keys = np.minimum(face_pair[:, 0], face_pair[:, 1])*len(f) + np.maximum(face_pair[:, 0], face_pair[:, 1])
    order = np.argsort(dual_keys)
    rows, cols = cotree.row.astype(np.int64), cotree.col.astype(np.int64)
    chosen = np.minimum(rows, cols)*len(f) + np.maximum(rows, cols)
    indices = order[np.searchsorted(dual_keys[order], chosen)]
    if not np.array_equal(dual_keys[indices], chosen):
        raise ValueError('Dual edge identity mismatch')
    used = tree.copy(); used[available[indices]] = True
    chi = len(v)-len(keys)+len(f)
    remainder = np.flatnonzero(~used)
    if chi > 2 or chi % 2 or len(remainder) != 2-chi:
        raise ValueError('Invalid closed orientable surface characteristic')
    cycles = []
    for edge in remainder:
        left, right = [int(a[edge])], [int(b[edge])]
        while left[-1] != right[-1]:
            path = left if distance[left[-1]] >= distance[right[-1]] else right
            ancestor = int(parent[path[-1]])
            if ancestor < 0 or len(left)+len(right) > len(v)+1:
                raise ValueError('Invalid cycle ancestry')
            path.append(ancestor)
        cycle = np.array(left + right[-2::-1] + [left[0]], dtype=np.int64)
        if len(cycle) < 4 or len(np.unique(cycle[:-1])) != len(cycle)-1:
            raise ValueError('Simple closed edge cycle required')
        cycles.append(cycle)
    return cycles, dict(vertices=len(v), triangles=len(f), edges=len(keys),
                        Euler_characteristic=chi, genus=(2-chi)//2, basis_cycles=len(cycles),
                        every_vertex_link_is_one_circle=True, geometry_modified=False,
                        shortest_cycle_basis_claimed=False, mechanical_feature_identity_verified=False)
