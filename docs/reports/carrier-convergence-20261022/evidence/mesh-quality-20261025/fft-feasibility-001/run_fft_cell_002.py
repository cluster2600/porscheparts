from pathlib import Path
import hashlib,json,sys,time
import numpy as np
import _muGrid
import _muFFT
import _muSpectre as mu
config=Path(sys.argv[1]);p=json.loads(config.read_text());out=Path(sys.argv[2]);assert not out.exists();N=p['resolution'];kind=p['kind'];floor=p['void_relative_stiffness'];threshold=.6170021750539874;assert type(N)is int and 5<=N<=129 and N%2==1 and kind in ['solid','laminate','gyroid']and 1e-8<=floor<=.01;out.mkdir();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();E=107000.;nu=.31;amp=.001
(out/'contract.json').write_text(json.dumps(dict(parameters=p,source_sha256=sha(Path(__file__)),parameters_sha256=sha(config),method='muSpectre small-strain Fourier-Galerkin periodic voxel experiment; separate from C3D8 finite elements',cg_relative_tolerance=1e-10,newton_tolerance=1e-10,equilibrium_tolerance=1e-10,maximum_cg_iterations=10000,relative_projected_stress_limit=1e-7,relative_energy_limit=1e-4,relative_hooke_limit=1e-8,mean_strain_absolute_limit=1e-9,relative_control_tensor_limit=1e-5,relative_tensor_antisymmetry_limit=1e-4,carrier_geometry_changed=False),indent=2))
C=np.empty((6,6));rows=[];phase=None
for mode in range(6):
 started=time.monotonic();cell=mu.cell.PocketFFTCellFactory([N]*3,[1.]*3,mu.Formulation.small_strain,[_muFFT.FourierDerivative(3,i)for i in range(3)],[1.]);hard=mu.material.MaterialLinearElastic1_3d.make(cell,'solid',E,nu);soft=mu.material.MaterialLinearElastic1_3d.make(cell,'void',E*floor,nu);solid=np.zeros(N**3,dtype=bool);seen=np.zeros(N**3,dtype=bool)
 for index,coord in cell.pixels.enumerate():
  assert 0<=index<N**3 and not seen[index];seen[index]=True;x,y,z=2*np.pi*(np.array(coord)+.5)/N;value=True if kind=='solid'else(coord[0]<N//2 if kind=='laminate'else abs(np.sin(x)*np.cos(y)+np.sin(y)*np.cos(z)+np.sin(z)*np.cos(x))<=threshold);solid[index]=value;(hard if value else soft).add_pixel(index)
 assert seen.all()
 if phase is None:phase=solid.copy()
 else:assert np.array_equal(phase,solid)
 rho=float(solid.mean());cell.initialise();H=np.zeros((3,3))
 if mode<3:H[mode,mode]=amp
 else:
  i,j=[(0,1),(0,2),(1,2)][mode-3];H[i,j]=H[j,i]=amp/2
 solver=mu.solvers.KrylovSolverCG(cell,1e-10,10000,_muGrid.Verbosity.Silent);result=mu.solvers.newton_cg(cell,H,solver,1e-10,1e-10,_muGrid.Verbosity.Silent);assert result.success,(result.status,result.message)
 strain=cell.strain.array().copy();stress=cell.stress.array().copy();assert strain.shape==stress.shape and strain.shape[:2]==(3,3)and strain.size==9*N**3 and all(np.isfinite(x).all()for x in [strain,stress]);eps=strain.reshape(3,3,-1,order='F');sig=stress.reshape(3,3,-1,order='F');assert np.max(abs(eps.mean(2)-H))<=1e-9
 moduli=np.where(solid,E,E*floor);G=moduli/(2*(1+nu));lam=moduli*nu/((1+nu)*(1-2*nu));predicted=2*G[None,None,:]*eps+np.eye(3)[:,:,None]*(lam*np.trace(eps,axis1=0,axis2=1))[None,None,:];hooke=float(np.max(abs(predicted-sig))/max(1.,float(abs(sig).max())));assert hooke<=1e-8
 projected=np.asarray(cell.project(np.asfortranarray(stress)));residual=float(np.linalg.norm(projected)/max(1.,np.linalg.norm(stress)));assert residual<=1e-7
 voigt=np.stack([sig[0,0],sig[1,1],sig[2,2],sig[0,1],sig[0,2],sig[1,2]]);average=voigt.mean(1);C[:,mode]=average/amp;d=voigt[:3];s=voigt[3:];density=(np.sum(d*d,0)-2*nu*(d[0]*d[1]+d[1]*d[2]+d[2]*d[0])+2*(1+nu)*np.sum(s*s,0))/(2*moduli);energy=float(density.mean());macro=.5*average[mode]*amp;work=.5*float(np.mean(np.sum(eps*sig,axis=(0,1))));err=abs(energy-macro)/macro;assert err<=1e-4 and abs(work-macro)/macro<=1e-4;file=out/f'mode-{mode}-fields.npz';np.savez_compressed(file,strain=strain,stress=stress,solid=solid);row=dict(mode=mode,solid_fraction=rho,cg_iterations=int(result.nb_fev),solver_equilibrium_norm=float(result.equil_norm),relative_projected_stress=residual,relative_hooke_residual=hooke,independent_stress_energy=energy,macro_energy=macro,stress_strain_work=work,relative_energy_residual=err,fields_sha256=sha(file),elapsed_seconds=time.monotonic()-started);rows.append(row);(out/'progress.json').write_text(json.dumps(rows,indent=2));print(row,flush=True)
G=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));dense=np.zeros((6,6));dense[:3,:3]=lam;dense[np.arange(3),np.arange(3)]+=2*G;dense[3:,3:]=np.eye(3)*G;expected=dense.copy()
if kind=='laminate':
 mod=np.array([E,E*floor]);w=np.array([rho,1-rho]);g=mod/(2*(1+nu));l=mod*nu/((1+nu)*(1-2*nu));A=l+2*g;a=np.sum(w/A);b=np.sum(w*l/A);d=np.sum(w*(A-l*l/A));e=np.sum(w*(l-l*l/A));expected=np.zeros((6,6));expected[0,0]=1/a;expected[0,1:3]=expected[1:3,0]=b/a;expected[1,1]=expected[2,2]=d+b*b/a;expected[1,2]=expected[2,1]=e+b*b/a;expected[3,3]=expected[4,4]=1/np.sum(w/g);expected[5,5]=np.sum(w*g)
control_error=float(np.linalg.norm(C-expected)/np.linalg.norm(expected))if kind!='gyroid'else None
if kind!='gyroid':assert control_error<=1e-5
antisym=float(np.linalg.norm(C-C.T)/np.linalg.norm(C));assert antisym<=1e-4;ev,V=np.linalg.eigh(dense);inv=(V*(1/np.sqrt(ev)))@V.T;values=np.linalg.eigvalsh(inv@((C+C.T)/2)@inv);assert values.min()>0 and values.max()<=rho+(1-rho)*floor+1e-4;report=dict(status='six_strain_FFT_cell_controls_and_energy_passed',kind=kind,resolution=N,solid_fraction=rho,void_relative_stiffness=floor,effective_C_MPa=C.tolist(),dense_C_MPa=dense.tolist(),analytic_control_C_MPa=expected.tolist()if kind!='gyroid'else None,relative_control_tensor_error=control_error,relative_antisymmetry=antisym,normalized_stiffness_eigenvalues=values.tolist(),minimum_tensor_stiffness_ratio=float(values.min()),cases=rows,carrier_geometry_changed=False,cellular_part_generated=False,unitcell_stiffness_converged=False,source_sha256=sha(Path(__file__)));(out/'assessment.json').write_text(json.dumps(report,indent=2));print(report['status'],control_error,flush=True)
