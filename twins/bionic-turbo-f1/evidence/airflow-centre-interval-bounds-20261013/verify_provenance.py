"""Confirm that reader v2 changes only an erroneous metadata path and output name."""
import hashlib,json
from pathlib import Path
w=Path(__file__).parent
v1=(w/'verify_centres.py').read_text()
expected=v1.replace('pinned_fraction_kernel_sha256=sha(p)',"pinned_fraction_kernel_sha256=sha(Path('work/bionic-feasibility-bounds-20261013/verify_bounds.py'))").replace("w/'independent-readback.json'","w/'independent-readback-v2.json'")
assert expected==(w/'verify_centres_v2.py').read_text()
a=json.loads((w/'independent-readback.json').read_text());b=json.loads((w/'independent-readback-v2.json').read_text())
for key in ('source_sha256','pinned_fraction_kernel_sha256'):a.pop(key);b.pop(key)
assert a==b
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=dict(source_sha256=sha(Path(__file__)),v1_sha256=sha(w/'verify_centres.py'),v2_sha256=sha(w/'verify_centres_v2.py'),scientific_outputs_identical=True,correction='kernel metadata was last manifest digest due to local name reuse; now exact kernel path',v1_retained=True)
(w/'provenance-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
