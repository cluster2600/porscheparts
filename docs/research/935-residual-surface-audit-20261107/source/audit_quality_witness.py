#!/usr/bin/env python3
"""Find and exactly certify a protected source-face quality witness, read-only."""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    spec = importlib.util.spec_from_file_location('residual_quality', job['quality_source'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    started = time.monotonic()
    tested = helper.controls()
    args.output.mkdir(mode=0o700, exist_ok=False)
    assert helper.sha(job['surface']) == 'aaaa18f894d609d4c265835d97f3d191cbfad40e7be32c69e5f83437dbafacf2'
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    tags = np.load(job['tags'], allow_pickle=False)
    assert tags.shape == (len(faces),) and tags.dtype.kind in 'iu'
    best, row = float('inf'), None
    # Ranking is approximate; acceptance uses the literal face and exact arithmetic.
    for start in range(0, len(faces), 50000):
        ids = np.flatnonzero(tags[start:start+50000] > 0)+start
        if not len(ids):
            continue
        p = vertices[faces[ids]]
        u, v = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
        n = np.cross(u, v)
        lengths = (u*u).sum(axis=1)+(v*v).sum(axis=1)+((u-v)**2).sum(axis=1)
        quality = 12*(n*n).sum(axis=1)/lengths**2
        assert np.isfinite(quality).all() and (quality >= 0).all()
        position = int(np.argmin(quality))
        if quality[position] < best:
            best, row = float(quality[position]), int(ids[position])
    assert row is not None and tags[row] > 0
    exact = helper.quality_squared(vertices[faces[row]])
    warning = Fraction.from_float(.01)**2
    report = dict(schema='935-source-quality-witness-1', source_sha256=helper.sha(__file__),
        job_sha256=helper.sha(args.job), controls=tested, input_surface_sha256=helper.sha(job['surface']),
        input_tags_sha256=helper.sha(job['tags']), source_surface_faces_scanned=len(faces),
        protected_face_tag=int(tags[row]), exact_witness_q_squared=[str(exact.numerator), str(exact.denominator)],
        witness_below_existing_warning=exact < warning, witness_row_not_public=True,
        global_minimum_proved=False, geometry_modified=False, candidate_exported=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    private = args.output/'private-witness.json'
    private.write_text(json.dumps({'row':row, 'vertices':faces[row].tolist()}, indent=2)+'\n')
    report['private_witness_sha256'] = helper.sha(private)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
