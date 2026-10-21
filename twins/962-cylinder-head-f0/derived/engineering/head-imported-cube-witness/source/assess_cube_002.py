"""Nine-node field/algebra observations; imported connectivity remains unverified."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

N = 9

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def blocks(path,width):
    """Read numeric MATLAB ASCII blocks without executing source text."""
    text=Path(path).read_text();result=[]
    bodies=re.findall(r"=\s*\[\s*(.*?)\]\s*;",text,re.S)
    if len(re.findall(r"=\s*\[",text))!=len(bodies):raise ValueError("Torn numeric export is not complete")
    for body in bodies:
        rows=[]
        for line in body.splitlines():
            line=line.strip().rstrip(';').strip()
            if not line or line.startswith('%'):continue
            parts=line.split()
            if len(parts)!=width or any(not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",v) for v in parts):
                raise ValueError("Complete finite numeric MATLAB block required")
            row=[float(v) for v in parts]
            if not all(math.isfinite(v) for v in row):raise ValueError("Finite exports required")
            rows.append(row)
        if not rows:raise ValueError("Empty matrix/vector export")
        result.append(rows)
    if not result:raise ValueError("Actual numeric KSP export unavailable")
    return result

def norm(values):return math.sqrt(math.fsum(v*v for v in values))

def actual_settings(text):
    text=text.lower()
    if any(len(re.findall(r'type:\s*'+value+r'\b',text))!=1 for value in ['gmres','hypre']) or 'boomeramg preconditioning' not in text:
        raise ValueError("One actual GMRES and HYPRE BoomerAMG setup must be visible")
    cycles=re.findall(r'cycle type\s+(\S+)',text)
    iterations=re.findall(r'maximum number of iterations per hypre call\s+(\S+)',text)
    tolerances=re.findall(r'convergence tolerance per hypre call\s+(\S+)',text)
    if cycles!=['v'] or iterations!=['1'] or len(tolerances)!=1 or float(tolerances[0])!=0:
        raise ValueError("Actual one V-cycle and zero BoomerAMG tolerance required")
    return dict(ksp_type='gmres',pc_type='hypre',hypre_type='boomeramg',cycle_type='V',maximum_iterations_per_PC_call=1,tolerance_per_PC_call=0)

def require(ok, message):
    if not ok: raise ValueError(message)


def matrix(path):
    data = blocks(path, 3); require(len(data) == 1, 'Exactly one complete matrix block required')
    result = [[0.] * N for _ in range(N)]; seen = set()
    for i, j, value in data[0]:
        require(i == int(i) and j == int(j) and 1 <= i <= N and 1 <= j <= N and (int(i), int(j)) not in seen, 'Unique in-range matrix entry')
        seen.add((int(i), int(j))); result[int(i)-1][int(j)-1] = value
    require(all((i, i) in seen for i in range(1, N+1)), 'All nine matrix rows required')
    return result


def vector(path):
    data = blocks(path, 1); require(len(data) == 1 and len(data[0]) == N, 'One complete nine-entry vector required')
    return [row[0] for row in data[0]]


def algebra(A, P, b, y):
    bn = norm(b); an = norm(v for row in A for v in row)
    require(all(math.isfinite(v) and v > 0 for v in [bn, an]), 'Finite nonzero algebraic norms required')
    boundary = [i for i in range(N) if all(abs(A[i][j] - (1. if i == j else 0.)) <= 1e-12 for j in range(N))]
    free = [i for i in range(N) if i not in boundary]
    require(len(boundary) == 8 and len(free) == 1, 'Eight Dirichlet rows and one free row required')
    i = free[0]; residual = norm(math.fsum(A[k][j]*y[j] for j in range(N))-b[k] for k in range(N))/bn
    difference = norm(A[k][j]-P[k][j] for k in range(N) for j in range(N))/an
    require(all(math.isfinite(v) for v in [residual, difference]) and residual <= 1e-10 and difference <= 1e-12, 'Algebraic residual/A-P criterion')
    require(abs(A[i][i]-8) <= 1e-10 and abs(b[i]+2) <= 1e-10 and abs(y[i]+.25) <= 1e-10 and all(abs(b[j]) <= 1e-10 and abs(y[j]) <= 1e-10 for j in boundary), 'Exact unique-free-DOF Newton residual/direction reference')
    return dict(true_relative_residual=residual, RHS_norm=bn, actual_A_P_relative_Frobenius=difference,
        identity_rows=boundary, free_row=i, free_diagonal=A[i][i], free_RHS=b[i], free_correction=y[i],
        linear_system='J*y=F; F=J*u0-physical_source; u_new=u0-y', zero_initial_free_w_from_bound_input=0.,
        physical_source_free_entry_mm3=2., Newton_residual_free_entry_mm3=b[i], Newton_direction_free_entry_mm2=y[i],
        post_update_free_w_mm2=-y[i], Newton_direction_is_not_final_spatial_w=True,
        row_equals_spatial_node_assumed=False, full_node_to_PETSc_row_map_established=False, SPD_or_CG_claimed=False)


def spatial(rows, reference):
    expected = {tuple(p) for p in reference['coordinates_mm']}; values = {}; seen = set()
    for row in rows:
        tag = Decimal(row['id']); xyz = tuple(float(row[k]) for k in ['x','y','z']); value = float(row['w'])
        require(tag.is_finite() and tag == tag.to_integral_value() and tag >= 0 and int(tag) not in seen, 'Unique integer spatial node IDs required')
        require(all(math.isfinite(v) for v in [*xyz, value]) and xyz in expected and xyz not in values, 'Unique exact finite cube coordinates/field required')
        seen.add(int(tag)); values[xyz] = value
    require(set(values) == expected and len(values) == N, 'Complete nine spatial nodes required')
    errors = [abs(v-(.25 if xyz == (0,0,0) else 0.)) for xyz,v in values.items()]
    require(max(errors) <= 1e-10, 'All-node discrete P1 field criterion')
    return values, dict(nodes=N, boundary_nodes=8, interior_nodes=1, maximum_absolute_w_error_mm2=max(errors), center_w_mm2=values[(0,0,0)], every_node_associated_by_id_and_exact_coordinates=True)


def p1_reference_checks(values, reference):
    # Reconstruct on the AUTHORED reference tets, never claim these were read from MOOSE.
    points = dict(zip(reference['node_tags'], map(tuple, reference['coordinates_mm'])))
    sub = lambda a,b: tuple(x-y for x,y in zip(a,b))
    dot = lambda a,b: math.fsum(x*y for x,y in zip(a,b))
    cross = lambda a,b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    energy = integral = volume = flux = 0.; reaction = {tag:0. for tag in points}; per_face = []
    for tags, face in zip(reference['positive_tetrahedra_node_tags'], reference['outward_triangles_node_tags']):
        p = [points[t] for t in tags]; edges = [sub(p[j], p[0]) for j in [1,2,3]]; det = dot(edges[0], cross(edges[1], edges[2]))
        require(det == 4, 'Exact authored positive tetrahedral determinant')
        gradients = [tuple(v/det for v in cross(edges[a], edges[b])) for a,b in [(1,2),(2,0),(0,1)]]
        gradients.insert(0, tuple(-sum(g[k] for g in gradients) for k in range(3)))
        w = [values[q] for q in p]; gradient = tuple(math.fsum(w[j]*gradients[j][k] for j in range(4)) for k in range(3)); V = det/6
        volume += V; energy += V*dot(gradient,gradient); integral += V*math.fsum(w)/4
        for j,tag in enumerate(tags): reaction[tag] += V*dot(gradients[j],gradient)-V/4
        a,b,c = [points[t] for t in face]; area_normal = tuple(v/2 for v in cross(sub(b,a),sub(c,a)))
        q = -dot(gradient,area_normal); flux += q; per_face.append(q)
    boundary = math.fsum(v for tag,v in reaction.items() if tag != 201)
    require(all(math.isfinite(v) for v in [energy,integral,flux,boundary,volume]), 'Finite derived P1 metrics')
    require(abs(energy-.5) <= 1e-10 and abs(integral-.5) <= 1e-10 and abs(energy-integral) <= 1e-10 and abs(boundary+8) <= 1e-9 and abs(reaction[201]) <= 1e-9 and abs(flux-6) <= 1e-9, 'Authored-reference P1 energy/reaction/flux criterion')
    return dict(authored_reference_tetrahedra=12, imported_connectivity_read_back=False, energy_mm5=energy, integral_w_mm5=integral,
        raw_reference_gradient_flux_mm3=flux, raw_reference_triangle_fluxes_mm3=per_face, source_volume_mm3=volume,
        boundary_reaction_sum_mm3=boundary, free_residual_mm3=reaction[201], known_raw_flux_continuum_deficit_fraction=.25,
        continuum_or_mesh_convergence_passed=False)


def csv_rows(path):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), 'Unique complete CSV column names')
        rows = list(reader)
    require(all(None not in row and all(v is not None for v in row.values()) for row in rows), 'Complete CSV rows required')
    return rows


def assess(output, contract_path, digest):
    output = Path(output); contract_path = Path(contract_path)
    require(sha(contract_path) == digest, 'Exact frozen contract required'); contract = json.loads(contract_path.read_text())
    receipt_path = output/'native-execution.json'; receipt_sha = sha(receipt_path); receipt = json.loads(receipt_path.read_text())
    require(type(receipt.get('returncode')) is int and receipt['returncode'] == 0 and receipt.get('native_execution_completed') is True and receipt.get('process_reaped') is True and receipt.get('inputs_unchanged') is True and receipt.get('binary_and_runtime_unchanged') is True and receipt.get('controller_error') is None and receipt.get('controller_SIGTERM_requested') is False, 'Stopped source-bound successful invocation required')
    require(sha(output/'frozen-contract.json') == digest, 'Executed contract differs')
    for name,h in contract['source_sha256s'].items():
        require(sha(output/'source-snapshots'/name) == h, 'Executed source snapshot differs')
    for name in ['imported-cube.i','imported-cube.msh']:
        require(sha(output/name) == contract['source_sha256s'][name], 'Executed solver input differs')
    require(contract['mesh_sha256'] == sha(output/'imported-cube.msh'), 'Explicit actual mesh hash required')
    pins = receipt.get('artifact_sha256'); require(isinstance(pins,dict) and pins, 'Complete stopped artifact manifest required')
    paths = [p for p in output.rglob('*') if p.is_file() or p.is_symlink()]
    require(not any(p.is_symlink() for p in paths), 'Symlink export refused')
    names = {str(p.relative_to(output)) for p in paths if p.name not in ['native-execution.json','assessment.json']}
    require(names == set(pins), 'Full stopped artifact closure differs')
    for name,h in pins.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and re.fullmatch('[0-9a-f]{64}',str(h)) and sha(output/name) == h, 'Artifact bytes or safe path differs')
    required = {'operator.m','preconditioner.m','rhs.m','correction.m','ksp.txt','true_residual.txt','native.log','imported-cube.csv','imported-cube.e','imported-cube.i','imported-cube.msh','frozen-contract.json'}
    require(required <= names and (output/'imported-cube.e').stat().st_size > 0, 'Required native exports missing')
    node_files = [n for n in names if re.fullmatch(r'imported-cube_nodes.*\.csv',n)]
    require(len(node_files) == 1, 'One complete FINAL nodal CSV required')
    reference = json.loads((output/'source-snapshots/cube-reference.json').read_text())
    values, field = spatial(csv_rows(output/node_files[0]), reference); geometric = p1_reference_checks(values,reference)
    numeric = algebra(matrix(output/'operator.m'),matrix(output/'preconditioner.m'),vector(output/'rhs.m'),vector(output/'correction.m'))
    require(abs(field['center_w_mm2']-numeric['post_update_free_w_mm2']) <= 1e-10, 'Final centre must match zero-initial Newton update u0-y')
    settings = actual_settings((output/'ksp.txt').read_text()); log = (output/'native.log').read_text()
    require('DIVERGED' not in log and len(re.findall(r'Linear solve converged due to CONVERGED_',log)) == 1 and 'Nonlinear solve converged' in log and re.search('true resid',log,re.I), 'One actual successful Newton/KSP solve required')
    native_norms = [float(v) for v in re.findall(r'KSP final norm of residual\s+(\S+)',(output/'true_residual.txt').read_text())]
    require(len(native_norms) == 1 and math.isfinite(native_norms[0]) and 0 <= native_norms[0]/numeric['RHS_norm'] <= 1e-10, 'Native final true residual criterion')
    rows = csv_rows(output/'imported-cube.csv'); require(len(rows) == 1, 'One FINAL scalar CSV row required')
    native_flux = float(rows[0]['raw_outward_gradient_flux'])
    require(math.isfinite(native_flux) and abs(native_flux-6) <= 1e-9 and abs(native_flux-geometric['raw_reference_gradient_flux_mm3']) <= 1e-9, 'Native flux versus discrete reference criterion')
    require(sha(contract_path) == digest and sha(receipt_path) == receipt_sha and all(sha(output/n) == h for n,h in pins.items()), 'Evidence drift during assessment')
    return dict(status='scoped_nine_node_and_algebra_observations_passed_imported_connectivity_pending',passed=True,
        native_execution_sha256=receipt_sha,artifact_sha256=pins,spatial_field=field,algebra=numeric,authored_reference_P1=geometric,
        actual_settings=settings,native_raw_flux_mm3=native_flux,complete_imported_mesh_witness_passed=False,
        actual_imported_connectivity_Jacobians_and_sideset_readback_complete=False,head_or_physical_or_LPBF_or_manufacturing_admitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True); parser.add_argument('--contract-sha256',required=True); args = parser.parse_args()
    result = assess(args.output,args.contract,args.contract_sha256)
    with (args.output/'assessment.json').open('x') as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
