"""Fixed imported affine elastic cube; no solver launch or generic mesh fallback."""
import csv
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from collections import Counter, defaultdict

def need(ok, message):
    if not ok: raise ValueError(message)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def oriented(row):
    return min(tuple(row[i:]+row[:i]) for i in range(3))

def determinant(p):
    e = [tuple(p[j][k]-p[0][k] for k in range(3)) for j in [1,2,3]]
    return sum(e[0][k]*(e[1][(k+1)%3]*e[2][(k+2)%3]-e[1][(k+2)%3]*e[2][(k+1)%3]) for k in range(3))

def side_table_from_primary(path, digest):
    import re
    need(sha(path)==digest, 'Exact reviewed SEACAS primary source required')
    source=Path(path).read_text()
    match=re.search(r'static const int tetra_table\[4\]\[7\]\s*=\s*\{(.*?)\};',source,re.S)
    need(match is not None, 'Explicit primary tetra_table missing')
    rows=[list(map(int,re.findall(r'\d+',row))) for row in re.findall(r'\{([^{}]+)\}',match.group(1))]
    need(len(rows)==4 and all(len(row)==7 for row in rows), 'Exact four primary side rows required')
    return {i+1:[v-1 for v in row[:3]] for i,row in enumerate(rows)}

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


COMP = [(0,0),(1,1),(2,2),(0,1),(0,2),(1,2)]
DISP = ['disp_x','disp_y','disp_z']
FORCE = ['rx','ry','rz']
CARD_SHA = '63783fe610ad80b8b430e44b4b47a5c5636130202b65d592beb2920399217a4a'


def bits(point): return struct.pack('<3d', *point)
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return math.fsum(x*y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def integer(value):
    x=Decimal(str(value));need(x.is_finite() and x==x.to_integral_value() and x>=0,'Nonnegative integer ID required');return int(x)


def rows(path):
    with Path(path).open(newline='') as stream:
        reader=csv.DictReader(stream)
        need(reader.fieldnames and len(set(reader.fieldnames))==len(reader.fieldnames),'Unique CSV headers required')
        result=list(reader)
    need(result and all(None not in r and all(v is not None for v in r.values()) for r in result),'Complete CSV rows required')
    return result


def node_values(data,coordinates):
    values={};ids=set();expected={bits(p) for p in coordinates}
    for row in data:
        need(set(row)=={'id','x','y','z',*DISP,*FORCE},'Exactly declared nodal fields required')
        tag=integer(row['id']);xyz=tuple(float(row[k]) for k in 'xyz');fields=[float(row[k]) for k in DISP+FORCE]
        need(all(math.isfinite(v) for v in [*xyz,*fields]) and tag not in ids and bits(xyz) in expected and bits(xyz) not in values,'Unique exact finite node/field association')
        ids.add(tag);values[bits(xyz)]={'observed_id':tag,'xyz':xyz,'u':fields[:3],'r':fields[3:]}
    need(set(values)==expected and len(values)==len(coordinates),'Complete node coordinate set required')
    return values


def join_qp(data,centroids,tolerance):
    need(len(data)==len(centroids),'One quadrature point per complete cell required')
    result={};seen_ids=set()
    for row in data:
        need(set(row)=={'elem_id','qp_id','x','y','z',*[f'{prefix}_{a}{b}' for prefix in ['stress','total_strain'] for a,b in ['xx','yy','zz','xy','xz','yz']]},'Exactly declared cell tensor fields required')
        element=integer(row['elem_id']);need(integer(row['qp_id'])==0 and element not in seen_ids,'One unique centroid qp0 per observed element')
        xyz=tuple(float(row[k]) for k in 'xyz');need(all(math.isfinite(v) for v in xyz),'Finite quadrature coordinates')
        matches=[i for i,c in enumerate(centroids) if all(abs(x-y)<=tolerance for x,y in zip(xyz,c))]
        need(len(matches)==1 and matches[0] not in result,'Unique unambiguous centroid-to-cell association')
        result[matches[0]]=row;seen_ids.add(element)
    need(set(result)==set(range(len(centroids))),'Complete centroid coverage required')
    return result


def p1_cell(points,displacements,lam,mu):
    edges=[sub(points[j],points[0]) for j in (1,2,3)];det=dot(edges[0],cross(edges[1],edges[2]))
    need(math.isfinite(det) and det>0,'Positive finite P1 tetrahedron required')
    gradients=[tuple(v/det for v in cross(edges[a],edges[b])) for a,b in [(1,2),(2,0),(0,1)]]
    gradients.insert(0,tuple(-math.fsum(g[k] for g in gradients) for k in range(3)))
    grad=[[math.fsum(displacements[a][i]*gradients[a][j] for a in range(4)) for j in range(3)] for i in range(3)]
    strain=[[(grad[i][j]+grad[j][i])/2 for j in range(3)] for i in range(3)];trace=sum(strain[i][i] for i in range(3))
    stress=[[2*mu*strain[i][j]+(lam*trace if i==j else 0) for j in range(3)] for i in range(3)]
    volume=det/6;energy=.5*volume*math.fsum(stress[i][j]*strain[i][j] for i in range(3) for j in range(3))
    forces=[[volume*dot(stress[i],g) for i in range(3)] for g in gradients]
    need(all(math.isfinite(v) for v in [energy,*[x for row in forces+strain+stress for x in row]]),'Finite P1 fields/reactions/energy')
    return volume,strain,stress,forces,energy


def geometry(data,reference,table):
    need(all(all(type(v) is int for v in row) for row in data['cells']),'Integer connectivity required')
    coords=list(map(tuple,data['coords']));cells=[[v-1 for v in row] for row in data['cells']]
    expected=dict(zip(map(bits,reference['coordinates_mm']),reference['node_tags']))
    need(len(coords)==15 and len(set(coords))==15 and len(expected)==15 and {bits(p) for p in coords}==set(expected),'Complete exact 15 coordinate rows')
    need(len(cells)==40 and all(len(r)==4 and len(set(r))==4 and all(type(v) is int and 0<=v<15 for v in r) for r in cells),'Complete valid 40 TET4 rows')
    source=[tuple(sorted(r)) for r in reference['positive_tetrahedra_node_tags']]
    signatures=[tuple(sorted(expected[bits(coords[v])] for v in r)) for r in cells]
    need(len(set(signatures))==40 and Counter(signatures)==Counter(source),'Complete source cell bijection without duplicates')
    need({v for row in cells for v in row}==set(range(15)),'No orphan imported node')
    exact_det=[determinant([[Fraction(x) for x in coords[v]] for v in row]) for row in cells]
    need(all(v>0 for v in exact_det) and sum(exact_det)/6==343,'All exact positive determinants and exact source volume343')
    faces=defaultdict(list)
    for i,row in enumerate(cells):
        for order in [(1,2,3),(0,3,2),(0,1,3),(0,2,1)]:
            face=[row[k] for k in order];faces[tuple(sorted(face))].append((i,oriented(face)))
    boundary={}
    for key,items in faces.items():
        need(len(items) in (1,2),'Tetrahedral manifold incidence')
        if len(items)==1:boundary[key]=items[0]
        else:need(items[1][1]==oriented(list(reversed(items[0][1]))),'Opposed internal face orientations')
    need(len(boundary)==12 and len({v for row in boundary for v in row})==8,'Exactly12 exterior faces and8 boundary nodes')
    need(Counter(oriented([expected[bits(coords[v])] for v in row]) for _,row in boundary.values())==Counter(oriented(r) for r in reference['outward_triangles_node_tags']),'Exact source outward boundary')
    selected=[]
    need(len(data['side_elements'])==len(data['side_numbers'])==12,'Complete sideset11')
    for e,s in zip(data['side_elements'],data['side_numbers']):
        need(type(e) is int and 1<=e<=40 and type(s) is int and s in table,'Valid sideset element/side indices')
        row=[cells[e-1][k] for k in table[s]];key=tuple(sorted(row))
        need(key in boundary and boundary[key]==(e-1,oriented(row)),'Source-bound sideset orientation and owning cell')
        selected.append(key)
    need(len(set(selected))==12 and set(selected)==set(boundary),'Complete exact sideset11 exterior coverage')
    return coords,cells,[source.index(k) for k in signatures]


def fields(data,node_rows,qp_rows,reference,card,table):
    tol=card['acceptance'];coords,cells,source_rows=geometry(data,reference,table);nodes=node_values(node_rows,coords)
    A=[[float(Fraction(x)) for x in row] for row in card['affine_gradient_A']];stress0=[[float(Fraction(x)) for x in row] for row in card['exact_constant_stress_MPa']]
    strain0=[[float(Fraction(x)) for x in row] for row in card['exact_constant_strain']];lam=float(Fraction(card['exact_Lame_MPa']['lambda']));mu=float(Fraction(card['exact_Lame_MPa']['mu']))
    maxima={k:0. for k in ['displacement_mm','CDF_CSV_displacement_mm','CDF_CSV_reaction_N','strain','stress_MPa','reaction_N']}
    def close(actual,expected,key,limit):
        need(math.isfinite(actual) and math.isfinite(expected),'Finite field comparison');maxima[key]=max(maxima[key],abs(actual-expected));need(abs(actual-expected)<=limit,'Field error: '+key)
    for i,p in enumerate(coords):
        record=nodes[bits(p)]
        for j in range(3):
            close(record['u'][j],dot(A[j],p),'displacement_mm',tol['maximum_displacement_error_mm'])
            close(data['nodal'][DISP[j]][i],record['u'][j],'CDF_CSV_displacement_mm',tol['maximum_Exodus_CSV_displacement_difference_mm'])
            close(data['nodal'][FORCE[j]][i],record['r'][j],'CDF_CSV_reaction_N',tol['maximum_reaction_error_N'])
    centroids=[tuple(math.fsum(coords[v][k] for v in row)/4 for k in range(3)) for row in cells]
    joined=join_qp(qp_rows,centroids,tol['maximum_qp_coordinate_error_mm']);reactions=[[0.]*3 for _ in coords];energy=qp_energy=0.;associations=[]
    for i,row in enumerate(cells):
        q=joined[i];V,eps,sigma,forces,U=p1_cell([coords[v] for v in row],[nodes[bits(coords[v])]['u'] for v in row],lam,mu);energy+=U
        for a,v in enumerate(row):
            for j in range(3):reactions[v][j]+=forces[a][j]
        density=0.
        for (a,b),suffix in zip(COMP,['xx','yy','zz','xy','xz','yz']):
            es=float(q['total_strain_'+suffix]);ss=float(q['stress_'+suffix]);density+=(1 if a==b else 2)*es*ss
            close(es,strain0[a][b],'strain',tol['maximum_strain_error']);close(eps[a][b],strain0[a][b],'strain',tol['maximum_strain_error'])
            close(ss,stress0[a][b],'stress_MPa',tol['maximum_stress_error_MPa']);close(sigma[a][b],stress0[a][b],'stress_MPa',tol['maximum_stress_error_MPa'])
        qp_energy+=.5*V*density
        associations.append({'observed_CSV_element_id':integer(q['elem_id']),'qp_id':0,'Exodus_cell_row0':i,'source_tetrahedron_tag':reference['tetrahedron_tags'][source_rows[i]],'centroid_mm':centroids[i]})
    for i,p in enumerate(coords):
        for j in range(3):close(nodes[bits(p)]['r'][j],reactions[i][j],'reaction_N',tol['maximum_reaction_error_N'])
    boundary_tags={v for row in reference['outward_triangles_node_tags'] for v in row}
    source_tags=dict(zip(map(bits,reference['coordinates_mm']),reference['node_tags']))
    free_forces=[abs(x) for p in coords if source_tags[bits(p)] not in boundary_tags for x in nodes[bits(p)]['r']]
    need(len(free_forces)==21 and max(free_forces)<=tol['maximum_reaction_error_N'],'All21 free-component forces vanish')
    total_force=[math.fsum(nodes[bits(p)]['r'][j] for p in coords) for j in range(3)];total_moment=[math.fsum(cross(p,nodes[bits(p)]['r'])[j] for p in coords) for j in range(3)]
    need(max(map(abs,total_force))<=tol['maximum_force_balance_N'] and max(map(abs,total_moment))<=tol['maximum_moment_balance_N_mm'],'Total force/moment equilibrium')
    work=math.fsum(dot(nodes[bits(p)]['u'],nodes[bits(p)]['r']) for p in coords);expected_energy=float(Fraction(card['exact_total_elastic_energy_N_mm']));expected_work=float(Fraction(card['exact_boundary_work_N_mm']))
    need(all(math.isfinite(x) and x>0 for x in [energy,qp_energy,work,expected_energy,expected_work]),'Positive finite elastic energy and work')
    errors=[abs(energy-expected_energy)/expected_energy,abs(qp_energy-expected_energy)/expected_energy,abs(work-expected_work)/expected_work,abs(work-2*energy)/(2*energy)]
    need(max(errors)<=tol['relative_energy_and_work_error'],'Independent P1/native tensor/reaction work identity')
    return {'complete_displacement_values':45,'complete_reaction_values':45,'complete_centroid_tensor_records':40,'maximum_errors':maxima,'P1_energy_N_mm':energy,'native_QP_energy_N_mm':qp_energy,'nodal_work_N_mm':work,'energy_and_work_relative_errors':errors,'total_force_N':total_force,'total_moment_N_mm':total_moment,'cell_QP_associations':associations,'node_CSV_associations':[{'Exodus_row0':i,'CSV_id':nodes[bits(p)]['observed_id'],'source_tag':reference['node_tags'][reference['coordinates_mm'].index(list(p))]} for i,p in enumerate(coords)],'PETSc_row_to_node_map_assumed':False}


def algebra(A,P,F,y,tolerance):
    need(len(A)==len(P)==len(F)==len(y)==45 and all(len(r)==45 for r in A+P),'Complete45DOF algebra exports')
    need(all(math.isfinite(x) for row in A+P for x in row) and all(math.isfinite(x) for x in F+y),'Finite complete algebra')
    fn=norm(F);an=norm(x for r in A for x in r);need(fn>0 and an>0,'Nonzero algebraic problem')
    residual=norm(math.fsum(A[i][j]*y[j] for j in range(45))-F[i] for i in range(45))/fn;ap=norm(A[i][j]-P[i][j] for i in range(45) for j in range(45))/an
    need(residual<=tolerance and ap<=tolerance,'J*y=F and A=P criteria')
    identity=[i for i in range(45) if all(A[i][j]==float(i==j) for j in range(45))]
    need(len(identity)==24,'24 exact Dirichlet rows and21 free rows required')
    return {'relative_Jy_minus_F':residual,'relative_A_minus_P':ap,'identity_rows':identity,'free_rows':21,'Newton_convention':'J*y=F; zero initial state; u_new=-y. Algebra rows are not assigned to spatial DOFs.','post_update_vector_in_PETSc_row_order':[-x for x in y],'full_node_to_PETSc_row_map_established':False,'SPD_or_CG_claimed':False}


def read_exodus(path):
    from scipy.io import netcdf_file
    import scipy
    import numpy
    need(scipy.__version__=='1.17.1' and numpy.__version__=='2.2.6','Existing reviewed SciPy/NumPy versions required')
    with Path(path).open('rb') as stream:need(stream.read(4)==b'CDF\x02','Recorded CDF2 format required')
    with netcdf_file(str(path),mode='r',mmap=False,maskandscale=False) as dataset:
        dims=dataset.dimensions
        need(all(dims.get(k)==v for k,v in {'num_dim':3,'num_nodes':15,'num_elem':40,'num_el_blk':1,'num_side_sets':1,'num_nod_var':6}.items()),'Exact15/40/oneblock/sixfield dimensions')
        def array(name,shape):
            need(name in dataset.variables,'Missing Exodus variable: '+name);value=dataset.variables[name].data.copy();need(value.shape==shape,'Exodus shape: '+name);return value.tolist()
        def text(row):return b''.join(row).split(b'\0',1)[0].decode('ascii').strip()
        coords=list(map(list,zip(*(array('coord'+axis,(15,)) for axis in 'xyz'))));cells=array('connect1',(40,4))
        kind=getattr(dataset.variables['connect1'],'elem_type',b'');need(isinstance(kind,bytes) and kind.decode().strip().upper() in {'TET4','TETRA','TETRA4'},'ExplicitTET4 type')
        need(array('ss_prop1',(1,))==[11] and array('ss_status',(1,))==[1],'Active sideset11')
        names=dataset.variables.get('ss_names');need(names is not None and names.data.shape[0]==1 and text(names.data.copy().tolist()[0])=='all_boundary','Exact sideset name')
        times=dataset.variables['time_whole'].data.copy().tolist();need(times and all(math.isfinite(v) for v in times) and all(a<b for a,b in zip(times,times[1:])),'Finite ordered export times')
        node_map=array('node_num_map',(15,));element_map=array('elem_num_map',(40,))
        need(all(type(v) is int and v>0 for v in node_map+element_map) and len(set(node_map))==15 and len(set(element_map))==40,'Complete observed Exodus maps')
        names=dataset.variables.get('name_nod_var');need(names is not None and names.data.shape[0]==6,'Six nodal field names');names=[text(row) for row in names.data.copy().tolist()]
        need(set(names)==set(DISP+FORCE) and len(set(names))==6,'Exactly three displacements plus three reactions by name')
        nodal={name:array('vals_nod_var'+str(i+1),(len(times),15))[-1] for i,name in enumerate(names)}
        return {'coords':coords,'cells':cells,'side_elements':array('elem_ss1',(12,)),'side_numbers':array('side_ss1',(12,)),'nodal':nodal,'observed_external_node_map':node_map,'observed_external_element_map':element_map,'times':times,'dimensions':dict(dims),'element_type':kind.decode()}


def matrix(path):
    data=blocks(path,3);need(len(data)==1,'One complete matrix block');result=[[0.]*45 for _ in range(45)];seen=set()
    for i,j,v in data[0]:
        need(i==int(i) and j==int(j) and 1<=i<=45 and 1<=j<=45 and (int(i),int(j)) not in seen,'Unique in-range matrix entry');seen.add((int(i),int(j)));result[int(i)-1][int(j)-1]=v
    need(all((i,i) in seen for i in range(1,46)),'All45 diagonal entries required');return result


def vector(path):
    data=blocks(path,1);need(len(data)==1 and len(data[0])==45,'One complete45entry vector');return [r[0] for r in data[0]]


def assess(contract_path,digest,output):
    import sys
    need(sha(contract_path)==digest,'Exact actual assessment contract');c=json.loads(Path(contract_path).read_text())
    need(c['assessment_authorized'] is True and c['root_and_peer_review_complete'] is True,'Separate actual assessment authority')
    output=Path(output);need(str(output.resolve())==c['expected_output'] and not output.exists() and not output.is_symlink(),'Fresh exact assessment path')
    need(sha(__file__)==c['assessor_sha256'] and sha(sys.executable)==c['python_sha256'],'Selected checker/interpreter identities')
    for name,h in c['input_sha256'].items():need(sha(name)==h,'Input drift before assessment: '+name)
    directory=Path(c['native_directory']);native=json.loads((directory/'native-execution.json').read_text())
    need(sha(directory/'native-execution.json')==c['native_receipt_sha256'] and native['contract_sha256']==c['native_contract_sha256'],'Stopped native receipt/contract associations')
    need(native['native_execution_completed'] is True and native['returncode']==0 and native['process_reaped'] is True and native['controller_error'] is None and native['inputs_unchanged'] and native['binary_and_runtime_unchanged'],'Successful stopped native invocation')
    need(native['artifact_sha256']==c['native_artifact_sha256'],'Complete frozen native artifact map')
    for name,h in native['artifact_sha256'].items():
        rel=Path(name);need(not rel.is_absolute() and '..' not in rel.parts and not (directory/rel).is_symlink() and sha(directory/rel)==h,'Exact safe native artifact: '+name)
    need(sha(c['card'])==CARD_SHA,'Exact fictitious affine card');card=json.loads(Path(c['card']).read_text());reference=json.loads(Path(c['reference']).read_text())
    required=[__file__,c['card'],c['reference'],c['primary_side_source'],str(directory/'native-execution.json'),str(directory/'native.log'),str(directory/'frozen-contract.json')]
    for field in ['Exodus_file','nodal_CSV','fields_CSV','operator','preconditioner','rhs','correction','ksp']:
        path=Path(c[field]);need(path.parent.resolve()==directory.resolve() and path.name in native['artifact_sha256'],'Consumed field must be original native artifact: '+field)
        required.append(str(path))
    need({str(Path(p).resolve()) for p in required}<={str(Path(p).resolve()) for p in c['input_sha256']},'All consumed fields/reference/source/primary/receipt must be direct-pinned')
    need(sha(directory/'frozen-contract.json')==c['native_contract_sha256'],'Exact native contract file')
    need('native.log' in native['artifact_sha256'] and (directory/'native.log').read_text().count('Solve Converged!')==1,'One actual converged native solve')
    need(c['primary_side_source_sha256']=='9cedc3c636874dddd4c750ce2a4acd0250eb9b981c5c471630944803a5549047','Exact reviewed SEACAS side-table source')
    table=side_table_from_primary(c['primary_side_source'],c['primary_side_source_sha256']);data=read_exodus(c['Exodus_file'])
    result=fields(data,rows(c['nodal_CSV']),rows(c['fields_CSV']),reference,card,table)
    result.update(algebra=algebra(matrix(c['operator']),matrix(c['preconditioner']),vector(c['rhs']),vector(c['correction']),card['acceptance']['relative_saved_algebraic_residual']),actual_solver=actual_settings(Path(c['ksp']).read_text()))
    for name,h in c['input_sha256'].items():need(sha(name)==h,'Input drift after assessment: '+name)
    need(sha(contract_path)==digest,'Assessment contract drift')
    result.update(status='fixed_imported_affine_elastic_cube_observations_passed',passed=True,contract_sha256=digest,assessor_sha256=sha(__file__),native_receipt_sha256=c['native_receipt_sha256'],input_sha256=c['input_sha256'],Exodus_times=data['times'],Exodus_node_map=data['observed_external_node_map'],Exodus_element_map=data['observed_external_element_map'],Exodus_dimensions=data['dimensions'],complete_source_geometry_and_sideset=True,all_inputs_unchanged=True,qualification=card['qualification'],scope='One fictitious affine software cube only; no head, material, convergence or physical qualification.')
    with output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assess(args.contract,args.contract_sha256,args.output)

