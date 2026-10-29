"""Replay the frozen powder-port geometry experiment in a fresh staging directory.

This reconstructs and checks the digital geometry. It does not run the pending
complete-carrier mechanics, GPU query workload or internal powder-clearance study.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = ROOT / 'docs/reports/carrier-interface-20261028/evidence/powder-ports-001'
IMAGE = 'sha256:7ed241be10194d98e4ae750cb7f983b0d501742f1ac651580b86c165cba39537'
VERSIONS = {'numpy': '2.4.6', 'scipy': '1.17.1', 'libigl': '2.6.3',
            'manifold3d': '3.5.4', 'matplotlib': '3.11.2'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_transport(path, archive):
    data = np.load(archive)
    vertices, faces = data['vertices'], data['triangles']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as stream:
        stream.write(f'{len(vertices)} {len(faces)}\n')
        np.savetxt(stream, vertices, fmt='%.17g')
        np.savetxt(stream, faces, fmt='%d')
    with path.open() as stream:
        nv, nf = map(int, stream.readline().split())
        recovered_vertices = np.loadtxt(stream, max_rows=nv)
        recovered_faces = np.loadtxt(stream, dtype=np.uint64)
    assert nf == len(faces)
    assert np.array_equal(vertices, recovered_vertices)
    assert np.array_equal(faces, recovered_faces)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('A fresh output directory is required')
    assert sys.version_info[:2] == (3, 11), 'Use the pinned Python 3.11 runtime'
    observed = {package: version(package) for package in VERSIONS}
    assert observed == VERSIONS, f'Runtime differs from frozen profile: {observed}'
    subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', IMAGE],
                   check=True, capture_output=True, text=True)
    manifest = json.loads((EVIDENCE / 'publication-manifest.json').read_text())
    for entry in manifest['files']:
        assert sha(EVIDENCE / entry['file']) == entry['sha256']
    for entry in manifest['external_inputs']:
        assert sha(EVIDENCE / entry['file']) == entry['sha256']
    helper = Path(__file__).with_name('reconstruct_core_envelopes.py')
    assert sha(helper) == sha(EVIDENCE / 'sources/reconstruct_core_envelopes.py')
    started = time.monotonic()
    output = args.output.resolve()
    output.mkdir(parents=True)
    (output / 'parts').symlink_to(ROOT / 'parts', target_is_directory=True)
    work = output / 'work/carrier-interface-20261028'
    work.parent.mkdir()
    shutil.copytree(EVIDENCE / 'sources', work)
    reference = work / 'full-reconstructed-p10-001/candidate.npz'
    reference.parent.mkdir()
    shutil.copyfile(EVIDENCE / '../reconstructed-carrier-001/candidate.npz', reference)
    for rank in range(4):
        target = work / f'meshlib-seed-p10-r{rank}-h0125-004'
        target.mkdir()
        for sign in ('positive', 'negative'):
            shutil.copyfile(EVIDENCE / f'inputs/networks/rank-{rank}/{sign}.npz',
                            target / f'{sign}.npz')
    stages = []

    def execute(script, *arguments, raw_intermediate=False):
        log = output / f'stage-{len(stages):02d}.log'
        with log.open('w') as stream:
            result = subprocess.run([sys.executable, str(work / script), *arguments],
                                    cwd=output, stdout=stream, stderr=stream)
        stage = {'script': script, 'returncode': result.returncode,
                 'log': log.name}
        stages.append(stage)
        if raw_intermediate and result.returncode:
            raw = json.loads((work / 'ported-carrier-001/assessment.json').read_text())
            # Retain the raw refusal; the next stage repairs it and must pass.
            assert result.returncode == 1
            assert raw['status'] == 'ported_geometry_native_checks_refused'
            assert not raw['no_added_material']
            assert raw['positive_material_shells'] == 1
            assert raw['negative_closed_void_shells'] == 0
            assert raw['final_oriented_triangle_roundtrip_exact']
            assert all(r['oriented_triangle_roster_exact'] for r in raw['protected'])
            assert raw['nominal_mass_kg'] <= 1.30
            stage['expected_raw_refusal_retained'] = True
        elif result.returncode:
            raise RuntimeError(f'{script} failed; see {log}')

    execute('plan_powder_ports_003.py')
    execute('build_powder_ports_001.py', raw_intermediate=True)
    execute('inspect_port_residue_001.py')
    execute('reseat_port_seams_002.py')
    execute('encode_port_checks_002.py')
    write_transport(work / 'cgal-self-inputs-001/reconstructed10.mesh64', reference)
    for worker, compiled in [('cgal-self-check-002', 'cgal-self-compile-002'),
                             ('cgal-port-gap-worker-002', 'cgal-port-gap-compile-002'),
                             ('cgal-port-control-worker-001', 'cgal-port-control-compile-001')]:
        execute(f'{worker}/run_check.py', '--compile', '--output', str(work / compiled))
    execute('check_reseated_embedding_002.py')
    execute('run_port_gap_checks_001.py')
    execute('cgal-port-control-worker-001/run_check.py',
            '--input-directory', str(work / 'cgal-port-inputs-001'),
            '--binary', str(work / 'cgal-port-control-compile-001/output/check-hausdorff'),
            '--output', str(work / 'cgal-port-controls-001'))
    execute('qualify_powder_ports_001.py')
    execute('render_powder_ports_001.py')
    sys.path.insert(0, str(helper.parent))
    from reconstruct_core_envelopes import canonical_surface
    actual = np.load(work / 'ported-seams-002/candidate.npz')
    expected = np.load(EVIDENCE / 'candidate.npz')
    same = all(np.array_equal(a, b) for a, b in zip(
        canonical_surface(actual['vertices'], actual['triangles']),
        canonical_surface(expected['vertices'], expected['triangles'])))
    assert same, 'Replayed geometry differs from the published oriented triangles'
    report = {'status': 'frozen_powder_port_geometry_replay_passed',
              'oriented_geometry_matches_published_candidate': same,
              'runtime': observed, 'stages': stages,
              'elapsed_seconds': time.monotonic() - started,
              'complete_carrier_mechanics_converged': False,
              'gpu_queries_qualified_for_this_geometry': False,
              'powder_drainability_demonstrated': False,
              'manufacturing_authorized': False}
    (output / 'replay-assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
