"""HELD/UNRUN finite identities plus one separately admitted metadata query."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
P=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-staging-freshness-prep-001'
H=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-root-execution-001'
O=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-003'
D=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-003'
PREFIX=E/'moose-local-installed-002'
CAP=32*1024**2
START=time.monotonic()
QUERY="""import json,os,sys
print(json.dumps(dict(executable=sys.executable,resolved_executable=os.path.realpath(sys.executable),version=sys.version,version_info=list(sys.version_info[:3]),flags=dict(isolated=sys.flags.isolated,no_site=sys.flags.no_site,dont_write_bytecode=sys.flags.dont_write_bytecode,no_user_site=sys.flags.no_user_site,optimize=sys.flags.optimize),site_loaded='site' in sys.modules,distutils_hack_loaded='_distutils_hack' in sys.modules),sort_keys=True,allow_nan=False),flush=True)
"""


def need(condition, message):
    if not condition:
        raise ValueError(message)


def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)


def time_check():
    need(time.monotonic()-START<60,'Whole-operation internal60s bound')


def selected(pin):
    name=Path(pin['path'])
    need(not name.is_absolute() and '..' not in name.parts,'Relative fixed control/input required')
    p=R/name
    need(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Canonical regular declared file required')
    time_check();got=rec(p);time_check()
    need(got==pin,'Declared file identity changed: '+str(name))
    return p,got


def admit():
    need(len(sys.argv)==2 and len(sys.argv[1])==64 and all(x in '0123456789abcdef' for x in sys.argv[1]),'Exact separate root authorization digest required')
    A=H/'authorization.json'
    need(H.is_dir() and not H.is_symlink() and set(p.name for p in H.iterdir())=={'authorization.json'},'Fresh helper root with authorization only required')
    need(A.is_file() and not A.is_symlink() and rec(A)['sha256']==sys.argv[1],'Changed root authorization')
    auth=json.loads(A.read_text());plan_path=P/'held-plan.json';plan=json.loads(plan_path.read_text())
    need(auth.get('schema')=='962-native003-finite-helper-root-admission/v1' and auth.get('operation')=='freshness' and auth.get('operation_authorized') is True,'No freshness authority')
    need(type(auth.get('invocations')) is int and auth['invocations']==1 and auth.get('automatic_retry') is False,'One operation and no retry required')
    need(auth.get('independent_source_review_complete') is True and auth.get('root_source_review_complete') is True,'Pending helper source reviews')
    need(auth.get('runtime_metadata_query_authorized') is True and all(auth.get(k) is False for k in ['native_execution_authorized','fixture_execution_authorized','field_parsing_authorized','manufacturing_authorized']),'Metadata query only; no native/scientific authority')
    need(auth['helper']==rec(Path(__file__)) and auth['plan']==rec(plan_path),'Exact helper/plan required')
    need(auth['limits']==plan['operation_limits'] and auth['limits']==dict(whole_seconds=60,TERM_grace_seconds=8,stream_buffer_bytes=1048576,query_seconds=5,total_inclusive_bytes=33554432,thread_environment=1,retries=0),'Fixed helper limits required')
    need(plan['operation_source_authority_only'] is True and plan['native_execution_authorized'] is False,'Exact held plan required')
    before={name:selected(pin)[1] for name,pin in plan['known_native_roles'].items()}
    for name,pin in plan['source_plan_bindings'].items():before[name]=selected(pin)[1]
    for name in ['helper_source_peer','helper_source_bindings','helper_root_review','helper_preparation_index','staging_receipt']:before[name]=selected(auth[name])[1]
    need(auth['staging_receipt']['path']==plan['future_staging_receipt'],'Fixed separate staging receipt required')
    before.update(helper=rec(Path(__file__)),plan=rec(plan_path),authorization=rec(A))
    return auth,plan,before


def alias(p):
    return dict(is_symlink=p.is_symlink(),raw_target=os.readlink(p) if p.is_symlink() else None,resolved=str(p.resolve(strict=True)))


def observe(actual,plan,out):
    time_check()
    need(len(actual['input_sha256'])==257 and len(actual['runtime_sha256s'])==19 and len(actual['runtime_symlinks'])==13 and len(actual['expected_provider_paths'])==22 and len(actual['expected_host_records'])==89,'Exact finite scope required')
    out.update(inputs={},runtime_files={},runtime_links={},providers={},host_records={},staged_inputs={})
    for name,digest in actual['input_sha256'].items():
        p=R/name
        need(not Path(name).is_absolute() and '..' not in Path(name).parts and p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Changed declared input path')
        time_check();v=rec(p);time_check();need(v['sha256']==digest,'Changed declared input digest: '+name);out['inputs'][name]=v
    for name,digest in actual['runtime_sha256s'].items():
        p=PREFIX/name
        need(not Path(name).is_absolute() and '..' not in Path(name).parts and p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Changed selected runtime path')
        time_check();v=rec(p);time_check();need(v['sha256']==digest,'Changed selected runtime digest: '+name);out['runtime_files'][name]=v
    for name,target in actual['runtime_symlinks'].items():
        p=PREFIX/name
        need(not Path(name).is_absolute() and '..' not in Path(name).parts,'Invalid selected runtime alias')
        v=alias(p);need(v['is_symlink'] and v['raw_target']==target and Path(v['resolved']).is_relative_to(PREFIX),'Changed selected runtime alias');out['runtime_links'][name]=v
    for name,expected in actual['expected_provider_paths'].items():
        p=Path(name);need(p.is_absolute() and p.is_file(),'Missing declared provider path')
        v=alias(p);need(v==expected,'Changed selected provider path: '+name);out['providers'][name]=v
    for name,expected in actual['expected_host_records'].items():
        item=Path(name);need('..' not in item.parts,'Invalid declared host record')
        p=item if item.is_absolute() else R/item;need(p.is_file(),'Missing declared host record')
        if p.is_symlink():need(name in actual['expected_provider_paths'] and alias(p)==actual['expected_provider_paths'][name],'Undeclared host alias')
        else:need(p.resolve(strict=True)==p,'Unexpected host parent alias')
        time_check();v=rec(p);time_check();need(v==expected,'Changed declared host record: '+name);out['host_records'][name]=v
    py=actual['outer_python'];meta=actual['outer_python_observed_metadata'];p=Path(py['path']);v=alias(p)
    need(py['path']==meta['path'] and v['resolved']==meta['resolved_path'],'Changed selected native Python route')
    target=Path(v['resolved']);need(target.is_file() and not target.is_symlink() and target.resolve(strict=True)==target,'Changed selected Python body path')
    time_check();got=rec(target);time_check();need(got['sha256']==py['sha256']==meta['sha256'] and got['bytes']==py['bytes']==meta['bytes'],'Changed selected native Python body')
    out['outer_python']=dict(expected=py,body=got,alias=v)
    for name,pin in actual['staged_inputs'].items():out['staged_inputs'][name]=selected(pin)[1]
    need(out['staged_inputs']==plan['expected_staged_inputs'] and set(p.name for p in O.iterdir())==set(actual['staged_inputs']) and not D.exists(),'Only four staged inputs and no native root required')
    return out


def metadata_query(actual):
    argv=[actual['outer_python']['path'],'-B','-I','-S','-c',QUERY]
    env=actual['outer_environment']
    need(env==dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',FI_PROVIDER='tcp'),'Fixed selected query environment')
    q=dict(argv=argv,environment=env,attempts=0,started=False,PID=None,returncode=None,reaped=False,error=None,stop_actions=[],stdout=None,stderr=None,metadata=None,query_scope='json/os/sys metadata only; no native or fixture import/execution',new_session=False)
    proc=None;begin=time.monotonic()
    try:
        time_check();need(60-(begin-START)>0,'No query time remaining')
        with (H/'query.stdout').open('xb') as out,(H/'query.stderr').open('xb') as err:
            q['attempts']=1
            proc=subprocess.Popen(argv,cwd=H,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=False)
            q.update(attempts=1,started=True,PID=proc.pid)
            q['returncode']=proc.wait(timeout=min(5,max(0.001,60-(time.monotonic()-START))))
            q['reaped']=True
    except BaseException:
        q['error']=traceback.format_exc()
    finally:
        if proc is not None and not q['reaped']:
            try:
                if proc.poll() is None:
                    q['stop_actions'].append('direct owned unreaped child TERM');proc.terminate()
                q['returncode']=proc.wait(timeout=min(8,max(0.001,60-(time.monotonic()-START))))
                q['reaped']=True
            except BaseException:
                q['cleanup_TERM_error']=traceback.format_exc()
                try:
                    if proc.poll() is None:q['stop_actions'].append('direct owned unreaped child KILL');proc.kill()
                    q['returncode']=proc.wait(timeout=max(0.001,60-(time.monotonic()-START)))
                    q['reaped']=True
                except BaseException:q['cleanup_KILL_error']=traceback.format_exc()
        q['elapsed_through_cleanup']=time.monotonic()-begin
        for name in ['stdout','stderr']:
            p=H/('query.'+name)
            if p.exists():q[name]=rec(p)
    try:
        need(q['started'] and q['attempts']==1 and q['returncode']==0 and q['reaped'] and q['error'] is None and q['stop_actions']==[] and q['elapsed_through_cleanup']<=5,'Metadata query did not close normally within5s')
        need(q['stdout'] is not None and 0<q['stdout']['bytes']<=65536 and q['stderr'] is not None and q['stderr']['bytes']==0,'Query streams must be complete, small and unambiguous')
        raw=(H/'query.stdout').read_bytes();need(raw.endswith(b'\n') and len(raw.splitlines())==1,'Exactly one complete JSON metadata line required')
        v=json.loads(raw);need(set(v)=={'executable','resolved_executable','version','version_info','flags','site_loaded','distutils_hack_loaded'},'Exact metadata keys required')
        need(v['version_info']==[3,12,11] and v['resolved_executable']==actual['outer_python_observed_metadata']['resolved_path'] and v['executable']==actual['outer_python']['path'],'Selected native3.12 route/version required')
        need(v['flags']==dict(isolated=1,no_site=1,dont_write_bytecode=1,no_user_site=1,optimize=0) and v['site_loaded'] is False and v['distutils_hack_loaded'] is False,'Explicit -B-I-S startup required')
        need(isinstance(v['version'],str) and v['version'].startswith('3.12.11 '),'Exact major/minor/patch version string required')
        q['metadata']=v
    except BaseException:
        q['validation_error']=traceback.format_exc()
    return q


def owned_bytes():
    total=0
    for root in [H,O]:
        need(root.is_dir() and not root.is_symlink(),'Owned directory changed')
        for p in root.iterdir():
            need(p.is_file() and not p.is_symlink(),'Unexpected owned entry')
            total+=p.stat().st_size
    return total


def main():
    auth,plan,before=admit()
    report=dict(schema='962-observer004-native003-fresh-preflight/v1',status='INCOMPLETE',metadata_query_only=True,native_execution=False,fixture_execution=False,field_parsing=False,helper=before['helper'],held_plan=before['plan'],authorization=before['authorization'],controls_before=before,controls_after=None,observations_before=None,observations_after=None,query=None,error=None,all_declared_identities_unchanged=False)
    try:
        actual=json.loads(selected(plan['known_native_roles']['actual'])[0].read_text())
        need(actual['schema']=='962-observer004-native-measurement-actual/v1' and actual['native_execution_authorized'] is False,'Exact held native actual required')
        stage=json.loads(selected(auth['staging_receipt'])[0].read_text())
        need(stage['schema']=='962-observer004-native-measurement-four-input-staging/v1' and stage['all_four_copies_byte_exact'] is True and stage['no_execution'] is True and stage['staged_inputs']==actual['staged_inputs']==plan['expected_staged_inputs'],'Exact separate successful no-execution staging receipt required')
        prior_pin=actual['native002_actual_preserved'];prior=json.loads(selected(prior_pin)[0].read_text())
        need(len(prior['input_sha256'])==222 and len(actual['input_sha256'])==257 and all(actual['input_sha256'].get(k)==v for k,v in prior['input_sha256'].items()),'Explicit222-to257 unchanged ancestry required')
        report['ancestry']=dict(prior_actual=prior_pin,preserved222=222,new_records=35,total257=257,original197_reestablished=False,original197_scope='Historical lineage only; no separate197-map reconstruction is performed here.')
        report['observations_before']={};observe(actual,plan,report['observations_before'])
        report['query']=metadata_query(actual)
        need(report['query'].get('validation_error') is None and report['query']['error'] is None,'Metadata query refused')
        report['observations_after']={};observe(actual,plan,report['observations_after'])
        after={name:selected(pin)[1] for name,pin in plan['known_native_roles'].items()}
        for name,pin in plan['source_plan_bindings'].items():after[name]=selected(pin)[1]
        for name in ['helper_source_peer','helper_source_bindings','helper_root_review','helper_preparation_index','staging_receipt']:after[name]=selected(auth[name])[1]
        after.update(helper=rec(Path(__file__)),plan=rec(P/'held-plan.json'),authorization=rec(H/'authorization.json'))
        report['controls_after']=after
        need(before==after and report['observations_before']==report['observations_after'],'Finite identities changed across query')
        report['all_declared_identities_unchanged']=True;report['status']='COMPLETE_METADATA_ONLY'
    except BaseException:report['error']=traceback.format_exc()
    report['elapsed_before_receipt']=time.monotonic()-START
    report['late_native_roles']=dict(known_seven=plan['known_native_roles'],staging_receipt=auth['staging_receipt'],fresh_preflight='Externally compute this complete receipt identity; no embedded self hash or native admission.')
    report['scope_limits']=dict(full_ABI_or_runtime_closure=False,native_callback_or_solve=False,physical_acceptance=False,sampled_RSS_pass=False,hard_quota=False,whole_return_external_clock_and_group_and_inclusive_postchecks_required=True)
    encoded=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    need(owned_bytes()+len(encoded)<=CAP,'Complete freshness streams/receipt exceeds32MiB; no truncation')
    with (H/'fresh-preflight.json').open('xb') as f:f.write(encoded)
    if report['status']!='COMPLETE_METADATA_ONLY' or report['error'] is not None or owned_bytes()>CAP or time.monotonic()-START>=60:
        print('Freshness closure refused; retain full prefinal receipt and require independent outer0.',file=sys.stderr,flush=True);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
