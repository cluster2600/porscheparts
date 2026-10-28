"""HELD read-only current partial-head apex1474426 context census; no candidate, quality or geometry writes."""
from pathlib import Path
from types import SimpleNamespace
import ast, hashlib, json, math, platform, struct, sys, time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/direct-sicn-apex1474426-head-context-001'
MESH='work/962-engineering/head-star-replacement-001/head-volume.msh'
MSH_SHA='9d85bbd0f762aebe07d96fad9618f2d7b8992ae29d288c8ba1829dc0481cc895'
WORKER='work/962-engineering/head-star-replacement-001/readback-report.json'
RECEIPT='work/962-engineering/head-star-replacement-001/execution-receipt.json'
FIRST='work/962-engineering/head-star-remaining-full-stars-001/readback-report.json'
OBS='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json'
MESH_HELPER='twins/962-cylinder-head-f0/source/mesh_head.py'
CLASS_HELPER='work/962-engineering/head-star-remaining-full-stars-prep-001/reader.py'
FIRST_CONTRACT='work/962-engineering/head-star-remaining-full-stars-001/frozen-contract.json'
CLOSED='work/962-engineering/head-star-replacement-root-execution-001/closed-result.json'
CENSUS_PEER='work/962-engineering/head-star-remaining-full-stars-result-peer-001/review.json'
SCREEN='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/fixed-shell-tight-face-screen-001.json'
EXTRACT_RECEIPT='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/receipt.json'
EXTRACT_CLOSED='work/962-engineering/direct-sicn-apex1474426-cavity-extract-root-execution-001/closed-result.json'
EXTRACT_PEER='work/962-engineering/direct-sicn-apex1474426-cavity-extract-result-peer-001/review.json'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-prep-001/extract_shell.py': '49cf077be7ede9b145910597d032a58e5462c240fa8d378e40b86bf4e1a9dbcd', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-prep-001/held-contract.json': '9b47ccde4a695a52ade566bf9d12cc1622e5909983d1e48a0656fbb2b93c4d10', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-result-peer-001/independent-saved-check.json': 'ec7449522124f3b5b1742b3323cd305fb6591d3864bb72ae3b675eb374a35a78', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-result-peer-001/review.json': 'f459ea19b290090e3bd5b58deb7e68224946e849f5e2d1d7caca6871470fb7de', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-root-execution-001/closed-result.json': '56703b3680ffbb85a8d29cee9e9915bfeeee312fe51601b5445fb16e9d60da7d', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-root-execution-001/result-review.json': '41f905f55635f11ce6f27254f331032a29acb689fb7ac5a176ec2b1e71e93d18', 'work/962-engineering/direct-sicn-apex1474426-cavity-extract-source-peer-001/review-002.json': '6778c7cb288e5853d04e9dbcbe3d13fa954fa2a079fae183f71104fb0c7fdcba', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/fixed-shell-tight-face-screen-001.json': 'ac8a56be67a8b0e646939a12e15addf10461592d43ef801317a8b91cd4cbd79d', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json': '6ad00be791b8b752106b5324b9f80df314f7458d8d0475b1ffc1a053bc04d12a', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/receipt.json': '96eba9c2872d24983a962ff797a48fe9f521815d8946641a145cc324bc013a5e', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json': '3d80523e2ebd2a92584546f89dc71d35f401696338f99f45480d196a25f840f6', 'work/962-engineering/direct-sicn-apex1474426-local-replacement-reuse-note-001/NOTE.md': '3de96e8209066fb085cb1ac50db3dc7873533bf0cc386f79bdb703395c8f6f6b', 'work/962-engineering/direct-sicn-apex1474426-local-replacement-reuse-note-001/source-bindings.json': '1b2052173b054854fdec3039766a07e32601930ff630910230d244e403d91a7e', 'work/962-engineering/head-star-context-census-prep-001/reader.py': 'c59e0c14dd3e6ee9747168ac80f4284374ef62025fe4ec59e171f128ada2122a', 'work/962-engineering/head-star-context-census-source-peer-001/review.json': '1fcbcacb752b3383cadd4ed64bbb6382a6e741274c9dd05c017a8f464e01c96f', 'work/962-engineering/head-star-remaining-full-stars-001/frozen-contract.json': '58bff7528882916674457ac1b3a631fa49f1512f7e464d69633f6ef205d0cb25', 'work/962-engineering/head-star-remaining-full-stars-001/readback-report.json': 'e43e2de37512feef3c880a7e8ca5d2db39ecf147708de6e2e04bd8030fda5b68', 'work/962-engineering/head-star-remaining-full-stars-prep-001/reader.py': 'afcad55f5e716b90ff4bac39cee4268101a21c4bbd9078f950b9bf372948a05d', 'work/962-engineering/head-star-remaining-full-stars-result-peer-001/review.json': '039e9cc8e970a0d7bd44869f3d0fab6d6168fffe086c12951d8efe753b987573', 'work/962-engineering/head-star-replacement-001/execution-receipt.json': 'aeb4597e001ce6a68e20b90e961036719139c3225451a2dbfbabe151b7f5d67f', 'work/962-engineering/head-star-replacement-001/head-volume.msh': '9d85bbd0f762aebe07d96fad9618f2d7b8992ae29d288c8ba1829dc0481cc895', 'work/962-engineering/head-star-replacement-001/readback-report.json': '780937d788385cf2a227db6c2cec308474b9fcca32375f868d39bc74ae80429b', 'work/962-engineering/head-star-replacement-root-execution-001/closed-result.json': 'f99279040e88822c910ff6d7d56249125d2dce98d32d088f856428862dde9ae4'}
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3));CHUNK=100000;APEX=1474426;BOUNDARY=871731
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
 if (c.get('schema')!='962-apex1474426-current-head-context/v1' or c.get('native_execution_authorized') is not True
     or c.get('native_read_only_query_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or any(c.get(k) is not False for k in FORBIDDEN)
     or c.get('automatic_retry') is not False or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT
     or c.get('MSH_sha256')!=MSH_SHA or c.get('MSH_bytes')!=235742918):raise ValueError('Exact read-only context authority required')
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

def current_after_proof(worker,receipt,closed,first,prior,peer,helpers):
 """One current partial.after==saved proof; no optimizer aliases or quality query."""
 proof=helpers['partial_after_proof'](worker,receipt,closed,prior)
 if (prior['MSH_sha256']!=MSH_SHA or prior['MSH_bytes']!=235742918
     or prior['partial_report_sha256']!=FIXED_INPUTS[WORKER] or prior['expected_positive_poor_total']!=208
     or first.get('status')!='direct_saved_file_readback_completed' or first.get('bound_inputs_unchanged') is not True
     or first.get('single_partial_replacement_saved_proof')!={'report_sha256':FIXED_INPUTS[WORKER],'field':'after','after_equals_saved_reopen':True,'independent_prior_reader_alias_used':False,'old210_bins_reused':False}
     or any(first.get(k)!=v for k,v in proof['array_sha256s'].items())
     or first['direct_fresh_classifications']!=proof['classifications']
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CURRENT208_CENSUS_MESH_REMAINS_REJECTED'
     or peer['bindings']['report']['sha256']!=FIXED_INPUTS[FIRST] or peer['blockers']!=[] or peer['head_volume_accepted'] is not False):
  raise ValueError('Current partial-after/saved census proof required')
 helpers['require_after_match'](first,proof,208)
 return proof

def selection_records(observation,shell):
 """Specific original60/33/32 map and native owner/corner identity; no candidate."""
 cells=observation['native_ordered_cell_rows'];points=observation['selected_node_rows'];mapping=shell['local_to_global_node_tags']
 old={row['tetrahedron_tag']:row['node_tags'] for row in cells};old_points={row['node_tag']:row for row in points}
 if (observation.get('apex')!=APEX or shell.get('excluded_source_apex_tag')!=APEX
     or shell.get('apex_not_in_shell_input') is not True or shell.get('necessary_face_quality_passed') is not True
     or shell.get('generation_input_rejected_by_necessary_face_quality') is not False
     or len(cells)!=60 or len(old)!=60 or len(points)!=33 or len(old_points)!=33
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or len(mapping)!=32 or any(type(t) is not int or t<=0 for t in mapping) or mapping!=sorted(set(mapping))
     or APEX in mapping or set(old_points)!=set(mapping+[APEX])
     or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(mapping)}):
  raise ValueError('Specific current original60/33 and32shell identity required')
 source_boundary=shell['original_source_classifications']['boundary_global_node_tags']
 other=shell['original_source_classifications']['other_interior_global_node_tags']
 if (len(source_boundary)!=27 or len(other)!=5 or source_boundary!=sorted(set(source_boundary))
     or other!=sorted(set(other)) or set(source_boundary)&set(other) or sorted(source_boundary+other)!=mapping
     or source_boundary!=[t for t in mapping if t<=BOUNDARY] or any(t<=BOUNDARY for t in other)):
  raise ValueError('Original27 boundary and5 other dim3 shell tags required')
 vertices=shell['vertex_rows']
 if len(vertices)!=32:raise ValueError('All32 original coordinate rows required')
 for local,(tag,row) in enumerate(zip(mapping,vertices),1):
  point=old_points[tag];xyz=row['coordinates_mm']
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag or len(xyz)!=3
      or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
      or [float(x).hex() for x in xyz]!=row['binary64_hex'] or row['binary64_hex']!=point['binary64_hex']
      or struct.pack('<3d',*xyz)!=struct.pack('<3d',*point['coordinates_mm'])
      or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']
      or row['original_source_boundary_node'] is not (tag in source_boundary)):
   raise ValueError('Original shell coordinate words/classification flags differ')
 rows=shell['oriented_triangle_rows'];expected_faces={}
 if len(rows)!=60:raise ValueError('Complete60 shell faces required')
 for row in rows:
  local=row['local_node_tags'];owner=row['source_owner_tetrahedron_tag'];pattern=row['native_corner_indices']
  if len(local)!=3 or any(type(t) is not int or t<1 or t>32 for t in local) or len(set(local))!=3:
   raise ValueError('Exact local1..32 shell triangles required')
  face=[mapping[t-1] for t in local];key=tuple(sorted(face))
  if (key in expected_faces or face!=row['source_global_node_tags'] or owner not in old
      or tuple(pattern) not in FACES or [old[owner][i] for i in pattern]!=face
      or next(cell['native_array_index'] for cell in cells if cell['tetrahedron_tag']==owner)!=row['source_native_array_index']):
   raise ValueError('Exact unique native shell owner/corner/order required')
  expected_faces[key]=face
 return old,old_points,mapping,expected_faces,set(source_boundary)

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
  selected_functions(CLASS_HELPER,['classifications','partial_after_proof','require_after_match'],ns)
  core=SimpleNamespace(np=np,array_sha=arrsha)
  worker=json.loads((ROOT/WORKER).read_text());receipt=json.loads((ROOT/RECEIPT).read_text());first=json.loads((ROOT/FIRST).read_text())
  prior=json.loads((ROOT/FIRST_CONTRACT).read_text());closed=json.loads((ROOT/CLOSED).read_text());peer=json.loads((ROOT/CENSUS_PEER).read_text())
  proof=current_after_proof(worker,receipt,closed,first,prior,peer,ns);expected=proof['array_sha256s']
  observation=json.loads((ROOT/OBS).read_text());shell=json.loads((ROOT/SHELL).read_text())
  old,old_points,mapping,expected_faces,original_boundary=selection_records(observation,shell)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setNumber('Mesh.MaxNumThreads3D',2)
  report['stage']='opening_original_parent';save();gmsh.open(str(ROOT/MESH))
  xyz,_,et,en=ns['volume_arrays'](gmsh);tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0],dtype='<u8'))
  order=np.argsort(et);et=np.asarray(et,dtype='<u8')[order];en=np.asarray(en,dtype='<u8')[order]
  if not np.isfinite(xyz).all() or len(np.unique(tags))!=len(tags) or len(np.unique(et))!=len(et):raise ValueError('Unique full finite arrays required')
  actual_arrays=dict(zip(['sorted_coordinates_sha256','sorted_node_tags_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'],map(arrsha,[xyz,tags,et,en])))
  if actual_arrays!=expected or (len(tags),len(et))!=(1097050,3620820):raise ValueError('Opened complete parent arrays differ from original worker.after')
  classes=ns['classifications'](core,gmsh,tags,BOUNDARY)
  if classes!=proof['classifications']:raise ValueError('Complete native classifications differ from original worker.after')
  boundary_tags=np.arange(1,BOUNDARY+1,dtype='<u8');boundary_ix=np.searchsorted(tags,boundary_tags)
  if np.any(boundary_ix>=len(tags)) or not np.array_equal(tags[boundary_ix],boundary_tags):raise ValueError('Complete original source boundary tags required')
  source_boundary_identity={'source_boundary_nodes':BOUNDARY,'source_node_tags_sha256':arrsha(boundary_tags),
   'source_coordinate_bits_sha256':arrsha(xyz[boundary_ix]),
   'classification_dimensions_sha256':classes['boundary_node_classification_dimensions_sha256'],
   'classification_entity_tags_sha256':classes['boundary_node_classification_entity_tags_sha256'],
   'no_curve_or_surface_periodic_mapping':classes['no_curve_or_surface_periodic_mapping'],
   'periodic_entities_checked':classes['periodic_entities_checked']}
  if source_boundary_identity!=proof['source_boundary_identity']:raise ValueError('Current original source boundary identity differs')
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
       or int(dim)!=(2 if tag in original_boundary else 3) or (int(dim),int(entity)) not in entities):
    raise ValueError('Selected33 coordinate/class/entity/param join failed')
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
  metadata={'full_lower_dimensional_inventory':json_sha(lower),'full_entity_metadata':json_sha(entity_rows),
   'full_physical_group_metadata':json_sha(groups),'full_periodic_metadata':json_sha(periodic)}
  if metadata!=worker['after_preservation']['metadata_sha256s']:raise ValueError('Current partial lower/entity/physical/periodic metadata differs')
  require_inputs(c)
  if sha(np.__file__)!=NUMPY_SHA:raise ValueError('Selected NumPy bytes changed after query')
  report.update(status='complete_current_partial_head_apex1474426_context_census',stage='completed',complete_context_census=True,
   original_parent_MSH_sha256=MSH_SHA,original_parent_MSH_bytes=235742918,full_array_sha256s=actual_arrays,
   full_native_classifications=classes,full_node_count=len(tags),full_TET4_count=len(et),
   complete_old_apex_incident_rows=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)],
   all60_selected_shell_face_records=joined,complete_outside_owner_rows=[{'tetrahedron_tag':t,'node_tags':outside_rows[t]} for t in sorted(outside_rows)],
   complete_outside_owner_coordinate_rows=outside_coordinates,selected33_native_node_rows=selected_nodes,
   independently_derived_global_maxima=actual_max,full_lower_dimensional_inventory=lower,
   full_entity_metadata=entity_rows,full_physical_group_metadata=groups,full_periodic_metadata=periodic,
   future_preservation_references=preservation,runtime=observed,runtime_sha256s=actual,bound_inputs_unchanged=True,
   current_source_boundary_identity=source_boundary_identity,
   retained_current_quality_and_global_incidence={'quality':proof['quality'],'actual_tetra_boundary':proof['actual_tetra_boundary'],'internal_tetra_face_orientation':proof['internal_tetra_face_orientation']},
   quality_and_global_incidence='Retained current partial.after/saved only; no native qualities or global incidence recomputed.',
   candidate_or_MSH_written=False,selected_geometry_JSON_exported=True,connected_interface_ownership_only=True,
   global_embedding_containment_or_after_edit_preservation_proved=False,readback_wall_seconds=time.monotonic()-start)
  save();return 0
 except BaseException as error:
  report.update(status='refused_or_interrupted_context_census',complete_context_census=False,error=str(error));save();raise
 finally:
  if initialized:gmsh.finalize()

if __name__=='__main__':raise SystemExit(main())
