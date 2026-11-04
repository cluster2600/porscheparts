"""Bounded native Linux cube control and one admitted study-surface tet trial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS, (7*1024**3, 7*1024**3))
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[:2])


def run_case(python, mesher, source, output, env, log, deadline):
    argv = [str(python), str(mesher), str(source), str(output), '--size', '1.5', '--algorithm', '10', '--threads', '2']
    started = time.monotonic()
    timeout = False
    with log.open('x') as stream:
        process = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True, preexec_fn=child_limits)
        try:
            process.wait(timeout=deadline)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    return {'argv': argv, 'exit_code': process.returncode, 'timeout': timeout,
            'seconds': time.monotonic()-started, 'log_sha256': sha(log),
            'peak_children_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--site-packages', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root
    python = root/'runtime/bin/python'
    mesher = root/'mesh_solid.py'
    source = root/'candidate.npz'
    verification = root/'surface-verification.json'
    checks = json.loads(verification.read_text())
    if not checks['accepted_for_volume_meshing'] or sha(source) != checks['candidate_npz_sha256']:
        raise SystemExit('Independent surface admission missing or input mismatch')
    if sha(mesher) != '3cf167772ab4e4d90674693cb47e986e08c43e872db0b43c7529a533dc07dae6':
        raise SystemExit('Retained mesher source mismatch')
    for name in ('cube', 'tet-1p5mm', 'cube.log', 'head.log', 'mesh-execution.json'):
        if (root/name).exists():
            raise SystemExit('Existing mesh output refused: '+name)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(args.site_packages)
    env['OPENBLAS_NUM_THREADS'] = '1'
    env['OMP_NUM_THREADS'] = '1'
    metadata = subprocess.run([str(python), '-c',
        'import sys,json,gmsh,numpy; gmsh.initialize(); print(json.dumps({"python":sys.version.split()[0],"gmsh":gmsh.__version__,"numpy":numpy.__version__,"gmsh_module":gmsh.__file__})); gmsh.finalize()'],
        env=env, capture_output=True, text=True, timeout=30, check=True)
    runtime = json.loads(metadata.stdout)
    if runtime['gmsh'] != '4.12.1':
        raise SystemExit('Unexpected Gmsh API version')
    save(root/'mesh-plan.json', {'source_sha256': sha(__file__), 'candidate_sha256': sha(source),
        'surface_verification_sha256': sha(verification), 'mesher_sha256': sha(mesher),
        'runtime': runtime, 'interior_size_mm': 1.5, 'threads': 2,
        'child_address_space_gib': 7, 'cube_deadline_seconds': 60,
        'head_deadline_seconds': 900, 'physical_geometry_accepted': False,
        'scope': 'Single local study-mesh comparison; no solver, manufacturing or physical release'})
    cube = run_case(python, mesher, 'cube', root/'cube', env, root/'cube.log', 60)
    save(root/'cube-execution.json', cube)
    if cube['exit_code'] or cube['timeout']:
        raise SystemExit('Cube control execution failed; head not launched')
    report = json.loads((root/'cube/report.json').read_text())
    cube_accepted = (report['nonpositive_tetrahedra'] == 0 and abs(report['signed_volume_mm3']-1) < 1e-12
                     and report['tetrahedra'] > 0 and report['quality_minSICN_quantiles'][0] > 0)
    if not cube_accepted:
        raise SystemExit('Cube control rejected; head not launched')
    result = run_case(python, mesher, source, root/'tet-1p5mm', env, root/'head.log', 900)
    result['cube_control_accepted'] = True
    result['runtime_plan_sha256'] = sha(root/'mesh-plan.json')
    save(root/'mesh-execution.json', result)
    print(json.dumps(result), flush=True)
    if result['exit_code'] or result['timeout']:
        raise SystemExit('Bounded head meshing failed; no mesh accepted')


if __name__ == '__main__':
    main()
