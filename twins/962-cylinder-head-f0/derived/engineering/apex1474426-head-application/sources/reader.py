"""HELD current partial-head60-to101 application; no mesher or optimizer."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
from itertools import combinations
import ast,hashlib,json,math,platform,struct,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/apex1474426-head-application-001'
MESH='work/962-engineering/head-star-replacement-001/head-volume.msh'
CONTEXT='work/962-engineering/direct-sicn-apex1474426-head-context-001/readback-report.json'
CONTEXT_CONTRACT='work/962-engineering/direct-sicn-apex1474426-head-context-001/frozen-contract.json'
OBSERVATION='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1474426-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1474426-001/fixture-report.json'
LOCAL_PEER='work/962-engineering/fixed-shell-netgen-apex1474426-result-peer-001/review.json'
DOMAIN='work/962-engineering/apex1474426-domain-equivalence-001/report.json'
DOMAIN_PEER='work/962-engineering/apex1474426-domain-equivalence-result-peer-001/review.json'
DOMAIN_SOURCE='work/962-engineering/apex1474426-domain-equivalence-prep-001/certify_domain.py'
DOMAIN_ACTUAL='work/962-engineering/apex1474426-domain-equivalence-execution-prep-001/actual-contract.json'
ORIGINAL_WORKER='work/962-engineering/head-star-replacement-001/readback-report.json'
ORIGINAL_RECEIPT='work/962-engineering/head-star-replacement-001/execution-receipt.json'
PARTIAL_CLOSED='work/962-engineering/head-star-replacement-root-execution-001/closed-result.json'
PARTIAL_METADATA='work/962-engineering/head-star-remaining-full-stars-001/frozen-contract.json'
FIRST='work/962-engineering/head-star-remaining-full-stars-001/readback-report.json'
PROOF_SOURCE='work/962-engineering/head-star-remaining-full-stars-prep-001/reader.py'
HEAD='twins/962-cylinder-head-f0/source/mesh_head.py'
CORE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
AUDIT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py'
FIXED_INPUTS={'work/962-engineering/head-star-replacement-001/head-volume.msh': '9d85bbd0f762aebe07d96fad9618f2d7b8992ae29d288c8ba1829dc0481cc895', 'work/962-engineering/direct-sicn-apex1474426-head-context-001/readback-report.json': '714f1c47bc71429a84842d8396be094ccceffb6f4e111991f089eefc974685a8', 'work/962-engineering/direct-sicn-apex1474426-head-context-001/frozen-contract.json': 'e4fdadbb618eccdaae2372c9fadb15e368cb917772ee6c8de4631011830e18ef', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json': '3d80523e2ebd2a92584546f89dc71d35f401696338f99f45480d196a25f840f6', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json': '6ad00be791b8b752106b5324b9f80df314f7458d8d0475b1ffc1a053bc04d12a', 'work/962-engineering/fixed-shell-netgen-apex1474426-001/arrays.json': 'ea3c5864a6b607afaf8428a806f65d8e3a81a6e4548e1588dd17b72ea44553b5', 'work/962-engineering/fixed-shell-netgen-apex1474426-001/fixture-report.json': '043c06613ce159acdc4432e0d155dcddc02fa909b02fe955c5f78e6d1b38f076', 'work/962-engineering/fixed-shell-netgen-apex1474426-result-peer-001/review.json': '12e4829d9a8a02e382c326ea5ef05f58c81f98c1b8b8b8df842846654ba60bd1', 'work/962-engineering/apex1474426-domain-equivalence-001/report.json': '3bd7bdcb6c22f168d275190c1f1605e91f21fce6f7c38f823b2cd0bac04d1b72', 'work/962-engineering/apex1474426-domain-equivalence-result-peer-001/review.json': '554245d8a542f2dee0ca11e8b0a6e3fb6482414a8e751dcc036f6e2b26de4339', 'work/962-engineering/apex1474426-domain-equivalence-prep-001/certify_domain.py': 'daebceae4a6a0402fbbe3f19c3bff5006ac6d2674d43cd452b32a4c7aa6a20d6', 'work/962-engineering/apex1474426-domain-equivalence-execution-prep-001/actual-contract.json': '0235a197176c2ab3a569e3f51466f6c8a7dba270d12d647b85f25d243b37da7a', 'work/962-engineering/head-star-replacement-001/readback-report.json': '780937d788385cf2a227db6c2cec308474b9fcca32375f868d39bc74ae80429b', 'work/962-engineering/head-star-replacement-001/execution-receipt.json': 'aeb4597e001ce6a68e20b90e961036719139c3225451a2dbfbabe151b7f5d67f', 'work/962-engineering/head-star-replacement-root-execution-001/closed-result.json': 'f99279040e88822c910ff6d7d56249125d2dce98d32d088f856428862dde9ae4', 'work/962-engineering/head-star-remaining-full-stars-001/frozen-contract.json': '58bff7528882916674457ac1b3a631fa49f1512f7e464d69633f6ef205d0cb25', 'work/962-engineering/head-star-remaining-full-stars-001/readback-report.json': 'e43e2de37512feef3c880a7e8ca5d2db39ecf147708de6e2e04bd8030fda5b68', 'work/962-engineering/head-star-remaining-full-stars-prep-001/reader.py': 'afcad55f5e716b90ff4bac39cee4268101a21c4bbd9078f950b9bf372948a05d', 'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py': '0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a', 'work/962-engineering/head-star-replacement-001/frozen-contract.json': '018e833bdccc5d72865c79f2f3f18ce190c4bae6ba2cac2f10a182cc5d61618f'}
ARRAYS_SHA=FIXED_INPUTS[ARRAYS];WORKER_SHA=FIXED_INPUTS[WORKER]
FREE=list(range(33,41))
APEX=1474426;NMAX=1613805;EMAX=32158126;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
CONTROLS={'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8*1024**3,'sampled_output_stop_bytes':1024**3,'native_threads':2,'automatic_retry':False}
COUNTS={'removeElements':1,'setNode':1,'addNodes':1,'addElementsByType':1,'rebuildNodeCache':1,
 'rebuildElementCache':1,'write_mesh':1,'generate':0,'optimize':0,'createGeometry':0,'reclassifyNodes':0,'solve':0}
FORBIDDEN=['generation_authorized','optimization_authorized','reclassification_authorized','renumbering_authorized',
 'surface_TRI_insertion_authorized','stitching_authorized','head_PDE_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']

QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def json_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def selected(path,names,namespace):
 tree=ast.parse((ROOT/path).read_text());rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in rows}!=set(names):raise ValueError('Exact selected frozen helper definitions required')
 exec(compile(ast.Module(body=rows,type_ignores=[]),path,'exec'),namespace)


def require_contract(c):
 if (c.get('schema')!='962-apex1474426-head-application/v1' or c.get('native_execution_authorized') is not True
     or c.get('partial_head_replacement_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('automatic_retry') is not False or c.get('head_execution_authorized') is not False
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('options')!=OPTIONS
     or c.get('declared_operation_counts')!=COUNTS or c.get('controls')!=CONTROLS or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT):
  raise ValueError('Separate reviewed one-partial-replacement actual authority required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed source/data/peer requires its exact direct pin')
 for name,digest in c['input_hashes'].items():
  path=ROOT/name
  if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or sha(path)!=digest:
   raise ValueError('Bound input drift: '+name)
 original=json.loads((ROOT/CONTEXT_CONTRACT).read_text())
 for key in ['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init','numpy_init_sha256','expected_runtime']:
  if c[key]!=original[key]:raise ValueError('Selected original runtime scope changed: '+key)
 if sha(Path(c['numpy_init']))!=c['numpy_init_sha256']:raise ValueError('Selected NumPy init changed')
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Exactly three selected native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source or interpreter changed')


def require_domain(domain,peer,observation,shell,a):
 if (domain.get('schema')!='962-exact-apex1474426-old60-new101-domain-result/v1' or domain.get('status')!='same_compact_oriented_local_domain'
     or any(domain.get(k) is not True for k in ['exact_old_pair_embedding','exact_candidate_pair_embedding','local_domain_equivalence_proved','bound_inputs_unchanged','exact_common32_coordinate_words','exact_identical_oriented60_boundary','exact_signed_volume_identity'])
     or domain.get('pair_failures')!={'old':0,'candidate':0}
     or (domain.get('old_complete_unordered_pairs'),domain.get('candidate_complete_unordered_pairs'),domain.get('complete_unordered_pairs'),domain.get('plane_triples_enumerated'))!=(1770,5050,6820,381920)
     or domain.get('source_sha256')!=FIXED_INPUTS[DOMAIN_SOURCE] or domain.get('contract_sha256')!=FIXED_INPUTS[DOMAIN_ACTUAL]
     or domain.get('source_candidate_report_sha256')!=WORKER_SHA or domain.get('source_candidate_arrays_sha256')!=ARRAYS_SHA
     or domain.get('source_candidate_independent_peer_sha256')!=FIXED_INPUTS[LOCAL_PEER]
     or domain.get('qualification')!=QUALIFICATION or domain.get('native_optimizer_or_meshwrite_calls')!=0 or domain.get('coordinates_changed') is not False
     or peer.get('schema')!='962-apex1474426-domain-independent-stopped-peer/v1' or peer.get('decision')!='CLEAR_COMPLETED_EXACT_LOCAL_DOMAIN_SAVED_ASSOCIATIONS'
     or peer.get('bindings',{}).get('report_sha256')!=FIXED_INPUTS[DOMAIN] or peer['bindings'].get('source_sha256')!=FIXED_INPUTS[DOMAIN_SOURCE]):
  raise ValueError('Completed current old60/new101 domain report and independent saved-association peer required')
 for name in [WORKER,ARRAYS,LOCAL_PEER,OBSERVATION,SHELL]:
  if domain['input_hashes'].get(name)!=FIXED_INPUTS[name]:raise ValueError('Current domain source/input association differs')
 expected_map={str(tag):i+1 for i,tag in enumerate(shell['local_to_global_node_tags'])};expected_map[str(APEX)]=33
 if domain.get('original_global_to_comparison_node_tags')!=expected_map:raise ValueError('Exact original60 comparison mapping required')
 expected_faces=sorted(min(tuple(face[i:]+face[:i]) for i in range(3)) for face in [row['local_node_tags'] for row in shell['oriented_triangle_rows']])
 for name,cells,count,internal in [('old',{row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']},1770,90),('candidate',dict(zip(a['tetra_tags'],a['tetra_node_tags'])),5050,172)]:
  data=domain[name];rows=domain['pair_results'][name]
  if (data['cell_count']!=len(cells) or data['internal_face_pairs']!=internal or data.get('all_exact_positive') is not True
      or [tuple(face) for face in data['oriented_boundary']]!=expected_faces
      or len(rows)!=count or [tuple(row['tetrahedron_tags']) for row in rows]!=list(combinations(sorted(cells),2))
      or any(row.get('intersection_equals_tagged_shared_simplex') is not True or row.get('plane_triples_enumerated')!=56 or row.get('illegal_intersection_vertices')!=0 or row.get('all_illegal_rational_witnesses')!=[] for row in rows)):
   raise ValueError('Complete current pair-result coverage/common shell required; predicates are not rerun')
 if domain['old']['exact_signed_volume_mm3']!=domain['candidate']['exact_signed_volume_mm3'] or domain['old']['exact_signed_volume_mm3']!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact current common-shell volume proof differs')

def candidate_rows(worker,arrays,domain,peer,observation,shell):
 a=arrays['saved_reopen'];state=worker['saved_reopen']
 if (worker.get('status')!='completed_specific_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA or worker['after']!=state
     or (state['nodes'],state['tetrahedra'],state['referenced_interior_nodes'],state['unreferenced_nodes'])!=(40,101,8,0)
     or a['node_tags']!=list(range(1,41)) or a['tetra_tags']!=list(range(288,389))
     or len(a['coordinates_mm'])!=40 or len(a['tetra_node_tags'])!=101 or arrays['after']!=a):
  raise ValueError('Exact completed current40-node101-cell raw saved Netgen state required')
 coordinates=[]
 for xyz in a['coordinates_mm']:
  if len(xyz)!=3 or any(type(v) is not float or not math.isfinite(v) for v in xyz):raise ValueError('Complete finite raw binary64 coordinate triples required')
  coordinates.append(list(xyz)) # Copy raw float words including signed zero, never Fraction roundtrips.
 if (any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int or t not in a['node_tags'] for t in row) for row in a['tetra_node_tags'])
     or set().union(*(set(row) for row in a['tetra_node_tags']))!=set(a['node_tags'])):raise ValueError('Full101 ordered TET4 membership and no orphan required')
 for name in ['SICN','Jacobian','native_volume_mm3']:
  values=a['native_qualities'][name]
  if len(values)!=101 or any(type(v) is not float or not math.isfinite(v) or v<=0 for v in values) or (name=='SICN' and any(v<.1 for v in values)):
   raise ValueError('Complete101 finite positive native metrics and unchanged SICN0.1 required')
 if [struct.pack('<3d',*row) for row in a['coordinates_mm']]!=[struct.pack('<3d',*row) for row in arrays['after']['coordinates_mm']]:raise ValueError('After/saved raw coordinate words differ')
 for saved,after in [(a['independent_signed_volume_mm3'],arrays['after']['independent_signed_volume_mm3']),*[(a['native_qualities'][n],arrays['after']['native_qualities'][n]) for n in ['SICN','Jacobian','native_volume_mm3']]]:
  if [struct.pack('<d',v) for v in saved]!=[struct.pack('<d',v) for v in after]:raise ValueError('After/saved raw metric words differ')
 require_domain(domain,peer,observation,shell,a)
 exact=domain['candidate']['quality_rows']
 if len(exact)!=101 or [row['tetrahedron_tag'] for row in exact]!=a['tetra_tags']:raise ValueError('Complete101 accepted exact candidate associations required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('exact_point1_gate_passed') is not True or Fraction(int(det['numerator']),int(det['denominator']))<=0 or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every current exact candidate positive determinant and SICN squared gate required')
 return coordinates


def edit_once(gmsh,case,counts):
 if len(case['old'])!=60 or not case['old']:raise ValueError('Empty or incomplete removal refused')
 if gmsh.model.mesh.getMaxNodeTag()!=case['nmax'] or gmsh.model.mesh.getMaxElementTag()!=case['emax']:
  raise ValueError('Actual global maxima differ from complete fixture arrays')
 for tag,row in case['old'].items():
  kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
  if kind!=4 or list(nodes)!=row or (dim,entity)!=(3,1):raise ValueError('Old element row/entity changed before removal')
 if gmsh.model.mesh.getNode(1474426)[2:]!=(3,1):raise ValueError('Apex storage slot has wrong class')
 counts['removeElements']+=1;gmsh.model.mesh.removeElements(3,1,sorted(case['old']))
 counts['setNode']+=1;gmsh.model.mesh.setNode(1474426,case['proposed'][1474426],[])
 tags=case['fresh_nodes']
 counts['addNodes']+=1;gmsh.model.mesh.addNodes(3,1,tags,[x for t in tags for x in case['proposed'][t]])
 counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(1,4,list(case['replacement']),[t for r in case['replacement'].values() for t in r])
 counts['rebuildNodeCache']+=1;gmsh.model.mesh.rebuildNodeCache(False)
 counts['rebuildElementCache']+=1;gmsh.model.mesh.rebuildElementCache(False)


def make_case(observation,shell,candidate,arrays,context,domain,domain_peer):
 coordinates=candidate_rows(candidate,arrays,domain,domain_peer,observation,shell)
 mapping=shell['local_to_global_node_tags'];old={row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']}
 if (observation.get('apex')!=APEX or len(mapping)!=32 or len(set(mapping))!=32 or APEX in mapping or len(old)!=60
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or context.get('status')!='complete_current_partial_head_apex1474426_context_census' or context.get('complete_context_census') is not True
     or context.get('original_parent_MSH_sha256')!=FIXED_INPUTS[MESH]
     or context['complete_old_apex_incident_rows']!=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)]
     or context['independently_derived_global_maxima']!={'node':NMAX,'element_all_dimensions':EMAX}):
  raise ValueError('Exact current60-star context, parent and all-dimensional maxima required')
 original={row['node_tag']:row for row in observation['selected_node_rows']};native={row['node_tag']:row for row in context['selected33_native_node_rows']}
 classes={tag:[row['dimension'],row['entity_tag']] for tag,row in native.items()}
 if set(original)!=set(mapping+[APEX]) or set(native)!=set(original):raise ValueError('All33 original coordinate/class rows required')
 for tag,row in original.items():
  actual=native[tag]
  if (struct.pack('<3d',*row['coordinates_mm'])!=struct.pack('<3d',*actual['coordinates_mm']) or [float(v).hex() for v in row['coordinates_mm']]!=row['binary64_hex']
      or actual['available_parametric_coordinates']!=[] or actual['parametric_binary64_hex']!=[]):raise ValueError('Every selected original coordinate word and observed parameter row must match current context')
 if len(shell['vertex_rows'])!=32:raise ValueError('All32 fixed source shell rows required')
 for local,row in enumerate(shell['vertex_rows'],1):
  tag=mapping[local-1]
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag
      or struct.pack('<3d',*coordinates[local-1]).hex()!=row['binary64_little_endian_bytes_hex']
      or struct.pack('<3d',*coordinates[local-1])!=struct.pack('<3d',*original[tag]['coordinates_mm'])
      or classes[tag]!=([2,1] if row['original_source_boundary_node'] else [3,1])):
   raise ValueError('Actual27 source-boundary and5 source-interior shell identities must stay exact')
 if sum(row['original_source_boundary_node'] for row in shell['vertex_rows'])!=27 or classes[APEX]!=[3,1]:raise ValueError('Exact27/5 shell classes and volume apex required')
 fresh=list(range(NMAX+1,NMAX+8));node_map={local:tag for local,tag in enumerate(mapping,1)};node_map.update({33:APEX,**dict(zip(range(34,41),fresh))})
 slots=sorted(old)+list(range(EMAX+1,EMAX+42));replacement={tag:[node_map[x] for x in row] for tag,row in zip(slots,arrays['saved_reopen']['tetra_node_tags'])}
 if len(replacement)!=101 or len(set(slots))!=101:raise ValueError('Exactly old60 slots plus41 globally fresh element tags required')
 proposed={node_map[tag]:list(xyz) for tag,xyz in zip(range(1,41),coordinates)}
 return dict(old=old,nmax=NMAX,emax=EMAX,node_map=node_map,element_slots=slots,replacement=replacement,proposed=proposed,classes=classes,fresh_nodes=fresh,expected_counts={'nodes':1097057,'TET4':3620861,'interior':225326})


def source_reference(core,gmsh,context):
 np=core.np;nt,xyz,_=gmsh.model.mesh.getNodes();ix=np.argsort(nt);nt=np.asarray(nt,dtype='<u8')[ix];xyz=np.asarray(xyz,dtype='<f8').reshape(-1,3)[ix]
 expected=np.arange(1,BOUNDARY+1,dtype='<u8');where=np.searchsorted(nt,expected)
 if np.any(where>=len(nt)) or not np.array_equal(nt[where],expected):raise ValueError('Every original surface tag required')
 points=np.ascontiguousarray(xyz[where]);types,tags,conn=gmsh.model.mesh.getElements(2)
 if list(types)!=[2] or len(tags)!=1:raise ValueError('Exact complete original TRI3 surface required')
 order=np.argsort(tags[0]);tt=np.asarray(tags[0],dtype='<u8')[order];rows=np.asarray(conn[0],dtype='<u8').reshape(-1,3)[order]
 lower=context['full_lower_dimensional_inventory']
 if (len(lower)!=1 or len(rows)!=1743878 or core.array_sha(tt)!=lower[0]['element_tags_u64_sha256']
     or core.array_sha(rows)!=lower[0]['ordered_connectivity_u64_sha256'] or np.any(rows<1) or np.any(rows>BOUNDARY)):
  raise ValueError('Full ordered parent surface typed hashes changed')
 return points,rows.astype(np.int64)-1


def metadata_snapshot(core,gmsh,state,case,context,after):
 np=core.np;xyz,nt,et,en=state;entities=sorted((int(d),int(t)) for d,t in gmsh.model.getEntities())
 entity_rows=[];lower=[];periodic=[];all_lower=[];groups=[];dimensions=np.full(len(nt),-1,dtype=np.int8);entity_tags=np.zeros(len(nt),dtype=np.int64)
 for dim,entity in entities:
  boundary=[list(map(int,row)) for row in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] if dim else []
  entity_rows.append({'dimension':dim,'entity_tag':entity,'oriented_immediate_boundary':boundary,'name':gmsh.model.getEntityName(dim,entity)})
  owned=np.asarray(gmsh.model.mesh.getNodes(dim,entity,False,False)[0],dtype='<u8');where=np.searchsorted(nt,owned)
  if (len(np.unique(owned))!=len(owned) or np.any(where>=len(nt)) or not np.array_equal(nt[where],owned) or np.any(dimensions[where]!=-1)):
   raise ValueError('Every current node must classify exactly once')
  dimensions[where]=dim;entity_tags[where]=entity
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
   all_lower.append(tt)
   lower.append({'dimension':dim,'entity_tag':entity,'element_type':kind,'nodes_per_element':width,'count':len(tt),
    'minimum_tag':int(tt.min()) if len(tt) else None,'maximum_tag':int(tt.max()) if len(tt) else None,
    'element_tags_u64_sha256':core.array_sha(tt),'ordered_connectivity_u64_sha256':core.array_sha(rows)})
 for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
  groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
 lower.sort(key=lambda row:(row['dimension'],row['entity_tag'],row['element_type']))
 if np.any(dimensions<0):raise ValueError('Missing current node classifications')
 original=~np.isin(nt,np.asarray(case['fresh_nodes'],dtype='<u8'))
 if (core.array_sha(nt[original])!=context['full_array_sha256s']['sorted_node_tags_sha256']
     or core.array_sha(dimensions[original])!=context['full_native_classifications']['node_classification_dimensions_sha256']
     or core.array_sha(entity_tags[original])!=context['full_native_classifications']['node_classification_entity_tags_sha256']):
  raise ValueError('Every original node tag and classification must remain exact')
 fresh=np.flatnonzero(~original)
 if (len(fresh)!=(7 if after else 0) or (after and (nt[fresh].tolist()!=case['fresh_nodes'] or np.any(dimensions[fresh]!=3) or np.any(entity_tags[fresh]!=1)))):
  raise ValueError('Only exactly seven fresh nodes on existing volume1 permitted')
 node_mask=~np.isin(nt,np.asarray([APEX,*case['fresh_nodes']],dtype='<u8'))
 removed=list(case['replacement'] if after else case['old']);cell_mask=~np.isin(et,np.asarray(removed,dtype='<u8'))
 preservation={'outside_node_tags_u64_sha256':core.array_sha(nt[node_mask]),'outside_coordinate_words_f64_sha256':core.array_sha(xyz[node_mask]),
  'outside_tetra_tags_u64_sha256':core.array_sha(et[cell_mask]),'outside_ordered_tetra_connectivity_u64_sha256':core.array_sha(en[cell_mask]),
  'outside_nodes':int(np.count_nonzero(node_mask)),'outside_TET4':int(np.count_nonzero(cell_mask))}
 for key,value in preservation.items():
  if context['future_preservation_references'][key]!=value:raise ValueError('Outside preservation changed: '+key)
 metadata={'full_lower_dimensional_inventory':lower,'full_entity_metadata':entity_rows,'full_physical_group_metadata':groups,'full_periodic_metadata':periodic}
 for key,value in metadata.items():
  if value!=context[key]:raise ValueError('Complete original lower/entity/physical/periodic metadata changed: '+key)
 all_et=np.concatenate([et,*all_lower])
 if len(np.unique(all_et))!=len(all_et):raise ValueError('All-dimensional element tag collision refused')
 maxima={'node':int(nt.max()),'element_all_dimensions':int(all_et.max())}
 if maxima!={'node':NMAX+(7 if after else 0),'element_all_dimensions':EMAX+(41 if after else 0)}:raise ValueError('Complete actual maxima changed')
 if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(maxima['node'],maxima['element_all_dimensions']):raise ValueError('Native tag caches differ from complete current arrays')
 for tag,expected in case['classes'].items():
  coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag)
  if [int(dim),int(entity)]!=expected or list(map(float,param))!=[]:raise ValueError('Selected original classification/parametric association changed')
  index=int(np.searchsorted(nt,tag));want=case['proposed'][tag] if after else next(r['coordinates_mm'] for r in context['selected33_native_node_rows'] if r['node_tag']==tag)
  if int(nt[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want) or struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*want):raise ValueError('Selected original coordinate words changed')
 if after:
  for tag,row in case['replacement'].items():
   index=int(np.searchsorted(et,tag))
   if index>=len(et) or int(et[index])!=tag or en[index].tolist()!=row:raise ValueError('Every new ordered replacement row required')
  for tag in case['fresh_nodes']:
   index=int(np.searchsorted(nt,tag))
   if struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*case['proposed'][tag]):raise ValueError('Fresh proposed coordinate words changed')
 return dict(preservation=preservation,metadata_sha256s={key:json_sha(value) for key,value in metadata.items()},
  original_classification_projection_exact=True,new_nodes_on_volume1=7 if after else 0,maxima=maxima)


def require_snapshot(before,after):
 if before['preservation']!=after['preservation'] or before['metadata_sha256s']!=after['metadata_sha256s']:
  raise ValueError('Any outside or complete original metadata drift refused')
 if after['original_classification_projection_exact'] is not True or after['new_nodes_on_volume1']!=7:raise ValueError('Every original classification and exactly seven new volume nodes required')


def require_original_records(core,worker,receipt,first,closed,metadata,context):
 proof=core.partial_after_proof(worker,receipt,closed,metadata);core.require_after_match(first,proof,208)
 if (metadata['MSH_sha256']!=FIXED_INPUTS[MESH] or metadata['partial_report_sha256']!=FIXED_INPUTS[ORIGINAL_WORKER]
     or metadata['partial_contract_sha256']!=FIXED_INPUTS['work/962-engineering/head-star-replacement-001/frozen-contract.json']
     or proof['array_sha256s']!=context['full_array_sha256s'] or proof['classifications']!=context['full_native_classifications']
     or proof['source_boundary_identity']!=context['current_source_boundary_identity'] or proof['quality']!=context['retained_current_quality_and_global_incidence']['quality']
     or (proof['total_mesh_nodes'],proof['tetrahedra'],proof['tetra_referenced_interior_nodes'],proof['unreferenced_mesh_nodes'])!=(1097050,3620820,225319,0)):
  raise ValueError('Single stopped current partial.after/saved, fresh208 census and current context required')
 for key,value in proof['array_sha256s'].items():
  if first[key]!=value:raise ValueError('Current census full tagged-array association differs')
 return proof


def valid_positive_volume(audit):
 return all(row['nonpositive_count']==0 for row in audit['quality'].values()) and audit['volume_relative_error']<=1e-6


def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Exactly fresh three-file materialization plus native.log required')
 report=dict(schema='962-apex1474426-head-application-result/v1',status='running',stage='imports',procedural_checks_passed=False,
  actual_whole_head_SICN_gate_passed=False,expected_whole_head_positive_poor_count_not_observed=204,
  expected_count_is_not_acceptance=True,native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  original_parent_MSH_sha256=FIXED_INPUTS[MESH],local_candidate_report_sha256=FIXED_INPUTS[WORKER],local_candidate_arrays_sha256=FIXED_INPUTS[ARRAYS],current_local_domain_report_sha256=FIXED_INPUTS[DOMAIN],current_local_domain_peer_sha256=FIXED_INPUTS[DOMAIN_PEER],context_sha256=FIXED_INPUTS[CONTEXT],
  original_local_domain_equivalence_is_separate=True,global_embedding_or_containment_proved=False,
  stronger_Mesh2_criterion_passed=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 started=time.monotonic();gmsh=None;initialized=False
 def checkpoint():
  with (OUT/'readback-report.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 try:
  import numpy as np
  import gmsh
  observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
  runtime={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(gmsh.__file__),'gmsh_library':sha(gmsh.lib._name)}
  if (observed!=RUNTIME or runtime!=c['runtime_sha256s'] or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve() or sha(np.__file__)!=c['numpy_init_sha256']):raise ValueError('Exact selected native/NumPy runtime required')
  report.update(runtime=observed,runtime_sha256s=runtime)
  ns={'np':np,'math':math,'hashlib':hashlib}
  selected(HEAD,['array_sha','volume_arrays','canonical_oriented','surface_roundtrip','distribution','tetra_volumes','tetra_boundary'],ns)
  selected(CORE,['tagged_volume','internal_face_orientation'],ns)
  selected(AUDIT,['classifications','array_identity','boundary_identity','audit_after'],ns)
  selected(PROOF_SOURCE,['partial_after_proof','require_after_match'],ns)
  core=SimpleNamespace(np=np,CANDIDATE_VOLUME=915453.1236217883,**{k:v for k,v in ns.items() if callable(v)})
  context=json.loads((ROOT/CONTEXT).read_text());observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text())
  candidate=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text())
  domain=json.loads((ROOT/DOMAIN).read_text());domain_peer=json.loads((ROOT/DOMAIN_PEER).read_text());case=make_case(observation,shell,candidate,arrays,context,domain,domain_peer)
  worker=json.loads((ROOT/ORIGINAL_WORKER).read_text());first=json.loads((ROOT/FIRST).read_text())
  proof=require_original_records(core,worker,json.loads((ROOT/ORIGINAL_RECEIPT).read_text()),first,json.loads((ROOT/PARTIAL_CLOSED).read_text()),json.loads((ROOT/PARTIAL_METADATA).read_text()),context)
  report.update(local_to_global_node_map=case['node_map'],replacement_element_slots=case['element_slots'],replacement_ordered_rows=case['replacement'])
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='opening_exact_current_partial_head';checkpoint();gmsh.open(str(ROOT/MESH))
  points,faces=source_reference(core,gmsh,context)
  report['stage']='complete_before_audit';checkpoint();state,before=core.audit_after(core,gmsh,points,faces)
  before['source_boundary_identity']=core.boundary_identity(core,state,points,before['classifications'])
  if before!=proof or not valid_positive_volume(before):raise ValueError('Complete fresh original audit must equal sole current partial worker.after')
  before_snapshot=metadata_snapshot(core,gmsh,state,case,context,False);del state
  report.update(before=before,before_preservation=before_snapshot,stage='one_tag_sparse_replacement');checkpoint()
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed before replacement')
  report['partial_replacement_attempted']=True;edit_once(gmsh,case,report['native_operation_counts']);report['partial_replacement_completed']=True
  report['stage']='complete_after_audit';checkpoint();state,after=core.audit_after(core,gmsh,points,faces)
  after['source_boundary_identity']=core.boundary_identity(core,state,points,after['classifications'])
  after_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,after_snapshot)
  if (after['total_mesh_nodes'],after['tetrahedra'],after['tetra_referenced_interior_nodes'])!=(1097057,3620861,225326) or not valid_positive_volume(after):raise ValueError('Actual changed counts/positive metrics/relative volume gate failed')
  if after['source_boundary_identity']!=before['source_boundary_identity']:raise ValueError('Original exact boundary bits/classes/periodicity changed')
  local_et=np.asarray(case['element_slots'],dtype='<u8');local_metrics={name:np.asarray(gmsh.model.mesh.getElementQualities(local_et,api),dtype='<f8') for name,api in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
  if any(len(v)!=101 or not np.isfinite(v).all() or np.any(v<=0) for v in local_metrics.values()) or np.any(local_metrics['SICN']<.1):raise ValueError('Every actual replacement cell must freshly pass unchanged local SICN/positivity gate')
  report.update(after=after,after_preservation=after_snapshot,replacement101_native_metrics={k:v.tolist() for k,v in local_metrics.items()},actual_replacement101_SICN_gate_passed=True)
  del state
  path=OUT/'head-volume.msh';report['stage']='saving_partial_repair';checkpoint();report['native_operation_counts']['write_mesh']+=1;gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit';checkpoint();state,saved=core.audit_after(core,gmsh,points,faces)
  saved['source_boundary_identity']=core.boundary_identity(core,state,points,saved['classifications'])
  saved_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,saved_snapshot)
  if saved!=after or saved_snapshot!=after_snapshot or sha(path)!=digest:raise ValueError('Full after/saved tagged arrays/metrics/classifications/metadata identity changed')
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()) or report['native_operation_counts']!=COUNTS:raise ValueError('Exact options/API operation attempts changed')
  report.update(saved_reopen=saved,saved_preservation=saved_snapshot,saved_mesh_identity_exact=True,mesh_sha256=digest,mesh_bytes=path.stat().st_size,
   procedural_checks_passed=True,actual_whole_head_SICN_gate_passed=after['quality']['minimum_SICN']['minimum']>=.1,
   actual_whole_head_positive_poor_count=after['quality']['minimum_SICN']['below_point1_count'],stage='completed_partial_repair_audits',status='completed_partial_head_replacement_whole_head_quality_gate_applied')
 except Exception as error:report.update(status='refused_or_failed_outputs_preserved',error=type(error).__name__+': '+str(error))
 finally:
  if initialized:
   try:report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))];gmsh.logger.stop()
   except Exception as error:report.update(status='failed_runtime_cleanup',cleanup_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
   try:gmsh.finalize()
   except Exception as error:report.update(status='failed_runtime_cleanup',finalize_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
  try:require_contract(c);report['bound_inputs_unchanged']=True
  except Exception:report['bound_inputs_unchanged']=False
  report['wall_seconds']=time.monotonic()-started;checkpoint()
 return 0 if report['procedural_checks_passed'] and report['actual_whole_head_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2


if __name__=='__main__':raise SystemExit(main())
