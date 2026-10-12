#!/usr/bin/env python3
"""Geometric USD rotor hypothesis and ten conditional material mass/inertia cards."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from build_system_twin import positive
from run_reconstruction import fresh, save, sha
from run_hypothesis_tests import ASSUMPTIONS

STUDY = Path(__file__).resolve().parents[1]


def properties(mesh_mm, density_kg_m3):
    density = positive(density_kg_m3)
    if not isinstance(mesh_mm, trimesh.Trimesh) or not mesh_mm.is_watertight or not mesh_mm.is_winding_consistent:
        raise ValueError('Closed consistently oriented mesh required')
    mesh = mesh_mm.copy(); mesh.apply_scale(.001)
    data = mesh.mass_properties
    if data['volume'] <= 0 or not np.isfinite(mesh.vertices).all():
        raise ValueError('Positive volume and finite geometry required')
    center = data['center_mass']; mass = data['volume'] * density
    inertia = data['inertia'] * density
    origin = inertia + mass * (np.eye(3) * (center @ center) - np.outer(center, center))
    if np.linalg.eigvalsh(inertia).min() <= 0:
        raise ValueError('Positive definite inertia required')
    return {'volume_m3':float(data['volume']), 'mass_kg':float(mass),
        'center_of_mass_m':center.tolist(), 'inertia_about_COM_kg_m2':inertia.tolist(),
        'inertia_about_candidate_axis_origin_kg_m2':origin.tolist(),
        'polar_inertia_about_candidate_z_kg_m2':float(origin[2,2]),
        'geometric_mass_offset_kg_m':float(mass * np.linalg.norm(center[:2])),
        'tip_radius_m':float(np.linalg.norm(mesh.vertices[:,:2],axis=1).max())}


def rotational_scenarios(values):
    results = []
    for rpm in ASSUMPTIONS['rotor_rpm']:
        omega = rpm * math.pi / 30
        for stop in ASSUMPTIONS['stop_time_s']:
            results.append({'rotor_rpm_assumed':rpm, 'stop_time_s_assumed':stop,
                'kinetic_energy_j':.5 * values['polar_inertia_about_candidate_z_kg_m2'] * omega ** 2,
                'deceleration_torque_nm':-values['polar_inertia_about_candidate_z_kg_m2'] * omega / stop,
                'tip_speed_m_s':values['tip_radius_m'] * omega,
                'unbalance_force_n_assumed':ASSUMPTIONS['residual_unbalance_kg_m'] * omega ** 2})
    return results


def build(case_path, output):
    from pxr import Gf, Usd, UsdGeom, UsdPhysics
    case = json.loads(Path(case_path).read_text())
    if case.get('purpose') != 'hypothesis_screen' or case.get('scale_verified') is not False:
        raise ValueError('Only uncalibrated hypotheses may use these material cards')
    source = Path(case['rotor_stl_path'])
    if sha(source) != case['rotor_stl_sha256']:
        raise ValueError('Rotor hash mismatch')
    mesh = trimesh.load_mesh(source, process=True)
    cards_path = STUDY / 'vast-omniverse-screen/materials.json'
    cards = json.loads(cards_path.read_text())['materials']
    materials = {c['id']: properties(mesh, c['density_g_cm3'] * 1000) for c in cards}
    for values in materials.values():
        values['hypothesis_rotational_scenarios'] = rotational_scenarios(values)
    out = fresh(output)
    stage_path = out / 'rotor-hypothesis.usda'
    stage = Usd.Stage.CreateNew(str(stage_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1); UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, '/World'); stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetCustomData({'status':'rotor_hypothesis_only', 'scale_verified':False,
        'historical_assembly_verified':False, 'physical_validation':False})
    scene = UsdPhysics.Scene.Define(stage, '/World/PhysicsScene')
    scene.CreateGravityMagnitudeAttr(0)
    rotor = UsdGeom.Xform.Define(stage, '/World/Rotor')
    body = UsdPhysics.RigidBodyAPI.Apply(rotor.GetPrim())
    body.CreateRigidBodyEnabledAttr(True); body.CreateKinematicEnabledAttr(True)
    rotor.GetPrim().SetCustomData({'rotation':'prescribed_one_revolution_not_solved_dynamics',
        'input_sha256':sha(source), 'mechanical_support_and_joints_defined':False})
    rpm = positive(case['rotor_rpm'])
    stage.SetTimeCodesPerSecond(rpm / 60); stage.SetStartTimeCode(0); stage.SetEndTimeCode(1)
    rotate = rotor.AddRotateZOp(); rotate.Set(0, Usd.TimeCode(0)); rotate.Set(360, Usd.TimeCode(1))
    geometry = UsdGeom.Mesh.Define(stage, '/World/Rotor/Geometry')
    geometry.CreatePointsAttr([Gf.Vec3f(*p) for p in mesh.vertices * .001])
    geometry.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
    geometry.CreateFaceVertexIndicesAttr(mesh.faces.reshape(-1).tolist())
    geometry.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    geometry.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    geometry.CreateExtentAttr([Gf.Vec3f(*p) for p in mesh.bounds * .001])
    geometry.CreateDisplayColorAttr([Gf.Vec3f(.65,.69,.73)])
    UsdPhysics.CollisionAPI.Apply(geometry.GetPrim()).CreateCollisionEnabledAttr(True)
    UsdPhysics.MeshCollisionAPI.Apply(geometry.GetPrim()).CreateApproximationAttr('none')
    variants = rotor.GetPrim().GetVariantSets().AddVariantSet('material')
    for card in cards:
        name = card['id']; variants.AddVariant(name); variants.SetVariantSelection(name)
        result = materials[name]
        eigenvalues, axes = np.linalg.eigh(result['inertia_about_COM_kg_m2'])
        if np.linalg.det(axes) < 0:
            axes[:,0] *= -1
        rotation = Gf.Matrix4d(Gf.Matrix3d(*axes.T.reshape(-1).tolist()), Gf.Vec3d(0)).ExtractRotationQuat()
        with variants.GetVariantEditContext():
            mass = UsdPhysics.MassAPI.Apply(rotor.GetPrim())
            mass.CreateMassAttr(result['mass_kg'])
            mass.CreateCenterOfMassAttr(Gf.Vec3f(*result['center_of_mass_m']))
            mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*eigenvalues))
            mass.CreatePrincipalAxesAttr(Gf.Quatf(rotation.GetReal(), Gf.Vec3f(*rotation.GetImaginary())))
            rotor.GetPrim().SetCustomDataByKey('material_card_scope', card['card_scope'])
    variants.SetVariantSelection('alsi10mg')
    stage.GetRootLayer().Save()
    reread = Usd.Stage.Open(str(stage_path))
    if not reread or UsdGeom.GetStageMetersPerUnit(reread) != 1 or not reread.GetDefaultPrim():
        raise ValueError('USD reread failed')
    for name, result in materials.items():
        prim = reread.GetPrimAtPath('/World/Rotor'); prim.GetVariantSets().GetVariantSet('material').SetVariantSelection(name)
        api = UsdPhysics.MassAPI(prim)
        if not np.isclose(api.GetMassAttr().Get(), result['mass_kg'], rtol=1e-6):
            raise ValueError('USD variant mass mismatch')
        axes = np.asarray(Gf.Matrix4d(1).SetRotate(Gf.Quatd(api.GetPrincipalAxesAttr().Get())))[:3,:3].T
        tensor = axes @ np.diag(api.GetDiagonalInertiaAttr().Get()) @ axes.T
        expected_tensor = np.asarray(result['inertia_about_COM_kg_m2'])
        if np.linalg.norm(tensor - expected_tensor) / np.linalg.norm(expected_tensor) > 1e-5:
            raise ValueError('USD variant inertia axes or units mismatch')
    if sha(source) != case['rotor_stl_sha256']:
        raise ValueError('Input changed during USD export')
    save(out / 'mass-inertia.json', {'geometry_sha256':sha(source), 'materials_sha256':sha(cards_path),
        'purpose':'hypothesis_screen', 'scale_verified':False, 'materials':materials,
        'residual_unbalance_measured':False, 'strength_or_fatigue_validated':False,
        'scenario_definition':'existing_hypothesis_tests_rpm_stop_unbalance_assumptions',
        'scenario_assumptions_program_sha256':sha(Path(__file__).with_name('run_hypothesis_tests.py'))})
    save(out / 'receipt.json', {'status':'geometric_rotor_twin_hypothesis_not_complete_system',
        'geometry_sha256':sha(source), 'case_sha256':sha(case_path), 'USD_version':Usd.GetVersion(),
        'meters_per_unit':1, 'material_variants':len(materials), 'triangles':len(mesh.faces),
        'USD_reread_passed':True, 'prescribed_rotation_rpm':rpm, 'dynamic_simulation_executed':False,
        'bench_measurements_used':False, 'manufacturing_authorized':False,
        'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.case, args.output))
