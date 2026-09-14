"""Calcul thermique séquentiel, aucune modification de dictionnaire ou de maillage."""
import json
import math
from pathlib import Path
import re
import shutil
import time
from run_quadrature import MIB, PREP, inventory, need, pump, save, sha


class Guard:
    def __init__(self): self.steps = 0; self.balances = 0; self.mesh_ok = False
    def line(self, line):
        need('FOAM FATAL' not in line and 'Floating point exception' not in line and
             not re.search(r'(?<!\w)[+-]?(?:nan|inf(?:inity)?)(?!\w)', line, re.I), 'native_fatal_or_nonfinite')
        need(not re.search(r'Failed\s+\d+\s+mesh checks', line), 'mesh_failure')
        if line.strip() == 'Mesh OK.': self.mesh_ok = True
        clock = re.fullmatch(r'Time = ([0-9.eE+-]+)\s*', line)
        if clock:
            need(self.mesh_ok and self.steps == self.balances and self.steps < 1600 and
                 math.isclose(float(clock[1]), (self.steps+1)*2.5e-8, rel_tol=1e-10, abs_tol=1e-16), 'native_time_grid')
            self.steps += 1
        if line.startswith('F58_BALANCE '):
            v = list(map(float, line.split()[1:]))
            need(len(v) == 10 and all(math.isfinite(x) for x in v) and self.steps == self.balances+1 and
                 math.isclose(v[0], self.steps*2.5e-8, rel_tol=1e-10, abs_tol=1e-16) and
                 math.isclose(v[1], 2.5e-8, rel_tol=1e-13) and v[7] == 0, 'thermal_energy_time_grid')
            self.balances += 1
        need('Solving for p_rgh,' not in line and 'Solving for U' not in line, 'flow_solve_forbidden')


def main():
    results = Path('/results'); packet = Path('/packet'); report = {'cases': {}, 'completed': False,
        'field_export': False, 'work_tmpfs_limit_bytes': 1024**3, 'per_case_log_limit_bytes': 128*MIB,
        'manufacturing_authorized': False}
    try:
        need(sha(packet/'preparation-report.json') == PREP, 'preparation_pin')
        prep = json.loads((packet/'preparation-report.json').read_text())
        for q in ('q10', 'q20'):
            deadline = time.monotonic()+250; source = Path('/input')/q; case = Path('/work')/q
            frozen = prep['cases'][q]['inputs_sha256']; need(inventory(source) == frozen, 'case_pin')
            shutil.copytree(source, case); need(inventory(case) == frozen, 'copy_pin')
            guard = Guard(); item = {'completed': False}; report['cases'][q] = item
            try:
                with (results/(q+'.log')).open('xb') as output:
                    item['checkMesh_exit'] = pump(['checkMesh', '-case', str(case), '-allTopology', '-allGeometry'], output, deadline, 128*MIB, guard.line)
                    need(item['checkMesh_exit'] == 0 and guard.mesh_ok, 'mesh_gate_failed')
                    item['solver_exit'] = pump(['/f58bin/additiveFoamF58', '-case', str(case)], output, deadline, 128*MIB, guard.line)
                after = inventory(case)
                item['preexisting_inputs_unchanged'] = all(after.get(n) == h for n, h in frozen.items())
                item['generated_files_sha256'] = {n: h for n, h in after.items() if n not in frozen}
                item['no_unapproved_input_additions_or_remesh'] = all(n.split('/')[0] not in ('0', 'constant', 'system')
                    and 'polyMesh' not in Path(n).parts for n in item['generated_files_sha256'])
                item['completed'] = (item['solver_exit'] == 0 and guard.steps == guard.balances == 1600 and
                    item['preexisting_inputs_unchanged'] and item['no_unapproved_input_additions_or_remesh'] and time.monotonic() <= deadline)
                need(item['completed'], 'incomplete_40us_coupon')
            finally:
                item['telemetry'] = vars(guard); item['log_sha256'] = sha(results/(q+'.log'))
                item['readonly_inputs_unchanged'] = inventory(source) == frozen
            shutil.rmtree(case)  # Only this worker-created, exact tmpfs case; next case stays sequential.
        report['completed'] = True
    except Exception as e: report['error'] = type(e).__name__+': '+str(e)
    finally: save(results/'worker-report.json', report)
    return 0 if report['completed'] else 2


if __name__ == '__main__': raise SystemExit(main())
