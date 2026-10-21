"""HELD one coupled cavity SLSQP diagnostic; no native mesh apply or MSH write."""
from fractions import Fraction
import hashlib,importlib,importlib.util,json,math,re,struct,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
# A materialized worker is three levels below the same engineering worktree root.
OUTPUT_NAME='fixed-shell-coupled-sicn-001'
LIMITS=dict(wall_seconds=30,sampled_RSS_bytes=1024**3,sampled_output_bytes=16*1024**2,threads=2)
SOLVER=dict(method='SLSQP',maxiter=100,ftol=1e-10,eps=2.0**-26)
GATE=.1
FREE=[27,28,29]
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
INPUTS={ARRAYS:'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f',
 WORKER:'8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7',
 SHELL:'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}
TARGETS={198:[29,4,5,6],204:[28,7,9,8]}
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)

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

def typed_state(a):
    return (struct.pack('<'+'Q'*len(a['node_tags']),*a['node_tags']),
        struct.pack('<'+'d'*(3*len(a['coordinates_mm'])),*[v for row in a['coordinates_mm'] for v in row]),
        struct.pack('<'+'Q'*len(a['tetra_tags']),*a['tetra_tags']),
        struct.pack('<'+'Q'*(4*len(a['tetra_node_tags'])),*[v for row in a['tetra_node_tags'] for v in row]),
        *[struct.pack('<'+'d'*len(a['native_qualities'][name]),*a['native_qualities'][name]) for name in ['SICN','Jacobian','native_volume_mm3']],
        struct.pack('<'+'d'*len(a['independent_signed_volume_mm3']),*a['independent_signed_volume_mm3']))

def before_state(worker,arrays,shell):
    a=arrays['saved_reopen'];r=worker['saved_reopen']
    if (worker.get('status')!='completed_specific_cavity_Netgen_only' or worker.get('fixture_procedural_checks_passed') is not True
        or worker.get('actual_SICN_gate_passed') is not False or worker.get('saved_mesh_identity_exact') is not True
        or worker.get('bound_inputs_unchanged') is not True or worker.get('full_tiny_arrays_sha256')!=INPUTS[ARRAYS]
        or (r['nodes'],r['tetrahedra'],r['referenced_interior_nodes'],r['unreferenced_nodes'])!=(19,39,3,0)
        or a['node_tags']!=list(range(1,17))+[27,28,29] or len(a['coordinates_mm'])!=19
        or len(a['tetra_tags'])!=39 or a['tetra_tags']!=sorted(set(a['tetra_tags']))
        or len(a['tetra_node_tags'])!=39 or any(len(t)!=4 or len(set(t))!=4 or not set(t)<=set(a['node_tags']) for t in a['tetra_node_tags'])
        or any(len(a['native_qualities'][name])!=39 for name in ['SICN','Jacobian','native_volume_mm3'])
        or len(a['independent_signed_volume_mm3'])!=39 or typed_state(a)!=typed_state(arrays['after'])):
        raise ValueError('Exact complete current19node/39cell saved-after state required')
    state=typed_state(a)
    for key,value in zip(['sorted_node_tags_sha256','sorted_coordinates_sha256','tetra_tags_sha256','tagged_tetra_connectivity_sha256'],state[:4]):
        if hashlib.sha256(value).hexdigest()!=r[key]:raise ValueError('Fresh typed arrays differ from native saved report')
    if worker['after']!=r:raise ValueError('Full saved/after reports differ')
    points=dict(zip(a['node_tags'],a['coordinates_mm']));cells=dict(zip(a['tetra_tags'],a['tetra_node_tags']))
    if set(v for row in cells.values() for v in row)!=set(points):raise ValueError('Unreferenced nodes prohibited')
    if any(cells.get(tag)!=row for tag,row in TARGETS.items()):raise ValueError('Exact two poor-cell ordered tags required')
    if sorted(t for t,q in zip(a['tetra_tags'],a['native_qualities']['SICN']) if q<.1)!=[198,204]:raise ValueError('Exactly the two current native poor cells required')
    if any(not math.isfinite(v) for row in points.values() for v in row):raise ValueError('Finite source coordinates required')
    for row in shell['vertex_rows']:
        if struct.pack('<3d',*points[row['local_node_tag']]).hex()!=row['binary64_little_endian_bytes_hex']:raise ValueError('All16 frozen shell bits required')
    return points,cells,a

def topology_diagnostic(cells,shell):
    def canonical(face):
        face=tuple(face);i=face.index(min(face));return face[i:]+face[:i]
    incidence={}
    for row in cells.values():
        for corners in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:
            face=tuple(row[i] for i in corners);incidence.setdefault(tuple(sorted(face)),[]).append(face)
    exterior=[rows[0] for rows in incidence.values() if len(rows)==1]
    return dict(boundary_faces=len(exterior),internal_face_pairs=sum(len(rows)==2 for rows in incidence.values()),
        nonmanifold_faces=sum(len(rows)>2 for rows in incidence.values()),
        same_oriented_internal_faces=sum(len(rows)==2 and canonical(rows[0])!=canonical(rows[1][::-1]) for rows in incidence.values()),
        exact28_oriented_shell_faces=sorted(canonical(face) for face in exterior)==sorted(canonical(row['local_node_tags']) for row in shell['oriented_triangle_rows']),
        unchanged_all39_ordered_connectivity=True,geometric_overlap_or_intersection_checked=False)


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
    if (c.get('schema')!='962-fixed-shell-coupled-sicn/v1' or c.get('scope')!='specific_current_cavity_analytic_SLSQP_only'
        or c.get('proposal_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
        or c.get('selected_runtime_review_complete') is not True or c.get('qualification')!=QUALIFICATION
        or c.get('limits')!=LIMITS or c.get('solver')!=SOLVER or c.get('sicn_gate')!=GATE
        or c.get('free_tags')!=FREE or c.get('automatic_retry') is not False):
        raise ValueError('Separately reviewed one-call analytic cavity child required')
    if sys.version_info[:3]!=(3,12,11):raise ValueError('Registered Python3.12.11 required')
    for mapping in (c['input_hashes'],c['runtime_files']):
        if not mapping:raise ValueError('Nonempty exact input/selected-runtime maps required')
        for name,digest in mapping.items():
            p=Path(name)
            if not re.fullmatch('[0-9a-f]{64}',digest) or not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=digest:
                raise ValueError('Frozen input or selected runtime changed')
    require_input_bindings({str(Path(k).relative_to(ROOT)):v for k,v in c['input_hashes'].items() if Path(k).is_relative_to(ROOT)})
    if c['reader_sha256']!=sha(__file__) or c['runner_sha256']!=sha(path.with_name('run_readback.py')):
        raise ValueError('Exact materialized worker/controller required')
    if c['runtime_files'].get(str(Path(sys.executable).resolve()))!=sha(Path(sys.executable).resolve()):
        raise ValueError('Exact selected interpreter required')
    if Path(c['output'])!=path.parent or path.parent.name!=OUTPUT_NAME:raise ValueError('Exact separately materialized output required')
    return c


def main():
    started=time.monotonic();out=Path(__file__).resolve().parent
    report=dict(status='refused',stage='contract',minimize_calls_attempted=0,qualification=QUALIFICATION)
    try:
        if set(p.name for p in out.iterdir())!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
            raise ValueError('Only fresh materialized sources/contract/controller log may exist')
        c=bound_contract(out/'frozen-contract.json');report['contract_sha256']=sha(out/'frozen-contract.json')
        report['stage']='source_state'
        worker=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());shell=json.loads((ROOT/SHELL).read_text())
        points,cells,a=before_state(worker,arrays,shell)
        node_tags=sorted(points);tet_tags=sorted(cells);connectivity=[cells[t] for t in tet_tags]
        indices,positions=tagged_indices(node_tags,connectivity,FREE)
        report['stage']='imports';np,optimize=scientific_modules(c)
        original=np.asarray([points[t] for t in node_tags],dtype=np.float64);original.setflags(write=False)
        original_hash=hashlib.sha256(original.tobytes()).hexdigest();cell_indices=np.asarray(indices,dtype=np.int64)
        report['stage']='calibration';before=signed_sicn_vector(np,original[cell_indices])
        native=dict(zip(a['tetra_tags'],a['native_qualities']['SICN']))
        if len(before)!=39 or any(not math.isclose(float(q),native[t],rel_tol=1e-11,abs_tol=1e-14) for t,q in zip(tet_tags,before)):
            raise ValueError('All39 original analytic/native rows must match inherited combined tolerance')
        initial_min=float(np.min(before))
        report['calibration']=dict(count=39,relative_tolerance=1e-11,absolute_tolerance=1e-14,
            maximum_absolute_error=max(abs(float(q)-native[t]) for t,q in zip(tet_tags,before)),
            initial_minimum=initial_min,all_saved_native_rows_match=True)
        x0=np.r_[original[positions].reshape(-1),initial_min]
        def quality(x):return signed_sicn_vector(np,assemble_points(np,original,positions,x)[cell_indices])
        report['loaded_scientific_files_before_call']=loaded_files(c)
        report['stage']='one_SLSQP';report['minimize_calls_attempted']=1
        save(out/'solver-start-checkpoint.json',report)
        result=optimize.minimize(lambda x:-x[-1],x0,method=SOLVER['method'],
            bounds=[(None,None)]*9+[(initial_min,1.)],
            constraints=[{'type':'ineq','fun':lambda x:quality(x)-x[-1]}],
            options={k:SOLVER[k] for k in ('maxiter','ftol','eps')})
        # Preserve a returned finite vector and its exact coordinate diagnostic before considering success.
        returned=np.asarray(result.x,dtype=np.float64)
        if returned.shape!=(10,) or not np.all(np.isfinite(returned)):raise ValueError('Finite returned10-vector required')
        report['complete_returned_vector']=[float(v) for v in returned]
        report['solver']=dict(method='SLSQP',calls=1,success=bool(result.success),status=int(result.status),
            nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),message=str(result.message))
        final=assemble_points(np,original,positions,returned)
        after={t:[float(v) for v in row] for t,row in zip(node_tags,final)}
        rows,volume=exact_rows(after,cells)
        exact_pass=all(row['exact_point1_gate_passed'] for row in rows)
        unchanged=fixed_bits(points,after)
        topology=topology_diagnostic(cells,shell)
        reference=Fraction(shell['exact_enclosed_volume_mm3']['numerator'],shell['exact_enclosed_volume_mm3']['denominator'])
        before_volume=sum((exact_quality([points[t] for t in row])[0]/6 for row in cells.values()),Fraction(0))
        original_unchanged=hashlib.sha256(original.tobytes()).hexdigest()==original_hash
        procedural=(unchanged and original_unchanged and topology['exact28_oriented_shell_faces']
            and topology['nonmanifold_faces']==0 and topology['same_oriented_internal_faces']==0
            and before_volume==reference and volume==reference)
        status=result_status(bool(result.success),exact_pass,procedural)
        report['stage']='retained_finite_diagnostic'
        diagnostic=dict(schema='962-specific-cavity-coupled-SLSQP-diagnostic/v1',status=status,
            contract_sha256=report['contract_sha256'],input_hashes=c['input_hashes'],solver=report['solver'],
            complete_returned_vector=report['complete_returned_vector'],free_tags=FREE,
            coordinate_variables=9,variables_with_epigraph=10,full_source_nodes=19,full_cells=39,
            all39_exact_quality_gate=exact_pass,solver_success_independent_of_exact_quality=True,
            complete_proposed_coordinate_rows=[dict(node_tag=t,coordinates_mm=after[t],binary64_hex=[float(v).hex() for v in after[t]]) for t in node_tags],
            all39_signed_quality_rows=rows,
            positive_poor_cell_tags=[row['tetrahedron_tag'] for row in rows if row['positive_orientation'] and not row['exact_point1_gate_passed']],
            nonpositive_or_undefined_cell_tags=[row['tetrahedron_tag'] for row in rows if not row['positive_orientation'] or row['exact_SICN_squared'] is None],
            all16_shell_coordinate_bits_unchanged=unchanged,original_array_bits_unchanged=original_unchanged,
            topology_diagnostic=topology,exact_before_signed_volume_mm3=rational(before_volume),exact_final_signed_volume_mm3=rational(volume),
            exact_signed_volume_equals_original_shell=volume==reference,procedural_checks_passed=procedural,
            epigraph_t=float(returned[-1]),initial_epigraph_lower_bound=initial_min,
            epigraph_bound_satisfied=initial_min<=float(returned[-1])<=1.,
            quality_scope='Exact Fraction determinant/Q-squared over all39 returned binary64 cells; displayed signed roots are approximate, not native or interval values.',
            fixed_shell_coordinate_policy_not_global_head_boundary=True,
            embedding_overlap_or_containment_checked=False,native_application_or_MSH_write=False,qualification=QUALIFICATION)
        save(out/'diagnostic.json',diagnostic);report['diagnostic_sha256']=sha(out/'diagnostic.json')
        report['loaded_scientific_files_after_return']=loaded_files(c)
        report['bound_inputs_unchanged']=all(sha(p)==h for m in (c['input_hashes'],c['runtime_files']) for p,h in m.items())
        if not report['bound_inputs_unchanged']:raise ValueError('Input/runtime changed during single call')
        report.update(status=status,all39_exact_quality_gate=exact_pass,procedural_checks_passed=procedural,
            native_application_or_MSH_write=False,wall_seconds=time.monotonic()-started)
        save(out/'fixture-report.json',report)
        return 0 if procedural and exact_pass and result.success else 2
    except Exception as error:
        report['error']=str(error);save(out/'fixture-report.json',report);return 2


if __name__=='__main__':raise SystemExit(main())
