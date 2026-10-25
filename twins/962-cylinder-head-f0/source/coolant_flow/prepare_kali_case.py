"""Prepare the checked water mesh for a bounded Foundation-13 isothermal RANS run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def header(name, kind="dictionary"):
    return f"FoamFile {{ format ascii; class {kind}; object {name}; }}\n"


def dictionaries(q, rho, area_mm2):
    if not all(math.isfinite(v) and v > 0 for v in (q, rho, area_mm2)):
        raise ValueError("Finite positive flow, density and inlet area required")
    velocity=q/(area_mm2*1e-6);nu=.000315/rho
    k=1.5*(.05*velocity)**2;omega=math.sqrt(k)/(.09**.25*.00154)
    files={
        'constant/physicalProperties':f'viscosityModel constant; nu [0 2 -1 0 0 0 0] {nu:.17g};\n',
        'constant/momentumTransport':'simulationType RAS; RAS { model kOmegaSST; turbulence on; printCoeffs on; }\n',
        'system/fvSchemes':'''ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) bounded Gauss upwind; div(phi,k) bounded Gauss upwind;
div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
fluxRequired { default no; p; }
''',
        'system/fvSolution':'''solvers {
p { solver GAMG; tolerance 1e-8; relTol 0.01; smoother GaussSeidel; }
"(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.01; }
}
SIMPLE { nNonOrthogonalCorrectors 0; consistent yes;
residualControl { p 1e-5; U 1e-5; "(k|omega)" 1e-5; } }
relaxationFactors { fields { p 0.3; } equations { U 0.5; k 0.5; omega 0.5; } }
''',
        'system/decomposeParDict':'numberOfSubdomains 4; method scotch;\n',
        'system/controlDict':'''application foamRun; solver incompressibleFluid;
startFrom startTime; startTime 0; stopAt endTime; endTime 2000; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 2; writeFormat ascii;
writePrecision 16; writeCompression off; runTimeModifiable false;
functions {
inletFlux { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep;
writeInterval 1; writeFields false; patch inlet; operation sum; fields (phi); }
outletFlux { $inletFlux; patch outlet; }
inletPressure { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep;
writeInterval 1; writeFields false; patch inlet; operation areaAverage; fields (p); }
outletPressure { $inletPressure; patch outlet; }
}
''',
    }
    # createPatch retains the type of an existing patch: use a new name, then restore walls.
    for index,old,new in ((1,'walls','waterWallTyped'),(2,'waterWallTyped','walls')):
        files[f'system/wallTypeStage{index}']=f'pointSync false; patches ( {{ name {new}; patchInfo {{ type wall; }} constructFrom patches; patches ({old}); }} );\n'
    for name,kind,dims,initial,inlet,outlet,wall in (
        ('U','volVectorField','0 1 -1 0 0 0 0',f'({velocity:.17g} 0 0)',
         f'type flowRateInletVelocity; volumetricFlowRate constant {q:.17g}; value uniform ({velocity:.17g} 0 0);',
         'type zeroGradient;','type noSlip;'),
        ('p','volScalarField','0 2 -2 0 0 0 0','0','type zeroGradient;',
         'type fixedValue; value uniform 0;','type zeroGradient;'),
        ('k','volScalarField','0 2 -2 0 0 0 0',str(k),f'type fixedValue; value uniform {k};',
         'type zeroGradient;','type kqRWallFunction; value uniform 1e-6;'),
        ('omega','volScalarField','0 0 -1 0 0 0 0',str(omega),f'type fixedValue; value uniform {omega};',
         'type zeroGradient;','type omegaWallFunction; value uniform 1;'),
        ('nut','volScalarField','0 2 -1 0 0 0 0','0','type calculated; value uniform 0;',
         'type calculated; value uniform 0;','type nutkWallFunction; value uniform 0;'),
    ):
        files['0/'+name]=header(name,kind)+f'dimensions [{dims}]; internalField uniform {initial};\nboundaryField {{ inlet {{ {inlet} }} outlet {{ {outlet} }} walls {{ {wall} }} }}\n'
    for name in list(files):
        if not name.startswith('0/'):files[name]=header(Path(name).name)+files[name]
    return files,velocity,k,omega


def prepare(mesh_dir,surface_dir,budget_path,output):
    audit=json.loads((mesh_dir/'saved-readback.json').read_text())
    if audit['independent_volume_quality_passed'] is not True or audit['below_sicn_01']!=0:
        raise ValueError('Volume screen has not passed')
    if sha(mesh_dir/'coolant.msh')!=audit['mesh_sha256']:
        raise ValueError('Saved mesh changed')
    surface_record=json.loads((surface_dir/'surface-report.json').read_text())
    if surface_record['geometry_admitted'] is not True or sha(surface_dir/'coolant.stl')!=surface_record['candidate_sha256']:
        raise ValueError('Screened boundary changed')
    if output.exists():raise ValueError('Output must be new')
    import trimesh
    import numpy as np
    from mesh_discrete import partition
    boundary=trimesh.load_mesh(surface_dir/'coolant.stl',process=True)
    groups=partition(np.asarray(boundary.vertices),np.asarray(boundary.faces))
    xyz=boundary.vertices[groups['inlet']]
    area=float(np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1).sum()/2)
    budget=json.loads(budget_path.read_text());q=budget['nominal']['results']['water_each_head_l_min']/60000
    rho=budget['constants']['water_density_kg_m3']
    files,velocity,k,omega=dictionaries(q,rho,area)
    output.mkdir(parents=True)
    for name,text in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    shutil.copyfile(mesh_dir/'coolant.msh',output/'coolant.msh')
    guard=Path(__file__).resolve().parent.parent/'flow4l/accept_mesh.py'
    shutil.copyfile(guard,output/'accept_mesh.py')
    shutil.copyfile(Path(__file__).with_name('run_kali_case.sh'),output/'run_kali_case.sh')
    (output/'case.foam').touch()
    record=dict(status='prepared_not_executed_isothermal_rans_case',cells=audit['cells'],grid_mm=None,
                flow_m3_s=q,water_density_kg_m3=rho,assumed_dynamic_viscosity_pa_s=.000315,
                inlet_area_mm2=area,inlet_mean_speed_m_s=velocity,inlet_turbulence_intensity=.05,
                inlet_length_scale_m=.00154,turbulence_k=k,turbulence_omega=omega,
                solver='OpenFOAM Foundation 13 incompressibleFluid',turbulence_model='kOmegaSST',
                discretisation='first_order_upwind_diagnostic',planned_processes=4,maximum_solver_seconds=1800,
                source_hashes={p.name:sha(p) for p in (Path(__file__),mesh_dir/'saved-readback.json',surface_dir/'surface-report.json',budget_path,guard)},
                case_hashes={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()},
                openfoam_mesh_accepted=False,hydraulic_performance_validated=False,manufacturing_authorized=False)
    (output/'case-report.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:record[k] for k in ('cells','flow_m3_s','inlet_area_mm2','inlet_mean_speed_m_s')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','surface','budget','output'):parser.add_argument(name,type=Path)
    a=parser.parse_args();prepare(*(p.resolve() for p in (a.mesh,a.surface,a.budget,a.output)))
