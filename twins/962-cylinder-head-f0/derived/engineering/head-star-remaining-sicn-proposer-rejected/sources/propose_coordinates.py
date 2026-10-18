"""HELD analytic coordinate proposal only; original-runtime native application is separate."""
from collections import Counter
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import sys

OUTPUT_NAME = 'head-star-remaining-sicn-proposal-001'
LIMITS = dict(wall_seconds=300, sampled_RSS_bytes=1024**3,
              sampled_output_bytes=16*1024**2, threads=2)
SOLVER = dict(method='SLSQP', maxiter=100, ftol=1e-10, eps=2.0**-26)
GATE = .1
COUNTS = dict(movable_nodes=155, coordinate_variables=465, variables_with_epigraph=466,
              constraints=5327, context_nodes=2938)
QUALIFICATION = dict(head_optimization_authorized=False, engineering_accepted=False,
                     physics_qualified=False, manufacturing_authorized=False)


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




def partial_after_proof(worker,receipt,closed,contract):
 """Bind the actual partial-replacement after/saved proof without optimizer aliases."""
 if (worker.get('schema')!='962-one-head-star-partial-replacement/v1'
     or worker.get('status')!='completed_partial_head_replacement_whole_head_quality_gate_applied'
     or worker.get('stage')!='completed_partial_repair_audits'
     or any(worker.get(k) is not True for k in ['procedural_checks_passed','partial_replacement_completed','saved_mesh_identity_exact','bound_inputs_unchanged'])
     or worker.get('after')!=worker.get('saved_reopen')
     or worker.get('mesh_sha256')!=contract['MSH_sha256'] or worker.get('mesh_bytes')!=contract['MSH_bytes']
     or worker.get('candidate_sha256')!=contract['partial_coordinate_candidate_sha256']
     or worker.get('original_parent_MSH_sha256')!=contract['original_parent_MSH_sha256']
     or receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('readback_report_sha256')!=contract['partial_report_sha256']
     or receipt.get('contract_sha256')!=contract['partial_contract_sha256']
     or receipt.get('reader_sha256')!=contract['partial_reader_sha256']
     or receipt.get('runner_sha256')!=contract['partial_runner_sha256']
     or receipt.get('native_log_sha256')!=contract['partial_native_log_sha256']
     or closed.get('returncode')!=2 or closed.get('stop_reason') is not None or closed.get('wait_reaped') is not True
     or any(closed.get(k) is not True for k in ['all72_inputs_unchanged','all3_selected_native_runtime_unchanged','selected_NumPy_unchanged','actual_unchanged'])
     or closed.get('actual_sha256')!=contract['partial_contract_sha256']
     or closed.get('outputs')!=contract['partial_output_inventory']):
  raise ValueError('Exact stopped partial-replacement after/saved proof required')
 proof=worker['after'];n=proof['tetrahedra'];quality=proof['quality'];keys={'sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'}
 counts={k:proof[k] for k in contract['expected_saved_counts']}
 if (counts!=contract['expected_saved_counts'] or any(type(v) is not int for v in counts.values())
     or set(proof['array_sha256s'])!=keys
     or set(quality)!={'minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3'}
     or any(type(row.get('count')) is not int or row['count']!=n or type(row.get('nonpositive_count')) is not int for row in quality.values())
     or quality['minimum_SICN']['below_point1_count']-quality['minimum_SICN']['nonpositive_count']!=contract['expected_positive_poor_total']
     or quality['minimum_SICN']['nonpositive_count']!=contract['diagnostic_maximum_nonpositive_cells']
     or worker.get('actual_whole_head_positive_poor_count')!=contract['expected_positive_poor_total']
     or worker.get('actual_whole_head_SICN_gate_passed') is not (quality['minimum_SICN']['minimum']>=.1 and quality['minimum_SICN']['nonpositive_count']==0)
     or proof['source_boundary_identity']!=contract['expected_source_boundary_identity']):
  raise ValueError('Complete current partial-head arrays/counts/quality/boundary proof required')
 return proof

def require_after_match(report,proof,expected_positive_poor_total):
 """Require direct full saved-file observations to match the single worker proof."""
 for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_tetra_referenced_nodes','tetra_referenced_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes')]:
  if type(report[observed]) is not int or report[observed]!=proof[expected]:raise ValueError('Saved node/tetrahedron/reference counts differ from worker.after')
 fields=['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count']
 for name,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
  observed=report['direct_native_quality_extrema'][name];expected=proof['quality'][key]
  if any(observed[k]!=expected[k] for k in [*fields,'array_sha256']):raise ValueError('Full saved native metric differs from worker.after: '+name)
  if name=='SICN' and observed['below_point1_count']!=expected['below_point1_count']:raise ValueError('SICN below-point1 count differs from worker.after')
 observed=report['independent_signed_volume_mm3'];expected=proof['quality']['independent_signed_volume_mm3']
 if (any(observed[k]!=expected[k] for k in fields) or observed['sum']!=proof['summed_tetra_volume_mm3'] or observed['relative_error_to_candidate']!=proof['volume_relative_error']):
  raise ValueError('Independent saved signed-volume distribution/sum differs from worker.after')
 if report['positive_poor_SICN_cells']['total']!=expected_positive_poor_total:raise ValueError('Exact current positive-poor partition required')

def current_census_proof(c,report,worker,receipt,closed,binding,peer):
    """Explicit current partial-after/saved authority; no optimizer or old-count aliases."""
    proof=partial_after_proof(worker,receipt,closed,binding)
    if (binding['MSH_sha256']!=c['source_mesh_sha256'] or binding['partial_report_sha256']!=c['source_worker_report_sha256']
            or binding['expected_positive_poor_total']!=208
            or report['status']!='direct_saved_file_readback_completed' or report['bound_inputs_unchanged'] is not True
            or report['single_partial_replacement_saved_proof']!=dict(report_sha256=c['source_worker_report_sha256'],field='after',after_equals_saved_reopen=True,independent_prior_reader_alias_used=False,old210_bins_reused=False)
            or {k:report[k] for k in c['source_tagged_array_sha256s']}!=c['source_tagged_array_sha256s']
            or proof['array_sha256s']!=c['source_tagged_array_sha256s'] or report['direct_fresh_classifications']!=proof['classifications']
            or peer['decision']!='CLEAR_COMPLETED_READ_ONLY_CURRENT208_CENSUS_MESH_REMAINS_REJECTED'
            or peer['bindings']['report']['sha256']!=c['source_census_sha256'] or peer['blockers']!=[] or peer['head_volume_accepted'] is not False):
        raise ValueError('Exact current partial-head/census/stopped-peer associations required')
    require_after_match(report,proof,208)
    return proof

def read_census(c):
    roles=['source_census','source_census_contract','source_worker_report','source_worker_receipt','source_worker_root_closed','source_census_peer']
    data={}
    for key in roles:
        if sha(c[key])!=c[key+'_sha256']:raise ValueError('Current evidence bytes changed: '+key)
        data[key]=json.loads(Path(c[key]).read_text())
    report=data['source_census'];s=report['complete_seed_star_census']
    current_census_proof(c,report,data['source_worker_report'],data['source_worker_receipt'],data['source_worker_root_closed'],data['source_census_contract'],data['source_census_peer'])
    if (s['schema']!='962-complete-current-poor-seed-stars/v1' or s['movable_count']!=155
            or s['prospective_coordinate_variables']!=465 or s['complete_incident_tetrahedron_count']!=5327
            or s['unique_incident_node_count']!=2938
            or s['unique_incident_boundary_node_count']!=1848 or s['unique_incident_other_interior_node_count']!=935
            or s['shared_by_multiple_movable_nodes_tetrahedra']!=223
            or s['all_seed_stars_complete_including_initially_good_and_shared_cells'] is not True
            or s['all_positive_poor_rows_covered_by_movable_stars'] is not True or s['unseedable_positive_poor_tetrahedron_tags']!=[]):
        raise ValueError('Frozen complete seed-star counts/attestation required')
    nodes=s['unique_incident_nodes']; cells=s['complete_incident_tetrahedra']; movable=s['movable_node_tags']
    if len(nodes)!=2938 or len(cells)!=5327 or len(movable)!=155:raise ValueError('Incomplete saved rows')
    tags=[r['node_tag'] for r in nodes]; connectivity=[r['node_tags'] for r in cells]
    indices,positions=tagged_indices(tags,connectivity,movable); seeds=set(movable)
    tet_tags=[r['tetrahedron_tag'] for r in cells]
    if tet_tags!=sorted(set(tet_tags)) or any(type(t) is not int or not 0<t<2**64 for t in tet_tags):
        raise ValueError('Sorted unique tetrahedron tags required')
    native_indices=[r['native_array_index'] for r in cells]
    if len(set(native_indices))!=5327 or any(type(i) is not int or not 0<=i<3620820 for i in native_indices):
        raise ValueError('Unique in-range native array indices required')
    coordinates=[]
    for r in nodes:
        xyz=r['coordinates_mm']; words=r['binary64_hex']; boundary=r['node_tag']<=871731
        if (len(xyz)!=3 or len(words)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
                or any(type(h) is not str or float(x).hex()!=h or struct.pack('<d',float.fromhex(h))!=struct.pack('<d',x) for x,h in zip(xyz,words))
                or r['in_movable_seed_set'] is not (r['node_tag'] in seeds) or r['source_boundary_tag'] is not boundary
                or r['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')):
            raise ValueError('Raw binary64 coordinate/tag/classification join failed')
        coordinates.append(xyz)
    poor=[]; counts=Counter(); q=[]; shared=0
    for r in cells:
        value=r['initial_native_SICN']; members=sorted(seeds.intersection(r['node_tags']))
        if (type(value) not in (int,float) or not math.isfinite(value) or value<=0 or not members
                or r['movable_node_tags']!=members or r['initially_positive_poor'] is not (value<GATE)):
            raise ValueError('Complete coupled cell/member/native-quality association failed')
        counts.update(members); shared+=len(members)>1; q.append(value)
        if value<GATE:poor.append(r['tetrahedron_tag'])
    poor_seed_union={t for r in cells if r['initially_positive_poor'] for t in r['node_tags'] if t>871731}
    if (len(poor)!=208 or poor!=s['positive_poor_tetrahedron_tags'] or poor_seed_union!=seeds or shared!=223
            or [[t,counts[t]] for t in movable]!=s['per_movable_node_complete_incident_counts']
            or sum(t<=871731 for t in tags)!=1848 or sum(t>871731 and t not in seeds for t in tags)!=935
            or s['initially_positive_poor_incident_tetrahedra']!=208 or s['initially_good_incident_tetrahedra']!=5119):
        raise ValueError('Complete 208-poor/5119-good/155-seed saved partition failed')
    typed = {
        'movable_node_tags_u64':('Q',movable), 'selected_tetrahedron_tags_u64':('Q',tet_tags),
        'selected_tetrahedron_connectivity_u64':('Q',[t for r in connectivity for t in r]),
        'union_node_tags_u64':('Q',tags), 'union_coordinates_f64':('d',[x for r in coordinates for x in r]),
        'selected_initial_SICN_f64':('d',q)}
    actual={k:hashlib.sha256(b''.join(struct.pack('<'+fmt,x) for x in values)).hexdigest() for k,(fmt,values) in typed.items()}
    if actual!=s['ordered_tagged_array_sha256s'] or actual!=c['census_typed_section_sha256s']:
        raise ValueError('Every typed census section must match its frozen hash')
    return coordinates,indices,positions,movable,q,tet_tags,tags


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


def bound_contract(path):
    c=json.loads(path.read_text())
    if (c.get('schema')!='962-current-partial-sicn-head-proposer/v1' or c.get('scope')!='analytic_current_partial_coordinate_proposal_only'
            or c.get('proposal_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
            or c.get('selected_runtime_review_complete') is not True or c.get('qualification')!=QUALIFICATION
            or c.get('limits')!=LIMITS or c.get('solver')!=SOLVER or c.get('sicn_gate')!=GATE or c.get('input_counts')!=COUNTS):
        raise ValueError('Separately reviewed bounded analytic-proposal child required')
    for mapping in (c['input_hashes'],c['runtime_files']):
        if not mapping:raise ValueError('Nonempty exact input and selected runtime maps required')
        for name,digest in mapping.items():
            p=Path(name)
            if not re.fullmatch('[0-9a-f]{64}',digest) or not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=digest:
                raise ValueError('Frozen input/selected runtime identity changed')
    if c['reader_sha256']!=sha(__file__) or c['runner_sha256']!=sha(path.with_name('run_readback.py')):
        raise ValueError('Reviewed copied worker/controller identities required')
    if c['runtime_files'].get(str(Path(sys.executable).resolve()))!=sha(Path(sys.executable).resolve()):
        raise ValueError('Exact selected interpreter required')
    if Path(c['output'])!=path.parent or path.parent.name!=OUTPUT_NAME:raise ValueError('Exact fresh output required')
    for key in ['source_census','source_census_contract','source_worker_report','source_worker_receipt','source_worker_root_closed','source_census_peer']:
        if c['input_hashes'].get(c[key])!=c[key+'_sha256']:raise ValueError('Every consumed current evidence role must be direct-pinned')
    return c


def main():
    out=Path(__file__).resolve().parent; report=dict(status='refused',stage='contract',minimize_calls_attempted=0,qualification=QUALIFICATION)
    try:
        if set(p.name for p in out.iterdir())!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
            raise ValueError('Only the three fresh materialized inputs and controller log may exist')
        c=bound_contract(out/'frozen-contract.json'); report['contract_sha256']=sha(out/'frozen-contract.json')
        report['stage']='census'; print('census: begin',flush=True)
        coordinates,indices,positions,tags,native_q,tet_tags,node_tags=read_census(c)
        report['stage']='imports'; print('imports: begin',flush=True); np,optimize=scientific_modules(c)
        original=np.asarray(coordinates,dtype=np.float64); original.setflags(write=False)
        original_hash=hashlib.sha256(original.tobytes()).hexdigest(); cell_indices=np.asarray(indices,dtype=np.int64)
        report['stage']='calibration'; print('calibration: all 5327 saved native rows',flush=True)
        before=signed_sicn_vector(np,original[cell_indices])
        if any(not math.isclose(float(a),b,rel_tol=1e-11,abs_tol=1e-14) for a,b in zip(before,native_q)):
            raise ValueError('Vectorized analytic/native census calibration failed')
        report['calibration']=dict(count=5327,relative_tolerance=1e-11,absolute_tolerance=1e-14,
            maximum_absolute_error=max(abs(float(a)-b) for a,b in zip(before,native_q)),
            initial_minimum=float(np.min(before)),all_saved_native_rows_match=True)
        x0=np.r_[original[positions].reshape(-1),float(np.min(before))]
        def quality(x):return signed_sicn_vector(np,assemble_points(np,original,positions,x)[cell_indices])
        report['loaded_scientific_files_before']=loaded_files(c)
        report['stage']='one_SLSQP'; print('one_SLSQP: begin 466 variables / 5327 constraints',flush=True)
        report['minimize_calls_attempted']=1
        save(out/'solver-start-checkpoint.json',report)  # Survives a controller kill; not a completed result.
        result=optimize.minimize(lambda x:-x[-1],x0,method=SOLVER['method'],
            bounds=[(None,None)]*465+[(float(np.min(before)),1.)],
            constraints=[{'type':'ineq','fun':lambda x:quality(x)-x[-1]}],
            options={k:SOLVER[k] for k in ('maxiter','ftol','eps')})
        solver=dict(method='SLSQP',calls=1,success=bool(result.success),status=int(result.status),
                    nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),message=str(result.message))
        report['solver']=solver;final=assemble_points(np,original,positions,result.x)
        rows=[dict(node_tag=t,coordinates_mm=[float(x) for x in final[p]],binary64_hex=[float(x).hex() for x in final[p]]) for t,p in zip(tags,positions)]
        fixed=np.setdiff1d(np.arange(2938),positions)
        fixed_bits=bool(np.array_equal(final[fixed].view('u8'),original[fixed].view('u8')))
        diagnostic=dict(schema='962-current-partial-SICN-solver-final-state-diagnostic/v1',is_coordinate_proposal=False,
            native_application_authorized=False,source_census_sha256=c['source_census_sha256'],source_mesh_sha256=c['source_mesh_sha256'],
            source_worker_report_sha256=c['source_worker_report_sha256'],source_tagged_array_sha256s=c['source_tagged_array_sha256s'],
            census_typed_section_sha256s=c['census_typed_section_sha256s'],coordinate_rows=rows,selected_tetrahedron_tags=tet_tags,
            epigraph_t=float(result.x[-1]),epigraph_binary64_hex=float(result.x[-1]).hex(),solver=solver,fixed_context_coordinate_bits_unchanged=fixed_bits,
            quality_value_order='Increasing selected source tetrahedron tag; native corner order retained',
            analytic_signed_SICN=None,quality_evaluation_error=None,global_optimum_or_epigraph_feasibility_claimed=False,qualification=QUALIFICATION)
        try:
            after=quality(result.x);diagnostic['analytic_signed_SICN']=after.tolist()
            diagnostic['minimum_constraint_residual']=float(np.min(after-result.x[-1]))
        except ValueError as error:
            diagnostic['quality_evaluation_error']=str(error);save(out/'solver-final-state.json',diagnostic)
            report['diagnostic_state_sha256']=sha(out/'solver-final-state.json');raise
        save(out/'solver-final-state.json',diagnostic) # Retain every finite returned point before quality/solver refusal.
        report['diagnostic_state_sha256']=sha(out/'solver-final-state.json')
        metrics=dict(count=int(after.size),minimum=float(np.min(after)),below_point1_count=int(np.count_nonzero(after<GATE)),
                     nonpositive_count=int(np.count_nonzero(after<=0)),array_sha256=hashlib.sha256(after.astype('<f8').tobytes()).hexdigest())
        report['analytic_quality']=metrics;report['epigraph_t']=float(result.x[-1])
        report['minimum_constraint_residual']=diagnostic['minimum_constraint_residual']
        report['all_fixed_context_coordinate_bits_unchanged']=fixed_bits
        report['loaded_scientific_files_after']=loaded_files(c)
        report['bound_inputs_unchanged']=all(sha(p)==h for m in (c['input_hashes'],c['runtime_files']) for p,h in m.items())
        report['all5327_analytic_quality_gate']=metrics['count']==5327 and not metrics['below_point1_count'] and not metrics['nonpositive_count']
        if not result.success or metrics['count']!=5327 or metrics['below_point1_count'] or metrics['nonpositive_count']:
            raise ValueError('Single solver call did not produce a provisional all-cell SICN >= 0.1 proposal')
        if hashlib.sha256(original.tobytes()).hexdigest()!=original_hash or not fixed_bits:
            raise ValueError('A fixed context coordinate changed')
        if not report['bound_inputs_unchanged']:raise ValueError('Input/runtime changed during proposal')
        proposal=dict(schema='962-direct-SICN-tagged-coordinate-proposal/v1',source_census_sha256=c['source_census_sha256'],
            source_mesh_sha256=c['source_mesh_sha256'],source_worker_report_sha256=c['source_worker_report_sha256'],
            source_tagged_array_sha256s=c['source_tagged_array_sha256s'],census_typed_section_sha256s=c['census_typed_section_sha256s'],
            coordinate_rows=rows,solver=solver,analytic_quality=metrics,native_application_required=True,global_optimum_or_epigraph_feasibility_claimed=False,qualification=QUALIFICATION)
        report['stage']='emit'; print('emit: analytic coordinate proposal only',flush=True)
        save(out/'coordinate-proposal.json',proposal); report.update(status='analytic_coordinate_proposal_completed',proposal_sha256=sha(out/'coordinate-proposal.json'))
        save(out/'fixture-report.json',report); return 0
    except Exception as error:
        report['error']=str(error); save(out/'fixture-report.json',report); return 2


if __name__=='__main__':raise SystemExit(main())
