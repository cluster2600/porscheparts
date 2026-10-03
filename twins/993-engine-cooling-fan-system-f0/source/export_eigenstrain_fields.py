#!/usr/bin/env python3
"""Export actual released native node fields, in meters at deformation scale one."""
import argparse
import json
from pathlib import Path

import numpy as np
from prepare_engineering_sensitivities import parse_mesh
from summarize_engineering_sensitivities import displacement_blocks, eigenstrain, sha


def boundary(elements, nodes):
    faces = {}
    for e in elements.values():
        center = np.mean([nodes[i] for i in e[:4]],axis=0)
        for inds in ((0,1,2,4,5,6),(0,3,1,7,8,4),(1,3,2,8,9,5),(2,3,0,9,7,6)):
            face = [e[i] for i in inds]
            key = tuple(sorted(face[:3]))
            if key in faces:
                del faces[key]
            else:
                p = np.array([nodes[i] for i in face[:3]])
                reverse = np.dot(np.cross(p[1]-p[0],p[2]-p[0]),p.mean(axis=0)-center)<0
                faces[key] = (face,reverse)
    triangles = []
    for (a,b,c,ab,bc,ca), reverse in faces.values():
        for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):
            triangles.append(tri[::-1] if reverse else tri)
    tags = sorted({v for tri in triangles for v in tri})
    index = {tag:i for i,tag in enumerate(tags)}
    return tags,np.array([[index[t] for t in tri] for tri in triangles],dtype=np.int32)


def export(case, asset, plot):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    from pxr import Gf,Sdf,Usd,UsdGeom,UsdShade,UsdValidation,Vt
    summary = eigenstrain(case)
    nodes,elements = parse_mesh((case/'rotor.inp').read_text())
    fields = displacement_blocks(case/'rotor.frd')
    tags,triangles = boundary(elements,nodes)
    xyz = np.array([nodes[i] for i in tags])
    u = np.array([fields[-1][i] for i in tags])
    magnitude = np.linalg.norm(u,axis=1)
    maximum = summary['states'][-1]['maximum_displacement_mm']
    points = (xyz+u)*.001
    stored = points.astype(np.float32)
    colors = plt.get_cmap('viridis')(magnitude/max(maximum,1e-20))[:,:3].astype(np.float32)
    asset.parent.mkdir(parents=True,exist_ok=True)
    if asset.exists() or plot.exists():
        raise FileExistsError('Use new output files to preserve field receipts')
    stage = Usd.Stage.CreateNew(str(asset.resolve()))
    UsdGeom.SetStageMetersPerUnit(stage,1.)
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage,'/ImpellerStudy').GetPrim()
    stage.SetDefaultPrim(root)
    root.SetCustomData({'geometryRole':'native_C3D10_boundary_linear_subtriangles',
                       'sourceDeckSHA256':summary['file_sha256']['rotor.inp'],
                       'sourceFieldsSHA256':summary['file_sha256']['rotor.frd'],
                       'state':'released_uncalibrated_eigenstrain', 'deformationScale':1.,
                       'solverUnits':'mm,N,s,tonne','displayField':'displacement_magnitude_mm',
                       'processCalibrated':False,'digitalTwinValidated':False,
                       'manufacturingAuthorized':False,'scanIncluded':False,
                       'physicalTimeRepresented':False,'qualifiedMaterialAssigned':False})
    mesh = UsdGeom.Mesh.Define(stage,'/ImpellerStudy/AnalysisSurface')
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(stored))
    mesh.CreateFaceVertexCountsAttr([3]*len(triangles))
    mesh.CreateFaceVertexIndicesAttr(triangles.ravel().tolist())
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr([Gf.Vec3f(*map(float,stored.min(axis=0))),Gf.Vec3f(*map(float,stored.max(axis=0)))])
    api = UsdGeom.PrimvarsAPI(mesh)
    api.CreatePrimvar('displayColor',Sdf.ValueTypeNames.Color3fArray,UsdGeom.Tokens.vertex).Set(Vt.Vec3fArray.FromNumpy(colors))
    api.CreatePrimvar('solverNodeId',Sdf.ValueTypeNames.IntArray,UsdGeom.Tokens.vertex).Set(tags)
    api.CreatePrimvar('solverDisplacement_m',Sdf.ValueTypeNames.Vector3fArray,UsdGeom.Tokens.vertex).Set(Vt.Vec3fArray.FromNumpy((u*.001).astype(np.float32)))
    api.CreatePrimvar('displacementMagnitude_mm',Sdf.ValueTypeNames.FloatArray,UsdGeom.Tokens.vertex).Set(magnitude.astype(np.float32).tolist())
    material = UsdShade.Material.Define(stage,'/ImpellerStudy/FieldMaterial')
    material.GetPrim().SetCustomData({'role':'visual_field_shader_not_alloy_properties'})
    shader = UsdShade.Shader.Define(stage,'/ImpellerStudy/FieldMaterial/Surface')
    shader.CreateIdAttr('UsdPreviewSurface')
    reader = UsdShade.Shader.Define(stage,'/ImpellerStudy/FieldMaterial/Color')
    reader.CreateIdAttr('UsdPrimvarReader_float3')
    reader.CreateInput('varname',Sdf.ValueTypeNames.String).Set('displayColor')
    reader.CreateOutput('result',Sdf.ValueTypeNames.Float3)
    shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).ConnectToSource(reader.ConnectableAPI(),'result')
    shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.7)
    shader.CreateOutput('surface',Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    stage.GetRootLayer().Save()
    reopened = Usd.Stage.Open(str(asset.resolve()))
    issues = UsdValidation.ValidationContext(UsdValidation.ValidationRegistry().GetOrLoadAllValidators()).Validate(reopened)
    if issues:
        raise ValueError('OpenUSD validation findings: '+str([e.GetMessage() for e in issues]))
    # Faithful field plot: actual boundary nodes, undeformed coordinates, no
    # fitted artwork or geometry hidden by a deformation multiplier.
    fig,axes = plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,(a,b,title) in zip(axes,[(0,1,'XY'),(0,2,'XZ')]):
        dots = ax.scatter(xyz[:,a],xyz[:,b],c=magnitude,s=.7,vmin=0,vmax=maximum,cmap='viridis',rasterized=True)
        ax.set_aspect('equal');ax.set_title(title+' — undeformed native boundary nodes')
        ax.set_xlabel('XYZ'[a]+' (mm, model assumption)');ax.set_ylabel('XYZ'[b]+' (mm, model assumption)')
    fig.colorbar(dots,ax=axes,label='Native released displacement magnitude (mm)')
    fig.suptitle('Uncalibrated elastic eigenstrain — no physical build prediction')
    plot.parent.mkdir(parents=True,exist_ok=True);fig.savefig(plot,dpi=180);plt.close(fig)
    return {'status':'generic_openusd_validation_passed_native_field_export',
            'source_field_sha256':summary['file_sha256']['rotor.frd'],
            'asset_sha256':sha(asset),'plot_sha256':sha(plot),'openusd_version':'.'.join(map(str,Usd.GetVersion())),
            'boundary_nodes':len(tags),'linear_subtriangles':len(triangles),'meters_per_unit':1,'up_axis':'Z',
            'deformation_scale':1,'maximum_coordinate_storage_error_mm':float(np.linalg.norm(stored-points,axis=1).max()*1000),
            'all_generic_validator_issues':len(issues),'nvidia_asset_validator_available':False,
            'simready_validated':False,'digital_twin_validated':False,'process_calibrated':False,
            'manufacturing_authorized':False,'scan_included':False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case',type=Path);p.add_argument('asset',type=Path);p.add_argument('plot',type=Path);p.add_argument('report',type=Path)
    a=p.parse_args();result=export(a.case,a.asset,a.plot)
    with a.report.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Native field asset checked; SimReady and physical digital twin remain unvalidated')
