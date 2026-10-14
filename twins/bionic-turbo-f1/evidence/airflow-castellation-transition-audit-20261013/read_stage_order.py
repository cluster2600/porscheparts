"""Locate the two audited native snapshots in the archived log, without execution."""
import json,hashlib
from pathlib import Path
w=Path(__file__).parent;p=Path('work/bionic-airflow-20261012/regional-castellation-fixed-091/log.snappyHexMesh');lines=p.read_text().splitlines();entries=[dict(line=i+1,text=l) for i,l in enumerate(lines) if ('Writing ' in l and 'mesh to time ' in l) or l.startswith(('Surface refinement iteration','Dangling cell refinement iteration','Refinement transition refinement iteration'))]
assert any('refined but unbalanced "surface refinement iteration 0" mesh to time 1e-07' in e['text'] for e in entries)
(w/'stage-order.json').write_text(json.dumps(dict(reader_sha256=hashlib.file_digest(Path(__file__).open('rb'),'sha256').hexdigest(),log_sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),entries=entries,interpretation='First audited mesh is written immediately after surface refinement iteration 0. Debug labels are not flow time. No unique-cause claim.'),indent=2)+'\n')
