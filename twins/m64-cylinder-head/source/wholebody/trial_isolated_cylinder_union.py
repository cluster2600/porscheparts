#!/usr/bin/env python3
"""Isolated native partition trial, not an accepted master or a physical release.

Record the old full-serialization guard as well as each protected face's own
geometry. Additional p-curves on another support are not physical displacement.
"""
import argparse
import io
import json
import math
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_four_valve_distribution import CAD
from trial_fixed_boundary_seam import read_native,indexed,tolerances
from trial_trimmed_support import unify_local
from run_parallel_cad_trials import native

VARIANTS={
    'land':('01cce1b6009b29f2755b2b86b52e572b2ca9872caf4704fb819da91004f87cc5',(1302,1306)),
    'collar':('3d298c4b354b30eb22704d6ca0430de24666283461effac41710e1af1adf65bb',(1302,1304,1306,1541,1542,1543)),
}


def encoded(shape):
    from OCP.BRepTools import BRepTools
    stream=io.BytesIO();BRepTools.Write_s(shape,stream);return stream.getvalue()


def own_geometry(face):
    """Exact serialized native support, located curves, trims and vertices.

    Iterate wire occurrences, including both orientations of periodic seams.
    This signature alone does not certify solid validity or region equivalence.
    """
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve2d
    from OCP.GeomTools import GeomTools
    from OCP.TopAbs import TopAbs_WIRE,TopAbs_VERTEX
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS,TopoDS_Iterator
    def geom(item):
        if item is None:return None
        stream=io.BytesIO();GeomTools.Write_s(item,stream);return stream.getvalue()
    def placement(loc):
        t=loc.Transformation();return tuple(t.Value(i,j) for i in range(1,4) for j in range(1,5))
    face=TopoDS.Face_s(face);loc=TopLoc_Location();surface=BRep_Tool.Surface_s(face,loc)
    rows=[(geom(surface),placement(loc),str(face.Orientation()),BRep_Tool.Tolerance_s(face),BRep_Tool.NaturalRestriction_s(face))]
    for wire in indexed(face,TopAbs_WIRE):
        items=[];it=TopoDS_Iterator(wire)
        while it.More():
            edge=TopoDS.Edge_s(it.Value());loc=TopLoc_Location();curve=BRep_Tool.Curve_s(edge,loc,0.,0.)
            pc=BRep_Tool.CurveOnSurface_s(edge,face,0.,0.);c2=BRepAdaptor_Curve2d(edge,face)
            items.append((str(edge.Orientation()),geom(curve),placement(loc),geom(pc),BRep_Tool.Range_s(edge),
                (c2.FirstParameter(),c2.LastParameter()),BRep_Tool.Tolerance_s(edge),BRep_Tool.SameRange_s(edge),
                BRep_Tool.SameParameter_s(edge),BRep_Tool.Degenerated_s(edge),
                tuple((encoded(v),str(v.Orientation())) for v in indexed(edge,TopAbs_VERTEX))))
            it.Next()
        rows.append((str(wire.Orientation()),wire.Closed(),tuple(items)))
    return tuple(rows)


def edge_occurrences(face):
    from OCP.TopAbs import TopAbs_WIRE
    from OCP.TopoDS import TopoDS,TopoDS_Iterator
    for wire in indexed(face,TopAbs_WIRE):
        it=TopoDS_Iterator(wire)
        while it.More():yield TopoDS.Edge_s(it.Value());it.Next()


def periodic_seam(face,edge):
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    uses=[e for e in edge_occurrences(face) if e.IsSame(edge)]
    return (len(uses)==2 and uses[0].Orientation()!=uses[1].Orientation()
            and BRep_Tool.IsClosed_s(TopoDS.Edge_s(edge),TopoDS.Face_s(face)))


def pcurve_gaps(faces):
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Curve2d,BRepAdaptor_Surface
    from OCP.TopoDS import TopoDS
    rows=[]
    for i,raw in faces:
        face=TopoDS.Face_s(raw);surface=BRepAdaptor_Surface(face)
        for j,edge in enumerate(edge_occurrences(face),1):
            curve=BRepAdaptor_Curve(edge);pc=BRepAdaptor_Curve2d(edge,face)
            lo,hi=curve.FirstParameter(),curve.LastParameter()
            bounds=(lo,hi,pc.FirstParameter(),pc.LastParameter())
            if not all(math.isfinite(t) for t in bounds) or lo>=hi or max(abs(lo-bounds[2]),abs(hi-bounds[3]))>1e-12:
                raise ValueError('matching_bounded_curve_ranges_required')
            gaps=[]
            for k in range(129):
                t=lo+(hi-lo)*k/128;uv=pc.Value(t)
                gaps.append(curve.Value(t).Distance(surface.Value(uv.X(),uv.Y())))
            if not all(math.isfinite(x) for x in gaps):raise ValueError('finite_pcurve_gaps_required')
            rows.append(dict(face=i,edge_occurrence=j,samples=129,maximum_sampled_gap=max(gaps)))
    return rows


def run(args):
    import OCP
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_SHELL
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Lin
    sha,selected=VARIANTS[args.variant]
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or native.sha256(args.body)!=sha or OCP.__version__!='7.9.3.1'):
        raise ValueError('exact_native_input_runtime_and_fresh_output_required')
    args.output.mkdir(mode=0o700);signal.alarm(180);start=time.monotonic();cad=CAD()
    report=dict(schema='m64-isolated-cylinder-union/v1',status='incomplete',input_sha256=sha,
        source_sha256=native.sha256(__file__),helper_sha256=native.sha256(Path(__file__).with_name('trial_trimmed_support.py')),
        selected_faces_private=selected,master_replaced=False,manufacturing_authorized=False,
        independent_BOP_performed=False,physical_millimetres_certified=False)
    reference=read_native(args.body);original=encoded(reference);shape=read_native(args.body);working=encoded(shape)
    def save():native.save(args.output/'report.json',report)
    save()
    try:
        faces=indexed(shape,TopAbs_FACE);before_tol=tolerances(shape)
        surfaces=[BRepAdaptor_Surface(TopoDS.Face_s(faces[i-1])) for i in selected]
        if not all(s.GetType()==GeomAbs_Cylinder for s in surfaces):raise ValueError('cylinders_required')
        base=surfaces[0].Cylinder();checks=[]
        for i,s in zip(selected,surfaces):
            c=s.Cylinder();d=(abs(c.Radius()-base.Radius()),gp_Lin(base.Axis()).Distance(c.Location()),c.Axis().Direction().Angle(base.Axis().Direction()))
            if max(d)>1e-12 or faces[i-1].Orientation()!=faces[selected[0]-1].Orientation():raise ValueError('coincident_oriented_cylinders_required')
            checks.append(dict(face_private=i,radius_difference=d[0],axis_distance=d[1],axis_angle=d[2]))
        protected={i:(encoded(f),own_geometry(f)) for i,f in enumerate(faces,1) if i not in selected}
        edge_map=TopTools_IndexedMapOfShape();owners={}
        for i,f in enumerate(faces,1):
            for e in indexed(f,TopAbs_EDGE):owners.setdefault(edge_map.Add(e),[]).append(i)
        internal={k for k,fs in owners.items() if len(fs)==2 and set(fs)<=set(selected)}
        graph={i:set() for i in selected}
        for k in internal:
            i,j=owners[k];graph[i].add(j);graph[j].add(i)
        reached={selected[0]};pending=[selected[0]]
        while pending:
            for i in graph[pending.pop()]-reached:reached.add(i);pending.append(i)
        if reached!=set(selected):raise ValueError('connected_selected_group_required')
        result=unify_local(shape,[faces[i-1] for i in protected]);after=indexed(result,TopAbs_FACE)
        mapping=TopTools_IndexedMapOfShape();edges_after=TopTools_IndexedMapOfShape()
        for f in after:mapping.Add(f)
        for e in indexed(result,TopAbs_EDGE):edges_after.Add(e)
        changed=[i for i,f in enumerate(faces,1) if not mapping.Contains(f)]
        protected_bytes=[i for i,(raw,_) in protected.items() if not mapping.Contains(faces[i-1]) or encoded(after[mapping.FindIndex(faces[i-1])-1])!=raw]
        protected_geometry=[i for i,(_,g) in protected.items() if not mapping.Contains(faces[i-1]) or own_geometry(after[mapping.FindIndex(faces[i-1])-1])!=g]
        protected_result_ids={mapping.FindIndex(faces[j-1]) for j in protected}
        new_faces=[(i,f) for i,f in enumerate(after,1) if i not in protected_result_ids]
        at=tolerances(result);removed={k for k in owners if not edges_after.Contains(edge_map.FindKey(k))}
        retained=internal-removed;seams=[]
        for k in sorted(retained):
            edge=edge_map.FindKey(k)
            incident=[(i,f) for i,f in enumerate(after,1) if any(e.IsSame(edge) for e in indexed(f,TopAbs_EDGE))]
            seams.append(dict(original_edge_private=k,incident_faces_private=[i for i,_ in incident],
                passed=len(incident)==1 and incident[0][0] in {i for i,_ in new_faces} and periodic_seam(incident[0][1],edge)))
        pcurves=pcurve_gaps(new_faces)
        report.update(cylinder_checks=checks,changed_faces_private=changed,protected_serialization_changed_private=protected_bytes,
            protected_own_geometry_changed_private=protected_geometry,removed_edges_private=sorted(removed),internal_edges_private=sorted(internal),
            native_valid=cad.valid(result),solids=len(indexed(result,TopAbs_SOLID)),shells=len(indexed(result,TopAbs_SHELL)),
            faces=len(after),new_faces_private=[i for i,_ in new_faces],new_face_pcurve_samples_private=pcurves,
            tolerances_not_increased=all(max(at[k])<=max(before_tol[k]) for k in at),
            before_selected_area=sum(cad.area(faces[i-1]) for i in selected),after_selected_area=sum(cad.area(f) for _,f in new_faces),
            retained_internal_seams_private=seams,new_edges_created=any(not edge_map.Contains(e) for e in indexed(result,TopAbs_EDGE)),
            working_copy_serialization_changed=encoded(shape)!=working,
            preserved_face_map_private={i:mapping.FindIndex(f) for i,f in enumerate(faces,1) if mapping.Contains(f)})
        if (set(changed)!=set(selected) or len(new_faces)!=1 or not removed<=internal or not removed
                or not all(r['passed'] for r in seams) or report['new_edges_created'] or protected_geometry
                or not report['native_valid'] or report['solids']!=1 or report['shells']!=1 or not report['tolerances_not_increased']
                or abs(report['before_selected_area']-report['after_selected_area'])>1e-6
                or not pcurves or max(r['maximum_sampled_gap'] for r in pcurves)>1e-6):
            raise ValueError('native_boundary_geometry_or_pcurve_guard_failed')
        path=args.output/'candidate-private.brep'
        if not BRepTools.Write_s(result,str(path)):raise ValueError('native_write_failed')
        path.chmod(0o600);report.update(candidate_sha256=native.sha256(path),readback_valid=cad.valid(read_native(path)))
        if not report['readback_valid']:raise ValueError('native_readback_invalid')
        report['status']='diagnostic_pending_BOP_mesh_and_independent_region_review'
    except Exception as error:report.update(status='rejected',error=type(error).__name__+': '+str(error))
    finally:
        signal.alarm(0);report.update(isolated_reference_unchanged=encoded(reference)==original,
            file_unchanged=native.sha256(args.body)==sha,seconds=time.monotonic()-start)
        if not report['isolated_reference_unchanged'] or not report['file_unchanged']:report['status']='rejected_source_changed'
        save()
    print(json.dumps({k:report.get(k) for k in ('status','error','candidate_sha256','faces','seconds')}))
    return 0 if report['status'].startswith('diagnostic_pending') else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('body','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--variant',choices=VARIANTS,required=True)
    raise SystemExit(run(p.parse_args()))
