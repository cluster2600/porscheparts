#!/usr/bin/env python3
"""Compare completed AMB2018 thermal histories; never authorize head printing."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

FATAL=re.compile(r'FOAM FATAL|^\s*Floating point exception\b|\b(?:nan|inf)\b',re.I|re.M)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def series(path):
    values=np.loadtxt(path,comments='#',ndmin=2)
    if (values.shape[1]!=2 or len(values)<2 or not np.isfinite(values).all()
            or values[0,0]!=0 or values[-1,0]!=.004 or (np.diff(values[:,0])<=0).any()):
        raise ValueError('complete_finite_strictly_ordered_0_to_4ms_series_required')
    return values


def field(path):
    match=re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',path.read_text(),re.S)
    if not match: raise ValueError('nonuniform_ascii_scalar_field_required')
    data=np.fromstring(match[2],sep=' ')
    if int(match[1])!=56250 or len(data)!=56250 or not np.isfinite(data).all():
        raise ValueError('complete_56250_cell_field_required')
    return data


def analyze(case):
    paths=[case/'postProcessing'/name/'0/volFieldValue.dat' for name in
           ('temperatureMaximum','temperatureMinimum','laserPower')]
    data=[series(p) for p in paths]
    if not all(np.array_equal(data[0][:,0],v[:,0]) for v in data[1:]):
        raise ValueError('synchronized_diagnostics_required')
    logpath=case/'log.additiveFoam';log=logpath.read_text()
    if (FATAL.search(log)
            or re.search(r'Solving for (?:p_rgh|U)',log)
            or 'Mesh OK.' not in (case/'log.checkMesh').read_text()):
        raise ValueError('successful_mesh_and_finite_thermal_only_log_required')
    steps=np.array([float(v) for v in re.findall(r'^Time = ([\d.eE+-]+)$',log,re.M)])
    if not np.array_equal(steps,data[0][1:,0]): raise ValueError('log_series_time_grid_mismatch')
    final_residuals=[]
    for block in re.split(r'^Time = [\d.eE+-]+$',log,flags=re.M)[1:]:
        r=re.findall(r'Thermo: iteration \d+ residual: ([\d.eE+-]+)',block)
        if not r: raise ValueError('missing_thermal_iteration_result')
        final_residuals.append(float(r[-1]))
    times=data[0][:,0];power=data[2][:,1]
    # qDot is the source averaged over the preceding solver step, not a point sample.
    energy=float(np.dot(np.diff(times),power[1:]))
    history=dict(steps=len(steps),peak_temperature_K=float(data[0][:,1].max()),
        minimum_temperature_K=float(data[1][:,1].min()),final_maximum_temperature_K=float(data[0][-1,1]),
        absorbed_energy_J=energy,nominal_absorbed_energy_J=.14784,
        relative_input_energy_difference=abs(energy/.14784-1),
        max_final_phase_fraction_residual=float(max(final_residuals)),
        steps_above_thermo_tolerance=sum(r>=1e-8 for r in final_residuals),
        log_sha256=sha(logpath),series_sha256={p.parents[1].name:sha(p) for p in paths})
    return history,data[0],field(case/'0.002/T')


def run(args):
    if args.output.exists(): raise ValueError('fresh_output_required')
    control_a=(args.base/'system/controlDict').read_text()
    control_b=(args.refined/'system/controlDict').read_text()
    expected=control_a.replace('maxDi           1;','maxDi           0.5;').replace('maxAlphaCo      1;','maxAlphaCo      0.5;')
    if expected==control_a or expected!=control_b: raise ValueError('only_declared_time_limit_changes_allowed')
    names=('system/blockMeshDict','system/fvSolution','system/fvSchemes','constant/scanPath',
           'constant/transportProperties','constant/heatSourceDict','0/T','0/U','0/p_rgh')
    if any(sha(args.base/p)!=sha(args.refined/p) for p in names): raise ValueError('case_physics_or_mesh_changed')
    if sha(args.base/'system/blockMeshDict')!='a0467739c03f5e7baaacdcc55ae37541ded0274de77b969d41ead511c525d59d':
        raise ValueError('fixed_upstream_structured_grid_required')
    a,ta,fa=analyze(args.base);b,tb,fb=analyze(args.refined)
    result=dict(schema='m64-amb2018-thermal-comparison/v1',status='completed_diagnostics_only',
        source_sha256=sha(Path(__file__)),base=a,refined=b,
        unchanged_inputs_sha256={n:sha(args.base/n) for n in names},
        control_sha256=[sha(p/'system/controlDict') for p in (args.base,args.refined)],
        temperature_field_2ms_sha256=[sha(p/'0.002/T') for p in (args.base,args.refined)],
        peak_temperature_relative_difference=abs(a['peak_temperature_K']/b['peak_temperature_K']-1),
        field_2ms_temperature_rise_relative_L2=float(np.linalg.norm(fa-fb)/np.linalg.norm(fb-300)),
        field_2ms_maximum_absolute_difference_K=float(np.max(np.abs(fa-fb))),
        spatial_convergence_demonstrated=False,full_energy_balance_checked=False,
        melt_flow_solved=False,head_print_simulated=False,manufacturing_authorized=False)
    args.output.mkdir(mode=0o700)
    (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for t,label in ((ta,'Time limits 1'),(tb,'Time limits 0.5')): axes[0].plot(t[:,0]*1000,t[:,1],label=label)
    axes[0].set_xlabel('Time (ms)');axes[0].set_ylabel('Maximum temperature (K)');axes[0].legend();axes[0].grid(alpha=.2)
    im=axes[1].imshow(fb.reshape(15,25,150)[:,12,:],origin='lower',aspect='auto',extent=(-.5,2.5,-.3,0),cmap='inferno')
    axes[1].set_title('Refined time limits, y = 0, t = 2 ms');axes[1].set_xlabel('x (mm)');axes[1].set_ylabel('z (mm)');fig.colorbar(im,ax=axes[1],label='Temperature (K)')
    fig.suptitle('AdditiveFOAM IN625 reference track — thermal only, NOT a cylinder-head print')
    fig.tight_layout();fig.savefig(args.output/'thermal-reference.png',dpi=150);plt.close(fig)
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base','refined','output'):parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
