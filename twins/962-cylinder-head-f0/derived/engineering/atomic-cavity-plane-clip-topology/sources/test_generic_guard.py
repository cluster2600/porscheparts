"""Generic topology guard literals only; no worker/scientific import or native call."""
import ast
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'work/962-engineering/atomic-cavity-plane-clip-topology-prep-001/audit_atomic_topology.py'
expected = '9025dfaacb8e3b51f2ef80ccf7570b8e5e9cea1081902cad60c5c758844b0092'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == expected
nodes = [n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'require_reference_topology']
assert len(nodes) == 1
namespace = {'math': math}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)
guard = namespace['require_reference_topology']
base = dict(boundary_edges=0, nonmanifold_edges=0, orientation_imbalanced_edges=0, euler_characteristic=0, signed_volume_mm3=1.)
for euler in [-208, -210, -4, 0, 2]:
    guard(dict(base, euler_characteristic=euler), 1)
cases = [(base, value) for value in [0, 2, True, 1.]]
cases += [(dict(base, euler_characteristic=value), 1) for value in [None, 1., True]]
missing = dict(base); missing.pop('euler_characteristic'); cases.append((missing, 1))
for key in ['boundary_edges', 'nonmanifold_edges', 'orientation_imbalanced_edges']:
    cases += [(dict(base, **{key:value}), 1) for value in [1, None, False]]
cases += [(dict(base, signed_volume_mm3=value), 1) for value in [0, -1, math.nan, math.inf, True, '1']]
assert len(cases) == 23
for surface, count in cases:
    try:
        guard(surface, count)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid generic literal accepted')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == expected
print('PASS: 5 integer-Euler literals and 23 invalid-input refusals; no scientific imports')
