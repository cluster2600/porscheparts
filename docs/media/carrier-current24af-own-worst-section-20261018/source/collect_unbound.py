"""Read-only actual R1 common-peak native collector; no native imports."""
import copy
import hashlib
import importlib.util
import json
import math
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[1]
EXPECTED = None  # Genuine tool tuple and marker chunk only after this invocation is reaped.

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
    return digest.hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()

def relative(path):
    return str(path.relative_to(R))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def stable(path):
    assert path.is_file() and not path.is_symlink()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        assert stat.S_ISREG(before.st_mode)
        key = lambda row: [row.st_dev, row.st_ino, row.st_mode, row.st_size, row.st_mtime_ns, row.st_ctime_ns]
        assert key(before) == key(path.lstat())
        digest = hashlib.sha256()
        count = 0
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
            count += len(block)
        assert key(before) == key(os.fstat(stream.fileno())) == key(path.lstat()) and count == before.st_size
    return dict(bytes=count, sha256=digest.hexdigest(), identity=key(before))

def assert_inverse(role):
    pp, pl, pc = (H / f'pending-{name}.json' for name in ('plan', 'launch-plan', 'command'))
    ap, al, ac = (H / f'{name}.json' for name in ('plan', 'launch-plan', 'command'))
    p, l, c = read(ap), read(al), read(ac)
    go = p['root_GO']
    assert sha(R / go) == p['root_GO_sha256'] == l['root_GO_sha256'] == c['root_GO_sha256']
    assert p['launch_ready'] is l['launch_ready'] is c['launch_ready'] is True
    bp = copy.deepcopy(p)
    bp.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    del bp['files_sha256'][go]
    bl = copy.deepcopy(l)
    bl.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    bl['command'][6:8] = [str(pp), sha(pp)]
    del bl['inputs_sha256'][go]
    bl['inputs_sha256'] = {relative(pp) if key == relative(ap) else key: sha(pp) if key == relative(ap) else value for key, value in bl['inputs_sha256'].items()}
    bc = copy.deepcopy(c)
    bc.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    bc['argv'][4], bc['argv'][6] = str(pl), sha(pl)
    for back, pending in ((bp, pp), (bl, pl), (bc, pc)):
        assert back == read(pending) and encoded(back) == pending.read_bytes()
    assert l['command'][6:8] == [str(ap), sha(ap)]
    assert c['argv'][4] == str(al) and c['argv'][6] == sha(al)
    return p, l, c

def collect():
    assert EXPECTED is not None and set(EXPECTED)=={'handle','initial','terminal','pid','marker_chunk'}, 'UNBOUND: genuine reaped authoring tuple required'
    began=time.monotonic();p,launch,command=assert_inverse('actual_common');output,execution=R/p['output_directory'],R/p['execution_directory']
    assert {q.name for q in output.iterdir()}=={'carrier-current24af-own-worst-section.png','carrier-current24af-own-worst-section.svg','carrier-current24af-own-worst-section.pdf','render-receipt.json'}
    assert {q.name for q in execution.iterdir()}=={'started.json','stdout.log','stderr.log','execution-receipt.json'}
    a=read(output/'render-receipt.json');s=read(execution/'execution-receipt.json');started=read(execution/'started.json');tool=read(H/'actual-tool-terminal.json')
    assert tool['actual_tool_handle']==EXPECTED['handle'] and tool['initial_chunk']==EXPECTED['initial']and tool['terminal_chunk']==EXPECTED['terminal']and tool['actual_tool_returncode']==0 and tool['own_handle_collected']
    assert tool['actual_stdout']=={k:s[k]for k in ['status','actual_returncode','no_non_zombie_group_members','elapsed_seconds']}
    pins={**launch['source_sha256'],**launch['inputs_sha256']};fd={n:stable((R/n).resolve(strict=True))for n in pins};assert {n:v['sha256']for n,v in fd.items()}==pins==s['sources_before']==s['sources_after']
    assert s['status']=='executed'and s['actual_returncode']==0 and s['direct_child_reaped']and s['no_non_zombie_group_members']and s['sources_and_plan_unchanged']
    assert s['final_group_members']==s['residual_members_before_cleanup']==s['signals_to_owned_group_only']==[]and s['failure']is s['cleanup_error']is None and s['timeout']is s['interrupted']is False
    assert s['total_wall_budget_seconds']==180 and s['cleanup_grace_seconds']==[10,10]and s['plan_sha256']==started['plan_sha256']==sha(H/'launch-plan.json')and s['command']==launch['command']and s['cwd']==command['cwd']==str(R)
    assert s['pid']==started['pid']==started['pgid']==EXPECTED['pid']
    queries={}
    for label,selector in [('PID','-p'),('PGID','-g')]:
        argv=['/bin/ps',selector,str(EXPECTED['pid']),'-o','pid=,ppid=,pgid=,stat='];q=subprocess.run(argv,capture_output=True,text=True,timeout=2);assert q.returncode==1 and q.stdout==q.stderr=='';queries[label]=dict(argv=argv,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr)
    assert all(sha(execution/name)==digest for name,digest in s['logs_sha256'].items())
    m=load('_actual_R1_draw_pure_checks',H/'render.py');data,native,owner=m.closed_data(p);assert a['source_sha256']==sha(H/'render.py')and a['section_ROOT_sha256']==p['section_ROOT_sha256']and a['observation_ROOT_sha256']==p['observation_ROOT_sha256']
    assert a['status']=='actual_current24af_own_worst_section_and_explicit_projected_chords_rendered_no_admission'and a['actual_peak_xyz_mm']==native['case_peak']['reference_undeformed_IP_xyz_mm']
    pairs,unresolved=m.reciprocal_pairs(native)
    assert a['normal_chords']==[chord for pair in pairs for chord in pair]and a['reciprocal_pairs']==pairs and a['actual_IP_unresolved_rows']==unresolved and a['selected_case']==p['selected_case']and len(pairs)==2 and len(unresolved)==4
    assert a['all_qualified_chords_retained']==owner['exact_recomputed_chord_rows']and len(a['all_qualified_chords_retained'])==8 and a['all_unresolved_rows_retained']==owner['retained_null_rows']and len(a['all_unresolved_rows_retained'])==32
    assert a['normal_chords_projected_to_YZ']is True and a['section_thickness_claimed']is a['new_CAD_or_FEA']is a['candidate_qualified']is False
    assert len(a['checks'])==2 and all(row['full_native_edges_submitted']==data['section']['edge_count']==28 and row['sampled_positions_sha256']==data['section']['sampled_positions_sha256']and row['aspect']==1. for row in a['checks'])and[a['checks'][i]['display_crop_only']for i in range(2)]==[False,True]
    coords=[point for edge in data['section']['edges']for point in edge['points_xyz_mm']];assert len(coords)==708
    assert a['checks'][0]['xlim']==[min(q[1]for q in coords),max(q[1]for q in coords)]and a['checks'][0]['ylim']==[min(q[2]for q in coords),max(q[2]for q in coords)]
    lo,hi=read(R/p['global_peak_file'])['all_global_maximum_ties'][0]['corner_measure']['bounds_mm'];assert a['checks'][1]['xlim']==[lo[1],hi[1]]and a['checks'][1]['ylim']==[lo[2],hi[2]]
    assert a['runtime_files_sha256']==p['runtime_sha256']and all(sha(R/n)==v for n,v in p['runtime_sha256'].items())
    exports={q.name:stable(q)for q in sorted(output.iterdir())if q.suffix in ['.png','.svg','.pdf']};assert {n:v['sha256']for n,v in exports.items()}==a['outputs_sha256']and len(exports)==3
    marker=read(H/'official-PDF-marker.json');assert marker['executed_exactly_once']and marker['tool_result']['exit_code']==0 and marker['tool_result']['chunk_id']==EXPECTED['marker_chunk']and marker['immediately_before_authoring_initial_chunk']==EXPECTED['initial']and marker['authoring_handle']==EXPECTED['handle']
    qa=read(H/'pdf-QA-001.json');visual=read(H/'local-visual-review-001.json');assert qa['PDF_sha256']==sha(output/'carrier-current24af-own-worst-section.pdf')and qa['returncode']==qa['pdfinfo_returncode']==0 and sha(R/qa['PNG_path'])==qa['PNG_sha256']==visual['PDF_raster_sha256']
    assert visual['status']=='actual_PNG_and_Poppler_PDF_page_viewed_PASS'and visual['PNG_sha256']==sha(output/'carrier-current24af-own-worst-section.png')and visual['PDF_sha256']==qa['PDF_sha256']
    files=[*output.iterdir(),*execution.iterdir(),H/'official-PDF-marker.json',H/'pdf-QA-001.json',H/'local-visual-review-001.json'];outputs={relative(q):stable(q)for q in sorted(files)};controls={n:stable(H/n)for n in ['plan.json','launch-plan.json','command.json','pending-plan.json','pending-launch-plan.json','pending-command.json']}
    return dict(schema='owned-actual-current24af-own-worst-section-projected-chord-figure-terminal-1',status='closed_actual_RC0_three_exports_explicit_projected_3D_chords_local_visual_QA_PASS_no_publication',actual_tool=tool,actual_child_returncode=0,pid=EXPECTED['pid'],pgid=EXPECTED['pid'],direct_child_reaped=True,owned_group_empty=True,fresh_PID_and_PGID_absent=True,fresh_process_queries=queries,root_GO_sha256=sha(H/'root-GO-001.json'),current_merged_pins=pins,merged_pins=len(pins),all_resolved_input_FD_identities=fd,all_six_control_FD_identities=controls,three_whole_pending_object_and_stored_byte_inverses=True,render_receipt_sha256=sha(output/'render-receipt.json'),all_outputs=outputs,output_file_count=len(outputs),exports=exports,whole_render_checks=a['checks'],all8_qualified_chords_and32_unresolved_rows_retained=True,all4_IP_chords_and4_local_NULL_rows_retained=True,whole_projected_chords=a['normal_chords'],actual_peak_xyz_mm=a['actual_peak_xyz_mm'],normal_chords_are_not_section_thickness=True,actual_runtime_files=len(a['runtime_files_sha256']),runtime_authority_files=len(p['runtime_sha256']),official_marker_exactly_once=True,PNG_and_actual_PDF_raster_viewed=True,PDF_raster_sha256=qa['PNG_sha256'],candidate_qualified=False,new_CAD_FEA_or_publication=False,collector_source_sha256=sha(__file__),collection_elapsed_seconds=time.monotonic()-began)

if __name__=='__main__':
    result=collect();target=H/'terminal-collection-001.json'
    with target.open('xb')as stream:stream.write(encoded(result));stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(status=result['status'],terminal_sha256=sha(target),pins=result['merged_pins'],outputs=result['output_file_count'],runtime=result['actual_runtime_files'])))

