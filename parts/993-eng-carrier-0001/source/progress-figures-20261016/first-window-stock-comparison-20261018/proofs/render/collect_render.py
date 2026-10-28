"""Read-only complete owned Figure32 output, runtime, marker and cleanup collection."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import time
import xml.etree.ElementTree as ET

H=Path(__file__).resolve().parent;R=H.parents[1]
GO='cbfb072c989da2c9fac3fd26ec25a0d2b0ca801668bf4ea3ba4f6e25aa5e55b0'
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''): digest.update(block)
    return digest.hexdigest()
def read(path): return json.loads(path.read_bytes())
def encoded(x):return(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def rel(path): return str(path.relative_to(R))
def absent(flag, pid):
    result = subprocess.run(['/bin/ps', flag, str(pid), '-o', 'pid=,ppid=,pgid=,stat='], capture_output=True, text=True, timeout=2)
    assert result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip()
    return True
def whole_outputs(output, execution):
    rows = {}
    for directory in (output, execution):
        for path in sorted(directory.rglob('*')):
            assert not path.is_symlink()
            if not path.is_file(): continue
            before = path.stat(); digest = sha(path); after = path.stat()
            assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            rows[rel(path)] = dict(sha256=digest, bytes=after.st_size)
    return rows


def inverses():
    names=['pending-plan.json','pending-launch-plan.json','pending-command.json']
    pending=[read(H/n)for n in names];p,l,c=[read(H/n)for n in ['plan.json','launch-plan.json','command.json']]
    go_key=rel(H/'root-render-GO-001.json');assert sha(R/go_key)==GO
    assert all(x['launch_ready']is True and x['root_GO']==go_key and x['root_GO_sha256']==GO for x in [p,l,c])
    a=copy.deepcopy(p);a.update(launch_ready=False,root_GO=None,root_GO_sha256=None);a['files_sha256'].pop(go_key)
    b=copy.deepcopy(l);b.update(launch_ready=False,root_GO=None,root_GO_sha256=None);b['command'][7:9]=[str(H/names[0]),sha(H/names[0])];b['inputs_sha256'].pop(go_key)
    b['inputs_sha256']={rel(H/names[0])if k==rel(H/'plan.json')else k:sha(H/names[0])if k==rel(H/'plan.json')else v for k,v in b['inputs_sha256'].items()}
    d=copy.deepcopy(c);d.update(launch_ready=False,root_GO=None,root_GO_sha256=None);d['argv'][4]=str(H/names[1]);d['argv'][6]=sha(H/names[1])
    assert all(x==old and encoded(x)==(H/n).read_bytes()for n,x,old in zip(names,[a,b,d],pending))
    assert l['command'][7:9]==[str(H/'plan.json'),sha(H/'plan.json')]and c['argv'][4]==str(H/'launch-plan.json')and c['argv'][6]==sha(H/'launch-plan.json')
    return p,l,c


def collect():
    began=time.monotonic();p,l,c=inverses();tool=read(H/'actual-tool-terminal.json');marker=read(H/'official-marker-and-launch.json')
    assert tool['session_id']==47888 and tool['initial_chunk']=='38b22f'and tool['terminal_chunk']=='4626e5'and tool['actual_tool_returncode']==0
    mark=marker['official_marker'];assert mark['actual_invocations']==mark['expected_output_count']==1 and mark['operation_kind']=='create'and mark['output_format']=='pdf'
    assert mark['tool_result']['exit_code']==0 and mark['tool_result']['chunk_id']=='fe6897'and marker['authoring_started_only_after_marker_RC0']
    output,execution=R/p['output_directory'],R/l['execution_directory'];s=read(execution/'execution-receipt.json');started=read(execution/'started.json')
    pins={**l['source_sha256'],**l['inputs_sha256']};assert{n:sha(R/n)for n in pins}==pins==s['sources_before']==s['sources_after']
    assert s['sources_and_plan_unchanged']and s['plan_sha256']==started['plan_sha256']==sha(H/'launch-plan.json')and s['command']==l['command']
    assert s['status']=='executed'and s['actual_returncode']==0 and s['direct_child_reaped']and s['no_non_zombie_group_members']
    assert s['pid']==started['pid']==started['pgid']==18835 and s['final_group_members']==[]and s['residual_members_before_cleanup']==[]
    assert not s['timeout']and not s['interrupted']and s['failure']is s['cleanup_error']is None and s['signals_to_owned_group_only']==[]
    assert s['total_wall_budget_seconds']==180 and s['cleanup_grace_seconds']==[10,10]and absent('-p',18835)and absent('-g',18835)
    for n,digest in s['logs_sha256'].items():assert sha(execution/n)==digest
    spec=importlib.util.spec_from_file_location('_Figure32_readonly_collector',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    actual,data=m.verify(H/'plan.json',sha(H/'plan.json'),rendering=True);assert actual==p
    r=read(output/'render-receipt.json');diag=read(output/'runtime-origin-diagnostic.json')
    assert r['schema']=='actual-two-STL-first-window-stock-comparison-render-1'and r['status']=='display_only_six_panels_complete_STLs_common_framing'
    assert r['plan_sha256']==sha(H/'plan.json')and r['source_sha256']==sha(H/'figure.py')and r['cases']==data['cases']and r['display_boxes']==data['display_boxes']
    assert r['all_faces_retained_in_overviews']and r['framing_vertices_are_only_actual_vertices_from_both_inputs']
    assert r['overview_pixel_shapes']==[[281,1878,4],[281,1878,4]]and r['native_mass_difference_g']==data['native_mass_difference_g']
    assert not r['geometry_modified']and r['native_calls']==0 and not r['old_FEA_transferred']and not r['engineering_qualification_transferred']
    assert [(x['case'],x['X_side'])for x in r['closeups']]==[(0,-1),(0,1),(1,-1),(1,1)]
    for row in r['closeups']:
        assert row['selected_triangles']>0 and row['XY_mm']==next(b['XY_mm']for b in data['display_boxes']if b['X_side']==row['X_side'])
    for name,case in zip(p['STLs'],data['cases']):
        path=R/name
        with path.open('rb')as f:header=f.read(84)
        assert struct.unpack('<I',header[80:84])[0]==case['STL_triangles']and path.stat().st_size==84+50*case['STL_triangles']
    runtime={str((R/n).resolve()):h for n,h in p['runtime_sha256'].items()};loaded=set(r['runtime_imported_files'])
    assert len(runtime)==5259 and len(loaded)==598 and loaded<=set(runtime)
    assert diag['runtime_imported_files']==r['runtime_imported_files']and diag['outside_runtime_imported_files']==[]and diag['declared_runtime_file_count']==5259
    assert set(r['exports_sha256'])=={f.name for f in output.iterdir()if f.is_file()}-{'render-receipt.json'}
    for n,digest in r['exports_sha256'].items():assert sha(output/n)==digest
    start=read(output/'render-started.json');pngready=read(output/'PNG-ready.json')
    assert start['status']=='MARKER_BEFORE_IMAGE_AUTHORING'and start['plan_sha256']==sha(H/'plan.json')and start['STLs']==p['STLs']
    assert pngready['status']=='PNG_WRITTEN_BEFORE_VECTOR_EXPORTS'and pngready['sha256']==sha(output/'carrier-first-window-stock-comparison.png')
    assert(output/'render-started.json').stat().st_mtime_ns<(output/'carrier-first-window-stock-comparison.png').stat().st_mtime_ns<=(output/'PNG-ready.json').stat().st_mtime_ns
    assert(output/'PNG-ready.json').stat().st_mtime_ns<(output/'carrier-first-window-stock-comparison.svg').stat().st_mtime_ns<(output/'carrier-first-window-stock-comparison.pdf').stat().st_mtime_ns
    ET.parse(output/'carrier-first-window-stock-comparison.svg')
    qa=read(H/'visual-QA-observation.json');assert qa['PNG_viewed']and qa['PDF_page_raster_viewed']and qa['pdfinfo']['exit_code']==qa['pdffonts']['exit_code']==0
    assert qa['pdf_raster_terminal']['exit_code']==0 and(H/'pdf-qa-001.png').is_file()
    outputs=whole_outputs(output,execution)
    return dict(schema='owned-Figure32-two-STL-comparison-render-terminal-1',status='closed_actual_RC0_Figure32_PNG_SVG_PDF_display_only',
        actual_tool=tool,actual_child_returncode=0,pid=18835,pgid=18835,direct_child_reaped=True,owned_group_empty=True,fresh_PID_and_PGID_absent=True,
        ROOT_GO_sha256=GO,official_PDF_marker_invoked_once_RC0=True,official_marker_tool_chunk='fe6897',official_marker_receipt_sha256=sha(H/'official-marker-and-launch.json'),
        render_receipt_sha256=sha(output/'render-receipt.json'),supervision_sha256=sha(execution/'execution-receipt.json'),
        all_current5289_pins_and_sources_before_after_equal=True,three_whole_pending_object_and_stored_byte_inverses=True,
        all_outputs=outputs,output_count=len(outputs),complete_cases=data['cases'],display_boxes=data['display_boxes'],closeup_rows=r['closeups'],
        overview_pixel_shapes=r['overview_pixel_shapes'],all_overview_faces_retained=True,loaded_runtime_files=sorted(loaded),declared_runtime_files=5259,
        exports_sha256={n:sha(output/n)for n in ['carrier-first-window-stock-comparison.png','carrier-first-window-stock-comparison.svg','carrier-first-window-stock-comparison.pdf']},
        agent_PNG_and_PDF_visual_QA_sha256=sha(H/'visual-QA-observation.json'),PDF_QA_raster_sha256=sha(H/'pdf-qa-001.png'),ROOT_visual_QA_claimed=False,
        timeout=False,signals=[],cleanup_error=None,supervised_elapsed_seconds=s['elapsed_seconds'],native_calls=0,publication_executed=False,
        old_FEA_transferred=False,engineering_qualification_transferred=False,collection_elapsed_seconds=time.monotonic()-began)


if __name__=='__main__':
    result=collect();target=H/'terminal-collection.json'
    with target.open('xb')as f:f.write(encoded(result));f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(status=result['status'],terminal_sha256=sha(target),outputs=result['output_count'],runtime_loaded=len(result['loaded_runtime_files']),actual_child_returncode=0)))
