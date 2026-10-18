"""Derive only historical-observation labels and the corresponding fresh pending controls."""
from pathlib import Path
import ast,copy,difflib,hashlib,json,os
H=Path(__file__).resolve().parent;OLD=H.with_name('carrier-seven-edge-law-figure-preparation-001');R=H.parents[1]
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def enc(v):return(json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def read(q):return json.loads(q.read_bytes())
def save(q,b):
    with q.open('xb')as f:f.write(b);f.flush();os.fsync(f.fileno())
edits={
 'figure.py':[
  ('Plot the closed requested/native seven-edge law; no CAD import or native operation.','Plot the closed seven-edge law observation snapshot; no CAD import or native operation.'),
  ('One valid raw Solid saved; all downstream geometry checks remain PENDING.','At the law observation, geometry gates were pending; one valid raw Solid was saved.'),
  ('Law behavior only. No Cut, mass, interfaces, surface, STEP, mesh or FEA check is transferred from earlier candidates.','Historical law observation only. Later geometry checks are separate; none is transferred into the law proof.'),
  ("candidate_qualified=False,downstream_geometry_gates='PENDING',wall_seconds=", "candidate_qualified=False,downstream_geometry_gates='PENDING',downstream_geometry_gate_status_scope='historical_at_the_law_observation',wall_seconds=")],
 'README.md':[
  ('These facts establish the closed law observation only;\nall separate geometry, mass, interfaces, surface, STEP, mesh and FEA gates\nremain pending. Earlier study cases and Figure 28 are unchanged.',
   'These facts describe the closed law observation snapshot. At that observation,\ngeometry, mass, interfaces, surface, STEP, mesh and FEA gates were pending. Later\nreceipts belong to their own checks and are not transferred into this law proof.\nThe PENDING fields in law-data.json are historical snapshot values, not a current\nglobal gate assessment. Earlier study cases and Figure 28 are unchanged.')]
}
changes={}
for name,replacements in edits.items():
    original=(OLD/name).read_text();new=original;rows=[]
    for before,after in replacements:
        assert new.count(before)==1;new=new.replace(before,after,1);rows.append(dict(before=before,after=after,count=1))
    back=new
    for e in reversed(rows):assert back.count(e['after'])==1;back=back.replace(e['after'],e['before'],1)
    assert back==original;save(H/name,new.encode());save(H/(name+'.diff'),''.join(difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='001/'+name,tofile='002/'+name)).encode())
    changes[name]=dict(original_path=str((OLD/name).relative_to(R)),original_sha256=sha(OLD/name),new_sha256=sha(H/name),replacements=rows,whole_inverse_equal=True)
for name in ['law-data.json','selfcheck.py','dependency-inventory.json','ARMING.md']:save(H/name,(OLD/name).read_bytes())
oldtree=ast.parse((OLD/'figure.py').read_text());newtree=ast.parse((H/'figure.py').read_text());bodies=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,ast.FunctionDef)}
a,b=bodies(oldtree),bodies(newtree);assert[k for k in a if a[k]!=b[k]]==['render']
record=dict(schema='law-figure-historical-label-source-revision-1',file_changes=changes,unchanged_byte_files={n:sha(H/n)for n in['law-data.json','selfcheck.py','dependency-inventory.json','ARMING.md']},all_function_AST_unchanged_except_render=True,render_changes_only_two_English_labels_and_snapshot_scope_metadata=True,scientific_values_proofs_native_records_and_runtime_unchanged=True,old_preparation_immutable=True)
save(H/'source-changes.json',enc(record))
oldp=read(OLD/'pending-plan.json');p=copy.deepcopy(oldp)
local=['figure.py','law-data.json','selfcheck.py','README.md','dependency-inventory.json']
for name in local:
    del p['files_sha256'][str((OLD/name).relative_to(R))];p['files_sha256'][str((H/name).relative_to(R))]=sha(H/name)
for name in ['source-changes.json','selfcheck_revision.py',Path(__file__).name]:p['files_sha256'][str((H/name).relative_to(R))]=sha(H/name)
p['data']=str((H/'law-data.json').relative_to(R));p['output_directory']=str((H/'render-001').relative_to(R));p['downstream_geometry_gate_status_scope']='historical_at_the_law_observation'
save(H/'pending-plan.json',enc(p))
oldl=read(OLD/'pending-launch.json');l=copy.deepcopy(oldl)
for name in local:del l['inputs_sha256'][str((OLD/name).relative_to(R))];l['inputs_sha256'][str((H/name).relative_to(R))]=sha(H/name)
for name in ['source-changes.json','selfcheck_revision.py',Path(__file__).name]:l['inputs_sha256'][str((H/name).relative_to(R))]=sha(H/name)
del l['inputs_sha256'][str((OLD/'pending-plan.json').relative_to(R))];l['inputs_sha256'][str((H/'pending-plan.json').relative_to(R))]=sha(H/'pending-plan.json')
del l['source_sha256'][str((OLD/'figure.py').relative_to(R))];l['source_sha256'][str((H/'figure.py').relative_to(R))]=sha(H/'figure.py')
l['command'][2]=str(H/'figure.py');l['command'][4]=str(H/'plan.json');l['command'][6]=str(H/'render-001');l['output_directory']=str((H/'render-001').relative_to(R));l['execution_directory']=str((H/'execution-001').relative_to(R));save(H/'pending-launch.json',enc(l))
oldc=read(OLD/'pending-command.json');c=copy.deepcopy(oldc);c['argv'][4]=str(H/'launch-plan.json');c['pending_plan_sha256']=sha(H/'pending-plan.json');c['pending_launch_sha256']=sha(H/'pending-launch.json');save(H/'pending-command.json',enc(c))
# Compute exact leaf edits for each whole pending object; maps/runtimes not changed remain outside this delta.
def differences(old,new,path=()):
    if isinstance(old,dict)and isinstance(new,dict):
        out=[]
        for key in sorted(set(old)|set(new)):
            if key not in old:out.append(dict(path=list(path+(key,)),before_present=False,after_present=True,after=new[key]))
            elif key not in new:out.append(dict(path=list(path+(key,)),before_present=True,after_present=False,before=old[key]))
            else:out+=differences(old[key],new[key],path+(key,))
        return out
    if isinstance(old,list)and isinstance(new,list)and len(old)==len(new):
        return[e for i,(x,y)in enumerate(zip(old,new))for e in differences(x,y,path+(i,))]
    return[]if old==new else[dict(path=list(path),before_present=True,after_present=True,before=old,after=new)]
controls={}
for name,old,new in [('pending-plan.json',oldp,p),('pending-launch.json',oldl,l),('pending-command.json',oldc,c)]:
    delta=differences(old,new);restored=copy.deepcopy(new)
    for e in reversed(delta):
        node=restored
        for k in e['path'][:-1]:node=node[k]
        k=e['path'][-1]
        if e['before_present']:node[k]=e['before']
        else:del node[k]
    assert restored==old and enc(restored)==(OLD/name).read_bytes();controls[name]=dict(original_path=str((OLD/name).relative_to(R)),original_sha256=sha(OLD/name),new_sha256=sha(H/name),changes=delta,whole_object_and_original_bytes_inverse_equal=True)
save(H/'control-changes.json',enc(dict(schema='law-figure-002-whole-pending-object-derivation-1',controls=controls)))
print(json.dumps(dict(source_sha256=sha(H/'figure.py'),data_sha256=sha(H/'law-data.json'),plan_sha256=sha(H/'pending-plan.json'),launch_sha256=sha(H/'pending-launch.json'),command_sha256=sha(H/'pending-command.json'),source_changes_sha256=sha(H/'source-changes.json'),control_changes_sha256=sha(H/'control-changes.json'))))
