#!/usr/bin/env python3
"""Independent ideal-bearing spin and quadratic-drag checks; no contacts or elastic blades."""
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    data = json.loads((directory / 'newton/newton-summary.json').read_text())
    source = directory / 'physx-spin.usda'
    if args.prepare_only:
        from scipy.spatial.transform import Rotation
        inertia, axes = np.linalg.eigh(np.array(data['inertia_about_com_kg_m2']))
        if np.linalg.det(axes) < 0: axes[:, 0] *= -1
        q = Rotation.from_matrix(axes).as_quat()
        vector = lambda values: '(' + ', '.join(str(float(v)) for v in values) + ')'
        if source.exists(): raise FileExistsError(source)
        source.write_text('''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World" {
    def PhysicsScene "Physics" {
        float physics:gravityMagnitude = 0
        vector3f physics:gravityDirection = (0, 0, -1)
    }
    def Xform "Rotor" (
        prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI", "PhysxRigidBodyAPI"]
    ) {
        bool physics:rigidBodyEnabled = true
        float physics:mass = MASS
        point3f physics:centerOfMass = COM
        float3 physics:diagonalInertia = INERTIA
        quatf physics:principalAxes = AXES
        vector3f physics:angularVelocity = (0, 0, 18000)
        float physxRigidBody:angularDamping = 0
        float physxRigidBody:maxAngularVelocity = 36000
        def Xform "Visual" (prepend references = @./components.usdc@</World/Rotor>) {}
    }
    def PhysicsRevoluteJoint "IdealBearing" {
        rel physics:body1 = </World/Rotor>
        uniform token physics:axis = "Z"
    }
}
'''.replace('MASS', str(data['mass_kg'])).replace('COM', vector(data['center_of_mass_m']))
       .replace('INERTIA', vector(inertia)).replace('AXES', vector([q[3], *q[:3]])))
        print('PhysX stage prepared, not yet simulated:', source)
        return
    assert source.is_file()
    import ovphysx
    from ovphysx import PhysX
    from ovphysx.types import TensorType
    # Pinned image ships 0.4.13: use its documented USD-owned API, not newer OVStage APIs.
    assert ovphysx.__version__ == '0.4.13'
    physics = PhysX(device='cpu')
    binding = velocity_binding = wrench_binding = None
    try:
        physics.add_usd(str(source)); physics.wait_all()
        binding = physics.create_tensor_binding(pattern='/World/Rotor', tensor_type=TensorType.RIGID_BODY_POSE)
        assert tuple(binding.shape) == (1, 7)
        poses = np.zeros(binding.shape, dtype=np.float32)
        for i in range(200): physics.step_sync(.00001, i * .00001)
        binding.read(poses)
        assert np.isfinite(poses).all()
        xyzw = poses[0, 3:7]
        angle = float(2 * np.arctan2(abs(xyzw[2]), abs(xyzw[3])))
        expected = 3000 * np.pi / 30 * .002
        error = abs(angle - expected)
        assert error < .002 and np.linalg.norm(poses[0, :3]) < 1e-5
        velocity_binding = physics.create_tensor_binding(pattern='/World/Rotor', tensor_type=TensorType.RIGID_BODY_VELOCITY)
        wrench_binding = physics.create_tensor_binding(pattern='/World/Rotor', tensor_type=TensorType.RIGID_BODY_WRENCH)
        velocity = np.zeros(velocity_binding.shape, dtype=np.float32)
        wrench = np.zeros(wrench_binding.shape, dtype=np.float32)
        assert tuple(velocity.shape) == (1, 6) and tuple(wrench.shape) == (1, 9)
        velocity_binding.read(velocity)
        free_spin_final_omega = float(velocity[0, 5])
        # Start the independent loaded case at the same speed as Newton.
        velocity[:] = 0.
        velocity[0, 5] = 3000 * np.pi / 30
        velocity_binding.write(velocity)
        velocity_binding.read(velocity)
        initial_omega = float(velocity[0, 5])
        assert abs(initial_omega - 3000 * np.pi / 30) < .01
        coefficient = data['drag_coefficient_Nm_per_rad_s_squared']
        trace = [[0., initial_omega]]
        for i in range(1000):
            w = float(velocity[0, 5])
            wrench[0, 5] = -coefficient * w * abs(w)
            wrench_binding.write(wrench)
            physics.step_sync(.0001, .002 + i * .0001)
            velocity_binding.read(velocity)
            trace.append([(i + 1) * .0001, float(velocity[0, 5])])
        trace = np.array(trace)
        expected_speed = initial_omega / (1 + coefficient * initial_omega * trace[:, 0] / data['polar_inertia_about_shaft_kg_m2'])
        coast_error = float(np.max(np.abs(trace[:, 1] - expected_speed)) / initial_omega)
        assert np.isfinite(trace).all() and coast_error < .001 and trace[-1, 1] < initial_omega
        np.savetxt(directory / 'physx-coastdown.csv', trace, delimiter=',', header='time_s,omega_rad_s', comments='')
        report = {'status': 'passed_ideal_bearing_spin_and_quadratic_drag', 'ovphysx_version': ovphysx.__version__,
            'physics_device': 'cpu', 'duration_s': .002, 'steps': 200,
            'expected_angle_rad': expected, 'observed_angle_rad': angle, 'absolute_angle_error_rad': error,
            'pose_xyzw': poses.tolist(), 'cfd_drag_included': True, 'collisions_simulated': False,
            'free_spin_final_omega_rad_s': free_spin_final_omega,
            'loaded_case_initial_omega_rad_s': initial_omega,
            'coastdown_duration_s': .1, 'coastdown_dt_s': .0001,
            'coastdown_relative_analytic_error': coast_error,
            'coastdown_final_rpm': float(trace[-1, 1] * 30 / np.pi),
            'pmb240a_simulated': False, 'manufacturing_authorized': False}
        (directory / 'physx-summary.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        if binding: binding.destroy()
        if velocity_binding: velocity_binding.destroy()
        if wrench_binding: wrench_binding.destroy()
        physics.release()


if __name__ == '__main__': main()
