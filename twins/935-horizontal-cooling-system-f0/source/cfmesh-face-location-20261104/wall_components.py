#!/usr/bin/env python3
"""Count edge-connected components of rotor faces incident to flagged cells."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from distance_screen import body, digest


def component_sizes(faces):
    parent = list(range(len(faces)))
    edge_owner = {}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, vertices in enumerate(faces):
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            edge = tuple(sorted((a, b)))
            if edge in edge_owner:
                parent[root(i)] = root(edge_owner[edge])
            else:
                edge_owner[edge] = i
    groups = defaultdict(int)
    for i in range(len(faces)):
        groups[root(i)] += 1
    return sorted(groups.values(), reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('poly_mesh', type=Path)
    parser.add_argument('face_set')
    args = parser.parse_args()
    p = args.poly_mesh
    if Path(args.face_set).name != args.face_set:
        raise ValueError('invalid set name')
    matches = re.findall(r'rotor\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', (p/'boundary').read_text(), re.S)
    if len(matches) != 1:
        raise ValueError('expected one rotor patch')
    count, start = map(int, matches[0])
    ids = list(map(int, body(p/'sets'/args.face_set)))
    if not ids or len(ids) != len(set(ids)) or any(i < 0 or i >= start for i in ids):
        raise ValueError('expected unique internal faces')
    wanted = set(ids)
    own, nei, rotor = {}, {}, []
    for i, value in enumerate(body(p/'owner')):
        if i in wanted: own[i] = int(value)
        if start <= i < start + count: rotor.append(int(value))
    for i, value in enumerate(body(p/'neighbour')):
        if i in wanted: nei[i] = int(value)
    if len(own) != len(wanted) or len(nei) != len(wanted) or len(rotor) != count or any(v < 0 for v in list(own.values()) + list(nei.values()) + rotor):
        raise ValueError('incomplete owner or neighbour lists')
    cells = set(own.values()) | set(nei.values())
    selected = {start+i for i, cell in enumerate(rotor) if cell in cells}
    faces = []
    for i, line in enumerate(body(p/'faces')):
        if i not in selected: continue
        match = re.fullmatch(r'(\d+)\(([^()]*)\)', line)
        if not match: raise ValueError('unsupported face format')
        vertices = [int(x) for x in match.group(2).split()]
        if len(vertices) != int(match.group(1)) or len(vertices) < 3 or len(set(vertices)) != len(vertices):
            raise ValueError('invalid face')
        faces.append(vertices)
    if len(faces) != len(selected): raise ValueError('missing selected face')
    sizes = component_sizes(faces)
    print(json.dumps({'set':args.face_set, 'flagged_faces':len(ids), 'wall_faces':len(faces),
        'components':len(sizes), 'largest_components':sizes[:20], 'singleton_components':sizes.count(1),
        'method':'shared whole edge among selected wall faces only',
        'hashes':{x:digest(p/x) for x in ('boundary','owner','neighbour','faces')},
        'face_set_sha256':digest(p/'sets'/args.face_set)},indent=2,sort_keys=True))

if __name__ == '__main__': main()
