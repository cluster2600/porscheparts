"""HELD one fixed current110 component SLSQP diagnostic; no native application."""
from fractions import Fraction
import hashlib,importlib,importlib.util,json,math,re,struct,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
LIMITS=dict(wall_seconds=30,sampled_RSS_bytes=1024**3,sampled_output_bytes=16*1024**2,threads=2)
SOLVER=dict(method='SLSQP',maxiter=100,ftol=1e-10,eps=2.0**-26)
GATE=.1
FREE=[]  # Bound once from one exact frozen component in a separate process.
ROLES={'census': 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json', 'census_acceptance': 'work/962-engineering/head-star-current110-full-stars-root-execution-001/result-peer-acceptance.json', 'graph': 'work/962-engineering/head-star-current110-coupling-graph-001/coupling-graph.json', 'graph_acceptance': 'work/962-engineering/head-star-current110-coupling-graph-001/root-review.json', 'worker': 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json', 'worker_acceptance': 'work/962-engineering/current126-alternative-combined-application-root-execution-001/result-peer-acceptance.json', 'runtime_donor': 'work/962-engineering/fixed-shell-coupled-sicn-prep-001/held-contract.json'}
DESCRIPTORS={'census': {'path': 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json', 'sha256': '657fbb0ce1c89dbf691f5a07c62feedf0fd91f7bc78f21d2aa14a3e01a9566da', 'bytes': 1691746}, 'census_acceptance': {'path': 'work/962-engineering/head-star-current110-full-stars-root-execution-001/result-peer-acceptance.json', 'sha256': '3d21b5f1e2cca935e6840e6444acd247b74ef877462c3382a07798c0217c7ed0', 'bytes': 3370}, 'graph': {'path': 'work/962-engineering/head-star-current110-coupling-graph-001/coupling-graph.json', 'sha256': 'cf50b7abb47a35dcfdc52fd95605d2eec6ce406dd3a2d528439dfc7c6fe3de0b', 'bytes': 1198884}, 'graph_acceptance': {'path': 'work/962-engineering/head-star-current110-coupling-graph-001/root-review.json', 'sha256': '7d8925cfc3a4d8c445b4cfd7282d9092768e49f81637c97e01be820961ba4145', 'bytes': 2897}, 'worker': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json', 'sha256': '522b994bf693231cbbc5d7a098200b4746d20bc65b2e91235d6bbe2b3c676732', 'bytes': 289378}, 'worker_acceptance': {'path': 'work/962-engineering/current126-alternative-combined-application-root-execution-001/result-peer-acceptance.json', 'sha256': 'a0a889ab8b7ae77bcfcce4da464492eebf3472c782329a4dedc7252493c7ab46', 'bytes': 85319}, 'runtime_donor': {'path': 'work/962-engineering/fixed-shell-coupled-sicn-prep-001/held-contract.json', 'sha256': '5d55d648d65b76e4482210d7f02244dea44025332eea09b3566ae81cba247790', 'bytes': 16664}}
MANIFEST='work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json'
INPUTS={'work/962-engineering/head-star-current110-full-stars-001/readback-report.json': '657fbb0ce1c89dbf691f5a07c62feedf0fd91f7bc78f21d2aa14a3e01a9566da', 'work/962-engineering/head-star-current110-full-stars-root-execution-001/result-peer-acceptance.json': '3d21b5f1e2cca935e6840e6444acd247b74ef877462c3382a07798c0217c7ed0', 'work/962-engineering/head-star-current110-coupling-graph-001/coupling-graph.json': 'cf50b7abb47a35dcfdc52fd95605d2eec6ce406dd3a2d528439dfc7c6fe3de0b', 'work/962-engineering/head-star-current110-coupling-graph-001/root-review.json': '7d8925cfc3a4d8c445b4cfd7282d9092768e49f81637c97e01be820961ba4145', 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json': '522b994bf693231cbbc5d7a098200b4746d20bc65b2e91235d6bbe2b3c676732', 'work/962-engineering/current126-alternative-combined-application-root-execution-001/result-peer-acceptance.json': 'a0a889ab8b7ae77bcfcce4da464492eebf3472c782329a4dedc7252493c7ab46', 'work/962-engineering/fixed-shell-coupled-sicn-prep-001/held-contract.json': '5d55d648d65b76e4482210d7f02244dea44025332eea09b3566ae81cba247790', 'work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json': '8ae9f9e93aee4b9d06936c87f856b6e318e0b4ce5dbf5e9d78c9b99acdd8f8d7'}
SOURCE_MSH_SHA='1b3a5a454b9fcbeb2cf5d36aaa8be0bc9cce9319897e47a31af3ac597d5cdb20'
QUALIFICATION={'native_application_authorized': False, 'head_execution_authorized': False, 'stitching_authorized': False, 'engineering_accepted': False, 'physics_qualified': False, 'manufacturing_authorized': False, 'material_qualified': False, 'process_calibrated': False, 'training_authorized': False}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')

def signed_sicn_vector(np, points, allow_planar=False):
    """Same ideal-reference/cofactor expression as the calibrated scalar; no regularizer."""
    p = np.asarray(points)
    if p.ndim!=3 or p.shape[1:]!=(4,3) or p.dtype.kind not in 'fiu':
        raise ValueError('Finite numeric (n,4,3) coordinates required')
    p = p.astype(np.float64, copy=False)
    if not np.all(np.isfinite(p)):raise ValueError('Nonfinite coordinates')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        e = p[:,1:,:]-p[:,0:1,:]
        a = e[:,0,:]; b = (2.*e[:,1,:]-e[:,0,:])/math.sqrt(3.)
        c = math.sqrt(1.5)*(e[:,2,:]-(e[:,0,:]+e[:,1,:])/3.)
        bc,ca,ab = np.cross(b,c),np.cross(c,a),np.cross(a,b)
        rowdot = lambda x,y: np.einsum('ij,ij->i',x,y)
        determinant = rowdot(a,bc)
        denominator2 = (rowdot(a,a)+rowdot(b,b)+rowdot(c,c))*(rowdot(bc,bc)+rowdot(ca,ca)+rowdot(ab,ab))
        if (not np.all(np.isfinite(determinant)) or not np.all(np.isfinite(denominator2))
                or np.any(denominator2<=0) or (not allow_planar and np.any(determinant==0))):
            raise ValueError('Degenerate/nonfinite iterate refused without regularization')
        q = 3.*determinant/np.sqrt(denominator2)
    if not np.all(np.isfinite(q)):raise ValueError('Nonfinite signed SICN')
    return q  # Negative values remain violated inequalities, never absolute values.

def tagged_indices(node_tags, cells, movable_tags):
    valid = lambda tags: (list(tags)==sorted(set(tags)) and all(type(t) is int and 0<t<2**64 for t in tags))
    if not valid(node_tags) or not valid(movable_tags) or not set(movable_tags)<=set(node_tags):
        raise ValueError('Sorted unique bounded node tags and movable subset required')
    lookup = {t:i for i,t in enumerate(node_tags)}
    if any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int or t not in lookup for t in row) for row in cells):
        raise ValueError('Every TET4 needs four distinct known node tags')
    return [[lookup[t] for t in row] for row in cells], [lookup[t] for t in movable_tags]

def assemble_points(np, original, positions, vector):
    x = np.asarray(vector, dtype=np.float64)
    if x.shape!=(3*len(positions)+1,) or not np.all(np.isfinite(x)):
        raise ValueError('Finite coordinate variables plus one epigraph variable required')
    points = original.copy()
    points[positions] = x[:-1].reshape((-1,3))
    return points

def same_numpy(module, original, expected_origin):
    if module is not original or module.__version__!='2.2.6' or Path(module.__file__).resolve()!=Path(expected_origin).resolve():
        raise ValueError('Selected NumPy object/version/origin changed')

def loaded_files(c):
    """Supplementary actually-loaded inventory, not complete package/OS closure."""
    rows={}
    for name,module in tuple(sys.modules.items()):
        if name=='numpy' or name.startswith('numpy.') or name=='scipy' or name.startswith('scipy.'):
            filename=getattr(module,'__file__',None)
            if filename:
                p=Path(filename).resolve(); root=Path(c['numpy_init']).resolve().parent if name.split('.')[0]=='numpy' else Path(c['scipy_directory']).resolve()
                if not p.is_relative_to(root):raise ValueError('Loaded module escaped selected package')
                actual=sha(p); expected=c['runtime_files'].get(str(p))
                if expected is not None and actual!=expected:raise ValueError('Selected module changed')
                rows[str(p)]=dict(sha256=actual,selected_prebound=expected is not None)
    return rows

def scientific_modules(c):
    import numpy as np
    same_numpy(np,np,c['numpy_init']); original=np; old_path=tuple(sys.path)
    directory=Path(c['scipy_directory']).resolve()
    if directory.name!='scipy' or 'scipy' in sys.modules:raise ValueError('Exact initially unloaded SciPy required')
    spec=importlib.util.spec_from_file_location('scipy',directory/'__init__.py',submodule_search_locations=[str(directory)])
    scipy=importlib.util.module_from_spec(spec); sys.modules['scipy']=scipy; spec.loader.exec_module(scipy)
    optimize=importlib.import_module('scipy.optimize')
    if scipy.__version__!='1.17.1' or Path(scipy.__file__).resolve()!=directory/'__init__.py' or tuple(sys.path)!=old_path:
        raise ValueError('SciPy origin/version or module search path changed')
    same_numpy(sys.modules['numpy'],original,c['numpy_init']); loaded_files(c)
    return np,optimize

def rational(value):
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))

def subtract(a,b):
    return [x-y for x,y in zip(a,b)]

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

def exact_quality(coordinates):
    if len(coordinates)!=4 or any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in coordinates):
        raise ValueError('Four finite binary64 triples required')
    p=[[Fraction.from_float(float(x)) for x in row] for row in coordinates]
    a,e2,e3=[subtract(row,p[0]) for row in p[1:]]
    b=[2*y-x for x,y in zip(a,e2)];c=[3*z-x-y for x,y,z in zip(a,e2,e3)]
    determinant=dot(a,cross(e2,e3))
    norm2=dot(a,a)+dot(b,b)/3+dot(c,c)/6
    bc,ca,ab=cross(b,c),cross(c,a),cross(a,b)
    cofactor2=dot(bc,bc)/18+dot(ca,ca)/6+dot(ab,ab)/3
    q2=18*determinant**2/(norm2*cofactor2) if norm2*cofactor2>0 else None
    return determinant,q2

def require_input_bindings(pins):
    if any(pins.get(path)!=digest for path,digest in INPUTS.items()):raise ValueError('Exact single saved-state input pins required')

def component_choice(manifest, component_ID):
    if (manifest.get('schema')!='962-current110-fixed73-component-cases/v1'
            or type(component_ID) is not int or not 1<=component_ID<=73
            or len(manifest.get('cases',[]))!=73):
        raise ValueError('One exact component ID from the frozen 73-case manifest required')
    case=manifest['cases'][component_ID-1]
    if (case['component_ID']!=component_ID or case['case_key']!='component-%04d'%component_ID
            or case['counts']['movable_nodes'] not in (1,2)
            or case['counts']['coordinate_variables']!=3*case['counts']['movable_nodes']
            or case['counts']['TET4']<1 or case['counts']['TET4']>77):
        raise ValueError('Frozen current component shape required')
    return case


def read_component(c,case):
    report=json.loads((ROOT/ROLES['census']).read_text())
    graph=json.loads((ROOT/ROLES['graph']).read_text())
    admission=json.loads((ROOT/ROLES['census_acceptance']).read_text())
    graph_admission=json.loads((ROOT/ROLES['graph_acceptance']).read_text())
    worker=json.loads((ROOT/ROLES['worker']).read_text())
    worker_admission=json.loads((ROOT/ROLES['worker_acceptance']).read_text())
    if (admission.get('decision')!='ACCEPT_CURRENT110_COMPLETE_READ_ONLY_CENSUS_AND_SAVED_ASSOCIATIONS_ONLY_WHOLE_HEAD_QUALITY_REJECTED'
            or admission.get('report')!=DESCRIPTORS['census'] or admission.get('whole_head_quality_accepted') is not False
            or graph_admission.get('decision')!='ACCEPT_LOCAL_QUALITY_COUPLING_GRAPH_SAVED_METADATA_ONLY_NO_REPAIR_FEASIBILITY'
            or graph_admission.get('graph')!=DESCRIPTORS['graph']
            or graph_admission.get('later_census_root_acceptance')!=DESCRIPTORS['census_acceptance']
            or worker_admission.get('decision')!='ACCEPT_COMPLETED_SAVED_PARTIAL_REPAIR_CAPTURE_ONLY_STRICT_WHOLE_HEAD_REJECTION_RETAINED'
            or worker_admission.get('report')!=DESCRIPTORS['worker']
            or worker_admission.get('whole_head_quality_accepted') is not False):
        raise ValueError('Current stopped census, graph and partial-head admissions required')
    if (report.get('status')!='direct_saved_file_readback_completed' or report.get('bound_inputs_unchanged') is not True
            or report.get('SICN_point1_gate_passed') is not False
            or report.get('single_partial_replacement_saved_proof',{}).get('report_sha256')!=INPUTS[ROLES['worker']]
            or worker.get('after')!=worker.get('saved_reopen')
            or worker.get('mesh_sha256')!=SOURCE_MSH_SHA or worker.get('mesh_bytes')!=235798094
            or worker.get('actual_whole_head_positive_poor_count')!=110
            or any(report.get(k)!=v for k,v in worker['after']['array_sha256s'].items())
            or report.get('direct_fresh_classifications')!=worker['after']['classifications']):
        raise ValueError('Exact current110 census-to-saved-parent identity required')
    s=report['complete_seed_star_census']
    if (s.get('schema')!='962-complete-current-poor-seed-stars/v1' or s.get('movable_count')!=82
            or s.get('prospective_coordinate_variables')!=246 or s.get('complete_incident_tetrahedron_count')!=2482
            or s.get('unique_incident_node_count')!=1439 or s.get('unique_incident_boundary_node_count')!=889
            or s.get('unique_incident_other_interior_node_count')!=468
            or s.get('initially_positive_poor_incident_tetrahedra')!=110
            or s.get('initially_good_incident_tetrahedra')!=2372 or s.get('shared_by_multiple_movable_nodes_tetrahedra')!=58
            or s.get('all_seed_stars_complete_including_initially_good_and_shared_cells') is not True
            or s.get('all_positive_poor_rows_covered_by_movable_stars') is not True
            or s.get('unseedable_positive_poor_tetrahedron_tags')!=[]):
        raise ValueError('Complete saved82-variable/2482-cell star union required')
    nodes=s['unique_incident_nodes'];rows=s['complete_incident_tetrahedra'];movable=s['movable_node_tags']
    if len(nodes)!=1439 or len(rows)!=2482 or len(movable)!=82:
        raise ValueError('Every current saved context and cell row required')
    tags=[r['node_tag'] for r in nodes];tet_tags=[r['tetrahedron_tag'] for r in rows]
    connectivity=[r['node_tags'] for r in rows]
    tagged_indices(tags,connectivity,movable)
    if tet_tags!=sorted(set(tet_tags)) or any(type(t) is not int or not 0<t<2**64 for t in tet_tags):
        raise ValueError('Complete sorted actual tetrahedron tags required')
    seeds=set(movable);coordinates=[];native=[]
    for r in nodes:
        xyz=r['coordinates_mm'];words=r['binary64_hex'];boundary=r['node_tag']<=871731
        if (len(xyz)!=3 or len(words)!=3
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz)
                or any(float(v).hex()!=h or struct.pack('<d',float.fromhex(h))!=struct.pack('<d',v) for v,h in zip(xyz,words))
                or r['in_movable_seed_set'] is not (r['node_tag'] in seeds)
                or r['source_boundary_tag'] is not boundary
                or r['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')
                or boundary and r['node_tag'] in seeds):
            raise ValueError('Exact saved coordinate words, source boundary and dim3 movable classification required')
        coordinates.extend(xyz)
    native_indices=[]
    for r in rows:
        q=r['initial_native_SICN'];members=sorted(seeds.intersection(r['node_tags']))
        if (not members or members!=r['movable_node_tags'] or type(q) not in (int,float)
                or not math.isfinite(q) or q<=0 or r['initially_positive_poor'] is not (q<.1)
                or type(r['native_array_index']) is not int or not 0<=r['native_array_index']<3622025):
            raise ValueError('All good/shared/poor ordered native cell associations required')
        native.append(q);native_indices.append(r['native_array_index'])
    if len(set(native_indices))!=2482:
        raise ValueError('Unique current full-parent native array positions required')
    sections={
        'movable_node_tags_u64':('Q',movable),
        'selected_tetrahedron_tags_u64':('Q',tet_tags),
        'selected_tetrahedron_connectivity_u64':('Q',[v for row in connectivity for v in row]),
        'union_node_tags_u64':('Q',tags),
        'union_coordinates_f64':('d',coordinates),
        'selected_initial_SICN_f64':('d',native)}
    observed={k:hashlib.sha256(struct.pack('<'+kind*len(values),*values)).hexdigest()
        for k,(kind,values) in sections.items()}
    if observed!=s['ordered_tagged_array_sha256s'] or observed!=c['census_typed_section_sha256s']:
        raise ValueError('All six complete selected typed census sections required')
    if (graph.get('input')!=DESCRIPTORS['census']
            or graph.get('all2482_source_incident_cell_records_preserved')!=rows
            or graph.get('all110_source_positive_poor_tetrahedron_tags')!=s['positive_poor_tetrahedron_tags']
            or len(graph.get('components',[]))!=73):
        raise ValueError('Accepted exact complete graph/census memberships required')
    selected=graph['components'][case['component_ID']-1]
    for k in ['component_ID','movable_node_tags','tetrahedron_tags','initially_positive_poor_tetrahedron_tags',
              'initially_good_tetrahedron_tags','shared_by_multiple_movable_nodes_tetrahedron_tags',
              'all_incident_node_tags','fixed_context_node_tags','fixed_source_boundary_node_tags',
              'fixed_other_interior_node_tags','counts']:
        if case[k]!=selected[k]:
            raise ValueError('Manifest differs from frozen graph component: '+k)
    node_lookup={r['node_tag']:r for r in nodes};cell_lookup={r['tetrahedron_tag']:r for r in rows}
    selected_nodes=[node_lookup[n] for n in case['all_incident_node_tags']]
    selected_cells=[cell_lookup[t] for t in case['tetrahedron_tags']]
    canonical=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if (hashlib.sha256(canonical(selected_nodes)).hexdigest()!=case['source_context_rows_sha256']
            or hashlib.sha256(canonical(selected_cells)).hexdigest()!=case['source_cell_rows_sha256']):
        raise ValueError('Exact complete current component row serialization required')
    points={r['node_tag']:r['coordinates_mm'] for r in selected_nodes}
    cells={r['tetrahedron_tag']:r['node_tags'] for r in selected_cells}
    if (set(v for row in cells.values() for v in row)!=set(points)
            or set(case['movable_node_tags'])!=seeds.intersection(points)
            or [r['tetrahedron_tag'] for r in selected_cells if r['initially_positive_poor']]!=case['initially_positive_poor_tetrahedron_tags']
            or not case['initially_positive_poor_tetrahedron_tags']):
        raise ValueError('Complete component stars without omitted good/shared cells or orphans required')
    return points,cells,{r['tetrahedron_tag']:r['initial_native_SICN'] for r in selected_cells}

def topology_diagnostic(cells,frozen_boundary):
    def canonical(face):
        face=tuple(face);i=face.index(min(face));return face[i:]+face[:i]
    incidence={}
    for row in cells.values():
        for corners in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:
            face=tuple(row[i] for i in corners);incidence.setdefault(tuple(sorted(face)),[]).append(face)
    exterior=[rows[0] for rows in incidence.values() if len(rows)==1]
    boundary=sorted(canonical(face) for face in exterior)
    return dict(boundary_faces=len(exterior),oriented_boundary_faces=[list(face) for face in boundary],
        internal_face_pairs=sum(len(rows)==2 for rows in incidence.values()),
        nonmanifold_faces=sum(len(rows)>2 for rows in incidence.values()),
        same_oriented_internal_faces=sum(len(rows)==2 and canonical(rows[0])!=canonical(rows[1][::-1]) for rows in incidence.values()),
        frozen_boundary_supplied=frozen_boundary is not None,
        exact_frozen_oriented_boundary=None if frozen_boundary is None else boundary==sorted(canonical(face) for face in frozen_boundary),
        unchanged_ordered_component_connectivity=True,geometric_overlap_or_intersection_checked=False)


def fixed_bits(original,final):
    if set(final)!=set(original):raise ValueError('Complete original node-tag set required')
    return all(struct.pack('<3d',*original[t])==struct.pack('<3d',*final[t]) for t in original if t not in FREE)


def exact_rows(points,cells):
    rows=[];volume=Fraction(0)
    for tag,row in sorted(cells.items()):
        det,q2=exact_quality([points[t] for t in row]);volume+=det/6
        passed=det>0 and q2 is not None and q2>=Fraction(1,100)
        rows.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,
            exact_native_ordered_determinant_mm3=rational(det),
            exact_SICN_squared=None if q2 is None else rational(q2),
            signed_SICN_approximate=None if q2 is None else (1 if det>0 else -1 if det<0 else 0)*math.sqrt(float(q2)),
            positive_orientation=det>0,exact_point1_gate_passed=passed))
    return rows,volume


def result_status(solver_success,exact_quality_gate,procedural_checks):
    if not procedural_checks:return 'rejected_procedural_diagnostic_retained'
    if not exact_quality_gate:return 'rejected_exact_quality_diagnostic_retained'
    return 'exact_feasible_point_solver_converged_native_unapproved' if solver_success else 'feasible_point_solver_not_converged'


def bound_contract(path):
    c=json.loads(path.read_text())
    if (c.get('schema')!='962-current110-one-component-exact-sicn/v1'
            or c.get('scope')!='one_frozen_current110_component_analytic_SLSQP_only'
            or c.get('proposal_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
            or c.get('selected_runtime_review_complete') is not True or c.get('qualification')!=QUALIFICATION
            or c.get('limits')!=LIMITS or c.get('solver')!=SOLVER or c.get('sicn_gate')!=GATE
            or c.get('automatic_retry') is not False or c.get('native_mesh_application_authorized') is not False):
        raise ValueError('Separately reviewed one-call current110 component child required')
    if sys.version_info[:3]!=(3,12,11):
        raise ValueError('Registered Python3.12.11 required')
    for mapping in (c['input_hashes'],c['runtime_files']):
        if not mapping:raise ValueError('Nonempty exact input/selected-runtime maps required')
        for name,digest in mapping.items():
            p=Path(name)
            if not re.fullmatch('[0-9a-f]{64}',digest) or not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=digest:
                raise ValueError('Frozen input or selected runtime changed')
    require_input_bindings({str(Path(k).relative_to(ROOT)):v for k,v in c['input_hashes'].items() if Path(k).is_relative_to(ROOT)})
    runtime_record=json.loads((ROOT/ROLES['runtime_donor']).read_text())
    for key in ['native_python','numpy_init','scipy_directory','runtime','runtime_files']:
        if c.get(key)!=runtime_record[key]:
            raise ValueError('Exact inherited finite selected runtime required: '+key)
    if c['reader_sha256']!=sha(__file__) or c['runner_sha256']!=sha(path.with_name('run_readback.py')):
        raise ValueError('Exact materialized worker/controller required')
    if c['runtime_files'].get(str(Path(sys.executable).resolve()))!=sha(Path(sys.executable).resolve()):
        raise ValueError('Exact selected interpreter required')
    manifest=json.loads((ROOT/MANIFEST).read_text());case=component_choice(manifest,c.get('component_ID'))
    case_bytes=json.dumps(case,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if (c.get('case_key')!=case['case_key'] or c.get('case_record_sha256')!=hashlib.sha256(case_bytes).hexdigest()
            or c.get('component_manifest_sha256')!=INPUTS[MANIFEST] or c.get('free_tags')!=case['movable_node_tags']
            or Path(c['output'])!=path.parent or path.parent!=ROOT/case['output_directory']):
        raise ValueError('One exact fixed component record/output required')
    return c,case


def main():
    global FREE
    started=time.monotonic();out=Path(__file__).resolve().parent
    report=dict(status='refused',stage='contract',minimize_calls_attempted=0,qualification=QUALIFICATION)
    try:
        if set(p.name for p in out.iterdir())!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
            raise ValueError('Only fresh materialized sources/contract/controller log may exist')
        c,case=bound_contract(out/'frozen-contract.json');FREE=case['movable_node_tags']
        report.update(contract_sha256=sha(out/'frozen-contract.json'),case_key=case['case_key'],
            component_ID=case['component_ID'],case_record_sha256=c['case_record_sha256'],
            component_manifest_sha256=INPUTS[MANIFEST],source_census_sha256=INPUTS[ROLES['census']],
            source_graph_sha256=INPUTS[ROLES['graph']],source_mesh_sha256=SOURCE_MSH_SHA,
            stage='source_state',component_counts=case['counts'])
        points,cells,native=read_component(c,case)
        node_tags=sorted(points);tet_tags=sorted(cells);connectivity=[cells[t] for t in tet_tags]
        indices,positions=tagged_indices(node_tags,connectivity,FREE)
        topology_before=topology_diagnostic(cells,None)
        boundary=topology_before['oriented_boundary_faces']
        boundary_fixed=all(t not in FREE for face in boundary for t in face)
        before_rows,before_volume=exact_rows(points,cells)
        report.update(before_topology=topology_before,
            all_component_boundary_vertices_fixed=boundary_fixed,
            exact_before_signed_volume_mm3=rational(before_volume),
            all_before_signed_quality_rows=before_rows)
        if (not boundary or not boundary_fixed or topology_before['nonmanifold_faces']!=0
                or topology_before['same_oriented_internal_faces']!=0
                or before_volume<=0 or not all(r['positive_orientation'] for r in before_rows)):
            raise ValueError('Complete positively oriented component with fixed closed oriented boundary required')
        original_connectivity=json.dumps(connectivity,separators=(',',':')).encode()
        report['stage']='imports';np,optimize=scientific_modules(c)
        original=np.asarray([points[t] for t in node_tags],dtype=np.float64);original.setflags(write=False)
        original_hash=hashlib.sha256(original.tobytes()).hexdigest();cell_indices=np.asarray(indices,dtype=np.int64)
        report['stage']='calibration';before=signed_sicn_vector(np,original[cell_indices])
        if len(before)!=len(cells) or any(not math.isclose(float(q),native[t],rel_tol=1e-11,abs_tol=1e-14) for t,q in zip(tet_tags,before)):
            raise ValueError('All current component analytic/native rows must match inherited combined tolerance')
        initial_min=float(np.min(before))
        report['calibration']=dict(count=len(cells),relative_tolerance=1e-11,absolute_tolerance=1e-14,
            maximum_absolute_error=max(abs(float(q)-native[t]) for t,q in zip(tet_tags,before)),
            initial_minimum=initial_min,all_saved_native_rows_match=True)
        x0=np.r_[original[positions].reshape(-1),initial_min]
        def quality(x):return signed_sicn_vector(np,assemble_points(np,original,positions,x)[cell_indices])
        report['loaded_scientific_files_before_call']=loaded_files(c)
        report['stage']='one_SLSQP';report['minimize_calls_attempted']=1
        save(out/'solver-start-checkpoint.json',report)
        result=optimize.minimize(lambda x:-x[-1],x0,method=SOLVER['method'],
            bounds=[(None,None)]*(3*len(FREE))+[(initial_min,1.)],
            constraints=[{'type':'ineq','fun':lambda x:quality(x)-x[-1]}],
            options={k:SOLVER[k] for k in ('maxiter','ftol','eps')})
        returned=np.asarray(result.x,dtype=np.float64)
        if returned.shape!=(3*len(FREE)+1,) or not np.all(np.isfinite(returned)):
            raise ValueError('Complete finite returned component coordinates plus epigraph required')
        report['complete_returned_vector']=[float(v) for v in returned]
        report['solver']=dict(method='SLSQP',calls=1,success=bool(result.success),status=int(result.status),
            nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),message=str(result.message))
        final=assemble_points(np,original,positions,returned)
        after={t:[float(v) for v in row] for t,row in zip(node_tags,final)}
        rows,volume=exact_rows(after,cells)
        exact_pass=all(row['exact_point1_gate_passed'] for row in rows)
        unchanged=fixed_bits(points,after)
        source_boundary_exact=all(struct.pack('<3d',*points[t])==struct.pack('<3d',*after[t]) for t in points if t<=871731)
        topology=topology_diagnostic(cells,boundary)
        connectivity_unchanged=json.dumps([cells[t] for t in tet_tags],separators=(',',':')).encode()==original_connectivity
        original_unchanged=hashlib.sha256(original.tobytes()).hexdigest()==original_hash
        procedural=(unchanged and source_boundary_exact and original_unchanged and connectivity_unchanged
            and boundary_fixed and topology['exact_frozen_oriented_boundary'] is True
            and topology['nonmanifold_faces']==0 and topology['same_oriented_internal_faces']==0
            and volume==before_volume)
        status=result_status(bool(result.success),exact_pass,procedural)
        report['stage']='retained_finite_diagnostic'
        diagnostic=dict(schema='962-current110-one-component-SLSQP-exact-diagnostic/v1',status=status,
            contract_sha256=report['contract_sha256'],input_hashes=c['input_hashes'],solver=report['solver'],
            component_ID=case['component_ID'],case_key=case['case_key'],
            case_record_sha256=c['case_record_sha256'],component_manifest_sha256=INPUTS[MANIFEST],
            source_census_sha256=INPUTS[ROLES['census']],source_graph_sha256=INPUTS[ROLES['graph']],
            source_mesh_sha256=SOURCE_MSH_SHA,
            complete_returned_vector=report['complete_returned_vector'],free_tags=FREE,
            coordinate_variables=3*len(FREE),variables_with_epigraph=3*len(FREE)+1,
            full_source_nodes=len(points),full_cells=len(cells),
            all_component_exact_quality_gate=exact_pass,solver_success_independent_of_exact_quality=True,
            complete_proposed_coordinate_rows=[dict(node_tag=t,coordinates_mm=after[t],binary64_hex=[float(v).hex() for v in after[t]]) for t in node_tags],
            all_component_signed_quality_rows=rows,
            positive_poor_cell_tags=[row['tetrahedron_tag'] for row in rows if row['positive_orientation'] and not row['exact_point1_gate_passed']],
            nonpositive_or_undefined_cell_tags=[row['tetrahedron_tag'] for row in rows if not row['positive_orientation'] or row['exact_SICN_squared'] is None],
            all_fixed_context_coordinate_bits_unchanged=unchanged,source_boundary_context_bits_unchanged=source_boundary_exact,
            all_component_boundary_vertices_fixed=boundary_fixed,original_array_bits_unchanged=original_unchanged,
            original_ordered_connectivity_unchanged=connectivity_unchanged,topology_diagnostic=topology,
            exact_before_signed_volume_mm3=rational(before_volume),exact_final_signed_volume_mm3=rational(volume),
            exact_signed_volume_equals_same_component_before=volume==before_volume,
            donor39_cell_shell_volume_reused=False,procedural_checks_passed=procedural,
            epigraph_t=float(returned[-1]),initial_epigraph_lower_bound=initial_min,
            epigraph_bound_satisfied=initial_min<=float(returned[-1])<=1.,
            quality_scope='Exact Fraction determinant/Q-squared over every returned binary64 component cell; displayed signed roots are approximate, not native or interval values.',
            fixed_local_boundary_is_distinct_from_original_global_source_boundary=True,
            embedding_overlap_or_containment_checked=False,native_application_or_MSH_write=False,
            no_pressure_thermal_stud_load_or_material_case=True,qualification=QUALIFICATION)
        save(out/'diagnostic.json',diagnostic);report['diagnostic_sha256']=sha(out/'diagnostic.json')
        report['loaded_scientific_files_after_return']=loaded_files(c)
        report['bound_inputs_unchanged']=all(sha(p)==h for m in (c['input_hashes'],c['runtime_files']) for p,h in m.items())
        if not report['bound_inputs_unchanged']:
            raise ValueError('Input/runtime changed during single call; finite diagnostic remains unapproved')
        report.update(status=status,all_component_exact_quality_gate=exact_pass,procedural_checks_passed=procedural,
            native_application_or_MSH_write=False,wall_seconds=time.monotonic()-started)
        save(out/'fixture-report.json',report)
        return 0 if procedural and exact_pass and result.success else 2
    except Exception as error:
        report['error']=str(error);save(out/'fixture-report.json',report);return 2


if __name__=='__main__':raise SystemExit(main())
