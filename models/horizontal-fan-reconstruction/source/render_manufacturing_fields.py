#!/usr/bin/env python3
"""Render actual boundary displacement values and export a scale-one USDA mesh."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def render(bundle,asset,plot,label):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    report=json.load(open(bundle.with_suffix('.json')))
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=report['field_bundle_sha256']:raise ValueError('Field bundle integrity failure')
    if asset.exists() or plot.exists():raise FileExistsError('Fresh output required')
    fields=np.load(bundle);xyz=fields['xyz_mm'];u=fields['released_displacement_mm'];magnitude=np.linalg.norm(u,axis=1);points=(xyz+u)*.001;triangles=fields['triangles'];colors=plt.get_cmap('viridis')(magnitude/max(float(magnitude.max()),1e-20))[:,:3]
    vec=lambda x:'('+', '.join(format(float(v),'.10g') for v in x)+')'
    text='#usda 1.0\n(defaultPrim = "ManufacturingStudy"\n metersPerUnit = 1\n upAxis = "Z")\n'
    meta={'configuration':report['configuration_id'],'sourceSTEP_SHA256':report['source_step_sha256'],'sourceDeckSHA256':report['source_deck_sha256'],'sourceFieldSHA256':report['source_field_sha256'],'state':'released_uncalibrated_elastic_contraction','conditionsAndResults':'../results/lpbf/'+label+'-diagonal-edge-summary.json','scope':'Assumed contraction and rigid attachments; no calibrated process or validated manufacturing'}
    text+='def Xform "ManufacturingStudy" (customData = {\n'+''.join(' string '+k+' = '+json.dumps(v)+'\n' for k,v in meta.items())+' double deformationScale = 1\n bool processCalibrated = false\n bool digitalTwinValidated = false\n bool manufacturingValidated = false\n})\n{\n'
    text+=' def Mesh "NativeReleasedBoundary" (prepend apiSchemas = ["MaterialBindingAPI"]) {\n uniform token subdivisionScheme = "none"\n point3f[] points = ['+', '.join(vec(p) for p in points)+']\n'
    text+=' int[] faceVertexCounts = ['+', '.join(['3']*len(triangles))+']\n int[] faceVertexIndices = ['+', '.join(map(str,triangles.ravel()))+']\n'
    text+=' color3f[] primvars:displayColor = ['+', '.join(vec(c) for c in colors)+'] (interpolation = "vertex")\n'
    text+=' vector3f[] primvars:solverDisplacement_m = ['+', '.join(vec(v) for v in u*.001)+'] (interpolation = "vertex")\n'
    text+=' float[] primvars:displacementMagnitude_mm = ['+', '.join(format(float(v),'.10g') for v in magnitude)+'] (interpolation = "vertex")\n'
    text+=' int[] primvars:solverNodeId = ['+', '.join(map(str,fields['solver_node_id']))+'] (interpolation = "vertex")\n'
    text+=' float3[] extent = ['+vec(points.min(axis=0))+', '+vec(points.max(axis=0))+']\n rel material:binding = </ManufacturingStudy/FieldMaterial>\n }\n'
    text+=''' def Material "FieldMaterial" {
 token outputs:surface.connect = </ManufacturingStudy/FieldMaterial/Preview.outputs:surface>
 def Shader "Color" {
 uniform token info:id = "UsdPrimvarReader_float3"
 string inputs:varname = "displayColor"
 float3 outputs:result
 }
 def Shader "Preview" {
 uniform token info:id = "UsdPreviewSurface"
 color3f inputs:diffuseColor.connect = </ManufacturingStudy/FieldMaterial/Color.outputs:result>
 float inputs:roughness = 0.7
 token outputs:surface
 }
 }
}
'''
    asset.write_text(text)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,(i,j) in zip(axes,[(0,1),(0,2)]):
        dots=ax.scatter(xyz[:,i],xyz[:,j],c=magnitude,s=.8,vmin=0,vmax=float(magnitude.max()),cmap='viridis',rasterized=True);ax.set_aspect('equal');ax.set_xlabel('XYZ'[i]+' [mm]');ax.set_ylabel('XYZ'[j]+' [mm]')
        ax.set_title('Actual native boundary values; undeformed coordinates')
    fig.colorbar(dots,ax=axes,label='Released displacement magnitude [mm]');fig.suptitle(label+' | assumed strain 0.001, diagonal edge | no process calibration');fig.savefig(plot,dpi=150);plt.close(fig)
    receipt={**report,'asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'plot_sha256':hashlib.sha256(plot.read_bytes()).hexdigest(),'asset_meters_per_unit':1,'up_axis':'Z','asset_deformation_scale':1,'plot_coordinates':'undeformed solver boundary nodes; actual displacement color, no clipping','maximum_boundary_displacement_mm':float(magnitude.max()),'usd_validator_executed_by_exporter':False,'NVIDIA_SimReady_qualified':False}
    asset.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('asset',type=Path);p.add_argument('plot',type=Path);p.add_argument('--label',choices=['R0','V5'],required=True);a=p.parse_args();render(a.bundle,a.asset,a.plot,a.label)
