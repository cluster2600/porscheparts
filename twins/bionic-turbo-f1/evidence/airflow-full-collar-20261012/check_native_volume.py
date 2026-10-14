"""Cross-check independent geometry volume against the native checkMesh report."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/full-collar-063')
r=json.loads((case/'report.json').read_text());assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
a=json.loads((w/'readback.json').read_text());log=(case/'log.checkMesh').read_text()
m=re.search(r'Min volume = (\S+)\. Max volume = (\S+)\.  Total volume = (\S+)\.',log);assert m
minimum,maximum,total=map(float,m.groups())
assert minimum>0 and maximum>=minimum and total>0
assert abs(minimum/a['minimum_cell_volume_m3']-1)<1e-12
assert abs(total/a['boundary_volume_m3']-1)<1e-12
assert abs(total/a['analytic_volume_m3']-1)<1e-12
out=dict(source_sha256=sha(Path(__file__)),native_log_sha256=sha(case/'log.checkMesh'),independent_readback_sha256=sha(w/'readback.json'),native_minimum_volume_m3=minimum,native_maximum_volume_m3=maximum,native_total_volume_m3=total,relative_total_difference=abs(total/a['boundary_volume_m3']-1),matched=True,performance_ranking_authorized=False)
with (w/'volume-crosscheck.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out))
