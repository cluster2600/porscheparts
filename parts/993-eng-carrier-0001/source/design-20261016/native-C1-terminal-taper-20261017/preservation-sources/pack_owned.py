"""Pack only the fixed closed taper evidence; stdlib, no scientific reproduction."""
import hashlib, importlib.util, json, os, resource, signal, stat, sys
from pathlib import Path, PurePosixPath
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARCHIVES=('taper-common.zip','taper-rigid.zip','taper-spring.zip')
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for data in iter(lambda:f.read(1024**2),b''):h.update(data)
 return h.hexdigest()
def relative(value):
 p=PurePosixPath(value);require(bool(value)and p.parts and not p.is_absolute()and p.as_posix()==value and all(x not in ('','.','..')for x in p.parts),'Noncanonical relative path');return Path(*p.parts)
def regular(path):
 require(not any(q.is_symlink()for q in [path,*path.parents])and stat.S_ISREG(path.lstat().st_mode),'Regular source without symlink ancestors required')
def small(path):
 regular(path);require(path.stat().st_size<8*1024**2,'Only small control JSON may be parsed');return json.loads(path.read_text())
def write(path,value):
 with path.open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def inventory_archives(value):
 require(set(value['archives'])==set(ARCHIVES)and len(value['members'])==495,'Fixed three-group495 inventory required');out={name:{}for name in ARCHIVES}
 for name,row in value['members'].items():
  relative(name);require(not any(x in ('runtimes','site-packages','__pycache__')for x in Path(name).parts),'Runtime payload forbidden');require(type(row['bytes'])is int and row['bytes']>=0 and len(row['sha256'])==64,'Member size or digest malformed');require(row['archive_slot']in out,'Unknown archive');out[row['archive_slot']][name]=dict(bytes=row['bytes'],sha256=row['sha256'])
 for name,rows in out.items():
  expected=value['archives'][name];require(len(rows)==expected['member_count']and sum(x['bytes']for x in rows.values())==expected['uncompressed_bytes']and expected['maximum_compressed_bytes']==100000000,'Archive roster or bound changed')
 return out
def authorities(value,rows):
 for stage in value['stages']:
  r=ROOT/relative(stage['ROOT']);t=ROOT/relative(stage['terminal']);require(sha(r)==stage['ROOT_sha256']and sha(t)==stage['terminal_sha256'],'Closed stage ROOT/terminal changed');rv=small(r);tv=small(t)
  require(rv['terminal_sha256']==sha(t)and tv['status']==stage['historical_status'],'Closed stage terminal join differs');require(rv['actual_tool_RC']==(1 if stage['role']in ('prototype','STEP_refusal')else 0),'Historical native refusal/status differs')
  for field in ('assessment_sha256','supervision_sha256'):
   if field in rv:require(rv[field]==tv[field],'Stage ROOT and terminal result join differs')
 f=value['FEA_ROOT'];r=ROOT/relative(f['path']);t=ROOT/relative(f['owner_terminal']);require(sha(r)==f['sha256']and sha(t)==f['owner_terminal_sha256'],'Closed FEA authority changed');rv=small(r);tv=small(t);require(rv['actual_tool_RC']==0 and rv['terminal_sha256']==sha(t),'Closed FEA join differs')
 require(set(tv['cases'])=={'rigid','spring'},'Both closed FEA cases required')
 for key,case in tv['cases'].items():
  require(key in ('rigid','spring')and case['actual_tool_returncode']==case['actual_container_returncode']==0 and case['owned_container_removed'],'Owned native case not closed')
  require(len(case['whole_outputs_sha256'])==31 and all(rows['taper-'+key+'.zip'].get(n,{}).get('sha256')==digest for n,digest in case['whole_outputs_sha256'].items()),'Entire closed case inventory differs')
 require(value['candidate_qualified']is False and value['law_RC1_retained']and value['STEP_strict_refusal_retained']and value['stress_convergence']is False,'Historical scientific limits must remain explicit')
def verify(path,expected,execute=False):
 require(sha(path)==expected,'Reviewed pack control differs');p=small(path);require(p['schema']=='closed-new-taper-three-archive-pack-control-1'and p['bounds']==dict(outer=200,inner=180,CPU=[150,151],threads=1,workers=0),'Pack scope or bounds changed')
 if execute:require(p['launch_ready']is True and p['root_GO']and sha(ROOT/relative(p['root_GO']))==p['root_GO_sha256'],'Pack not armed')
 require(all(sha(ROOT/relative(n))==digest for n,digest in p['files_sha256'].items()),'Pack utility/control source changed');v=small(ROOT/relative(p['inventory']));rows=inventory_archives(v);authorities(v,rows)
 for members in rows.values():
  for name,row in members.items():
   q=ROOT/relative(name);regular(q);require(q.stat().st_size==row['bytes'],'Stored member size differs')
 out=ROOT/relative(p['destination']);require(not out.exists()and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh capsule destination required');require(not(ROOT/relative(p['actual_pack_plan'])).exists()and not(ROOT/relative(p['actual_pack_plan'])).with_name('packaging.json').exists(),'Pack receipts must be fresh')
 require(os.statvfs(HERE).f_bavail*os.statvfs(HERE).f_frsize>=p['minimum_free_bytes'],'Space reserve required');return p,v,rows,out

def pack(path,expected):
 p,v,rows,out=verify(path,expected,True);require(os.getpriority(os.PRIO_PROCESS,0)==10,'Owned child nice10 required');out.mkdir();actual_plan=ROOT/relative(p['actual_pack_plan']);write(actual_plan,dict(source_root=str(ROOT),destination=str(out),archives=rows))
 spec=importlib.util.spec_from_file_location('_unchanged_fixed_package',HERE/'package.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);require(sha(HERE/'package.py')==p['package_source_sha256'],'Original packer changed');mod.pack(actual_plan,sha(actual_plan))
 receipt=small(actual_plan.with_name('packaging.json'));require(receipt['originals_unchanged']and receipt['original_bytes']==sum(x['bytes']for a in rows.values()for x in a.values())and set(receipt['archives'])==set(ARCHIVES),'Actual whole-byte packing proof differs')
 files={}
 for dest,source in p['capsule_files'].items():
  dst=out/relative(dest);src=ROOT/relative(source);regular(src);dst.parent.mkdir(parents=True,exist_ok=True);before=src.stat();digest=hashlib.sha256();count=0
  with src.open('rb')as a,dst.open('xb')as b:
   for block in iter(lambda:a.read(1024**2),b''):b.write(block);digest.update(block);count+=len(block)
   b.flush();os.fsync(b.fileno())
  require(count==before.st_size and digest.hexdigest()==sha(src)==sha(dst)and mod.identity(before)==mod.identity(src.stat()),'Capsule utility copy changed');files[dest]=digest.hexdigest()
 template=small(ROOT/relative(p['manifest_template']));require(template['archives']is None and template['files_sha256']is None,'Only absent actual identities may be filled');template.update(archives=receipt['archives'],files_sha256=files);write(out/'manifest.json',template)
 write(out/'archive.json',dict(schema='standalone-taper-capsule-files-1',files_sha256={str(q.relative_to(out)):sha(q)for q in sorted(out.rglob('*'))if q.is_file()},new_solver_run=False,numerical_replay_executed=False))
 require(all(sha(ROOT/relative(n))==digest for n,digest in p['files_sha256'].items())and sha(path)==expected,'Control/source changed during packaging');print(json.dumps(dict(status='actual_three_archives_and_standalone_manifest_created_not_verified_or_replayed',manifest_sha256=sha(out/'manifest.json'),archive_sha256=sha(out/'archive.json'),archives={n:dict(bytes=x['bytes'],sha256=x['sha256'])for n,x in receipt['archives'].items()},members=495,new_solver_run=False)))
if __name__=='__main__':
 mode,path,digest=sys.argv[1:];path=Path(path)
 if mode=='preflight':p,_,_,_=verify(path,digest);print(json.dumps(dict(status='source_only_pack_preflight_no_body_scan',launch_ready=p['launch_ready'],small_pins=len(p['files_sha256']))))
 elif mode=='pack':
  resource.setrlimit(resource.RLIMIT_CPU,(150,151));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180s packaging cap')));signal.alarm(180)
  try:pack(path,digest)
  finally:signal.alarm(0)
 else:raise ValueError('Only preflight or reviewed pack allowed')
