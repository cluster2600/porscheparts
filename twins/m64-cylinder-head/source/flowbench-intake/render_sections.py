#!/usr/bin/env python3
"""Native sections of existing intake parts; no roof or fluid domain is built.

All source meshes, section coordinates and resulting images stay private.
"""
import argparse
import json
import math
from pathlib import Path
import time

import inspect_pilot as inspection


def extract(args):
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopLoc import TopLoc_Location
    start = time.monotonic()
    paths = {name: getattr(args, name) for name in inspection.EXPECTED}
    expected = dict(inspection.EXPECTED)
    candidate = None
    if args.candidate_report:
        candidate = json.loads(args.candidate_report.read_text())
        if candidate['status'] != 'two_plane_chamber_geometry_checks_passed_not_head_or_fluid_domain_qualification':
            raise ValueError('candidate_geometry_checks_required_before_render')
        if candidate['inputs_sha256']['body'] != inspection.EXPECTED['body']:
            raise ValueError('candidate_master_binding_mismatch')
        expected['body'] = candidate['exports']['chambered-candidate']['step_sha256']
    if {name: inspection.digest(path) for name, path in paths.items()} != expected:
        raise ValueError('exact_inspection_sources_required')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    cad = inspection.design.CAD()
    body = cad.read_step(args.body)
    module = cad.read_step(args.module)
    solids = cad.indexed(module, cad.TopAbs_SOLID)
    bank = TopoDS_Shape()
    if not BRepTools.Read_s(bank, str(args.intake), BRep_Builder()):
        raise ValueError('native_bank_read_failed')
    registration = json.loads(args.registration.read_text())
    ids = {r['name']: r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
    p = inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
    parts = [('body_master', body), ('intake_raw_negative', bank)]
    for part in inspection.design.construct(cad, p, {'intake_mm': 0., 'exhaust_mm': 0.}):
        shape = solids.FindKey(ids[part['name']])
        if part['role'] == 'valve' and part['spec']['kind'] == 'intake':
            tr = cad.gp_Trsf()
            tr.SetTranslation(cad.gp_Vec(*inspection.lift_translation(part['spec']['axis_angle_deg'], 6.)))
            shape = cad.BRepBuilderAPI_Transform(shape, tr, True).Shape()
        tr = cad.gp_Trsf()
        tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0), cad.gp_Dir(0,0,1)), -math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3))
        parts.append((part['role'], cad.BRepBuilderAPI_Transform(shape, tr, True).Shape()))
    report = {'schema': 'native-current-intake-section/v1',
              'inputs_sha256': expected, 'source_sha256': inspection.digest(__file__),
              'manufacturing_authorized': False, 'new_roof_created': candidate is not None,
              'candidate_report_sha256': inspection.digest(args.candidate_report) if candidate else None,
              'raw_negative_is_not_a_qualified_fluid_domain': True,
              'registration_applied_only_to_module_once': True, 'sections': []}
    for x in (22.5, 0.):
        plane = cad.gp_Pln(cad.gp_Pnt(x,0,0), cad.gp_Dir(1,0,0))
        face = cad.BRepBuilderAPI_MakeFace(plane, -150.,150.,-150.,150.).Face()
        rows = []
        for role, shape in parts:
            section = cad.BRepAlgoAPI_Section(shape, plane, False)
            section.Build()
            if not section.IsDone():
                raise ValueError('native_section_failed')
            edges = cad.indexed(section.Shape(), cad.TopAbs_EDGE)
            curves = []
            for i in range(1, edges.Extent()+1):
                curve = BRepAdaptor_Curve(cad.TopoDS.Edge_s(edges.FindKey(i)))
                a, b = curve.FirstParameter(), curve.LastParameter()
                if not math.isfinite(a+b):
                    raise ValueError('unbounded_section_curve')
                points = [curve.Value(a+(b-a)*k/40) for k in range(41)]
                curves.append([[q.Y(), q.Z()] for q in points])
            triangles = []
            if role != 'intake_raw_negative':
                op = BRepAlgoAPI_Common(shape, face)
                if not op.IsDone():
                    raise ValueError('planar_common_failed')
                common = op.Shape()
                BRepMesh_IncrementalMesh(common, .04, False, .15, False)
                faces = cad.indexed(common, cad.TopAbs_FACE)
                for i in range(1, faces.Extent()+1):
                    location = TopLoc_Location()
                    mesh = BRep_Tool.Triangulation_s(cad.TopoDS.Face_s(faces.FindKey(i)), location)
                    if mesh is None:
                        continue
                    for j in range(1, mesh.NbTriangles()+1):
                        indices = mesh.Triangle(j).Get()
                        points = [mesh.Node(k).Transformed(location.Transformation()) for k in indices]
                        triangles.append([[q.Y(),q.Z()] for q in points])
            rows.append({'role': role, 'curves': curves, 'triangles': triangles})
        report['sections'].append({'world_x': x, 'parts': rows})
    report['inputs_unchanged'] = all(inspection.digest(paths[k]) == v for k,v in expected.items())
    report['elapsed_seconds'] = time.monotonic()-start
    target = args.output/'sections.json'
    target.write_text(json.dumps(report)+'\n'); target.chmod(0o600)
    print(json.dumps({'elapsed_seconds': report['elapsed_seconds'], 'sections': len(report['sections'])}))


def render(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.lines import Line2D
    data = json.loads(args.source.read_text())
    if args.output.exists():
        raise FileExistsError(args.output)
    palette = {'body_master': '#697482', 'intake_raw_negative': '#087da8',
               'valve': '#b85143', 'seat': '#e3a225', 'guide': '#28977a'}
    fig, axes = plt.subplots(1,3,figsize=(18,8),gridspec_kw={'width_ratios':[1,1,1]})
    for ax, section, limits in zip(axes, (data['sections'][0],data['sections'][0],data['sections'][1]),
                                    ((-78,83,-16,94),(-52,52,-12,19),(-60,60,-12,94))):
        for part in section['parts']:
            role = part['role']; color = palette[role]
            if part['triangles']:
                ax.add_collection(PolyCollection(part['triangles'], facecolors=color, edgecolors='none', alpha=.9))
            for curve in part['curves']:
                ax.plot([p[0] for p in curve],[p[1] for p in curve], color=color,
                        linewidth=1.1 if role=='intake_raw_negative' else .7,
                        linestyle='--' if role=='intake_raw_negative' else '-')
        ax.axhline(0,color='#808080',lw=.8,ls=':')
        ax.set_xlim(*limits[:2]);ax.set_ylim(*limits[2:]);ax.set_aspect('equal')
        ax.set_xlabel('Y — unités du scan (hypothèse 1 unité = 1 mm)')
        ax.set_ylabel('Z — unités du scan');ax.grid(alpha=.15)
    axes[0].set_title('Coupe native X = +22,5\nAdmission à droite : levée 6 mm ; échappement fermé')
    axes[1].set_title('Détail des portées et du fond\nLe contour bleu est le négatif brut, pas un domaine CFD')
    candidate = data['new_roof_created']
    axes[2].set_title('Coupe centrale X = 0\n'+('Chambre candidate à deux pans ; bougie non percée' if candidate else 'Centre du corps encore plein : aucune chambre ajoutée'))
    axes[2].annotate('Chambre candidate\nrecessée sous les sièges' if candidate else 'Corps plein au centre\nz = 0,001 à 10',
                     xy=(0,3 if candidate else 6),xytext=(11,24),
                     arrowprops={'arrowstyle':'->','color':'#202020'},fontsize=10)
    fig.suptitle('M64 — '+('prototype CAO deux pans (non OEM) : ' if candidate else 'état CAO réel : ')+
                 'corps quatre logements + module 4V + conduit admission 06',fontsize=17,y=.97)
    labels={'body_master':'Corps chambre candidate (avant découpe des conduits)' if candidate else 'Corps maître 92640… (avant découpe des conduits)',
            'intake_raw_negative':'Conduit négatif 06 superposé', 'valve':'Soupapes', 'seat':'Sièges', 'guide':'Guides'}
    fig.legend(handles=[Line2D([0],[0],color=palette[k],lw=4,label=v) for k,v in labels.items()],
               loc='lower center',bbox_to_anchor=(.5,.067),ncol=3,frameon=False)
    fig.text(.5,.032,'Coupe extraite par OCCT des fichiers exacts ; '+
             ('chambre de conception à deux pans, pas de rapport volumétrique ni CFD.' if candidate else 'aucune chambre inventée, aucun résultat thermique ou CFD.'),ha='center',fontsize=10)
    fig.text(.5,.011,'Échelle et interfaces non certifiées. Modèle de conception non autorisé à fabriquer.',ha='center',fontsize=10,color='#9d2929')
    fig.subplots_adjust(top=.85,bottom=.19,wspace=.27)
    fig.savefig(args.output,dpi=170,facecolor='white');plt.close(fig)
    args.output.chmod(0o600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    extract_parser = sub.add_parser('extract')
    for name in inspection.EXPECTED:
        extract_parser.add_argument('--'+name,type=Path,required=True)
    extract_parser.add_argument('--output',type=Path,required=True)
    extract_parser.add_argument('--candidate-report',type=Path)
    render_parser = sub.add_parser('render')
    render_parser.add_argument('--source',type=Path,required=True)
    render_parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    (extract if args.command=='extract' else render)(args)
