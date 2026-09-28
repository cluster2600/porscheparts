#!/usr/bin/env python3
"""Assemble the current fan and numerical fields as a portable, evidence-labelled OpenUSD twin."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade, UsdUtils, UsdValidation, Vt
from scipy.spatial import cKDTree
import trimesh

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/fan-aerodynamics'
READ_PATCH = runpy.run_path(str(STUDY / 'source/audit_fan_pressure_physicsnemo.py'))['read_patch']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def stage(path):
    s = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(s, 1.)
    UsdGeom.SetStageUpAxis(s, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(s, '/World').GetPrim()
    s.SetDefaultPrim(root)
    return s


def mesh(s, path, vertices, faces, colors):
    m = UsdGeom.Mesh.Define(s, path)
    vertices = np.asarray(vertices, dtype=np.float32)
    assert np.isfinite(vertices).all()
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(vertices))
    m.CreateFaceVertexCountsAttr([len(f) for f in faces])
    m.CreateFaceVertexIndicesAttr(np.concatenate(faces).astype(np.int32).tolist())
    m.CreateSubdivisionSchemeAttr('none')
    m.CreateDoubleSidedAttr(True)
    m.CreateExtentAttr([Gf.Vec3f(*vertices.min(0).tolist()), Gf.Vec3f(*vertices.max(0).tolist())])
    colors = np.asarray(colors, dtype=np.float32).reshape(-1, 3)
    m.CreateDisplayColorPrimvar('uniform' if len(colors) > 1 else 'constant').Set(Vt.Vec3fArray.FromNumpy(colors))
    # Display colour is visualization only, not an inferred physical material.
    mat = UsdShade.Material.Define(s, path + '/DisplayMaterial')
    reader = UsdShade.Shader.Define(s, path + '/DisplayMaterial/Color')
    reader.CreateIdAttr('UsdPrimvarReader_float3')
    reader.CreateInput('varname', Sdf.ValueTypeNames.String).Set('displayColor')
    shader = UsdShade.Shader.Define(s, path + '/DisplayMaterial/Surface')
    shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(reader.ConnectableAPI(), 'result')
    shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.38)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
    return m


def scalar(m, name, values):
    UsdGeom.PrimvarsAPI(m).CreatePrimvar(name, Sdf.ValueTypeNames.FloatArray, 'uniform').Set(np.asarray(values, dtype=np.float32).tolist())


def build(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'fan-twin.usda'
    if target.exists(): raise FileExistsError(target)
    source = WORK / 'print-alternator-body160-pitch-plus-100k/analysis-mm.stl'
    reduction = source.parent / 'surface-reduction.json'
    assert json.loads(reduction.read_text())['analysis_sha256'] == sha(source)
    geometry = WORK / 'turbo-245-alternator-body160-pitch-plus'
    original = geometry / 'organic-fan-mm.stl'
    assert json.loads(reduction.read_text())['source_sha256'] == sha(original)
    alt = geometry / 'alternator-and-supports-mm.stl'
    rotor = trimesh.load_mesh(source, process=True)
    proxy = trimesh.load_mesh(alt, process=True)
    assert rotor.is_watertight and rotor.is_winding_consistent
    thermal_dir = WORK / 'zrapid-confirmation-20260928T121729Z'
    thermal_report = json.loads((thermal_dir / 'thermal-summary.json').read_text())
    assert thermal_report['surface_sha256'] == sha(source)
    with np.load(thermal_dir / 'thermal-fields.npz', allow_pickle=False) as data:
        mask = data['is_part']
        # LPBF coordinates start at mesh.min, then add a 6 mm build standoff.
        centres = data['centres_mm'][mask] + rotor.bounds[0] - [0, 0, 6]
        distance, indices = cKDTree(centres).query(rotor.triangles_center)
        temps = data['peak_temperature_k'][mask][indices]
    assert np.isfinite(temps).all() and distance.max() < 3
    from matplotlib import colormaps
    thermal_colors = colormaps['inferno'](np.clip((temps - 303.15) / 17, 0, 1))[:, :3]
    assets = stage(output / 'components.usdc')
    rm = mesh(assets, '/World/Rotor', rotor.vertices * .001, rotor.faces, [[.65, .68, .72]])
    rm.GetPrim().SetCustomData({'sourceSha256': sha(source), 'candidateMaterial': 'AlSi10Mg', 'geometry': 'PicoGK_analysis_100k'})
    tm = mesh(assets, '/World/ThermalRotor', rotor.vertices * .001, rotor.faces, thermal_colors)
    scalar(tm, 'peakBulkTemperatureK', temps)
    tm.GetPrim().SetCustomData({'field': 'LPBF_peak_bulk_temperature_not_engine_heat', 'colorMinimumK': 303.15,
        'colorMaximumK': 320.15, 'mapping': 'nearest_part_cell_to_face_centroid', 'maximumMappingDistanceMm': float(distance.max())})
    am = mesh(assets, '/World/AlternatorProxy', proxy.vertices * .001, proxy.faces, [[.65, .29, .08]])
    am.GetPrim().SetCustomData({'target': 'PMB_Classic_Retrofit_240A', 'geometry': 'historical_ASPL160_proxy_not_PMB_dimensions',
        'sourceSha256': sha(alt), 'shaft_rotation_resolved': False, 'rear_cone_and_pulley_missing': True})
    vtk = WORK / 'cfd-turbo-245-alternator-body160-pitch-plus/postProcessing/fanVelocityPlane/1200/cutPlane.vtk'
    points, faces, pressure = READ_PATCH(vtk)
    tokens = vtk.read_text().split(); i = tokens.index('U', tokens.index('CELL_DATA'))
    assert int(tokens[i + 1]) == 3 and int(tokens[i + 2]) == len(faces)
    velocity = np.asarray(tokens[i + 4:i + 4 + 3 * len(faces)], dtype=float).reshape(-1, 3)
    assert np.isfinite(velocity).all()
    speed = np.linalg.norm(velocity, axis=1)
    fm = mesh(assets, '/World/FlowPlane', points, faces, colormaps['viridis'](np.clip(speed / 60, 0, 1))[:, :3])
    scalar(fm, 'speedMps', speed); scalar(fm, 'kinematicPressureM2S2', pressure)
    fm.GetPrim().SetCustomData({'solver': 'OpenFOAM14_MRF', 'iteration': 1200, 'rpm': 3000.,
        'converged': False, 'colorMinimumMps': 0., 'colorMaximumMps': 60., 'transient_flow': False})
    assets.GetRootLayer().Save()
    s = stage(target)
    root = s.GetDefaultPrim()
    root.SetCustomData({'digitalTwinId': '993_Fan_Organic_PMB240_Integration', 'fidelity': 'numerical_research_twin',
        'live_sensor_connection': False, 'pmb_geometry_verified': False, 'manufacturing_authorized': False,
        'rpm_reference': 3000., 'source_geometry_units': 'mm_converted_to_m', 'cfd_converged': False})
    rotor_x = UsdGeom.Xform.Define(s, '/World/RotatingRotor')
    rotation = rotor_x.AddRotateZOp(UsdGeom.XformOp.PrecisionDouble)
    for dest, src in [('RotatingRotor/Geometry', 'Rotor'), ('AlternatorProxy', 'AlternatorProxy'),
                      ('ThermalRotor', 'ThermalRotor'), ('FlowPlane', 'FlowPlane')]:
        p = s.DefinePrim('/World/' + dest)
        p.GetReferences().AddReference('./components.usdc', '/World/' + src)
    for name in ['RearCone', 'PulleyAndSpacers', 'PMB240MeasuredEnvelope']:
        p = UsdGeom.Scope.Define(s, '/World/UnresolvedInterfaces/' + name).GetPrim()
        p.SetCustomData({'status': 'missing_dimensions_no_fabricated_geometry'})
    rows = np.loadtxt(output / 'newton/rotation.csv', delimiter=',', skiprows=1)
    assert rows.shape[1] == 3 and np.isfinite(rows).all()
    s.SetTimeCodesPerSecond(1000.); s.SetFramesPerSecond(1000.)
    s.SetStartTimeCode(0.); s.SetEndTimeCode(100.)
    views = root.GetVariantSets().AddVariantSet('studyView')
    for name in ['assembly', 'flow', 'print_thermal', 'newton_coastdown']:
        views.AddVariant(name); views.SetVariantSelection(name)
        with views.GetVariantEditContext():
            for part, show in [('RotatingRotor', name != 'print_thermal'), ('AlternatorProxy', name != 'print_thermal'),
                               ('FlowPlane', name == 'flow'), ('ThermalRotor', name == 'print_thermal')]:
                UsdGeom.Imageable(s.GetPrimAtPath('/World/' + part)).CreateVisibilityAttr().Set('inherited' if show else 'invisible')
            if name == 'newton_coastdown':
                for t, angle, omega in rows[::10]: rotation.Set(float(np.degrees(angle)), float(t * 1000))
            else:
                rotation.Set(0.)
    views.SetVariantSelection('assembly'); s.GetRootLayer().Save()
    # Viewer-owned camera/lights/render product live in a separate wrapper.
    view = stage(output / 'viewer.usda')
    view.GetRootLayer().subLayerPaths = ['./fan-twin.usda']
    camera = UsdGeom.Camera.Define(view, '/Session/Camera')
    matrix = Gf.Matrix4d().SetLookAt(Gf.Vec3d(.36, -.52, -.34), Gf.Vec3d(0, 0, .015), Gf.Vec3d(0, 0, 1)).GetInverse()
    camera.AddTransformOp().Set(matrix)
    camera.CreateClippingRangeAttr().Set(Gf.Vec2f(.001, 10.))
    camera.CreateFocalLengthAttr().Set(35.)
    dome = UsdLux.DomeLight.Define(view, '/Session/Dome'); dome.CreateIntensityAttr().Set(500.)
    light = UsdLux.DistantLight.Define(view, '/Session/Key'); light.CreateIntensityAttr().Set(2000.)
    light.AddRotateXYZOp().Set(Gf.Vec3f(35, -25, 0))
    var = UsdRender.Var.Define(view, '/Session/Render/Color'); var.CreateSourceNameAttr().Set('LdrColor')
    var.CreateDataTypeAttr().Set('color4f')
    product = UsdRender.Product.Define(view, '/Session/Render/Product')
    product.CreateResolutionAttr().Set(Gf.Vec2i(1280, 960))
    product.CreateCameraRel().SetTargets([camera.GetPath()]); product.CreateOrderedVarsRel().SetTargets([var.GetPath()])
    settings = UsdRender.Settings.Define(view, '/Session/Render/Settings')
    settings.CreateProductsRel().SetTargets([product.GetPath()])
    view.SetMetadata('renderSettingsPrimPath', str(settings.GetPath()))
    view.GetRootLayer().Save()
    inputs = [source, original, reduction, alt, vtk, thermal_dir / 'thermal-summary.json', thermal_dir / 'thermal-fields.npz',
              output / 'newton/rotation.csv', output / 'newton/newton-summary.json', Path(__file__)]
    report = {'status': 'authored_pending_validation', 'meters_per_unit': 1, 'rotor_faces': len(rotor.faces),
        'flow_faces': len(faces), 'thermal_mapping_max_distance_mm': float(distance.max()),
        'thermal_mapping_p95_distance_mm': float(np.quantile(distance, .95)),
        'thermal_color_range_k': [303.15, 320.15], 'flow_color_range_m_s': [0, 60],
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in inputs}}
    (output / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return target


def capture_wrappers(output):
    """Keep scientific field captures free of lighting and solid occlusion."""
    for name in ['flow', 'print_thermal', 'newton_coastdown']:
        path = output / f'viewer-{name}.usda'
        view = Usd.Stage.Open(str(path)) if path.exists() else stage(path)
        view.GetRootLayer().subLayerPaths = ['./viewer.usda']
        UsdGeom.SetStageMetersPerUnit(view, 1.)
        UsdGeom.SetStageUpAxis(view, UsdGeom.Tokens.z)
        view.SetDefaultPrim(view.GetPrimAtPath('/World'))
        view.SetMetadata('renderSettingsPrimPath', '/Session/Render/Settings')
        view.GetPrimAtPath('/World').GetVariantSets().GetVariantSet('studyView').SetVariantSelection(name)
        if name != 'newton_coastdown':
            part = 'FlowPlane' if name == 'flow' else 'ThermalRotor'
            base = f'/World/{part}/DisplayMaterial'
            shader = UsdShade.Shader(view.GetPrimAtPath(base + '/Surface'))
            shader.GetInput('diffuseColor').DisconnectSource()
            shader.GetInput('diffuseColor').Set(Gf.Vec3f(0))
            shader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(
                UsdShade.Shader(view.GetPrimAtPath(base + '/Color')).ConnectableAPI(), 'result')
            shader.CreateInput('specular', Sdf.ValueTypeNames.Float).Set(0.)
            shader.GetInput('roughness').Set(1.)
        if name == 'flow':
            for part in ['RotatingRotor', 'AlternatorProxy']:
                UsdGeom.Imageable(view.GetPrimAtPath('/World/' + part)).CreateVisibilityAttr().Set('invisible')
            matrix = Gf.Matrix4d().SetLookAt(Gf.Vec3d(0, 1.1, 0), Gf.Vec3d(0), Gf.Vec3d(0, 0, 1)).GetInverse()
            view.GetPrimAtPath('/Session/Camera').GetAttribute('xformOp:transform').Set(matrix)
            assert UsdGeom.Imageable(view.GetPrimAtPath('/World/RotatingRotor')).ComputeVisibility() == 'invisible'
        view.GetRootLayer().Save()
        context = UsdValidation.ValidationContext(UsdValidation.ValidationRegistry().GetOrLoadAllValidators())
        errors = context.Validate(view)
        assert not errors, [e.GetMessage() for e in errors]


def validate(path):
    s = Usd.Stage.Open(str(path))
    assert s and s.GetDefaultPrim() and UsdGeom.GetStageMetersPerUnit(s) == 1.
    assert UsdGeom.GetStageUpAxis(s) == 'Z'
    views = s.GetDefaultPrim().GetVariantSets().GetVariantSet('studyView')
    assert set(views.GetVariantNames()) == {'assembly', 'flow', 'print_thermal', 'newton_coastdown'}
    counts = {}
    for view in views.GetVariantNames():
        views.SetVariantSelection(view)
        counts[view] = 0
        for p in s.Traverse():
            if not p.IsA(UsdGeom.Mesh): continue
            m = UsdGeom.Mesh(p)
            pts = np.array(m.GetPointsAttr().Get()); idx = np.array(m.GetFaceVertexIndicesAttr().Get())
            assert np.isfinite(pts).all() and idx.min() >= 0 and idx.max() < len(pts)
            assert sum(m.GetFaceVertexCountsAttr().Get()) == len(idx)
            counts[view] += UsdGeom.Imageable(p).ComputeVisibility() != 'invisible'
        assert counts[view] == {'assembly': 2, 'flow': 3, 'print_thermal': 1, 'newton_coastdown': 2}[view]
    assert s.GetPrimAtPath('/World/AlternatorProxy').GetCustomData()['geometry'].startswith('historical_ASPL')
    views.SetVariantSelection('newton_coastdown')
    angle = s.GetPrimAtPath('/World/RotatingRotor').GetAttribute('xformOp:rotateZ')
    assert angle.GetNumTimeSamples() == 101 and angle.Get(100) > 1700
    views.SetVariantSelection('assembly')
    assert angle.GetNumTimeSamples() == 0
    extent = np.array(s.GetPrimAtPath('/World/RotatingRotor/Geometry').GetAttribute('extent').Get())
    assert .244 < np.ptp(extent, axis=0)[0] < .246
    registry = UsdValidation.ValidationRegistry()
    context = UsdValidation.ValidationContext(registry.GetOrLoadAllValidators())
    errors = context.Validate(s)
    assert not errors, [e.GetMessage() for e in errors]
    _, _, unresolved = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(path)))
    assert not unresolved, unresolved
    print(json.dumps({'status': 'passed', 'visible_meshes_by_view': counts, 'rotor_extent_m': np.ptp(extent, axis=0).tolist()}))
    return {'status': 'passed_openusd_composition_and_data_checks', 'views': counts, 'gpu_render_checked': False,
        'pmb_geometry_verified': False, 'simready_claimed': False,
        'openusd_validator_findings': [], 'unresolved_dependencies': []}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    path = args.output / 'fan-twin.usda' if args.validate_only else build(args.output)
    report = validate(path)
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if not args.validate_only:
        capture_wrappers(args.output)
        package = args.output / 'fan-twin.usdz'
        assert UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str((args.output / 'viewer.usda').resolve())), str(package))
        assert Usd.Stage.Open(str(package))
