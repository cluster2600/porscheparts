"""Prepare only Figure32 source/metadata and unarmed controls; never read STL bodies."""
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

H=Path(__file__).resolve().parent
R=H.parents[1]
OLD=R/'work/carrier-functional-law-candidate-image-preparation-004'
PROCESS=R/'work/carrier-process-20261017'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    with p.open('x')as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def rel(p):return str(Path(p).relative_to(R))

assert sys.argv[1:]==['prepare']
old=(OLD/'figure.py').read_text();new=(H/'figure.py').read_text()
def segment(text,name):return ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name))
helpers=['require','sha','read','write','fresh','read_binary']
assert all(segment(old,n)==segment(new,n)for n in helpers)
with(H/'raster_unlit.py').open('xb')as f:f.write((OLD/'raster_unlit.py').read_bytes())
delta=list(difflib.ndiff(old.splitlines(True),new.splitlines(True)))
assert ''.join(difflib.restore(delta,1))==old and ''.join(difflib.restore(delta,2))==new
with(H/'figure-from-Figure30.ndiff').open('x')as f:f.write(''.join(delta))
context={
 'old_generation':dict(ROOT=rel(PROCESS/'bounded-webs-C1-functional-law-surface-preparation-001/root-terminal-review-001.json'),owner=rel(PROCESS/'bounded-webs-C1-functional-law-surface-preparation-001/terminal-collection-001.json')),
 'old_mass':dict(ROOT=rel(PROCESS/'bounded-webs-C1-functional-law-addition-preparation-001/root-terminal-review-001.json'),owner=rel(PROCESS/'bounded-webs-C1-functional-law-addition-preparation-001/terminal-collection-001.json')),
 'stock_generation':dict(ROOT=rel(PROCESS/'bounded-webs-first-window-stock-surface-preparation-001/root-terminal-review-001.json'),owner=rel(PROCESS/'bounded-webs-first-window-stock-surface-preparation-001/terminal-collection-001.json')),
 'stock_native':dict(ROOT=rel(PROCESS/'bounded-webs-first-window-stock-admission-preparation-001/root-terminal-review-001.json'),owner=rel(PROCESS/'bounded-webs-first-window-stock-admission-preparation-001/terminal-collection.json')),
 'delivery':dict(ROOT='work/carrier-first-window-stock-geometry-delivery-preparation-002/root-terminal-review-001.json',owner='work/carrier-first-window-stock-geometry-delivery-preparation-002/terminal-collection.json')}
records={k:[read(R/v['ROOT']),read(R/v['owner'])]for k,v in context.items()}
for k,v in context.items():assert records[k][0]['owner_terminal_sha256']==sha(R/v['owner'])
spec=importlib.util.spec_from_file_location('_Figure32_stdlib_source',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data=m.select_data(records)
write(H/'closed-context.json',context);write(H/'geometry-data.json',data)
runtime=read(OLD/'plan.json')['runtime_sha256'];assert len(runtime)==5259
reuse=dict(schema='Figure32-actual-source-reuse-1',original_figure=rel(OLD/'figure.py'),original_figure_sha256=sha(OLD/'figure.py'),new_figure_sha256=sha(H/'figure.py'),six_helpers_literal_equal=helpers,
           whole_raster_byte_equal=True,raster_sha256=sha(H/'raster_unlit.py'),whole_ndiff_forward_and_inverse_byte_equal=True,
           runtime_source=rel(OLD/'plan.json'),runtime_source_sha256=sha(OLD/'plan.json'),runtime_files=5259,runtime_map_unchanged=True)
write(H/'source-reuse.json',reuse)
stls=[rel(PROCESS/'bounded-webs-C1-functional-law-surface-preparation-001/output-001/surface/carrier-remeshed.stl'),rel(PROCESS/'bounded-webs-first-window-stock-surface-preparation-001/output-001/surface/carrier-remeshed.stl')]
names=[rel(H/n)for n in ['figure.py','raster_unlit.py','selfcheck.py','prepare.py','README.md','ARMING.md','figure-from-Figure30.ndiff','source-reuse.json','closed-context.json','geometry-data.json']]
names += [p for row in context.values()for p in row.values()]
names += [rel(OLD/'figure.py'),rel(OLD/'raster_unlit.py'),rel(OLD/'plan.json'),rel(OLD/'root-terminal-review-001.json')]
nominal='parts/993-eng-carrier-0001/source/design-20261016/bounded-webs.json';names.append(nominal)
files={n:sha(R/n)for n in names};files.update(runtime)
for name,row in zip(stls,data['cases']):
    assert(R/name).stat().st_size==row['STL_bytes'];files[name]=row['STL_sha256']
plan=dict(schema='stock-two-actual-STL-comparison-figure-plan-1',launch_ready=False,root_GO=None,root_GO_sha256=None,source_root=str(R),
          bounds=dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),files_sha256=files,runtime_sha256=runtime,closed_context=context,data=rel(H/'geometry-data.json'),STLs=stls,
          figure_original=rel(OLD/'figure.py'),raster_original=rel(OLD/'raster_unlit.py'),raster_copy=rel(H/'raster_unlit.py'),
          nominal_study=nominal,overview_camera_degrees=[30.0,0.0],detail_axes=[0,1],detail_view_from_positive_Z=True,native_calls=0,output_directory=rel(H/'render-001'))
write(H/'pending-plan.json',plan)
sup='work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py'
py=R/'work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python'
shim="import os,runpy,sys;os.chdir('/');sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
launch=dict(schema='owned-two-STL-stock-comparison-pending-1',launch_ready=False,root_GO=None,root_GO_sha256=None,cwd=str(R),
 command=[str(py),'-I','-B','-c',shim,str(H/'figure.py'),'render',str(H/'pending-plan.json'),sha(H/'pending-plan.json'),str(H/'render-001')],
 total_wall_budget_seconds=180,cleanup_grace_seconds=[10,10],section_workers=1,maximum_pending_layers=2,output_directory=rel(H/'render-001'),execution_directory=rel(H/'execution-001'),
 source_sha256={sup:sha(R/sup),rel(H/'figure.py'):sha(H/'figure.py')},inputs_sha256=dict(files,**{rel(H/'pending-plan.json'):sha(H/'pending-plan.json')}))
write(H/'pending-launch-plan.json',launch)
command=dict(schema='pending-two-STL-stock-comparison-command-1',launch_ready=False,root_GO=None,root_GO_sha256=None,cwd=str(R),parent_not_niced=True,
 argv=['/usr/local/bin/python3','-I','-B',str(R/sup),str(H/'pending-launch-plan.json'),'--plan-sha256',sha(H/'pending-launch-plan.json')])
write(H/'pending-command.json',command)
assert not {'numpy','matplotlib','vispy','OCP','gmsh','build123d'}&set(sys.modules)
print(json.dumps(dict(status='SOURCE_ONLY_FIGURE32_NOT_ARMED',plan_sha256=sha(H/'pending-plan.json'),launch_sha256=sha(H/'pending-launch-plan.json'),command_sha256=sha(H/'pending-command.json'),runtime_files=5259,plan_pins=len(files),STL_body_read=False)))
