"""Freeze only the saved-stock metadata, sources and pending owned command."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

H=Path(__file__).resolve().parent;R=H.parents[2];W=R/'work/carrier-process-20261017';began=time.monotonic()
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):digest.update(block)
    return digest.hexdigest()
def read(path):return json.loads(path.read_text())
def rel(path):return str(path.relative_to(R))if path.is_relative_to(R)else str(path)
def write(path,value):
    with path.open('x')as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    spec=importlib.util.spec_from_file_location('_saved_stock_metadata_only',H/'admit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    source=m.RECORDS.closed_stock();write(H/'stock-source-assessment.json',dict(status='closed_constructed_stock_records_checked_no_native_revalidation',**source))
    parent=m.RECORDS.PARENT;basis=read(parent/'plan.json');oldlaunch=read(parent/'launch-plan.json')
    p={key:copy.deepcopy(basis[key])for key in ['native_site','baseline_STEP','volume_source','strict_cut_source','minimum_xyz_mm','maximum_xyz_mm','existing_bound_guard_mm']}
    p.update(schema='first-window-stock-native-local-plan-1',launch_ready=False,root_GO=None,root_GO_sha256=None,
        candidate_version='first-window-stock-alone-v1',candidate_BREP=source['candidate_BREP']['path'],candidate_BREP_sha256=source['candidate_BREP']['sha256'],
        study='work/part-workflow/run-001/cad/study.json',volume_observer_source=rel(W/'bounded-webs-BREP-volume-method-diagnostic-preparation-001/compare.py'),
        stock_source_ROOT=rel(parent/'root-terminal-review-001.json'),stock_source_ROOT_sha256=m.RECORDS.ROOT_SHA,
        stock_source_terminal=rel(parent/'terminal-collection.json'),failed_union_used=False,current07b_subset_required=False,old_complete7_law_inherited=False,candidate_qualified=False,
        bounds=dict(outer=600,inner=560,CPU=[520,540],threads=1,workers=0),output_directory=rel(H/'output-001'),execution_directory=rel(H/'execution-001'))
    pins={name:digest for name,digest in basis['files_sha256'].items()if '/runtimes/'in name}
    paths=[H/name for name in ['admit.py','records.py','selfcheck.py','prepare.py','README.md','ARMING.md','stock-source-assessment.json']]
    paths+=[R/p[key]for key in ['candidate_BREP','study','baseline_STEP','volume_source','strict_cut_source','volume_observer_source','stock_source_ROOT','stock_source_terminal']]
    paths+=[R/row['path']for row in source['artifacts'].values()]
    paths+=[parent/name for name in ['trial.py','build_stock.py','normal-builder/cad.py','source-changes.json','plan.json','launch-plan.json','execution-001/execution-receipt.json','output-001/assessment.json','output-001/effective-trial.json']]
    paths+=[parent/'output-001'/row['path']for row in source['actual_window_branch_ledgers'].values()]
    paths+=[W/'bounded-webs-C1-endfillet-preparation-002/close_end.py',W/'source010-exposure-preflight-003/supervise.py']
    for path in paths:pins[rel(path)]=sha(path)
    p['files_sha256']=pins;write(H/'pending-plan.json',p);m.verify(H/'pending-plan.json',sha(H/'pending-plan.json'))
    result=subprocess.run([sys.executable,'-I','-B',str(H/'selfcheck.py')],capture_output=True,text=True,timeout=30)
    for suffix,text in [('stdout',result.stdout),('stderr',result.stderr)]:
        with(H/f'selfcheck.{suffix}.log').open('x')as stream:stream.write(text)
    assert result.returncode==0,result.stderr
    assert not set(sys.modules).intersection({'OCP','build123d','numpy','gmsh'})
    write(H/'preflight.json',dict(status='SOURCE_ONLY_saved_stock_source_bindings_and12_stdlib_tests_PASS',plan_sha256=sha(H/'pending-plan.json'),plan_pins=len(pins),actual_tests_returncode=0,scientific_imports=False,native_executed=False,elapsed_seconds=time.monotonic()-began))
    supervisor=W/'source010-exposure-preflight-003/supervise.py'
    launch={key:copy.deepcopy(value)for key,value in oldlaunch.items()if key not in ['inputs_sha256','source_sha256']}
    launch.update(schema='owned_saved_first_window_stock_pending_1',launch_ready=False,root_GO=None,root_GO_sha256=None,
        command=[oldlaunch['command'][0],'-I','-B',str(H/'admit.py'),'run',str(H/'pending-plan.json'),sha(H/'pending-plan.json')],
        output_directory=p['output_directory'],execution_directory=p['execution_directory'],source_sha256={rel(q):sha(q)for q in [supervisor,H/'admit.py',H/'records.py']},inputs_sha256=dict(pins))
    for path in [H/'pending-plan.json',H/'preflight.json']:launch['inputs_sha256'][rel(path)]=sha(path)
    assert launch['total_wall_budget_seconds']==600 and launch['cleanup_grace_seconds']==[10,10]
    write(H/'pending-launch-plan.json',launch)
    command=dict(schema='pending_saved_first_window_stock_command_1',launch_ready=False,root_GO=None,root_GO_sha256=None,argv=[oldlaunch['command'][0],'-I','-B',str(supervisor),str(H/'pending-launch-plan.json'),'--plan-sha256',sha(H/'pending-launch-plan.json')],cwd=str(R),native_executed=False,parent_not_niced=True)
    write(H/'pending-command.json',command)
    assessment=dict(status='SOURCE_ONLY_saved_stock_independent_local_admission_pending_ROOT_review',candidate_BREP_sha256=p['candidate_BREP_sha256'],sources_sha256={name:sha(H/name)for name in ['admit.py','records.py','selfcheck.py','prepare.py','README.md','ARMING.md']},plan_sha256=sha(H/'pending-plan.json'),launch_sha256=sha(H/'pending-launch-plan.json'),command_sha256=sha(H/'pending-command.json'),preflight_sha256=sha(H/'preflight.json'),plan_pins=len(pins),merged_launch_pins=len({**launch['inputs_sha256'],**launch['source_sha256']}),actual_tests=12,actual_tests_returncode=0,native_executed=False)
    write(H/'preparation-assessment.json',assessment);print(json.dumps(assessment))

if __name__=='__main__':main()
