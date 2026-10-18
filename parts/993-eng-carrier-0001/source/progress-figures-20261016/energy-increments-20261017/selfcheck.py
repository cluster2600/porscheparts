"""Small stdlib checks of plot data guards; no solver/auditor import."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_energy_figure', HERE / 'render.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
manifest, data = module.load()
checks = ['all_real_16_and_32_state_series_accepted']
for label, change in [
    ('missing_state_refused', lambda d: d['ener-32.json']['frames'].pop()),
    ('changed_threshold_refused', lambda d: d['comparison.json']['thresholds'].update(ENER=0.01)),
    ('invented_residual_threshold_refused', lambda d: d['comparison.json']['unloaded_residual'].update(acceptance_threshold=0.1)),
    ('changed_maximum_refused', lambda d: d['comparison.json']['worst_Piola_relative_to_gross'].update(refined=0.0)),
    ('changed_load_factor_refused', lambda d: d['piola-32.json']['frames'][0].update(load_factor=0.125)),
]:
    altered = copy.deepcopy(data)
    change(altered)
    try:
        module.validate(altered)
    except ValueError:
        checks.append(label)
    else:
        raise AssertionError(label)
print(json.dumps({'status': 'passed', 'checks': checks, 'solver_or_audit_run': False}))
