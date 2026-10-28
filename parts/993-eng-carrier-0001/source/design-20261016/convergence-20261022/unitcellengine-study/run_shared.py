"""Audit the pinned upstream six-RHS implementation with consistent ersatz energy."""
import hashlib, importlib.util, itertools, json, resource, sys, time
from pathlib import Path
import numpy as np
import pypardiso

N=int(sys.argv[1]); floor=float(sys.argv[2]); kind=sys.argv[3]; out=Path(sys.argv[4]); adapted=sys.argv[5]=='adapted'
assert N in [4,16,64] and floor in [1.,1e-4,1e-6] and kind in ['solid','gyroid'] and not out.exists()
resource.setrlimit(resource.RLIMIT_AS,(48*1024**3,48*1024**3));out.mkdir();started=time.monotonic()
source=Path(__file__).parent/'source/src/unitcellengine/analysis/internal.py';raw=source.read_text()
old='scaling = (detJs[ax].T * rhos[einds][ax])[ax, ax].transpose((2, 0, 3, 1))'
new='scaling = (detJs[ax].T * (scalingMin + (1 - scalingMin) * rhos[einds])[ax])[ax, ax].transpose((2, 0, 3, 1))'
assert raw.count(old)==1
text=raw.replace(old,new) if adapted else raw
copy=out/'operator.py';copy.write_text(text)
spec=importlib.util.spec_from_file_location('audited_operator',copy);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
E=107000.;nu=.31;C=module.isotropicC(E,nu);perm=[0,1,2,3,5,4]
k,j,i=np.indices((N+1,)*3);coords=np.column_stack([i.ravel(),j.ravel(),k.ravel()])/N
k,j,i=np.indices((N,)*3);base=(i+(N+1)*(j+(N+1)*k)).ravel();e2n=base[:,None]+np.array([0,1,N+2,N+1,(N+1)**2,(N+1)**2+1,(N+1)**2+N+2,(N+1)**2+N+1])
x=2*np.pi*(i+.5)/N;y=2*np.pi*(j+.5)/N;z=2*np.pi*(k+.5)/N
solid=np.ones(N**3,dtype=bool) if kind=='solid' else (abs(np.sin(x)*np.cos(y)+np.sin(y)*np.cos(z)+np.sin(z)*np.cos(x))<=.6170021750539874).ravel()
phase=np.where(solid,1.,floor) if kind=='gyroid' else np.full(N**3,floor)
rhos=(phase-1e-8)/(1-1e-8)
np.savez(out/'mesh.npz',nodes=np.column_stack([np.arange(len(coords)),coords]),nsdf=np.zeros(len(coords)),ninds=np.ones(len(coords),bool),e2n=e2n,nels=np.array([N]*3),erhos=rhos,einds=np.ones(N**3,bool))
solve=pypardiso.PyPardisoSolver.solve;calls=[]
def recorded(self,A,b,*args,**kwargs):
 assert self.mtype==2 and b.ndim==2 and b.shape[1]==6
 t=time.monotonic();result=solve(self,A,b,*args,**kwargs)
 residual=A@result+A.T@result-A.diagonal()[:,None]*result-b
 errors=np.linalg.norm(residual,axis=0)/np.maximum(np.linalg.norm(b,axis=0),1e-12)
 # A uniform medium has only floating-point assembly noise on its zero RHS.
 absolute=np.linalg.norm(residual,axis=0);assert np.all((errors<=1e-7)|(absolute<=1e-9))
 calls.append(dict(matrix_shape=list(A.shape),rhs_shape=list(b.shape),matrix_type=self.mtype,relative_residuals=errors.tolist(),absolute_residuals=absolute.tolist(),elapsed_seconds=time.monotonic()-t))
 (out/'solve-record.json').write_text(json.dumps(calls,indent=2));return result
pypardiso.PyPardisoSolver.solve=recorded
CH=module.homogenization(out/'mesh.npz',C,filename=out/'result.npz',solver='direct',parallel=False)
assert len(calls)==1
data=np.load(out/'result.npz');xi=np.stack([data[f'xi{q+1}'] for q in range(6)],axis=-1).transpose(1,0,2)
assert xi.shape==(len(coords),3,6) and np.isfinite(xi).all()
# Independent trilinear shape gradients, all eight Gauss points, engineering shear order.
signs=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])
Bs=[]
for gp in itertools.product([-1/np.sqrt(3),1/np.sqrt(3)],repeat=3):
 grad=np.empty((8,3))
 for a in range(3):
  other=[b for b in range(3) if b!=a];grad[:,a]=signs[:,a]*np.prod(1+signs[:,other]*np.array(gp)[other],axis=1)*N/4
 B=np.zeros((6,24))
 for q in range(8):
  gx,gy,gz=grad[q];B[:,3*q:3*q+3]=[[gx,0,0],[0,gy,0],[0,0,gz],[gy,gx,0],[0,gz,gy],[gz,0,gx]]
 Bs.append(B)
Bs=np.array(Bs);Berror=float(np.max(abs(Bs-data['B'])));assert Berror<1e-11
mean=np.zeros((6,6));energy=np.zeros(6);forces=np.zeros((len(coords),3,6))
stressfile=np.lib.format.open_memmap(out/'stress-all-ip.npy',mode='w+',dtype='float64',shape=(N**3,8,6,6))
for start in range(0,N**3,2048):
 ids=slice(start,min(start+2048,N**3));local=xi[e2n[ids]].reshape(-1,24,6)
 strain=np.eye(6)[None,None,:,:]-np.einsum('gsa,eac->egsc',Bs,local)
 stress=np.einsum('st,egtc->egsc',C,strain)*phase[ids,None,None,None]
 stressfile[ids]=stress;mean+=stress.sum(axis=(0,1))/(8*N**3)
 energy+=np.einsum('egsc,egsc->c',strain,stress)/(16*N**3)
 nodal=np.einsum('gsa,egsc->eac',Bs,stress)/(8*N**3)
 for q in range(8):np.add.at(forces,e2n[ids,q],nodal[:,3*q:3*q+3,:])
stressfile.flush();del stressfile
energy_error=abs(energy-.5*np.diag(CH))/np.maximum(abs(.5*np.diag(CH)),1e-20)
tensor_error=float(np.linalg.norm(mean-CH)/np.linalg.norm(mean))
symmetry=float(np.linalg.norm(CH-CH.T)/np.linalg.norm(CH))
k,j,i=np.indices((N+1,)*3);masters=(i%N+N*(j%N+N*(k%N))).ravel();periodic=np.zeros((N**3,3,6));np.add.at(periodic,masters,forces)
equilibrium=np.max(abs(periodic),axis=(0,1));pbc=float(np.max(abs(xi-xi[((i%N)+(N+1)*((j%N)+(N+1)*(k%N))).ravel()])))
vals,vecs=np.linalg.eigh(C);inv=(vecs*(1/np.sqrt(vals)))@vecs.T;eigs=np.linalg.eigvalsh(inv@((CH+CH.T)/2)@inv)
np.savez_compressed(out/'fields.npz',xi=xi,physical_forces=forces)
report=dict(status='independent_operator_energy_checks_passed' if adapted else 'upstream_regularization_control',resolution=N,void_relative_stiffness=floor,kind=kind,adapted=adapted,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),adapted_source_sha256=hashlib.sha256(copy.read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),solid_fraction=float(solid.mean()),effective_C_MPa=CH[np.ix_(perm,perm)].tolist(),dense_C_MPa=C[np.ix_(perm,perm)].tolist(),relative_energy_residuals=energy_error.tolist(),independent_stress_average_tensor_error=tensor_error,relative_antisymmetry=symmetry,normalized_stiffness_eigenvalues=eigs.tolist(),minimum_tensor_stiffness_ratio=float(eigs.min()),independent_B_max_error=Berror,periodic_corrector_error=pbc,periodic_force_max_errors=equilibrium.tolist(),solve_calls=calls,elapsed_seconds=time.monotonic()-started,carrier_convergence_demonstrated=False,cellular_part_generated=False,unitcell_mesh_convergence_demonstrated=False)
if adapted:
 assert max(energy_error)<=1e-4 and tensor_error<=1e-10 and symmetry<=1e-4 and pbc<=1e-8 and max(equilibrium)<=1e-7
 assert eigs.min()>0 and eigs.max()<=float(phase.mean())+1e-4
 if kind=='solid':assert np.linalg.norm(CH-floor*C)/np.linalg.norm(floor*C)<=1e-5
(out/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
