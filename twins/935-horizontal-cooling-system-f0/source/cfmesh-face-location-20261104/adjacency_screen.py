#!/usr/bin/env python3
"""Count flagged internal faces incident to rotor boundary-owner cells."""
import argparse
import json
import re
from pathlib import Path

from distance_screen import body, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('poly_mesh', type=Path)
    parser.add_argument('sets', nargs='+')
    args = parser.parse_args()
    p = args.poly_mesh
    matches = re.findall(r'rotor\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', (p / 'boundary').read_text(), re.S)
    if len(matches) != 1:
        raise ValueError('expected one rotor patch')
    count, start = map(int, matches[0])
    selected = {}
    for name in args.sets:
        if Path(name).name != name:
            raise ValueError('invalid set name')
        ids = [int(x) for x in body(p / 'sets' / name)]
        if len(ids) != len(set(ids)) or any(i < 0 or i >= start for i in ids):
            raise ValueError('expected unique internal face indices')
        selected[name] = ids
    wanted = set(i for ids in selected.values() for i in ids)
    owners = {}
    rotor_cells = set()
    owner_count = 0
    for i, line in enumerate(body(p / 'owner')):
        owner_count += 1
        if i in wanted or start <= i < start + count:
            value = int(line)
            if value < 0:
                raise ValueError('negative owner')
            if i in wanted:
                owners[i] = value
            if start <= i < start + count:
                rotor_cells.add(value)
    neighbours = {}
    neighbour_count = 0
    for i, line in enumerate(body(p / 'neighbour')):
        neighbour_count += 1
        if i in wanted:
            value = int(line)
            if value < 0:
                raise ValueError('internal face has negative neighbour')
            neighbours[i] = value
    if len(owners) != len(wanted) or len(neighbours) != len(wanted) or owner_count < start + count or not rotor_cells:
        raise ValueError('missing faces or empty rotor')
    output = {'boundary_sha256': digest(p / 'boundary'), 'owner_sha256': digest(p / 'owner'),
              'neighbour_sha256': digest(p / 'neighbour'), 'rotor_owner_cells': len(rotor_cells),
              'owner_list_count': owner_count, 'neighbour_list_count': neighbour_count, 'sets': {}}
    for name, ids in selected.items():
        owner_hit = sum(owners[i] in rotor_cells for i in ids)
        neighbour_hit = sum(neighbours[i] in rotor_cells for i in ids)
        both = sum(owners[i] in rotor_cells and neighbours[i] in rotor_cells for i in ids)
        output['sets'][name] = {'sha256': digest(p / 'sets' / name), 'count': len(ids),
            'owner_incident': owner_hit, 'neighbour_incident': neighbour_hit,
            'both_incident': both, 'either_incident': owner_hit + neighbour_hit - both}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
