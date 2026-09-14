#!/usr/bin/env python3
"""Private deterministic underside render of the actual chambered STEP.

Appearance is illustrative grey, not a selected or qualified alloy.
"""
import argparse
import json
import math
from pathlib import Path
import time

import inspect_pilot as inspection


def extract(args):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    start=time.monotonic()
    report=json.loads(args.candidate_report.read_text())
    if report['status']!='two_plane_chamber_geometry_checks_passed_not_head_or_fluid_domain_qualification':
        raise ValueError('candidate_checks_required')
    if inspection.digest(args.body)!=report['exports']['chambered-candidate']['step_sha256']:
        raise ValueError('candidate_STEP_binding_mismatch')
    for name in ('module','build','registration'):
        if inspection.digest(getattr(args,name))!=inspection.EXPECTED[name]:
            raise ValueError('exact_component_sources_required')
    if args.output.exists():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700)
    cad=inspection.design.CAD()
    body=cad.read_step(args.body);module=cad.read_step(args.module)
    solids=cad.indexed(module,cad.TopAbs_SOLID)
    registration=json.loads(args.registration.read_text())
    ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
    p=inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
    parts=[{'name':'body','role':'body','shape':body}]
    for part in inspection.design.construct(cad,p,{'intake_mm':0.,'exhaust_mm':0.}):
        shape=solids.FindKey(ids[part['name']])
        if part['role']=='valve' and part['spec']['kind']=='intake':
            tr=cad.gp_Trsf();tr.SetTranslation(cad.gp_Vec(*inspection.lift_translation(part['spec']['axis_angle_deg'],6.)))
            shape=cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()
        tr=cad.gp_Trsf();tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3))
        parts.append({'name':part['name'],'role':part['role'],'shape':cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()})
    result={'schema':'m64-chamber-underside-tessellation/v1',
            'source_sha256':inspection.digest(__file__),
            'candidate_report_sha256':inspection.digest(args.candidate_report),
            'body_STEP_sha256':inspection.digest(args.body),
            'module_STEP_sha256':inspection.digest(args.module),
            'manufacturing_authorized':False,'new_product_geometry_created':False,
            'tessellation':{'linear_deflection_scan_units':.18,'relative':False,'angular_deflection_radians':.25},
            'module_lifts_design_mm':{'intake':6.,'exhaust':0.},
            'material_appearance_not_selected_alloy':'neutral_grey', 'parts':[]}
    for part in parts:
        shape=part['shape'];BRepMesh_IncrementalMesh(shape,.18,False,.25,False)
        target=args.output/(part['name']+'.stl')
        if not StlAPI_Writer().Write(shape,str(target)):raise ValueError('tessellation_export_failed')
        target.chmod(0o600)
        result['parts'].append({'name':part['name'],'role':part['role'],'filename':target.name,'sha256':inspection.digest(target)})
    result['elapsed_seconds']=time.monotonic()-start
    target=args.output/'tessellation-report.json';target.write_text(json.dumps(result,indent=2)+'\n');target.chmod(0o600)
    print(json.dumps({'elapsed_seconds':result['elapsed_seconds'],'parts':len(result['parts'])}),flush=True)


def render(args):
    import numpy as np
    import pyvista as pv
    import vtk
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    if args.output.exists():raise FileExistsError(args.output)
    report=json.loads((args.meshes/'tessellation-report.json').read_text())
    section=json.loads(args.sections.read_text())
    if report['body_STEP_sha256']!=section['inputs_sha256']['body'] or not section['new_roof_created']:
        raise ValueError('section_and_body_binding_mismatch')
    fig=plt.figure(figsize=(16,10),facecolor='#f6f7f8')
    ax=fig.add_axes([.005,.16,.76,.72],facecolor='#f6f7f8')
    palette={'body':'#a0a7ad','valve':'#d1d7db','seat':'#7f8991','guide':'#5c6870'}
    bounds=[];rows=[]
    plot=pv.Plotter(off_screen=True,window_size=(1520,1150))
    plot.background_color='#f6f7f8'
    for part in report['parts']:
        path=args.meshes/part['filename']
        if inspection.digest(path)!=part['sha256']:raise ValueError('mesh_hash_mismatch')
        mesh=pv.read(path)
        if not mesh.is_all_triangles or not np.isfinite(mesh.points).all() or not 0<mesh.n_cells<=2000000:
            raise ValueError('invalid_STL_or_render_triangle_budget_exceeded')
        bounds.extend([mesh.points.min(axis=0),mesh.points.max(axis=0)])
        plot.add_mesh(mesh,color=palette[part['role']],smooth_shading=False,
                      ambient=.35,diffuse=.65,specular=.15,show_edges=False)
        rows.append({'name':part['name'],'triangles':mesh.n_cells})
    b=np.array(bounds);lo=b.min(axis=0);hi=b.max(axis=0);span=hi-lo
    focus=(lo+hi)/2
    plot.camera_position=[tuple(focus+max(span)*np.array([.7,-1.2,-.8])),tuple(focus),(0,0,1)]
    plot.enable_parallel_projection();plot.camera.parallel_scale=max(span)*.57
    plot.enable_anti_aliasing('ssaa')
    pixels=plot.screenshot(return_img=True);plot.close()
    ax.imshow(pixels);ax.set_axis_off()
    inset=fig.add_axes([.69,.34,.295,.28],facecolor='white')
    center=next(s for s in section['sections'] if s['world_x']==0.)
    for part in center['parts']:
        if part['role']!='body_master':continue
        inset.add_collection(PolyCollection(part['triangles'],facecolors='#a0a7ad',edgecolors='none'))
        for curve in part['curves']:
            inset.plot([p[0] for p in curve],[p[1] for p in curve],color='#626d75',lw=.7)
    inset.set_xlim(-53,53);inset.set_ylim(-2,15);inset.set_aspect('equal')
    inset.axhline(0,color='#666666',ls=':',lw=.8)
    inset.set_title('Coupe CAO centrale\nChambre candidate à deux pans',fontsize=12)
    inset.set_xlabel('Y — unités du scan');inset.set_ylabel('Z');inset.grid(alpha=.1)
    fig.text(.05,.92,'M64 · prototype de chambre 4 soupapes',fontsize=24,weight='bold',color='#202831')
    fig.text(.05,.875,'Vue par-dessous · extérieur conservé · géométrie issue de la CAO, sans retouche générative',fontsize=13,color='#53616f')
    fig.text(.71,.70,'Admission : levée 6 mm\nÉchappement : fermé\nSièges et guides réels du module V2',fontsize=13,color='#283540',linespacing=1.6)
    fig.text(.71,.265,'Bougie centrale réservée, non percée.\nConduits non découpés dans ce corps.\nAucun débit ou résultat thermique calculé.',fontsize=11,color='#53616f',linespacing=1.6)
    fig.text(.05,.09,'Rendu des STEP sources, pas une photo de pièce fabriquée. Gris illustratif : alliage non sélectionné.',fontsize=12,color='#53616f')
    fig.text(.05,.052,'Échelle hypothétique · interfaces non certifiées · prototype NON AUTORISÉ À FABRIQUER',fontsize=12,color='#a63832',weight='bold')
    fig.savefig(args.output,dpi=170,facecolor=fig.get_facecolor());plt.close(fig);args.output.chmod(0o600)
    receipt={'schema':'m64-chamber-underside-render/v1','source_sha256':inspection.digest(__file__),
             'tessellation_report_sha256':inspection.digest(args.meshes/'tessellation-report.json'),
             'sections_sha256':inspection.digest(args.sections),'output_sha256':inspection.digest(args.output),
             'parts':rows,'manufacturing_authorized':False,'scientific_fields_rendered':False,
             'exact_CAD_tessellation_not_generative_image':True,
             'renderer':'VTK_z_buffer_PyVista_off_screen_no_geometry_smoothing',
             'PyVista_version':pv.__version__,'VTK_version':vtk.vtkVersion.GetVTKVersion()}
    target=args.output.with_suffix('.json');target.write_text(json.dumps(receipt,indent=2)+'\n');target.chmod(0o600)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    ext=sub.add_parser('extract')
    for name in ('body','module','build','registration','candidate-report','output'):
        ext.add_argument('--'+name,type=Path,required=True)
    renderer=sub.add_parser('render')
    for name in ('meshes','sections','output'):renderer.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();(extract if args.command=='extract' else render)(args)
