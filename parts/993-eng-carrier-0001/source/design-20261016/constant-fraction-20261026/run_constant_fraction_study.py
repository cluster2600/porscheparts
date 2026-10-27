"""Refinement study at constant solid fraction.

Runs the tuned-threshold case at each declared resolution and reports the full
tensor change between successive grids, against the unchanged 2% condition.
The comparison is only meaningful because every grid now carries the same
solid fraction to within half a cell.

The earlier fixed-threshold sequence is retained for contrast; it is not
rewritten. A refusal is recorded rather than a partial pass if any case fails.
"""
from pathlib import Path
import json
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent


def main() -> None:
    contract = json.loads((HERE / (sys.argv[2] if len(sys.argv) > 2 else 'study-contract.json')).read_text())
    out_root = Path(sys.argv[1])
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for n in contract['resolutions']:
            reports = []
            for floor, label in [(1e-4, '1e-4'), (1e-6, '1e-6')]:
                name = f'n{n}-floor{label}'
                out = out_root / name
                params = out_root / f'{name}-parameters.json'
                if not out.exists():
                    params.write_text(json.dumps(dict(
                        resolution=n,
                        void_relative_stiffness=floor,
                        target_solid_fraction=contract['target_solid_fraction'],
                        solver_binary=contract['solver_binary'],
                        solver_binary_sha256=contract['solver_binary_sha256'],
                        solver_threads=contract['solver_threads'],
                        seconds=contract['seconds'],
                        rss_gib=contract['rss_gib'],
                    ), indent=2) + '\n')
                    with (out_root / f'{name}-driver.log').open('w') as log:
                        subprocess.run(
                            [sys.executable, str(HERE / 'run_constant_fraction_case.py'),
                             str(params), str(out)],
                            stdout=log, stderr=subprocess.STDOUT, check=True)
                report = json.loads((out / 'assessment.json').read_text())
                assert report['status'].endswith('six_strain_energy_checks_passed')
                reports.append(report)

            left, right = [np.array(x['effective_C_MPa']) for x in reports]
            contrast = float(np.linalg.norm(left - right) / np.linalg.norm(right))
            row = dict(
                resolution=n,
                solid_fraction=reports[1]['solid_fraction'],
                solid_fraction_error_relative=reports[1]['solid_fraction_error_relative'],
                gyroid_threshold=reports[1]['gyroid_threshold'],
                minimum_tensor_stiffness_ratio=reports[1]['minimum_tensor_stiffness_ratio'],
                relative_void_floor_tensor_change=contrast,
                void_floor_test_passed=contrast <= .01,
            )
            if rows:
                previous = np.array(json.loads(
                    (out_root / f"n{rows[-1]['resolution']}-floor1e-6/assessment.json"
                     ).read_text())['effective_C_MPa'])
                change = float(np.linalg.norm(previous - right) / np.linalg.norm(right))
                row['relative_tensor_resolution_change'] = change
                row['resolution_change_passed'] = change <= .02
            rows.append(row)
            (out_root / 'comparison-progress.json').write_text(json.dumps(rows, indent=2) + '\n')
            print(row, flush=True)

        converged = (len(rows) >= 3
                     and all(x.get('resolution_change_passed') and x['void_floor_test_passed']
                             for x in rows[-2:]))
        (out_root / 'terminal.json').write_text(json.dumps(dict(
            status='constant_fraction_refinement_study_completed',
            threshold_policy='solved per resolution to hold the actual solid fraction',
            unitcell_stiffness_converged=converged,
            comparisons=rows,
            carrier_convergence_demonstrated=False,
            cellular_part_generated=False,
        ), indent=2) + '\n')
    except Exception as error:
        (out_root / 'refusal.json').write_text(json.dumps(dict(
            error=type(error).__name__,
            detail=str(error),
            completed_comparisons=rows,
            unitcell_stiffness_converged=False,
            epoch=time.time(),
        ), indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
