#!/usr/bin/env python3
"""Prepare paired local thermal diagnostics differing only in the Tmax limiter."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def replace(path, pattern, value):
    text, count = re.subn(pattern, value, path.read_text(), flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f'expected one match in {path.name}, got {count}')
    path.write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--include-constant-absorption', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    reports = {}
    modes = ['capped', 'uncapped']
    if a.include_constant_absorption:
        modes.append('uncapped_constant_absorption')
    for mode in modes:
        case = a.output / mode
        case.mkdir()
        for folder in ('0', 'constant', 'system'):
            shutil.copytree(a.source / folder, case / folder)
        control = case / 'system/controlDict'
        replace(control, r'^endTime\s+[^;]+;', 'endTime 0.00012;')
        replace(control, r'^writeInterval\s+[^;]+;', 'writeInterval 0.00004;')
        replace(control, r'^writeFormat\s+[^;]+;', 'writeFormat ascii;')
        replace(control, r'^functions\s*\{', '''functions
{
    diagnosticTemperatureBounds
    {
        type volFieldValue;
        libs ("libfieldFunctionObjects.so");
        fields (T);
        operation max;
        cellZone all;
        writeFields false;
        writeControl timeStep;
        writeInterval 1;
    }''')
        solution = case / 'system/fvSolution'
        if mode != 'capped':
            replace(solution, r'^\s*Tmax\s+3300\.0;',
                    '// Diagnostic only: omitted Tmax uses solver default vGreat.')
        if mode == 'uncapped_constant_absorption':
            replace(case / 'constant/heatSourceDict', r'\babsorption\s*\{[^}]*\}',
                    'absorption { model constant; eta 0.35; }')
        reports[mode] = {
            'files_sha256': {str(path.relative_to(case)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(case.rglob('*')) if path.is_file()},
            'temperature_limiter_3300K': mode == 'capped'}
    report = {'schema': 'porsche-additive-cap-diagnostic-f55/v1', 'cases': reports,
              'end_time_s': .00012, 'classification': 'local_thermal_diagnostic_not_process_qualification',
              'supplier_recipe_calibrated': False, 'manufacturing_authorized': False}
    (a.output / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'prepared': list(reports), 'end_time_s': .00012}))


if __name__ == '__main__':
    main()
