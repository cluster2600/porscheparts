#!/usr/bin/env python3
"""Prepare a conditional rotor MRF/SST test duct for OpenCFD v2406."""
import argparse
import json
import math
from pathlib import Path
import sys

import trimesh

from run_reconstruction import ROOT, fresh, save, sha
from build_system_twin import positive

sys.path.insert(0, str(ROOT / 'twins/reference-917-engine/source'))
from prepare_aircooled_openfoam_f34 import header, prepare_case, write_field


def prepare(case_path, output):
    case = json.loads(Path(case_path).read_text())
    if case.get('purpose') != 'hypothesis_screen' or not case.get('assumptions'):
        raise ValueError('Explicit duct and operating hypotheses required')
    config = case['cfd']
    if set(config['mesh_cells']) != {'coarse','medium','fine'}:
        raise ValueError('Exactly three named mesh levels are required')
    if type(config['iterations']) is not int or not 1 <= config['iterations'] <= 5000:
        raise ValueError('Bounded positive iteration count required')
    width, height, q, rho, nu = (positive(config[k]) for k in
        ('duct_half_width_m', 'duct_half_height_m', 'flow_m3_s', 'air_density_kg_m3', 'kinematic_viscosity_m2_s'))
    rpm = config['rotor_rpm']
    if isinstance(rpm, bool) or not math.isfinite(rpm) or rpm == 0:
        raise ValueError('Signed finite nonzero rotor speed required')
    source = Path(config['rotor_stl_path'])
    if sha(source) != config['rotor_stl_sha256']:
        raise ValueError('Rotor hash mismatch')
    mesh = trimesh.load_mesh(source, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError('A closed consistently oriented rotor is required')
    mesh.apply_scale(.001)
    bounds = mesh.bounds
    zone = positive(config['rotating_zone_radius_m'])
    z0, z1 = config['rotating_zone_z_m']
    if not 0 < zone < width or not -height < z0 < bounds[0, 2] < bounds[1, 2] < z1 < height:
        raise ValueError('Rotating zone must enclose the rotor and lie inside the duct')
    if (mesh.vertices[:, :2] ** 2).sum(axis=1).max() >= zone ** 2:
        raise ValueError('Rotating zone radius does not enclose the rotor')
    out = fresh(output)
    save(out / 'case.json', case)
    velocity = q / (4 * width * width)
    k = 1.5 * (positive(config['turbulence_intensity']) * velocity) ** 2
    omega = math.sqrt(k) / (.09 ** .25 * positive(config['turbulence_length_m']))
    temporary = out / 'rotor-si.stl'
    mesh.export(temporary)
    for name, cells in config['mesh_cells'].items():
        if len(cells) != 3 or any(isinstance(x, bool) or not isinstance(x, int) or x < 8 for x in cells):
            raise ValueError('Three positive integer mesh counts required')
        target = out / name
        prepare_case(target, temporary, tuple(cells), (2, 3), velocity, 300)
        for obsolete in ('0/T','0/epsilon','0/alphat','constant/physicalProperties','constant/momentumTransport'):
            (target / obsolete).unlink(missing_ok=True)
        old = (target / 'system/snappyHexMeshDict').read_text()
        old = old.replace('head', 'rotor').replace('scale 0.001;', '').replace('locationInMesh (-0.27 0 0.12);',
                                                f'locationInMesh ({-width * .733} {width * .617} {height * .813});')
        (target / 'system/snappyHexMeshDict').write_text(old)
        quality = target / 'system/meshQualityDict'
        quality.write_text(header('meshQualityDict') + quality.read_text())
        (target / 'constant/triSurface/head.stl').rename(target / 'constant/triSurface/rotor.stl')
        w, h = width, height
        vertices = [(-w,-w,-h),(w,-w,-h),(w,w,-h),(-w,w,-h),
                    (-w,-w,h),(w,-w,h),(w,w,h),(-w,w,h)]
        (target / 'system/blockMeshDict').write_text(header('blockMeshDict') +
            'convertToMeters 1;\nvertices (\n' + ''.join(f'({x} {y} {z})\n' for x,y,z in vertices) +
            f');\nblocks (hex (0 1 2 3 4 5 6 7) ({cells[0]} {cells[1]} {cells[2]}) simpleGrading (1 1 1));\n' +
            'edges ();\nboundary (\n inlet {type patch;faces ((4 5 6 7));}\n' +
            ' outlet {type patch;faces ((0 3 2 1));}\n' +
            ' duct {type wall;faces ((0 1 5 4)(1 2 6 5)(2 3 7 6)(3 0 4 7));}\n);\n')
        (target / 'constant/transportProperties').write_text(header('transportProperties') +
            f'transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] {nu};\n')
        (target / 'constant/turbulenceProperties').write_text(header('turbulenceProperties') +
            'simulationType RAS;\nRAS {RASModel kOmegaSST;turbulence on;printCoeffs on;}\n')
        (target / 'constant/MRFProperties').write_text(header('MRFProperties') +
            f'rotor {{cellZone rotorZone;active yes;nonRotatingPatches (inlet outlet duct);origin (0 0 0);axis (0 0 1);omega {rpm * math.pi / 30};}}\n')
        (target / 'system/topoSetDict').write_text(header('topoSetDict') +
            f'actions ({{name rotorCells;type cellSet;action new;source cylinderToCell;sourceInfo {{p1 (0 0 {z0});p2 (0 0 {z1});radius {zone};}}}}\n' +
            '{name rotorZone;type cellZoneSet;action new;source setToCellZone;sourceInfo {set rotorCells;}});\n')
        write_field(target, 'U', '[0 1 -1 0 0 0 0]', f'(0 0 {-velocity})',
            f'inlet {{type flowRateInletVelocity;volumetricFlowRate constant {q};value uniform (0 0 {-velocity});}}\n' +
            'outlet {type zeroGradient;}\nduct {type fixedValue;value uniform (0 0 0);}\nrotor {type fixedValue;value uniform (0 0 0);}', 'volVectorField')
        write_field(target, 'p', '[0 2 -2 0 0 0 0]', '0',
            'inlet {type zeroGradient;}\noutlet {type fixedValue;value uniform 0;}\nduct {type zeroGradient;}\nrotor {type zeroGradient;}')
        for field, dimensions, value, wall in [('k','[0 2 -2 0 0 0 0]',k,'kqRWallFunction'),
                                             ('omega','[0 0 -1 0 0 0 0]',omega,'omegaWallFunction'),
                                             ('nut','[0 2 -1 0 0 0 0]',0,'nutkWallFunction')]:
            inlet = f'type fixedValue;value uniform {value};' if field != 'nut' else 'type calculated;value uniform 0;'
            write_field(target, field, dimensions, str(value),
                f'inlet {{{inlet}}}\noutlet {{type zeroGradient;}}\nduct {{type {wall};value uniform {value};}}\nrotor {{type {wall};value uniform {value};}}')
        (target / 'system/fvSchemes').write_text(header('fvSchemes') + '''
ddtSchemes {default steadyState;}
gradSchemes {default cellLimited Gauss linear 1;}
divSchemes {default none;div(phi,U) bounded Gauss linearUpwind grad(U);div(phi,k) bounded Gauss upwind;div(phi,omega) bounded Gauss upwind;div((nuEff*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited 0.5;}
interpolationSchemes {default linear;}
snGradSchemes {default limited 0.5;}
wallDist {method meshWave;}
''')
        (target / 'system/fvSolution').write_text(header('fvSolution') + '''
solvers {p {solver GAMG;smoother GaussSeidel;tolerance 1e-9;relTol 0;} "(U|k|omega)" {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-9;relTol 0;}}
SIMPLE {nNonOrthogonalCorrectors 2;consistent yes;}
relaxationFactors {fields {p 0.3;} equations {U 0.5;k 0.5;omega 0.5;}}
''')
        functions = f'''velocitySquared {{type magSqr;libs ("libfieldFunctionObjects.so");field U;result UMagSqr;executeControl timeStep;executeInterval 1;writeControl timeStep;writeInterval 10;}}
forces {{type forces;libs ("libforces.so");patches (rotor);rho rhoInf;rhoInf {rho};CofR (0 0 0);writeControl timeStep;writeInterval 10;}}
'''
        for patch in ('inlet', 'outlet'):
            functions += f'''{patch}Flow {{type surfaceFieldValue;libs ("libfieldFunctionObjects.so");regionType patch;name {patch};operation sum;fields (phi);writeFields false;writeControl timeStep;writeInterval 10;}}
{patch}Pressure {{type surfaceFieldValue;libs ("libfieldFunctionObjects.so");regionType patch;name {patch};operation areaAverage;fields (p UMagSqr);writeFields false;writeControl timeStep;writeInterval 10;}}
'''
        (target / 'system/controlDict').write_text(header('controlDict') +
            f'application simpleFoam;startFrom startTime;startTime 0;stopAt endTime;endTime {config["iterations"]};deltaT 1;writeControl timeStep;writeInterval 100;purgeWrite 2;writeFormat ascii;writePrecision 12;runTimeModifiable false;functions {{{functions}}}\n')
        save(target / 'case-metadata.json', {'classification':'conditional_square_duct_not_935_installation',
            'rotor_sha256':sha(source), 'source_length_unit':'mm', 'solver_length_unit':'m',
            'prepared_input_sha256':{str(p.relative_to(target)):sha(p) for p in
                sorted(target.rglob('*')) if p.is_file() and p != target / 'case-metadata.json'},
            'rotor_rpm':rpm, 'specified_volume_flow_m3_s':q, 'density_kg_m3':rho,
            'pressure_report_basis':'area_average_total_pressure_rho_times_p_plus_half_magSqrU',
            'total_pressure_curve_validated':False, 'numerical_acceptance':False})
    save(out / 'receipt.json', {'status':'conditional_MRF_SST_cases_prepared_not_solved',
        'case_sha256':sha(case_path), 'rotor_sha256':sha(source),
        'solver_family':'OpenCFD_v2406', 'mesh_ids':list(config['mesh_cells']),
        'historical_installation_verified':False, 'manufacturing_authorized':False})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(prepare(args.case, args.output))
