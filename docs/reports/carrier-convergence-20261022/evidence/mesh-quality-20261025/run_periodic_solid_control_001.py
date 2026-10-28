from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'work/carrier-mesh-quality-20261025';SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022';OUT=W/'periodic-solid-control-001';OUT.mkdir();N=4;E=107000.;nu=.31;amp=.001;B=W/'spooles-upstream-review-015/mac-ccx-relink-001/fixed-with-mt/ccx_2.21';identity=hashlib.sha256(B.read_bytes()).hexdigest();assert identity=='95e9b61985446b686f5f146d1a947101a5ec8ac86fef0cf9e308d25f817c918a'
contract=dict(geometry='unit cube; complete C3D8 grid',grid=N,amplitude=amp,E_MPa=E,nu=nu,periodic_displacement_residual_limit_mm=1e-8,relative_energy_limit=.0001,relative_analytic_tensor_limit=.00001,carrier_geometry_changed=False,carrier_convergence_demonstrated=False);(OUT/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
node=lambda i,j,k:1+i+(N+1)*(j+(N+1)*k);phys=(N+1)**3;refs=np.arange(phys+1,phys+4);points=np.array([[i/N,j/N,k/N]for k in range(N+1)for j in range(N+1)for i in range(N+1)]);cells=np.array([[node(i,j,k),node(i+1,j,k),node(i+1,j+1,k),node(i,j+1,k),node(i,j,k+1),node(i+1,j,k+1),node(i+1,j+1,k+1),node(i,j+1,k+1)]for k in range(N)for j in range(N)for i in range(N)]);pairs=[]
for k in range(N+1):
 for j in range(N+1):
  for i in range(N+1):
   q=np.array([i,j,k]);wrap=q%N
   if np.any(q==N):pairs.append((node(i,j,k),node(*wrap),np.flatnonzero(q==N)))
C=np.empty((6,6));rows=[]
for mode in range(6):
 H=np.zeros((3,3))
 if mode<3:H[mode,mode]=amp
 else:
  i,j=[(0,1),(0,2),(1,2)][mode-3];H[i,j]=H[j,i]=amp/2
 lines=['*HEADING','Owned periodic full-solid C3D8 manufactured control','*NODE']
 lines +=[f'{i+1},'+','.join(format(float(x),'.17g')for x in p)for i,p in enumerate(points)]
 lines +=[f'{int(ref)},'+','.join(map(str,2*np.eye(3)[i]))for i,ref in enumerate(refs)];lines +=['*NSET,NSET=ALLN,GENERATE',f'1,{phys+3},1','*ELEMENT,TYPE=C3D8,ELSET=ALLE'];lines +=[str(i+1)+','+','.join(map(str,c))for i,c in enumerate(cells)]
 lines +=['*MATERIAL,NAME=TI','*ELASTIC',f'{E},{nu}','*SOLID SECTION,ELSET=ALLE,MATERIAL=TI']
 for slave,master,axes in pairs:
  for component in range(3):
   terms=[(slave,component+1,1),(master,component+1,-1)]+[(int(refs[axis]),component+1,-1)for axis in axes];lines +=['*EQUATION',str(len(terms))];lines +=[','.join(map(str,t))for t in terms]
 lines +=['*STEP','*STATIC','1,1','*BOUNDARY','1,1,3,0']
 lines +=[f'{int(refs[axis])},{component+1},{component+1},{H[component,axis]:.17g}'for axis in range(3)for component in range(3)]
 lines +=['*NODE PRINT,NSET=ALLN','U,RF','*EL PRINT,ELSET=ALLE','S','*END STEP'];deck=OUT/f'case-{mode}.inp';deck.write_text('\n'.join(lines)+'\n');execution=OUT/f'case-{mode}';subprocess.run([sys.executable,str(SOURCE/'run_local_ccx_solver_parallel.py'),'--binary',str(B),'--expected-binary',identity,'--deck',str(deck),'--output',str(execution),'--seconds','300','--rss-gib','4','--solver-threads','8'],check=True)
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
 average=stress.mean(0);C[:,mode]=average/amp;d=stress[:,:3];shear=stress[:,3:];density=(np.sum(d*d,1)-2*nu*(d[:,0]*d[:,1]+d[:,1]*d[:,2]+d[:,2]*d[:,0])+2*(1+nu)*np.sum(shear*shear,1))/(2*E);internal=float(density.mean());macro=.5*average[mode]*amp;work=.5*float(np.sum(F[:phys]*U[:phys]));residual=abs(internal-macro)/macro;row=dict(mode=mode,pbc_max_mm=pbc,independent_internal_energy=internal,macro_energy=macro,physical_RF_work=work,relative_energy_residual=residual);rows.append(row);assert residual<=.0001;(OUT/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
G=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));expected=np.zeros((6,6));expected[:3,:3]=lam;expected[np.arange(3),np.arange(3)]+=2*G;expected[3:,3:]=np.eye(3)*G;difference=float(abs(C-expected).max()/abs(expected).max());assert difference<=1e-5;report=dict(status='periodic_full_solid_six_strain_control_passed',effective_C_MPa=C.tolist(),analytic_C_MPa=expected.tolist(),relative_tensor_error=difference,cases=rows,carrier_convergence_demonstrated=False);(OUT/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],difference,flush=True)
