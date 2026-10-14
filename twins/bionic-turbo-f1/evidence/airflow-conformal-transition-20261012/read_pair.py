"""Verify the rejected and admitted block dictionaries differ only in closure encoding."""
import json,sys
from pathlib import Path
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
base=Path('work/bionic-airflow-20261012');a=base/'conformal-transition-057';b=base/'conformal-transition-058'
for c,code in ((a,134),(b,0)):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==code
 assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
for n in ('controlDict','fvSchemes','fvSolution'):assert (a/'system'/n).read_bytes()==(b/'system'/n).read_bytes()
x=json.loads((a/'construction.json').read_text());y=json.loads((b/'construction.json').read_text())
assert x['vertices']==y['vertices'] and x['expected_interface_faces']==y['expected_interface_faces']
assert [sorted(set(f)) for f in x['walls']]==[sorted(set(f)) for f in y['walls']]
assert (a/'system/blockMeshDict').read_text().split('boundary (')[0]==(b/'system/blockMeshDict').read_text().split('boundary (')[0]
print('Verified exact vertices, blocks, grading, zones and boundary vertex sets; closure encoding differs.')
