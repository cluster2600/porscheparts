"""Source-only fixed fixture preparation; root may run once into a fresh directory."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def surface(points, faces):
    return (b'962SURF1' + struct.pack('<QQ', len(points), len(faces))
            + b''.join(struct.pack('<ddd', *p) for p in points)
            + b''.join(struct.pack('<QQQ', *f) for f in faces))


def square(z, r=1):
    return [(-r, -r, z), (r, -r, z), (r, r, z), (-r, r, z)], [(0, 1, 2), (0, 2, 3)]


def combined(a, b):
    pa, fa = a
    pb, fb = b
    return pa + pb, fa + [tuple(len(pa) + x for x in f) for f in fb]


def prepare(out):
    if out.exists() or out.is_symlink():
        raise ValueError('Fresh literal output required')
    out.mkdir()
    p = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
         (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    # All cube triangles are outward; walls omit both horizontal caps.
    bottom = [(0,2,1),(0,3,2)]
    top = [(4,5,6),(4,6,7)]
    walls = [(0,1,5),(0,5,4),(1,2,6),(1,6,5),
             (2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    models = {
        'cube': (p, bottom + top + walls),
        'walls': (p, walls),
        'interior-square': square(0),
        'near-top-open': square(31/32, 1/2),
        'plane': square(2**-17, 1/2),
        'two-open-components': combined(square(1/32, 1/2), square(3/64, 1/2)),
        'asymmetric-union': combined(square(0, 1/2), square(1/32, 1/2)),
    }
    for name, (points, faces) in models.items():
        (out / (name + '.bin')).write_bytes(surface(points, faces))
        (out / (name + '.u64')).write_bytes(struct.pack('<' + 'Q' * len(faces), *range(len(faces))))
    (out/'malformed.bin').write_bytes(surface([(0,0,0),(1,0,0),(0,1,0)], [(0,1,3)]))
    (out/'empty.bin').write_bytes(surface([], []))
    (out/'one.u64').write_bytes(struct.pack('<Q', 0))
    cases = [
        ('open-to-closed', 'near-top-open', 'cube', 'near-top-open', 1/32),
        ('coincident-zero', 'plane', 'plane', 'plane', 0),
        ('component-union-max', 'two-open-components', 'plane', 'two-open-components', 3/64-2**-17),
        ('asymmetric-forward', 'plane', 'asymmetric-union', 'plane', 2**-17),
        ('asymmetric-reverse', 'asymmetric-union', 'plane', 'asymmetric-union', 1/32-2**-17),
        ('continuous-interior-max', 'interior-square', 'walls', 'interior-square', 1),
    ]
    expected = {'schema': '962-CGAL-directed-distance-literals/v1', 'cases': [
        {'id': name, 'source': a+'.bin', 'target': b+'.bin', 'source_ids': ids+'.u64',
         'returncode': 0, 'exact_directed_distance_mm': h,
         'required': 'completed closed interval contains exact h; unchanged mesh snapshots; all target faces',
         'polygon_budget_passed_expected': h < 0.0625}
        for name, a, b, ids, h in cases],
        'refusals': [{'id': x, 'source': x+'.bin', 'target': 'cube.bin',
                      'source_ids': 'one.u64', 'returncode': 2,
                      'query_completed': False, 'scalar_mm': None} for x in ('malformed','empty')],
        'analytic_notes': [
            'Near-top square lies inside the cube; top distance exactly1/32 is uniformly smallest.',
            'Target plane z=2**-17 gives exact union distance3/64-2**-17.',
            'Plane z=2**-17 to union z0,z1/32 is2**-17, strictly belowepsilon; reverse1/32-2**-17.',
            'Square boundary/vertices lie on four walls; center distance1 and every square point distance<=1.',
            'Fixtures prove software continuous-facet and directed behavior only; no head admission.']}
    (out/'expectations.json').write_text(json.dumps(expected, indent=2)+'\n')
    records = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(out.iterdir())}
    (out/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: prepare_literals.py fresh-output-directory')
    prepare(Path(sys.argv[1]))
