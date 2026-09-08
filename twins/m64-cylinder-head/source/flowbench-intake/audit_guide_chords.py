#!/usr/bin/env python3
"""Read-only diagnostics on a persisted gas surface, not mesh acceptance.

The floating-point broad phase is not an exhaustive intersection proof. Every
reported proper crossing is rechecked with exact rational MSH coordinates.
Run --native-only separately in an OCP runtime for analytic cylinder diagnostics.
No CAD repair, mesh generation, tolerance change or physical qualification.
"""
import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

FACES=(55,58,62,63)
DOMAIN_SHA='3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'
FACE_SHAS={55:'f4b546496c1b4a040c561ea46685469ec7e9feb4ab3c5dbe9efbeba58b81d465',
           58:'6312431d0d6bc19ac6a13b9197de9a2c2ff01741c0b065062f3c355afdcf1e82',
           62:'fe1820f9e706df3db439445746ede2b9c5888f61dd019c2bb489ff01129c9ffc',
           63:'5134bae58c7ae348813da1ea39c02e2e639b9f266828067d616fd40569b4c646'}
PRIVATE_ROOT=Path('/Users/maxime/projects/3dprinting993/work/m64-private-20260907')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))


def exact_crossing(segment,triangle):
    """Strict interior noncoplanar intersection, exact rational arithmetic.

    Endpoints, triangle edges and coplanarity are deliberately not classified.
    This predicate proves only its returned proper intersection, not absence.
    """
    p,q=(tuple(Fraction(x) for x in row) for row in segment)
    a,b,c=(tuple(Fraction(x) for x in row) for row in triangle)
    direction=sub(q,p);e1=sub(b,a);e2=sub(c,a);h=cross(direction,e2)
    determinant=dot(e1,h)
    if not determinant:return None
    offset=sub(p,a);u=dot(offset,h)/determinant
    k=cross(offset,e1);v=dot(direction,k)/determinant;t=dot(e2,k)/determinant
    if not (0<t<1 and u>0 and v>0 and u+v<1):return None
    return {'t':float(t),'u':float(u),'v':float(v),
            'exact_rational_parameters':{'t':str(t),'u':str(u),'v':str(v)},
            'strict_interior_crossing_exact_for_saved_MSH':True}


def sagitta(radius,chord):
    if not all(math.isfinite(x) for x in (radius,chord)) or radius<=0 or not 0<=chord<2*radius:
        raise ValueError('finite_positive_radius_and_minor_chord_required')
    # Rationalized expression avoids cancellation for short chords.
    return (chord/2)**2/(radius+math.sqrt(radius*radius-(chord/2)**2))


def radial_triangle_minimum(radial,axis):
    """Distance from origin to the whole projected convex triangle, not edges only."""
    signs=[dot(axis,cross(a,b)) for a,b in zip(radial,radial[1:]+radial[:1])]
    area=dot(axis,cross(sub(radial[1],radial[0]),sub(radial[2],radial[0])))
    if area and (all(s>=0 for s in signs) or all(s<=0 for s in signs)):
        return 0.  # Axis lies inside/on triangle: short-edge assumptions are not used.
    minimum=math.inf
    for a,b in zip(radial,radial[1:]+radial[:1]):
        direction=sub(b,a);den=dot(direction,direction)
        t=max(0.,min(1.,-dot(a,direction)/den)) if den else 0.
        closest=tuple(x+t*d for x,d in zip(a,direction))
        minimum=min(minimum,math.sqrt(dot(closest,closest)))
    return minimum


def mesh_chord_gate(points,triangles_by_face,frames):
    """Pure, conservative radial envelope gate on the four exact native05 faces.

    Frames are private native exports; caller must verify the frame receipt SHA.
    Passing only bounds the paired cylinders, never all surface intersections,
    volume quality, CFD or manufacturing. Target h is not an acceptance metric.
    """
    if frames['domain_sha256']!=DOMAIN_SHA:raise ValueError('exact_native05_frames_required')
    rows={r['face_id']:r for r in frames['faces_private']}
    if len(rows)!=4 or len(frames['faces_private'])!=4 or set(rows)!=set(FACES):
        raise ValueError('four_unique_native_cylinder_frames_required')
    results={}
    for fid,row in rows.items():
        if row['face_sha256']!=FACE_SHAS[fid]:raise ValueError('native_face_frame_hash_mismatch')
        radius=row['radius'];axis=tuple(row['axis_direction_private']);origin=tuple(row['axis_point_private'])
        tolerance=row['native_max_tolerance'];values=(radius,tolerance,*axis,*origin)
        if len(axis)!=3 or len(origin)!=3 or not all(math.isfinite(v) for v in values):
            raise ValueError('finite_native_cylinder_frame_required')
        if radius<=0 or tolerance<=0 or abs(dot(axis,axis)-1)>1e-12:
            raise ValueError('positive_radius_tolerance_and_unit_axis_required')
        triangles=triangles_by_face.get(fid)
        if not triangles:raise ValueError('nonempty_native_cylinder_mesh_required')
        radial={};node_error=0.
        for n in {n for tri in triangles for n in tri}:
            xyz=tuple(points[n])
            if len(xyz)!=3 or not all(math.isfinite(v) for v in xyz):raise ValueError('finite_mesh_points_required')
            d=sub(xyz,origin);axial=dot(d,axis);r=tuple(x-axial*a for x,a in zip(d,axis))
            radial[n]=r;node_error=max(node_error,abs(math.sqrt(dot(r,r))-radius))
        minimum=math.inf;maximum_chord=0.
        for tri in triangles:
            if len(tri)!=3 or len(set(tri))!=3:raise ValueError('three_distinct_nodes_required')
            r=[radial[n] for n in tri]
            minimum=min(minimum,radial_triangle_minimum(r,axis))
            maximum_chord=max(maximum_chord,*(math.sqrt(dot(sub(a,b),sub(a,b))) for a,b in zip(r,r[1:]+r[:1])))
        inward=max(0.,radius-minimum)
        results[fid]={'face_id':fid,'radius':radius,'triangles':len(triangles),
            'maximum_node_radial_error':node_error,'node_radius_within_native_tolerance':node_error<=tolerance,
            'minimum_radius_over_whole_facets':minimum,'maximum_transverse_chord':maximum_chord,
            'radial_envelope_error_bound':max(inward,node_error)}
    pairs=[]
    for guide,stem in ((55,63),(58,62)):
        g,s=rows[guide],rows[stem];axis=tuple(g['axis_direction_private'])
        direction_cross=cross(axis,s['axis_direction_private'])
        offset=sub(s['axis_point_private'],g['axis_point_private']);axial=dot(offset,axis)
        residual=tuple(d-axial*a for d,a in zip(offset,axis));axis_distance=math.sqrt(dot(residual,residual))
        parallel=math.sqrt(dot(direction_cross,direction_cross))<=1e-12
        gap=g['radius']-s['radius']
        # Bound frame differences over the whole convex facets by the maximum
        # norm of their linear radial-projection difference at mesh vertices.
        # This covers tiny nonparallel axes as well as an origin offset.
        frame_error=0.;stem_axis=tuple(s['axis_direction_private'])
        for n in {n for tri in triangles_by_face[stem] for n in tri}:
            dg=sub(points[n],g['axis_point_private']);ds=sub(points[n],s['axis_point_private'])
            rg=tuple(x-dot(dg,axis)*a for x,a in zip(dg,axis))
            rs=tuple(x-dot(ds,stem_axis)*a for x,a in zip(ds,stem_axis))
            difference=sub(rg,rs);frame_error=max(frame_error,math.sqrt(dot(difference,difference)))
        bound=results[guide]['radial_envelope_error_bound']+results[stem]['radial_envelope_error_bound']+frame_error
        matching_gap=abs(gap-.015)<=1e-12
        accepted=parallel and matching_gap and bound<=.0075 and all(results[i]['node_radius_within_native_tolerance'] for i in (guide,stem))
        pairs.append({'guide_face':guide,'stem_face':stem,'native_radial_gap':gap,
            'parallel_axes_numeric':parallel,'axis_line_distance':axis_distance,
            'maximum_frame_radial_projection_difference_over_stem_vertices':frame_error,
            'sum_radial_envelope_errors_including_axis_offset':bound,'maximum_allowed_error_sum':.0075,
            'conservative_remaining_radial_clearance':gap-bound,'accepted_local_radial_envelope':accepted})
    return {'faces':list(results.values()),'pairs':pairs,
        'local_radial_envelopes_accepted':all(p['accepted_local_radial_envelope'] for p in pairs),
        'all_surface_intersections_or_CFD_or_manufacturing_qualified':False,
        'method':'minimum_radius_of_entire_projected_triangle_convex_hull_not_edges_only'}


def read_surface(path):
    lines=path.read_text().splitlines()
    if lines[lines.index('$MeshFormat')+1]!='2.2 0 8':raise ValueError('ASCII_MSH22_required')
    first=lines.index('$Nodes')+1;points={}
    for line in lines[first+1:first+1+int(lines[first])]:
        values=line.split();points[int(values[0])]=tuple(values[1:4])
    first=lines.index('$Elements')+1;triangles=[]
    for line in lines[first+1:first+1+int(lines[first])]:
        v=list(map(int,line.split()))
        if v[1]!=2:raise ValueError('surface_triangles_only_required')
        if v[2]<2 or len(v)!=6+v[2]:raise ValueError('linear_tagged_triangle_required')
        triangles.append({'tag':v[0],'face':v[4],'nodes':tuple(v[3+v[2]:])})
    if len(triangles)>250000:raise ValueError('bounded_diagnostic_limit_exceeded')
    return points,triangles


def crossings(points,triangles):
    import numpy as np
    from rtree import index
    edges=defaultdict(set)
    for tri in triangles:
        ns=tri['nodes']
        for a,b in zip(ns,ns[1:]+ns[:1]):edges[tuple(sorted((a,b)))].add(tri['face'])
    coords={k:np.asarray(v,dtype=float) for k,v in points.items()}
    t=np.asarray([[coords[n] for n in tri['nodes']] for tri in triangles])
    e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];norm=np.linalg.norm(np.cross(e1,e2),axis=1)
    prop=index.Property();prop.dimension=3
    tree=index.Index(((i,tuple(np.r_[a,b]),None) for i,(a,b) in enumerate(zip(t.min(1),t.max(1)))),properties=prop)
    pairs=0;hits=[]
    for edge,owners in edges.items():
        a,b=(coords[n] for n in edge);d=b-a;length=float(np.linalg.norm(d))
        candidates=[i for i in tree.intersection(tuple(np.r_[np.minimum(a,b),np.maximum(a,b)]))
                    if not set(edge).intersection(triangles[i]['nodes'])]
        pairs+=len(candidates)
        if not candidates:continue
        cs=np.asarray(candidates);h=np.cross(np.broadcast_to(d,(len(cs),3)),e2[cs])
        det=np.einsum('ij,ij->i',e1[cs],h);mask=np.abs(det)>1e-13*length*norm[cs]
        cs=cs[mask];h=h[mask];det=det[mask]
        if not len(cs):continue
        s=a-t[cs,0];u=np.einsum('ij,ij->i',s,h)/det;q=np.cross(s,e1[cs])
        v=np.einsum('ij,j->i',q,d)/det;at=np.einsum('ij,ij->i',e2[cs],q)/det
        near=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(at>=-1e-10)&(at<=1+1e-10)
        for k in np.flatnonzero(near):
            tri=triangles[int(cs[k])]
            proof=exact_crossing([points[n] for n in edge],[points[n] for n in tri['nodes']])
            if proof:hits.append({'segment_nodes_private':edge,'segment_owner_faces':sorted(owners),
                                  'facet_tag_private':tri['tag'],'facet_nodes_private':tri['nodes'],
                                  'facet_face':tri['face'],**proof})
    return {'surface_edges':len(edges),'broad_phase_candidate_pairs':pairs,
            'proper_crossings_exactly_verified':len(hits),'crossings_private':hits,
            'exhaustive_self_intersection_or_nonintersection_proof':False,
            'coplanarity_shared_vertices_and_boundary_touches_not_classified':True,
            'broad_phase_parallel_relative_filter':1e-13,'broad_phase_barycentric_margin':1e-10}


def native_cylinders(domain,points,triangles):
    import numpy as np
    from OCP.BRep import BRep_Builder,BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape,TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.GeomAbs import GeomAbs_Cylinder
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(domain),BRep_Builder()):raise ValueError('native_read_failed')
    faces=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    result=[];axes={};frames={'domain_sha256':sha(domain),'faces_private':[]}
    for fid in FACES:
        adaptor=BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(fid)),True)
        if adaptor.GetType()!=GeomAbs_Cylinder:raise ValueError('expected_native_cylinder')
        cylinder=adaptor.Cylinder();origin=np.asarray(cylinder.Location().Coord())
        axis=np.asarray(cylinder.Axis().Direction().Coord());radius=cylinder.Radius();axes[fid]=(origin,axis)
        face=TopoDS.Face_s(faces.FindKey(fid));tolerance=BRep_Tool.Tolerance_s(face)
        for kind,cast in ((TopAbs_EDGE,TopoDS.Edge_s),(TopAbs_VERTEX,TopoDS.Vertex_s)):
            indexed=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(face,kind,indexed)
            tolerance=max(tolerance,*(BRep_Tool.Tolerance_s(cast(indexed.FindKey(i))) for i in range(1,indexed.Extent()+1)))
        frames['faces_private'].append({'face_id':fid,'face_sha256':FACE_SHAS[fid],'radius':radius,
            'axis_point_private':list(map(float,origin)),'axis_direction_private':list(map(float,axis)),
            'native_max_tolerance':tolerance})
        selected=[t for t in triangles if t['face']==fid];edges=set();nodes=set()
        for tri in selected:
            ns=tri['nodes'];nodes.update(ns)
            for a,b in zip(ns,ns[1:]+ns[:1]):edges.add(tuple(sorted((a,b))))
        radial={}
        for n in nodes:
            d=np.asarray(points[n],dtype=float)-origin;radial[n]=d-(d@axis)*axis
        node_error=max(abs(float(np.linalg.norm(r))-radius) for r in radial.values())
        minimum=radius;max_transverse=0.
        for a,b in edges:
            v=radial[b]-radial[a];den=float(v@v)
            at=float(np.clip(-(radial[a]@v)/den,0,1)) if den else 0.
            minimum=min(minimum,float(np.linalg.norm(radial[a]+at*v)))
            max_transverse=max(max_transverse,math.sqrt(den))
        result.append({'face_id':fid,'radius':radius,'triangles':len(selected),
            'maximum_node_radius_error':node_error,'minimum_edge_radius':minimum,
            'maximum_edge_sagitta':radius-minimum,'maximum_transverse_edge_chord':max_transverse,
            'facet_interior_bound_not_proven_by_edge_measurement_alone':True})
    alignment=[]
    for guide,stem in ((55,63),(58,62)):
        o,a=axes[guide];p,b=axes[stem];d=p-o
        alignment.append({'guide_face':guide,'stem_face':stem,
            'axis_cross_norm':float(np.linalg.norm(np.cross(a,b))),
            'axis_line_distance':float(np.linalg.norm(d-(d@a)*a))})
    grouped={fid:[t['nodes'] for t in triangles if t['face']==fid] for fid in FACES}
    gate=mesh_chord_gate({n:tuple(map(float,p)) for n,p in points.items()},grouped,frames)
    return {'cylinders':result,'pair_axis_alignment':alignment,'frames_private':frames,'whole_facet_chord_gate':gate}


def main(args):
    start=time.monotonic();out=args.output.resolve()
    if not out.is_relative_to(PRIVATE_ROOT) or out.exists():raise ValueError('new_private_output_required')
    manifest=json.loads(args.boundary_report.read_text());mr=json.loads(args.mesh_report.read_text())
    if sha(args.domain)!=DOMAIN_SHA or mr['native_BRep_sha256']!=DOMAIN_SHA:raise ValueError('exact_native05_required')
    if sha(args.boundary_report)!=mr['gas_domain_report_sha256']:raise ValueError('manifest_hash_mismatch')
    if sha(args.mesh)!=mr['persisted_surface']['MSH_sha256']:raise ValueError('saved_MSH_hash_mismatch')
    paths={'domain':args.domain,'boundary_report':args.boundary_report,'mesh_report':args.mesh_report,'mesh':args.mesh,'source':Path(__file__)}
    native_faces=[]
    for row in manifest['boundary_faces']:
        if row['id'] not in FACES:continue
        path=args.boundary_report.parent/row['file']
        if sha(path)!=row['sha256'] or row['sha256']!=FACE_SHAS[row['id']]:raise ValueError('native_face_hash_mismatch')
        paths['face_%d'%row['id']]=path
        native_faces.append({k:row[k] for k in ('id','role','sha256','area','surface_type','source_match')})
    hashes={k:sha(p) for k,p in paths.items()};points,triangles=read_surface(args.mesh)
    result=native_cylinders(args.domain,points,triangles) if args.native_only else crossings(points,triangles)
    report={'schema':'m64-persisted-guide-chord-diagnostic/v1','status':'diagnostic_complete_not_mesh_acceptance',
        'mode':'native_cylinder_diagnostics' if args.native_only else 'exact_rational_crossing_confirmation',
        'inputs_sha256':hashes,'native_faces':native_faces,'mesh_accepted':False,'CFD_executed':False,
        'CAD_modified':False,'manufacturing_authorized':False,'result':result,
        'elapsed_seconds':time.monotonic()-start,'all_inputs_unchanged':all(sha(p)==hashes[k] for k,p in paths.items())}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'mode':report['mode'],'report_sha256':sha(out),'elapsed_seconds':report['elapsed_seconds']}))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ('domain','boundary-report','mesh-report','mesh','output'):parser.add_argument('--'+field,type=Path,required=True)
    parser.add_argument('--native-only',action='store_true')
    resource.setrlimit(resource.RLIMIT_CPU,(110,115))
    raise SystemExit(main(parser.parse_args()))
