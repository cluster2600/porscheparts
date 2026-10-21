"""HELD disconnected sparse-tag28-to39 API editing fixture; no head or mesher."""
from pathlib import Path
from fractions import Fraction
import hashlib,importlib.util,json,math,struct,sys,time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
CAVITY='work/962-engineering/fixed-shell-generation-apex1435493-prep-001/reader.py'
CAVITY_SHA='d5f23d2512d0cdc53c3f648eaca6b3c5aba3105b4b3d14470ceab5761afd5879'
CUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
CUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
WORKER_SHA='8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
ARRAYS_SHA='ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f'
CANDIDATE='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
CANDIDATE_SHA='e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a'
PEER='work/962-engineering/fixed-shell-coupled-sicn-result-peer-001/review.json'
PEER_SHA='0adbeea0bef35c5a1f30f610c87bb27ef4333530ff2039e9e4c91a512287732b'
FREE=[27,28,29]
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
AUDIT_INPUTS={
 'twins/962-cylinder-head-f0/source/mesh_head.py':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5',
 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py':'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4',
 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json':'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}

OBSERVATION='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json'
OBSERVATION_SHA='53a1fb5696d46c8773eea0ffd3a971706946b380a0b3a5f5ba41d1d6a121d15a'
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Algorithm3D':1,
 'Mesh.MeshOnlyEmpty':1,'Mesh.Renumber':0,'Mesh.ElementOrder':1,'Mesh.Optimize':0,
 'Mesh.OptimizeNetgen':0,'Mesh.MeshSizeExtendFromBoundary':0,'Mesh.RandomSeed':1,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
COUNTS={'generate':0,'createGeometry_dim3':0,'optimize_Netgen':0,'setNode':1,
 'removeElements':1,'addNodes':5,'addElementsByType':5,'rebuildNodeCache':1,
 'rebuildElementCache':1,'reclassifyNodes':0,'write_mesh':1,'solve':0}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_cavity_module():
 spec=importlib.util.spec_from_file_location('frozen_specific_cavity_audit',ROOT/CAVITY)
 cavity=importlib.util.module_from_spec(spec);spec.loader.exec_module(cavity)
 return cavity
def candidate_rows(d,a):
 tags=list(range(1,17))+FREE
 if (d.get('status') not in ['exact_feasible_point_solver_converged_native_unapproved','feasible_point_solver_not_converged']
     or d.get('all39_exact_quality_gate') is not True or d.get('procedural_checks_passed') is not True
     or d.get('all16_shell_coordinate_bits_unchanged') is not True or d.get('original_array_bits_unchanged') is not True
     or d.get('free_tags')!=FREE or d.get('full_source_nodes')!=19 or d.get('full_cells')!=39
     or a['node_tags']!=tags or len(a['tetra_tags'])!=39 or len(a['tetra_node_tags'])!=39):
  raise ValueError('Exact finite all39 analytic candidate and original19/39 association required')
 if any(d['input_hashes'].get(str(ROOT/name))!=digest for name,digest in [(ARRAYS,ARRAYS_SHA),(WORKER,WORKER_SHA),(SHELL,AUDIT_INPUTS[SHELL])]):
  raise ValueError('Candidate source-state direct pins differ')
 qualification={'native_application_authorized':False,'head_execution_authorized':False,'stitching_authorized':False,
  'engineering_accepted':False,'physics_qualified':False,'manufacturing_authorized':False}
 if d.get('qualification')!=qualification:raise ValueError('Analytic candidate grants no native/head/physical authority')
 rows=d['complete_proposed_coordinate_rows']
 if [r['node_tag'] for r in rows]!=tags or len(rows)!=19:raise ValueError('All19 sorted candidate rows required')
 old=dict(zip(a['node_tags'],a['coordinates_mm']));coordinates=[];changes=[]
 for row in rows:
  t=row['node_tag'];xyz=row['coordinates_mm'];words=row['binary64_hex']
  if (len(xyz)!=3 or len(words)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz)
      or any(type(h) is not str or float(v).hex()!=h or struct.pack('<d',float.fromhex(h))!=struct.pack('<d',v) for v,h in zip(xyz,words))):
   raise ValueError('Exact finite candidate coordinate/hex association required')
  changed=struct.pack('<3d',*xyz)!=struct.pack('<3d',*old[t])
  if changed and t not in FREE:raise ValueError('Any shell coordinate bit drift refused')
  if changed:changes.append(t)
  coordinates.append([float(v) for v in xyz])
 exact=d['all39_signed_quality_rows']
 if len(exact)!=39 or [row['tetrahedron_tag'] for row in exact]!=a['tetra_tags']:
  raise ValueError('Complete39 exact candidate cell identities required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_native_ordered_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('positive_orientation') is not True or proof.get('exact_point1_gate_passed') is not True
      or not isinstance(q,dict) or Fraction(int(det['numerator']),int(det['denominator']))<=0
      or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every saved exact candidate determinant/quality gate required')
 return coordinates,changes

NODE_TAGS = tuple(range(101, 109)) + (201,)

BOUNDARY = ((-1.,-1.,-1.),(1.,-1.,-1.),(1.,1.,-1.),(-1.,1.,-1.),
            (-1.,-1.,1.),(1.,-1.,1.),(1.,1.,1.),(-1.,1.,1.))

TRIANGLES = ((101,103,102),(101,104,103),(105,106,107),(105,107,108),
             (101,102,106),(101,106,105),(104,108,107),(104,107,103),
             (101,105,108),(101,108,104),(102,103,107),(102,107,106))

TETS = tuple((201,)+f for f in TRIANGLES)

CENTRE = (0., 0., 0.)


def make_case(observation,shell,candidate,arrays):
 if observation.get('apex')!=1435493 or len(observation['native_ordered_cell_rows'])!=28:
  raise ValueError('Exact original28-cell star required')
 coordinates,changes=candidate_rows(candidate,arrays['saved_reopen'])
 if changes!=[28,29]:raise ValueError('Specific reviewed candidate coordinate changes required')
 points={r['node_tag']:r['coordinates_mm'] for r in observation['selected_node_rows']}
 if len(points)!=17 or sorted(points)!=sorted(shell['local_to_global_node_tags']+[1435493]):
  raise ValueError('Original17node association required')
 for r in observation['selected_node_rows']:
  if [float(v).hex() for v in r['coordinates_mm']]!=r['binary64_hex']:
   raise ValueError('Original coordinate/hex mismatch')
 for r in shell['vertex_rows']:
  if struct.pack('<3d',*points[r['source_global_node_tag']])!=struct.pack('<3d',*r['coordinates_mm']):
   raise ValueError('Shell coordinate bits changed')
 old={r['tetrahedron_tag']:r['node_tags'] for r in observation['native_ordered_cell_rows']}
 if len(old)!=28 or any(1435493 not in row or len(row)!=4 or len(set(row))!=4 for row in old.values()) or set(x for row in old.values() for x in row)!=set(points):
  raise ValueError('Complete nonempty native28star rows required')
 cube_nodes={t:9000001+101*i for i,t in enumerate(NODE_TAGS)}
 cube_points={cube_nodes[t]:list(xyz) for t,xyz in zip(NODE_TAGS,BOUNDARY+(CENTRE,))}
 cube_cells={50000001+103*i:[cube_nodes[t] for t in row] for i,row in enumerate(TETS)}
 triangles={90000001+107*i:[cube_nodes[t] for t in row] for i,row in enumerate(TRIANGLES)}
 diagnostic={70000001+109*i:[shell['local_to_global_node_tags'][x-1] for x in r['local_node_tags']] for i,r in enumerate(shell['oriented_triangle_rows'])}
 triangles={**diagnostic,**triangles}
 if set(points)&set(cube_points) or set(old)&(set(cube_cells)|set(triangles)):
  raise ValueError('Sparse fixture tags collided')
 points.update(cube_points);cells={**old,**cube_cells};nmax=max(points);emax=max([*cells,*triangles])
 node_map={i+1:t for i,t in enumerate(shell['local_to_global_node_tags'])}
 node_map.update({27:1435493,28:nmax+1,29:nmax+2})
 element_slots=sorted(old)+list(range(emax+1,emax+12))
 if len(element_slots)!=39 or len(set(element_slots))!=39:raise ValueError('Exactly28freed plus11fresh cell slots required')
 replacement={t:[node_map[x] for x in row] for t,row in zip(element_slots,arrays['saved_reopen']['tetra_node_tags'])}
 proposed=dict(points)
 for tag,xyz in zip(list(range(1,17))+FREE,coordinates):proposed[node_map[tag]]=xyz
 classes={t:[2,401] for t in shell['local_to_global_node_tags']};classes[1435493]=[3,11]
 classes.update({cube_nodes[t]:[2,501] for t in NODE_TAGS[:-1]});classes[cube_nodes[NODE_TAGS[-1]]]=[3,701]
 after_classes={**classes,nmax+1:[3,11],nmax+2:[3,11]}
 faces=list(triangles.values())
 return dict(points=points,cells=cells,triangles=triangles,old=old,cube_nodes=cube_nodes,cube_cells=cube_cells,
  nmax=nmax,emax=emax,node_map=node_map,element_slots=element_slots,replacement=replacement,proposed=proposed,
  classes=classes,after_classes=after_classes,faces=faces,candidate_changes=changes)


def require_outside(before,after,case):
 oldp=dict(zip(before['node_tags'],before['coordinate_words']));newp=dict(zip(after['node_tags'],after['coordinate_words']))
 if set(newp)!=set(oldp)|{case['nmax']+1,case['nmax']+2}:raise ValueError('Exact two fresh nodes required')
 if any(oldp[t]!=newp[t] for t in oldp if t!=1435493):raise ValueError('Any outside/fixed coordinate bit changed')
 oldc=dict(zip(before['tetra_tags'],before['tetra_node_tags']));newc=dict(zip(after['tetra_tags'],after['tetra_node_tags']))
 if {t:r for t,r in oldc.items() if t not in case['old']}!={t:r for t,r in newc.items() if t not in case['replacement']}:
  raise ValueError('Untouched ordered cell/tag changed')
 if any(newc.get(t)!=r for t,r in case['replacement'].items()) or set(newc)!=set(case['cube_cells'])|set(case['replacement']):
  raise ValueError('All39ordered replacement rows required')
 for key in ['entities','entity_boundaries','physical_groups','lower_dimensional_elements']:
  if before[key]!=after[key]:raise ValueError('Outside entity/lower-dimensional rows changed')
 if before['classifications']!={str(t):after['classifications'][str(t)] for t in oldp}:
  raise ValueError('Any original node classification changed')
 if after['classifications']!={str(t):v for t,v in case['after_classes'].items()}:
  raise ValueError('Fresh nodes must be on declared fixture volume')
 for t,xyz in case['proposed'].items():
  if newp[t]!=[float(x).hex() for x in xyz]:raise ValueError('Exact proposed coordinate words changed')


def construct(gmsh,case,counts):
 gmsh.model.add('disconnected_sparse_star_edit_capability_fixture')
 gmsh.model.addDiscreteEntity(2,401);gmsh.model.addDiscreteEntity(2,501)
 gmsh.model.addDiscreteEntity(3,11,[401]);gmsh.model.addDiscreteEntity(3,701,[501])
 groups=[(2,401,[t for t in case['points'] if t not in case['cube_nodes'].values() and t!=1435493]),
  (3,11,[1435493]),(2,501,list(case['cube_nodes'].values())[:-1]),(3,701,[list(case['cube_nodes'].values())[-1]])]
 for dim,entity,tags in groups:
  counts['addNodes']+=1;gmsh.model.mesh.addNodes(dim,entity,tags,[x for t in tags for x in case['points'][t]])
 for entity,kind,rows in [(11,4,case['old']),(701,4,case['cube_cells']),
  (401,2,{t:r for t,r in case['triangles'].items() if t<90000000}),
  (501,2,{t:r for t,r in case['triangles'].items() if t>=90000000})]:
  counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(entity,kind,list(rows),[t for r in rows.values() for t in r])


def edit_once(gmsh,case,counts):
 if len(case['old'])!=28 or not case['old']:raise ValueError('Empty or incomplete removal refused')
 if gmsh.model.mesh.getMaxNodeTag()!=case['nmax'] or gmsh.model.mesh.getMaxElementTag()!=case['emax']:
  raise ValueError('Actual global maxima differ from complete fixture arrays')
 for tag,row in case['old'].items():
  kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
  if kind!=4 or list(nodes)!=row or (dim,entity)!=(3,11):raise ValueError('Old element row/entity changed before removal')
 if gmsh.model.mesh.getNode(1435493)[2:]!=(3,11):raise ValueError('Apex storage slot has wrong class')
 counts['removeElements']+=1;gmsh.model.mesh.removeElements(3,11,sorted(case['old']))
 counts['setNode']+=1;gmsh.model.mesh.setNode(1435493,case['proposed'][1435493],[])
 tags=[case['nmax']+1,case['nmax']+2]
 counts['addNodes']+=1;gmsh.model.mesh.addNodes(3,11,tags,[x for t in tags for x in case['proposed'][t]])
 counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(11,4,list(case['replacement']),[t for r in case['replacement'].values() for t in r])
 counts['rebuildNodeCache']+=1;gmsh.model.mesh.rebuildNodeCache(False)
 counts['rebuildElementCache']+=1;gmsh.model.mesh.rebuildElementCache(False)


def inspect(gmsh,helper,case):
 np=helper.np;xyz,cells,et,en=helper.volume_arrays(gmsh)
 tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0]));ix=np.argsort(et);et=np.asarray(et)[ix];en=np.asarray(en)[ix];cells=cells[ix]
 if not np.isfinite(xyz).all() or len(set(map(int,tags)))!=len(tags) or not np.array_equal(np.unique(en),tags):
  raise ValueError('Finite unique fully referenced nodes required')
 if len(np.unique(np.sort(en,axis=1),axis=0))!=len(en) or len(np.unique(xyz,axis=0))!=len(xyz):raise ValueError('Duplicate nodes or cells refused')
 expected_faces=np.searchsorted(tags,np.asarray(case['faces']))
 boundary=helper.tetra_boundary(cells,expected_faces);orientation=helper.internal_face_orientation(cells)
 signed=helper.tetra_volumes(xyz,cells)
 metrics={name:np.asarray(gmsh.model.mesh.getElementQualities(et,api)) for name,api in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
 for name,values in [*metrics.items(),('signed_volume_mm3',signed)]:
  if len(values)!=len(et) or not np.isfinite(values).all() or (name!='SICN' and np.any(values<=0)):
   raise ValueError('Complete finite positive-volume metric rows required')
 expected=float(Fraction(1450956179458166404046894365859946143854307,522673715590561479879743397015195972796416))+8.
 if abs(float(signed.sum())/expected-1)>1e-6:raise ValueError('Existing relative volume bookkeeping gate failed')
 classes={};lower=[];entities=[list(x) for x in gmsh.model.getEntities()]
 for dim,entity in entities:
  for t in gmsh.model.mesh.getNodes(dim,entity,False,False)[0]:
   if str(int(t)) in classes:raise ValueError('Node classified twice')
   classes[str(int(t))]=[dim,entity]
  if dim<3:
   types,ets,ens=gmsh.model.mesh.getElements(dim,entity)
   for kind,tt,nn in zip(types,ets,ens):
    if kind!=2 or len(nn)!=3*len(tt):raise ValueError('Unexpected lower-dimensional fixture element')
    lower.extend([[dim,entity,int(kind),int(t),list(map(int,row))] for t,row in zip(tt,np.asarray(nn).reshape(-1,3))])
 if set(classes)!=set(map(str,map(int,tags))):raise ValueError('All fixture nodes must be classified once')
 if int(gmsh.model.mesh.getMaxNodeTag())!=int(max(tags)) or int(gmsh.model.mesh.getMaxElementTag())!=max([*map(int,et),*[r[3] for r in lower]]):raise ValueError('Actual global maximum tag differs from complete arrays')
 return dict(node_tags=tags.tolist(),coordinates_mm=xyz.tolist(),coordinate_words=[[float(x).hex() for x in row] for row in xyz],
  tetra_tags=et.tolist(),tetra_node_tags=en.tolist(),classifications=classes,entities=entities,lower_dimensional_elements=sorted(lower),
  native_qualities={k:v.tolist() for k,v in metrics.items()},signed_volume_mm3=signed.tolist(),boundary=boundary,internal_orientation=orientation,
  typed_sha256={k:helper.array_sha(v) for k,v in [('node_tags',tags.astype('<u8')),('coordinates',xyz.astype('<f8')),('tetra_tags',et.astype('<u8')),('tetra_nodes',en.astype('<u8'))]},
  entity_boundaries={str((dim,entity)):[list(x) for x in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] for dim,entity in entities},
  physical_groups=[list(x) for x in gmsh.model.getPhysicalGroups()],
  max_node_tag=int(gmsh.model.mesh.getMaxNodeTag()),max_element_tag=int(gmsh.model.mesh.getMaxElementTag()))


def require_contract(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('tag_sparse_editing_fixture_authorized') is not True
     or any(c.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','generation_authorized',
      'optimization_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or c.get('options')!=OPTIONS or c.get('declared_operation_counts')!=COUNTS or c.get('automatic_retry') is not False):
  raise ValueError('Exact tiny editing-only actual authority required')
 if c.get('output_directory')!=str(OUT.relative_to(ROOT)) or OUT.name!='tag-sparse-star-edit-cube-001':raise ValueError('Exact fresh fixture output required')
 for name,digest in c['input_hashes'].items():
  f=ROOT/name
  if Path(name).is_absolute() or '..' in Path(name).parts or f.is_symlink() or sha(f)!=digest:raise ValueError('Bound input drift')
 required={OBSERVATION:OBSERVATION_SHA,SHELL:AUDIT_INPUTS[SHELL],CANDIDATE:CANDIDATE_SHA,ARRAYS:ARRAYS_SHA,WORKER:WORKER_SHA,CAVITY:CAVITY_SHA,CUBE:CUBE_SHA,PEER:PEER_SHA,**AUDIT_INPUTS}
 if any(c['input_hashes'].get(k)!=v for k,v in required.items()):raise ValueError('A consumed fixed source/data input is not direct-pinned')
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected three native identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256'] or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']:
  raise ValueError('Materialized source/selected interpreter changed')


def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {x.name for x in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('One fresh controller-owned output only')
 local=load_cavity_module();helper,gmsh,observed,actual=local.load_audit_helper(c)
 observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text());local.shell_rows(shell)
 candidate=json.loads((ROOT/CANDIDATE).read_text());arrays=json.loads((ROOT/ARRAYS).read_text())
 case=make_case(observation,shell,candidate,arrays);counts={k:0 for k in COUNTS};report={'status':'running','API_counters_record_attempts':True};initialized=False
 try:
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.option.setNumber('General.Terminal',1)
  for k,v in OPTIONS.items():gmsh.option.setNumber(k,v)
  construct(gmsh,case,counts);before=inspect(gmsh,helper,case);report['before']=before
  if len(before['node_tags'])!=26 or len(before['tetra_tags'])!=40 or before['classifications']!={str(t):v for t,v in case['classes'].items()}:raise ValueError('Complete fixed before26/40 classification state required')
  if dict(zip(before['tetra_tags'],before['tetra_node_tags']))!=case['cells'] or dict(zip(before['node_tags'],before['coordinate_words']))!={t:[float(x).hex() for x in xyz] for t,xyz in case['points'].items()}:raise ValueError('Every constructed before coordinate/cell must equal fixed input')
  edit_once(gmsh,case,counts);after=inspect(gmsh,helper,case);report['after']=after;require_outside(before,after,case)
  if len(after['node_tags'])!=28 or len(after['tetra_tags'])!=51:raise ValueError('Complete51cell/28node after state required')
  mesh=OUT/'fixture.msh';counts['write_mesh']+=1;gmsh.write(str(mesh));gmsh.clear();gmsh.open(str(mesh));saved=inspect(gmsh,helper,case)
  report['saved_reopen']=saved
  if saved!=after:raise ValueError('Full saved/reopened arrays/classes/metrics differ')
  if counts!=COUNTS:raise ValueError('Exact observed editing/construction API attempt counts differ')
  require_contract(c);poor=[t for t,q in zip(after['tetra_tags'],after['native_qualities']['SICN']) if q<.1]
  report.update(status='completed_disconnected_tag_sparse_editing_fixture',fixture_procedural_checks_passed=True,actual_SICN_gate_passed=not poor,
   before=before,after=after,saved_reopen=saved,positive_poor_tags=poor,counts=counts,runtime=observed,runtime_sha256s=actual,
   mesh_sha256=sha(mesh),mesh_bytes=mesh.stat().st_size,saved_identity_exact=True,bound_inputs_unchanged=True,node_map=case['node_map'],element_slots=case['element_slots'],
   source_cell_tags_removed=sorted(case['old']),classification_scope='All16shell nodes are fixed diagnostic fixture-surface nodes; original source9boundary/7interior labels are not adopted or upgraded.',
   diagnostic28shell_triangles_present_before_edit_and_unchanged=True,local28shell_faces_imported_as_head_boundary_elements=False,connected_outside_neighbor_cancellation_tested=False,embedding_or_head_containment_proved=False,
   head_execution_authorized=False,stitching_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
  local.save(OUT/'fixture-report.json',report)
  return 0 if not poor else 2
 except BaseException as e:
  report.update(status='failed',error=str(e),counts=counts,head_execution_authorized=False,stitching_authorized=False,manufacturing_authorized=False)
  if not (OUT/'fixture-report.json').exists():local.save(OUT/'fixture-report.json',report)
  raise
 finally:
  if initialized:gmsh.finalize()

if __name__=='__main__':raise SystemExit(main())
