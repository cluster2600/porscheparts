#!/usr/bin/env python3
"""Classify OpenFOAM faceSet indices by the serialized boundary ranges."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('poly_mesh', type=Path)
    parser.add_argument('sets', nargs='+')
    args = parser.parse_args()
    boundary = args.poly_mesh / 'boundary'
    btext = boundary.read_text()
    patches = [(n, int(start), int(count)) for n, count, start in re.findall(
        r'(\w+)\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', btext, re.S)]
    if not patches or any(start != patches[i-1][1] + patches[i-1][2]
                          for i, (_, start, _) in enumerate(patches) if i):
        raise ValueError('missing or non-contiguous boundary ranges')
    first = patches[0][1]
    last = patches[-1][1] + patches[-1][2]
    result = {'boundary_sha256': digest(boundary), 'sets': {}}
    for name in args.sets:
        if Path(name).name != name:
            raise ValueError('set names must be basenames')
        path = args.poly_mesh / 'sets' / name
        match = re.search(r'(?:^|\n)\s*(\d+)\s*\(\s*([\s\d]*)\s*\)', path.read_text())
        if not match:
            raise ValueError('unsupported or invalid ASCII faceSet: ' + name)
        ids = [int(i) for i in match.group(2).split()]
        if len(ids) != int(match.group(1)) or len(set(ids)) != len(ids):
            raise ValueError('faceSet count or uniqueness mismatch: ' + name)
        counts = {'internal': sum(0 <= i < first for i in ids)}
        counts.update({n: sum(start <= i < start + count for i in ids)
                       for n, start, count in patches})
        if sum(counts.values()) != len(ids) or any(i >= last for i in ids):
            raise ValueError('out-of-range face index: ' + name)
        result['sets'][name] = {'sha256': digest(path), 'count': len(ids), 'locations': counts}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
