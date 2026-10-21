"""Independent byte identities and raw sixteen-state nodal work; no solver call."""
from pathlib import Path
import hashlib,json,math
import numpy as np
root=Path.cwd();binding=root/'work/part-workflow/run001-constitutive-binding-002';b=json.loads((binding/'binding.json').read_text());old=root/b['retained_original_folder'];new=root/'work/part-workflow/run-001/cad';out=root/'work/carrier-design-20261016/constitutive-binding-independent-002.json'
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not out.exists()
assert all(h(Path(path))==value for path,value in b['inputs_sha256'].items())
assert all(h(binding/name)==value for name,value in b['outputs_sha256'].items())
assert h(old/'mesh.npz')==h(new/'mesh-9/mesh.npz')==b['identical_mesh_npz_sha256']
assert h(old/'reference-linear.inp')==h(new/'mesh-9/combined-spring-1000-static.inp')==b['identical_reference_deck_sha256']
def strip_heading(path):
 lines=path.read_text().splitlines(keepends=True);kept=[];drop=False
 for line in lines:
  if line.strip().upper()=='*HEADING':drop=True;continue
  if drop and line.startswith('*') and not line.startswith('**'):drop=False
  if not drop:kept.append(line)
 return ''.join(kept).encode()
oldmesh,newmesh=strip_heading(old/'mesh.inp'),strip_heading(new/'mesh-9/mesh.inp');assert oldmesh==newmesh
with np.load(old/'mesh.npz',allow_pickle=False) as a,np.load(new/'mesh-9/mesh.npz',allow_pickle=False) as c:
 assert set(a.files)==set(c.files)
 assert all(np.array_equal(a[k],c[k]) and a[k].dtype==c[k].dtype for k in a.files)
 tags=a['tags'].copy();xyz=a['xyz'].copy()
def blocks(path):
 result=[]
 for raw in path.read_text().splitlines():
  line=raw.strip()
  if not line or line.startswith('**'):continue
  if line.startswith('*'):result.append((line.upper().replace(' ',''),[]))
  else:result[-1][1].append(line)
 return result
runtime=json.loads((old/'runtime.json').read_text());name=runtime['name'];deck=blocks(old/(name+'.inp'));reference=blocks(old/'reference-linear.inp')
relevant=lambda d:[(key,rows) for key,rows in d if key.startswith(('*SPRING,','*ELEMENT,TYPE=SPRING1','*BOUNDARY')) or key=='*CLOAD']
assert relevant(deck)==relevant(reference),'Reference loads/springs differ from nonlinear model initial data'
load=np.zeros_like(xyz);k=np.zeros_like(xyz);sets={}
for key,rows in deck:
 if key=='*CLOAD':
  for row in rows:
   node,dof,value=row.split(',');i=np.searchsorted(tags,int(node));assert tags[i]==int(node);load[i,int(dof)-1]+=float(value)
 elif key.startswith('*ELEMENT,TYPE=SPRING1'):sets[key.split('ELSET=')[1]]=[int(row.split(',')[1]) for row in rows]
 elif key.startswith('*SPRING,'):
  ids=np.searchsorted(tags,sets.pop(key.split('ELSET=')[1]));k[ids,int(rows[0])-1]+=float(rows[1])
assert not sets
widths={'displacements':4,'forces':4,'stresses':8,'equivalent plastic strain':3,'internal energy density':3};counts={key:{} for key in widths};displacements={};peaks={};active=None;time=None;urows=[]
def finish():
 if active=='displacements':displacements[time]=np.asarray(urows)
with (old/(name+'.dat')).open() as stream:
 for line in stream:
  clean=line.strip()
  if 'for set ' in clean and 'time ' in clean:
   finish();active=next((key for key in widths if clean.startswith(key+' (')),None);time=float(clean.rsplit('time',1)[1]);urows=[]
   if active:assert time not in counts[active];counts[active][time]=0
  elif active:
   fields=clean.split()
   if len(fields)==widths[active] and fields[0].isdigit():
    counts[active][time]+=1
    if active=='displacements':urows.append([float(v) for v in fields])
    elif active=='equivalent plastic strain':peaks[time]=max(peaks.get(time,0.),float(fields[-1]))
finish()
analysis=json.loads((binding/'luo-flat1-analysis.json').read_text());work=json.loads((binding/'luo-flat1-finite-work.json').read_text());times=[i/8 for i in range(1,17)]
assert all(sorted(v)==times for v in counts.values())
assert [f['total_time'] for f in analysis['frames']]==[f['total_time'] for f in work['frames']]==times
assert h(old/(name+'.dat'))==work['solver_dat_sha256']==analysis['inputs_sha256'][name+'.dat']
# Roundoff comparison only: printed raw fields and identical loads. No change to the independent work tolerance.
atol,rtol=1e-7,1e-12
previous=np.zeros_like(xyz);previous_factor=0.;cumulative=0.;rows=[]
for t,af,wf in zip(times,analysis['frames'],work['frames']):
 data=displacements[t];assert np.array_equal(data[:,0],tags);u=data[:,1:];factor=t if t<=1 else 2-t
 ext=float(.5*(factor+previous_factor)*np.sum(load*(u-previous)));spring=float(.5*np.sum(k*(u*u-previous*previous)));cumulative+=ext
 assert math.isclose(ext,wf['external_work_increment_Nmm'],rel_tol=rtol,abs_tol=atol)
 assert math.isclose(spring,wf['spring_work_increment_Nmm'],rel_tol=rtol,abs_tol=atol)
 assert math.isclose(cumulative,wf['external_cumulative_work_Nmm'],rel_tol=rtol,abs_tol=atol)
 assert math.isclose(cumulative,af['external_incremental_trapezoid_work_Nmm'],rel_tol=rtol,abs_tol=atol)
 assert np.max(np.linalg.norm(u,axis=1))==af['displacement_max_mm']
 assert peaks[t]==af['PEEQ_max'] and factor==af['load_factor']==wf['load_factor']
 rows.append({'total_time':t,'load_factor':factor,'raw_displacement_rows':counts['displacements'][t],'raw_stress_rows':counts['stresses'][t],'PEEQ_max':peaks[t],'external_increment_Nmm':ext,'spring_increment_Nmm':spring,'external_cumulative_Nmm':cumulative,'independent_work_pass_retained':wf['work_pass']})
 previous,previous_factor=u,factor
assert len(rows)==16 and work['all_frames_pass'] and b['ENER_all_frames_pass'] is False and analysis['all_frames_ENER_diagnostic_pass'] is False
report={'status':'passed','binding_json_sha256':h(binding/'binding.json'),'own_source_sha256':h(__file__),'mesh_NPZ_sha256':h(old/'mesh.npz'),'reference_deck_sha256':h(old/'reference-linear.inp'),'mesh_INP_after_only_heading_removal_sha256':hashlib.sha256(oldmesh).hexdigest(),'NPZ_all_arrays_and_dtypes_exact':True,'only_mesh_heading_differs':True,'loads_and_spring_blocks_identical':True,'raw_DAT_sha256':h(old/(name+'.dat')),'frames':rows,'work_comparison_roundoff_only':{'atol_Nmm':atol,'rtol':rtol},'ENER_all_frames_pass_retained':False,'independent_work_all_frames_pass_retained':True,'STEP_identity_inferred':False,'source_STEP_sha256':b['source_geometry_STEP_sha256'],'current_STEP_sha256':b['current_geometry_STEP_sha256'],'new_solver_or_geometry_run':False}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:value for key,value in report.items() if key!='frames'}))
