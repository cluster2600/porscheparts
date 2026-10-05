#!/usr/bin/env python3
"""Actual CAD tessellation views and CPU OpenUSD export; no solver fields invented."""
import argparse,hashlib,json,os
from pathlib import Path
import numpy as np
from screen_lpbf_geometry import triangles


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


COLORS={'V2_original_assembly':(.65,.67,.70),'plenum_shell_envelope':(.22,.57,.77),
        'input_pulley_pitch_envelope':(.86,.58,.24),'driver_pulley_pitch_envelope':(.86,.58,.24),
        'input_shaft_extension_envelope':(.70,.70,.74),
        'belt_pitch_path_envelope':(.20,.20,.24),'support_stock_envelopes':(.39,.68,.44)}


def export(root,geometry,asset,plot):
    from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    from matplotlib.collections import PolyCollection
    report=json.loads((geometry/'geometry-report.json').read_text());stage=Usd.Stage.CreateNew(str(asset))
    UsdGeom.SetStageMetersPerUnit(stage,1.);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    fan=UsdGeom.Xform.Define(stage,'/Fan');stage.SetDefaultPrim(fan.GetPrim())
    metadata={'study':report['study_id'],'status':'Assumed packaging geometry; no installed or manufacturing qualification',
              'parameters':'../parameters/assembly-study-S1.json','conditionsAndResults':'../results/assembly/S1/geometry-report.json',
              'interfaceContract':'../parameters/assembly-interface-contract.json',
              'CFDDiagnostic':'../results/cfd/D2-establishment-diagnostic.json',
              'manufacturingRoute':'../ASSEMBLY_MANUFACTURING_S1.md',
              'sourceAssemblySHA256':report['source_assembly_sha256'],'physicalValidationEstablished':False,
              'digitalTwinValidated':False,'SimReadyQualified':False}
    fan.GetPrim().SetCustomData(metadata);records={};points_for_limits=[];groups={}
    for name,component in report['components'].items():
        UsdGeom.Xform.Define(stage,'/Fan/'+name)
        material=UsdShade.Material.Define(stage,'/Fan/Materials/'+name)
        shader=UsdShade.Shader.Define(stage,str(material.GetPath())+'/Preview');shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*COLORS[name]))
        shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.6)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
        combined=[]
        for index,(mesh_name,digest) in enumerate(component['separate_solid_STL_sha256'].items()):
            path=geometry/'geometry'/mesh_name
            if sha(path)!=digest:raise ValueError('CAD tessellation identity differs')
            tri=triangles(path);combined.append(tri);points,indices=np.unique(tri.reshape(-1,3)*.001,axis=0,return_inverse=True)
            mesh=UsdGeom.Mesh.Define(stage,'/Fan/'+name+'/Solid'+str(index));mesh.CreateSubdivisionSchemeAttr('none')
            mesh.CreatePointsAttr(points.tolist());mesh.CreateFaceVertexCountsAttr([3]*len(tri));mesh.CreateFaceVertexIndicesAttr(indices.tolist())
            mesh.CreateExtentAttr([points.min(axis=0).tolist(),points.max(axis=0).tolist()])
            mesh.GetPrim().SetCustomData({'sourceSTLSHA256':digest,'sourceRole':component['role'],'physicalMaterialQualified':False})
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
            actual=np.asarray(mesh.GetPointsAttr().Get());error=float(np.max(np.abs(actual-points)))
            bound=float(np.finfo(np.float32).eps*np.max(np.abs(points))+1e-12)
            if error>bound:raise ValueError('Unexpected coordinate representation error')
            records[str(mesh.GetPath())]={'source_stl_sha256':digest,'triangles':len(tri),'points':len(points),
                       'maximum_float32_coordinate_error_m':error,'float32_representation_bound_m':bound}
            points_for_limits.append(points*1000)
        groups[name]=np.concatenate(combined)
    stage.GetRootLayer().Save()
    asset.write_text(asset.read_text().rstrip()+'\n')
    fig,axes=plt.subplots(1,3,figsize=(15,6));limits=np.concatenate(points_for_limits)
    for ax,(a,b,title) in zip(axes,[(0,1,'Vue suivant Z'),(0,2,'Vue suivant Y'),(1,2,'Vue suivant X')]):
        for name,tri in groups.items():
            ax.add_collection(PolyCollection(tri[:,:,[a,b]],facecolor=COLORS[name],edgecolor='none',alpha=.55 if name=='plenum_shell_envelope' else .65,rasterized=True))
        ax.set_xlim(limits[:,a].min()-15,limits[:,a].max()+15);ax.set_ylim(limits[:,b].min()-15,limits[:,b].max()+15)
        ax.set_aspect('equal');ax.set_xlabel('XYZ'[a]+' (mm)');ax.set_ylabel('XYZ'[b]+' (mm)');ax.set_title(title);ax.grid(alpha=.2)
    fig.suptitle('S1 — CAO d’étude à échelle supposée ; plénum et entraînement simplifiés',fontsize=12)
    fig.text(.5,.015,'Projection des triangles CAO, transparence visuelle. Aucun champ calculé ni interface moteur mesurée.',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(plot,dpi=150);plt.close(fig)
    receipt={'status':'actual_CAD_layout_exported_no_solver','asset_sha256':sha(asset),'plot_sha256':sha(plot),
             'script_sha256':sha(Path(__file__)),'source_geometry_report_sha256':sha(geometry/'geometry-report.json'),
             'USD_version':list(Usd.GetVersion()),'metersPerUnit':1,'upAxis':'Z','meshes':records,
             'linked_input_sha256':{value:sha(asset.parent/value) for value in metadata.values() if isinstance(value,str) and value.startswith('../')},
             'all_coordinates_checked':True,'plot_uses_same_native_CAD_tessellations':True,
             'material_colors_are_visual_roles_not_qualification':True,'physical_validation_established':False,
             'NVIDIA_SimReady_qualified':False,'Omniverse_GPU_execution_verified':False,'digital_twin_validated':False}
    asset.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':receipt['status'],'meshes':len(records)}))


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__)
    for arg in ['root','geometry','asset','plot']:cli.add_argument(arg,type=Path)
    a=cli.parse_args();export(a.root,a.geometry,a.asset,a.plot)
