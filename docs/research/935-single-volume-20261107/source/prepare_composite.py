"""Read the admitted 3MF exactly; retain supports without duplicating head arrays."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import xml.parsers.expat
import zipfile

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    admitted = json.loads(Path(job['composite_report']).read_text())
    assert admitted['all_resource_geometry_checks_passed'] and admitted['every_coordinate_and_index_roundtrip_exact']
    assert admitted['component_graph_readback_passed'] and admitted['one_connected_union_contact_graph']
    assert admitted['three_mf_sha256'] == sha(job['composite'])
    assert admitted['reference_head_input_sha256'] == sha(job['head'])
    expected = {r['id']:r for r in admitted['resources']}
    states, units, components, items = {}, [], [], []
    current = None
    def element(name, attr):
        nonlocal current
        if name == 'model':
            units.append(attr['unit'])
        elif name == 'object':
            current = int(attr['id'])
            assert current not in states
            states[current] = dict(vh=hashlib.sha256(), fh=hashlib.sha256(), nv=0, nf=0, vertices=[], faces=[])
        elif name == 'vertex':
            point = tuple(float(attr[k]) for k in ('x', 'y', 'z'))
            state = states[current]
            state['vh'].update(struct.pack('<ddd', *point))
            state['nv'] += 1
            if current != 1:
                state['vertices'].append(point)
        elif name == 'triangle':
            face = tuple(int(attr[k]) for k in ('v1', 'v2', 'v3'))
            state = states[current]
            state['fh'].update(struct.pack('<qqq', *face))
            state['nf'] += 1
            if current != 1:
                state['faces'].append(face)
        elif name == 'component':
            assert 'transform' not in attr
            components.append((current, int(attr['objectid'])))
        elif name == 'item':
            assert 'transform' not in attr
            items.append(int(attr['objectid']))
    reader = xml.parsers.expat.ParserCreate()
    reader.StartElementHandler = element
    with zipfile.ZipFile(job['composite']) as archive:
        assert archive.testzip() is None
        with archive.open('3D/3dmodel.model') as stream:
            for chunk in iter(lambda:stream.read(1048576), b''):
                reader.Parse(chunk, False)
            reader.Parse(b'', True)
    parent = len(expected)+1
    assert units == ['millimeter'] and items == [parent]
    assert components == [(parent, i) for i in range(1, parent)]
    assert set(states) == set(range(1, parent+1))
    vertices, faces, vo, fo = [], [], [0], [0]
    for i, row in sorted(expected.items()):
        state = states[i]
        assert state['nv'] == row['vertices'] and state['nf'] == row['triangles']
        assert state['vh'].hexdigest() == row['vertices_sha256']
        assert state['fh'].hexdigest() == row['triangles_sha256']
        if i != 1:
            v, f = np.asarray(state['vertices']), np.asarray(state['faces'], dtype=np.int64)
            assert np.isfinite(v).all() and f.min() >= 0 and f.max() < len(v)
            vertices.append(v)
            faces.append(f)
            vo.append(vo[-1]+len(v))
            fo.append(fo[-1]+len(f))
    with np.load(job['head'], allow_pickle=False) as head:
        assert hashlib.sha256(np.asarray(head['vertices'], dtype='<f8').tobytes()).hexdigest() == expected[1]['vertices_sha256']
        assert hashlib.sha256(np.asarray(head['triangles'], dtype='<i8').tobytes()).hexdigest() == expected[1]['triangles_sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    out = args.output/'supports.npz'
    np.savez_compressed(out, vertices=np.concatenate(vertices), triangles=np.concatenate(faces),
                        vertex_offsets=np.asarray(vo), face_offsets=np.asarray(fo),
                        resource_ids=np.arange(2, parent, dtype=np.int64))
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
                  head_sha256=sha(job['head']), composite_sha256=sha(job['composite']),
                  supports_sha256=sha(out), actual_mesh_resources=len(expected),
                  auxiliary_mesh_resources=len(vertices), every_resource_coordinate_and_index_verified=True,
                  assembly_and_units_verified=True, geometry_changed=False, manufacturing_qualified=False)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
