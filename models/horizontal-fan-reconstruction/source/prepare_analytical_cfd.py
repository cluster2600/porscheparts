#!/usr/bin/env python3
"""Prepare a bounded Foundation-13 isolated-fan MRF pilot after OCC fluid meshing."""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(mesh,output,parameters,rpm=6000,iterations=200):
    import shutil
    report=json.loads((mesh/'mesh-report.json').read_text())
    p=json.loads(parameters.read_text())
    if report['mode']!='fluid' or report['minimum_Gauss4_jacobian']<=0:
        raise ValueError('Positive fluid mesh required')
    if report['configuration_id']!=p['configuration_id']:raise ValueError('Geometry identity mismatch')
    output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(mesh/'volume.msh',output/'volume.msh')
    def write(name,body,cls='dictionary'):
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('FoamFile {version 2.0; format ascii; class '+cls+'; object '+path.name+';}\n'+body+'\n')
    write('system/controlDict',f'''
application foamRun; solver incompressibleFluid;
startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval {iterations}; purgeWrite 1;
writeFormat ascii; writePrecision 10; writeCompression off; runTimeModifiable false;
functions {{
 inletFlow {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
 writeControl timeStep; writeInterval 1; patch inlet; operation sum; fields (phi); writeFields false;}}
 outletFlow {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
 writeControl timeStep; writeInterval 1; patch outlet; operation sum; fields (phi); writeFields false;}}
 rotorForces {{type forces; libs ("libforces.so"); patches (rotor); rho rhoInf; rhoInf 1.2;
 CofR (0 0 0); writeControl timeStep; writeInterval 1;}}
}}
''')
    write('system/fvSchemes','''
ddtSchemes {default steadyState;}
gradSchemes {default Gauss linear; grad(U) cellLimited Gauss linear 1;}
divSchemes {default none; div(phi,U) bounded Gauss upwind; div(phi,k) bounded Gauss upwind;
 div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited .5;}
interpolationSchemes {default linear;}
snGradSchemes {default limited .5;} wallDist {method meshWave;}
''')
    write('system/fvSolution','''
solvers {p {solver GAMG; smoother GaussSeidel; tolerance 1e-8; relTol .01;}
 "(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}}
SIMPLE {nNonOrthogonalCorrectors 2; consistent no;}
relaxationFactors {fields {p .25;} equations {U .5; k .5; omega .5;}}
''')
    write('system/decomposeParDict','numberOfSubdomains 4; method scotch;')
    half=p['diameter_mm']*.00015
    write('system/topoSetDict',f'''actions (
 {{name rotorCells; type cellSet; action new; source boxToCell; box (-1 -1 {-half}) (1 1 {half});}}
 {{name rotorZone; type cellZoneSet; action new; source setToCellZone; set rotorCells;}}
);''')
    write('constant/MRFProperties',f'MRF {{cellZone rotorZone; origin (0 0 0); axis (0 0 1); omega {rpm} [rpm];}}')
    write('constant/physicalProperties','viscosityModel constant; nu 1.5e-5;')
    write('constant/momentumTransport','simulationType RAS; RAS {model kOmegaSST; turbulence on;}')
    write('0/U','''dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 -1);
boundaryField {"(inlet|outlet)" {type pressureInletOutletVelocity; value uniform (0 0 -1);}
rotor {type MRFnoSlip;} shroud {type noSlip;}}''','volVectorField')
    write('0/p','''dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {inlet {type totalPressure; p0 uniform 0; value uniform 0;}
outlet {type fixedValue; value uniform 0;} "(rotor|shroud)" {type zeroGradient;}}''','volScalarField')
    for name,dim,value,wall in [('k','0 2 -2',.01,'kqRWallFunction'),('omega','0 0 -1',10,'omegaWallFunction'),('nut','0 2 -1',0,'nutkWallFunction')]:
        opening=f'type calculated; value uniform {value};' if name=='nut' else f'type inletOutlet; inletValue uniform {value}; value uniform {value};'
        write('0/'+name,f'dimensions [{dim} 0 0 0 0]; internalField uniform {value}; boundaryField {{"(inlet|outlet)" {{{opening}}} "(rotor|shroud)" {{type {wall}; value uniform {value};}}}}','volScalarField')
    preparation={'status':'prepared_not_solved','configuration_id':p['configuration_id'],'rpm_assumed':rpm,
                 'tip_mach_assuming_343_m_s':rpm*3.141592653589793/30*p['diameter_mm']/2000/343,
                 'air_density_kg_m3_assumed':1.2,'kinematic_viscosity_m2_s_assumed':1.5e-5,
                 'inlet':'top total pressure zero gauge','outlet':'bottom static pressure zero gauge',
                 'expected_axial_flow_direction':[0,0,-1],'rotation_positive_axis':[0,0,1],
                 'model':'steady isolated incompressible RANS kOmegaSST MRF, first-order convection',
                 'MRF_zone_half_height_m':half,'mesh_sha256':hashlib.sha256((output/'volume.msh').read_bytes()).hexdigest(),
                 'required_mesh_gate':'checkMesh -allGeometry -allTopology, Mesh OK and zero failed checks',
                 'wall_layers_present':False,'grid_independence_established':False,'installed_engine_included':False,
                 'convergence_required_before_ranking':True,'physical_validation_established':False,'manufacturing_authorized':False}
    (output/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n');return preparation


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mesh',type=Path);parser.add_argument('output',type=Path);parser.add_argument('parameters',type=Path)
    parser.add_argument('--rpm',type=float,default=6000);parser.add_argument('--iterations',type=int,default=200)
    args=parser.parse_args();print(json.dumps(prepare(args.mesh,args.output,args.parameters,args.rpm,args.iterations)))
