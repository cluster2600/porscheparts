"""Restore and reanalyse the two closed h2 cases; no solver, mesher or CAD import."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time

HERE = Path(__file__).resolve().parent


def load(name, path, injected=None):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); module.__dict__.update(injected or {}); spec.loader.exec_module(module)
    return module


archive = load('_fixed_local_refinement_archive', HERE / 'restore.py')


def checked_case(case, retained, expected_mesh):
    archive.require(retained['procedure'] == 'static' and retained['name'] == case['name'], 'Case label differs')
    archive.require(retained['mesh_sha256'] == expected_mesh, 'Actual qualified C1 local-h2 mesh identity differs')


def replay(output, expected, numpy_site, base_capsule=None):
    started = time.monotonic(); cpu = time.process_time(); report = archive.manifest(expected, base_capsule)
    output = Path(output).absolute()
    archive.require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                    'Fresh output without symlinks required')
    required = sum(row['bytes'] for row in archive.all_members(report).values())
    required += sum(report['archives'][case['archive']]['members'][case['root'] + '/' + name]['bytes']
                    for case in report['cases'] for name in ('energy-audit.json', 'global-peaks.json')) + 1024*1024
    archive.require(shutil.disk_usage(output.parent).free >= required, 'Insufficient free space for one exact restoration and four reports')
    output.mkdir(); results = []; code = 1; runtime_before = None
    receipt = dict(status='incomplete_reanalysis', capsule_manifest_sha256=expected, cwd=os.getcwd(),
                   actual_workers=0, new_solver_run=False, new_mesh=False, stress_convergence_established=False)
    try:
        archive.require(os.getcwd() == '/' and os.getpriority(os.PRIO_PROCESS, 0) == 10
                        and all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')),
                        'cwd=/, nice10 and one BLAS thread required')
        base_root, _ = archive.dependency(report, base_capsule)
        runtime = json.loads((base_root / 'runtime-provenance.json').read_text())
        runtime_before = {p: archive.sha(numpy_site / p) for p in runtime['numpy_files_sha256']}
        archive.require(runtime_before == runtime['numpy_files_sha256']
                        and archive.sha(Path(sys.executable).resolve()) == runtime['python_binary_sha256'], 'Analysis runtime differs')
        sys.path.insert(0, str(numpy_site)); import numpy as np
        archive.require(sys.version.split()[0] == runtime['python_version'] and np.__version__ == runtime['numpy_version']
                        and Path(np.__file__).resolve().is_relative_to(numpy_site.resolve()), 'Runtime versions/origin differ')
        restored = output / 'restored'; archive.restore(restored, expected, base_capsule)
        binding = load('_exact_C1_BREP_binding', base_root / 'sources/cad_binding.py')
        energy = load('_unchanged_energy_C1', base_root / 'sources/audit_energy.py', {'_verify_BREP_binding': binding.verify})
        simulation = load('_unchanged_simulation_h2', base_root / 'sources/simulate.py')
        peak = load('_unchanged_peak_locator_C1', base_root / 'sources/locate.py', {'_verify_BREP_binding': binding.verify})
        archive.require(energy.ENERGY_RELATIVE_TOLERANCE == 1e-4, 'Original energy threshold differs')
        for case in report['cases']:
            case_root = restored / case['root']; folder = case_root / 'cad/mesh-7'
            native = json.loads((folder / (case['name'] + '.json')).read_text())
            checked_case(case, native, report['C1_h2_mesh_sha256'])
            actual_energy = energy.audit(folder, case['name'])
            historical_energy = json.loads((case_root / 'energy-audit.json').read_text())
            archive.require(actual_energy == historical_energy and actual_energy['energy_closure_pass']
                            and actual_energy['tolerance'] == 1e-4, 'Complete independent energy result differs')
            actual_peak = peak.locate_case(folder, case['name'], energy, simulation, np)
            historical_peak = json.loads((case_root / 'global-peaks.json').read_text())
            archive.require(actual_peak == historical_peak and actual_peak['maximum_VM_MPa'] == case['expected_VM_MPa']
                            and actual_peak['maximum_ties'] == 1 and actual_peak['all_global_maximum_ties'][0]['element_id'] == 90371
                            and actual_peak['all_global_maximum_ties'][0]['IP_one_based'] == 2, 'Complete peak/IP result differs')
            for label, value in [('energy', actual_energy), ('peak', actual_peak)]:
                with (output / (case['key'] + '-' + label + '.json')).open('x') as stream:
                    json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
                retained_path = case_root / ('energy-audit.json' if label == 'energy' else 'global-peaks.json')
                archive.require(archive.sha(output / (case['key'] + '-' + label + '.json')) == archive.sha(retained_path),
                                'Entire replayed report bytes differ')
            results.append(dict(case=case['name'], energy_result_entirely_equal=True, peak_result_entirely_equal=True,
                                relative_energy_error=actual_energy['relative_energy_closure_error'], tolerance=1e-4,
                                VM_MPa=actual_peak['maximum_VM_MPa'], element_id=90371, IP_one_based=2))
        archive.require(all(archive.sha(restored / p) == row['sha256'] for p, row in archive.all_members(report).items()), 'Restored original changed during analysis')
        receipt.update(status='two_actual_C1_h2_BREP_cases_reanalysed_entire_results_and_bytes_equal', restored_inputs_unchanged=True); code = 0
    except BaseException as error:
        receipt['error'] = dict(type=type(error).__name__, message=str(error))
    finally:
        unchanged = False
        if runtime_before is not None:
            unchanged = (runtime_before == {p: archive.sha(numpy_site / p) for p in runtime_before}
                         and archive.sha(Path(sys.executable).resolve()) == runtime['python_binary_sha256'])
        archive.manifest(expected, base_capsule)
        if not unchanged: code = 1; receipt['status'] = 'runtime_changed_or_not_verified'
        receipt.update(actual_returncode=code, cases=results, runtime_unchanged=unchanged,
                       runtime_files=len(runtime_before or {}) + 1, wall_seconds=time.monotonic()-started,
                       CPU_seconds=time.process_time()-cpu, maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       memory_units='Darwin bytes', inner_wall_seconds=150, CPU_limit_seconds=[140, 141])
        with (output / 'reanalysis-receipt.json').open('x') as stream:
            json.dump(receipt, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(receipt)); return code


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('output', type=Path)
    p.add_argument('--manifest-sha256', required=True); p.add_argument('--numpy-site', type=Path, required=True)
    p.add_argument('--base-capsule', type=Path)
    a = p.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (140, 141))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150s reanalysis cap')))
    signal.alarm(150)
    try: raise SystemExit(replay(a.output, a.manifest_sha256, a.numpy_site, a.base_capsule))
    finally: signal.alarm(0)
