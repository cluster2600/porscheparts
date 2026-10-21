"""Read-only closeout of the one authorized actual-STL render; no graphic/native imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

H = Path(__file__).resolve().parent
R = H.parents[1]
def require(ok, message):
    if not ok: raise ValueError(message)
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def encoded(value): return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()

def collect():
    started = time.monotonic()
    p,l,c = [read(H/n) for n in ['plan.json','launch-plan.json','command.json']]
    a=read(H/'arming-assessment.json');s=read(H/'execution-001/execution-receipt.json');tool=read(H/'actual-tool-terminal.json')
    require(tool['owned_handle']==32423 and tool['actual_returncode']==0 and s['status']=='executed' and s['actual_returncode']==0,'Actual RC0 tool/supervisor join differs')
    require(s['direct_child_reaped'] is True and s['no_non_zombie_group_members'] is True and s['sources_and_plan_unchanged'] is True and s['failure'] is s['cleanup_error'] is None and not s['timeout'] and not s['interrupted'],'Unclosed or changed supervised run')
    require(s['residual_members_before_cleanup']==s['signals_to_owned_group_only']==s['final_group_members']==[],'Unexpected owned-group residue or signal')
    require(s['command']==l['command'] and s['plan_sha256']==sha(H/'launch-plan.json')==a['launch_sha256'] and a['plan_sha256']==sha(H/'plan.json') and a['command_sha256']==sha(H/'command.json'),'Actual plan/arming/command differs')
    pins=dict(l['inputs_sha256'],**l['source_sha256']);require(len(pins)==5291 and s['sources_before']==s['sources_after']==pins,'Whole supervision pin maps differ')
    require(all(sha(R/n)==h for n,h in pins.items()),'A complete current input/source/runtime differs')
    go=p['root_GO'];gh=p['root_GO_sha256'];require(gh=='2ad883f14e8551fd6ce457c72bb856e3c9798e7bc345377e7199fe352c3a35d6' and sha(R/go)==gh and l['root_GO']==c['root_GO']==go and l['root_GO_sha256']==c['root_GO_sha256']==gh,'ROOT render GO differs')
    inverse=[]
    for name,value in [('pending-plan.json',p),('pending-launch.json',l),('pending-command.json',c)]:
        old=read(H/name);v=json.loads(json.dumps(value))
        for key in ['status','launch_ready','root_GO','root_GO_sha256']:v[key]=old[key]
        if name=='pending-plan.json':del v['files_sha256'][go]
        elif name=='pending-launch.json':v['command'][8]=None;del v['inputs_sha256'][go];del v['inputs_sha256'][str((H/'plan.json').relative_to(R))]
        else:v['rendering_not_authorized']=True;v['argv'][6]=None
        require(v==old and encoded(v)==(H/name).read_bytes(),'Whole pending object/byte inverse differs');inverse.append(name)
    for n,h in s['logs_sha256'].items():require(sha(H/'execution-001'/n)==h,'Closed log differs')
    require((H/'execution-001/stdout.log').read_bytes()==(H/'execution-001/stderr.log').read_bytes()==b'','Unexpected child log text')
    names={'carrier-functional-law-candidate.png','carrier-functional-law-candidate.svg','carrier-functional-law-candidate.pdf','runtime-origin-diagnostic.json','render-receipt.json'}
    require({q.name for q in (H/'render-001').iterdir()}==names,'Unexpected render path set')
    diagnostic=read(H/'render-001/runtime-origin-diagnostic.json');receipt=read(H/'render-001/render-receipt.json');data=read(H/'geometry-data.json')
    canonical={str((R/n).resolve()):h for n,h in p['runtime_sha256'].items()};loaded=diagnostic['runtime_imported_files']
    require(len(p['runtime_sha256'])==len(canonical)==5259 and diagnostic['declared_runtime_file_count']==5259 and len(loaded)==598 and loaded==sorted(set(loaded)) and diagnostic['outside_runtime_imported_files']==sorted(set(loaded)-set(canonical))==[],'Whole runtime-origin diagnostic differs')
    require(receipt['schema']=='actual-functional-law-candidate-STL-render-1' and receipt['status']=='actual_complete_candidate_STL_two_panel_display_only' and receipt['plan_sha256']==sha(H/'plan.json') and receipt['source_sha256']==sha(H/'figure.py'),'Actual render receipt identity differs')
    require(receipt['input_sha256']==p['files_sha256'] and receipt['runtime_imported_files']==loaded and all(sha(n)==canonical[n] for n in loaded),'Whole imported runtime/input map differs')
    require(receipt['complete_STL_triangles']==data['STL_triangles']==637850 and receipt['all_faces_retained_in_overview'] is True and receipt['local_selected_triangle_count']>0 and receipt['local_display_box_mm']==data['source_edge431_display_box_mm'],'Actual full geometry/display crop differs')
    require(receipt['source_physical_edge431']==data['whole_source_physical_edges'][0] and receipt['native_mass_kg']==data['native_mass_kg']==1.2623644100871174 and receipt['local_projected_axes']==[0,2] and receipt['local_view_from_negative_Y'] is True and receipt['geometry_modified'] is False and receipt['engineering_qualification_transferred'] is False and receipt['native_calls']==0 and receipt['cwd']=='/','Scope/source datums/native mass/cwd differs')
    require(set(receipt['exports_sha256'])==names-{'render-receipt.json'} and all(sha(H/'render-001'/n)==h for n,h in receipt['exports_sha256'].items()),'Whole export/diagnostic hash map differs')
    source_spec=importlib.util.spec_from_file_location('_closed_actual_STL_figure',H/'figure.py');source=importlib.util.module_from_spec(source_spec);source_spec.loader.exec_module(source);source.verify(H/'plan.json',sha(H/'plan.json'),rendering=True)
    sup_spec=importlib.util.spec_from_file_location('_owned_supervisor_readonly',R/'work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py');sup=importlib.util.module_from_spec(sup_spec);sup_spec.loader.exec_module(sup);group=sup.members(s['pid']);require(group==[],'Fresh owned group still exists')
    outputs={str(q.relative_to(H)):dict(bytes=q.stat().st_size,sha256=sha(q))for folder in ['render-001','execution-001']for q in sorted((H/folder).iterdir())}
    previous=R/'work/carrier-functional-law-candidate-image-preparation-003';identical={suffix:sha(H/'render-001'/('carrier-functional-law-candidate.'+suffix))==sha(previous/'render-001'/('carrier-functional-law-candidate.'+suffix))for suffix in ['png','svg','pdf']}
    return dict(schema='actual-functional-law-candidate-STL-render-terminal-1',status='closed_actual_RC0_complete_actual_STL_two_panel_figure_no_engineering_admission',collector_sha256=sha(__file__),actual_owned_handle=32423,actual_initial_chunk='dbf2ee',actual_terminal_chunk='c89c5e',actual_tool_returncode=0,actual_child_returncode=0,actual_supervisor_wall_seconds=s['elapsed_seconds'],actual_render_wall_seconds=receipt['wall_seconds'],actual_render_CPU_seconds=receipt['CPU_seconds'],actual_render_maxRSS_bytes=receipt['maxRSS_bytes'],direct_child_reaped=True,owned_PID=s['pid'],fresh_group_members=group,timeout=False,signals=[],cleanup_error=None,source_sha256=sha(H/'figure.py'),plan_sha256=sha(H/'plan.json'),launch_plan_sha256=sha(H/'launch-plan.json'),command_sha256=sha(H/'command.json'),arming_sha256=sha(H/'arming-assessment.json'),supervision_sha256=sha(H/'execution-001/execution-receipt.json'),render_receipt_sha256=sha(H/'render-001/render-receipt.json'),whole_output_files=outputs,current_merged_pins=5291,whole_before_after_current_maps_equal=True,whole_three_pending_object_and_byte_inverses=inverse,whole_runtime_origin_diagnostic=diagnostic,whole_current_imported_runtime_sha256={n:canonical[n] for n in loaded},all5259_runtime_files_unchanged=True,complete_triangle_count=637850,local_selected_triangle_count=receipt['local_selected_triangle_count'],native_mass_kg=receipt['native_mass_kg'],whole_source_physical_edge431=receipt['source_physical_edge431'],previous003_partial_export_byte_equal_observation=identical,original002_and003_refusals_preserved=True,native_geometry_mesh_FEA_calls=0,engineering_qualification_transferred=False,actual_visual_review='PENDING_ROOT',PDF_raster_review='PENDING_ROOT',elapsed_collection_seconds=time.monotonic()-started)

if __name__=='__main__':
    result=collect()
    with(H/'render-terminal-collection-001.json').open('x')as stream:json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({key:result[key]for key in ['status','actual_tool_returncode','current_merged_pins','complete_triangle_count','local_selected_triangle_count']}))
