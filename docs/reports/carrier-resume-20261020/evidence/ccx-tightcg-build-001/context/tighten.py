"""Tighten a source-level CG tolerance; retain original accuracy gates."""
from pathlib import Path
import difflib
import hashlib
import json

p=Path('/build/ccx_2.21/src/preiter.c');before=p.read_bytes();needle=b'double eps=1.e-4,*u=NULL,*au=NULL;'
if before.count(needle)!=1:raise ValueError('The exact expected upstream tolerance declaration differs')
after=before.replace(needle,b'double eps=1.e-12,*u=NULL,*au=NULL;');p.write_bytes(after)
Path('/output/preiter-original.c').write_bytes(before)
Path('/output/source-tightening.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='preiter-original.c',tofile='preiter-tightened.c')))
Path('/output/source-edit.json').write_text(json.dumps(dict(upstream_version='CalculiX 2.21 / Debian 2.21-1 source',source_before_sha256=hashlib.sha256(before).hexdigest(),source_after_sha256=hashlib.sha256(after).hexdigest(),original_CG_epsilon=1e-4,tightened_CG_epsilon=1e-12,original_acceptance_tolerances_changed=False,other_numerical_source_changes=False,controls_pending=True),indent=2)+'\n')
