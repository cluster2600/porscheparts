"""Solve and independently audit all six strain cases on an explicit periodic T10 domain."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import assess_native_P2 as quadratic
import periodic_interface_topology as topology
import periodic_interface_mesh as mesh_audit
from periodic_interface_mesh import audit_periodicity,audit_t10,EDGES


def ccx_number(value):
    if not np.isfinite(value):raise ValueError('Finite CalculiX field required')
    # CalculiX 2.21 input fields are limited to 20 characters, including a minus sign.
    for precision in range(17,11,-1):
        text=format(float(value),f'.{precision}g')
        if len(text)<=20:return text
    raise ValueError('CalculiX numeric field exceeds 20 characters')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--qualification',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();expected='95e9b61985446b686f5f146d1a947101a5ec8ac86fef0cf9e308d25f817c918a';assert sha(a.binary)==expected
    contract=json.loads(a.contract.read_text());assert contract['maximum_relative_energy_residual']==1e-4 and contract['maximum_periodic_displacement_error']==1e-8 and contract['per_case_seconds']==600
    rss=contract['per_case_RSS_GiB'];assert type(rss)is int and rss in [12,24]
    generation=json.loads((a.mesh/'assessment.json').read_text());assert generation['status']=='explicit_periodic_T10_research_mesh_audited'and generation['geometry']['whole_simplex_relative_Jacobian_bound']<=1e-8
    if generation['kind']=='gyroid':
        assert sha(a.mesh/'cell.step')==contract['reference_geometry_sha256'] and a.qualification
        q=json.loads(a.qualification.read_text());assert q['kind']=='cube'and q['status']=='explicit_periodic_T10_six_strain_checks_passed'and q['relative_analytic_solid_tensor_error']<=1e-5 and len(q['cases'])==6 and all(sha(f)in q['source_sha256'].values()for f in [Path(__file__),Path(quadratic.__file__),Path(topology.__file__),Path(mesh_audit.__file__),Path(__file__).with_name('run_local_ccx_solver_parallel.py')]) and expected in q['source_sha256'].values()
    data=np.load(a.mesh/'transport.npz');points=np.array([[float(ccx_number(v))for v in row]for row in data['points']]);cells=data['cells'];assert list(map(tuple,quadratic.EDGES))==EDGES;audit_periodicity(points);wire_geometry=audit_t10(points,cells);assert wire_geometry['whole_simplex_relative_Jacobian_bound']<=1e-8
    topology.audit_facets(points,cells)
    phys=len(points);refs=np.arange(phys+1,phys+4);upper=abs(points-.5)<=1e-8;slaves=np.flatnonzero(upper.any(1));wrapped=points[slaves]-upper[slaves];distance,masters=cKDTree(points).query(wrapped);assert max(distance)<=1e-8 and not upper[masters].any()
    master=np.arange(phys);master[slaves]=masters;active=np.unique(master);ids=np.full(phys,-1,int);ids[active]=np.arange(len(active));mapped=ids[master[cells]];row=np.repeat(mapped[:,0],9);col=mapped[:,1:].ravel();graph=coo_matrix((np.ones(len(row)),(row,col)),shape=(len(active),len(active)));components=connected_components(graph,directed=False,return_labels=False);assert components==1
    pin=int(active[0]);E=107000.;nu=.31;amp=.001;assert E==contract['material_E_MPa']and nu==contract['material_nu']and amp==contract['macroscopic_engineering_strain_amplitude'];a.output.mkdir();start=time.monotonic()
    provenance={str(f):sha(f)for f in [Path(__file__),a.contract,a.binary,a.mesh/'transport.npz',a.mesh/'cell.step',a.mesh/'assessment.json',Path(quadratic.__file__),Path(topology.__file__),Path(mesh_audit.__file__),Path(__file__).with_name('run_local_ccx_solver_parallel.py')]+([a.qualification]if a.qualification else[])};(a.output/'contract.json').write_text(json.dumps(dict(study_contract=contract,source_sha256=provenance,periodic_components=int(components),physical_nodes=phys,tetrahedra=len(cells),amplitude=amp,serialized_geometry=wire_geometry),indent=2))
    x=points[cells[:,:4]];det=np.linalg.det((x[:,1:]-x[:,0,None,:]).transpose(0,2,1));weights=det/24;volume=float(det.sum()/6);assert abs(volume-generation['geometry']['volume_mm3'])<1e-10
    base=['*HEADING','Explicit normalized periodic T10 research cell','*NODE']+[f'{i+1},'+','.join(ccx_number(v)for v in point)for i,point in enumerate(points)]
    base +=[f'{int(ref)},'+','.join(map(str,2*np.eye(3)[axis]))for axis,ref in enumerate(refs)]+['*NSET,NSET=ALLN,GENERATE',f'1,{phys+3},1','*ELEMENT,TYPE=C3D10,ELSET=ALLE']+[str(i+1)+','+','.join(map(str,cell+1))for i,cell in enumerate(cells)]
    base+=['*MATERIAL,NAME=TI','*ELASTIC',f'{E},{nu}','*SOLID SECTION,ELSET=ALLE,MATERIAL=TI']
    for s,m in zip(slaves,masters):
        for component in range(3):
            terms=[(int(s+1),component+1,1),(int(m+1),component+1,-1)]+[(int(refs[axis]),component+1,-1)for axis in np.flatnonzero(upper[s])];base+=['*EQUATION',str(len(terms))]+[','.join(map(str,t))for t in terms]
    C=np.empty((6,6));cases=[]
    for mode in range(6):
        H=np.zeros((3,3))
        if mode<3:H[mode,mode]=amp
        else:
            i,j=[(0,1),(0,2),(1,2)][mode-3];H[i,j]=H[j,i]=amp/2
        deck=a.output/f'case-{mode}.inp';lines=base+['*STEP','*STATIC','1,1','*BOUNDARY',f'{pin+1},1,3,0']+[f'{int(refs[axis])},{component+1},{component+1},{H[component,axis]:.17g}'for axis in range(3)for component in range(3)]+['*NODE PRINT,NSET=ALLN','U,RF','*EL PRINT,ELSET=ALLE','S','*END STEP'];deck.write_text('\n'.join(lines)+'\n');execution=a.output/f'case-{mode}'
        subprocess.run([sys.executable,str(Path(__file__).parent/'run_local_ccx_solver_parallel.py'),'--binary',str(a.binary),'--expected-binary',expected,'--deck',str(deck),'--output',str(execution),'--seconds','600','--rss-gib',str(rss),'--solver-threads','8'],check=True)
        receipt=json.loads((execution/'actual-terminal.json').read_text());dat=execution/'case/job.dat';assert receipt['actual_returncode']==0 and receipt['process_reaped']and receipt['inputs_unchanged']and receipt['solver_finished_marker']and sha(dat)==receipt['output_sha256']['job.dat']
        fields={k:[]for k in ['displacements','forces','stresses']};current=None
        for line in dat.read_text().splitlines():
            s=line.strip()
            for key in fields:
                if s.startswith(key+' ('):assert not fields[key];current=key
            v=s.split()
            if current and len(v)==(8 if current=='stresses'else 4)and v[0].isdigit():fields[current].append(v)
        assert len(fields['displacements'])==len(fields['forces'])==phys+3 and len(fields['stresses'])==4*len(cells)
        for key in ['displacements','forces']:assert [int(v[0])for v in fields[key]]==list(range(1,phys+4))
        assert [(int(v[0]),int(v[1]))for v in fields['stresses']]==[(i+1,j+1)for i in range(len(cells))for j in range(4)]
        U=np.array([list(map(float,v[1:]))for v in fields['displacements']]);F=np.array([list(map(float,v[1:]))for v in fields['forces']]);S=np.array([list(map(float,v[2:]))for v in fields['stresses']]).reshape(-1,4,6);assert all(np.isfinite(v).all()for v in [U,F,S])
        pbc=float(abs(U[slaves]-U[masters]-upper[slaves]@H.T).max());assert pbc<=1e-8 and abs(U[refs-1]-H.T).max()<=1e-8
        mean=np.einsum('e,egc->c',weights,S);C[:,mode]=mean/amp;internal,quadratic_volume=quadratic.stress_energy(points,cells,S,E,nu,np);macro=.5*mean[mode]*amp;work=.5*float(np.sum(F[:phys]*U[:phys]));energy_error=abs(internal-macro)/abs(macro);work_error=abs(work-macro)/abs(macro)
        assert energy_error<=1e-4 and work_error<=1e-4 and abs(quadratic_volume-volume)/volume<=1e-8
        affine_error=float(abs(U[:phys]-(points-points[pin])@H.T).max())if generation['kind']=='cube'else None
        if affine_error is not None:assert affine_error<=1e-8
        cases.append(dict(mode=mode,pbc_max_mm=pbc,internal_energy_Nmm=internal,macro_energy_Nmm=macro,physical_RF_work_Nmm=work,relative_energy_residual=energy_error,relative_boundary_work_error=work_error,solid_control_affine_U_max_error_mm=affine_error,physical_nodes=phys,stress_integration_points=4*len(cells)));(a.output/'progress.json').write_text(json.dumps(cases,indent=2));np.savez_compressed(a.output/f'case-{mode}-fields.npz',U=U,F=F,S=S);print('case passed',mode,energy_error,work_error,flush=True)
    G=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));dense=np.zeros((6,6));dense[:3,:3]=lam;dense[np.arange(3),np.arange(3)]+=2*G;dense[3:,3:]=np.eye(3)*G;sym=float(np.linalg.norm(C-C.T)/np.linalg.norm(C));assert sym<=1e-4;d,v=np.linalg.eigh(dense);inv=(v*(1/np.sqrt(d)))@v.T;eigen=np.linalg.eigvalsh(inv@((C+C.T)/2)@inv);assert eigen.min()>0 and eigen.max()<=volume+1e-4
    error=float(np.linalg.norm(C-dense)/np.linalg.norm(dense))if generation['kind']=='cube'else None
    if error is not None:assert error<=1e-5
    report=dict(status='explicit_periodic_T10_six_strain_checks_passed',kind=generation['kind'],effective_C_MPa=C.tolist(),dense_C_MPa=dense.tolist(),solid_fraction=volume,relative_antisymmetry=sym,normalized_stiffness_eigenvalues=eigen.tolist(),minimum_tensor_stiffness_ratio=float(eigen.min()),relative_analytic_solid_tensor_error=error,cases=cases,elapsed_seconds=time.monotonic()-start,source_sha256=provenance,unitcell_mesh_convergence_demonstrated=False,carrier_convergence_demonstrated=False,cellular_carrier_generated=False,void_phase='absent; traction-free internal surfaces');(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
