"""Freeze source-only controls from existing closed small receipts and runtime metadata."""
import ast
import hashlib
import json
from pathlib import Path
import sys

H = Path(__file__).resolve().parent
R = H.parents[1]
def sha(p):
    d = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): d.update(b)
    return d.hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, value):
    with Path(p).open('x') as f: json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')
def rel(p): return str(Path(p).relative_to(R))

runtime_source = 'work/carrier-surface-publication-001/replay-launch-plan.json'
runtime_prefix = 'work/part-workflow/runtimes/pyslm-coverage-011/env/'
runtime = {n:h for n,h in read(R/runtime_source)['inputs_sha256'].items() if n.startswith(runtime_prefix)}
assert len(runtime) == 5205
context = read(H/'closed-context.json')
loader = 'parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/figure.py'
raster = 'parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/raster_unlit.py'
reuse = dict(schema='functional-law-candidate-figure-literal-reuse-1', exact_original_read_binary=True, exact_whole_raster_bytes=True, loader_original=loader, loader_original_sha256=sha(R/loader), raster_original=raster, raster_sha256=sha(R/raster), runtime_original_launch=runtime_source, runtime_original_launch_sha256=sha(R/runtime_source), original_runtime_files=len(runtime), original_runtime_map_only_no_old_scientific_inputs_transferred=True)
write(H/'source-reuse.json', reuse)
completion = read(H/'runtime-completion.json')
assert completion['inherited_runtime_files'] == 5205 and completion['completed_runtime_files'] == 5259
assert not set(runtime) & set(completion['additional_runtime_sha256'])
runtime.update(completion['additional_runtime_sha256'])
assert len(runtime) == 5259
names = [loader, raster, runtime_source, 'work/carrier-surface-publication-001/root-publication-review-001.json']
names += [v for c in context.values() for v in c.values()]
names += [rel(H/n) for n in ['figure.py','raster_unlit.py','selfcheck.py','prepare.py','README.md','PREPARATION.md','ARMING.md','sources-and-pending-display-spec.json','geometry-data.json','closed-context.json','source-reuse.json']]
names += [rel(H/n) for n in ['runtime-completion.json','selfcheck_revision.py','source-changes.json']]
names += [completion['runtime_origin_evidence']['owner_terminal'], completion['runtime_origin_evidence']['diagnostic'], completion['runtime_origin_evidence']['root_review']]
files = {n:sha(R/n) for n in names}
files.update(runtime)
stl='work/carrier-process-20261017/bounded-webs-C1-functional-law-surface-preparation-001/output-001/surface/carrier-remeshed.stl'
assert (R/stl).stat().st_size == 31892584
files[stl] = '8d0b09b705e17ae2a8a57588ae44879790c97ef31fbd7ec44995536971442a6d'
plan = dict(schema='functional-law-candidate-STL-figure-plan-1', status='SOURCE_ONLY_NOT_ARMED', launch_ready=False, root_GO=None, root_GO_sha256=None, source_root=str(R), bounds=dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0), files_sha256=files, runtime_sha256=runtime, closed_context=context, data=rel(H/'geometry-data.json'), STL=stl, loader_original=loader, raster_original=raster, raster_copy=rel(H/'raster_unlit.py'), overview_camera_degrees=[30.0,0.0], detail_axes=[0,2], detail_view_from_negative_Y=True, native_calls=0, engineering_qualification_transferred=False, output_directory=rel(H/'render-001'))
write(H/'pending-plan.json',plan)
sup='work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py'
shim="import os,runpy,sys;os.chdir('/');sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
launch=dict(schema='owned_actual_functional_law_STL_figure_pending_1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,cwd=str(R),command=[str(R/runtime_prefix/'bin/python'),'-I','-B','-c',shim,str(H/'figure.py'),'render',str(H/'plan.json'),None,str(H/'render-001')],total_wall_budget_seconds=180,cleanup_grace_seconds=[10,10],section_workers=1,maximum_pending_layers=2,output_directory=rel(H/'render-001'),execution_directory=rel(H/'execution-001'),source_sha256={sup:sha(R/sup),rel(H/'figure.py'):sha(H/'figure.py')},inputs_sha256=dict(files,**{rel(H/'pending-plan.json'):sha(H/'pending-plan.json')}))
assert launch['command'][8] is None
write(H/'pending-launch.json',launch)
command=dict(schema='actual-functional-law-STL-figure-pending-command-1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,rendering_not_authorized=True,pending_plan_sha256=sha(H/'pending-plan.json'),pending_launch_sha256=sha(H/'pending-launch.json'),argv=['/usr/local/bin/python3','-I','-B',str(R/sup),str(H/'launch-plan.json'),'--plan-sha256',None])
write(H/'pending-command.json',command)
assert not {'numpy','matplotlib','vispy','OCP','gmsh','build123d'} & set(sys.modules)
print(json.dumps(dict(status='source_controls_frozen_not_armed', runtime_files=len(runtime),plan_pins=len(files),launch_merged_pins=len(dict(launch['inputs_sha256'],**launch['source_sha256'])),STL_body_not_read=True,plan_sha256=sha(H/'pending-plan.json'),launch_sha256=sha(H/'pending-launch.json'),command_sha256=sha(H/'pending-command.json'))))
