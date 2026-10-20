"""Tighten the actual PCG/CG stopping multiplier, retaining accuracy gates."""
from pathlib import Path
import difflib
import hashlib
import json

p=Path('/build/ccx_2.21/src/pcgsolver.c');before=p.read_bytes();needle=b'c1=0.005'
if before.count(needle)!=2:raise ValueError('Expected both upstream PCG and CG stopping coefficients')
after=before.replace(needle,b'c1=1.e-12');p.write_bytes(after)
Path('/output/pcgsolver-original.c').write_bytes(before)
Path('/output/source-tightening.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='pcgsolver-original.c',tofile='pcgsolver-tightened.c')))
Path('/output/source-edit.json').write_text(json.dumps(dict(upstream_version='CalculiX 2.21 / Debian 2.21-1 source',source_before_sha256=hashlib.sha256(before).hexdigest(),source_after_sha256=hashlib.sha256(after).hexdigest(),actual_stopping_rule='maximum recursive residual <= c1 * mean nonzero initial residual (PCG)',original_stopping_multiplier=.005,tightened_stopping_multiplier=1e-12,changed_declarations=2,preiter_epsilon_argument_is_not_used_as_stopping_threshold=True,original_acceptance_tolerances_changed=False,other_numerical_source_changes=False,controls_pending=True),indent=2)+'\n')
