#!/usr/bin/env python3
"""Check whether a stationary gas remains stationary across a staircase MRF zone."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from prepare_case import IMAGE, header, sha
from run_cartesian_pilot import verify


def prepare(parent, output, omega):
    verify(parent)
    output.mkdir(parents=True, exist_ok=False)
    for directory in ('0', 'constant', 'system'):
        (output / directory).mkdir()
    sources = {}
    for name in ('system/fvSchemes', 'system/fvSolution', 'constant/thermophysicalProperties'):
        sources[name] = sha(parent / name)
        (output / name).write_bytes((parent / name).read_bytes())
    def dictionary(name, body):
        (output / name).write_text('FoamFile {version 2.0; format ascii; class dictionary; object ' + Path(name).name + ';}\n' + body + '\n')
    dictionary('system/blockMeshDict', '''vertices ((-.04 -.04 -.04)(.04 -.04 -.04)(.04 .04 -.04)(-.04 .04 -.04)(-.04 -.04 .04)(.04 -.04 .04)(.04 .04 .04)(-.04 .04 .04));
blocks (hex (0 1 2 3 4 5 6 7) (20 20 20) simpleGrading (1 1 1)); edges ();
boundary (walls {type wall; faces ((0 3 2 1)(4 5 6 7)(0 1 5 4)(1 2 6 5)(2 3 7 6)(3 0 4 7));});''')
    dictionary('system/topoSetDict', '''actions (
{name rotorCells; type cellSet; action new; source cylinderToCell; p1 (0 0 -.05); p2 (0 0 .05); radius .02;}
{name rotorZone; type cellZoneSet; action new; source setToCellZone; set rotorCells;});''')
    dictionary('constant/MRFProperties', f'MRF {{active yes; cellZone rotorZone; origin (0 0 0); axis (0 0 1); omega constant {omega:.15g}; nonRotatingPatches (walls);}}')
    dictionary('constant/turbulenceProperties', 'simulationType laminar;')
    for name, dims, value, kind, boundary in (
        ('U','0 1 -1 0 0 0 0','(0 0 0)','volVectorField','noSlip'),
        ('p','1 -1 -2 0 0 0 0','101325','volScalarField','zeroGradient'),
        ('T','0 0 0 1 0 0 0','298.15','volScalarField','zeroGradient')):
        (output / ('0/'+name)).write_text(header(name,kind)+f'dimensions [{dims}];\ninternalField uniform {value};\nboundaryField {{walls {{type {boundary};}}}}\n')
    dictionary('system/controlDict', '''application rhoPimpleFoam; startFrom startTime; startTime 0; stopAt endTime;
endTime 2e-5; deltaT 1e-7; writeControl timeStep; writeInterval 200; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off; timeFormat general; timePrecision 12; runTimeModifiable false;
functions {
velocitySquared {type magSqr; libs ("libfieldFunctionObjects.so"); field U; result UMagSqr; executeControl timeStep; executeInterval 1; writeControl none;}
minima {type volFieldValue; libs ("libfieldFunctionObjects.so"); regionType all; operation min; fields (p T UMagSqr); writeFields false; writeControl timeStep; writeInterval 1;}
maxima {type volFieldValue; libs ("libfieldFunctionObjects.so"); regionType all; operation max; fields (p T UMagSqr); writeFields false; writeControl timeStep; writeInterval 1;}
}''')
    files = {str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}
    manifest = {'schema':'static-mrf-equilibrium-witness/v1','source_sha256':sha(Path(__file__)), 'parent_file_sha256':sources,
                'image':IMAGE,'omega_rad_s':omega,'expected':'Uniform inertial gas at rest; all physical walls stationary; no rotor, forcing, heat or pressure difference.',
                'criteria':{'max_abs_p_error_Pa':.001,'max_abs_T_error_K':1e-6,'max_speed_m_s':1e-8},
                'file_sha256':files,'performance_ranking_authorized':False}
    (output / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def assess(minima, maxima, criteria):
    if minima.shape != maxima.shape or minima.ndim != 2 or minima.shape[1] != 4 or not np.isfinite(minima).all() or not np.isfinite(maxima).all() or not np.array_equal(minima[:,0], maxima[:,0]):
        raise ValueError('Complete matching finite native histories required')
    values = {'max_abs_p_error_Pa':float(max(abs(minima[:,1]-101325).max(),abs(maxima[:,1]-101325).max())),
              'max_abs_T_error_K':float(max(abs(minima[:,2]-298.15).max(),abs(maxima[:,2]-298.15).max())),
              'max_speed_m_s':float(np.sqrt(maxima[:,3].max()))}
    return {'observed':values,'stationary_equilibrium_reproduced':all(values[k] <= criteria[k] for k in values)}


def run(case, manifest):
    command = 'source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; blockMesh > log.blockMesh 2>&1 && topoSet > log.topoSet 2>&1 && checkMesh -allTopology -allGeometry > log.checkMesh 2>&1 && rhoPimpleFoam > log.rhoPimpleFoam 2>&1'
    result = subprocess.run(['docker','run','--rm','--pull=never','--platform','linux/arm64','--network','none','--read-only',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g',
        '--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}',
        '--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c',
        'timeout --signal=TERM --kill-after=10s 240 bash -c ' + __import__('shlex').quote(command)],capture_output=True,text=True,timeout=270)
    report = {'native_exit_code':result.returncode,'performance_ranking_authorized':False,'stderr':result.stderr}
    if result.returncode == 0:
        assert 'Mesh OK.' in (case/'log.checkMesh').read_text()
        assert (case/'log.rhoPimpleFoam').read_text().rstrip().endswith('End')
        low=np.loadtxt(case/'postProcessing/minima/0/volFieldValue.dat')
        high=np.loadtxt(case/'postProcessing/maxima/0/volFieldValue.dat')
        assert len(low)==200 and abs(low[-1,0]-2e-5)<1e-15
        report.update(assess(low,high,manifest['criteria']))
    assert all(sha(case/name)==digest for name,digest in manifest['file_sha256'].items())
    report['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
    (case/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return {k:v for k,v in report.items() if k!='output_sha256'}


if __name__ == '__main__':
    parent, root = map(Path,sys.argv[1:])
    for name, omega in (('inertial-control',0.),('staircase-mrf',10471.975511966)):
        case=root/name
        print(name,json.dumps(run(case,prepare(parent,case,omega))),flush=True)
