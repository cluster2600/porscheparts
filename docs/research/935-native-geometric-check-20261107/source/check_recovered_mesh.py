"""Complete one bounded native check of the exact previously recovered OpenFOAM mesh."""
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


def write(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2)+'\n')


def completed(result, text):
    return (not result['timeout'] and result['exit_code'] in (0, 1)
            and any(line.strip() == 'End' for line in text.splitlines()))


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root/'input-manifest.json').read_text())
    for row in manifest['files']:
        assert sha(root/row['path']) == row['sha256']
    assert manifest['field_solve_permitted'] is False
    assert manifest['native_check_seconds'] == 1200
    assert manifest['upstream_shape_quality_passed'] is False
    write(root/'worker-pid.json', {'pid': os.getpid(), 'epoch': time.time()})

    def stop(number, _frame):
        raise SystemExit(128+number)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (48*1024**3, 48*1024**3))

    def run(name, command, seconds):
        began = time.monotonic()
        timed_out = False
        with (root/(name+'.log')).open('x') as log:
            child = subprocess.Popen(['bash', '-c', command], cwd=root, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit)
            try:
                child.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        row = dict(exit_code=child.returncode, timeout=timed_out, seconds=time.monotonic()-began,
                   log_sha256=sha(root/(name+'.log')), owned_child_reaped=True)
        write(root/(name+'-execution.json'), row)
        return row

    setup = Path('/opt/openfoam13/etc/bashrc')
    assert sha(setup) == 'dd62f167ea8928a76cf76af72627b50bd62788df10bf13d8d4e4c4f9d0ee9541'
    prefix = 'source /opt/openfoam13/etc/bashrc >/dev/null 2>&1 || exit 91; '
    version = run('version', prefix+'foamVersion', 30)
    assert version['exit_code'] == 0 and 'OpenFOAM-13' in (root/'version.log').read_text()
    control = run('control-check', prefix+'checkMesh -case control', 60)
    assert control['exit_code'] == 0 and not control['timeout']
    assert 'Mesh OK.' in (root/'control-check.log').read_text()
    result = run('head-check', prefix+'checkMesh -case head', 1200)
    text = (root/'head-check.log').read_text()
    assert '12981388' in text and '30072005' in text and '4181299' in text
    for row in manifest['files']:
        assert sha(root/row['path']) == row['sha256'], 'A recovered input changed during inspection'
    passed = completed(result, text) and result['exit_code'] == 0 and 'Mesh OK.' in text
    return dict(source_sha256=sha(__file__), input_manifest_sha256=sha(root/'input-manifest.json'),
                terminal='native_geometric_check_finished', control_passed=True, native_head_check=result,
                native_head_check_completed=completed(result, text), native_head_check_passed=passed,
                input_files_unchanged=True, geometry_modified=False, field_solve_executed=False,
                upstream_shape_quality_passed=False, case_specific_operator_admission=False,
                physics_admitted=False, manufacturing_qualified=False, engine_qualified=False)


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    try:
        write(root/'terminal.json', main())
    except BaseException as error:
        write(root/'worker-error.json', {'exception_type': type(error).__name__,
                                       'field_solve_executed': False, 'physics_admitted': False})
        raise
