#!/usr/bin/env python3
"""Adapt the conditional duct recipe to the qualified Foundation 13 runtime."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from prepare_candidate_cfd import prepare as prepare_parent
from prepare_conforming_surface import load_surface
from prepare_aircooled_openfoam_f34 import header
from run_reconstruction import save, sha


def write_si_obj(path, vertices, faces):
    """Retain indexed double coordinates instead of rounding an SI binary STL."""
    vertices = np.asarray(vertices, dtype=np.float64) * .001
    with Path(path).open('x') as stream:
        np.savetxt(stream, vertices, fmt='v %.17g %.17g %.17g')
        stream.write('g rotor\n')
        np.savetxt(stream, faces.astype(np.int64) + 1, fmt='f %d %d %d')
    with Path(path).open() as stream:
        for expected in vertices:
            row = stream.readline().split()
            if row[0] != 'v' or not np.array_equal(np.array(row[1:], dtype=float), expected):
                raise ValueError('OBJ coordinate transport changed the SI surface')
        if stream.readline() != 'g rotor\n':
            raise ValueError('Single rotor region required')
        for expected in faces:
            row = stream.readline().split()
            if row[0] != 'f' or not np.array_equal(np.array(row[1:], dtype=int) - 1, expected):
                raise ValueError('OBJ connectivity transport changed the surface')
        if stream.read():
            raise ValueError('Unexpected OBJ payload')


def prepare(case_path, output):
    case = json.loads(Path(case_path).read_text())
    if case.get('scale_verified') is not False or case.get('axis_verified') is not False:
        raise ValueError('This recipe requires explicitly unverified physical scale and axis')
    config = case['cfd']
    if config.get('assumed_m_per_source_unit') != .001:
        raise ValueError('Parent recipe requires the explicit 0.001 m/source-unit hypothesis')
    vertices, faces = load_surface(config['rotor_bundle_path'], config['rotor_bundle_sha256'],
                                   config['rotor_stl_path'], config['rotor_stl_sha256'])
    output = prepare_parent(case_path, output)
    (output / 'receipt.json').rename(output / 'parent-v2406-receipt.json')
    obj = output / 'rotor-si.obj'
    write_si_obj(obj, vertices, faces)
    (output / 'rotor-si.stl').unlink()
    for name in config['mesh_cells']:
        target = output / name
        (target / 'case-metadata.json').rename(target / 'parent-v2406-metadata.json')
        (target / 'constant/triSurface/rotor.stl').unlink()
        shutil.copyfile(obj, target / 'constant/triSurface/rotor.obj')
        for obsolete in ('transportProperties', 'turbulenceProperties'):
            (target / 'constant' / obsolete).unlink()
        def write(relative, text):
            (target / relative).write_text(header(Path(relative).name) + text)
        snappy = target / 'system/snappyHexMeshDict'
        text = snappy.read_text().replace('rotor.stl', 'rotor.obj')
        snappy.write_text(text.replace('maxGlobalCells 5000000;', 'maxGlobalCells 2000000;'))
        write('constant/physicalProperties', 'viscosityModel constant;\n'
              f'nu [0 2 -1 0 0 0 0] {config["kinematic_viscosity_m2_s"]};\n')
        write('constant/momentumTransport', 'simulationType RAS;\nRAS {model kOmegaSST;turbulence on;printCoeffs on;}\n')
        write('constant/MRFProperties', 'rotor {cellZone rotorZone;origin (0 0 0);axis (0 0 1);'
              f'omega {config["rotor_rpm"]} [rpm];}}\n')
        u = target / '0/U'
        text = u.read_text()
        old = 'rotor {type fixedValue;value uniform (0 0 0);}'
        if text.count(old) != 1:
            raise ValueError('Parent rotor boundary changed')
        u.write_text(text.replace(old, 'rotor {type MRFnoSlip;}'))
        # Foundation uses limited corrected; the OpenCFD alias is not assumed.
        for filename in ('fvSchemes',):
            path = target / 'system' / filename
            path.write_text(path.read_text().replace('limited 0.5', 'limited corrected 0.5'))
        rho = config['air_density_kg_m3']
        functions = ('velocitySquared {type magSqr;libs ("libfieldFunctionObjects.so");field U;result UMagSqr;'
                     'executeControl timeStep;executeInterval 1;writeControl timeStep;writeInterval 10;}\n'
                     f'rotorForces {{type forces;libs ("libforces.so");patches (rotor);rho rhoInf;rhoInf {rho};'
                     'CofR (0 0 0);writeControl timeStep;writeInterval 10;}\n')
        for patch in ('inlet', 'outlet'):
            functions += (f'{patch}Flow {{type surfaceFieldValue;libs ("libfieldFunctionObjects.so");'
                          f'patch {patch};operation sum;fields (phi);writeFields false;'
                          'writeControl timeStep;writeInterval 10;}\n'
                          f'{patch}Pressure {{type surfaceFieldValue;libs ("libfieldFunctionObjects.so");'
                          f'patch {patch};operation average;weightField phi;fields (p UMagSqr);writeFields false;'
                          'writeControl timeStep;writeInterval 10;}\n')
        write('system/controlDict', 'solver incompressibleFluid;startFrom startTime;startTime 0;stopAt endTime;'
              f'endTime {config["iterations"]};deltaT 1;writeControl timeStep;writeInterval 100;purgeWrite 2;'
              'writeFormat ascii;writePrecision 14;runTimeModifiable false;functions {' + functions + '}\n')
        inputs = {str(p.relative_to(target)): sha(p) for p in sorted(target.rglob('*')) if p.is_file()}
        save(target / 'case-metadata.json', {
            'classification': 'conditional_square_duct_not_935_installation', 'solver_family': 'OpenFOAM_Foundation_13',
            'geometry_sha256': config['rotor_stl_sha256'], 'bundle_sha256': config['rotor_bundle_sha256'],
            'source_length_unit': 'uncalibrated_scan_unit', 'assumed_m_per_source_unit': .001,
            'solver_length_unit': 'm', 'scale_verified': False, 'axis_verified': False,
            'surface_vertices': len(vertices), 'surface_triangles': len(faces),
            'double_precision_SI_transport_exact': True, 'SI_OBJ_sha256': sha(obj),
            'rotor_rpm_assumed': config['rotor_rpm'], 'specified_volume_flow_m3_s': config['flow_m3_s'],
            'density_kg_m3_assumed': rho, 'pressure_report_basis': 'flux_weighted_rho_times_p_plus_half_magSqrU',
            'pressure_curve_validated': False, 'numerical_acceptance': False, 'manufacturing_authorized': False,
            'prepared_input_sha256': inputs})
    save(output / 'receipt.json', {
        'status': 'conditional_Foundation13_MRF_SST_prepared_not_solved', 'source_sha256': sha(__file__),
        'parent_source_sha256': sha(Path(__file__).with_name('prepare_candidate_cfd.py')),
        'case_sha256': sha(case_path), 'solver_family': 'OpenFOAM_Foundation_13',
        'historical_installation_verified': False, 'numerical_acceptance': False, 'manufacturing_authorized': False})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(prepare(args.case, args.output))
