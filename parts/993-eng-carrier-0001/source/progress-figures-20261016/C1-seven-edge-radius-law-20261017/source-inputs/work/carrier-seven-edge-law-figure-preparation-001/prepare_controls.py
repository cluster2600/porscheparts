"""Create this specific source-only law-figure packet from closed small receipts."""
from pathlib import Path
import hashlib,importlib.util,json,os
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def read(q):q.stat();return json.loads(q.read_bytes())
def write(q,v):
    with q.open('xb')as f:f.write((json.dumps(v,indent=2,sort_keys=True)+'\n').encode());f.flush();os.fsync(f.fileno())
spec=importlib.util.spec_from_file_location('_new_scalar_figure_source',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
native=R/'work/carrier-process-20261017/bounded-webs-C1-full-contour-native-observer-preparation-001'
root=native/'root-terminal-review-001.json';owner=native/'terminal-collection-001.json'
assert sha(root)=='68c5afa2cb79f88839a4e026bb7523f8e7732ce7ac781395a12a92892bd15cd6'
assert sha(owner)=='7a0d05364c8b5786374f58366c1031498fc977a5b07f9e96ca379ef67a0206c0'
data=m.select_data(read(root),read(owner));write(H/'law-data.json',data)
base=R/'work/carrier-terminal-taper-four-case-figure-preparation-001';prior=read(base/'pending-plan.json');runtime=prior['runtime_sha256'];assert len(runtime)==219
contract=R/'work/carrier-process-20261017/bounded-webs-C1-full-contour-law-contract-preparation-001/law_contract.py'
restriction=R/'work/carrier-process-20261017/bounded-webs-C1-terminal-law-restriction-analysis-001/analyze.py'
supervisor=R/'work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py'
raw=native/'patched-output-001/candidate-native.brep';assert sha(raw)==read(root)['patched_raw_BREP_sha256']
inputs=[root,owner,native/'observe_contour.py',raw,contract,contract.parent/'root-source-review-001.json',restriction,base/'figure.py',base/'root-terminal-review-001.json',H/'figure.py',H/'law-data.json',H/'selfcheck.py',H/'README.md',Path(__file__)]
files={str(q.relative_to(R)):sha(q)for q in inputs};files.update(runtime)
dep={str(q.relative_to(R)):dict(bytes=q.stat().st_size,sha256=sha(q))for q in inputs if q not in[H/'figure.py',H/'law-data.json',H/'selfcheck.py',H/'README.md',Path(__file__)]}
write(H/'dependency-inventory.json',dict(schema='closed-seven-edge-law-figure-dependencies-1',all_dependencies_closed=True,inputs=dep,raw_BREP_parsed=False,native_assessments_reparsed=False,owner_terminal_complete_selection=True,plot_runtime_source_plan_sha256=sha(base/'pending-plan.json')))
files[str((H/'dependency-inventory.json').relative_to(R))]=sha(H/'dependency-inventory.json')
p=dict(schema='closed-seven-edge-law-figure-plan-1',status='SOURCE_ONLY_NOT_ARMED',source_root=str(R),launch_ready=False,root_GO=None,root_GO_sha256=None,workers=0,samples_per_native_knot_span=81,native_CAD_mesh_or_FEA_calls=0,bounds=dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),files_sha256=files,runtime_sha256=runtime,pure_helpers_source=str((base/'figure.py').relative_to(R)),literal_helper_names=['require','sha','read','write','fresh'],contract_source=str(contract.relative_to(R)),data=str((H/'law-data.json').relative_to(R)),closed_context=dict(root_review=str(root.relative_to(R)),owner_terminal=str(owner.relative_to(R))),output_directory=str((H/'render-001').relative_to(R)),exact_proof_separate_from_sampled_plot=True,stock_post_Build_curve=None,candidate_qualified=False,downstream_geometry_gates='PENDING')
write(H/'pending-plan.json',p)
python='/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10'
l=dict(schema='owned_closed_seven_edge_law_scalar_figure_pending_1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,total_wall_budget_seconds=180,cleanup_grace_seconds=[10,10],section_workers=1,maximum_pending_layers=2,cwd=str(R),command=[python,'-B',str(H/'figure.py'),'render',str(H/'plan.json'),None,str(H/'render-001')],output_directory=str((H/'render-001').relative_to(R)),execution_directory=str((H/'execution-001').relative_to(R)),inputs_sha256=dict(files,**{str((H/'pending-plan.json').relative_to(R)):sha(H/'pending-plan.json')}),source_sha256={str(supervisor.relative_to(R)):sha(supervisor),str((H/'figure.py').relative_to(R)):sha(H/'figure.py')})
write(H/'pending-launch.json',l)
c=dict(schema='owned_scalar_law_figure_pending_command-1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,argv=['/usr/local/bin/python3','-I','-B',str(supervisor),str(H/'launch-plan.json'),'--plan-sha256',None],pending_plan_sha256=sha(H/'pending-plan.json'),pending_launch_sha256=sha(H/'pending-launch.json'),rendering_not_authorized=True)
write(H/'pending-command.json',c)
print(json.dumps(dict(plan_sha256=sha(H/'pending-plan.json'),launch_sha256=sha(H/'pending-launch.json'),command_sha256=sha(H/'pending-command.json'),data_sha256=sha(H/'law-data.json'),plan_pins=len(files),runtime_files=len(runtime))))
