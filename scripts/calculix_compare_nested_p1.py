"""Compare complete admitted nested P1 fields under an explicit identical load case.

Requires complete assessment artifacts; this does not execute a solver or grant
strength, manufacturing or spatial-convergence acceptance."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def density(s,E,nu):return ((1+nu)*(s[:,:3]**2).sum(1)-nu*s[:,:3].sum(1)**2+2*(1+nu)*(s[:,3:]**2).sum(1))/(2*E)
def controls():
 K=np.array([[2.,-1.],[-1.,2.]]);f=np.array([1.,0.]);P=np.array([[1.],[.2]]);uc=P@np.linalg.solve(P.T@K@P,P.T@f);uf=np.linalg.solve(K,f);e=uf-uc;dw=float(f@(uf-uc));assert dw>0 and abs(e@K@e-dw)<1e-15
 s=np.eye(6);d=density(s,100.,.3);assert np.allclose(d[:3],.005) and np.allclose(d[3:],.013)
 assert np.all(density(np.zeros((3,6)),100.,.3)==0)
 return {'Galerkin_energy_increment_identity':True,'six_independent_compliance_components':True,'zero_increment':True}
def check_nested_connectivity(coarse,fine,parents,edges,old_vertex_count):
 parents=np.asarray(parents,dtype=np.int64);edges=np.asarray(edges,dtype=np.int64)
 assert fine.shape==(len(coarse)+len(parents),4) and len(np.unique(parents))==len(parents)
 assert np.all((parents>=0)&(parents<len(coarse))) and edges.ndim==2 and edges.shape[1]==2
 selected=np.zeros(len(coarse),dtype=bool);selected[parents]=True;used=np.zeros(len(edges),dtype=bool)
 for begin in range(0,len(coarse),65536):
  end=min(begin+65536,len(coarse));keep=~selected[begin:end];assert np.array_equal(coarse[begin:end][keep],fine[begin:end][keep]),'Unrefined connectivity changed'
 for begin in range(0,len(parents),65536):
  end=min(begin+65536,len(parents));ids=parents[begin:end];p=coarse[ids];f=fine[ids];g=fine[len(coarse)+begin:len(coarse)+end];newf=f>=old_vertex_count;newg=g>=old_vertex_count
  assert np.all(newf.sum(1)==1) and np.all(newg.sum(1)==1),'Each child needs exactly one new midpoint'
  mf=f[np.arange(len(f)),newf.argmax(1)];mg=g[np.arange(len(g)),newg.argmax(1)];assert np.array_equal(mf,mg),'Child pair uses different midpoints';eidx=mf-old_vertex_count;assert np.all((eidx>=0)&(eidx<len(edges)));used[eidx]=True;e=edges[eidx]
  assert np.all((e[:,:,None]==p[:,None,:]).any(2)),'Midpoint edge not in parent'
  for child,new in [(f,newf),(g,newg)]:
   assert np.all(np.diff(np.sort(child,axis=1),axis=1)>0),'Repeated child vertex'
   assert np.all((child[:,:,None]==p[:,None,:]).any(2)|new),'Child has foreign original vertex'
  fa=(f==e[:,0,None]).any(1);fb=(f==e[:,1,None]).any(1);ga=(g==e[:,0,None]).any(1);gb=(g==e[:,1,None]).any(1)
  assert np.all(fa^fb) and np.array_equal(fa,gb) and np.array_equal(fb,ga),'Children do not bisect opposite edge endpoints'
 assert used.all(),'Unused midpoint in nesting map'
 return dict(all_unchanged_cells_bitwise_identical=True,all_child_pairs_bound_to_actual_parent_connectivity=True,all_midpoint_edges_used=True,split_parents=len(parents),new_interior_nodes=len(edges))

def nesting_controls():
 c=np.array([[0,1,2,3]]);f=np.array([[0,4,2,3],[4,1,2,3]]);p=np.array([0]);e=np.array([[0,1]]);check_nested_connectivity(c,f,p,e,4)
 bad=[(f,p,np.array([[0,2]])),(np.array([[0,4,2,3],[5,1,2,3]]),p,e),(np.array([[0,4,1,3],[4,1,2,3]]),p,e)]
 for changed,parents,edges in bad:
  try:check_nested_connectivity(c,changed,parents,edges,4)
  except AssertionError:pass
  else:raise AssertionError('Damaged parent/child binding admitted')
 return dict(actual_parent_child_valid_case=True,foreign_edge_refused=True,different_midpoint_refused=True,missing_parent_vertex_refused=True)

def load_binding(source,refined,load_case):
 assert load_case in ('gravity','combined'),'Explicit supported load case required'
 for report in (source,refined):
  declared=report.get('load_case')
  assert declared==load_case or (load_case=='gravity' and declared is None),'Admitted load case differs'
  suffix='/current-'+load_case+'/case/job.dat'
  assert any(str(path).endswith(suffix) for path in report['source_sha256']),'Current DAT execution does not match requested load case'
 for name in ['groups.npz',load_case+'-serialized-loads.npz']:
  assert source['payload_source_sha256'][name]==refined['payload_source_sha256'][name],'Load/support functional differs'
 return True

def main():
 import argparse
 p=argparse.ArgumentParser(__doc__);p.add_argument('--load-case',choices=('gravity','combined'),required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--refined',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();q=controls();q.update(nesting_controls())
 reports=[a.source/'assessment.json',a.refined/'assessment.json'];r0,r1=[json.loads(p.read_text()) for p in reports];assert all(r['status']=='complete_current_P1_equilibrium_and_energy_passed' for r in [r0,r1])
 v0=np.load(a.source/'decoded/vertices.npy',mmap_mode='r');v1=np.load(a.refined/'decoded/vertices.npy',mmap_mode='r');assert np.array_equal(v0.view(np.uint64),v1[:len(v0)].view(np.uint64))
 m=np.load(a.map);parents=m['appended_parent_indices'];removed=m['replaced_parent_indices'];edges=m['midpoint_edges'];assert np.array_equal(parents,removed) and len(np.unique(parents))==len(parents)
 n0=r0['counts']['s'];n1=r1['counts']['s'];assert n1==n0+len(parents) and len(v1)==len(v0)+len(edges)
 assert np.array_equal(v1[len(v0):].view(np.uint64),((v0[edges[:,0]]+v0[edges[:,1]])/2).view(np.uint64))
 c0=np.load(a.source/'decoded/cells.npy',mmap_mode='r');c1=np.load(a.refined/'decoded/cells.npy',mmap_mode='r');nesting=check_nested_connectivity(c0,c1,parents,edges,len(v0))
 u0=np.load(a.source/'fields/u.npy',mmap_mode='r');u1=np.load(a.refined/'fields/u.npy',mmap_mode='r');s0=np.load(a.source/'fields/s.npy',mmap_mode='r');s1=np.load(a.refined/'fields/s.npy',mmap_mode='r');vol=np.load(a.refined/'fields/volumes.npy',mmap_mode='r')
 # Assessor names the evaluated integration volumes volumes.npy.
 materials=[]
 for folder,report in [(a.source,r0),(a.refined,r1)]:
  candidates=[folder.parent/'report.json',folder.parent/'assessment-payload/report.json'];bound=[p for p in candidates if str(p.resolve()) in report['source_sha256']]
  assert len(bound)==1 and sha(bound[0])==report['source_sha256'][str(bound[0].resolve())],'Material source not bound to admitted field'
  materials.append(json.loads(bound[0].read_text())['material'])
 assert materials[0]==materials[1],'Material differs between levels'
 load_binding(r0,r1,a.load_case)
 material=materials[1];terms=[];maxdu=0.;sumdu=0.;sumu=0.
 for begin in range(0,n1,65536):
  end=min(begin+65536,n1);ids=np.arange(begin,end);source_ids=ids.copy();new=ids>=n0;source_ids[new]=parents[ids[new]-n0];ds=s1[begin:end]-s0[source_ids];terms.append(math.fsum((vol[begin:end]*density(ds,material['E_MPa'],material['nu'])).tolist()))
 for begin in range(0,len(v0),65536):
  end=min(begin+65536,len(v0));du=u1[begin:end]-u0[begin:end];maxdu=max(maxdu,float(np.linalg.norm(du,axis=1).max()));sumdu+=float((du**2).sum());sumu+=float((u0[begin:end]**2).sum())
 middu=u1[len(v0):]-(u0[edges[:,0]]+u0[edges[:,1]])/2;maxdu=max(maxdu,float(np.linalg.norm(middu,axis=1).max()))
 e=math.fsum(terms);dw=r1['external_work_Nmm']-r0['external_work_Nmm'];W=r1['external_work_Nmm']
 metrics=['external_work_Nmm','displacement_max_mm','VM_volume_weighted_p95_MPa','VM_peak_MPa'];changes={k:dict(source=r0[k],refined=r1[k],relative_change=(r1[k]-r0[k])/r0[k]) for k in metrics}
 result=dict(load_case=a.load_case,status='complete_same_load_nested_P1_increment_measured',controls=q,nested_connectivity_binding=nesting,source_sha256={str(p):sha(p) for p in reports+[a.map,Path(__file__)]},source_cells=n0,refined_cells=n1,added_free_interior_nodes=len(edges),all_original_vertex_bytes_unchanged=True,same_load_and_boundary_binding_checked_by_both_assessors=True,metrics=changes,prolongated_displacement_max_difference_mm=maxdu,original_node_displacement_l2_relative=math.sqrt(sumdu/sumu),stress_difference_compliance_energy_Nmm=e,normalized_energy_difference=math.sqrt(2*e/W),compliance_increment_Nmm=dw,Galerkin_identity_defect_Nmm=dw-2*e,Galerkin_identity_defect_relative_to_work=abs(dw-2*e)/W,monotonic_work_observed=dw>=0,spatial_convergence_demonstrated=False,strength_qualified=False,scope='One complete nested same-load increment. Printed-field and numerical errors remain visible; at least another admitted increment is needed for stabilization assessment.')
 a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
