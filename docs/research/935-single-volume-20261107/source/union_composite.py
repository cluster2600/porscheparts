"""Bounded offline Mesh64 import and one Boolean union of the admitted composite."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import manifold3d as m
import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exact_roundtrip(vertices, faces, result):
    mesh = result.to_mesh64()
    out_v, out_f, ids = np.asarray(mesh.vert_properties), np.asarray(mesh.tri_verts), np.asarray(mesh.face_id)
    assert len(out_f) == len(faces) and np.array_equal(np.sort(ids), np.arange(len(faces)))
    for start in range(0, len(faces), 50000):
        actual = out_v[out_f[start:start+50000], :3]
        expected = vertices[faces[ids[start:start+50000]]]
        same = np.zeros(len(actual), dtype=bool)
        for shift in range(3):
            same |= np.all(actual == np.roll(expected, shift, axis=1), axis=(1, 2))
        assert same.all(), 'Mesh64 import changed a source triangle'


def make(vertices, faces, original):
    mesh = m.Mesh64(np.require(vertices, dtype=np.float64, requirements=['C', 'W']),
                    np.require(faces, dtype=np.uint64, requirements=['C', 'W']),
                    run_index=np.array([0, len(faces)*3], dtype=np.uint64),
                    run_original_id=np.array([original], dtype=np.uint32),
                    face_id=np.arange(len(faces), dtype=np.uint64), tolerance=0)
    result = m.Manifold(mesh)
    assert result.status() == m.Error.NoError and result.num_tri() > 0 and result.volume() > 0
    return result


def controls():
    first = m.Manifold.cube((1., 1., 1.))
    cube = first.to_mesh64()
    v, f = np.asarray(cube.vert_properties), np.asarray(cube.tri_verts)
    identity = make(v, f, m.Manifold.reserve_ids(1))
    exact_roundtrip(v, f, identity)
    joined = m.Manifold.batch_boolean([first, first.translate((.5, 0., 0.))], m.OpType.Add)
    assert joined.status() == m.Error.NoError and abs(joined.volume()-1.5) < 1e-12
    assert len(joined.decompose()) == 1
    separate = m.Manifold.batch_boolean([first, first.translate((2., 0., 0.))], m.OpType.Add)
    assert separate.volume() == 2 and len(separate.decompose()) == 2
    thin = v*np.array([2**-20, 1., 1.])+np.array([100., 0., 0.])
    assert len(np.unique(thin.astype(np.float32), axis=0)) < len(thin)
    exact = make(thin, f, m.Manifold.reserve_ids(1))
    exact_roundtrip(thin, f, exact)
    # The scalar volume sum loses translation precision; triangle coordinates stay exact.
    assert abs(exact.volume()-2**-20) < np.spacing(100.)
    return dict(analytic_overlap_union=True, disjoint_components_preserved=True,
                exact_source_triangle_roundtrip=True, float64_thin_box_preserved=True,
                float32_thin_box_collapse_demonstrated=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    assert importlib.metadata.version('manifold3d') == '3.5.4'
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    checks = controls()
    (args.output/'controls.json').write_text(json.dumps(checks, indent=2)+'\n')
    head = dict(np.load(job['head'], allow_pickle=False))
    supports = dict(np.load(job['supports'], allow_pickle=False))
    ids = supports['resource_ids']
    start_id = m.Manifold.reserve_ids(len(ids)+1)
    print('Importing exact head triangles through Mesh64', flush=True)
    body = make(head['vertices'], head['triangles'], start_id)
    exact_roundtrip(head['vertices'], head['triangles'], body)
    (args.output/'head-admission.json').write_text(json.dumps(dict(
        original_triangles=len(head['triangles']), exact_coordinate_triangle_and_winding_roundtrip=True,
        seconds=time.monotonic()-began), indent=2)+'\n')
    del head
    parts = []
    for index, resource in enumerate(ids):
        a, b = supports['vertex_offsets'][index:index+2]
        c, d = supports['face_offsets'][index:index+2]
        v, f = supports['vertices'][a:b], supports['triangles'][c:d]
        part = make(v, f, start_id+int(resource)-1)
        exact_roundtrip(v, f, part)
        parts.append(part)
    print('Unioning the support, plate and coupon resources', flush=True)
    auxiliary = m.Manifold.batch_boolean(parts, m.OpType.Add)
    assert auxiliary.status() == m.Error.NoError
    print('Unioning the head with the complete auxiliary assembly', flush=True)
    result = m.Manifold.batch_boolean([body, auxiliary], m.OpType.Add)
    assert result.status() == m.Error.NoError and result.volume() > 0
    mesh = result.to_mesh64()
    v, f = np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts, dtype=np.int64)
    runs = np.asarray(mesh.run_index)
    origins = np.repeat(np.asarray(mesh.run_original_id, dtype=np.int64)-start_id+1, np.diff(runs)//3)
    assert len(origins) == len(f) and np.all((origins >= 1) & (origins <= len(ids)+1))
    path = args.output/'candidate.npz'
    np.savez_compressed(path, vertices=v, triangles=f, source_resource_ids=origins,
                        source_triangle_ids=np.asarray(mesh.face_id, dtype=np.int64))
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), candidate_sha256=sha(path),
                  manifold_version=importlib.metadata.version('manifold3d'), mesh64_only=True,
                  source_resources=len(ids)+1, vertices=len(v), triangles=len(f),
                  native_components=len(result.decompose()), native_volume_mm3=result.volume(),
                  controls=checks, every_input_triangle_roundtrip_verified=True,
                  independent_export_geometry_provenance_and_layer_checks_pending=True,
                  manufacturing_qualified=False, engine_qualified=False, seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
