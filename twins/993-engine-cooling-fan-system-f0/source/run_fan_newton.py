#!/usr/bin/env python3
"""Rotor-only coast-down: Newton Featherstone + Warp, driven by an exploratory CFD point."""
import argparse
import hashlib
import json
from pathlib import Path

import newton
from newton.solvers import SolverFeatherstone
import numpy as np
import trimesh
import warp as wp

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]


@wp.kernel
def aero_drag(velocity: wp.array(dtype=float), coefficient: float, torque: wp.array(dtype=float)):
    w = velocity[0]
    torque[0] = -coefficient * w * wp.abs(w)


def simulate(mass, com, inertia, omega, coefficient, dt):
    builder = newton.ModelBuilder(gravity=0.0)
    body = builder.add_link(mass=mass, com=wp.vec3(*com), inertia=wp.mat33(*inertia.ravel()), label='FanRotor')
    joint = builder.add_joint_revolute(-1, body, axis=wp.vec3(0, 0, 1), damping=0., armature=0.,
        target_ke=0., target_kd=0., limit_lower=-1.e6, limit_upper=1.e6)
    builder.add_articulation([joint])
    builder.joint_qd[0] = omega
    model = builder.finalize(device='cpu')
    a, b = model.state(), model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, a)
    control = model.control()
    solver = SolverFeatherstone(model, angular_damping=0.)
    rows = [[0., 0., omega]]
    for i in range(round(.1 / dt)):
        a.clear_forces()
        wp.launch(aero_drag, dim=1, inputs=[a.joint_qd, coefficient], outputs=[control.joint_f], device='cpu')
        solver.step(a, b, control, None, dt)
        a, b = b, a
        rows.append([(i + 1) * dt, float(a.joint_q.numpy()[0]), float(a.joint_qd.numpy()[0])])
    return np.array(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source = ROOT / 'work/fan-aerodynamics/print-alternator-body160-pitch-plus-100k/analysis-mm.stl'
    mesh = trimesh.load_mesh(source, process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent
    mesh.apply_scale(.001)
    mesh.density = 2670.  # Candidate AlSi10Mg density; no lot or porosity calibration.
    mass, com, inertia = float(mesh.mass), mesh.center_mass, mesh.moment_inertia
    polar = float(inertia[2, 2] + mass * np.dot(com[:2], com[:2]))
    flow_path = STUDY / 'print-and-flow-trial-results.json'
    flow = json.loads(flow_path.read_text())['variants']['pitch-plus']['flow_summary']
    omega = flow['rpm'] * np.pi / 30
    coefficient = abs(flow['mean_fluid_torque_Nm']) / omega**2
    assert mass > 0 and polar > 0 and coefficient > 0
    coarse = simulate(mass, com, inertia, omega, coefficient, .0002)
    fine = simulate(mass, com, inertia, omega, coefficient, .0001)
    analytic = omega / (1 + coefficient * omega * fine[:, 0] / polar)
    error = float(np.max(np.abs(fine[:, 2] - analytic)) / omega)
    refinement = float(abs(coarse[-1, 2] - fine[-1, 2]) / omega)
    assert np.isfinite(fine).all() and error < 1e-4 and refinement < 1e-4
    assert np.all(np.diff(fine[:, 2]) <= 0) and fine[-1, 2] > 0
    args.output.mkdir(parents=True)
    np.savetxt(args.output / 'rotation.csv', fine, delimiter=',', header='time_s,angle_rad,omega_rad_s', comments='')
    report = {'scope': 'isolated_rotor_coast_down_quadratic_drag_not_vehicle_dynamics',
        'runtime': {'newton': newton.__version__, 'warp': wp.__version__, 'device': 'cpu'},
        'mass_kg': mass, 'density_kg_m3': 2670., 'center_of_mass_m': com.tolist(),
        'inertia_about_com_kg_m2': inertia.tolist(), 'polar_inertia_about_shaft_kg_m2': polar,
        'initial_rpm': flow['rpm'], 'final_rpm': float(fine[-1, 2] * 30 / np.pi),
        'duration_s': .1, 'dt_s': .0001, 'drag_coefficient_Nm_per_rad_s_squared': coefficient,
        'maximum_relative_analytic_speed_error': error, 'relative_refinement_difference': refinement,
        'cfd_converged': flow['numerical_window_checks_passed'], 'pmb_240a_inertia_or_load_included': False,
        'belt_bearings_fatigue_or_elastic_blades_simulated': False,
        'manufacturing_authorized': False,
        'input_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, flow_path, Path(__file__)]}}
    (args.output / 'newton-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
