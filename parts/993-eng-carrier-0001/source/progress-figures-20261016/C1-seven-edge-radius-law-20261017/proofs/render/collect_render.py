"""Read-only closure of the actual scalar-law plot; no plotting or native import."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,stat,struct,subprocess,sys
import xml.etree.ElementTree as ET
H=Path(__file__).resolve().parent;R=H.parents[1]
def require(ok,message):
    if not ok:raise ValueError(message)
def enc(v):return(json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def inspect(q):
    require(not q.is_symlink(),'Symlink file')
    with q.open('rb')as f:
        s=os.fstat(f.fileno());ident=lambda x:[x.st_dev,x.st_ino,x.st_mode,x.st_size,x.st_mtime_ns,x.st_ctime_ns]
        require(stat.S_ISREG(s.st_mode)and ident(s)==ident(q.lstat()),'Regular stable FD/path required');h=hashlib.sha256();n=0
        for b in iter(lambda:f.read(1024**2),b''):h.update(b);n+=len(b)
        require(n==s.st_size and ident(s)==ident(os.fstat(f.fileno()))==ident(q.lstat()),'File changed during read')
    return dict(bytes=n,sha256=h.hexdigest(),identity=ident(s))
def read(q):q.stat();return json.loads(q.read_bytes())
p=read(H/'plan.json');l=read(H/'launch-plan.json');c=read(H/'command.json');a=read(H/'arming-assessment.json')
require(inspect(H/'root-render-GO-001.json')['sha256']=='0b08a1aec8e6df00a320b477072b622c01419100a8f2a3536635b6e663bf4acc'==p['root_GO_sha256']==l['root_GO_sha256']==c['root_GO_sha256'],'Actual ROOT render GO differs')
oldp=read(H/'pending-plan.json');oldl=read(H/'pending-launch.json');oldc=read(H/'pending-command.json');pi=copy.deepcopy(p);del pi['files_sha256'][p['root_GO']]
for key in['status','launch_ready','root_GO','root_GO_sha256']:pi[key]=oldp[key]
require(enc(pi)==(H/'pending-plan.json').read_bytes(),'Whole original pending plan bytes inverse differs')
li=copy.deepcopy(l);del li['inputs_sha256'][l['root_GO']];del li['inputs_sha256'][str((H/'plan.json').relative_to(R))];li['inputs_sha256'][str((H/'pending-plan.json').relative_to(R))]=inspect(H/'pending-plan.json')['sha256'];li['command'][5]=oldl['command'][5]
for key in['status','launch_ready','root_GO','root_GO_sha256']:li[key]=oldl[key]
require(enc(li)==(H/'pending-launch.json').read_bytes(),'Whole original pending launch bytes inverse differs')
ci=copy.deepcopy(c);ci['argv'][6]=oldc['argv'][6]
for key in['status','launch_ready','root_GO','root_GO_sha256']:ci[key]=oldc[key]
require(enc(ci)==(H/'pending-command.json').read_bytes(),'Whole original pending command bytes inverse differs')
ph=inspect(H/'plan.json')['sha256'];lh=inspect(H/'launch-plan.json')['sha256'];require(ph==a['armed_plan_sha256']==l['command'][5]and lh==a['armed_launch_sha256']==c['argv'][6]and inspect(H/'command.json')['sha256']==a['armed_command_sha256'],'Actual armed plan/command SHA binding differs')
sp=importlib.util.spec_from_file_location('_closed_scalar_law_figure_source',H/'figure.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
checked,data,requested,proof=m.verify(H/'plan.json',ph,True);require(checked==p,'Whole current plan differs')
e=R/l['execution_directory'];out=R/p['output_directory'];s=read(e/'execution-receipt.json');started=read(e/'started.json');rr=read(out/'render-receipt.json');merged={**l['inputs_sha256'],**l['source_sha256']}
require(s['status']=='executed'and s['actual_returncode']==0 and s['direct_child_reaped']is True and s['no_non_zombie_group_members']is True and s['final_group_members']==[],'Actual plot process is not closed RC0/reaped/empty')
require(s['failure']is None and s['cleanup_error']is None and s['timeout']is False and s['interrupted']is False and s['signals_to_owned_group_only']==[],'Actual plot interruption/cleanup differs')
require(s['sources_before']==s['sources_after']==merged and s['sources_and_plan_unchanged']is True and s['plan_sha256']==lh and s['command']==l['command'],'Whole supervisor actual source maps/command differ')
require(started['pid']==started['pgid']==s['pid']and started['plan_sha256']==lh,'Actual owned plot identity differs')
require(l['command'][0]=='/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10'and l['command'][1]=='-B'and'-I'not in l['command']and l['total_wall_budget_seconds']==180 and l['cleanup_grace_seconds']==[10,10],'Original interpreter/supervisor route differs')
require(rr['schema']=='closed-seven-edge-law-render-1'and rr['status']=='actual_closed_law_data_scalar_plot_no_native_or_qualification'and rr['plan_sha256']==ph and rr['source_sha256']==inspect(H/'figure.py')['sha256'],'Actual render receipt context differs')
require(rr['files_sha256']==p['files_sha256']and rr['runtime_sha256']==p['runtime_sha256']and set(rr['runtime_imported_files'])<=set(p['runtime_sha256']),'Whole render inputs/runtime differ')
require(rr['full_fraction_proof']==proof and rr['requested_native_coefficients']==requested and rr['whole_exact_proof_recomputed_equal']is True and rr['whole_physical_edges']==[431,293,292,291,290,289,161],'Whole native-law/physical-domain proof differs')
require(rr['visual_samples_per_native_knot_span']==81 and rr['sampled_curve_is_not_the_proof']is True and rr['stock_post_Build_curve']is None and rr['native_CAD_mesh_or_FEA_calls']==0 and rr['candidate_qualified']is False,'Sampling/native/qualification scope differs')
require(rr['downstream_geometry_gates']=='PENDING'and rr['downstream_geometry_gate_status_scope']=='historical_at_the_law_observation'and rr['cwd']=='/','Historical observer scope/cwd differs')
for name,h in s['logs_sha256'].items():require(inspect(e/name)['sha256']==h,'Whole plot log differs')
require((e/'stderr.log').read_bytes()==b''and(e/'stdout.log').read_bytes()==b'','Unexpected renderer stdout/stderr')
export_names={'carrier-seven-edge-radius-law.png','carrier-seven-edge-radius-law.svg','carrier-seven-edge-radius-law.pdf'};require(set(rr['outputs_sha256'])==export_names and{q.name for q in out.iterdir()}==export_names|{'render-receipt.json'},'Exact render output pathset differs')
for n,h in rr['outputs_sha256'].items():require(inspect(out/n)['sha256']==h,'Whole retained export bytes differ')
png=(out/'carrier-seven-edge-radius-law.png').read_bytes();require(png[:8]==b'\x89PNG\r\n\x1a\n'and struct.unpack('>II',png[16:24])==(2610,1890),'PNG signature/dimensions differ')
svg=''.join(ET.fromstring((out/'carrier-seven-edge-radius-law.svg').read_bytes()).itertext());require('At the law observation, geometry gates were pending'in svg and'No post-Build curve or raw Solid is fabricated'in svg and'Curves are sampled visuals'in svg,'English snapshot/proof/stock SVG labels missing')
pdf=(out/'carrier-seven-edge-radius-law.pdf').read_bytes();require(pdf.startswith(b'%PDF-')and b'/FontFile2'in pdf,'PDF header/embedded TrueType font missing')
current={n:inspect(R/n)['sha256']for n in merged};require(current==merged,'Current whole input/source/runtime pins differ')
runtime={n:current[n]for n in p['runtime_sha256']};require(runtime==rr['runtime_sha256'],'Whole plot runtime changed')
fresh=subprocess.run(['/bin/ps','-g',str(s['pid']),'-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);require(fresh.returncode==1 and not fresh.stdout.strip()and not fresh.stderr.strip(),'Owned plot group is not freshly absent')
require(not any(n.split('.')[0]in['numpy','matplotlib','PIL','OCP','build123d','gmsh']for n in sys.modules),'Collector imported plotting or native libraries')
outputs={str(q.relative_to(H)):inspect(q)for folder in[out,e]for q in sorted(folder.iterdir())if q.is_file()};require(len(outputs)==8,'Expected four exports/receipt plus four execution files')
report=dict(schema='closed-seven-edge-scalar-law-render-owner-terminal-1',status='closed_actual_RC0_three_scalar_exports_complete_exact_proof_retained_no_qualification',actual_owned_handle=51553,actual_initial_tool_chunk='d682c9',actual_terminal_tool_chunk='4ec1b2',actual_tool_returncode=0,actual_child_returncode=s['actual_returncode'],actual_pid=s['pid'],actual_supervisor_elapsed_seconds=s['elapsed_seconds'],direct_child_reaped=True,fresh_owned_group_absent=True,whole_three_pending_original_byte_inverses=True,ROOT_GO_sha256=p['root_GO_sha256'],plan_sha256=ph,launch_sha256=lh,supervision_sha256=inspect(e/'execution-receipt.json')['sha256'],render_receipt_sha256=inspect(out/'render-receipt.json')['sha256'],current_all_pin_count=len(current),current_pins_sha256=current,all219_runtime_files_current_equal=True,actual_loaded_runtime_files=rr['runtime_imported_files'],whole_full_Fraction_proof_equal=True,whole_requested_native_coefficients=requested,whole_seven_actual_law_records_and_intervals=proof['edges'],stock_RC1_no_invented_post_Build_curve=True,patched_RC0_law_PASS_only=True,native_HasResultFalse_preserved=True,geometry_gate_fields_are_historical_snapshot=True,whole_outputs=outputs,PNG_signature_dimensions=[2610,1890],SVG_English_snapshot_proof_stock_labels_present=True,PDF_header_and_TrueType_font_checked=True,PDF_raster_view_performed=False,ROOT_independent_PNG_view_pending=True,collector_source_sha256=inspect(Path(__file__))['sha256'],collector_plot_CAD_mesh_or_FEA_calls=0,publication_or_tracked_document_mutation=False)
with(H/'render-terminal-collection-001.json').open('xb')as f:
    f.write(enc(report));f.flush();os.fsync(f.fileno())
print(json.dumps(dict(status=report['status'],terminal_sha256=inspect(H/'render-terminal-collection-001.json')['sha256'],actual_pid=s['pid'],actual_returncode=0,whole_outputs=len(outputs),current_pins=len(current),PNG=str(out/'carrier-seven-edge-radius-law.png'))))
