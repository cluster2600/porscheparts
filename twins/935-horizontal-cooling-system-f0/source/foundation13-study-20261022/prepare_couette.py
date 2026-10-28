"""Prepare three SI laminar MRF Couette controls for the installed Foundation 13."""
import json,math,sys
from pathlib import Path
from run_reconstruction import ROOT,fresh,save,sha
sys.path.insert(0,str(ROOT/'twins/reference-917-engine/source'))
from prepare_aircooled_openfoam_f34 import header,write_field
RI=.05;RO=.1;L=.01;RPM=60.;NU=.001;RHO=3.;OMEGA=RPM*math.pi/30

def velocity(x,y):
 r=math.hypot(x,y);b=OMEGA*RI**2*RO**2/(RO**2-RI**2);a=-b/RO**2
 return (-y*(a+b/r**2),x*(a+b/r**2),0.)

def torque():return -4*math.pi*RHO*NU*OMEGA*L*RI**2*RO**2/(RO**2-RI**2)

def generate(output):
 out=fresh(output)
 for name,n in [('coarse',8),('medium',16),('fine',32)]:
  p=out/name;p.mkdir();[(p/d).mkdir() for d in ['0','constant','system']]
  def write(relative,text):(p/relative).write_text(header(Path(relative).name)+text)
  vertices=[(r*math.cos(j*math.pi/2),r*math.sin(j*math.pi/2),z) for z in [-L/2,L/2] for r in [RI,RO] for j in range(4)]
  blocks=[];arcs=[];inner=[];outer=[];ends=[]
  for j in range(4):
   k=(j+1)%4;ids=[j,4+j,4+k,k,8+j,12+j,12+k,8+k]
   blocks.append('hex ('+' '.join(map(str,ids))+f') rotor ({n} {n} 1) simpleGrading (1 1 1)')
   inner.append([j,8+j,8+k,k]);outer.append([4+j,4+k,12+k,12+j]);ends.extend([[j,k,4+k,4+j],[8+j,12+j,12+k,8+k]])
   for base,r,z in [(0,RI,-L/2),(4,RO,-L/2),(8,RI,L/2),(12,RO,L/2)]:
    phi=(j+.5)*math.pi/2;arcs.append(f'arc {base+j} {base+k} ({r*math.cos(phi):.17g} {r*math.sin(phi):.17g} {z:.17g})')
  faces=lambda values:' '.join('('+' '.join(map(str,v))+')' for v in values)
  text='convertToMeters 1;\nvertices (\n'+''.join('('+ ' '.join(f'{x:.17g}' for x in v)+')\n' for v in vertices)+');\nblocks (\n'+'\n'.join(blocks)+');\nedges (\n'+'\n'.join(arcs)+');\nboundary (\n'
  for key,kind,values in [('rotor','wall',inner),('stator','wall',outer),('frontAndBack','empty',ends)]:text+=f'{key} {{type {kind};faces ({faces(values)});}}\n'
  write('system/blockMeshDict',text+');\nmergePatchPairs ();\n')
  write('constant/physicalProperties',f'viscosityModel constant;\nnu [0 2 -1 0 0 0 0] {NU};\n')
  write('constant/momentumTransport','simulationType laminar;\n')
  write('constant/MRFProperties',f'MRF {{cellZone rotor;origin (0 0 0);axis (0 0 1);omega {RPM} [rpm];}}\n')
  write_field(p,'U','[0 1 -1 0 0 0 0]','(0 0 0)','rotor {type MRFnoSlip;}\nstator {type noSlip;}\nfrontAndBack {type empty;}','volVectorField')
  write_field(p,'p','[0 2 -2 0 0 0 0]','0','rotor {type zeroGradient;}\nstator {type zeroGradient;}\nfrontAndBack {type empty;}')
  write('system/fvSchemes','ddtSchemes {default steadyState;}\ngradSchemes {default Gauss linear;}\ndivSchemes {default none;div(phi,U) bounded Gauss linear;div((nuEff*dev2(T(grad(U))))) Gauss linear;}\nlaplacianSchemes {default Gauss linear corrected;}\ninterpolationSchemes {default linear;}\nsnGradSchemes {default corrected;}\n')
  write('system/fvSolution','solvers {p {solver GAMG;tolerance 1e-12;relTol 0;smoother GaussSeidel;} U {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-12;relTol 0;}}\nSIMPLE {nNonOrthogonalCorrectors 1;pRefCell 0;pRefValue 0;}\nrelaxationFactors {fields {p 0.3;}equations {U 0.7;}}\n')
  functions=f'rotorForces {{type forces;libs ("libforces.so");patches (rotor);rho rhoInf;rhoInf {RHO};CofR (0 0 0);log true;writeControl timeStep;writeInterval 20;}}'
  write('system/controlDict',f'solver incompressibleFluid;startFrom startTime;startTime 0;stopAt endTime;endTime 2000;deltaT 1;writeControl timeStep;writeInterval 200;purgeWrite 2;writeFormat ascii;writePrecision 14;timePrecision 14;runTimeModifiable false;functions {{{functions}}}\n')
  save(p/'input-receipt.json',{'classification':'synthetic_MRF_wall_velocity_and_torque_control','cells':4*n*n,'inner_radius_m':RI,'outer_radius_m':RO,'depth_m':L,'rotor_rpm':RPM,'nu_m2_s':NU,'density_kg_m3':RHO,'analytic_torque_Nm':torque(),'source_sha256':sha(__file__),'prepared_input_sha256':{str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()},'rotor_935_CFD_accepted':False})
 save(out/'contract.json',{'qualification':'935_Foundation13_MRF_Couette','mesh_levels':['coarse','medium','fine'],'fine_velocity_relative_L2_limit':.005,'fine_velocity_relative_Linf_limit':.005,'fine_torque_relative_error_limit':.02,'fine_to_medium_torque_relative_difference_limit':.03,'torque_steady_relative_change_limit':1e-5,'rotor_935_CFD_accepted':False})
 print(out)
if __name__=='__main__':generate(Path(sys.argv[1]))
