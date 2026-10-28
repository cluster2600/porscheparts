"""Generate and independently audit a bounded periodic six-strain cell experiment."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
import argparse
import platform
SOURCE=Path(__file__).resolve().parent
p=argparse.ArgumentParser('Six-strain periodic C3D8 cell study; local Mac solver, no carrier geometry change')
p.add_argument('--parameters',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--expected-binary',required=True);p.add_argument('--solid-control',action='store_true');args=p.parse_args()
config_path=args.parameters;config=json.loads(config_path.read_text());OUT=args.output;N=config['resolution'];E=107000.;nu=.31;amp=.001;floor=config['void_relative_stiffness'];threshold=config['threshold'];B=args.binary.resolve();identity=hashlib.sha256(B.read_bytes()).hexdigest()
if platform.system()!='Darwin' or OUT.exists() or type(N)is not int or not 4<=N<=64 or not 1e-8<=floor<=1e-2 or not 0<threshold<2 or identity!=args.expected_binary:raise ValueError('Fresh bounded Mac fixture and matching binary identity required')
OUT.mkdir()

contract=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parameters_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),parameters=config,geometry='periodic gyroid sheet in a full solid/ersatz-void C3D8 grid',grid=N,amplitude=amp,E_MPa=E,nu=nu,periodic_displacement_residual_limit_mm=1e-8,relative_energy_limit=.0001,relative_analytic_tensor_limit=.00001,carrier_geometry_changed=False,carrier_convergence_demonstrated=False,solid_control=args.solid_control,runner_sha256=hashlib.sha256((SOURCE/'run_local_ccx_solver_parallel.py').read_bytes()).hexdigest(),native_binary_sha256=identity);(OUT/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
node=lambda i,j,k:1+i+(N+1)*(j+(N+1)*k);phys=(N+1)**3;refs=np.arange(phys+1,phys+4);points=np.array([[i/N,j/N,k/N]for k in range(N+1)for j in range(N+1)for i in range(N+1)]);cells=np.array([[node(i,j,k),node(i+1,j,k),node(i+1,j+1,k),node(i,j+1,k),node(i,j,k+1),node(i+1,j,k+1),node(i+1,j+1,k+1),node(i,j+1,k+1)]for k in range(N)for j in range(N)for i in range(N)]);pairs=[]
for k in range(N+1):
 for j in range(N+1):
  for i in range(N+1):
   q=np.array([i,j,k]);wrap=q%N
   if np.any(q==N):pairs.append((node(i,j,k),node(*wrap),np.flatnonzero(q==N)))
k,j,i=np.indices((N,N,N));x=2*np.pi*(i+.5)/N;y=2*np.pi*(j+.5)/N;z=2*np.pi*(k+.5)/N;solid=(abs(np.sin(x)*np.cos(y)+np.sin(y)*np.cos(z)+np.sin(z)*np.cos(x))<=threshold).reshape(-1);solid=np.ones_like(solid)if args.solid_control else solid;rho=float(solid.mean());assert (rho==1 if args.solid_control else 0<rho<1);cell_E=np.where(solid,E,E*floor);voigt_upper=rho+(1-rho)*floor
remaining=set(map(int,np.flatnonzero(solid)));components=0
while remaining:
 components+=1;stack=[remaining.pop()]
 while stack:
  q=stack.pop();k,t=divmod(q,N*N);j,i=divmod(t,N)
  for a,b,c in [((i+1)%N,j,k),((i-1)%N,j,k),(i,(j+1)%N,k),(i,(j-1)%N,k),(i,j,(k+1)%N),(i,j,(k-1)%N)]:
   neighbour=a+N*(b+N*c)
   if neighbour in remaining:remaining.remove(neighbour);stack.append(neighbour)
assert components==1,'Periodic solid phase is disconnected'
C=np.empty((6,6));rows=[]
for mode in range(6):
 H=np.zeros((3,3))
 if mode<3:H[mode,mode]=amp
 else:
  i,j=[(0,1),(0,2),(1,2)][mode-3];H[i,j]=H[j,i]=amp/2
 lines=['*HEADING','Owned periodic gyroid C3D8 homogenization fixture','*NODE']
 lines +=[f'{i+1},'+','.join(format(float(x),'.17g')for x in p)for i,p in enumerate(points)]
 lines +=[f'{int(ref)},'+','.join(map(str,2*np.eye(3)[i]))for i,ref in enumerate(refs)];lines +=['*NSET,NSET=ALLN,GENERATE',f'1,{phys+3},1','*ELEMENT,TYPE=C3D8,ELSET=ALLE'];lines +=[str(i+1)+','+','.join(map(str,c))for i,c in enumerate(cells)]
 for phase,selected,modulus in [('SOLID',solid,E),('VOID',~solid,E*floor)]:
  if not np.any(selected):continue
  ids=np.flatnonzero(selected)+1;lines +=['*ELSET,ELSET='+phase]
  lines +=[','.join(map(str,ids[start:start+16]))for start in range(0,len(ids),16)]
  lines +=['*MATERIAL,NAME=TI_'+phase,'*ELASTIC',f'{modulus},{nu}','*SOLID SECTION,ELSET='+phase+',MATERIAL=TI_'+phase]
 for slave,master,axes in pairs:
  for component in range(3):
   terms=[(slave,component+1,1),(master,component+1,-1)]+[(int(refs[axis]),component+1,-1)for axis in axes];lines +=['*EQUATION',str(len(terms))];lines +=[','.join(map(str,t))for t in terms]
 lines +=['*STEP','*STATIC','1,1','*BOUNDARY','1,1,3,0']
 lines +=[f'{int(refs[axis])},{component+1},{component+1},{H[component,axis]:.17g}'for axis in range(3)for component in range(3)]
 lines +=['*NODE PRINT,NSET=ALLN','U,RF','*EL PRINT,ELSET=ALLE','S','*END STEP'];deck=OUT/f'case-{mode}.inp';deck.write_text('\n'.join(lines)+'\n');execution=OUT/f'case-{mode}';subprocess.run([sys.executable,str(SOURCE/'run_local_ccx_solver_parallel.py'),'--binary',str(B),'--expected-binary',identity,'--deck',str(deck),'--output',str(execution),'--seconds','600','--rss-gib','24','--solver-threads','8'],check=True)
 receipt=json.loads((execution/'actual-terminal.json').read_text());assert receipt['actual_returncode']==0 and receipt['process_reaped']and receipt['inputs_unchanged'];assert hashlib.sha256((execution/'case/job.dat').read_bytes()).hexdigest()==receipt['output_sha256']['job.dat'];fields={k:[]for k in ['displacements','forces','stresses']};current=None
 for line in(execution/'case/job.dat').read_text().splitlines():
  stripped=line.strip()
  for key in fields:
   if stripped.startswith(key+' ('):assert not fields[key];current=key
  values=stripped.split()
  if current and len(values)==(8 if current=='stresses'else 4)and values[0].isdigit():fields[current].append(values)
 assert len(fields['displacements'])==phys+3 and len(fields['forces'])==phys+3 and len(fields['stresses'])==8*len(cells)
 for key in ['displacements','forces']:assert [int(x[0])for x in fields[key]]==list(range(1,phys+4))
 assert [(int(x[0]),int(x[1]))for x in fields['stresses']]==[(i+1,j+1)for i in range(len(cells))for j in range(8)]
 U=np.array([[float(y)for y in x[1:]]for x in fields['displacements']]);F=np.array([[float(y)for y in x[1:]]for x in fields['forces']]);stress=np.array([[float(y)for y in x[2:]]for x in fields['stresses']]);assert all(np.isfinite(x).all()for x in [U,F,stress]);pbc=max(float(abs(U[s-1]-U[m-1]-H[:,axes].sum(axis=1)).max())for s,m,axes in pairs);assert pbc<=1e-8;assert abs(U[refs-1]-H.T).max()<=1e-8
 average=stress.mean(0);C[:,mode]=average/amp;d=stress[:,:3];shear=stress[:,3:];density=(np.sum(d*d,1)-2*nu*(d[:,0]*d[:,1]+d[:,1]*d[:,2]+d[:,2]*d[:,0])+2*(1+nu)*np.sum(shear*shear,1))/(2*np.repeat(cell_E,8));internal=float(density.mean());macro=.5*average[mode]*amp;work=.5*float(np.sum(F[:phys]*U[:phys]));residual=abs(internal-macro)/macro;row=dict(mode=mode,pbc_max_mm=pbc,independent_internal_energy=internal,macro_energy=macro,physical_RF_work=work,relative_energy_residual=residual);rows.append(row);assert residual<=.0001 and abs(work-macro)/macro<=.0001;(OUT/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
G=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));expected=np.zeros((6,6));expected[:3,:3]=lam;expected[np.arange(3),np.arange(3)]+=2*G;expected[3:,3:]=np.eye(3)*G;difference=float(abs(C-expected).max()/abs(expected).max());symmetry=float(np.linalg.norm(C-C.T)/np.linalg.norm(C));assert symmetry<=.0001;values,vectors=np.linalg.eigh(expected);inverse=(vectors*(1/np.sqrt(values)))@vectors.T;normalized=inverse@((C+C.T)/2)@inverse;eigenvalues=np.linalg.eigvalsh(normalized);assert eigenvalues.min()>0 and eigenvalues.max()<=voigt_upper+.0001;
if args.solid_control:assert difference<=1e-5
report=dict(status='periodic_full_solid_six_strain_control_passed'if args.solid_control else'periodic_gyroid_six_strain_energy_checks_passed',relative_solid_control_tensor_error=difference if args.solid_control else None,effective_C_MPa=C.tolist(),dense_C_MPa=expected.tolist(),relative_antisymmetry=symmetry,normalized_stiffness_eigenvalues=eigenvalues.tolist(),minimum_tensor_stiffness_ratio=float(eigenvalues.min()),solid_fraction=rho,solid_periodic_components=components,void_relative_stiffness=floor,gyroid_threshold=threshold,resolution=N,voigt_upper_ratio=voigt_upper,cases=rows,source_sha256=contract['source_sha256'],parameters_sha256=contract['parameters_sha256'],carrier_convergence_demonstrated=False,cellular_part_generated=False,unitcell_mesh_convergence_demonstrated=False);(OUT/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],rho,eigenvalues.tolist(),flush=True)
