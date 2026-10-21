"""Plot recorded cap classifications; no quality or geometry acceptance query."""
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
candidate = ROOT / 'work/962-engineering/atomic-cavity-plane-clip-exact-head-001/head-plane0/candidate.bin'
reference = ROOT / 'work/962-engineering/atomic-cavity-plane-clip-repair-reference-001/readback-report.json'
pins = {candidate: 'd2af68ee8ab242e992b15b6e2a93ac7e487972277af7f31a8496a7036ec32240',
        reference: 'ebf9dd540d32ff6dd2d47267a94d8500b498b30e783288a91eba5c556d21b108'}
sha = lambda data: hashlib.sha256(data).hexdigest()
for path, expected in pins.items():
    assert sha(path.read_bytes()) == expected
for name in ('cap-reference.png', 'cap-reference.svg', 'plot-receipt.json'):
    assert not (HERE / name).exists()
cap = json.loads(reference.read_text())['cap']['components'][0]
ids = cap['topology']['boundary_vertices']
loops = cap['topology']['oriented_boundary_cycles']
poor = set(cap['poor_face_ids'])
assert len(set(ids)) == 3508 and [len(x) for x in loops] == [1482, 2026]
assert len(poor) == 2396 and len(cap['face_ids']) == 3508
points = {}; faces = []
with candidate.open('rb') as stream:
    assert stream.read(8) == b'962SURF1'
    nv, nf = struct.unpack('<QQ', stream.read(16))
    assert (nv, nf) == (869355, 1739126)
    for vertex in ids:
        stream.seek(24 + 24 * vertex)
        x, y, z = struct.unpack('<ddd', stream.read(24))
        assert z == 0.0
        points[vertex] = (x, y)
    for fid in cap['face_ids']:
        stream.seek(24 + 24 * nv + 24 * fid)
        row = struct.unpack('<QQQ', stream.read(24))
        assert len(set(row)) == 3 and all(v in points for v in row)
        faces.append((fid, [points[v] for v in row]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
matplotlib.rcParams['svg.hashsalt'] = '962-clipped-cap-d2af'
fig, ax = plt.subplots(figsize=(10, 11))
fig.subplots_adjust(bottom=0.20, top=0.90)
for selected, color in ((False, '#dde3e8'), (True, '#dc5a52')):
    polygons = [p for fid, p in faces if (fid in poor) == selected]
    ax.add_collection(PolyCollection(polygons, facecolors=color, edgecolors='#5d6570', linewidths=0.15))
for cycle, color in zip(loops, ('#087ca7', '#a45c00')):
    rows = [points[v] for v in cycle + [cycle[0]]]
    ax.plot([p[0] for p in rows], [p[1] for p in rows], color=color, linewidth=1.2)
ax.autoscale_view(); ax.margins(0.07); ax.set_aspect('equal')
ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
ax.set_title('962 C bionic study: rejected clipped-cap reference\n'
             'XY projection of the assumed z = 0 finishing plane')
ax.legend(handles=[Patch(color='#dc5a52', label='2,396 recorded poor cap triangles (q < 2/29)'),
                   Patch(color='#dde3e8', label='1,112 other cap triangles'),
                   Patch(color='#087ca7', label='Boundary cycle 0: 1,482 vertices'),
                   Patch(color='#a45c00', label='Boundary cycle 1: 2,026 vertices')],
          loc='upper center', bbox_to_anchor=(0.5, -0.08), fontsize=9)
fig.text(0.5, 0.01, 'Exact source coordinates; recorded classifications only. No OEM, strength or printability approval.',
         ha='center', fontsize=8)
fig.savefig(HERE / 'cap-reference.png', dpi=160)
fig.savefig(HERE / 'cap-reference.svg', metadata={'Date': None})
plt.close(fig)
raw = (HERE / 'cap-reference.png').read_bytes()
assert raw[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', raw[16:24]) == (1600, 1760)
ET.parse(HERE / 'cap-reference.svg')
for path, expected in pins.items():
    assert sha(path.read_bytes()) == expected
outputs = {n: {'bytes': (HERE/n).stat().st_size, 'sha256': sha((HERE/n).read_bytes())}
           for n in ('cap-reference.png', 'cap-reference.svg')}
receipt = {'status': 'recorded_cap_projection_only_not_physics', 'input_sha256':
           {str(p.relative_to(ROOT)): h for p, h in pins.items()}, 'source_sha256': sha(Path(__file__).read_bytes()),
           'matplotlib': matplotlib.__version__, 'selected_point_rows': 3508, 'selected_face_rows': 3508,
           'quality_recomputed': False, 'coordinates_or_geometry_modified': False,
           'all_bound_inputs_unchanged': True, 'outputs': outputs, 'manufacturing_authorized': False}
(HERE/'plot-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
