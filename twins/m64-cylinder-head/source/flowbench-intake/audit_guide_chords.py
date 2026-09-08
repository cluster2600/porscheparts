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
import re
import time

FACES=(55,56,57,58,61,62,63,64)
DOMAIN_SHA='3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'
FACE_SHAS={55:'f4b546496c1b4a040c561ea46685469ec7e9feb4ab3c5dbe9efbeba58b81d465',
           56:'d3bfc62403f1bbf60bb1e71dbdda09a48e0fbf4aed8dcbbeb62a480e63b074e0',
           57:'c8dc168593fdc85c1cf52b425861ea1505d5a000dfad054f7ab8d8b7959845df',
           58:'6312431d0d6bc19ac6a13b9197de9a2c2ff01741c0b065062f3c355afdcf1e82',
           61:'3a4754f6312c4ca4b78fe14ba4127cbdb18bb8d6254d8e07a8e8dd0b16e2ba97',
           62:'fe1820f9e706df3db439445746ede2b9c5888f61dd019c2bb489ff01129c9ffc',
           63:'5134bae58c7ae348813da1ea39c02e2e639b9f266828067d616fd40569b4c646',
           64:'fc19b8b3258fb45cf7122f4d839a427b46c93c35e2be1b6de46c4570858ec159'}
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


def axial_interval(row,reference):
    axis=reference['axis_direction_private'];own=row['axis_direction_private']
    angular=math.sqrt(dot(cross(axis,own),cross(axis,own)))
    offset=sub(row['axis_point_private'],reference['axis_point_private']);along=dot(offset,axis)
    radial=sub(offset,tuple(along*a for a in axis))
    if angular>1e-12 or math.sqrt(dot(radial,radial))>row['native_max_tolerance']+reference['native_max_tolerance']:
        raise ValueError('component_cylinders_not_coaxial_within_native_tolerances')
    return sorted(along+dot(own,axis)*v for v in row['native_axial_parameter_bounds'])


def interval_union_length(intervals):
    if not intervals:return 0.
    current=None;length=0.
    for low,high in sorted(intervals):
        if current is None:current=[low,high]
        elif low<=current[1]:current[1]=max(current[1],high)
        else:length+=current[1]-current[0];current=[low,high]
    return length+current[1]-current[0]


def gap_portion_inventory(cylinders):
    """Select finite-length annular portions from ALL native cylinders.

    Radius/axis/axial overlap supplement the source component attribution.
    Boundary-only contacts inside native tolerance are explicit exclusions,
    not asserted to be exactly disjoint mathematical surfaces.
    """
    if len({r['face_id'] for r in cylinders})!=len(cylinders):raise ValueError('unique_cylinder_inventory_required')
    candidates=[];excluded=[]
    for row in cylinders:
        radius=row['radius']
        if not math.isfinite(radius) or radius<=0:raise ValueError('positive_native_radius_required')
        kind='guide' if abs(radius-3.015)<=1e-12 else 'stem' if abs(radius-3.)<=1e-12 else None
        if kind is None:
            excluded.append({'face_id':row['face_id'],'reason':'radius_not_inner_guide_or_stem','radius':radius});continue
        expected='walls_guide' if kind=='guide' else 'walls_valve'
        if row['role']!=expected or row['component'] not in ('intake_1','intake_2'):
            raise ValueError('unattributed_possible_gap_cylinder_must_be_reviewed')
        if not row['BRep_face_valid'] or not row['full_cylindrical_band_verified_numeric']:
            raise ValueError('axial_interval_requires_valid_full_cylindrical_band')
        candidates.append((row,kind))
    groups=[]
    for component in ('intake_1','intake_2'):
        guides=sorted([r for r,k in candidates if k=='guide' and r['component']==component],key=lambda r:r['face_id'])
        stems=sorted([r for r,k in candidates if k=='stem' and r['component']==component],key=lambda r:r['face_id'])
        if not guides or not stems:raise ValueError('guide_and_stem_component_required')
        reference=guides[0];intervals={r['face_id']:axial_interval(r,reference) for r in guides+stems}
        active=[];touches=[]
        for stem in stems:
            si=intervals[stem['face_id']];overlaps=[]
            for guide in guides:
                gi=intervals[guide['face_id']]
                overlaps.append((min(si[1],gi[1])-max(si[0],gi[0]),stem['native_max_tolerance']+guide['native_max_tolerance']))
            if any(length>tolerance for length,tolerance in overlaps):active.append(stem)
            else:
                touch=any(abs(length)<=tolerance for length,tolerance in overlaps)
                note={'face_id':stem['face_id'],'component':component,
                    'reason':'boundary_touch_within_native_tolerance_no_finite_length_pairing' if touch else 'no_axial_overlap_with_inner_guide',
                    'maximum_axial_overlap_numeric':max(x for x,t in overlaps)}
                excluded.append(note)
                if touch:touches.append(stem['face_id'])
        coverage=[]
        for guide in guides:
            low,high=intervals[guide['face_id']]
            clips=[(max(low,intervals[s['face_id']][0]),min(high,intervals[s['face_id']][1])) for s in active]
            covered=interval_union_length([(a,b) for a,b in clips if b>a]);missing=max(0.,high-low-covered)
            tolerance=guide['native_max_tolerance']+max(s['native_max_tolerance'] for s in active) if active else 0.
            if not active or missing>tolerance:raise ValueError('inner_guide_axial_coverage_incomplete')
            coverage.append({'guide_face':guide['face_id'],'axial_length':high-low,'covered_stem_length':covered,
                'uncovered_length_numeric':missing,'native_tolerance_budget':tolerance})
        groups.append({'component':component,'guide_faces':[r['face_id'] for r in guides],
            'stem_faces':[r['face_id'] for r in active],'reference_axis_face':reference['face_id'],
            'guide_axial_coverage':coverage,'boundary_touch_exclusions':touches})
    selected=sorted({fid for g in groups for key in ('guide_faces','stem_faces') for fid in g[key]})
    return {'groups':groups,'selected_face_ids':selected,'excluded_cylinders':excluded,
        'selection':'native_radius_component_coaxiality_and_finite_axial_overlap',
        'native_tolerances_not_modified':True}


def mesh_chord_gate(points,triangles_by_face,frames):
    """Pure conservative envelope gate on every native05 annular portion.

    Frames are private native exports; caller must verify the frame receipt SHA.
    triangles_by_face keys are NATIVE face indices, not Gmsh entity tags.
    Passing only bounds the paired cylinders, never all surface intersections,
    volume quality, CFD or manufacturing. Target h is not an acceptance metric.
    """
    if frames.get('schema')!='m64-native-guide-cylinder-frames/v2' or frames['domain_sha256']!=DOMAIN_SHA:
        raise ValueError('exact_native05_v2_inventory_frames_required')
    inventory=frames['native_inventory']
    if not inventory['all_native_faces_examined'] or len(inventory['surface_types'])!=inventory['native_face_count']:
        raise ValueError('complete_native_face_inventory_required')
    actual_cylinders=sorted(r['face_id'] for r in inventory['surface_types'] if r['surface_type']=='GeomAbs_Cylinder')
    if actual_cylinders!=sorted(r['face_id'] for r in inventory['cylinders_private']):
        raise ValueError('native_cylinder_inventory_incomplete')
    coverage=gap_portion_inventory(inventory['cylinders_private'])
    if coverage!=frames['coverage'] or coverage['selected_face_ids']!=list(FACES):
        raise ValueError('derived_gap_portion_inventory_changed_or_incomplete')
    rows={r['face_id']:r for r in frames['faces_private']}
    if len(rows)!=8 or len(frames['faces_private'])!=8 or set(rows)!=set(FACES):
        raise ValueError('eight_unique_native_gap_portion_frames_required')
    inventoried={r['face_id']:r for r in inventory['cylinders_private']}
    if any(rows[fid]!=inventoried[fid] for fid in FACES):raise ValueError('selected_frames_differ_from_native_inventory')
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
        radial={};node_error=0.;node_axials=[]
        for n in {n for tri in triangles for n in tri}:
            xyz=tuple(points[n])
            if len(xyz)!=3 or not all(math.isfinite(v) for v in xyz):raise ValueError('finite_mesh_points_required')
            d=sub(xyz,origin);axial=dot(d,axis);r=tuple(x-axial*a for x,a in zip(d,axis))
            radial[n]=r;node_axials.append(axial);node_error=max(node_error,abs(math.sqrt(dot(r,r))-radius))
        minimum=math.inf;maximum_chord=0.
        for tri in triangles:
            if len(tri)!=3 or len(set(tri))!=3:raise ValueError('three_distinct_nodes_required')
            r=[radial[n] for n in tri]
            minimum=min(minimum,radial_triangle_minimum(r,axis))
            maximum_chord=max(maximum_chord,*(math.sqrt(dot(sub(a,b),sub(a,b))) for a,b in zip(r,r[1:]+r[:1])))
        inward=max(0.,radius-minimum)
        results[fid]={'face_id':fid,'radius':radius,'triangles':len(triangles),
            'maximum_node_radial_error':node_error,'node_radius_within_native_tolerance':node_error<=tolerance,
            'nodes_within_native_axial_interval':min(node_axials)>=row['native_axial_parameter_bounds'][0]-tolerance and max(node_axials)<=row['native_axial_parameter_bounds'][1]+tolerance,
            'minimum_radius_over_whole_facets':minimum,'maximum_transverse_chord':maximum_chord,
            'radial_envelope_error_bound':max(inward,node_error)}
    groups=[]
    for group in coverage['groups']:
        reference=rows[group['reference_axis_face']];axis=reference['axis_direction_private']
        all_ids=group['guide_faces']+group['stem_faces'];bounds={}
        for fid in all_ids:
            own=rows[fid];own_axis=own['axis_direction_private'];frame_error=0.
            for n in {n for tri in triangles_by_face[fid] for n in tri}:
                dr=sub(points[n],reference['axis_point_private']);ds=sub(points[n],own['axis_point_private'])
                rr=tuple(x-dot(dr,axis)*a for x,a in zip(dr,axis));rs=tuple(x-dot(ds,own_axis)*a for x,a in zip(ds,own_axis))
                difference=sub(rr,rs);frame_error=max(frame_error,math.sqrt(dot(difference,difference)))
            bounds[fid]=results[fid]['radial_envelope_error_bound']+frame_error
        guide_bound=max(bounds[i] for i in group['guide_faces']);stem_bound=max(bounds[i] for i in group['stem_faces'])
        gap=min(rows[i]['radius'] for i in group['guide_faces'])-max(rows[i]['radius'] for i in group['stem_faces'])
        bound=guide_bound+stem_bound
        accepted=abs(gap-.015)<=1e-12 and bound<=.0075 and all(results[i]['node_radius_within_native_tolerance'] and results[i]['nodes_within_native_axial_interval'] for i in all_ids)
        groups.append({'component':group['component'],'guide_faces':group['guide_faces'],'stem_faces':group['stem_faces'],
            'native_radial_gap':gap,'worst_guide_envelope_error_in_common_frame':guide_bound,
            'worst_stem_envelope_error_in_common_frame':stem_bound,
            'sum_radial_envelope_errors_including_axis_offset':bound,'maximum_allowed_error_sum':.0075,
            'conservative_remaining_radial_clearance':gap-bound,'accepted_local_radial_envelope':accepted})
    return {'faces':list(results.values()),'groups':groups,'coverage':coverage,
        'local_radial_envelopes_accepted':all(g['accepted_local_radial_envelope'] for g in groups),
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


def bind_triangles_to_native(triangles,mesh_report,expected_native_ids):
    """Consume the saved import bijection; never assume native/Gmsh ID equality."""
    binding=mesh_report['import']['face_binding_private'];matches=binding['matches_private']
    if not binding['descriptor_bijection_verified']:raise ValueError('verified_native_Gmsh_bijection_required')
    reverse={r['gmsh_face_tag']:r['source_face_index'] for r in matches}
    if len(reverse)!=len(matches) or len(set(reverse.values()))!=len(matches) or set(reverse.values())!=set(expected_native_ids):
        raise ValueError('complete_one_to_one_native_Gmsh_binding_required')
    if {t['face'] for t in triangles}!=set(reverse):raise ValueError('saved_MSH_native_face_coverage_mismatch')
    return [{**t,'gmsh_face_tag_private':t['face'],'face':reverse[t['face']]} for t in triangles]


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


def native_cylinders(domain,points,triangles,manifest):
    from OCP.BRep import BRep_Builder,BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape,TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BRepCheck import BRepCheck_Analyzer
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(domain),BRep_Builder()):raise ValueError('native_read_failed')
    faces=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    source_rows={r['id']:r for r in manifest['boundary_faces']}
    if len(source_rows)!=len(manifest['boundary_faces']) or set(source_rows)!=set(range(1,faces.Extent()+1)):
        raise ValueError('complete_unique_classified_face_inventory_required')
    inventory={'native_face_count':faces.Extent(),'all_native_faces_examined':False,
               'surface_types':[],'cylinders_private':[]}
    for fid in range(1,faces.Extent()+1):
        face=TopoDS.Face_s(faces.FindKey(fid));adaptor=BRepAdaptor_Surface(face,True)
        surface_type=str(adaptor.GetType()).split('.')[-1];source=source_rows[fid]
        if source['surface_type']!=surface_type:raise ValueError('classified_native_surface_type_mismatch')
        inventory['surface_types'].append({'face_id':fid,'surface_type':surface_type})
        if adaptor.GetType()!=GeomAbs_Cylinder:continue
        cylinder=adaptor.Cylinder();tolerance=BRep_Tool.Tolerance_s(face)
        for kind,cast in ((TopAbs_EDGE,TopoDS.Edge_s),(TopAbs_VERTEX,TopoDS.Vertex_s)):
            indexed=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(face,kind,indexed)
            tolerance=max(tolerance,*(BRep_Tool.Tolerance_s(cast(indexed.FindKey(i))) for i in range(1,indexed.Extent()+1)))
        sources=[r.get('source','') for r in source.get('source_match',[])]
        components={m.group(1) for name in sources if (m:=re.match(r'^((?:intake|exhaust)_[12])_',name))}
        span=adaptor.LastUParameter()-adaptor.FirstUParameter();length=adaptor.LastVParameter()-adaptor.FirstVParameter()
        props=GProp_GProps();BRepGProp.SurfaceProperties_s(face,props)
        analytic=2*math.pi*cylinder.Radius()*length
        area_error=abs(props.Mass()/analytic-1.) if analytic>0 else math.inf
        inventory['cylinders_private'].append({'face_id':fid,'face_sha256':source['sha256'],
            'radius':cylinder.Radius(),'role':source['role'],'source_names':sources,
            'component':next(iter(components)) if len(components)==1 else None,
            'axis_point_private':list(cylinder.Location().Coord()),
            'axis_direction_private':list(cylinder.Axis().Direction().Coord()),
            'native_axial_parameter_bounds':[adaptor.FirstVParameter(),adaptor.LastVParameter()],
            'native_angular_parameter_span':span,'BRep_face_valid':BRepCheck_Analyzer(face,True,False,True).IsValid(),
            'native_area':props.Mass(),'full_band_analytic_area':analytic,'full_band_relative_area_error':area_error,
            'full_cylindrical_band_verified_numeric':abs(span-2*math.pi)<=1e-9 and area_error<=1e-9,
            'full_band_comparison_relative_tolerance':1e-9,
            'native_max_tolerance':tolerance})
    inventory['all_native_faces_examined']=True
    coverage=gap_portion_inventory(inventory['cylinders_private'])
    frames={'schema':'m64-native-guide-cylinder-frames/v2','domain_sha256':sha(domain),
        'native_inventory':inventory,'coverage':coverage,
        'faces_private':[r for r in inventory['cylinders_private'] if r['face_id'] in coverage['selected_face_ids']]}
    grouped={fid:[t['nodes'] for t in triangles if t['face']==fid] for fid in FACES}
    gate=mesh_chord_gate({n:tuple(map(float,p)) for n,p in points.items()},grouped,frames)
    return {'frames_private':frames,'whole_facet_chord_gate':gate}


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
        path=args.boundary_report.parent/row['file']
        if sha(path)!=row['sha256']:raise ValueError('native_face_hash_mismatch')
        if row['id'] in FACE_SHAS and row['sha256']!=FACE_SHAS[row['id']]:raise ValueError('native_gap_face_hash_mismatch')
        paths['face_%d'%row['id']]=path
        native_faces.append({k:row[k] for k in ('id','role','sha256','area','surface_type','source_match')})
    hashes={k:sha(p) for k,p in paths.items()};points,triangles=read_surface(args.mesh)
    triangles=bind_triangles_to_native(triangles,mr,[r['id'] for r in manifest['boundary_faces']])
    result=native_cylinders(args.domain,points,triangles,manifest) if args.native_only else crossings(points,triangles)
    report={'schema':'m64-persisted-guide-chord-diagnostic/v2','status':'diagnostic_complete_not_mesh_acceptance',
        'mode':'native_cylinder_diagnostics' if args.native_only else 'exact_rational_crossing_confirmation',
        'inputs_sha256':hashes,'native_faces':native_faces,'mesh_accepted':False,'CFD_executed':False,
        'MSH_faces_rebound_through_verified_native_import_bijection':True,
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
