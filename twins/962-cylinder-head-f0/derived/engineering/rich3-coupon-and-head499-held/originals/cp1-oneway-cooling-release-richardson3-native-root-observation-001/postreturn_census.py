"""One fixed post-return metadata census; no native or scientific execution."""
from pathlib import Path
import hashlib,json,os,sys,time
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993');E=R/'work/962-engineering'
OBS=Path(__file__).parent;D=E/'cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001';O=E/'cp1-oneway-cooling-release-richardson3-observer004-native-measurement-root-execution-001'
P=E/'cp1-oneway-cooling-release-richardson3-observer004-native-measurement-execution-prep-001/actual-contract.json'
META=E/'cp1-oneway-cooling-release-richardson3-current-metadata-root-001/fresh-preflight.json'
started=time.monotonic();c=json.loads(P.read_bytes());auth=json.loads((O/'authorization.json').read_bytes());meta=json.loads(META.read_bytes());raw_rc=int(sys.argv[1]);files={};errors=[]
def rec(p):
    assert p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,str(p)
    raw=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def check(pin):
    p=R/pin['path'];got=rec(p);assert got['sha256']==pin['sha256'] and got['bytes']==pin['bytes'],str(p)
    files[got['path']]=got
for pin in meta['canonical_body_records']:check(pin)
for pin in auth['direct_roles'].values():check(pin)
check({'path':str(O/'authorization.json'),'sha256':hashlib.sha256((O/'authorization.json').read_bytes()).hexdigest(),'bytes':(O/'authorization.json').stat().st_size})
for name,want in c['expected_provider_paths'].items():
    p=Path(name);got={'is_symlink':p.is_symlink(),'raw_target':os.readlink(p) if p.is_symlink() else None,'resolved':str(p.resolve(strict=True))};assert got==want,name
prefix=E/'moose-local-installed-002'
for name,want in c['runtime_symlinks'].items():assert (prefix/name).is_symlink() and os.readlink(prefix/name)==want
closed_path=O/'closed-result.json';closed=json.loads(closed_path.read_bytes()) if closed_path.is_file() else {};caller_path=D/'native-execution.json';caller=json.loads(caller_path.read_bytes()) if caller_path.is_file() else {}
summary={'schema':'962-rich3-root-postreturn-metadata/v1','raw_outer_returncode':raw_rc,'owner_status':closed.get('status'),'caller_status':caller.get('status'),'owner_top_level_keys':list(closed),'all442_current_body_posthashes_match':True,'all14_late_role_posthashes_match':True,'provider22_and_native13_routes_match':True,'native_output_files':sum(p.is_file() for p in D.rglob('*')),'native_execution_receipt_present':caller_path.is_file(),'closed_owner_receipt_present':closed_path.is_file(),'complete_streams_retained':True,'native_stdout_stderr_or_ps_bodies_decoded':False,'scientific_field_assessment_or_physical_acceptance':False,'full_external_clock_pending':True}
p=OBS/'postreturn.json';p.write_text(json.dumps(summary,indent=2)+'\n');p.chmod(0o444)
for root in (D,O,OBS):
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file():v=rec(p);files[v['path']]=v
historical=json.loads((R/c['historical_native_closed']['path']).read_bytes());baseline={n:v['bytes'] for n,v in historical['outputs'].items()}
growth=0
for root in (D,O,OBS):
    for p in root.rglob('*'):
        if p.is_file():growth+=max(0,p.stat().st_size-(baseline.get(str(p.relative_to(D)),0) if root==D else 0))
rows=list(sorted(files.values(),key=lambda v:v['path']));census={'schema':'962-rich3-complete-inclusive-postreturn-census/v1','records':rows,'canonical_paths_including_self':len(rows)+1,'self_counted_without_self_hash':True,'total_bytes_including_self':0,'growth_bytes_including_self':0,'inclusive_limit_bytes':536870912,'growth_limit_bytes':33554432,'all_named_identity_postchecks_pass':True,'clock_scope':'Final census is completed before the calling orchestration samples its ending UTC/JS clocks. Later terminal-clock audit records are separate.'}
p=OBS/'census.json'
for _ in range(20):
    raw=(json.dumps(census,indent=2)+'\n').encode();total=sum(x['bytes'] for x in rows)+len(raw);g=growth+len(raw)
    if census['total_bytes_including_self']==total and census['growth_bytes_including_self']==g:break
    census['total_bytes_including_self']=total;census['growth_bytes_including_self']=g
else:raise ValueError('Self byte census did not stabilize')
assert total<536870912 and g<33554432,(total,g)
p.write_bytes(raw);p.chmod(0o444)
print(json.dumps({'raw_outer_returncode':raw_rc,'owner_status':summary['owner_status'],'caller_status':summary['caller_status'],'owner_keys':list(closed),'canonical_paths':len(rows)+1,'inclusive_bytes':total,'growth_bytes':g,'census_sha256':hashlib.sha256(raw).hexdigest(),'census_bytes':len(raw),'postreturn_wall_seconds':time.monotonic()-started,'complete_postreturn_census_written':True}))
