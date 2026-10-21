"""HELD sparse-FD trust-constr tiny analytic witness; no Gmsh or head application."""
import hashlib,importlib,importlib.util,json,math,re,struct,sys,warnings
from pathlib import Path
OUTPUT_NAME='direct-sicn-sparse-cube-001'
LIMITS=dict(wall_seconds=30,sampled_RSS_bytes=1024**3,sampled_output_bytes=16*1024**2,threads=2)
SOLVER=dict(method='trust-constr',maxiter=100,gtol=1e-8,xtol=1e-10,barrier_tol=1e-10,
            finite_diff_rel_step=2.0**-26,sparse_jacobian=True,factorization_method='AugmentedSystem')
GATE=.1
ADDITIONAL_RUNTIME_SUFFIXES=('scipy/optimize/_hessian_update_strategy.py', 'scipy/optimize/_trustregion_constr/__init__.py', 'scipy/optimize/_trustregion_constr/canonical_constraint.py', 'scipy/optimize/_trustregion_constr/equality_constrained_sqp.py', 'scipy/optimize/_trustregion_constr/minimize_trustregion_constr.py', 'scipy/optimize/_trustregion_constr/projections.py', 'scipy/optimize/_trustregion_constr/qp_subproblem.py', 'scipy/optimize/_trustregion_constr/report.py', 'scipy/optimize/_trustregion_constr/tr_interior_point.py', 'scipy/sparse/__init__.py', 'scipy/sparse/_base.py', 'scipy/sparse/_compressed.py', 'scipy/sparse/_construct.py', 'scipy/sparse/_coo.py', 'scipy/sparse/_csc.py', 'scipy/sparse/_csr.py', 'scipy/sparse/_sparsetools.cpython-312-darwin.so', 'scipy/sparse/_sputils.py', 'scipy/sparse/linalg/__init__.py', 'scipy/sparse/linalg/_dsolve/__init__.py', 'scipy/sparse/linalg/_dsolve/_superlu.cpython-312-darwin.so', 'scipy/sparse/linalg/_dsolve/linsolve.py')
QUALIFICATION=dict(head_optimization_authorized=False,engineering_accepted=False,
                   physics_qualified=False,manufacturing_authorized=False)

NODE_TAGS = tuple(range(101, 109)) + (201,)
TET_TAGS = tuple(range(2001, 2013))
TRI_TAGS = tuple(range(1001, 1013))
BOUNDARY = ((-1.,-1.,-1.),(1.,-1.,-1.),(1.,1.,-1.),(-1.,1.,-1.),
            (-1.,-1.,1.),(1.,-1.,1.),(1.,1.,1.),(-1.,1.,1.))
TRIANGLES = ((101,103,102),(101,104,103),(105,106,107),(105,107,108),
             (101,102,106),(101,106,105),(104,108,107),(104,107,103),
             (101,105,108),(101,108,104),(102,103,107),(102,107,106))
TETS = tuple((201,)+f for f in TRIANGLES)
INITIAL = (63./64., 1./4., -1./8.)
CENTRE = (0., 0., 0.)


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
    return q


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


def jacobian_entries(node_tags,cells,movable_tags):
    """Exact structural corner-coordinate support plus the common epigraph column."""
    indices,positions=tagged_indices(node_tags,cells,movable_tags)
    variable={p:i for i,p in enumerate(positions)};rows=[];columns=[];t=3*len(positions)
    for i,cell in enumerate(indices):
        support={t}
        for p in cell:
            if p in variable:support.update(range(3*variable[p],3*variable[p]+3))
        for j in sorted(support):rows.append(i);columns.append(j)
    return rows,columns,(len(cells),t+1)


def objective(x):return -float(x[-1])


def objective_gradient(x):
    if len(x)!=4:raise ValueError('Exactly three coordinates and one epigraph variable required')
    return [0.,0.,0.,-1.]


def zero_objective_hessian(sparse,x):
    if len(x)!=4:raise ValueError('Exactly four tiny variables required')
    return sparse.csr_matrix((4,4),dtype=float)


def final_quality_gate(success,vector,values):
    if (success is not True or len(vector)!=4 or len(values)!=12
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in [*vector,*values])
            or any(v<GATE for v in values)):
        raise ValueError('Finite successful returned result and ALL12 analytic SICN >=0.1 required')


def bound_contract(path):
    c=json.loads(path.read_text())
    if (c.get('schema')!='962-sparse-FD-trust-constr-tiny/v1' or c.get('scope')!='tiny_analytic_software_witness_only'
            or c.get('execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
            or c.get('selected_runtime_review_complete') is not True or c.get('qualification')!=QUALIFICATION
            or c.get('limits')!=LIMITS or c.get('solver')!=SOLVER or c.get('sicn_gate')!=GATE):
        raise ValueError('Separately reviewed fixed tiny actual child required')
    for mapping in (c['input_hashes'],c['runtime_files']):
        if not mapping:raise ValueError('Nonempty exact source/runtime maps required')
        for name,digest in mapping.items():
            p=Path(name)
            if not re.fullmatch('[0-9a-f]{64}',digest) or not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=digest:
                raise ValueError('Source/selected runtime identity changed')
    expected_extra={str(Path(c['scipy_directory']).parent/name) for name in ADDITIONAL_RUNTIME_SUFFIXES}
    if (set(c['additional_runtime_files'])!=expected_extra
            or any(c['runtime_files'].get(name)!=digest for name,digest in c['additional_runtime_files'].items())):
        raise ValueError('All22 sparse/trust runtime candidates require exact selected current pins')
    if (c['reader_sha256']!=sha(__file__) or c['runner_sha256']!=sha(path.with_name('run_readback.py'))
            or c['runtime_files'].get(str(Path(sys.executable).resolve()))!=sha(Path(sys.executable).resolve())
            or Path(c['output'])!=path.parent or path.parent.name!=OUTPUT_NAME
            or c['tiny_native_report_sha256']!='0512708595378fe0d316de08305c35f98138b082a2deb83bdb60717783cd8058'
            or c['input_hashes'].get(c['tiny_native_report'])!=c['tiny_native_report_sha256']):
        raise ValueError('Exact materialized source/interpreter/output/native reference required')
    return c


def tiny_reference(c,np):
    report=json.loads(Path(c['tiny_native_report']).read_text())
    if sha(c['tiny_native_report'])!=c['tiny_native_report_sha256'] or report['status']!='completed_tiny_software_witness':
        raise ValueError('Exact completed tiny native reference required')
    expected=dict(node_tags=list(NODE_TAGS),tet_tags=list(TET_TAGS),connectivity=[list(r) for r in TETS],
                  triangle_tags=list(TRI_TAGS),triangles=[list(r) for r in TRIANGLES])
    for name in ['before','centre_reference']:
        row=report[name]
        if any(row[k]!=v for k,v in expected.items()) or row['coordinates_mm']!=[list(r) for r in BOUNDARY+(INITIAL if name=='before' else CENTRE,)]:
            raise ValueError('Exact native literal ordered topology/coordinate association required')
        if (np.asarray(row['coordinates_mm'],dtype='<f8').tobytes()!=np.asarray(BOUNDARY+(INITIAL if name=='before' else CENTRE,),dtype='<f8').tobytes()
                or len(row['qualities']['minSICN'])!=12):
            raise ValueError('Exact binary64 literal coordinates and complete12 native rows required')
    return report


def main():
    out=Path(__file__).resolve().parent;report=dict(status='refused',stage='contract',minimize_calls_attempted=0,
        qualification=QUALIFICATION,no_Gmsh_import_or_native_mesh_apply=True,constraint_Hessian='explicit BFGS: dense4x4; not an all-sparse solver',
        objective_gradient='exact [0,0,0,-1]',objective_Hessian='exact zero4x4 CSR',warning_capture_scope='Python warnings only; no instrumented backend factorization count')
    try:
        if set(p.name for p in out.iterdir())!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
            raise ValueError('Only three fresh materialized inputs and owned controller log permitted')
        c=bound_contract(out/'frozen-contract.json');report['contract_sha256']=sha(out/'frozen-contract.json')
        report['stage']='imports';print('selected scientific imports: begin',flush=True)
        np,optimize=scientific_modules(c);sparse=importlib.import_module('scipy.sparse');report['loaded_scientific_files_before']=loaded_files(c)
        reference=tiny_reference(c,np);original=np.asarray(BOUNDARY+(INITIAL,),dtype=np.float64);original.setflags(write=False)
        indices,positions=tagged_indices(list(NODE_TAGS),[list(r) for r in TETS],[201]);cell_indices=np.asarray(indices,dtype=np.int64)
        before=signed_sicn_vector(np,original[cell_indices]);centre=np.asarray(BOUNDARY+(CENTRE,),dtype=np.float64)
        centre_quality=signed_sicn_vector(np,centre[cell_indices])
        for values,name in [(before,'before'),(centre_quality,'centre_reference')]:
            if any(not math.isclose(float(a),b,rel_tol=1e-11,abs_tol=1e-14) for a,b in zip(values,reference[name]['qualities']['minSICN'])):
                raise ValueError('Complete tiny analytic/native calibration failed')
        initial_min=float(np.min(before))
        if not 0<initial_min<GATE or float(np.min(centre_quality))<GATE:raise ValueError('Poor initial / known feasible centre required')
        rows,cols,shape=jacobian_entries(list(NODE_TAGS),[list(r) for r in TETS],[201])
        pattern=sparse.coo_matrix((np.ones(len(rows),dtype=bool),(rows,cols)),shape=shape).tocsr()
        report.update(calibration=dict(count=12,relative_tolerance=1e-11,absolute_tolerance=1e-14,
            all_before_and_centre_native_rows_match=True),initial_analytic_quality=before.tolist(),
            sparsity=dict(shape=list(shape),row_indices=rows,column_indices=cols,nnz=int(pattern.nnz),
                tiny_pattern_is_full12x4=True,head_sparse_benefit_established=False))
        x0=np.r_[original[positions].reshape(-1),initial_min]
        quality=lambda x:signed_sicn_vector(np,assemble_points(np,original,positions,x)[cell_indices])
        constraint=optimize.NonlinearConstraint(lambda x:quality(x)-x[-1],0.,np.inf,jac='2-point',hess=optimize.BFGS(),
            finite_diff_rel_step=SOLVER['finite_diff_rel_step'],finite_diff_jac_sparsity=pattern)
        report.update(stage='one_trust_constr',minimize_calls_attempted=1);print('one trust-constr call:4variables/12constraints',flush=True)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('always')  # Standard stderr stays owned/logged even if killed.
                result=optimize.minimize(objective,x0,method='trust-constr',jac=objective_gradient,
                    hess=lambda x:zero_objective_hessian(sparse,x),bounds=[(None,None)]*3+[(initial_min,1.)],constraints=[constraint],
                    options={k:SOLVER[k] for k in ('maxiter','gtol','xtol','barrier_tol','sparse_jacobian','factorization_method')})
        finally:
            sys.stderr.flush();warning_log=(out/'native.log').read_text(errors='replace')
            report['warnings_retained_in_owned_native_log']=True
            report['dense_SVD_warning_observed']='SVD' in warning_log or 'Singular Jacobian' in warning_log
            report['warning_text_scan_is_not_backend_fallback_proof']=True
        same_numpy(sys.modules['numpy'],np,c['numpy_init'])
        report['solver']=dict(method='trust-constr',calls=1,success=bool(result.success),status=int(result.status),
            nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),message=str(result.message),
            x=list(map(float,result.x)),fun=float(result.fun),optimality=float(result.optimality),constr_violation=float(result.constr_violation))
        final=assemble_points(np,original,positions,result.x);after=quality(result.x)
        report['final_analytic_quality']=after.tolist();final_quality_gate(bool(result.success),list(map(float,result.x)),after.tolist())
        if final[:8].tobytes()!=original[:8].tobytes():raise ValueError('Any fixed boundary coordinate bit changed')
        report.update(final_coordinates_mm=final.tolist(),all_eight_boundary_coordinate_bits_unchanged=True,
            node_tags=list(NODE_TAGS),tetrahedron_tags=list(TET_TAGS),oriented_TET4=[list(r) for r in TETS],oriented_TRI3=[list(r) for r in TRIANGLES],
            loaded_scientific_files_after=loaded_files(c),no_mesh_or_head_proposal_written=True)
        if any(report['loaded_scientific_files_after'].get(p)!=v for p,v in report['loaded_scientific_files_before'].items()):
            raise ValueError('A previously loaded scientific file changed')
        report['bound_inputs_unchanged']=all(sha(p)==h for mapping in (c['input_hashes'],c['runtime_files']) for p,h in mapping.items())
        if not report['bound_inputs_unchanged']:raise ValueError('Bound source/runtime changed during one call')
        report.update(status='completed_tiny_analytic_software_witness',stage='finished')
        save(out/'fixture-report.json',report);return 0
    except Exception as error:
        report['error']=str(error);save(out/'fixture-report.json',report);return 2


if __name__=='__main__':raise SystemExit(main())
