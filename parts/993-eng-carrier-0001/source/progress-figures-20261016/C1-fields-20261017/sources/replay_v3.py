"""Restore the existing C1 capsule, complete small inputs, replay the frozen field drawing."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import resource
import runpy
import shutil
import signal
import sys
import time

HERE=Path(__file__).resolve().parent

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def relative(value):
    p=PurePosixPath(value)
    require(bool(value)and not p.is_absolute()and p.parts and all(x not in ('','.','..')for x in p.parts)and p.as_posix()==value,'Exact relative path required')
    return Path(*p.parts)
def write(path,value):
    with Path(path).open('x')as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def read(path):return json.loads(Path(path).read_text())
def fresh(path):
    path=Path(path).absolute();require(not path.exists()and not any(p.is_symlink()for p in [path,*path.parents]),'Fresh nonsymlink output required');return path

def copy_one(source_root,target_root,name,expected):
    source=Path(source_root)/relative(name);target=Path(target_root)/relative(name)
    require(source.is_file()and not any(p.is_symlink()for p in [source,*source.parents])and sha(source)==expected,'Mirror source/hash differs')
    require(not target.exists()and not any(p.is_symlink()for p in [target,*target.parents]),'Mirror target collision or symlink')
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb')as a,target.open('xb')as b:shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
    require(sha(source)==sha(target)==expected,'Mirror copy changed')

def rebase(original,new_root):
    result=copy.deepcopy(original);result['source_root']=str(Path(new_root).absolute())
    inverse=copy.deepcopy(result);inverse['source_root']=original['source_root']
    require(inverse==original,'Only source_root may change');return result

def verify_capsule(expected,dependency):
    require(sha(HERE/'manifest-003.json')==expected,'Figure capsule manifest differs');m=read(HERE/'manifest-003.json')
    require(m['schema']=='C1-fields-dependent-replay-capsule-1','Wrong capsule')
    require(all((HERE/relative(n)).is_file()and not(HERE/n).is_symlink()and sha(HERE/n)==h for n,h in m['files_sha256'].items()),'Small capsule payload differs')
    actual={str(p.relative_to(HERE/'payload'))for p in (HERE/'payload').rglob('*')if p.is_file()}
    require(actual==set(m['mirror_files_sha256']),'Unexpected/missing mirror payload')
    dependency=Path(dependency).absolute()
    require(all(not p.is_symlink()for p in [dependency,*dependency.parents]),'Dependency path symlink')
    require(all((dependency/relative(n)).is_file()and not(dependency/n).is_symlink()and sha(dependency/n)==h for n,h in m['dependency']['files_sha256'].items()),'Existing C1 capsule dependency changed')
    require(sha(dependency/'manifest.json')==m['dependency']['manifest_sha256'],'Existing C1 manifest changed')
    figure=read(HERE/'payload'/relative(m['original_figure_plan']))
    require(sha(HERE/'payload'/relative(m['original_figure_plan']))==m['original_figure_plan_sha256'],'Original figure plan changed')
    native=read(dependency/'manifest.json');archived={n:r for a in native['archives'].values()for n,r in a['members'].items()}
    require(len(archived)==m['archive_member_count']==186 and sum(r['bytes']for r in archived.values())==m['expanded_archive_bytes'],'Existing archive scope differs')
    require(all(m['files_sha256'].get('payload/'+n)==h and n not in archived for n,h in m['mirror_files_sha256'].items()),'Mirror differs or would overwrite archived input')
    for name,h in figure['files_sha256'].items():
        if not Path(name).is_absolute():require(m['mirror_files_sha256'].get(name)==h or archived.get(name,{}).get('sha256')==h,'A figure input is absent from both sources')
    require({n:h for n,h in figure['files_sha256'].items()if Path(n).is_absolute()}==figure['runtime_sha256'],'Only existing absolute runtime inputs permitted')
    require(all(Path(n).is_absolute()and sha(n)==h for n,h in figure['runtime_sha256'].items()),'Pinned211 runtime changed')
    require(not(set(m['supplemental_runtime_sha256'])&set(figure['runtime_sha256']))and all(Path(n).is_absolute()and sha(n)==h for n,h in m['supplemental_runtime_sha256'].items()),'Supplemental observed runtime changed')
    return m,figure

def check_imported_runtime(runtime):
    loaded={str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['numpy','matplotlib','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
    require(loaded<=set(runtime),'Late scientific import outside pinned runtime')
    return sorted(loaded)

def run(plan_path,expected):
    started=time.monotonic();plan_path=Path(plan_path).absolute();require(sha(plan_path)==expected,'Replay plan changed');plan=read(plan_path)
    require(plan['launch_ready']is True and plan['root_GO_sha256']is not None,'Replay remains NON-ARMED before restore/import/render')
    require(sha(plan['root_GO'])==plan['root_GO_sha256'],'Actual root replay GO differs')
    require(plan['outer_seconds']==180 and plan['phase_seconds']==150 and plan['workers']==0 and plan['threads']==1,'Unexpected replay bounds')
    require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1'for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']),'Owned nice10/BLAS1 required')
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s restore preparation budget')));signal.setitimer(signal.ITIMER_REAL,150)
    resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    m,original=verify_capsule(plan['capsule_manifest_sha256'],plan['dependency_directory']);output=fresh(plan['output_directory'])
    require(shutil.disk_usage(output.parent).free>=m['expanded_archive_bytes']+m['mirror_bytes']+sum(m['expected_exports_bytes'].values()),'Insufficient space for exact restoration plus drawing')
    output.mkdir();restored=output/'restored';dependency=Path(plan['dependency_directory'])
    spec=importlib.util.spec_from_file_location('_existing_C1_restore',dependency/'restore.py');restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)
    native=restore.restore(restored,m['dependency']['manifest_sha256'])
    require(sum(len(row['members'])for row in native['archives'].values())==m['archive_member_count']==186,'Actual C1 archive member count differs')
    for name,h in m['mirror_files_sha256'].items():copy_one(HERE/'payload',restored,name,h)
    # Exactly the original current plan, with only its source_root rebased to the fresh restored tree.
    rebased=rebase(original,restored);rebased_path=output/'rebased-figure-plan.json';write(rebased_path,rebased)
    require(all(sha(restored/name)==h for name,h in rebased['files_sha256'].items()),'Restored inputs/runtime not identical before drawing')
    require(time.monotonic()-started+95<=150,'Restore exhausted the95s frozen-render reserve')
    old_argv=list(sys.argv);old_cwd=os.getcwd()
    try:
        sys.argv=[str(restored/relative(m['renderer'])), 'render',str(rebased_path),sha(rebased_path),str(output/'render')]
        # Its exact original __main__ sets cwd=/, inner95s and CPU90-91; outer owned180s remains authority.
        runpy.run_path(sys.argv[0],run_name='__main__')
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);sys.argv=old_argv;os.chdir(old_cwd)
    imported_after_exports=check_imported_runtime({**original['runtime_sha256'],**m['supplemental_runtime_sha256']})
    receipt=read(output/'render/render-receipt.json');original_receipt=read(HERE/'payload'/relative(m['original_render_receipt']))
    require(all(sha(output/'render'/name)==h for name,h in m['expected_exports_sha256'].items()),'Portable PNG/SVG/PDF not byteexact002')
    for key in ['checks','global_maxima','camera_basis_U_V_depth','runtime_sha256']:
        require(receipt[key]==original_receipt[key],'Entire scientific/camera/runtime result changed: '+key)
    require(receipt['cwd']=='/'and receipt['FEA_started']is False,'Frozen main context differs')
    require(all(sha(restored/name)==h for name,h in rebased['files_sha256'].items()),'Restored inputs/runtime changed after drawing')
    verify_capsule(plan['capsule_manifest_sha256'],plan['dependency_directory']);require(sha(plan_path)==expected,'Replay plan changed after drawing')
    require(time.monotonic()-started<=150,'Replay exceeded declared150s phase')
    write(output/'replay-receipt.json',dict(status='dependent_C1_restore_and_frozen_fields_replay_byteexact',dependency_manifest_sha256=m['dependency']['manifest_sha256'],capsule_manifest_sha256=plan['capsule_manifest_sha256'],replay_plan_sha256=expected,
        restored_archive_members=186,small_mirror_files=len(m['mirror_files_sha256']),rebase_only_source_root=True,original_figure_plan_sha256=m['original_figure_plan_sha256'],rebased_figure_plan_sha256=sha(rebased_path),
        source_sha256=sha(__file__),frozen_renderer_sha256=sha(restored/m['renderer']),frozen_render_receipt_sha256=sha(output/'render/render-receipt.json'),entire_checks_maxima_camera_runtime_equal002=True,
        outputs_sha256={n:sha(output/'render'/n)for n in m['expected_exports_sha256']},runtime_before_after_equal=True,scientific_imported_files_after_exports=imported_after_exports,late_scientific_imports_within_original211_and_observed8=True,supplemental_runtime_sha256=m['supplemental_runtime_sha256'],all_inputs_after_equal=True,FEA_started=False,CAD_mesh_kernel_called=False,
        rendering_from_closed_results_only=True,standalone_without_C1_capsule=False,wall_seconds=time.monotonic()-started,CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    print(json.dumps(dict(status='dependent_portable_replay_passed_3_exports_byteexact',receipt_sha256=sha(output/'replay-receipt.json'))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','replay']);p.add_argument('plan');p.add_argument('--plan-sha256',required=True);a=p.parse_args()
    if a.mode=='replay':run(a.plan,a.plan_sha256)
    else:
        require(sha(a.plan)==a.plan_sha256,'Plan changed');plan=read(a.plan);m,_=verify_capsule(plan['capsule_manifest_sha256'],plan['dependency_directory'])
        print(json.dumps(dict(status='stdlib_dependent_replay_inputs_checked_NO_restore_NO_render',launch_ready=plan['launch_ready'],archive_members=m['archive_member_count'],mirror_files=len(m['mirror_files_sha256']))),flush=True)
