"""Run a cube and one bounded study tet case in the pinned mesh-CFD image."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    os.umask(0o077)
    python = '/opt/venv/bin/python'
    admission = json.loads((root/'surface-verification.json').read_text())
    if not admission['accepted_for_volume_meshing'] or sha(root/'candidate.npz') != admission['candidate_npz_sha256']:
        raise SystemExit('Surface input admission failed')
    if sha(root/'mesh_solid.py') != '3cf167772ab4e4d90674693cb47e986e08c43e872db0b43c7529a533dc07dae6':
        raise SystemExit('Retained mesher hash mismatch')
    if any((root/name).exists() for name in ['cube', 'tet-1p5mm', 'cloud-mesh-execution.json', 'cloud-mesh-plan.json']):
        raise SystemExit('Existing cloud result refused')
    env = os.environ.copy()
    env['OPENBLAS_NUM_THREADS'] = '1'
    env['OMP_NUM_THREADS'] = '1'
    available = sorted(os.sched_getaffinity(0))
    threads = min(24, len(available))
    if threads < 12:
        raise SystemExit('Cloud CPU allocation below prepared minimum')
    probe = subprocess.run([python, '-c',
        'import json,sys,numpy,gmsh; gmsh.initialize(); print(json.dumps({"python":sys.version.split()[0],"numpy":numpy.__version__,"gmsh_api":gmsh.GMSH_API_VERSION,"gmsh_module":gmsh.__file__})); gmsh.finalize()'],
        env=env, capture_output=True, text=True, timeout=30, check=True)
    runtime = json.loads(probe.stdout)
    if runtime['gmsh_api'] != '4.12.1':
        raise SystemExit('Pinned image Gmsh API mismatch')
    plan = {'source_sha256': sha(__file__), 'candidate_sha256': sha(root/'candidate.npz'),
        'surface_verification_sha256': sha(root/'surface-verification.json'),
        'mesher_sha256': sha(root/'mesh_solid.py'), 'runtime': runtime,
        'threads': threads, 'child_address_space_gib': 24, 'interior_size_mm': 1.5,
        'algorithm': 10, 'head_deadline_seconds': 1800,
        'image': 'ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f',
        'physical_geometry_accepted': False, 'physics_admitted': False}
    (root/'cloud-mesh-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (root/'worker-pid.json').write_text(json.dumps({'pid': os.getpid(), 'started_epoch': time.time()})+'\n')

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (24*1024**3, 24*1024**3))
        os.sched_setaffinity(0, available[:threads])

    def case(source, name, deadline):
        argv = [python, str(root/'mesh_solid.py'), str(source), str(root/name),
                '--size', '1.5', '--algorithm', '10', '--threads', str(threads)]
        started = time.monotonic()
        timed_out = False
        with (root/(name+'.log')).open('x') as stream:
            process = subprocess.Popen(argv, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True, preexec_fn=limits)
            try:
                process.wait(timeout=deadline)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        result = {'argv': argv, 'exit_code': process.returncode, 'timeout': timed_out,
                  'seconds': time.monotonic()-started, 'log_sha256': sha(root/(name+'.log')),
                  'peak_children_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
        (root/(name+'-execution.json')).write_text(json.dumps(result, indent=2)+'\n')
        if process.returncode or timed_out:
            raise SystemExit('Bounded cloud meshing failed: '+name)
        return result

    case('cube', 'cube', 60)
    cube = json.loads((root/'cube/report.json').read_text())
    if cube['nonpositive_tetrahedra'] or abs(cube['signed_volume_mm3']-1) > 1e-12:
        raise SystemExit('Cloud cube control failed; head not launched')
    result = case(root/'candidate.npz', 'tet-1p5mm', 1800)
    result['cube_control_passed'] = True
    (root/'cloud-mesh-execution.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
