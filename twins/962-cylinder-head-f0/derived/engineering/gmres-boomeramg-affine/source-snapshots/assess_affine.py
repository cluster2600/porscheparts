"""Independent finite-array, algebraic, all-node and face-flux witness checks."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re

N=64
SIDES={"left":1.,"right":-1.,"bottom":2.,"top":-2.,"back":3.,"front":-3.}


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


def matrices(path):
    result=[]
    for block in blocks(path,3):
        matrix=[[0.]*N for _ in range(N)];seen=set()
        for i,j,value in block:
            if i!=int(i) or j!=int(j) or not 1<=i<=N or not 1<=j<=N or (int(i),int(j)) in seen:
                raise ValueError("Unique in-range matrix entries required")
            seen.add((int(i),int(j)));matrix[int(i)-1][int(j)-1]=value
        if any((i,i) not in seen for i in range(1,N+1)):raise ValueError("Complete 64-row operator required")
        result.append(matrix)
    return result


def vectors(path):
    result=[[row[0] for row in block] for block in blocks(path,1)]
    if any(len(v)!=N for v in result):raise ValueError("Complete length-64 vectors required")
    return result


def norm(values):return math.sqrt(math.fsum(v*v for v in values))


def bound_exports(output,receipt):
    pins=receipt.get('artifact_sha256')
    if not isinstance(pins,dict) or not pins:raise ValueError("Native export hash manifest missing")
    paths=[p for p in output.rglob('*') if p.is_file() or p.is_symlink()]
    if any(p.is_symlink() for p in paths):raise ValueError("Native exports must be regular non-symlink files")
    names={str(p.relative_to(output)) for p in paths if p.name not in ['native-execution.json','assessment.json']}
    if names!=set(pins):raise ValueError("Native export inventory missing or changed")
    required={'operator.m','preconditioner.m','rhs.m','correction.m','ksp.txt','true_residual.txt','native.log','affine.csv','affine.i','frozen-contract.json'}
    if not required<=names or len([n for n in names if re.fullmatch(r'affine_nodes.*\.csv',n)])!=1:
        raise ValueError("Required actual exports missing from native manifest")
    for name,digest in pins.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not re.fullmatch(r'[0-9a-f]{64}',str(digest)) or sha(output/p)!=digest:
            raise ValueError("Bound native export bytes changed")
    return pins


def algebra(A,P,b,y):
    bnorm=norm(b);anorm=norm(v for row in A for v in row)
    if not all(math.isfinite(v) and v>0 for v in [bnorm,anorm]):raise ValueError("Finite nonzero operator and RHS norms required")
    identity=[i for i in range(N) if all(abs(A[i][j]-(1. if i==j else 0.))<=1e-12 for j in range(N))]
    free=[i for i in range(N) if i not in identity]
    if len(identity)!=56 or len(free)!=8:raise ValueError("Exactly 56 identity BC rows and eight free rows required")
    r=[math.fsum(A[i][j]*y[j] for j in range(N))-b[i] for i in range(N)]
    fnorm=norm(A[i][j] for i in free for j in free)
    if not math.isfinite(fnorm) or fnorm<=0:raise ValueError("Finite nonzero free operator required")
    result=dict(true_relative_residual=norm(r)/bnorm,RHS_norm=bnorm,operator_Frobenius_norm=anorm,
        identity_rows=identity,free_rows=free,
        full_symmetry_relative_Frobenius=norm(A[i][j]-A[j][i] for i in range(N) for j in range(N))/anorm,
        free_symmetry_relative_Frobenius=norm(A[i][j]-A[j][i] for i in free for j in free)/fnorm,
        actual_A_P_relative_Frobenius=norm(A[i][j]-P[i][j] for i in range(N) for j in range(N))/anorm,
        Dirichlet_column_coupling_count=sum(abs(A[i][j])>1e-12 for i in free for j in identity),
        row_equals_node_assumed=False,native_free_vs_geometric_P1_matrix_equality_established=False,
        positive_definiteness_or_preconditioner_SPD_established=False)
    numeric=['true_relative_residual','full_symmetry_relative_Frobenius','free_symmetry_relative_Frobenius','actual_A_P_relative_Frobenius']
    if not all(math.isfinite(result[k]) for k in numeric) or result['true_relative_residual']>1e-10 or result['free_symmetry_relative_Frobenius']>1e-12 or result['actual_A_P_relative_Frobenius']>1e-12:
        raise ValueError("Frozen actual operator/residual criteria failed")
    return result


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


def spatial(rows):
    values={};ids=set();errors=[];boundary_errors=[]
    for row in rows:
        x=[float(row[k]) for k in ['x','y','z']];w=float(row['w']);node=float(row['id'])
        if not all(math.isfinite(v) for v in [*x,w,node]) or node!=int(node) or node in ids:
            raise ValueError("Unique finite nodal samples required")
        ids.add(node);key=tuple(round((v-1)*3) for v in x)
        if any(not 0<=i<=3 or abs(v-(1+i/3))>1e-12 for i,v in zip(key,x)) or key in values:
            raise ValueError("Complete exact declared spatial grid required")
        error=abs(w-(x[0]+2*x[1]+3*x[2]));errors.append(error);values[key]=w
        if any(i in (0,3) for i in key):boundary_errors.append(error)
    if len(values)!=64 or len(boundary_errors)!=56:raise ValueError("All 64 nodes, including eight interior nodes, are required")
    maximum=max(errors)/12;rms=norm(errors)/(8*12)
    if maximum>1e-10 or rms>1e-10 or max(boundary_errors)>1e-10:
        raise ValueError("All-node affine field or Dirichlet data failed")
    flux={};h=1/3
    for axis,names in enumerate([('left','right'),('bottom','top'),('back','front')]):
        others=[i for i in range(3) if i!=axis]
        for end,name in enumerate(names):
            terms=[]
            for j in range(3):
                for k in range(3):
                    differences=[]
                    for dj in (0,1):
                        for dk in (0,1):
                            lo=[0]*3;lo[axis]=2 if end else 0;lo[others[0]]=j+dj;lo[others[1]]=k+dk
                            hi=lo.copy();hi[axis]+=1
                            differences.append((values[tuple(hi)]-values[tuple(lo)])/h)
                    terms.append((-1 if end else 1)*math.fsum(differences)/4*h*h)
            flux[name]=math.fsum(terms)
    if any(abs(flux[name]-expected)>1e-9 for name,expected in SIDES.items()):raise ValueError("Independent complete Q1 face flux failed")
    return dict(nodes=64,boundary_nodes=56,genuine_interior_nodes=8,relative_maximum_error=maximum,
        relative_unweighted_nodal_RMS_error=rms,boundary_maximum_absolute_error=max(boundary_errors),
        reconstructed_Q1_face_fluxes=flux,outer_cell_face_integrals=54,
        topology_basis='Frozen GeneratedMesh 3x3x3 HEX8 topology; complete spatial node coverage verified')


def assess(output,contract_path,digest):
    output=Path(output);contract_path=Path(contract_path)
    if sha(contract_path)!=digest:raise ValueError("Exact frozen witness contract required")
    contract=json.loads(contract_path.read_text());execution_digest=sha(output/'native-execution.json')
    receipt=json.loads((output/'native-execution.json').read_text())
    if type(receipt.get('returncode')) is not int or receipt['returncode']!=0 or receipt.get('process_reaped') is not True or receipt.get('binary_and_runtime_unchanged') is not True or receipt.get('inputs_unchanged') is not True:
        raise ValueError("Completed source-bound native witness required")
    if sha(output/'frozen-contract.json')!=digest:raise ValueError("Executed contract changed")
    source=Path(__file__).resolve().parent
    for name,h in contract['source_sha256s'].items():
        if sha(output/'source-snapshots'/name)!=h or sha(source/name)!=h:raise ValueError("Current or executed source/input identity changed")
    if sha(output/'affine.i')!=contract['source_sha256s']['affine.i']:
        raise ValueError("Actual solver input changed from the frozen source")
    exports=bound_exports(output,receipt)
    A=matrices(output/'operator.m');P=matrices(output/'preconditioner.m');b=vectors(output/'rhs.m');y=vectors(output/'correction.m')
    if not len(A)==len(P)==len(b)==len(y)==1:raise ValueError("Exactly one actual KSP solve with complete matching exports required")
    matrix_checks=[algebra(*items) for items in zip(A,P,b,y)]
    settings=actual_settings((output/'ksp.txt').read_text());log=(output/'native.log').read_text()
    if 'DIVERGED' in log or len(re.findall(r'Linear solve converged due to CONVERGED_',log))!=len(A):
        raise ValueError("Every native KSP convergence reason must succeed")
    if not re.search(r'true resid',log,re.I) or 'Nonlinear solve converged' not in log:
        raise ValueError("Native true-residual history and nonlinear convergence required")
    native_residual=(output/'true_residual.txt').read_text()
    native_norms=[float(v) for v in re.findall(r'KSP final norm of residual\s+(\S+)',native_residual)]
    if len(native_norms)!=len(A) or any(not math.isfinite(v) or v<0 or v/row['RHS_norm']>1e-10 for v,row in zip(native_norms,matrix_checks)):
        raise ValueError("Native final true residual export missing or invalid")
    node_files=list(output.glob('affine_nodes*.csv'))
    if len(node_files)!=1:raise ValueError("One complete final spatial nodal export required")
    with node_files[0].open() as stream:field=spatial(list(csv.DictReader(stream)))
    with (output/'affine.csv').open() as stream:rows=list(csv.DictReader(stream))
    if len(rows)!=1:raise ValueError("One complete final six-face flux row required")
    native_flux={name:float(rows[0]['flux_'+name]) for name in SIDES}
    if any(not math.isfinite(v) or abs(v-SIDES[name])>1e-9 or abs(v-field['reconstructed_Q1_face_fluxes'][name])>1e-9 for name,v in native_flux.items()):
        raise ValueError("Every native and independent face flux must pass separately")
    if sha(output/'native-execution.json')!=execution_digest or bound_exports(output,receipt)!=exports:
        raise ValueError("Native receipt or exports changed during assessment")
    if sha(contract_path)!=digest or any(sha(source/name)!=h for name,h in contract['source_sha256s'].items()):
        raise ValueError("Frozen contract or current sources changed during assessment")
    return dict(status='synthetic_GMRES_BoomerAMG_affine_witness_passed',passed=True,linear_solves=len(A),
        native_execution_sha256=execution_digest,artifact_sha256=exports,actual_KSP_PC_settings=settings,
        algebraic_checks=matrix_checks,all_node_field=field,native_face_fluxes=native_flux,
        native_true_residual_text=native_residual,native_final_true_residual_norms=native_norms,
        native_free_vs_geometric_P1_matrix_equality_established=False,
        head_import_or_scalability_or_resolution_established=False,CG_or_SPD_credited=False,
        thermal_performance_or_strength_validated=False,manufacturing_authorized=False)
