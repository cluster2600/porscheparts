"""Check all source boundaries with an independent exact CGAL inspector.

The enclosing tetrahedron is synthetic and establishes no carrier containment.
"""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys
import numpy as np

root=Path(__file__).resolve().parent
inventory=json.loads((root/'assessment.json').read_text())
rows=[]
for item in inventory['rows']:
    label=f"source-r{item['rank']}-{'positive' if item['branch']>0 else 'negative'}"
    case=root/label;case.mkdir();out=case/'decoded-001';out.mkdir()
    path=Path(item['input']);assert hashlib.sha256(path.read_bytes()).hexdigest()==item['input_sha256']
    with np.load(path,allow_pickle=False)as z:
        v=np.asarray(z['vertices'],dtype='<f8');f=np.asarray(z['triangles'],dtype='<u8')
        assert np.isfinite(v).all()
        mesh=out/'candidate.meshbin'
        with mesh.open('wb')as stream:
            stream.write(struct.pack('<QQ',len(v),len(f)));stream.write(v.tobytes());stream.write(f.tobytes())
        length=2**int(np.ceil(np.log2(max(1,float(np.abs(v).max()))*4)))
        tetra=case/'synthetic-enclosure.mesh64'
        tetra.write_text(f'4 4\n{-length} {-length} {-length}\n{3*length} {-length} {-length}\n{-length} {3*length} {-length}\n{-length} {-length} {3*length}\n0 2 1\n0 1 3\n0 3 2\n1 2 3\n')
    plan=dict(scope='Exact self-embedding, connectedness and outward orientation of original source; synthetic enclosure is not a carrier domain',input_sha256=item['input_sha256'],meshbin_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(),enclosure_sha256=hashlib.sha256(tetra.read_bytes()).hexdigest())
    (case/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    command=[sys.executable,'work/qualified-dilation-001/prove.py',str(case),str(tetra)]
    result=subprocess.run(command,check=True)
    terminal=json.loads((case/'proof-terminal.json').read_text())
    proof=json.loads((out/'independent-domain.json').read_text())
    rows.append(dict(case=label,returncode=terminal['returncode'],report=proof))
    print(label,terminal['returncode'],proof['status'],flush=True)
report=dict(status='all_source_boundaries_embedded' if all(x['returncode']==0 and x['report']['status']=='complete_strict_domain_containment_passed'for x in rows) else 'source_embedding_refused',scope='Complete source-surface inspection only; no carrier-domain or mechanical claim',rows=rows)
(root/'embedding-summary.json').write_text(json.dumps(report,indent=2)+'\n')
