"""Prepare a separate 32-state CCX input and provenance; never calls a solver."""
import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import uuid

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=ROOT/'work/carrier-design-20261016/luo-flat1-verified-nlgeom-unload-mesh9'
DESIGN=ROOT/'parts/993-eng-carrier-0001/source/design-20261016'
SIMULATE=ROOT/'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def prepare():
    case=HERE/'case';case.mkdir(exist_ok=False)
    old_runtime=json.loads((BASE/'runtime.json').read_text());old_plan=json.loads((BASE/'plan.json').read_text())
    name=old_runtime['name'];old_deck=BASE/(name+'.inp')
    if sha(old_deck)!=old_runtime['input_sha256'] or sha(BASE/'mesh.inp')!=old_runtime['mesh_sha256']:
        raise ValueError('Retained input binding differs')
    old=old_deck.read_bytes();expected=b'*STATIC,SOLVER=SPOOLES\n0.125,1,0.001,0.125\n'
    if old.count(expected)!=2:raise ValueError('Unexpected retained static-step records')
    new=old.replace(expected,b'*STATIC,SOLVER=SPOOLES\n0.0625,1,0.001,0.0625\n')
    (case/(name+'.inp')).write_bytes(new)
    copies=['mesh.inp','mesh.npz','mesh.json','material-curve.inp','material-provenance.json','material-DATA_LICENSE.json']
    for n in copies:shutil.copyfile(BASE/n,case/n)
    plan=json.loads(json.dumps(old_plan));plan['frozen_at_UTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for key in ['step','unload_step']:
        plan[key]['initial_increment']=0.0625;plan[key]['maximum_increment']=0.0625
    plan['step']['timeout_seconds']=3600
    write(case/'plan.json',plan)
    (HERE/'deck.diff').write_text(''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile='retained/combined-spring-1000-luo-flat1-NLGEOM.inp',tofile='prepared/combined-spring-1000-luo-flat1-NLGEOM.inp')))
    (HERE/'plan.diff').write_text(''.join(difflib.unified_diff((BASE/'plan.json').read_text().splitlines(True),(case/'plan.json').read_text().splitlines(True),fromfile='retained/plan.json',tofile='prepared/plan.json')))
    # The one changed executable-function line is a resource bound, not mathematics.
    original=SIMULATE.read_text();tree=ast.parse(original)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    function=ast.get_source_segment(original,node)+'\n'
    if function.count('assert 1 <= timeout_seconds <= 1800')!=1:raise ValueError('Unexpected original execution bound')
    refined=function.replace('assert 1 <= timeout_seconds <= 1800','assert 1 <= timeout_seconds <= 3600',1)
    header='''"""Isolated future Docker execute helper, derived from the retained helper.

No container is created and no execution happens on import. A future approved
private caller must set CONTAINER to its newly owned container, as in the
original runner. Only the upper timeout assertion differs in execute().
"""
import subprocess
import time
DOCKER='/usr/local/bin/docker'
CONTAINER=None

'''
    (HERE/'execute_3600.py').write_text(header+refined)
    ast.parse((HERE/'execute_3600.py').read_text())
    (HERE/'execute-function.diff').write_text(''.join(difflib.unified_diff(function.splitlines(True),refined.splitlines(True),fromfile='retained_simulate.execute',tofile='isolated_execute_3600.execute')))
    container='carrier-ener-convergence-'+uuid.uuid4().hex[:12]
    execution=dict(schema='ener-increment-convergence-preparation-1',status='prepared_not_executed',execution_authorized=False,
        choice='Complete two-step cycle; nominal 16 loading and 16 unloading states; no amplitude card or force scaling added.',
        baseline_folder=str(BASE),baseline_runtime_sha256=sha(BASE/'runtime.json'),baseline_plan_sha256=sha(BASE/'plan.json'),
        retained_version='CalculiX 2.21 / Debian package calculix-ccx 2.21-1',
        retained_runner={'path':str(DESIGN/'run_plastic900.py'),'sha256':sha(DESIGN/'run_plastic900.py')},
        retained_execution_helper={'path':str(SIMULATE),'sha256':sha(SIMULATE)},
        image=old_runtime['image'],ccx_binary_sha256=old_runtime['ccx_binary_sha256'],
        retained_container=old_runtime['container'],retained_owned_container_removed=old_runtime['owned_container_removed'],
        retained_solver_seconds=old_runtime['seconds'],retained_coupon_seconds=old_runtime['coupon']['seconds'],
        retained_execution_host={'kind':'local Docker controlled through /usr/local/bin/docker','documented_host_platform':'macOS-27.2-arm64-arm-64bit','documented_host_architecture':'arm64','image_operating_system':'Linux','image_architecture':None,'image_architecture_scope':'Not recorded in retained receipts; not inspected or guessed during this preparation.'},
        proposed_execution_host={'preferred':'Kali1 native CCX','status':'unverified_no_retained_CCX_runtime_attestation','native_binary_path':None,'local_Docker_fallback':'prepared only; not selected and not launched'},
        resources={'cpus':1,'memory_GiB':6,'swap_GiB':0,'network':'none','pids_limit':128,'timeout_seconds':3600,'threads':{'OMP_NUM_THREADS':'1','CCX_NPROC_RESULTS':'1','OPENBLAS_NUM_THREADS':'1'}},
        prepared_case=str(case),prepared_deck_sha256=sha(case/(name+'.inp')),prepared_plan_sha256=sha(case/'plan.json'),
        expected_thresholds={'ENER_relative_to_gross':0.001,'Piola_relative_to_gross':0.0001,'maximum_measured_PEEQ':old_plan['plasticity']['maximum_measured_equivalent_plastic_strain']},
        parser_scope={'analyze_plastic900':'Loops over all sorted states; load factor t for loading and 2-t for unloading; no fixed sixteen-state limit.','audit_finite_work':'Loops over all sorted states with the same force-factor convention; no fixed sixteen-state limit.','historical_bind_carrier_constitutive_evidence':'Hard-coded sixteen-state binding remains unchanged and must not be used to promote this experiment.'},
        proposed_new_Docker_container_name=container,
        historical_container_creation_argv=['/usr/local/bin/docker','run','-d','--name',old_runtime['container'],'--network','none','--cpus','1','--memory','6g','--memory-swap','6g','--pids-limit','128','--tmpfs','/tmp:rw,size=512m','--entrypoint','/bin/sleep',old_runtime['image'],'infinity'],
        historical_solver_argv=['/usr/local/bin/docker','exec','-w','/study/'+BASE.parent.name+'/'+BASE.name,'-e','OMP_NUM_THREADS=1','-e','CCX_NPROC_RESULTS=1','-e','OPENBLAS_NUM_THREADS=1',old_runtime['container'],'timeout','1800','ccx','-i',name],
        proposed_Docker_solver_argv_if_fallback_later_approved=['/usr/local/bin/docker','exec','-w','/study/'+HERE.name+'/case','-e','OMP_NUM_THREADS=1','-e','CCX_NPROC_RESULTS=1','-e','OPENBLAS_NUM_THREADS=1',container,'timeout','3600','ccx','-i',name],
        future_runtime_preconditions=['Root review and explicit execution decision.','Choose and attest host, architecture, binary, libraries and isolation before execution.','For Docker fallback: new owned container, pinned image and binary SHA; use isolated execute_3600 helper, never the old helper with a 3600 argument.','Do not use the removed historical container or any current regional generator/watchers.'],
        numerical_interpretation='Refinement may improve the ENER diagnostic; success is not presumed. Keep all failed states and compare like load factors, residual displacement and PEEQ. No material allowable or global admission follows.')
    write(HERE/'execution-plan.json',execution)
    files=[HERE/'prepare.py',HERE/'verify.py',HERE/'execute_3600.py',HERE/'README.md',HERE/'deck.diff',HERE/'plan.diff',HERE/'execute-function.diff',HERE/'execution-plan.json',*case.iterdir(),
        BASE/'runtime.json',BASE/'plan.json',old_deck,BASE/'source-snapshot.py',BASE/'combined-spring-1000-luo-flat1-NLGEOM.sta',*[(BASE/n) for n in copies],
        DESIGN/'run_plastic900.py',SIMULATE,DESIGN/'analyze_plastic900.py',DESIGN/'audit_finite_work.py',DESIGN/'ccx_curve_reference.py',
        DESIGN/'constitutive-evidence/luo-flat1-analysis.json',DESIGN/'constitutive-evidence/luo-flat1-finite-work.json',ROOT/'work/carrier-design-20261016/owned-ccx-runtime.json',ROOT/'work/part-workflow/run-001/cad/simulation-runtime.json']
    write(HERE/'preparation-manifest.json',{'schema':'ener-refinement-input-manifest-1','status':'prepared_no_solver_execution','baseline_folder':str(BASE),'case_name':name,'copied_inputs':copies,'files_sha256':{str(p):sha(p) for p in files}})
    print(json.dumps({'status':'prepared_no_solver_execution','directory':str(HERE),'manifest_sha256':sha(HERE/'preparation-manifest.json'),'deck_sha256':sha(case/(name+'.inp')),'execution_plan_sha256':sha(HERE/'execution-plan.json')}))


if __name__=='__main__':prepare()
