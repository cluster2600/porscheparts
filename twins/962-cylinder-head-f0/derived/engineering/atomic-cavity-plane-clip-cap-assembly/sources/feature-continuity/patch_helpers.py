"""Exact retained topology functions; no legacy audit entrypoint."""
from collections import Counter, defaultdict
import numpy as np


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


def patch_groups(faces):
    incidence = defaultdict(list)
    for i, row in enumerate(faces):
        for a, b in zip(row, np.roll(row, -1)):
            incidence[tuple(sorted((int(a), int(b))))].append(i)
    neighbours = [set() for _ in faces]
    for incident in incidence.values():
        for i in incident:
            neighbours[i].update(set(incident) - {i})
    unseen = set(range(len(faces))); groups = []
    while unseen:
        first = min(unseen); unseen.remove(first); pending = [first]; group = []
        while pending:
            i = pending.pop(); group.append(i)
            for j in neighbours[i] & unseen:
                unseen.remove(j); pending.append(j)
        groups.append(np.array(sorted(group), dtype=np.int64))
    return groups


def patch_topology(faces):
    directed = [(int(a), int(b)) for row in faces for a, b in zip(row, np.roll(row, -1))]
    counts = Counter(tuple(sorted(edge)) for edge in directed)
    balance = Counter()
    for a, b in directed:
        balance[tuple(sorted((a, b)))] += 1 if a < b else -1
    if any(n not in (1, 2) for n in counts.values()) or any(counts[e] == 2 and v for e, v in balance.items()):
        raise ValueError("Patch edge manifold/orientation failure")
    boundary = sorted(edge for edge in directed if counts[tuple(sorted(edge))] == 1)
    incoming, outgoing = Counter(b for a, b in boundary), Counter(a for a, b in boundary)
    if incoming != outgoing or any(n != 1 for n in incoming.values()):
        raise ValueError("Patch boundary must consist of disjoint oriented loops")
    vertices = sorted(set(int(v) for v in faces.flat)); boundary_vertices = set(incoming)
    links = defaultdict(list)
    for row in faces:
        for i, v in enumerate(row):
            links[int(v)].append((int(row[(i+1) % 3]), int(row[(i+2) % 3])))
    for v, edges in links.items():
        degrees = Counter(x for e in edges for x in e)
        expected = sorted([1, 1] + [2]*(len(degrees)-2)) if v in boundary_vertices else [2]*len(degrees)
        if connected(degrees, edges) != 1 or sorted(degrees.values()) != expected:
            raise ValueError("Patch vertex link is not a boundary path or interior cycle")
    result = dict(vertices=len(vertices), edges=len(counts), faces=len(faces),
        euler_characteristic=len(vertices)-len(counts)+len(faces),
        components=len(patch_groups(faces)), boundary_loops=connected(boundary_vertices, boundary) if boundary else 0,
        boundary_vertices=len(boundary_vertices), boundary_edges=len(boundary), vertex_link_manifold=True)
    if result["components"] != 1:
        raise ValueError("A patch must remain connected")
    return result, np.asarray(boundary, dtype=np.int64).reshape(-1, 2)
