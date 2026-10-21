"""HELD one exact original-head28-to39 partial repair; no mesher or optimizer."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
import ast,hashlib,json,math,platform,struct,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/head-star-replacement-001'
MESH='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/head-volume.msh'
CONTEXT='work/962-engineering/head-star-context-census-001/readback-report.json'
OBSERVATION='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
CANDIDATE='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
ORIGINAL_WORKER='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/worker-report.json'
FIRST='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json'
DIAGNOSIS='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-optimized-diagnosis-001/readback-report.json'
ORIGINAL_RECEIPT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/receipt.json'
HEAD='twins/962-cylinder-head-f0/source/mesh_head.py'
CORE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
AUDIT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py': '0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a', 'work/962-engineering/tag-sparse-star-edit-cube-prep-001/reader.py': '3ca04d04ef849e6f130e6cde632a9615de911ddc9d14c8c28d410cefc4c50af5', 'work/962-engineering/tag-sparse-star-edit-cube-001/fixture-report.json': '579608f4a3d19876802d68e513f06a9fedeb61f335b9f5149765543e24a1765e', 'work/962-engineering/tag-sparse-star-edit-cube-result-peer-001/review.json': '6ca5a91ddcddc2307dc8285551f3ad3aaf26c0e0db147ba78620d050422dd7fe', 'work/962-engineering/head-star-context-census-001/readback-report.json': '14dbff3287a47ecd6cffaba0ca8aef68b04920234623c344d3ebd2154df29061', 'work/962-engineering/head-star-context-census-001/execution-receipt.json': '8caaef375da54b98798e9baa1112acc432a5506557a79d44caffff60c67fb2d3', 'work/962-engineering/head-star-context-census-001/frozen-contract.json': 'acfaed980dde61ded4775be938e102b1d98467a00bdeb8f1002be3f65ec5f31f', 'work/962-engineering/head-star-context-census-result-peer-001/review.json': 'f241ad9d32cc3fda27891bafd1adfbf2ed99161c9d1eca085d51760894acede3', 'work/962-engineering/head-star-context-census-root-execution-001/closed-result.json': 'fd8975499f876c892d0e186cc0b4c8343159d9e32efb07242072f798830e70c3', 'work/962-engineering/head-star-context-census-prep-001/reader.py': 'c59e0c14dd3e6ee9747168ac80f4284374ef62025fe4ec59e171f128ada2122a', 'work/962-engineering/domain-equivalence-001/report.json': '5ced0d27239b3523e459073b0bcd00512da5ec045e5dbbcf27caaa2a3dfff1e5', 'work/962-engineering/domain-equivalence-result-peer-001/review.json': '07a77de0e03534a24c496ca1e18ebdda7a19ceb0c1cec19768d61268a0629b4f', 'work/962-engineering/fixed-shell-coupled-embedding-001/report.json': '478a6e42824772b181ed0d8f9d3523f6fe4e0c07043a9cdc0afe1916f7fe7240', 'work/962-engineering/fixed-shell-coupled-embedding-result-peer-001/review.json': '24ba3917b38c238b9d9e8faa4af0e254c2d6578125e25294fc8ab61678a2589c', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json': '53a1fb5696d46c8773eea0ffd3a971706946b380a0b3a5f5ba41d1d6a121d15a', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json': 'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8', 'work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json': 'e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a', 'work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json': 'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f', 'work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json': '8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7', 'work/962-engineering/fixed-shell-coupled-sicn-apply-001/fixture-report.json': '1abe79cbda293b9d6f4b5d6e7dc737cbea15c24de13d4704ddd45302cf98bc88', 'work/962-engineering/fixed-shell-coupled-sicn-apply-result-peer-001/review.json': '7b4b85b1d366de2b1750920e6d9adfee83caf289a0a7b8742fb0c0bdb589f63f', 'work/962-engineering/fixed-shell-coupled-sicn-result-peer-001/review.json': '0adbeea0bef35c5a1f30f610c87bb27ef4333530ff2039e9e4c91a512287732b', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/worker-report.json': '16f6ecc580d766c3c541517f0f89bd80d5cd0f660f40b157a04c5362c2245e6a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/receipt.json': '426e76e578b4ae0093e85515703f216c64cf1b2aaaf7474d6d8fb8a4641a32de', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json': '5946ffbd9f2f127306673d967b583b11d8906793e2079971bc0430d65ae65f88', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001/head-volume.msh': '4b983f4ab0134d01573059aecb8f4ba512dabbdfe54fbce6abaa0a06af29fe1d'}
FIXED_INPUTS[DIAGNOSIS]='94ff85bf941205cb67024d42b47b66256b2af19eb34904762efb4bcd1cdb0235'
ARRAYS_SHA=FIXED_INPUTS[ARRAYS];WORKER_SHA=FIXED_INPUTS[WORKER]
AUDIT_INPUTS={SHELL:FIXED_INPUTS[SHELL]};FREE=[27,28,29]
APEX=1435493;NMAX=1613803;EMAX=32158115;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
CONTROLS={'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8*1024**3,'sampled_output_stop_bytes':1024**3,'native_threads':2,'automatic_retry':False}
COUNTS={'removeElements':1,'setNode':1,'addNodes':1,'addElementsByType':1,'rebuildNodeCache':1,
 'rebuildElementCache':1,'write_mesh':1,'generate':0,'optimize':0,'createGeometry':0,'reclassifyNodes':0,'solve':0}
FORBIDDEN=['generation_authorized','optimization_authorized','reclassification_authorized','renumbering_authorized',
 'surface_TRI_insertion_authorized','stitching_authorized','head_PDE_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']

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
 if (c.get('schema')!='962-held-head-star-replacement/v1' or c.get('native_execution_authorized') is not True
     or c.get('partial_head_replacement_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('automatic_retry') is not False
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('options')!=OPTIONS
     or c.get('declared_operation_counts')!=COUNTS or c.get('controls')!=CONTROLS or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT):
  raise ValueError('Separate reviewed one-partial-replacement actual authority required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed source/data/peer requires its exact direct pin')
 for name,digest in c['input_hashes'].items():
  path=ROOT/name
  if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or sha(path)!=digest:
   raise ValueError('Bound input drift: '+name)
 original=json.loads((ROOT/'work/962-engineering/head-star-context-census-001/frozen-contract.json').read_text())
 for key in ['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init','numpy_init_sha256','expected_runtime']:
  if c[key]!=original[key]:raise ValueError('Selected original runtime scope changed: '+key)
 if sha(Path(c['numpy_init']))!=c['numpy_init_sha256']:raise ValueError('Selected NumPy init changed')
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Exactly three selected native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source or interpreter changed')

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

def edit_once(gmsh,case,counts):
 if len(case['old'])!=28 or not case['old']:raise ValueError('Empty or incomplete removal refused')
 if gmsh.model.mesh.getMaxNodeTag()!=case['nmax'] or gmsh.model.mesh.getMaxElementTag()!=case['emax']:
  raise ValueError('Actual global maxima differ from complete fixture arrays')
 for tag,row in case['old'].items():
  kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
  if kind!=4 or list(nodes)!=row or (dim,entity)!=(3,1):raise ValueError('Old element row/entity changed before removal')
 if gmsh.model.mesh.getNode(1435493)[2:]!=(3,1):raise ValueError('Apex storage slot has wrong class')
 counts['removeElements']+=1;gmsh.model.mesh.removeElements(3,1,sorted(case['old']))
 counts['setNode']+=1;gmsh.model.mesh.setNode(1435493,case['proposed'][1435493],[])
 tags=[case['nmax']+1,case['nmax']+2]
 counts['addNodes']+=1;gmsh.model.mesh.addNodes(3,1,tags,[x for t in tags for x in case['proposed'][t]])
 counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(1,4,list(case['replacement']),[t for r in case['replacement'].values() for t in r])
 counts['rebuildNodeCache']+=1;gmsh.model.mesh.rebuildNodeCache(False)
 counts['rebuildElementCache']+=1;gmsh.model.mesh.rebuildElementCache(False)

def make_case(observation,shell,candidate,arrays,context):
 coordinates,changes=candidate_rows(candidate,arrays['saved_reopen'])
 if changes!=[28,29] or observation.get('apex')!=APEX:raise ValueError('Specific accepted local39-cell candidate and original apex required')
 mapping=shell['local_to_global_node_tags'];old={r['tetrahedron_tag']:r['node_tags'] for r in observation['native_ordered_cell_rows']}
 if (len(mapping)!=16 or len(set(mapping))!=16 or APEX in mapping or len(old)!=28
     or any(len(r)!=4 or len(set(r))!=4 or APEX not in r for r in old.values())
     or context.get('status')!='complete_original_head_star_context_census' or context.get('complete_context_census') is not True
     or context['complete_old_apex_incident_rows']!=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)]
     or context['independently_derived_global_maxima']!={'node':NMAX,'element_all_dimensions':EMAX}):
  raise ValueError('Exact completed original28-star context and all-dimensional maxima required')
 original={r['node_tag']:r for r in observation['selected_node_rows']}
 classes={r['node_tag']:[r['dimension'],r['entity_tag']] for r in context['selected17_native_node_rows']}
 if set(original)!=set(mapping+[APEX]) or set(classes)!=set(original):raise ValueError('All17 original coordinate/class rows required')
 for local,row in enumerate(shell['vertex_rows'],1):
  tag=mapping[local-1]
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag
      or struct.pack('<3d',*coordinates[local-1]).hex()!=row['binary64_little_endian_bytes_hex']
      or struct.pack('<3d',*coordinates[local-1])!=struct.pack('<3d',*original[tag]['coordinates_mm'])
      or classes[tag]!=([2,1] if local<=9 else [3,1])):raise ValueError('Actual nine surface/seven interior shell identities must stay exact')
 if classes[APEX]!=[3,1]:raise ValueError('Reused original apex must remain on existing volume1')
 node_map={local:tag for local,tag in enumerate(mapping,1)};node_map.update({27:APEX,28:NMAX+1,29:NMAX+2})
 slots=sorted(old)+list(range(EMAX+1,EMAX+12))
 replacement={tag:[node_map[x] for x in row] for tag,row in zip(slots,arrays['saved_reopen']['tetra_node_tags'])}
 if len(replacement)!=39 or len(set(slots))!=39:raise ValueError('Exactly old28slots plus11 globally fresh element tags required')
 proposed={node_map[tag]:xyz for tag,xyz in zip(list(range(1,17))+FREE,coordinates)}
 return dict(old=old,nmax=NMAX,emax=EMAX,node_map=node_map,element_slots=slots,replacement=replacement,
  proposed=proposed,classes=classes,fresh_nodes=[NMAX+1,NMAX+2],expected_counts={'nodes':1097050,'TET4':3620820,'interior':225319})

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
 if (len(fresh)!=(2 if after else 0) or (after and (nt[fresh].tolist()!=case['fresh_nodes'] or np.any(dimensions[fresh]!=3) or np.any(entity_tags[fresh]!=1)))):
  raise ValueError('Only exactly two fresh nodes on existing volume1 permitted')
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
 if maxima!={'node':NMAX+(2 if after else 0),'element_all_dimensions':EMAX+(11 if after else 0)}:raise ValueError('Complete actual maxima changed')
 if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(maxima['node'],maxima['element_all_dimensions']):raise ValueError('Native tag caches differ from complete current arrays')
 for tag,expected in case['classes'].items():
  coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag)
  if [int(dim),int(entity)]!=expected or list(map(float,param))!=[]:raise ValueError('Selected original classification/parametric association changed')
  index=int(np.searchsorted(nt,tag));want=case['proposed'][tag] if after else next(r['coordinates_mm'] for r in context['selected17_native_node_rows'] if r['node_tag']==tag)
  if int(nt[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want) or struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*want):raise ValueError('Selected original coordinate words changed')
 if after:
  for tag,row in case['replacement'].items():
   index=int(np.searchsorted(et,tag))
   if index>=len(et) or int(et[index])!=tag or en[index].tolist()!=row:raise ValueError('Every new ordered replacement row required')
  for tag in case['fresh_nodes']:
   index=int(np.searchsorted(nt,tag))
   if struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*case['proposed'][tag]):raise ValueError('Fresh proposed coordinate words changed')
 return dict(preservation=preservation,metadata_sha256s={key:json_sha(value) for key,value in metadata.items()},
  original_classification_projection_exact=True,new_nodes_on_volume1=2 if after else 0,maxima=maxima)

def require_snapshot(before,after):
 if before['preservation']!=after['preservation'] or before['metadata_sha256s']!=after['metadata_sha256s']:
  raise ValueError('Any outside or complete original metadata drift refused')
 if after['original_classification_projection_exact'] is not True or after['new_nodes_on_volume1']!=2:raise ValueError('Every original classification and exactly two new volume nodes required')

def require_original_records(worker,receipt,first,diagnosis,context):
 proof=worker['after']
 if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None or receipt.get('worker_report')!=worker
     or worker.get('saved_mesh_identity_exact') is not True or worker.get('bound_inputs_unchanged') is not True
     or receipt.get('bound_inputs_unchanged') is not True or worker.get('mesh_sha256')!=FIXED_INPUTS[MESH]
     or receipt.get('mesh_sha256')!=FIXED_INPUTS[MESH] or worker.get('mesh_bytes')!=235742414
     or diagnosis.get('status')!='direct_saved_file_readback_completed' or diagnosis.get('bound_inputs_unchanged') is not True
     or diagnosis.get('single_optimized_worker_proof')!={'worker_report_sha256':FIXED_INPUTS[ORIGINAL_WORKER],'field':'after','independent_prior_reader_alias_used':False}
     or diagnosis.get('direct_counts_metrics_and_positive_poor_total_match_single_worker_after') is not True
     or proof['array_sha256s']!=context['full_array_sha256s'] or proof['classifications']!=context['full_native_classifications']
     or first.get('direct_fresh_classifications')!=proof['classifications'] or first.get('bound_inputs_unchanged') is not True):
  raise ValueError('Single stopped original worker.after, completed diagnosis, first census and context required')
 for key,value in proof['array_sha256s'].items():
  if diagnosis[key]!=value or first[key]!=value:raise ValueError('Original full tagged array association differs')
 for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes')]:
  if diagnosis[observed]!=proof[expected]:raise ValueError('Original completed diagnosis count differs')
 for observed,expected in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
  if any(diagnosis['direct_native_quality_extrema'][observed].get(k)!=v for k,v in proof['quality'][expected].items()):raise ValueError('Original completed native metric association differs')
 signed=diagnosis['independent_signed_volume_mm3']
 if (any(signed[k]!=v for k,v in proof['quality']['independent_signed_volume_mm3'].items())
     or signed['sum']!=proof['summed_tetra_volume_mm3'] or signed['relative_error_to_candidate']!=proof['volume_relative_error']
     or proof['quality']['minimum_SICN']['below_point1_count']!=210 or diagnosis['positive_poor_SICN_cells']['total']!=210):raise ValueError('Original signed volume/210-poor baseline differs')
 return proof

def valid_positive_volume(audit):
 return all(row['nonpositive_count']==0 for row in audit['quality'].values()) and audit['volume_relative_error']<=1e-6

def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Exactly fresh three-file materialization plus native.log required')
 report=dict(schema='962-one-head-star-partial-replacement/v1',status='running',stage='imports',procedural_checks_passed=False,
  actual_whole_head_SICN_gate_passed=False,expected_whole_head_positive_poor_count_not_observed=208,
  expected_count_is_not_acceptance=True,native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  original_parent_MSH_sha256=FIXED_INPUTS[MESH],candidate_sha256=FIXED_INPUTS[CANDIDATE],context_sha256=FIXED_INPUTS[CONTEXT],
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
  core=SimpleNamespace(np=np,CANDIDATE_VOLUME=915453.1236217883,**{k:v for k,v in ns.items() if callable(v)})
  context=json.loads((ROOT/CONTEXT).read_text());observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text())
  candidate=json.loads((ROOT/CANDIDATE).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());case=make_case(observation,shell,candidate,arrays,context)
  worker=json.loads((ROOT/ORIGINAL_WORKER).read_text());first=json.loads((ROOT/FIRST).read_text())
  proof=require_original_records(worker,json.loads((ROOT/ORIGINAL_RECEIPT).read_text()),first,json.loads((ROOT/DIAGNOSIS).read_text()),context)
  report.update(local_to_global_node_map=case['node_map'],replacement_element_slots=case['element_slots'],replacement_ordered_rows=case['replacement'])
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='opening_exact_original_head';checkpoint();gmsh.open(str(ROOT/MESH))
  points,faces=source_reference(core,gmsh,context)
  report['stage']='complete_before_audit';checkpoint();state,before=core.audit_after(core,gmsh,points,faces)
  before['source_boundary_identity']=core.boundary_identity(core,state,points,before['classifications'])
  if before!=proof or not valid_positive_volume(before):raise ValueError('Complete fresh original audit must equal sole original worker.after')
  before_snapshot=metadata_snapshot(core,gmsh,state,case,context,False);del state
  report.update(before=before,before_preservation=before_snapshot,stage='one_tag_sparse_replacement');checkpoint()
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed before replacement')
  report['partial_replacement_attempted']=True;edit_once(gmsh,case,report['native_operation_counts']);report['partial_replacement_completed']=True
  report['stage']='complete_after_audit';checkpoint();state,after=core.audit_after(core,gmsh,points,faces)
  after['source_boundary_identity']=core.boundary_identity(core,state,points,after['classifications'])
  after_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,after_snapshot)
  if (after['total_mesh_nodes'],after['tetrahedra'],after['tetra_referenced_interior_nodes'])!=(1097050,3620820,225319) or not valid_positive_volume(after):raise ValueError('Actual changed counts/positive metrics/relative volume gate failed')
  if after['source_boundary_identity']!=before['source_boundary_identity']:raise ValueError('Original exact boundary bits/classes/periodicity changed')
  local_et=np.asarray(case['element_slots'],dtype='<u8');local_metrics={name:np.asarray(gmsh.model.mesh.getElementQualities(local_et,api),dtype='<f8') for name,api in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
  if any(len(v)!=39 or not np.isfinite(v).all() or np.any(v<=0) for v in local_metrics.values()) or np.any(local_metrics['SICN']<.1):raise ValueError('Every actual replacement cell must freshly pass unchanged local SICN/positivity gate')
  report.update(after=after,after_preservation=after_snapshot,replacement39_native_metrics={k:v.tolist() for k,v in local_metrics.items()},actual_replacement39_SICN_gate_passed=True)
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
