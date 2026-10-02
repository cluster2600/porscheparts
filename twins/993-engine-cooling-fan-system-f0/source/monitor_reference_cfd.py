#!/usr/bin/env python3
"""Stop owned steady cases after both flow and torque windows settle."""
import argparse
import json
from pathlib import Path
import time
from summarize_fan_cfd import summarize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('cases', nargs='+', type=Path)
args = parser.parse_args()
pending = args.cases.copy()
for case in pending:
    if not (case/'system/controlDict').is_file():
        raise ValueError(f'Not a prepared case: {case}')
deadline = time.monotonic() + 7200
while pending:
    if time.monotonic() > deadline:
        raise TimeoutError('Study monitor exceeded two hours; solver remains independently controlled')
    for case in pending[:]:
        log = case/'log.foamRun'
        log_text = log.read_text() if log.exists() else ''
        if 'FOAM FATAL' in log_text:
            raise RuntimeError(f'Solver failed: {case}')
        try:
            report = summarize(case, allow_running=True)
        except (FileNotFoundError, ValueError, IndexError):
            if '\nEnd\n' in log_text:
                print(f'Ended without usable convergence windows: {case}', flush=True)
                pending.remove(case)
            continue  # Output tables may be between writes during a running iteration.
        (case/'running-summary.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        if report['normal_solver_exit']:
            pending.remove(case)
        elif report['last_iteration'] >= 250 and all(report[key] for key in (
                'numerical_window_checks_passed', 'standard_mesh_check_passed',
                'extended_mesh_check_passed', 'rotating_frame_interface_check_passed')):
            control = case/'system/controlDict'
            text = control.read_text()
            if 'stopAt endTime;' not in text:
                raise ValueError('Expected an owned endTime-controlled study case')
            temporary = control.with_suffix('.monitor-tmp')
            temporary.write_text(text.replace('stopAt endTime;', 'stopAt writeNow;'))
            temporary.replace(control)
            (case/'convergence-stop-request.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Convergence stop: {case} at {report["last_iteration"]}', flush=True)
            pending.remove(case)
    if pending:
        time.sleep(45)
