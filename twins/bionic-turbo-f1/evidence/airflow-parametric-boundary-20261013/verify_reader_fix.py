"""Check that the retained reader correction only normalizes sparse zero coefficients."""
import hashlib,json
from pathlib import Path
from fractions import Fraction as F
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
w=Path(__file__).parent;a=(w/'verify_boundary.py').read_text();b=(w/'verify_boundary_v2.py').read_text()
expected=a.replace("assert xyzpoly==[{0:F(x)} for x in xyz]","assert xyzpoly==[{0:F(x)} if x else {} for x in xyz]").replace("w/'independent-readback.json'","w/'independent-readback-v2.json'")
assert b==expected
s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());u=F(sy['archived_regression_point']['u']);n=0;mismatches=[]
for binding in sy['coordinate_bindings']:
 if binding['variable']!='u':continue
 n+=1;i=binding['point'];actual=[F(binding['x_coefficient'])*u,F(binding['y_coefficient'])*u,F(binding['z_exact'])];source=[F(x) for x in s['vertices'][i]];assert actual==source
 sparse=[{0:x} if x else {} for x in actual];raw=[{0:x} for x in source]
 if sparse!=raw:mismatches.append(i);assert all(x==y or (x=={} and y=={0:F(0)}) for x,y in zip(sparse,raw))
assert mismatches
out=dict(source_sha256=sha(Path(__file__)),v1_sha256=sha(w/'verify_boundary.py'),v2_sha256=sha(w/'verify_boundary_v2.py'),only_zero_representation_and_output_name_changed=True,all_u_bound_coordinates_exact=n,zero_representation_mismatches=mismatches,v1_result='assertion_before_geometric_verification',v2_result='complete_independent_readback',geometry_or_threshold_changed=False)
(w/'reader-fix-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
