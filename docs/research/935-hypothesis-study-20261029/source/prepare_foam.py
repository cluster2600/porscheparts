"""Prepare an assumed external-airflow and passive-heat-transfer study of the scan envelope."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import numpy as np

p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('frame',type=Path);p.add_argument('output',type=Path);p.add_argument('--base-mm',type=float,default=16)
a=p.parse_args();a.output.mkdir()
for n in ['0','constant','constant/geometry','system']:(a.output/n).mkdir()
template=Path('/opt/openfoam13/tutorials/incompressibleFluid/motorBikeSteady/system')
def write(rel,body,cls='dictionary',dimensions=None,internal=None):
    name=Path(rel).name
    text='FoamFile\n{ version 2.0; format ascii; class '+cls+'; object '+name+'; }\n'
    if dimensions is not None:text+='dimensions '+dimensions+';\ninternalField uniform '+internal+';\n'
    (a.output/rel).write_text(text+body+'\n')
d=np.load(a.source);frame=np.load(a.frame);v=d['vertices']@frame.T;origin=v.min(axis=0);v=(v-origin)/1000;f=d['triangles']
with (a.output/'constant/geometry/head.obj').open('w') as out:
    for q in v:out.write('v '+' '.join(format(float(z),'.17g') for z in q)+'\n')
    for tri in f+1:out.write('f '+' '.join(map(str,tri))+'\n')
extent=v.max(axis=0);lo=np.array([-.08,-.08,-.08]);hi=extent+[.24,.08,.08];counts=np.ceil((hi-lo)/(a.base_mm/1000)).astype(int)
pts=np.array([[lo[0],lo[1],lo[2]],[hi[0],lo[1],lo[2]],[hi[0],hi[1],lo[2]],[lo[0],hi[1],lo[2]],[lo[0],lo[1],hi[2]],[hi[0],lo[1],hi[2]],[hi[0],hi[1],hi[2]],[lo[0],hi[1],hi[2]]])
vertices='\n'.join('('+ ' '.join(map(str,q))+')' for q in pts)
write('system/blockMeshDict',f'''convertToMeters 1;
vertices ({vertices});
blocks (hex (0 1 2 3 4 5 6 7) ({counts[0]} {counts[1]} {counts[2]}) simpleGrading (1 1 1));
boundary
(
 inlet {{ type patch; faces ((0 4 7 3)); }}
 outlet {{ type patch; faces ((2 6 5 1)); }}
 farfield {{ type patch; faces ((0 3 2 1) (4 5 6 7) (3 7 6 2) (1 5 4 0)); }}
);
''')
write('system/snappyHexMeshDict','''castellatedMesh true;
snap false;
addLayers false;
geometry { head { type triSurface; file "head.obj"; } }
castellatedMeshControls
{
 maxLocalCells 500000; maxGlobalCells 1500000; minRefinementCells 10;
 maxLoadUnbalance 0.10; nCellsBetweenLevels 3; features ();
 refinementSurfaces { head { level (2 2); patchInfo { type wall; } } }
 resolveFeatureAngle 30; refinementRegions {};
 insidePoint (-0.07123 -0.06789 -0.06432);
 allowFreeStandingZoneFaces true;
}
snapControls
{
 nSmoothPatch 3; tolerance 2; nSolveIter 30; nRelaxIter 5;
 nFeatureSnapIter 10; implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false;
}
addLayersControls {}
meshQualityControls
{
 #include "meshQualityDict"
}
debug 0;
mergeTolerance 1e-6;
''')
shutil.copyfile(template/'meshQualityDict',a.output/'system/meshQualityDict')
schemes=(template/'fvSchemes').read_text().replace('div(phi,k)', 'div(phi,T) bounded Gauss upwind;\n    div(phi,k)')
(a.output/'system/fvSchemes').write_text(schemes)
solution=(template/'fvSolution').read_text().replace('    U\n','    T { solver smoothSolver; smoother GaussSeidel; tolerance 1e-9; relTol 0.01; }\n    U\n',1).replace('nNonOrthogonalCorrectors 0','nNonOrthogonalCorrectors 2').replace('U               0.9','U               0.7')
(a.output/'system/fvSolution').write_text(solution)
write('system/controlDict','''application foamRun; solver incompressibleFluid;
startFrom startTime; startTime 0; stopAt endTime; endTime 600; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 2;
writeFormat ascii; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 6; runTimeModifiable false;
functions
{
 #includeFunc scalarTransport(T, diffusivity=viscosity, alphal=1.408450704, alphat=1.176470588)
 inletFlux { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); patch inlet; operation sum; fields (phi); writeFields false; }
 outletFlux { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); patch outlet; operation sum; fields (phi); writeFields false; }
 #includeFunc yPlus
}
''')
write('system/decomposeParDict','numberOfSubdomains 4; method scotch;')
write('constant/physicalProperties','viscosityModel constant; nu [0 2 -1 0 0 0 0] 1.8e-5;')
write('constant/momentumTransport','simulationType RAS; RAS { model kOmegaSST; turbulence on; }')
settings={
 'U':('volVectorField','[0 1 -1 0 0 0 0]','(15 0 0)','type fixedValue; value uniform (15 0 0);','type inletOutlet; inletValue uniform (15 0 0); value uniform (15 0 0);','type slip;','type noSlip;'),
 'p':('volScalarField','[0 2 -2 0 0 0 0]','0','type zeroGradient;','type fixedValue; value uniform 0;','type zeroGradient;','type zeroGradient;'),
 'k':('volScalarField','[0 2 -2 0 0 0 0]','0.84375','type fixedValue; value uniform 0.84375;','type inletOutlet; inletValue uniform 0.84375; value uniform 0.84375;','type zeroGradient;','type kqRWallFunction; value uniform 0.84375;'),
 'omega':('volScalarField','[0 0 -1 0 0 0 0]','167.7','type fixedValue; value uniform 167.7;','type inletOutlet; inletValue uniform 167.7; value uniform 167.7;','type zeroGradient;','type omegaWallFunction; value uniform 167.7;'),
 'nut':('volScalarField','[0 2 -1 0 0 0 0]','0.005','type calculated; value uniform 0.005;','type calculated; value uniform 0.005;','type calculated; value uniform 0.005;','type nutkWallFunction; value uniform 0;'),
 'T':('volScalarField','[0 0 0 1 0 0 0]','300','type fixedValue; value uniform 300;','type inletOutlet; inletValue uniform 300; value uniform 300;','type zeroGradient;','type fixedValue; value uniform 400;')}
for name,(cls,dim,val,inlet,outlet,far,head) in settings.items():
 write('0/'+name,'boundaryField { inlet {'+inlet+'} outlet {'+outlet+'} farfield {'+far+'} head {'+head+'} }',cls,dim,val)
(a.output/'assumptions.json').write_text(json.dumps({'scope':'external cooling envelope with assumed air and isothermal wall; not internal intake/exhaust CFD or coupled engine CHT','velocity_m_s':15,'air_K':300,'wall_K':400,'kinematic_viscosity_m2_s':1.8e-5,'Pr':.71,'Pr_turbulent':.85,'inlet_turbulence_intensity':.05,'inlet_mixing_length_m':.01,'base_cell_mm':a.base_mm,'near_surface_nominal_mm':a.base_mm/4,'frame_rows_ABC':frame.tolist(),'origin_in_ABC_mm':origin.tolist(),'boundary_layers_added':False,'manufacturing_qualified':False},indent=2)+'\n')
print('Prepared conditional OpenFOAM case:',a.output)
