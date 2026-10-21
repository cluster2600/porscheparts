"""Small indexed-complex census, adapted from the retained patch topology checks."""
from collections import Counter, defaultdict


def connected(nodes, edges):
    neighbours = {int(v): set() for v in nodes}
    for a, b in edges:
        neighbours[int(a)].add(int(b)); neighbours[int(b)].add(int(a))
    count = 0; unseen = set(neighbours)
    while unseen:
        count += 1; pending = [unseen.pop()]
        while pending:
            for v in neighbours[pending.pop()] & unseen:
                unseen.remove(v); pending.append(v)
    return count


def incidence(faces):
    result = defaultdict(list)
    for fid, triangle in faces.items():
        if len(triangle) != 3 or len(set(triangle)) != 3:
            raise ValueError('Three distinct local vertex IDs required')
        for a, b in zip(triangle, triangle[1:]+triangle[:1]):
            result[tuple(sorted((a, b)))].append((fid, a, b))
    return result


def face_groups(faces):
    neighbours = {fid:set() for fid in faces}
    for rows in incidence(faces).values():
        group = {row[0] for row in rows}
        for fid in group:
            neighbours[fid].update(group-{fid})
    todo = set(faces); groups = []
    while todo:
        first = min(todo); todo.remove(first); stack = [first]; group = []
        while stack:
            fid = stack.pop(); group.append(fid)
            for other in sorted(neighbours[fid] & todo):
                todo.remove(other); stack.append(other)
        groups.append(sorted(group))
    return groups


def link_status(edges, boundary):
    degree = Counter(v for edge in edges for v in edge)
    unique = len({tuple(sorted(edge)) for edge in edges}) == len(edges)
    components = connected(degree, edges) if edges else 0
    shape = (sorted(degree.values()) == [1, 1]+[2]*(len(degree)-2)
             if boundary else bool(degree) and all(v == 2 for v in degree.values()))
    return dict(vertices=len(degree), edges=len(edges), components=components,
                unique_link_edges=unique, expected='path' if boundary else 'cycle',
                valid=bool(unique and components == 1 and shape))


def topology(faces):
    edges = incidence(faces)
    vertices = sorted({v for t in faces.values() for v in t})
    bad_edges = [list(e) for e, rows in sorted(edges.items()) if len(rows) not in (1, 2)]
    bad_orientation = [list(e) for e, rows in sorted(edges.items())
                       if len(rows) == 2 and sum(1 if a < b else -1 for _, a, b in rows)]
    boundary = sorted((a, b) for rows in edges.values() if len(rows) == 1 for _, a, b in rows)
    incoming, outgoing = Counter(b for a,b in boundary), Counter(a for a,b in boundary)
    boundary_valid = incoming == outgoing and all(n == 1 for n in incoming.values())
    loops = None
    if boundary_valid:
        todo = set(boundary); following = dict(boundary); loops = []
        while todo:
            a, b = min(todo); start = a; loop = [a]; todo.remove((a, b))
            while b != start:
                loop.append(b); a = b; b = following[a]; todo.remove((a, b))
            loops.append(loop)
    links = defaultdict(list)
    for t in faces.values():
        for i, v in enumerate(t):
            links[v].append((t[(i+1)%3], t[(i+2)%3]))
    boundary_vertices = set(incoming)|set(outgoing)
    failed_links = [v for v in vertices if not link_status(links[v], v in boundary_vertices)['valid']]
    groups = face_groups(faces)
    euler = len(vertices)-len(edges)+len(faces)
    manifold = not bad_edges and not bad_orientation and boundary_valid and not failed_links
    return dict(vertices=len(vertices), edges=len(edges), faces=len(faces), Euler=euler,
                edge_connected_components=len(groups), edge_incidence_histogram=dict(Counter(len(x) for x in edges.values())),
                nonmanifold_edges=bad_edges, inconsistent_internal_orientations=bad_orientation,
                boundary_is_disjoint_oriented_cycles=boundary_valid, oriented_boundary_cycles=loops,
                boundary_edges=[list(e) for e in boundary], boundary_vertices=sorted(boundary_vertices),
                vertex_link_failures=failed_links, local_oriented_manifold_with_boundary=manifold,
                is_abstract_disk=bool(manifold and len(groups)==1 and euler==1 and loops is not None and len(loops)==1))


def vertex_contacts(groups, faces):
    owners = defaultdict(set)
    for gid, group in enumerate(groups):
        for fid in group:
            for v in faces[fid]:
                owners[v].add(gid)
    return {str(v):sorted(ids) for v, ids in sorted(owners.items()) if len(ids)>1}
