"""Compare all prepared physics and execution limits without relying on field sizes."""
import json,sys
from pathlib import Path
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');a=root/'connected-equilibrium-076';b=root/'coupled-equilibrium-084';parent=root/'post-snap-stitch-083'
x=json.loads((a/'manifest.json').read_text());y=json.loads((b/'manifest.json').read_text());r=json.loads((parent/'report.json').read_text());assert r['mesh_gate_passed'] and all(sha(parent/n)==h for n,h in r['output_sha256'].items())
assert x['criteria']==y['criteria']
for n,h in x['file_sha256'].items():assert sha(a/n)==h
for n,h in y['file_sha256'].items():
 assert sha(b/n)==h and sha(w/'coupled-equilibrium-084-inputs'/n)==h
 if n.startswith('constant/polyMesh/'):assert sha(parent/n)==h
xn={n:h for n,h in x['file_sha256'].items() if not n.startswith('constant/polyMesh/')};yn={n:h for n,h in y['file_sha256'].items() if not n.startswith('constant/polyMesh/')};assert xn==yn
ex=json.loads((a/'execution.json').read_text());ey=json.loads((b/'execution.json').read_text())
assert all(ex[k]==ey[k] for k in ('timeout_seconds','cpus','memory_gib','command'))
common=set(x['file_sha256'])&set(y['file_sha256']);changed=sorted(n for n in common if x['file_sha256'][n]!=y['file_sha256'][n]);added=sorted(set(y['file_sha256'])-set(x['file_sha256']));removed=sorted(set(x['file_sha256'])-set(y['file_sha256']));assert all(n.startswith('constant/polyMesh/') for n in changed+added+removed)
result=dict(reader_sha256=sha(Path(__file__)),criteria_identical=True,all_nonmesh_prepared_inputs_byte_identical=True,execution_command_budget_cpu_memory_unchanged=True,initial_inputs_copied_before_execution_and_verified=True,mesh_exact_parent083=True,changed_paths=changed,added_paths=added,removed_paths=removed,scope='Synthetic rest comparison on different cell topology. No physical performance or completed run inferred.')
with (w/'paired-inputs.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
