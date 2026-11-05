#!/usr/bin/env python3
"""Run cfMesh and checkMesh with separate, fail-closed process and log gates."""
import argparse
from pathlib import Path
import re
import subprocess
import sys


def run(command, case, output, timeout):
    with output.open('x') as log:
        return subprocess.run(command + ['-case', str(case)], cwd=case, stdout=log,
                              stderr=subprocess.STDOUT, timeout=timeout, check=False).returncode


def completed_mesher(text):
    return (text.rstrip().endswith('End')
            and 'Finished renaming boundary patches' in text
            and not re.search(r'Meshing process terminated!|cannot be untangled without sacrificing geometry constraints|FOAM FATAL', text, re.I))


def completed_check(text):
    return bool(re.search(r'^Mesh OK\.\s*$', text, re.M)) and text.rstrip().endswith('End') and not re.search(r'^Failed\s+\d+\s+mesh checks\.', text, re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path, help='existing OpenFOAM case')
    parser.add_argument('output', type=Path, help='new log directory')
    parser.add_argument('--timeout', type=int, default=1800, help='maximum seconds per process')
    args = parser.parse_args()
    case, output = args.case.resolve(), args.output.resolve()
    if args.timeout <= 0 or not (case / 'system' / 'meshDict').is_file():
        parser.error('case must contain system/meshDict and timeout must be positive')
    output.mkdir(parents=False, exist_ok=False)
    try:
        mesh_log = output / 'log.cartesianMesh'
        code = run(['cartesianMesh'], case, mesh_log, args.timeout)
        if code or not completed_mesher(mesh_log.read_text(errors='replace')):
            print('Meshing did not complete; checkMesh was not started.', file=sys.stderr)
            return 1
        check_log = output / 'log.checkMesh'
        code = run(['checkMesh', '-constant', '-allGeometry', '-allTopology', '-meshQuality'], case, check_log, args.timeout)
        if code or not completed_check(check_log.read_text(errors='replace')):
            print('Mesh quality was not accepted.', file=sys.stderr)
            return 1
        print('Mesh checks passed; CFD and physical validation are separate.')
        return 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f'Execution stopped: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
