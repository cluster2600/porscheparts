"""Preserve090 syntax refusal; new091 differs only by one closing brace."""
import json,shutil
from pathlib import Path
from run_native import execute,sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');old=root/'regional-castellation-090';initial=w/'regional-castellation-090-inputs';case=root/'regional-castellation-fixed-091';assert not case.exists()
r=json.loads((old/'report.json').read_text());assert r['native_exit_code']==1 and not r['container_state']['OOMKilled'];assert all(sha(old/n)==h for n,h in r['output_sha256'].items());man=json.loads((initial/'manifest.json').read_text());assert all(sha(initial/n)==h for n,h in man['file_sha256'].items())
case.mkdir()
for n in ('constant','system'):shutil.copytree(initial/n,case/n)
p=case/'system/snappyHexMeshDict';s=p.read_text();token='outer {level (1 1);}}}';assert s.count(token)==1 and s.count('{')==s.count('}')+1;s=s.replace(token,token+'}');assert s.count('{')==s.count('}');p.write_text(s)
changes=[]
for n,h in man['file_sha256'].items():
 if sha(case/n)!=h:changes.append(n)
assert changes==['system/snappyHexMeshDict']
(w/'syntax-pair.json').write_text(json.dumps(dict(source_sha256=sha(Path(__file__)),old_case=str(old),new_case=str(case),only_changed_file=changes,only_change='One missing closing brace in refinementSurfaces',all_other_prepared_bytes_identical=True),indent=2)+'\n')
execute(case,'snappyHexMesh -overwrite > log.snappyHexMesh 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1',[root/'outer-wall-bisect-086',root/'castellation-target-089',old])
