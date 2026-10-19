"""Execute one bounded cold native case through its declared profile, then seal it.

The runtime JSON contains explicit nonsecret SSH/runtime paths. No legacy case
or geometry is silently substituted. Every output directory must be fresh.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import time
import uuid

from native_case_contract import PROFILES, runtime_config, selected_inputs, sha, write, validate_terminal

SOURCE = Path(__file__).resolve().parent
STOP = False
FILES = {
    'process-skins-20261016': [
        'run_native_envelope_case.py', 'native_case_remote.py', 'native_case_contract.py',
        'left-repair-template-v2.json', 'repair_ancestral_line_sheet.py',
        'native_prism_case.py', 'seal_prism_native_case.py',
        'audit_envelope_case.py', 'audit_exact_volume.py'],
    'design-20261016': ['classify_mesh_contacts.py'],
    'native-cgal-mesh-remeasure-20261016': ['run.py', 'worker.py', 'audit_composed_repair.py'],
    'native-cgal-prism-free-20261016-v4': ['audit_composed_drift_initial.py', 'prism-face-schema.json'],
}


def request_stop(*_):
    global STOP
    STOP = True


def run(inputs_path, output, source_index, runtime_path):
    start = time.monotonic()
    inputs_path, output, runtime_path = map(lambda p: Path(p).resolve(), (inputs_path, output, runtime_path))
    runtime = runtime_config(runtime_path)
    manifest, _, files = selected_inputs(inputs_path, source_index)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'source'; snapshot.mkdir()
    frozen = {str(inputs_path):sha(inputs_path), str(runtime_path):sha(runtime_path)}
    sources = {}
    for directory, names in FILES.items():
        (snapshot/directory).mkdir()
        for name in names:
            path = SOURCE.parent/directory/name; relative = directory+'/'+name
            if path.is_symlink():
                raise ValueError('Source symlinks are forbidden')
            digest = sha(path); frozen[str(path)] = digest
            shutil.copy2(path, snapshot/relative)
            if sha(snapshot/relative) != digest:
                raise ValueError('Source changed while snapshotting')
            frozen[str(snapshot/relative)] = digest; sources[relative] = digest
    (output/'inputs').mkdir()
    for role, row in files.items():
        original = Path(row['path']); frozen[str(original)] = row['sha256']
        destination = output/'inputs'/original.name
        shutil.copy2(original, destination)
        if sha(destination) != row['sha256']:
            raise ValueError('Input changed while copying')
        frozen[str(destination)] = row['sha256']
    shutil.copy2(runtime_path, output/'runtime.json')
    shutil.copy2(inputs_path, output/'input-manifest.json')
    frozen[str(output/'runtime.json')] = sha(runtime_path)
    frozen[str(output/'input-manifest.json')] = sha(inputs_path)
    plan = dict(schema='native-envelope-one-case-plan-v2', source_index=source_index,
        profile=PROFILES[source_index], input_manifest_sha256=sha(inputs_path),
        input_carrier_sha256=manifest['input_sha256'],
        inputs={role:dict(name=Path(row['path']).name,sha256=row['sha256']) for role,row in files.items()},
        sources_sha256=sources,
        bounds=dict(cpu=2,memory='4G',swap=0,network='none',controller_seconds=3200),
        no_precomputed_geometry_reused=True)
    write(output/'plan.json', plan); frozen[str(output/'plan.json')] = sha(output/'plan.json')
    remote = runtime['remote_parent'].rstrip('/')+'/native-case-'+uuid.uuid4().hex[:16]
    state = dict(schema='native-envelope-one-case-frontend-v2', status='starting', source_index=source_index,
        remote_job=remote, runtime_sha256=sha(runtime_path), source_and_input_sha256=frozen)
    write(output/'execution-receipt.json', state)
    def verify():
        if any(sha(path) != expected for path,expected in frozen.items()):
            raise ValueError('Frontend source, runtime, plan or input changed')
    def ssh(arguments, **kwargs):
        return subprocess.run(['ssh','-o','BatchMode=yes',runtime['host'],shlex.join([str(x) for x in arguments])],
                              check=True, timeout=60, **kwargs)
    child = None; created = False
    try:
        if STOP or time.monotonic()-start > 3200:
            raise InterruptedError('Stopped before remote preparation')
        ssh(['mkdir', remote], capture_output=True); created = True
        for name in ['source', 'inputs', 'runtime.json', 'plan.json']:
            if STOP or time.monotonic()-start > 3200:
                raise InterruptedError('Stopped during remote upload preparation')
            subprocess.run(['scp','-q','-r',str(output/name),runtime['host']+':'+shlex.quote(remote+'/')],
                           check=True, timeout=90)
        verify()
        if STOP or time.monotonic()-start > 3200:
            raise InterruptedError('Stopped before launching the remote controller')
        command = [runtime['audit_python'], '-B', remote+'/source/process-skins-20261016/native_case_remote.py', remote]
        state.update(status='running', command=command); write(output/'execution-receipt.json', state)
        with (output/'remote-controller.log').open('w') as log:
            child = subprocess.Popen(['ssh','-o','BatchMode=yes',runtime['host'],shlex.join(command)],
                                     stdout=log,stderr=subprocess.STDOUT)
            requested = False; stop_start = None
            while child.poll() is None:
                if (STOP or time.monotonic()-start > 3200) and not requested:
                    # One exact owned cancellation file; remote controller stops
                    # only units named in the fresh jobs it created.
                    ssh([runtime['python'], '-c',
                         'from pathlib import Path;Path('+repr(remote+'/cancel.request')+').touch(exist_ok=False)'],
                        capture_output=True)
                    requested = True; stop_start = time.monotonic()
                if requested and time.monotonic()-stop_start > 200:
                    raise InterruptedError('Remote cleanup has not completed; owned remote receipts must be inspected')
                time.sleep(.25)
        if child.returncode != 0:
            raise ValueError('Native case refused; retained remote output contains exact reason')
        verify()
        state['status'] = 'collecting'
    except BaseException as error:
        state.update(status='rejected_or_incomplete',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        # Retain failed output as well. No job directory or old evidence is deleted.
        try:
            if created:
                copied = subprocess.run(['scp','-q','-r',runtime['host']+':'+shlex.quote(remote+'/output'),str(output/'result')],
                                        capture_output=True,timeout=90)
                state['remote_output_collected'] = copied.returncode == 0
        except BaseException as error:
            state.update(status='rejected_or_incomplete',collection_error_type=type(error).__name__,collection_error=str(error))
            raise
        finally:
            state.update(seconds=time.monotonic()-start,
                identities_unchanged=all(sha(path)==expected for path,expected in frozen.items()))
            write(output/'execution-receipt.json', state)
    verify()
    remote_terminal = output/'result/case.json'
    terminal = json.loads(remote_terminal.read_text())
    validate_terminal(terminal,plan,sha(runtime_path),output/'result')
    key = 'native_audit' if source_index in (0, 2) else 'legacy_case_directory'
    terminal[key] = dict(terminal[key], path='result/'+terminal[key]['path'])
    terminal['remote_terminal_receipt'] = dict(path='result/case.json', sha256=sha(remote_terminal))
    terminal['files_sha256'] = {str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*'))
                              if p.is_file() and p.name != 'case.json'}
    state.update(status='executed',identities_unchanged=True)
    write(output/'execution-receipt.json', state)
    terminal['files_sha256']['execution-receipt.json'] = sha(output/'execution-receipt.json')
    write(output/'case.json', terminal)
    return terminal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--source-index',type=int,required=True,choices=sorted(PROFILES))
    parser.add_argument('--runtime',type=Path,required=True)
    for sig in (signal.SIGTERM,signal.SIGINT):
        signal.signal(sig,request_stop)
    args = parser.parse_args(); result = run(args.inputs,args.output,args.source_index,args.runtime)
    print(json.dumps(dict(status=result['status'],source_index=result['source_index'],backend=result['backend'])))
