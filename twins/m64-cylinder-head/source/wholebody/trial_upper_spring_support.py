#!/usr/bin/env python3
"""Two bounded additive support variants, not a master or manufacturing release.

Preserve the nominal washer footprint and chamber candidate. Independently
audit contacts, BOP, mesh, cooling and loads before considering either variant.
Dimensions are uncalibrated scan units, not certified Porsche millimetres.
"""
import argparse
import io
import json
import math
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_four_valve_distribution import CAD
from build_scan_seeded_ports import operation
from trial_fixed_boundary_seam import read_native, indexed, tolerances
from run_parallel_cad_trials import native
from render_v5_v2 import PINS
from build_spring_seat_pads import unchanged_box

BODY_SHA = '93545442adaf0a95e741d50ef9efeef48c677ff3592dbeb637dba76bb74df6de'


def annulus(cad, row, bottom, top, outer, inner):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    axis, origin = row['axis_direction'], row['axis_origin']
    if (len(axis) != 3 or len(origin) != 3
            or any(isinstance(x, bool) or not math.isfinite(x) for x in (*axis, *origin, bottom, top, outer, inner))
            or not bottom < top or not 0 < inner < outer
            or not math.isclose(sum(x*x for x in axis), 1., abs_tol=1e-12, rel_tol=0.)):
        raise ValueError('finite_ring_and_unit_axis_required')
    frame = cad.gp_Ax2(cad.gp_Pnt(*(o+bottom*d for o,d in zip(origin,axis))), cad.gp_Dir(*axis))
    shape = operation(cad, BRepAlgoAPI_Cut,
        cad.BRepPrimAPI_MakeCylinder(frame,outer,top-bottom).Shape(),
        cad.BRepPrimAPI_MakeCylinder(frame,inner,top-bottom).Shape())
    if not math.isclose(cad.volume(shape), math.pi*(outer**2-inner**2)*(top-bottom), rel_tol=1e-10):
        raise ValueError('ring_volume_mismatch')
    return shape


def support_pad(cad, row, collar_height):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    if isinstance(collar_height, bool) or collar_height not in (0., 3.):
        raise ValueError('bounded_collar_height_required')
    pad = annulus(cad,row,55.1,58.1+collar_height,17.5,7.)
    if collar_height:
        pad = operation(cad,BRepAlgoAPI_Cut,pad,annulus(cad,row,58.1,58.1+collar_height,16.,7.))
    return pad


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    pins = {args.body: BODY_SHA, args.registration: PINS['registration.json'],
            Path(__file__): native.sha256(__file__)}
    if (args.output.exists() or args.output.is_symlink() or OCP.__version__ != '7.9.3.1'
            or isinstance(args.collar_height,bool) or args.collar_height not in (0.,3.)
            or any(p.is_symlink() or native.sha256(p) != h for p,h in pins.items())):
        raise ValueError('exact_inputs_and_fresh_output_required')
    args.output.mkdir(mode=0o700)
    report = dict(schema='m64-upper-spring-support/v1',status='incomplete',input_sha256=BODY_SHA,
        registration_sha256=pins[args.registration],source_sha256=pins[Path(__file__)],OCP_version=OCP.__version__,
        unit='uncalibrated_scan_unit',collar_height=args.collar_height,outer_radius=17.5,
        bottom=55.1,washer_floor=58.1,washer_inner_radius=7.,washer_outer_radius=16.,
        master_replaced=False,manufacturing_authorized=False,physical_clearance_qualified=False,
        BOP_check_performed=False,contact_audit_performed=False,mesh_run=False)
    def save(stage):
        report['stage']=stage; native.save(args.output/'report.json',report)
    def encoded(shape):
        stream=io.BytesIO(); BRepTools.Write_s(shape,stream); return stream.getvalue()
    def box(shape):
        b=Bnd_Box(); BRepBndLib.AddOptimal_s(shape,b,False,False); return list(b.Get())
    cad=CAD()
    def empty(shape):
        return not indexed(shape,TopAbs_SOLID) and cad.volume(shape)<=1e-7
    start=time.monotonic(); signal.alarm(540); save('reading')
    try:
        body=read_native(args.body); before=encoded(body); faces=indexed(body,TopAbs_FACE)
        if not cad.valid(body) or len(faces)!=4925: raise ValueError('exact_valid_parent_required')
        axes=json.loads(args.registration.read_text())['tools_private']
        row=next(r for r in axes if r['name']=='exhaust_2')
        pad=support_pad(cad,row,args.collar_height); save('union')
        candidate=operation(cad,BRepAlgoAPI_Fuse,body,pad)
        result_faces=indexed(candidate,TopAbs_FACE); mapping=TopTools_IndexedMapOfShape()
        for face in result_faces: mapping.Add(face)
        changed=[i for i,f in enumerate(faces,1) if not mapping.Contains(f)]
        preserved={i:mapping.FindIndex(f) for i,f in enumerate(faces,1) if mapping.Contains(f)}
        save('locality')
        removed=operation(cad,BRepAlgoAPI_Cut,body,candidate)
        added=operation(cad,BRepAlgoAPI_Cut,candidate,body)
        outside=operation(cad,BRepAlgoAPI_Cut,added,pad)
        bt,at=tolerances(body),tolerances(candidate)
        report.update(native_valid=cad.valid(candidate),solid_count=len(indexed(candidate,TopAbs_SOLID)),
            shell_count=len(indexed(candidate,TopAbs_SHELL)),faces=len(result_faces),changed_faces_private=changed,
            preserved_face_map_private=preserved,added_volume=cad.volume(added),removed_volume=cad.volume(removed),
            outside_pad_volume=cad.volume(outside),removed_and_outside_empty=empty(removed) and empty(outside),
            changed_face_distance_to_pad_private={i:cad.distance(faces[i-1],pad) for i in changed},
            before_bbox_private=box(body),after_bbox_private=box(candidate),
            tolerances_not_increased=all(max(at[k])<=max(bt[k]) for k in bt),
            before_max_tolerances={k:max(v) for k,v in bt.items()},after_max_tolerances={k:max(v) for k,v in at.items()},
            preserved_faces_identical=all(encoded(faces[i-1])==encoded(result_faces[j-1]) for i,j in preserved.items()),
            source_in_memory_unchanged=encoded(body)==before)
        report['overall_bbox_unchanged']=unchanged_box(report['before_bbox_private'],report['after_bbox_private'])
        save('spring_envelopes')
        overlaps=[operation(cad,BRepAlgoAPI_Common,candidate,annulus(cad,r,59.6,100.,15.,7.75)) for r in axes]
        report['spring_envelope_common_volumes']={r['name']:cad.volume(s) for r,s in zip(axes,overlaps)}
        if (report['solid_count']!=1 or report['shell_count']!=1 or not report['removed_and_outside_empty']
                or not report['overall_bbox_unchanged'] or not report['tolerances_not_increased']
                or not report['preserved_faces_identical'] or not report['source_in_memory_unchanged']
                or not all(empty(s) for s in overlaps)
                or any(x>1e-6 for x in report['changed_face_distance_to_pad_private'].values())):
            raise ValueError('native_locality_support_or_tolerance_guard_failed')
        path=args.output/'candidate-private.brep'
        if not BRepTools.Write_s(candidate,str(path)): raise ValueError('native_write_failed')
        path.chmod(0o600)
        report.update(candidate_sha256=native.sha256(path),readback_valid=cad.valid(read_native(path)))
        if not report['readback_valid']: raise ValueError('native_readback_invalid')
        report['status']='candidate_pending_contact_BOP_mesh_and_physics'
    except Exception as error:
        report.update(status='rejected',error=type(error).__name__+': '+str(error))
    finally:
        signal.alarm(0)
        report.update(seconds=time.monotonic()-start,inputs_unchanged=all(native.sha256(p)==h for p,h in pins.items()))
        if not report['inputs_unchanged']:report['status']='rejected_input_changed'
        save('finished')
    print(json.dumps({k:report.get(k) for k in ('status','error','candidate_sha256','faces','added_volume','seconds')}))
    return 0 if report['status'].startswith('candidate_pending') else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('body','registration','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--collar-height',type=float,choices=(0.,3.),required=True)
    raise SystemExit(run(parser.parse_args()))
