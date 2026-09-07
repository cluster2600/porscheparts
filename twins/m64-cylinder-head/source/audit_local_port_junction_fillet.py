#!/usr/bin/env python3
"""Read-only local-fillet constraints and real native tessellation receipt."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import build_local_port_junction_fillet as local


def boolean(kind, a, b):
    from OCP.TopTools import TopTools_ListOfShape
    job = kind(); args = TopTools_ListOfShape(); tools = TopTools_ListOfShape()
    args.Append(a); tools.Append(b)
    job.SetArguments(args); job.SetTools(tools); job.SetNonDestructive(True)
    job.SetRunParallel(False); job.SetFuzzyValue(0.); job.Build()
    if not job.IsDone():
        raise ValueError('read-only diagnostic Boolean failed')
    return job.Shape()


def tessellate(cad, shape, output):
    import numpy as np
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location
    mesh = BRepMesh_IncrementalMesh(shape, 0.025, False, 0.15, False)
    if not mesh.IsDone():
        raise ValueError('tessellation incomplete')
    faces = cad.indexed(shape, TopAbs_FACE); points=[]; triangles=[]; face_ids=[]
    for index in range(1, faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index)); loc = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face,loc)
        if mesh is None or mesh.NbTriangles()==0:
            raise ValueError('untessellated face')
        offset=len(points)
        points.extend(mesh.Node(i).Transformed(loc.Transformation()).Coord() for i in range(1,mesh.NbNodes()+1))
        for i in range(1,mesh.NbTriangles()+1):
            a,b,c=mesh.Triangle(i).Get()
            if face.Orientation()==TopAbs_REVERSED:b,c=c,b
            triangles.append([offset+a-1,offset+b-1,offset+c-1]);face_ids.append(index)
    np.savez_compressed(output,points=np.asarray(points),triangles=np.asarray(triangles,dtype=np.int64),
                        original_face_id=np.asarray(face_ids,dtype=np.int32))
    output.chmod(0o600)
    return {'path':str(output),'sha256':local.ports.sha(output),'faces':faces.Extent(),
            'triangles':len(triangles),'deflection':0.025,'angular_deflection_radians':0.15,
            'no_smoothing_or_decimation_or_transform':True}


def run(args):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepTools import BRepTools
    cad=local.ports.design.CAD();api=local.ports.native();start=time.monotonic()
    paths={'source':args.source,'prototype':args.prototype,'checkpoint':args.checkpoint,'body':args.body,
           'audit_source':Path(__file__),'fillet_source':Path(local.__file__)}
    hashes={k:local.ports.sha(p) for k,p in paths.items()}
    if hashes['body']!=args.body_sha256:
        raise ValueError('body hash mismatch')
    checkpoint=json.loads(args.checkpoint.read_text())
    if hashes['source']!=checkpoint['exports']['native_BRep_sha256']:
        raise ValueError('source checkpoint mismatch')
    if args.output.exists():raise FileExistsError(args.output)
    args.output.mkdir(mode=0o700)
    report={'schema':'private-local-junction-constraint-audit/v1','inputs_sha256':hashes,
            'length_unit':'unverified_scan_unit','no_body_cut_performed':True,
            'manufacturing_authorized':False,'prototype_tolerance_rejection_not_overridden':True}
    source=local.read_native(args.source);prototype=local.read_native(args.prototype)
    report['meshes']={}
    for name,shape in [('before',source),('after',prototype)]:
        report['meshes'][name]=tessellate(cad,shape,args.output/(name+'.npz'))
    local.ports.save(args.output/'tessellation-receipt.json',report)
    print('Before/after native meshes retained',flush=True)
    added=boolean(BRepAlgoAPI_Cut,prototype,source)
    removed=boolean(BRepAlgoAPI_Cut,source,prototype)
    av,ae=local.bounded.adaptive_volume(added);rv,re=local.bounded.adaptive_volume(removed)
    report['delta']={'added_valid':cad.valid(added),'removed_valid':cad.valid(removed),
                     'added_volume':av,'removed_volume':rv,'added_volume_error_estimate':ae,
                     'removed_volume_error_estimate':re,
                     'added_bbox_private':local.ports.bbox(api,added) if av>0 else None}
    path=args.output/'added-gas-volume.brep';BRepTools.Write_s(added,str(path));path.chmod(0o600)
    report['delta']['added_BRep_sha256']=local.ports.sha(path)
    local.ports.save(args.output/'delta-receipt.json',report)
    rows=[]
    for section in checkpoint['seed_sections_private']:
        axis=api['gp_Ax2'](api['gp_Pnt'](*section['center']),api['gp_Dir'](*section['normal']))
        circle=api['gp_Circ'](axis,section['radius'])
        wire=api['BRepBuilderAPI_MakeWire'](api['BRepBuilderAPI_MakeEdge'](circle).Edge()).Wire()
        disc=BRepBuilderAPI_MakeFace(wire).Face()
        expected=math.pi*section['radius']**2
        areas={}
        for name,shape in [('before',source),('after',prototype)]:
            missing=boolean(BRepAlgoAPI_Cut,disc,shape)
            areas[name+'_missing_disc_area']=cad.area(missing)
        rows.append({'section_private':section,'expected_disc_area':expected,**areas})
    report['section_discs']=rows
    report['all_recorded_section_discs_retained_area_screen']=all(row['before_missing_disc_area']<=1e-8 and row['after_missing_disc_area']<=1e-8 for row in rows)
    local.ports.save(args.output/'section-receipt.json',report)
    print('Recorded section disks audited',flush=True)
    body=cad.read_step(args.body)
    outside=boolean(BRepAlgoAPI_Cut,added,body)
    ov,oe=local.bounded.adaptive_volume(outside)
    shells=cad.indexed(body,TopAbs_SHELL)
    if shells.Extent()!=1:raise ValueError('expected one closed body shell')
    report['protection']={'added_outside_body_volume':ov,'outside_volume_error_estimate':oe,
                          'added_to_body_boundary_distance':cad.distance(added,shells.FindKey(1)),
                          'body_boundary_includes_all_original_skin_and_nominal_seat_guide_housings':True,
                          'distance_is_kernel_numerical_not_certified_hot_wall':True,
                          'body_registration_reapplied':False}
    report['source_files_unchanged']=all(local.ports.sha(p)==hashes[k] for k,p in paths.items())
    report['wall_seconds']=time.monotonic()-start
    local.ports.save(args.output/'constraint-report.json',report)
    print(json.dumps({'delta':report['delta'],'protection':report['protection'],
                      'section_discs_retained':report['all_recorded_section_discs_retained_area_screen'],
                      'wall_seconds':report['wall_seconds']}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','prototype','checkpoint','body','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--body-sha256',required=True)
    args=parser.parse_args();resource.setrlimit(resource.RLIMIT_CPU,(300,305));run(args)


if __name__=='__main__':main()
