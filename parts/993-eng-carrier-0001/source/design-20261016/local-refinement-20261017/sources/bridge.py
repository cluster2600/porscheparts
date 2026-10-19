"""Experimental T4 lineage / T10 lift, with no real-mesh entry point."""
from collections import Counter
import hashlib
import inspect
import math
from pathlib import Path
import struct

EDGE_PAIRS = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
OUTWARD_FACES = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
GROUPS = ('bolt0', 'bolt1', 'bolt2', 'bolt3', 'end0', 'end1')
PACKAGE_SOURCE_SHA256 = '92a19f6d8e415590cdced77482c71741bd8e766190995abe640b662bfd93b271'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bits(point):
    return struct.pack('>3d', *point)


def edge(a, b):
    return tuple(sorted((a, b)))


def midpoint(a, b):
    return tuple(.5 * (x + y) for x, y in zip(a, b))


def determinant(p):
    a, b, c = (tuple(p[i][j] - p[0][j] for j in range(3)) for i in (1, 2, 3))
    return (a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def compact_t10(nodes, elements, groups):
    """Retain all old nodes separately; compact ONLY tetra corner tags."""
    require(nodes and elements, 'Empty mesh')
    require(all(type(t) is int and t > 0 for t in nodes), 'Invalid node IDs')
    require(all(len(p) == 3 and all(type(x) is float and math.isfinite(x) for x in p)
                for p in nodes.values()), 'Nonfinite or invalid coordinates')
    require(set(groups) == set(GROUPS), 'Unexpected discrete groups')
    require(all(g and all(type(t) is int and t in nodes for t in g)
                and len(set(g)) == len(g) for g in groups.values()), 'Invalid discrete groups')
    require(all(type(e) is int and e > 0 for e in elements), 'Invalid element IDs')
    used, mids, corners, parent_lookup = set(), {}, set(), {}
    for eid, row in elements.items():
        require(len(row) == 10 and len(set(row)) == 10
                and all(type(t) is int and t in nodes for t in row), 'Invalid T10 connectivity')
        key = frozenset(row[:4])
        require(key not in parent_lookup, 'Duplicate tetra corners')
        parent_lookup[key] = eid
        d = determinant([nodes[t] for t in row[:4]])
        require(math.isfinite(d) and d > 0, 'Original orientation is not positive')
        corners.update(row[:4]); used.update(row)
        for n, (i, j) in enumerate(EDGE_PAIRS, 4):
            k = edge(row[i], row[j])
            require(k not in mids or mids[k] == row[n], 'Inconsistent old midside ID')
            mids[k] = row[n]
            require(max(abs(x - y) for x, y in zip(nodes[row[n]], midpoint(nodes[row[i]], nodes[row[j]])))
                    <= 1e-10, 'Original straight-midside serialization guard failed')
    require(used == set(nodes), 'Original orphan node')
    require(not (corners & set(mids.values())), 'Original corner/midside role conflict')
    require(len(set(mids.values())) == len(mids), 'Midside belongs to multiple edges')
    tags = sorted(corners); index = {t: i for i, t in enumerate(tags)}
    return dict(nodes=dict(nodes), elements=dict(elements), groups={k: list(v) for k, v in groups.items()},
                corner_tags=tags, points=[nodes[t] for t in tags],
                cells=[[index[t] for t in row[:4]] for row in elements.values()],
                old_edge_mids=mids, parent_lookup=parent_lookup)



def mark_t4(compact, regions):
    """Mark the SAME whole-edge measurement scope, without enlarging boxes.

    This selects one refinement call; it is not a claim that h/2 will pass.
    """
    require(len(regions) == 2 and len({r['id'] for r in regions}) == 2, 'Expected two fixed regions')
    selected = set(); by_region = {}
    for region in regions:
        lo, hi = region['bounds_mm']; target = region['target_h_mm']
        require(len(lo) == len(hi) == 3 and all(math.isfinite(x) for x in lo + hi)
                and all(a < b for a, b in zip(lo, hi))
                and math.isfinite(target) and target > 0, 'Invalid box or target')
        inside = lambda p: all(a <= x <= b for x, a, b in zip(p, lo, hi))
        marked = []
        for i, cell in enumerate(compact['cells']):
            p = [compact['points'][j] for j in cell]
            centre = tuple(sum(v[k] for v in p) / 4 for k in range(3))
            if any(math.dist(p[a], p[b]) > target and
                   (inside(centre) or (inside(p[a]) and inside(p[b])))
                   for a, b in EDGE_PAIRS):
                marked.append(i); selected.add(i)
        by_region[region['id']] = marked
    return sorted(selected), by_region


def refine_with_ledger(points, cells, marked, package):
    """Observe the pinned package's sole transform=None edge creation call.

    No native execution occurs on import. The private subclass returns the
    exact arrays from super()._find_nz, without changing refinement decisions.
    """
    np = package.np
    require(points.dtype == np.float64 and points.ndim == 2 and points.shape[1] == 3,
            'Expected float64 compact points')
    require(cells.ndim == 2 and cells.shape[1] == 4 and cells.dtype.kind in 'iu', 'Expected T4 cells')
    require(getattr(marked, 'ndim', None) == 1 and marked.dtype.kind in 'iu', 'Marked must be an integer array')
    require(np.isfinite(points).all() and np.all(cells >= 0) and np.all(cells < len(points)), 'Invalid mesh arrays')
    require(np.all(marked >= 0) and np.all(marked < len(cells)), 'Marked index out of range')
    require(np.array_equal(np.unique(cells), np.arange(len(points))), 'Unreferenced compact corner')
    source = Path(inspect.getfile(package.MeshTet1))
    require(hashlib.sha256(source.read_bytes()).hexdigest() == PACKAGE_SOURCE_SHA256, 'Package source drift')
    ledger = []

    class TracedMesh(package.MeshTet1):
        def _find_nz(self, rows, cols, shape, transform=None):
            result = super()._find_nz(rows, cols, shape, transform)
            if transform is None:
                require(shape[0] == shape[1], 'Unexpected edge creation shape')
                for k, (i, j) in enumerate(zip(*result)):
                    ledger.append(dict(vertex=int(shape[0] + k), parents=[int(i), int(j)]))
            return result

    state = np.random.get_state()
    before = (points.tobytes(), cells.tobytes(), marked.tobytes())
    try:
        refined = TracedMesh(points.T.copy(), cells.T.copy(), sort_t=False).refined(marked.copy())
    finally:
        np.random.set_state(state)
    require(before == (points.tobytes(), cells.tobytes(), marked.tobytes()), 'Input mutation')
    require(refined.p[:, :len(points)].T.tobytes() == points.tobytes(), 'Original corner movement')
    require([r['vertex'] for r in ledger] == list(range(len(points), refined.p.shape[1])), 'Incomplete new-edge lineage')
    require(all(0 <= i < r['vertex'] for r in ledger for i in r['parents']), 'Invalid new-edge lineage')
    return refined.p.T.copy(), refined.t.T.copy(), ledger


def boundary(elements):
    faces = {}
    for eid, row in elements.items():
        for local in OUTWARD_FACES:
            face = tuple(row[i] for i in local); key = tuple(sorted(face))
            faces.setdefault(key, []).append((eid, face))
    require(all(len(v) <= 2 for v in faces.values()), 'Nonmanifold corner face')
    return {k: v[0] for k, v in faces.items() if len(v) == 1}


def lift_t10(compact, native_points, native_cells, ledger):
    """Preserve old IDs/XYZ; lineage reuses a bisected edge's old midside.

    The native midpoint can differ from the old midside through serialization.
    This is reported, never interpreted as exact boundary/volume conservation.
    """
    if hasattr(native_cells, 'dtype'):
        require(native_cells.dtype.kind in 'iu', 'Native cells must be integer')
        native_cells = native_cells.tolist()
    if hasattr(native_points, 'tolist'):
        native_points = native_points.tolist()
    points = [tuple(p) for p in native_points]; cells = [tuple(c) for c in native_cells]
    old = compact['nodes']; tags = compact['corner_tags']; nodes = dict(old)
    require(len(points) >= len(tags) and all(bits(points[i]) == bits(old[t]) for i, t in enumerate(tags)), 'Native original corner movement')
    require([r['vertex'] for r in ledger] == list(range(len(tags), len(points))), 'Incomplete lineage')
    index_tags = list(tags); ancestors = [frozenset((t,)) for t in tags]
    next_tag = max(old) + 1; split_edges = {}; deltas = []
    for r in ledger:
        v = r['vertex']; parents = r['parents']
        require(len(parents) == 2 and all(type(i) is int and 0 <= i < v for i in parents)
                and parents[0] != parents[1], 'Invalid parent edge')
        a, b = parents
        require(all(math.isfinite(x) for x in points[v])
                and bits(points[v]) == bits(midpoint(points[a], points[b])), 'Native midpoint/lineage mismatch')
        key = edge(index_tags[a], index_tags[b])
        require(key not in split_edges, 'Repeated split edge')
        t = compact['old_edge_mids'].get(key)
        if t is None:
            t = next_tag; next_tag += 1
            nodes[t] = midpoint(nodes[key[0]], nodes[key[1]])
        split_edges[key] = t; index_tags.append(t)
        ancestors.append(ancestors[a] | ancestors[b])
        if bits(nodes[t]) != bits(points[v]):
            deltas.append(dict(native_index=v, retained_tag=t,
                               native_xyz_hex=[x.hex() for x in points[v]],
                               retained_xyz_hex=[x.hex() for x in nodes[t]]))
    require(len(set(index_tags)) == len(index_tags), 'Duplicate mapped corner ID')
    mids = dict(compact['old_edge_mids']); mids.update(split_edges)
    elements, parents, seen = {}, {}, set()
    for eid, cell in enumerate(cells, 1):
        require(len(cell) == 4 and len(set(cell)) == 4
                and all(type(i) is int and 0 <= i < len(points) for i in cell), 'Invalid native tetra')
        require(frozenset(cell) not in seen, 'Duplicate native tetra')
        seen.add(frozenset(cell))
        roots = frozenset().union(*(ancestors[i] for i in cell))
        require(roots in compact['parent_lookup'], 'No unique original tetra ancestry')
        row = [index_tags[i] for i in cell]
        d = determinant([nodes[t] for t in row])
        require(math.isfinite(d) and d != 0, 'Degenerate mapped tetra')
        if d < 0:
            row[0], row[1] = row[1], row[0]
        for i, j in EDGE_PAIRS:
            key = edge(row[i], row[j])
            if key not in mids:
                mids[key] = next_tag; nodes[next_tag] = midpoint(nodes[key[0]], nodes[key[1]])
                next_tag += 1
            row.append(mids[key])
        require(len(set(row)) == 10, 'Duplicate T10 node')
        elements[eid] = tuple(row); parents[eid] = compact['parent_lookup'][roots]
    require(set(t for row in elements.values() for t in row) == set(nodes), 'Retained or new orphan node')
    require(all(bits(nodes[t]) == bits(p) for t, p in old.items()), 'Old node movement')
    old_boundary = boundary(compact['elements']); new_boundary = boundary(elements)
    counts = Counter(parents.values())
    require(set(counts) == set(compact['elements']), 'Original tetra lost')
    require(all(n > 0 for n in counts.values()), 'Original tetra lost')
    inverse = {t: ancestors[i] for i, t in enumerate(index_tags)}
    face_parent = {}
    for key in new_boundary:
        roots = tuple(sorted(frozenset().union(*(inverse[t] for t in key))))
        require(roots in old_boundary, 'New exterior face lacks original facet ancestry')
        face_parent[key] = roots
    require(set(face_parent.values()) == set(old_boundary), 'Original exterior facet lost')
    outside = {k for k, (e, _) in old_boundary.items() if counts[e] == 1}
    require(all(k in new_boundary and face_parent[k] == k for k in outside), 'Exterior changed outside closure')
    return dict(nodes=nodes, elements=elements, groups={k: list(v) for k, v in compact['groups'].items()},
                boundary_faces=[v[1] for _, v in sorted(new_boundary.items())],
                parent_elements=parents, boundary_parent_faces=face_parent,
                closure_parent_elements=sorted(e for e, n in counts.items() if n > 1),
                old_node_count=len(old), native_to_retained_midpoint_differences=deltas,
                all_old_nodes_used=True, old_node_ids_xyz_unchanged=True,
                exact_boundary_or_volume_conservation_claimed=False)


def write_inp(path, original_node_lines, old_nodes, lifted):
    """Copy each old NODE row exactly; serialize only new nodes as roundtrip."""
    require(set(original_node_lines) == set(old_nodes), 'Incomplete original NODE lines')
    for t, line in original_node_lines.items():
        fields = line.strip().split(',')
        require(line.endswith('\n') and len(fields) == 4 and int(fields[0]) == t
                and bits(tuple(float(x) for x in fields[1:])) == bits(old_nodes[t]), 'Original NODE line mismatch')
    with Path(path).open('x', encoding='ascii', newline='') as stream:
        stream.write('*NODE\n')
        for t in sorted(old_nodes):
            stream.write(original_node_lines[t])
        for t in sorted(set(lifted['nodes']) - set(old_nodes)):
            stream.write(str(t) + ',' + ','.join(format(x, '.17g') for x in lifted['nodes'][t]) + '\n')
        stream.write('*ELEMENT,TYPE=C3D10,ELSET=BODY\n')
        for eid, row in lifted['elements'].items():
            stream.write(str(eid) + ',' + ','.join(map(str, row)) + '\n')
