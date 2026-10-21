"""Independent bounded read-only inspection of two already-saved cube meshes."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
RUN=ROOT/'work/962-engineering/hxt-size-cap-fixture-001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def canonical(face):
 f=tuple(int(x) for x in face);i=f.index(min(f));return f[i:]+f[:i]
def arrsha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
frozen=load(OUT/'frozen-contract.json')
for p,h in frozen['input_sha256'].items():
 if sha(ROOT/p)!=h:raise ValueError('Bound input changed: '+p)
contract=load(RUN/'contract.json');main=load(RUN/'receipt.json')
assert main['software_fixture_passed'] is True and main['head_accepted'] is False
assert main['contract_sha256']==frozen['native_contract_sha256']
for p,h in contract['source_sha256s'].items():
 assert sha(ROOT/p)==sha(RUN/'source-snapshots'/Path(p).name)==h
for p,h in contract['runtime_file_sha256s'].items():assert sha(Path(p))==h
import gmsh
runtime={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(Path(gmsh.__file__)),'gmsh_library':sha(Path(gmsh.lib._name))}
assert runtime==frozen['expected_actual_runtime_sha256'] and gmsh.__version__=='4.15.2' and platform.machine()=='arm64'
points=np.array([[0,0,0],[7,0,0],[7,7,0],[0,7,0],[0,0,7],[7,0,7],[7,7,7],[0,7,7]],dtype=float)
faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=int)+1
assert contract['geometry']['points']==points.tolist() and contract['geometry']['outward_triangles']==(faces-1).tolist()
source_boundary=sorted(canonical(f) for f in faces)
report={'schema':'962-size-cap-independent-saved-cube-review/v1','method':'Direct full saved-MSH coordinates, tetrahedra, all native qualities, independent volume and complete oriented tetra-face incidence; no generate/optimize/mesh-write/solve.','runtime_sha256':runtime,'cases':{},'head_geometry_loaded':False,'meshing_optimization_or_solve_calls':0,'head_execution_authorized':False,'head_accepted':False,'thermal_resolution_established':False,'manufacturing_authorized':False}
started=time.monotonic();gmsh.initialize([],readConfigFiles=False,run=False)
try:
 gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',2)
 for case in ['uncapped','capped-1p75']:
  b=RUN/case;rec=load(b/'receipt.json');worker=load(b/'worker-report.json')
  assert rec==main['cases'][case] and rec['returncode']==0 and rec['stop_reason'] is None
  assert rec['options']==worker['options']==contract['cases'][case]
  assert sha(b/'native.log')==rec['native_log_sha256'] and sha(b/'worker-report.json')==rec['worker_report_sha256']
  assert worker==rec['worker_report'] and worker['actual_runtime_sha256s']==runtime and worker['bound_inputs_unchanged'] is True
  assert worker['gmsh_warnings_errors']==[] and not any(x.startswith(('Warning','Error')) for x in (b/'native.log').read_text().splitlines())
  assert sha(b/'cube.msh')==worker['mesh_sha256'] and (b/'cube.msh').stat().st_size==worker['mesh_bytes']
  gmsh.open(str(b/'cube.msh'))
  tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order]
  assert len(np.unique(tags))==len(tags) and np.isfinite(xyz).all() and np.all((xyz>=0)&(xyz<=7))
  pos=np.searchsorted(tags,np.arange(1,9));assert np.array_equal(tags[pos],np.arange(1,9)) and np.array_equal(xyz[pos],points)
  types,et,en=gmsh.model.mesh.getElements(3);assert list(types)==[4]
  tet_tags=np.asarray(et[0]);conn=np.asarray(en[0]).reshape(-1,4);assert len(np.unique(tet_tags))==len(tet_tags)
  cells=np.searchsorted(tags,conn);assert np.array_equal(tags[cells],conn)
  referenced=np.unique(conn);inner=referenced[~np.isin(referenced,np.arange(1,9))];inside=xyz[np.searchsorted(tags,inner)]
  assert np.all((inside>0)&(inside<7))
  types2,_,nodes2=gmsh.model.mesh.getElements(2);assert list(types2)==[2]
  explicit=np.asarray(nodes2[0]).reshape(-1,3);assert sorted(canonical(f) for f in explicit)==source_boundary
  incidence={}
  for tet in conn:
   for ix in [[0,2,1],[0,1,3],[1,2,3],[2,0,3]]:
    f=tuple(int(v) for v in tet[ix]);key=tuple(sorted(f));incidence.setdefault(key,[]).append(f)
  exterior=[];internal=0
  for fs in incidence.values():
   assert len(fs)<=2
   if len(fs)==1:exterior.append(canonical(fs[0]))
   else:internal+=1;assert canonical(fs[0])==canonical(fs[1][::-1])
  assert sorted(exterior)==source_boundary
  x=xyz[cells];signed=np.einsum('ij,ij->i',x[:,1]-x[:,0],np.cross(x[:,2]-x[:,0],x[:,3]-x[:,0]))/6
  assert np.isfinite(signed).all() and np.all(signed>0) and math.fsum(signed)==343
  qualities={}
  for label,api,stored in [('SICN','minSICN','SICN'),('Jacobian','minDetJac','jacobian'),('volume_mm3','volume','volume_mm3')]:
   q=np.asarray(gmsh.model.mesh.getElementQualities(tet_tags,api));assert len(q)==len(conn) and np.isfinite(q).all()
   qualities[label]={'minimum':float(q.min()),'maximum':float(q.max()),'nonpositive_count':int(np.count_nonzero(q<=0)),'count':len(q),'array_sha256':arrsha(q)}
   assert qualities[label]['minimum']==worker['quality'][stored]['minimum'] and qualities[label]['maximum']==worker['quality'][stored]['maximum']
   if label!='SICN':assert np.all(q>0)
  values={'nodes':len(tags),'tetrahedra':len(conn),'referenced_nodes':len(referenced),'referenced_interior_nodes':len(inner),'all_counted_interior_nodes_strictly_inside_analytic_cube':True,'unreferenced_nodes':len(tags)-len(referenced),'boundary_triangles':len(exterior),'internal_opposite_face_pairs':internal,'exact_explicit_and_tetra_exterior_boundary':True,'native_quality':qualities,'independent_volume_mm3':{'minimum':float(signed.min()),'maximum':float(signed.max()),'sum':math.fsum(signed),'all_positive':True},'sorted_node_tags_sha256':arrsha(tags),'sorted_coordinates_sha256':arrsha(xyz),'tetra_tags_sha256':arrsha(tet_tags),'tagged_tetra_connectivity_sha256':arrsha(conn),'mesh_sha256':sha(b/'cube.msh'),'mesh_bytes':(b/'cube.msh').stat().st_size,'native_receipt_sha256':sha(b/'receipt.json'),'native_worker_sha256':sha(b/'worker-report.json'),'native_log_sha256':sha(b/'native.log'),'actual_head_SICN_point1_criterion_met_by_this_cube':qualities['SICN']['minimum']>=.1,'cube_does_not_qualify_head':True}
  for key,stored in [('nodes','total_nodes'),('tetrahedra','tetrahedra'),('referenced_nodes','referenced_nodes'),('referenced_interior_nodes','referenced_interior_nodes'),('unreferenced_nodes','unreferenced_nodes')]:assert values[key]==worker[stored]
  assert values['internal_opposite_face_pairs']==worker['internal_face_orientation']['internal_faces']
  report['cases'][case]=values;gmsh.clear()
finally:gmsh.finalize()
a,b=report['cases'].values();assert (a['nodes'],a['tetrahedra'],a['referenced_interior_nodes'])==(9,12,1);assert (b['nodes'],b['tetrahedra'],b['referenced_interior_nodes'])==(42,191,34)
assert b['referenced_interior_nodes']>a['referenced_interior_nodes'] and b['native_quality']['SICN']['minimum']<.1
for p,h in frozen['input_sha256'].items():assert sha(ROOT/p)==h
report.update(status='software_insertion_control_confirmed_no_head_acceptance',bound_inputs_unchanged=True,reader_wall_seconds=time.monotonic()-started,frozen_contract_sha256=sha(OUT/'frozen-contract.json'),native_contract_sha256=frozen['native_contract_sha256'],root_authorization_sha256=frozen['root_authorization_sha256'],main_native_receipt_sha256=sha(RUN/'receipt.json'))
with (OUT/'review.json').open('x') as f:f.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':report['status'],'cases':{k:{'nodes':v['nodes'],'tetrahedra':v['tetrahedra'],'interior_nodes':v['referenced_interior_nodes'],'min_SICN':v['native_quality']['SICN']['minimum']} for k,v in report['cases'].items()}}))
