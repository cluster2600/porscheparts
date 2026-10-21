"""HELD/UNRUN clean OWNER003 for lossless source002. A separately sealed launch is mandatory.

One saved-only source invocation; no native, optimizer, mesh write or word construction.
Metadata-only reuse of the completed twelve-guard owner; do not run during preparation.
"""
from pathlib import Path
import hashlib,json,os,re,signal,subprocess,time,traceback,sys
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993');E=R/'work/962-engineering'
P=E/'head-star-current24-exact-segment-feasibility-execution-prep-003'
D=E/'head-star-current24-exact-segment-feasibility-root-execution-002'
G=E/'head-star-current24-exact-segment-root-source-001'
S=E/'head-star-current24-exact-segment-feasibility-prep-002'
V=E/'head-star-current24-segment-runtime-001/venv'
SITE=V/'lib/python3.12/site-packages'
HEAD_OUTPUT=E/'head-star-current24-exact-segment-feasibility-002'
A=P/'actual-contract.json';L=D/'launch.json'
def rec(p):
 b=p.read_bytes();return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def protected(records):
 result={}
 for name,pin in records.items():
  p=R/name;assert p.is_file() and not p.is_symlink();assert rec(p)==pin,name;result[name]=rec(p)
 return result

def observed_after(records,regular=True):
 result={};errors={}
 for name in records:
  try:
   p=R/name
   if not p.is_file() or (regular and p.is_symlink()):raise ValueError('missing/nonregular protected path')
   result[name]=rec(p)
  except BaseException as exc:errors[name]=dict(type=type(exc).__name__,message=str(exc))
 return result,errors

def alias_record(p):
 resolved=p.resolve(strict=True);links={};current=p
 while current.is_symlink():
  raw=os.readlink(current);links[str(current)]=raw
  current=Path(os.path.abspath(current.parent/raw)) if not Path(raw).is_absolute() else Path(raw)
 return dict(path=str(p),resolved_path=str(resolved),raw_link_chain=links)


def need(condition,message):
    if not condition:raise ValueError(message)


def verify_lossless_gzip_bytes(compressed,manifest):
    """Bounded streaming byte identity only; never decode or validate scientific JSON."""
    need(type(compressed)is bytes and len(compressed)<=33554432,"Compressed input exceeds unchanged disk budget")
    logical=manifest["logical_payload"];stored=manifest["compressed_payload"]
    need(type(logical["bytes"])is int and 0<logical["bytes"]<=2147483648,
        "Declared inflation exceeds existing2GiB capacity ceiling")
    need(type(stored["bytes"])is int and stored["bytes"]==len(compressed)
        and stored["sha256"]==hashlib.sha256(compressed).hexdigest(),"Compressed byte identity")
    need(compressed[:10]==b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff",
        "Fixed gzip header: no filename/extra/time fields; level9")
    count=0;digest=hashlib.sha256()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed),mode="rb")as stream:
        while True:
            block=stream.read1(min(io.DEFAULT_BUFFER_SIZE,logical["bytes"]-count+1))
            if not block:break
            count+=len(block)
            need(count<=logical["bytes"] and count<=2147483648,"Declared bounded inflation exceeded")
            digest.update(block)
    need(count==logical["bytes"]and digest.hexdigest()==logical["sha256"],
        "Complete uncompressed byte count and SHA256; EOF/CRC required")
    return dict(bytes=count,sha256=digest.hexdigest(),complete_EOF_and_CRC=True)


# Fresh actual and external launch bind this source; no owner-supersession adapter.
launch_before=rec(L);actual_before=rec(A)
launch=json.loads(L.read_text());actual=json.loads(A.read_text())
assert launch['schema']=='962-current24-exact-segment-lossless-root-once-launch/v1'
assert launch['saved_only_segment_once_authorized'] is True
assert type(launch['execution_count']) is int and launch['execution_count']==1
assert launch['automatic_retry'] is False
assert actual['schema']=='962-current24-exact-segment-real-feasibility-execution-authority/v1'
assert actual['saved_only_segment_feasibility_diagnostic_authorized'] is True
assert type(actual['execution_count']) is int and actual['execution_count']==1
qualification=('head_PDE_authorized','engineering_accepted','physics_qualified','material_qualified',
 'process_calibrated','manufacturing_authorized','native_execution_authorized','optimizer_execution_authorized',
 'remeshing_authorized','surface_retriangulation_authorized','geometry_write_authorized',
 'automatic_retry','global_infeasibility_proved')
for key in qualification:assert actual[key] is False and launch[key] is False
assert actual['binary64_word_construction_authorized'] is False and launch['binary64_word_construction_authorized'] is False
assert actual['ordinary_seconds']==60 and actual['TERM_grace_seconds']==8
assert actual['sampled_RSS_stop_bytes']==2147483648 and actual['sampled_output_stop_bytes']==33554432
assert type(actual['threads']) is int and actual['threads']==1
assert actual['new_owned_session'] is True and actual['verified_owned_KILL_wait'] is True and actual['hard_OS_quota'] is False
assert Path(__file__).resolve()==P/'run_root_once_003.py'
assert actual['root_controller_path']==str(Path(__file__).resolve().relative_to(R))
assert actual['execution_preparation_paths']=={name:str((P/name).relative_to(R)) for name in
 ('actual-contract.json','run_root_once_003.py','preflight.json','preparation-index.json',
  'controller-reuse.json','controller.diff','METHOD.md')}
direct_roles=('actual','root_controller','exact_child_peer','exact_child_bindings','preflight',
 'preparation_index','controller_reuse','controller_diff','method','independent_source_review',
 'independent_source_bindings','root_source_admission','synthetic_guard_result','selected_root_runtime',
 'original_mathematical_guard_result','runtime_preflight','startup_preflight',
 'serializer_runtime_preflight','serializer_runtime_selection')
direct_before={}
for key in direct_roles:
 pin=launch[key];p=R/pin['path'];assert p.is_file() and not p.is_symlink()
 direct_before[str(p)]=rec(p);assert direct_before[str(p)]==pin
assert launch['actual']==actual_before and launch['root_controller']==rec(Path(__file__))
prep_roles={'actual':'actual-contract.json','root_controller':'run_root_once_003.py','preflight':'preflight.json',
 'preparation_index':'preparation-index.json','controller_reuse':'controller-reuse.json',
 'controller_diff':'controller.diff','method':'METHOD.md'}
for role,name in prep_roles.items():assert launch[role]['path']==str((P/name).relative_to(R))
for role in ('independent_source_review','independent_source_bindings','root_source_admission',
 'synthetic_guard_result','selected_root_runtime','original_mathematical_guard_result',
 'runtime_preflight','startup_preflight','serializer_runtime_preflight','serializer_runtime_selection'):
 assert launch[role]==actual[role]
index=json.loads((P/'preparation-index.json').read_text())
assert index['root_controller']==launch['root_controller']
for role in ('controller_reuse','controller_diff','method'):assert index[role]==launch[role]
assert index['source_only_preparation'] is True
assert actual['future_exact_child_peer'] is None and actual['future_launch'] is None and actual['future_result'] is None
admission=R/actual['root_source_admission']['path']
runtime=R/actual['runtime_preflight']['path'];startup=R/actual['startup_preflight']['path']
assert rec(runtime)['sha256']=='e427b7e491d4c36b05ffb08b13a9892c77cfb68f10f21ce7436d2235a37e2c26'
assert rec(startup)['sha256']=='ecd934f83ee0bc397e2def86235e19aa6fb35ff01b36f9f06e4cdf6e5201c856'
rt=json.loads(runtime.read_text());startup_pin=json.loads(startup.read_text())
guard_result=json.loads((R/actual['original_mathematical_guard_result']['path']).read_text())
selected=json.loads((R/actual['selected_root_runtime']['path']).read_text())
assert actual['original_mathematical_guard_result']['sha256']=='02536f95067c763851cb5479fdf9ed2ece78dd41bbbb4497a38acb509bf9da41'
assert actual['selected_root_runtime']['sha256']=='c0e74062acb71ecb443f472f7f38ebd8bf31d511b8796ce02d9fc42ec9e96073'
assert guard_result['returncode']==0 and guard_result['all_twelve_passed'] is True and guard_result['tests_passed']==12
assert guard_result['stop_reason'] is None and guard_result['error'] is None and guard_result['signals']==[]
assert guard_result['waited_reaped'] is True and guard_result['owned_group_absent'] is True
assert guard_result['all_bound_inputs_runtime_and_controls_current'] is True
assert selected['sympy_version']=='1.14.0' and selected['mpmath_version']=='1.3.0'
assert selected['exact_public_API_synthetic_probe_passed'] is True
assert selected['guard_result']==actual['original_mathematical_guard_result']
assert selected['runtime_preflight']==actual['runtime_preflight'] and selected['startup_preflight']==actual['startup_preflight']
serializer_rt=json.loads((R/actual['serializer_runtime_preflight']['path']).read_text())
serializer_selection=json.loads((R/actual['serializer_runtime_selection']['path']).read_text())
fixture=json.loads((R/actual['synthetic_guard_result']['path']).read_text())
assert serializer_rt['schema']=='962-current24-segment-gzip-runtime-preflight/v1'
assert serializer_selection['schema']=='962-current24-segment-gzip-selected-runtime/v1'
assert serializer_selection['runtime_preflight']==actual['serializer_runtime_preflight']
assert serializer_selection['guard_result']==actual['synthetic_guard_result']
assert serializer_selection['serializer_fixture_passed'] is True
for key in ('module_files','module_origins','observed'):assert serializer_selection[key]==serializer_rt[key]
assert serializer_rt['selected_math_runtime']==actual['selected_root_runtime']
assert serializer_selection['worker']==actual['worker']
assert serializer_selection['selected_math_runtime']==actual['selected_root_runtime']
assert serializer_selection['original_twelve_math_API_guards']==actual['original_mathematical_guard_result']
assert serializer_selection['original_twelve_math_API_guards_repeated']is False
assert serializer_selection['new_scientific_execution_authorized']is False
assert fixture['schema']=='962-current24-segment-gzip-synthetic-fixture-result/v1'
assert fixture['returncode']==0 and type(fixture['tests_passed']) is int and fixture['tests_passed']==4
assert fixture['worker']==actual['worker'] and fixture['fixture']==serializer_selection['fixture']
assert fixture['worker_source_peer']==actual['independent_source_review']
assert fixture['runtime_preflight']==actual['serializer_runtime_preflight']
assert fixture['package_file_count']==1667 and fixture['all1667_package_files_current']is True
assert fixture['root_stop_requests']==[] and fixture['head_or_SymPy_imported']is False
assert fixture['scientific_result_accepted']is False and fixture['automatic_retry']is False
admitted=json.loads(admission.read_text())
assert admitted['schema']=='962-current24-segment-source002-root-admission-after-fixtures/v1'
assert admitted['source']==actual['worker'] and admitted['source_peer']==actual['independent_source_review']
assert admitted['four_fixture_result']==actual['synthetic_guard_result']
assert admitted['selected_serialization_runtime']==actual['serializer_runtime_selection']
assert admitted['corrected_fixture']==fixture['fixture'] and admitted['fixture_peer']==fixture['fixture_source_peer']
assert admitted['scientific_certificate_accepted']is False and admitted['empty_feasibility_inferred']is False
assert admitted['future_exact_actual_peer_and_root_launch_required']is True
assert fixture['all_four_passed'] is True and fixture['stop_reason'] is None and fixture['error'] is None
assert fixture['signals']==[] and fixture['waited_reaped'] is True and fixture['owned_group_absent'] is True
assert fixture['all_bound_inputs_runtime_and_controls_current']is True
assert startup_pin['startup_records']=={}
startup_names_before=sorted(p.name for p in SITE.iterdir())
assert startup_names_before==sorted(startup_pin['site_top_level_names'])
source=R/actual['worker']['path'];held_path=R/actual['held_preparation']['path']
assert source==S/'classify_segment_feasibility.py' and held_path==S/'held-preparation.json'
assert rec(source)['sha256']=='b4b1abb1d3dbcb30cd78d63f454c652ec5153cf0c140132f837a1fae6c559865'
assert rec(held_path)['sha256']=='e7f07103e9c27eb7bc4b07609d1f1fb17d27ffcec426af40fe6cd54bb302e3f2'
held=json.loads(held_path.read_text())
prior=held['capacity_delta_evidence']['terminal_closed001']
assert prior['sha256']=='d76b3dadfe677f0c4321ea5a076333eec9287d7b114de96cadcd6d37fd92570a'
prior_closed=json.loads((R/prior['path']).read_text())
assert rec(R/prior['path'])==prior
base75=prior_closed['metadata_before']
assert len(base75)==75 and base75==prior_closed['metadata_after'] and prior_closed['all75_metadata_unchanged'] is True
required=dict(base75)
for name,pin in held['input_records'].items():
 if name in required:assert required[name]==pin
 required[name]=pin
for name in ('METHOD.md','classify_segment_feasibility.py','held-preparation.json','preparation-index.json',
 'source-delta.json','source-reuse.json','source.diff','test_serializer_guards.py'):
 pin=rec(S/name)
 if pin['path']in required:assert required[pin['path']]==pin
 required[pin['path']]=pin
for pin in (actual['independent_source_review'],actual['independent_source_bindings']):
 if pin['path']in required:assert required[pin['path']]==pin
 required[pin['path']]=pin
root_records=actual['serializer_root_metadata_records']
assert isinstance(root_records,dict) and len(root_records)>0
for name,pin in root_records.items():
 assert name==pin['path']
 if name in required:assert required[name]==pin
 required[name]=pin
for key in ('root_source_admission','synthetic_guard_result','serializer_runtime_preflight','serializer_runtime_selection'):
 assert root_records[actual[key]['path']]==actual[key]
expected=actual['protected_metadata_records']
assert expected==required and type(actual['protected_metadata_count']) is int
assert len(expected)==actual['protected_metadata_count']
before=protected(expected)
source=R/actual['worker']['path'];held_path=R/actual['held_preparation']['path']
held=json.loads(held_path.read_text())
assert rec(source)==held['source']==actual['worker']
assert rec(held_path)==actual['held_preparation'] and actual['input_records']==held['input_records']
assert held['input_record_count']==len(actual['input_records'])==55
assert actual['tuple_list']==held['tuple_list'] and rec(R/actual['tuple_list']['path'])==actual['tuple_list']
assert rt['installation']['sha256']=='c1713b9e706ad7eac8818e15b33943f1f320e17bda2101b2710ab28bb57091e2'
assert rec(R/rt['installation']['path'])==rt['installation']
installation=json.loads((R/rt['installation']['path']).read_text())
package_expected={}
assert {d['distribution'] for d in installation['distributions']}=={'sympy-1.14.0.dist-info','mpmath-1.3.0.dist-info'}
for distribution in installation['distributions']:
 assert len(distribution['files'])==distribution['count']
 for pin in distribution['files']:
  assert not Path(pin['path']).is_absolute()
  p=Path(os.path.normpath(str(SITE/pin['path'])));assert p.is_relative_to(V)
  name=str(p.relative_to(R));assert name not in package_expected
  package_expected[name]=dict(path=name,sha256=pin['sha256'],bytes=pin['bytes'])
assert len(package_expected)==1667 and rt['package_file_count']==1667 and rt['package_records']==package_expected
packages_before=protected(package_expected)
py=Path(rt['selected_python_alias']);assert py==V/'bin/python'
runtime_files={pin['path']:pin for pin in (rt['selected_python'],rt['libpython_provider'],installation['installer'])}
assert rt['selected_python']==installation['base_Python'] and rt['libpython_provider']==installation['libpython_provider']
assert actual['selected_python']==rt['selected_python'] and actual['libpython_provider']==rt['libpython_provider']
assert actual['selected_python_alias']==str(py) and actual['installer']==installation['installer']
runtime_before={name:rec(Path(name)) for name in runtime_files}
assert runtime_before==runtime_files
assert serializer_rt['selected_python']==rt['selected_python'] and serializer_rt['libpython_provider']==rt['libpython_provider']
module_files=serializer_rt['module_files'];assert set(module_files)=={'gzip','_compression'}
serializer_files={pin['path']:pin for pin in module_files.values()}
assert len(serializer_files)==2
serializer_modules_before=protected(serializer_files)
assert serializer_rt['module_origins']['zlib']['origin']=='built-in'
assert serializer_rt['module_origins']['zlib']['separate_module_file'] is False
assert serializer_rt['module_origins']['zlib']['selected_Python_provider']==rt['libpython_provider']
for name in ('gzip','_compression'):
 assert serializer_rt['module_origins'][name]['module_file']==module_files[name]
 assert serializer_rt['module_origins'][name]['origin']==module_files[name]['path']
# Imports happen only after externally bound module/provider files were freshly checked.
import gzip,io,zlib,_compression
serializer_observed_before=dict(Python_executable=sys.executable,Python_version=sys.version.split()[0],
 gzip_origin=gzip.__spec__.origin,zlib_origin=zlib.__spec__.origin,
 compression_origin=_compression.__spec__.origin,io_origin=io.__spec__.origin,
 zlib_compile_version=zlib.ZLIB_VERSION,zlib_runtime_version=zlib.ZLIB_RUNTIME_VERSION,
 SymPy_imported='sympy' in sys.modules)
assert serializer_observed_before==serializer_rt['observed']
assert serializer_observed_before['io_origin']=='frozen'
assert Path(sys.executable)==py
alias_paths=[py]+[Path(name) for name in runtime_files]+[Path(name)for name in serializer_files]
aliases_before={str(p):alias_record(p) for p in alias_paths}
assert aliases_before[str(py)]['resolved_path']==rt['selected_python']['path']
build_before=subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True,timeout=2).strip()
assert build_before==rt['macOS_build']==actual['macOS_build'] and os.uname().machine==rt['architecture']=='arm64'
assert rt['declared_versions']==dict(sympy='1.14.0',mpmath='1.3.0')
required_env=dict(SYMPY_GROUND_TYPES='python',SYMPY_USE_CACHE='no',OMP_NUM_THREADS='1',
 OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
assert rt['required_environment']==required_env
env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1',**required_env}
assert actual['environment']==env and actual['Python_flags']==['-B','-I']
assert actual['output_directory']==str(HEAD_OUTPUT.relative_to(R))
assert not HEAD_OUTPUT.exists() and not HEAD_OUTPUT.is_symlink()
assert all(not (D/name).exists() and not (D/name).is_symlink() for name in ('closed-result.json','stdout.log','stderr.log'))
argv=[str(py),'-B','-I',str(source),'--actual',str(A),'--actual-sha256',actual_before['sha256']]
assert actual['worker_argv_without_external_digest']==argv[:-1]
started=time.monotonic();proc=None;signals=[];samples=[];stop=None;error=None;interrupted=False
root_stop_requests=[];root_stop_cutoff=None
def request(signum,_frame):
 global interrupted
 interrupted=True
 root_stop_requests.append(dict(signal=int(signum),wall_seconds=time.monotonic()-started))
def stop_wait():
 if group_exists(proc.pid):
  try:os.killpg(proc.pid,signal.SIGTERM);signals.append('SIGTERM')
  except ProcessLookupError:pass
 try:proc.wait(timeout=8)
 except subprocess.TimeoutExpired:
  if group_exists(proc.pid):
   try:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL')
   except ProcessLookupError:pass
  proc.wait()

old=signal.signal(signal.SIGTERM,request)
try:
 with (D/'stdout.log').open('x') as out,(D/'stderr.log').open('x') as err:
  proc=subprocess.Popen(argv,cwd=R,stdout=out,stderr=err,start_new_session=True,env=env)
  while proc.poll() is None:
   elapsed=time.monotonic()-started
   ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=2)
   if ps.returncode==0 and ps.stdout.strip().isdigit() and int(ps.stdout.strip())>0:rss=int(ps.stdout.strip())*1024
   elif proc.poll() is not None:break
   else:stop='RSS_observation_failed_live_child';stop_wait();break
   output_bytes=(sum(p.stat().st_size for p in HEAD_OUTPUT.rglob('*') if p.is_file()) if HEAD_OUTPUT.exists() else 0)+sum((D/n).stat().st_size for n in ('stdout.log','stderr.log'))
   samples.append(dict(wall_seconds=elapsed,RSS_bytes=rss,output_bytes=output_bytes))
   if interrupted:stop='root_SIGTERM'
   elif elapsed>=60:stop='ordinary60s'
   elif rss>=2147483648:stop='sampled_RSS_2GiB'
   elif output_bytes>=33554432:stop='sampled_output_32MiB'
   if stop:stop_wait();break
   try:proc.wait(timeout=.05)
   except subprocess.TimeoutExpired:pass
  proc.wait()
except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
finally:
 try:
  if proc is not None and proc.poll() is None:stop=stop or 'root_cleanup';stop_wait()
  if proc is not None and group_exists(proc.pid):
   try:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL_lingering');stop=stop or 'lingering_group'
   except ProcessLookupError:pass
  if proc is not None:proc.wait()
 finally:
  signal.signal(signal.SIGTERM,old)
  root_stop_cutoff=dict(wall_seconds=time.monotonic()-started,
   boundary='SIGTERM_handler_restored_after_owned_child_cleanup',
   scope='Only Python SIGTERM handler deliveries before restoration are captured; no scientific child runs after this boundary. Later termination/nonzero or absent/partial receipt is not accepted.')
# Preserve a closed receipt even if any post-run observation fails.
after,metadata_errors=observed_after(expected)
packages_after,package_errors=observed_after(package_expected)
runtime_after,runtime_errors=observed_after(runtime_files,regular=False)
serializer_modules_after,serializer_module_errors=observed_after(serializer_files)
serializer_observed_after=None;serializer_observation_error=None
try:
 serializer_observed_after=dict(Python_executable=sys.executable,Python_version=sys.version.split()[0],
  gzip_origin=gzip.__spec__.origin,zlib_origin=zlib.__spec__.origin,
  compression_origin=_compression.__spec__.origin,io_origin=io.__spec__.origin,
  zlib_compile_version=zlib.ZLIB_VERSION,zlib_runtime_version=zlib.ZLIB_RUNTIME_VERSION,
  SymPy_imported='sympy' in sys.modules)
except BaseException as exc:serializer_observation_error=dict(type=type(exc).__name__,message=str(exc))
direct_after,direct_errors=observed_after(direct_before)
launch_after_map,launch_errors=observed_after({str(L):launch_before})
actual_after_map,actual_errors=observed_after({str(A):actual_before})
launch_after=launch_after_map.get(str(L));actual_after=actual_after_map.get(str(A))
aliases_after={};alias_errors={}
for name in aliases_before:
 try:aliases_after[name]=alias_record(Path(name))
 except BaseException as exc:alias_errors[name]=dict(type=type(exc).__name__,message=str(exc))
build_after=None;build_error=None
try:build_after=subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True,timeout=2).strip()
except BaseException as exc:build_error=dict(type=type(exc).__name__,message=str(exc))
startup_names_after=None;startup_error=None
try:startup_names_after=sorted(p.name for p in SITE.iterdir())
except BaseException as exc:startup_error=dict(type=type(exc).__name__,message=str(exc))
outputs={};output_errors={}
try:
 if HEAD_OUTPUT.is_symlink():raise ValueError('output directory is a symlink')
 if HEAD_OUTPUT.exists():
  for p in sorted(HEAD_OUTPUT.rglob('*')):
   if p.is_symlink():raise ValueError('output member is a symlink')
   if p.is_file():outputs[str(p.relative_to(HEAD_OUTPUT))]=rec(p)
except BaseException as exc:output_errors['inventory']=dict(type=type(exc).__name__,message=str(exc))
logs={};log_errors={}
for name in ('stdout.log','stderr.log'):
 try:logs[name]=rec(D/name)
 except BaseException as exc:log_errors[name]=dict(type=type(exc).__name__,message=str(exc))
artifact=None;artifact_error=None;complete_artifact=False;payload_integrity=None
try:
 manifest_path=HEAD_OUTPUT/'manifest.json';compressed_path=HEAD_OUTPUT/'real-segment-feasibility.json.gz'
 assert set(outputs)=={'manifest.json','real-segment-feasibility.json.gz'}
 assert sum(pin['bytes']for pin in outputs.values())<=33554432
 artifact=json.loads(manifest_path.read_text())
 assert artifact['schema']=='962-current24-complete-exact-segment-lossless-gzip-manifest/v1'
 assert artifact['status']=='complete_logical_certificate_stored_losslessly_scientific_review_pending'
 assert artifact['logical_schema']=='962-current24-complete-exact-segment-real-feasibility/v1'
 assert artifact['logical_status']=='complete_exact_real_feasibility_on19_saved_segments_only'
 for key,value in (('segment_count',19),('complete_cell_dispositions',916),('complete_constraint_associations',1832)):
  assert type(artifact[key])is int and artifact[key]==value
 assert artifact['source']==actual['worker'] and artifact['held_preparation']==actual['held_preparation']
 assert artifact['own_actual']==actual_before and artifact['tuple_list']==actual['tuple_list']
 assert artifact['gzip_parameters']==dict(mtime=0,filename='',compresslevel=9)
 assert artifact['compressed_payload']['filename']=='real-segment-feasibility.json.gz'
 assert artifact['compressed_payload']['sha256']==outputs['real-segment-feasibility.json.gz']['sha256']
 assert artifact['compressed_payload']['bytes']==outputs['real-segment-feasibility.json.gz']['bytes']
 assert artifact['logical_payload']['filename']=='real-segment-feasibility.json'
 assert artifact['logical_payload']['encoding']=='UTF-8' and artifact['logical_payload']['JSON_indent']==2
 assert artifact['logical_payload']['JSON_allow_nan']is False and artifact['logical_payload']['trailing_newline']is True
 assert artifact['all_logical_coefficients_roots_factors_signs_intervals_witnesses_retained']is True
 assert artifact['binary64_word_proposal_count']==0 and artifact['binary64_word_construction_supported']is False
 assert artifact['scientific_result_accepted']is False
 assert artifact['qualification']=={key:False for key in qualification}
 assert artifact['reader_capacity_ceiling_bytes']==2147483648
 compressed=compressed_path.read_bytes()
 payload_integrity=verify_lossless_gzip_bytes(compressed,artifact)
 # Complete byte integrity and declared manifest metadata only; no inner JSON tree or mathematics.
 complete_artifact=True
except BaseException as exc:artifact_error=dict(type=type(exc).__name__,message=str(exc))
absent=proc is not None and not group_exists(proc.pid)
all_current=(not any((metadata_errors,package_errors,runtime_errors,direct_errors,launch_errors,actual_errors,
 alias_errors,build_error,startup_error,serializer_module_errors,serializer_observation_error)) and startup_names_before==startup_names_after and
 before==after and packages_before==packages_after and runtime_before==runtime_after and
 serializer_modules_before==serializer_modules_after and serializer_observed_before==serializer_observed_after and
 direct_before==direct_after and launch_before==launch_after and actual_before==actual_after and
 aliases_before==aliases_after and build_before==build_after and os.uname().machine==rt['architecture'])
final_output_bytes=sum(pin['bytes'] for pin in outputs.values())+sum(pin['bytes'] for pin in logs.values())
output_budget_observed=not output_errors and not log_errors and final_output_bytes<=33554432
# The handler is already restored; the captured latch/list are stable here.
if interrupted and stop is None:stop='root_SIGTERM'
root_stop_requests_snapshot=[dict(event) for event in root_stop_requests]
complete=(proc is not None and proc.returncode==0 and stop is None and error is None and signals==[] and
 not interrupted and not root_stop_requests_snapshot and
 absent and all_current and complete_artifact and output_budget_observed)
j=dict(schema='962-current24-exact-segment-lossless-root-once-closed/v1',
 serializer_runtime_preflight=actual['serializer_runtime_preflight'],
 serializer_runtime_selection=actual['serializer_runtime_selection'],
 status='COMPLETE_SAVED_REAL_SEGMENT_ARTIFACT_PENDING_RESULT_REVIEW' if complete else 'INCOMPLETE_NO_FEASIBILITY_CONCLUSION',
 launch_before=launch_before,launch_after=launch_after,launch_unchanged=launch_before==launch_after,
 launch_observation_errors=launch_errors,actual_before=actual_before,actual_after=actual_after,
 actual_unchanged=actual_before==actual_after,actual_observation_errors=actual_errors,
 root_controller_before=direct_before[str(Path(__file__).resolve())],root_controller_after=direct_after.get(str(Path(__file__).resolve())),
 exact_child_peer=launch['exact_child_peer'],exact_child_bindings=launch['exact_child_bindings'],
 argv=argv,environment=env,returncode=proc.returncode if proc else None,wall_seconds=time.monotonic()-started,
 stop_reason=stop,signals=signals,error=error,root_SIGTERM_received_before_cutoff=interrupted,
 root_stop_requests_before_cutoff=root_stop_requests_snapshot,root_stop_handler_restore_cutoff=root_stop_cutoff,
 waited_reaped=proc is not None and proc.poll() is not None,
 owned_group_absent=absent,metadata_before=before,metadata_after=after,protected_metadata_count=len(before),
 all_protected_metadata_unchanged=before==after,retained_prior_metadata_count=len(base75),
 all75_prior_metadata_unchanged=all(after.get(name)==before[name]for name in base75),
 metadata_observation_errors=metadata_errors,
 package_records_before=packages_before,package_records_after=packages_after,package_file_count=len(packages_before),
 all1667_package_files_unchanged=packages_before==packages_after,package_observation_errors=package_errors,
 runtime_files_before=runtime_before,runtime_files_after=runtime_after,base_Python_provider_uv_unchanged=runtime_before==runtime_after,
 runtime_file_observation_errors=runtime_errors,
 serializer_module_files_before=serializer_modules_before,serializer_module_files_after=serializer_modules_after,
 serializer_module_observation_errors=serializer_module_errors,
 all_serializer_module_files_unchanged=serializer_modules_before==serializer_modules_after,
 serializer_origins_versions_before=serializer_observed_before,serializer_origins_versions_after=serializer_observed_after,
 serializer_origin_version_observation_error=serializer_observation_error,
 serializer_origins_versions_unchanged=serializer_observed_before==serializer_observed_after,
 python_and_runtime_aliases_before=aliases_before,
 python_and_runtime_aliases_after=aliases_after,all_aliases_unchanged=aliases_before==aliases_after,
 alias_observation_errors=alias_errors,direct_controls_before=direct_before,direct_controls_after=direct_after,
 all_direct_controls_unchanged=direct_before==direct_after,direct_control_observation_errors=direct_errors,
 macOS_build_before=build_before,macOS_build_after=build_after,macOS_build_unchanged=build_before==build_after,
 OS_build_observation_error=build_error,site_top_level_names_before=startup_names_before,
 site_top_level_names_after=startup_names_after,site_top_level_names_unchanged=startup_names_before==startup_names_after,
 startup_observation_error=startup_error,all_bound_inputs_runtime_and_controls_current=all_current,
 RSS_samples=samples,max_sampled_direct_child_RSS_bytes=max((x['RSS_bytes'] for x in samples),default=None),
 outputs=outputs,output_observation_errors=output_errors,stdout=logs.get('stdout.log'),stderr=logs.get('stderr.log'),
 log_observation_errors=log_errors,final_observed_worker_and_log_bytes=final_output_bytes,
 output_budget_observed=output_budget_observed,complete19_916_artifact_metadata_consistent=complete_artifact,
 compressed_full_payload_stream_integrity=payload_integrity,inner_logical_JSON_decoded=False,
 artifact_acceptance_scope='Manifest counts/identity plus complete compressed/uncompressed byte integrity only; inner logical rows and mathematical signs/ranges require independent saved-result review.',
 artifact_metadata_observation_error=artifact_error,complete_saved_artifact_and_controls=complete,
 scientific_result_independently_reviewed=False,empty_feasibility_inferred_from_incomplete=False,
 saved_segment_diagnostic_invocation_count=1 if proc is not None else 0,automatic_retry=False,
 binary64_word_construction_authorized=False,raw_MSH_BIN_body_access_by_controller=False,
 hard_OS_quota=False,complete_stdlib_dynamic_OS_ABI_closure=False,
 resource_scope='Ordinary child60s/T8 and sampled direct-child RSS plus output/log bytes; no hard OS quota, peak or completion guarantee.',
 qualification={key:False for key in qualification})
p=D/'closed-result.json'
with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
p.chmod(0o444)
print(json.dumps(dict(receipt=rec(p),status=j['status'],returncode=j['returncode'],
 wall_seconds=j['wall_seconds'],stop_reason=stop,error=error,owned_group_absent=absent,
 complete19_916_artifact_metadata_consistent=complete_artifact,all_bound_inputs_runtime_and_controls_current=all_current)))
if not complete:raise SystemExit(2)
