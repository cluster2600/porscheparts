"""Run the independent native detector and rational contact classification on one final envelope."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE=Path(__file__).resolve().parent
CLASSIFIER=SOURCE.parent/'design-20261016/classify_mesh_contacts.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(mesh,output,audit_python):
    mesh=Path(mesh).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__).resolve(),SOURCE/'audit_exact_volume.py',CLASSIFIER];frozen={str(p):sha(p) for p in files}
    (output/'source').mkdir()
    for p in files:shutil.copy2(p,output/'source'/p.name)
    input_sha=sha(mesh)
    commands=[[str(audit_python),str(SOURCE/'audit_exact_volume.py'),str(mesh),str(output/'topology')],
        [sys.executable,str(CLASSIFIER),str(mesh),str(output/'topology/pairs.npz'),str(output/'exact-contacts.json')]]
    for i,command in enumerate(commands):
        with (output/f'command-{i}.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    t=json.loads((output/'topology/assessment.json').read_text());e=json.loads((output/'exact-contacts.json').read_text())
    if t['input_sha256']!=input_sha or e['mesh_npz_sha256']!=input_sha or e['raw_pairs_npz_sha256']!=t['pairs_sha256']:
        raise ValueError('Independent audit receipts refer to different meshes or pairs')
    passed=t['topology_passed'] and e['remaining_pair_count']==0
    if sha(mesh)!=input_sha or any(sha(p)!=digest for p,digest in frozen.items()):raise ValueError('Independent audit source/input changed')
    report=dict(status='passed' if passed else 'rejected',input_sha256=input_sha,
        topology_receipt='topology/assessment.json',topology_receipt_sha256=sha(output/'topology/assessment.json'),
        pairs='topology/pairs.npz',pairs_sha256=sha(output/'topology/pairs.npz'),
        exact_contacts_receipt='exact-contacts.json',exact_contacts_receipt_sha256=sha(output/'exact-contacts.json'),
        raw_pair_count=t['raw_pair_count'],remaining_pair_count=e['remaining_pair_count'],source_sha256=frozen,
        sources_and_input_unchanged=True,commands=commands)
    (output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--audit-python',required=True,type=Path);a=p.parse_args();r=audit(a.mesh,a.output,a.audit_python)
    print(json.dumps({'status':r['status'],'raw_pair_count':r['raw_pair_count'],'remaining_pair_count':r['remaining_pair_count']}))
    sys.exit(0 if r['status']=='passed' else 1)
