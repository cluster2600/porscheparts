"""Check collected native witnesses; does not rerun or alter any geometry."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
closed = json.loads((root / 'hollow-connectivity.json').read_text())
opened = json.loads((root / 'tunnel-connectivity.json').read_text())
for key in ('results', 'zero_as_void_sensitivity_results'):
    assert [r['neighbours'] for r in closed[key]] == [6, 26]
    assert [r['isolated_sample_count'] for r in closed[key]] == [1728, 1728]
    assert [r['potential_isolated_component_count'] for r in closed[key]] == [1, 1]
    assert [r['isolated_sample_count'] for r in opened[key]] == [0, 0]
    assert [r['potential_isolated_component_count'] for r in opened[key]] == [0, 0]
assert closed['shared_exact_zero_samples'] == 0
assert opened['shared_exact_zero_samples'] == 48
assert opened['additional_exterior_samples_when_zeros_belong_to_void'] == [48, 48]
print('NATIVE_OCCUPANCY_AND_CONNECTIVITY_WITNESSES_PASS_NOT_PHYSICAL_VALIDATION')
