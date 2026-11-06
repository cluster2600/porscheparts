"""Export and independently parse an unchanged open source surface as an OBJ reference."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    assert job['schema'] == '935-retained-source-obj-1'
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    with np.load(job['arrays'], allow_pickle=False) as source:
        original_vertices, original_faces = source['vertices'], source['triangles']
    with np.load(job['retained'], allow_pickle=False) as source:
        vertices, faces = source['vertices'], source['triangles']
        source_vertices, source_faces = source['source_vertex_ids'], source['source_face_ids']
    assert np.array_equal(vertices, original_vertices[source_vertices])
    assert np.array_equal(source_vertices[faces], original_faces[source_faces])
    output = args.output / 'retained-unclassified-source-reference.obj'
    with output.open('x') as stream:
        stream.write('# Open acquired-surface reference; unresolved anatomy; no clipping or caps.\n')
        stream.write('# Owner nominal units only; physical metrology and manufacturing unqualified.\n')
        stream.write('o RetainedUnclassifiedSourceReference\n')
        for p in vertices:
            stream.write('v ' + ' '.join(format(float(x), '.17g') for x in p) + '\n')
        for face in faces:
            stream.write('f ' + ' '.join(str(int(x)+1) for x in face) + '\n')
    before = sha(output)
    # A separate streaming parser rejoins actual stored values to ORIGINAL arrays.
    vertex_count = face_count = 0
    with output.open() as stream:
        for line in stream:
            fields = line.split()
            if not fields or fields[0].startswith('#') or fields[0] == 'o':
                continue
            assert len(fields) == 4
            if fields[0] == 'v':
                assert vertex_count < len(source_vertices)
                observed = np.array([float(x) for x in fields[1:]])
                assert np.array_equal(observed, original_vertices[source_vertices[vertex_count]])
                vertex_count += 1
            else:
                assert fields[0] == 'f' and face_count < len(source_faces)
                stored = [int(x)-1 for x in fields[1:]]
                assert all(0 <= i < len(source_vertices) for i in stored)
                assert np.array_equal(source_vertices[stored], original_faces[source_faces[face_count]])
                face_count += 1
    assert vertex_count == len(vertices) and face_count == len(faces)
    assert sha(output) == before
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
                  output_sha256=before, output_bytes=output.stat().st_size,
                  vertices=vertex_count, original_faces=face_count,
                  original_coordinates_and_ordered_triangles_exact=True,
                  original_index_mapping_in_bound_retained_NPZ=True,
                  source_points_or_triangles_clipped_or_capped=False,
                  open_unclassified_source_reference=True, full_bare_head_created=False,
                  physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('RETAINED_SOURCE_OBJ_EXACT_READBACK_OK', flush=True)


if __name__ == '__main__':
    main()
