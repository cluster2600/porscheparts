#!/usr/bin/env python3
"""Check OpenUSD parsing, topology, units, materials and linked result files."""
import argparse,hashlib,json
from pathlib import Path


def validate(path,output,expected_meshes=None,meters_per_unit=.001):
    from pxr import Usd,UsdGeom,UsdShade,UsdUtils
    stage=Usd.Stage.Open(str(path))
    if not stage or not stage.GetDefaultPrim():raise ValueError('USD stage/default prim missing')
    if UsdGeom.GetStageMetersPerUnit(stage)!=meters_per_unit or UsdGeom.GetStageUpAxis(stage)!='Z':raise ValueError('Unexpected units or axis')
    linked_files=set()
    for prim in stage.Traverse():
        metadata=prim.GetCustomData()
        for key in ['parameters','conditionsAndResults']:
            if key in metadata:
                target=path.parent/metadata[key]
                if not target.is_file():raise ValueError('Missing linked calculation file '+metadata[key])
                linked_files.add(metadata[key])
    meshes=[]
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            mesh=UsdGeom.Mesh(prim);points=mesh.GetPointsAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get();indices=mesh.GetFaceVertexIndicesAttr().Get()
            if not points or sum(counts)!=len(indices) or min(indices)<0 or max(indices)>=len(points) or set(counts)!={3}:raise ValueError('Invalid triangle topology')
            material,_=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            if not material:raise ValueError('Material binding unresolved')
            edges={}
            for i in range(0,len(indices),3):
                tri=indices[i:i+3]
                for a,b in [(tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])]:
                    key=tuple(sorted((int(a),int(b))));edges[key]=edges.get(key,0)+1
            if any(n!=2 for n in edges.values()):raise ValueError('Mesh has non-manifold boundary edges')
            meshes.append({'path':str(prim.GetPath()),'triangles':len(counts),'points':len(points),'all_edges_incident_to_two_triangles':True})
    expected=expected_meshes if expected_meshes is not None else 16 if path.name=='studies.usda' else 8
    if len(meshes)!=expected:raise ValueError('Unexpected component count')
    from pxr import UsdValidation
    registry=UsdValidation.ValidationRegistry()
    names=sorted(m.name for m in registry.GetAllValidatorMetadata() if m.name!='usdShadeValidators:ShaderSdrCompliance')
    validators=registry.GetOrLoadValidatorsByName(names)
    context=UsdValidation.ValidationContext(validators)
    findings=[{'type':str(e.GetType()),'message':e.GetMessage()} for e in context.Validate(stage)]
    if findings:raise ValueError(json.dumps(findings))
    shader_block=None
    # Check the actual available resources before invoking the shader discovery.
    from pxr import Plug
    missing_resources=[]
    for plugin_name in ['usdHydra','usdShaders']:
        plugin=Plug.Registry().GetPluginWithName(plugin_name)
        if not plugin or not (Path(plugin.resourcePath)/'shaderDefs.usda').is_file():missing_resources.append(plugin_name)
    if missing_resources:
        shader_block='Blocked: available cached USD runtime lacks shaderDefs.usda'
    else:
        shader=registry.GetOrLoadValidatorByName('usdShadeValidators:ShaderSdrCompliance')
        shader_findings=UsdValidation.ValidationContext([shader]).Validate(stage)
        if shader_findings:raise ValueError('Shader compliance findings: '+str([e.GetMessage() for e in shader_findings]))
        names.append('usdShadeValidators:ShaderSdrCompliance')
    report={'status':'composition_geometry_and_material_binding_checks_passed_shader_rule_blocked' if shader_block else 'generic_OpenUSD_asset_checks_passed','USD_version':list(Usd.GetVersion()),'asset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'metersPerUnit':meters_per_unit,'upAxis':'Z','meshes':meshes,'linked_files_checked':sorted(linked_files),'validators_executed':names,'validator_findings':findings,
            'shader_Sdr_validation':shader_block or 'passed',
            'complete_generic_validation_established':shader_block is None,
            'Omniverse_GPU_execution_verified':False,'physical_validation_established':False,'SimReady_qualified':False}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('asset',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--expected-meshes',type=int);p.add_argument('--meters-per-unit',type=float,default=.001)
    a=p.parse_args();validate(a.asset,a.output,a.expected_meshes,a.meters_per_unit)
