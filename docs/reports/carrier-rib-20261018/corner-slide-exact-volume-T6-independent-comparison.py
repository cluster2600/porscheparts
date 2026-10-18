"""Compare independent ROOT universal T6 coefficients with the new exact implementation; no mesh reads."""
from fractions import Fraction
from pathlib import Path
import hashlib,importlib.util,json
H=Path(__file__).resolve().parent;R=H.parents[2]
P=R/'work/carrier-root-T6-symbolic-fixture-20261018-001.json'
assert hashlib.sha256(P.read_bytes()).hexdigest()=='be861abdcb5cf2821ed77c7ac36ec82723c0854120feee1f165f49441c1d1ff0'
spec=importlib.util.spec_from_file_location('_synthetic_only_mapped_exact',H/'mapped_exact.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
independent=json.loads(P.read_bytes());expected={tuple(row['indices']):Fraction(row['coefficient'])for row in independent['coefficients']};actual={indices:Fraction(value,2160)for indices,value in M.tensors(2)}
assert len(expected)==len(actual)==20 and expected==actual
points=[(0,0,8),(8,0,8),(0,8,8),(4,0,9),(4,4,8),(0,4,8)]
assert Fraction(M.face2160(points),2160*8**3)==Fraction(independent['nonaffine_midside_flux'])
record=dict(schema='current24af-exact-volume-independent-T6-symbolic-comparison-1',independent_ROOT_fixture=str(P.relative_to(R)),independent_ROOT_fixture_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),implementation_sha256=hashlib.sha256((H/'mapped_exact.py').read_bytes()).hexdigest(),node_order=independent['node_order'],all20_signed_rational_coefficients_equal=True,nonaffine_analytic_face_flux='3/16',actual_current_mesh_read_or_native_or_numpy=False)
with(H/'independent-symbolic-comparison.json').open('x')as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record))
