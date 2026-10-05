#!/usr/bin/env python3
"""Export actual study geometry to OpenUSD; no dynamics solver or SimReady claim."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from screen_lpbf_geometry import triangles


def build(geometry,output,label):
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise ValueError('Fresh output required')
    report=json.loads((geometry/'geometry-report.json').read_text());records={}
    text='#usda 1.0\n(\n    defaultPrim = "Fan"\n    metersPerUnit = 0.001\n    upAxis = "Z"\n)\n\ndef Xform "Fan" (\n    kind = "component"\n    customData = {\n        string study = '+json.dumps(label)+'\n        string configuration = '+json.dumps(report['configuration_id'])+'\n        string status = "Analytical study; physical and manufacturing validation absent"\n        string parameters = "../parameters/'+label+'.json"\n        string conditionsAndResults = "../results/mechanics/mesh-'+label+'-h3p6.json"\n        string fluidValidation = "R0 reference mesh QA passed; pilot convergence and aerodynamic mesh independence required"\n        bool physicalValidationEstablished = false\n        bool simReadyQualified = false\n    }\n)\n{\n'
    for name in report['components']:
        path=geometry/(name+'.stl');digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=report['components'][name]['stl_sha256']:raise ValueError('STL does not match geometry report')
        tri=triangles(path);points,indices=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True)
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
        tuplefmt=lambda row:'('+', '.join(format(float(x),'.9g') for x in row)+')'
        text+='    def Mesh "'+name+'" (prepend apiSchemas = ["MaterialBindingAPI"])\n    {\n        uniform token subdivisionScheme = "none"\n        uniform token orientation = "rightHanded"\n        bool doubleSided = false\n'
        text+='        point3f[] points = ['+', '.join(tuplefmt(p) for p in points)+']\n'
        text+='        int[] faceVertexCounts = ['+', '.join(['3']*len(tri))+']\n'
        text+='        int[] faceVertexIndices = ['+', '.join(str(int(x)) for x in indices)+']\n'
        text+='        normal3f[] normals = ['+', '.join(tuplefmt(n) for n in normals)+'] (interpolation = "uniform")\n'
        text+='        float3[] extent = ['+tuplefmt(points.min(axis=0))+', '+tuplefmt(points.max(axis=0))+']\n'
        text+='        color3f[] primvars:displayColor = [(0.68, 0.70, 0.72)] (interpolation = "constant")\n'
        text+='        custom string sourceSTLSHA256 = "'+digest+'"\n        rel material:binding = </Fan/Materials/AssumedAluminium>\n    }\n'
        records[name]={'triangles':len(tri),'points':len(points),'source_STL_sha256':digest}
    text+='''    def Scope "Materials"
    {
        def Material "AssumedAluminium"
        {
            token outputs:surface.connect = </Fan/Materials/AssumedAluminium/Preview.outputs:surface>
            def Shader "Preview"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.68, 0.70, 0.72)
                float inputs:metallic = 1
                float inputs:roughness = 0.35
                token outputs:surface
            }
        }
    }
}
'''
    output.write_text(text)
    receipt={'status':'geometry_and_result_linked_OpenUSD_asset','label':label,'metersPerUnit':.001,'upAxis':'Z','rotorAxis':[0,0,1],'inputDriveAxis':[1,0,0],
             'components':records,'source_geometry_report_sha256':hashlib.sha256((geometry/'geometry-report.json').read_bytes()).hexdigest(),
             'USD_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'material':'Visual assumed aluminium; no material qualification',
             'uses_actual_STL_coordinates_without_cutaway':True,'physical_validation_established':False,'SimReady_qualified':False,
             'Omniverse_GPU_runtime_executed':False,'physics_solver_executed_by_this_exporter':False}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('geometry',type=Path);p.add_argument('output',type=Path);p.add_argument('--label',choices=['R0','V5'],required=True)
    a=p.parse_args();build(a.geometry,a.output,a.label)
