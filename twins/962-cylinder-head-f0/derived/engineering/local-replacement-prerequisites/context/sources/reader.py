"""HELD read-only original-head star context census; no quality or geometry writes."""
from pathlib import Path
from types import SimpleNamespace
import ast, hashlib, json, math, platform, struct, sys, time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/head-star-context-census-001'
MESH='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/head-volume.msh'
MSH_SHA='4b983f4ab0134d01573059aecb8f4ba512dabbdfe54fbce6abaa0a06af29fe1d'
WORKER='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/worker-report.json'
RECEIPT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/receipt.json'
FIRST='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json'
OBS='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
MESH_HELPER='twins/962-cylinder-head-f0/source/mesh_head.py'
CLASS_HELPER='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-prep-001/reader.py'
CANDIDATE='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
FIXED_INPUTS={'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/worker-report.json': '16f6ecc580d766c3c541517f0f89bd80d5cd0f660f40b157a04c5362c2245e6a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/receipt.json': '426e76e578b4ae0093e85515703f216c64cf1b2aaaf7474d6d8fb8a4641a32de', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json': '5946ffbd9f2f127306673d967b583b11d8906793e2079971bc0430d65ae65f88', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json': '53a1fb5696d46c8773eea0ffd3a971706946b380a0b3a5f5ba41d1d6a121d15a', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json': 'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8', 'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-prep-001/reader.py': 'd978448ac685730c8ab1cf652dec23a00227eb5369869b89d6068017e678c5d5', 'work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json': 'e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/head-volume.msh': '4b983f4ab0134d01573059aecb8f4ba512dabbdfe54fbce6abaa0a06af29fe1d'}
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3));CHUNK=100000;APEX=1435493;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
NUMPY_SHA='c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'
FORBIDDEN=['optimization_authorized','mesh_write_authorized','generation_authorized','head_edit_authorized',
 'head_execution_authorized','stitching_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()

def canonical(face):
 return min(tuple(face[i:]+face[:i]) for i in range(3))

def json_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_interface(expected,owners,triangles):
 """Complete selected-face records, not a global incidence/embedding proof."""
 answer=[]
 if set(owners)!=set(expected) or set(triangles)!=set(expected):raise ValueError('Every selected face must be retained')
 for key,face in expected.items():
  rows=owners[key];old=[x for x in rows if x['removed_star_owner']];outside=[x for x in rows if not x['removed_star_owner']]
  if len(old)!=1 or len(outside)>1 or len(rows) not in (1,2):raise ValueError('Exactly one old owner and at most one outside owner required')
  if canonical(old[0]['oriented_face'])!=canonical(face):raise ValueError('Old owner winding differs from frozen outward shell')
  if outside:
   if canonical(outside[0]['oriented_face'])!=canonical(list(reversed(face))) or triangles[key]:
    raise ValueError('Interior selected face requires opposite outside owner and no exterior TRI')
  elif len(triangles[key])!=1 or canonical(triangles[key][0]['node_tags'])!=canonical(face):
   raise ValueError('One-owner selected face needs one exact oriented parent exterior TRI')
  answer.append({'shell_face_key':list(key),'oriented_shell_face':face,'owners':rows,
   'parent_exterior_TRI_rows':triangles[key],'interface_kind':'internal_with_outside_owner' if outside else 'parent_exterior'})
 return answer

def face_hits(np,rows,keys):
 """Exact uint64 unordered triples; NumPy search only, no coordinate predicate."""
 dtype=np.dtype([('a','<u8'),('b','<u8'),('c','<u8')])
 values=np.ascontiguousarray(np.sort(rows,axis=1),dtype='<u8').view(dtype).reshape(-1)
 wanted=np.ascontiguousarray(sorted(keys),dtype='<u8').reshape(-1,3).view(dtype).reshape(-1)
 positions=np.searchsorted(wanted,values);possible=np.flatnonzero(positions<len(wanted))
 return possible[wanted[positions[possible]]==values[possible]]

def require_inputs(c):
 if (c.get('schema')!='962-head-star-context-census/v1' or c.get('native_execution_authorized') is not True
     or c.get('native_read_only_query_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or any(c.get(k) is not False for k in FORBIDDEN)
     or c.get('automatic_retry') is not False or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT
     or c.get('MSH_sha256')!=MSH_SHA or c.get('MSH_bytes')!=235742414):raise ValueError('Exact read-only context authority required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed record/source/parent must be a direct fixed pin')
 for name,digest in c['input_hashes'].items():
  f=ROOT/name
  if Path(name).is_absolute() or f.is_symlink() or not f.resolve().is_relative_to(ROOT) or sha(f)!=digest:raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected native3 identity map required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source/interpreter changed')

def selected_functions(path,names,namespace):
 tree=ast.parse((ROOT/path).read_text());rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in rows}!=set(names):raise ValueError('Selected frozen helper definition absent')
 exec(compile(ast.Module(body=rows,type_ignores=[]),path,'exec'),namespace)

def main():
 start=time.monotonic();c=json.loads((OUT/'frozen-contract.json').read_text());require_inputs(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Fresh materialized output only')
 report={'status':'running','stage':'runtime_and_original_proof','complete_context_census':False,
  'native_generate_optimize_meshwrite_solve_calls':0,'quality_recomputed':False,**{k:False for k in FORBIDDEN}}
 def save():
  with (OUT/'readback-report.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 save();initialized=False
 try:
  import numpy as np
  import gmsh
  observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
  actual={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(gmsh.__file__),'gmsh_library':sha(gmsh.lib._name)}
  if (observed!=RUNTIME or actual!=c['runtime_sha256s'] or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve()
      or sha(np.__file__)!=NUMPY_SHA):raise ValueError('Loaded selected runtime/NumPy origin or bytes changed')
  arrsha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
  ns={'np':np};selected_functions(MESH_HELPER,['volume_arrays'],ns)
  selected_functions(CLASS_HELPER,['classifications'],ns)
  core=SimpleNamespace(np=np,array_sha=arrsha)
  worker=json.loads((ROOT/WORKER).read_text());receipt=json.loads((ROOT/RECEIPT).read_text());first=json.loads((ROOT/FIRST).read_text())
  if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None or receipt.get('worker_report')!=worker
      or receipt.get('bound_inputs_unchanged') is not True or worker.get('saved_mesh_identity_exact') is not True
      or worker.get('bound_inputs_unchanged') is not True or worker.get('mesh_sha256')!=MSH_SHA
      or receipt.get('mesh_sha256')!=MSH_SHA or worker.get('mesh_bytes')!=235742414
      or first.get('status')!='direct_saved_file_readback_completed' or first.get('bound_inputs_unchanged') is not True):
   raise ValueError('Single completed original worker.after and full first census required')
  proof=worker['after'];expected=proof['array_sha256s']
  if any(first.get(k)!=v for k,v in expected.items()) or first['direct_fresh_classifications']!=proof['classifications']:
   raise ValueError('Full first census and original four-array/class proof differ')
  observation=json.loads((ROOT/OBS).read_text());shell=json.loads((ROOT/SHELL).read_text())
  candidate=json.loads((ROOT/CANDIDATE).read_text())
  if candidate.get('all39_exact_quality_gate') is not True or candidate.get('all16_shell_coordinate_bits_unchanged') is not True:
   raise ValueError('Retained exact local candidate identity required; no quality recomputed here')
  candidate_rows={row['node_tag']:row for row in candidate['complete_proposed_coordinate_rows']}
  for row in shell['vertex_rows']:
   if struct.pack('<3d',*candidate_rows[row['local_node_tag']]['coordinates_mm']).hex()!=row['binary64_little_endian_bytes_hex']:
    raise ValueError('Local candidate and original16shell coordinate words differ')
  old={row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']}
  old_points={row['node_tag']:row for row in observation['selected_node_rows']}
  mapping=shell['local_to_global_node_tags']
  if len(old)!=28 or len(old_points)!=17 or len(mapping)!=16 or APEX in mapping or set(old_points)!=set(mapping+[APEX]):
   raise ValueError('Specific original17/28 and16 shell map required')
  faces=[[mapping[t-1] for t in row['local_node_tags']] for row in shell['oriented_triangle_rows']]
  expected_faces={tuple(sorted(face)):face for face in faces}
  if len(faces)!=28 or len(expected_faces)!=28:raise ValueError('Complete unique28shell required')
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setNumber('Mesh.MaxNumThreads3D',2)
  report['stage']='opening_original_parent';save();gmsh.open(str(ROOT/MESH))
  xyz,_,et,en=ns['volume_arrays'](gmsh);tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0],dtype='<u8'))
  order=np.argsort(et);et=np.asarray(et,dtype='<u8')[order];en=np.asarray(en,dtype='<u8')[order]
  if not np.isfinite(xyz).all() or len(np.unique(tags))!=len(tags) or len(np.unique(et))!=len(et):raise ValueError('Unique full finite arrays required')
  actual_arrays=dict(zip(['sorted_coordinates_sha256','sorted_node_tags_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'],map(arrsha,[xyz,tags,et,en])))
  if actual_arrays!=expected or (len(tags),len(et))!=(1097048,3620809):raise ValueError('Opened complete parent arrays differ from original worker.after')
  classes=ns['classifications'](core,gmsh,tags,BOUNDARY)
  if classes!=proof['classifications']:raise ValueError('Complete native classifications differ from original worker.after')
  if not np.array_equal(np.unique(en),tags):raise ValueError('Complete parent reference/orphan association changed')
  report['stage']='complete_selected_face_owner_scan';save()
  owners={key:[] for key in expected_faces};triangles={key:[] for key in expected_faces};apex_rows={}
  for startrow in range(0,len(et),CHUNK):
   conn=en[startrow:startrow+CHUNK]
   for j in np.flatnonzero(np.any(conn==APEX,axis=1)):
    apex_rows[int(et[startrow+j])]=conn[j].tolist()
   for pattern in FACES:
    rows=conn[:,pattern]
    for j in face_hits(np,rows,expected_faces):
     index=startrow+int(j);tag=int(et[index]);face=rows[j].tolist();key=tuple(sorted(face))
     owners[key].append({'tetrahedron_tag':tag,'node_tags':en[index].tolist(),'oriented_face':face,
      'native_corner_indices':list(pattern),'removed_star_owner':tag in old})
  if apex_rows!=old:raise ValueError('Complete original apex incidence/order differs; outside apex use refused')
  entities=sorted((int(d),int(t)) for d,t in gmsh.model.getEntities());entity_rows=[];lower=[];periodic=[];max_element=int(et.max());all_lower_tags=[]
  for dim,entity in entities:
   boundary=[list(map(int,row)) for row in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] if dim else []
   entity_rows.append({'dimension':dim,'entity_tag':entity,'oriented_immediate_boundary':boundary,'name':gmsh.model.getEntityName(dim,entity)})
   if dim in (1,2):
    master,nodes,masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,entity,True)
    periodic.append({'dimension':dim,'entity_tag':entity,'master_entity':int(master),'node_tags':list(map(int,nodes)),
     'master_node_tags':list(map(int,masters)),'affine_transform':list(map(float,transform))})
   if dim>=3:continue
   types,element_tags,element_nodes=gmsh.model.mesh.getElements(dim,entity)
   if not (len(types)==len(element_tags)==len(element_nodes)):raise ValueError('Complete lower-dimensional blocks required')
   for kind,tt,flat in zip(types,element_tags,element_nodes):
    kind=int(kind);properties=gmsh.model.mesh.getElementProperties(kind);width=int(properties[3])
    if int(properties[1])!=dim or width<=0 or len(flat)!=len(tt)*width:raise ValueError('Lower-dimensional type/row width changed')
    ix=np.argsort(tt);tt=np.asarray(tt,dtype='<u8')[ix];rows=np.asarray(flat,dtype='<u8').reshape(-1,width)[ix]
    if len(tt)!=len(np.unique(tt)) or (len(tt) and int(tt.min())<=0):raise ValueError('Unique positive lower-dimensional tags required')
    if len(tt):max_element=max(max_element,int(tt.max()));all_lower_tags.append(tt)
    lower.append({'dimension':dim,'entity_tag':entity,'element_type':kind,'nodes_per_element':width,'count':len(tt),
     'minimum_tag':int(tt.min()) if len(tt) else None,'maximum_tag':int(tt.max()) if len(tt) else None,
     'element_tags_u64_sha256':arrsha(tt),'ordered_connectivity_u64_sha256':arrsha(rows)})
    if dim==2 and kind==2:
     for begin in range(0,len(tt),CHUNK):
      for j in face_hits(np,rows[begin:begin+CHUNK],expected_faces):
       index=begin+int(j);face=rows[index].tolist()
       triangles[tuple(sorted(face))].append({'dimension':dim,'entity_tag':entity,'element_type':kind,'element_tag':int(tt[index]),'node_tags':face})
  lower.sort(key=lambda row:(row['dimension'],row['entity_tag'],row['element_type']))
  all_et=np.concatenate([et,*all_lower_tags])
  if len(np.unique(all_et))!=len(all_et):raise ValueError('All-dimensional element tag collision refused')
  actual_max={'node':int(tags.max()),'element_all_dimensions':max_element}
  if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(actual_max['node'],max_element):
   raise ValueError('Native maxima differ from complete independent all-dimensional arrays')
  if sum(x['count'] for x in lower if x['dimension']==2 and x['element_type']==2)!=1743878:
   raise ValueError('Complete parent exterior TRI count differs from original surface authority')
  joined=validate_interface(expected_faces,owners,triangles);outside_rows={};all_owner_tags=set()
  for record in joined:
   for row in record['owners']:
    tag=row['tetrahedron_tag'];kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
    if int(kind)!=4 or list(map(int,nodes))!=row['node_tags'] or int(dim)!=3:raise ValueError('Selected native row/owner join changed')
    row['dimension']=int(dim);row['entity_tag']=int(entity);all_owner_tags.add(tag)
    if not row['removed_star_owner']:outside_rows[tag]=row['node_tags']
  selected_nodes=[]
  for tag in sorted(old_points):
   coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag);coordinates=list(map(float,coordinates));param=list(map(float,param))
   index=int(np.searchsorted(tags,tag));want=old_points[tag]
   if (index>=len(tags) or int(tags[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*xyz[index])
       or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want['coordinates_mm'])
       or [x.hex() for x in coordinates]!=want['binary64_hex'] or not all(math.isfinite(x) for x in param)
       or int(dim)!=(2 if tag in mapping[:9] else 3) or (int(dim),int(entity)) not in entities):
    raise ValueError('Selected17 coordinate/class/entity/param join failed')
   selected_nodes.append({'node_tag':tag,'dimension':int(dim),'entity_tag':int(entity),'coordinates_mm':coordinates,
    'binary64_hex':[x.hex() for x in coordinates],'available_parametric_coordinates':param,'parametric_binary64_hex':[x.hex() for x in param]})
  selected_classes={row['node_tag']:[row['dimension'],row['entity_tag']] for row in selected_nodes}
  for face in joined:
   for triangle in face['parent_exterior_TRI_rows']:
    if any(selected_classes[t]!=[2,triangle['entity_tag']] for t in triangle['node_tags']):
     raise ValueError('Exterior interface TRI has inconsistent selected surface-node classification')
  outside_tags=sorted({t for row in outside_rows.values() for t in row});outside_coordinates=[]
  for tag in outside_tags:
   index=int(np.searchsorted(tags,tag));row=list(map(float,xyz[index]))
   if int(tags[index])!=tag:raise ValueError('Outside owner references absent node')
   outside_coordinates.append({'node_tag':tag,'coordinates_mm':row,'binary64_hex':[x.hex() for x in row]})
  groups=[]
  for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
   groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),
    'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
  node_mask=tags!=APEX;cell_mask=~np.isin(et,np.asarray(sorted(old),dtype='<u8'))
  preservation={'outside_node_tags_u64_sha256':arrsha(tags[node_mask]),'outside_coordinate_words_f64_sha256':arrsha(xyz[node_mask]),
   'outside_tetra_tags_u64_sha256':arrsha(et[cell_mask]),'outside_ordered_tetra_connectivity_u64_sha256':arrsha(en[cell_mask]),
   'outside_nodes':int(np.count_nonzero(node_mask)),'outside_TET4':int(np.count_nonzero(cell_mask)),
   'full_lower_dimensional_inventory_sha256':json_sha(lower),'full_entity_metadata_sha256':json_sha(entity_rows),
   'full_physical_group_metadata_sha256':json_sha(groups),'full_periodic_metadata_sha256':json_sha(periodic),
   'full_classification_proof_sha256':json_sha(classes)}
  require_inputs(c)
  if sha(np.__file__)!=NUMPY_SHA:raise ValueError('Selected NumPy bytes changed after query')
  report.update(status='complete_original_head_star_context_census',stage='completed',complete_context_census=True,
   original_parent_MSH_sha256=MSH_SHA,original_parent_MSH_bytes=235742414,full_array_sha256s=actual_arrays,
   full_native_classifications=classes,full_node_count=len(tags),full_TET4_count=len(et),
   complete_old_apex_incident_rows=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)],
   all28_selected_shell_face_records=joined,complete_outside_owner_rows=[{'tetrahedron_tag':t,'node_tags':outside_rows[t]} for t in sorted(outside_rows)],
   complete_outside_owner_coordinate_rows=outside_coordinates,selected17_native_node_rows=selected_nodes,
   independently_derived_global_maxima=actual_max,full_lower_dimensional_inventory=lower,
   full_entity_metadata=entity_rows,full_physical_group_metadata=groups,full_periodic_metadata=periodic,
   future_preservation_references=preservation,runtime=observed,runtime_sha256s=actual,bound_inputs_unchanged=True,
   quality_and_global_incidence='Retained original worker.after only; no native qualities/global incidence recomputed.',
   candidate_or_MSH_written=False,selected_geometry_JSON_exported=True,connected_interface_ownership_only=True,
   global_embedding_containment_or_after_edit_preservation_proved=False,readback_wall_seconds=time.monotonic()-start)
  save();return 0
 except BaseException as error:
  report.update(status='refused_or_interrupted_context_census',complete_context_census=False,error=str(error));save();raise
 finally:
  if initialized:gmsh.finalize()

if __name__=='__main__':raise SystemExit(main())
