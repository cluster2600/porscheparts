#!/usr/bin/env python3
"""Stop owned steady cases after both flow and torque windows settle."""
import argparse
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
        if log.exists() and 'FOAM FATAL' in log.read_text():
            raise RuntimeError(f'Solver failed: {case}')
        try:
            report = summarize(case, allow_running=True)
        except (FileNotFoundError, ValueError, IndexError):
            continue  # Output tables may be between writes during a running iteration.
        if report['normal_solver_exit']:
            pending.remove(case)
        elif report['last_iteration'] >= 250 and report['numerical_window_checks_passed']:
            control = case/'system/controlDict'
            text = control.read_text()
            if 'stopAt endTime;' not in text:
                raise ValueError('Expected an owned endTime-controlled study case')
            control.write_text(text.replace('stopAt endTime;', 'stopAt writeNow;'))
            print(f'Convergence stop: {case} at {report["last_iteration"]}', flush=True)
            pending.remove(case)
    if pending:
        time.sleep(5)
