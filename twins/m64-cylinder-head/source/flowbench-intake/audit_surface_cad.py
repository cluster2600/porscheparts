#!/usr/bin/env python3
"""Bounded independent sampled surface/CAD conformity diagnostics.

No mesh/CAD mutation, smoothing, acceptance-threshold change or global
Hausdorff/self-intersection proof. All geometry-bearing reports stay private.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

PRIVATE_ROOT=Path('/Users/maxime/projects/3dprinting993/work/m64-private-20260907')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def subtract(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return math.fsum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))


def sample_indices(count,limit):
    """Deterministic spread in persisted element order; not a worst-case proof."""
    if count<1 or limit<0:raise ValueError('positive_count_nonnegative_limit_required')
    if not limit or limit>=count:return list(range(count))
    if limit==1:return [count//2]
    return [i*(count-1)//(limit-1) for i in range(limit)]


def triangle_geometry(points):
    if len(points)!=3 or any(len(p)!=3 or not all(math.isfinite(x) for x in p) for p in points):
        raise ValueError('finite_triangle_coordinates_required')
    vector=cross(subtract(points[1],points[0]),subtract(points[2],points[0]));length=norm(vector)
    return {'area':length/2.,'degenerate':length==0.,
            'normal_private':[x/length for x in vector] if length else None}


def read_msh22(path):
    lines=path.read_text().splitlines()
    if lines[lines.index('$MeshFormat')+1]!='2.2 0 8':raise ValueError('ASCII_MSH22_required')
    start=lines.index('$Nodes')+1;count=int(lines[start]);points={}
    for line in lines[start+1:start+1+count]:
        row=line.split();tag=int(row[0])
        if tag in points:raise ValueError('duplicate_node_tag')
        points[tag]=tuple(map(float,row[1:4]))
    start=lines.index('$Elements')+1;count=int(lines[start]);triangles={}
    for line in lines[start+1:start+1+count]:
        row=list(map(int,line.split()))
        if row[1]!=2:continue
        if row[2]<2 or len(row)!=3+row[2]+3 or row[0] in triangles:raise ValueError('invalid_linear_triangle_record')
        triangles[row[0]]={'patch':row[3],'face_tag':row[4],'nodes':tuple(row[3+row[2]:])}
    return points,triangles


class FaceAudit:
    def __init__(self,face):
        from OCP.BRep import BRep_Tool
        from OCP.BRepTools import BRepTools
        from OCP.TopAbs import TopAbs_FORWARD,TopAbs_REVERSED
        self.face=face
        if not face.Location().IsIdentity():raise ValueError('explicit_world_transform_required_for_located_face')
        if face.Orientation() not in (TopAbs_FORWARD,TopAbs_REVERSED):raise ValueError('oriented_face_required')
        self.surface=BRep_Tool.Surface_s(face);self.bounds=BRepTools.UVBounds_s(face)
        self.sign=-1. if face.Orientation()==TopAbs_REVERSED else 1.
        self.tolerance=BRep_Tool.Tolerance_s(face)

    def point(self,xyz):
        from OCP.BRep import BRep_Tool
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape
        from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopoDS import TopoDS
        from OCP.gp import gp_Pnt,gp_Vec
        p=gp_Pnt(*xyz)
        distance=BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(p).Vertex(),self.face)
        if not distance.IsDone():raise ValueError('trimmed_face_distance_not_done')
        # Bind the UV to the SAME closest support found by BRepExtrema. Filtering
        # unrelated GeomAPI stationary projections by trim can select a remote
        # corner and attach its normal to the local point (historical v1 bug).
        closest=distance.PointOnShape2(1);support=distance.SupportOnShape2(1)
        row={'xyz_private':xyz,'trimmed_face_distance_numeric':distance.Value(),
            'closest_support_kind':str(support.ShapeType()).split('.')[-1],
            'closest_solution_count':distance.NbSolution(),
            'normal_method':'BRepExtrema_closest_support_native_UV_or_pcurve',
            'valid_trim_projection':False,'normal_private':None,
            'source_point_within_face_tolerance':distance.Value()<=self.tolerance}
        support_tolerance=self.tolerance
        try:
            if support.ShapeType()==TopAbs_FACE:u,v=distance.ParOnFaceS2(1)
            elif support.ShapeType()==TopAbs_EDGE:
                edge=TopoDS.Edge_s(support);parameter=distance.ParOnEdgeS2(1)
                if isinstance(parameter,tuple):parameter=parameter[0]
                curve=BRep_Tool.CurveOnSurface_s(edge,self.face,0.,0.)
                if curve is None:raise ValueError('closest_edge_pcurve_missing')
                uv=curve.Value(parameter);u,v=uv.X(),uv.Y()
                support_tolerance=BRep_Tool.Tolerance_s(edge)
            elif support.ShapeType()==TopAbs_VERTEX:
                vertex=TopoDS.Vertex_s(support);uv=BRep_Tool.Parameters_s(vertex,self.face)
                u,v=uv.X(),uv.Y();support_tolerance=BRep_Tool.Tolerance_s(vertex)
            else:raise ValueError('closest_support_has_no_native_UV')
            surface_point=self.surface.Value(u,v)
            binding_error=surface_point.Distance(closest)
            binding_budget=self.tolerance+support_tolerance
            row.update(closest_point_private=[closest.X(),closest.Y(),closest.Z()],
                closest_support_surface_binding_error=binding_error,
                native_tolerance_binding_budget=binding_budget,
                selected_projection={'uv_private':[u,v],'distance':p.Distance(surface_point),
                    'inside_trim':'native_face_support_not_stationary_projection_filter'})
            if not math.isfinite(binding_error) or binding_error>binding_budget:
                row['normal_unavailable_reason']='closest_support_surface_binding_exceeds_native_tolerances'
                return row
        except Exception as exc:
            row['normal_unavailable_reason']=type(exc).__name__+': '+str(exc)
            return row
        row['valid_trim_projection']=True
        surface_point,du,dv=gp_Pnt(),gp_Vec(),gp_Vec();self.surface.D1(u,v,surface_point,du,dv)
        a,b=(du.X(),du.Y(),du.Z()),(dv.X(),dv.Y(),dv.Z());n=cross(a,b);m=norm(n)
        row.update(surface_Jacobian_norm=m,
            surface_parametric_cross_sine=m/(norm(a)*norm(b)) if norm(a)*norm(b)>0 else 0.,
            normal_private=[self.sign*x/m for x in n] if m else None,
            surface_Jacobian_zero=m==0.)
        return row

    def triangle(self,points,vertex_rows=None):
        result=triangle_geometry(points)
        if result['degenerate']:return result
        probes=[('barycentre',tuple(math.fsum(p[i] for p in points)/3. for i in range(3)))]
        probes += [('edge_midpoint_%d'%j,tuple((points[j][i]+points[(j+1)%3][i])/2. for i in range(3))) for j in range(3)]
        result['samples']=[]
        for name,point in probes:
            row=self.point(point);row['kind']=name
            row['triangle_dot_CAD_normal']=dot(result['normal_private'],row['normal_private']) if row['normal_private'] else None
            result['samples'].append(row)
        if vertex_rows is not None and all(r['valid_trim_projection'] for r in vertex_rows):
            uv=[r['selected_projection']['uv_private'] for r in vertex_rows]
            result['UV_signed_double_area']=self.sign*((uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0]))
        result['samples_do_not_bound_entire_triangle']=True
        return result


def sampled_border_resolution(face):
    """Finite native edge/width probes, not continuous curvature/width bounds."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt,gp_Vec
    edges=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(face,TopAbs_EDGE,edges)
    rows=[];curves={}
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i));curve=BRepAdaptor_Curve(edge);curves[i]=curve
        first,last=curve.FirstParameter(),curve.LastParameter()
        row={'edge_id':i,'curve_type':str(curve.GetType()).split('.')[-1],
            'length_numeric_quadrature':GCPnts_AbscissaPoint.Length_s(curve),
            'edge_tolerance_numerical_scan_units':BRep_Tool.Tolerance_s(edge),
            'parameter_interval':[first,last],'curvature_samples':[]}
        for fraction in (.05,.2,.35,.5,.65,.8,.95):
            parameter=first+(last-first)*fraction;p,a,b=gp_Pnt(),gp_Vec(),gp_Vec()
            try:
                curve.D2(parameter,p,a,b);speed=a.Magnitude()
                kappa=a.Crossed(b).Magnitude()/speed**3 if speed else None
                row['curvature_samples'].append({'fraction':fraction,'curvature':kappa,'stationary':speed==0.})
            except Exception as exc:row['curvature_samples'].append({'fraction':fraction,'curvature':None,'error':type(exc).__name__})
        rows.append(row)
    longest=max(rows,key=lambda r:r['length_numeric_quadrature']);reference=curves[longest['edge_id']]
    width=[]
    for fraction in (.05,.1,.2,.25,.3,.35,.39,.4,.41,.5,.75,.9):
        parameter=reference.FirstParameter()+(reference.LastParameter()-reference.FirstParameter())*fraction
        point=reference.Value(parameter);vertex=BRepBuilderAPI_MakeVertex(point).Vertex();distances=[]
        for i in range(1,edges.Extent()+1):
            if i==longest['edge_id']:continue
            extrema=BRepExtrema_DistShapeShape(vertex,edges.FindKey(i))
            if not extrema.IsDone():raise ValueError('border_width_distance_not_done')
            distances.append({'opposite_edge_id':i,'distance':extrema.Value(),
                'closest_support_kind':str(extrema.SupportOnShape2(1).ShapeType()).split('.')[-1]})
        selected=min(distances,key=lambda r:r['distance'])
        width.append({'fraction':fraction,'reference_parameter':parameter,**selected})
    curvatures=[r['curvature'] for e in rows for r in e['curvature_samples'] if r['curvature'] is not None]
    if not curvatures:raise ValueError('no_native_curvature_sample_available')
    minimum=min(r['distance'] for r in width);maximum=max(curvatures)
    # Registered hypothesis for the next refinement trial, not an acceptance
    # tolerance: chord sagitta at most a quarter of sampled interior width.
    delta=minimum/4.;h=math.sqrt(8.*delta/maximum) if maximum>0 and minimum>0 else None
    local_hypotheses=[]
    for edge_id in sorted({r['opposite_edge_id'] for r in width}):
        local_width=min(r['distance'] for r in width if r['opposite_edge_id']==edge_id)
        local_hypotheses.append({'opposite_edge_id':edge_id,'sampled_width_min':local_width,
            'suggested_maximum_edge_length_from_samples':math.sqrt(2.*local_width/maximum) if maximum>0 and local_width>0 else None})
    return {'edge_count':edges.Extent(),'edges':rows,'reference_edge_id':longest['edge_id'],
        'width_samples':width,'sampled_interior_width_min':minimum,'sampled_curvature_max':maximum,
        'global_width_minimum_or_curvature_maximum_proven':False,
        'reference_fraction_range_sampled':[.05,.9],
        'width_is_distance_to_other_boundary_not_a_uv_span':True,
        'refinement_hypothesis':{'sagitta_formula':'delta approximately kappa*h^2/8',
            'width_fraction':.25,'target_sagitta':delta,'suggested_maximum_edge_length_from_samples':h,
            'per_opposite_boundary_hypotheses':local_hypotheses,
            'admissibility_or_physical_precision_claim':False}}


def run(args):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopoDS import TopoDS_Shape,TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE
    import OCP
    started=time.monotonic()
    if not 1<=args.max_face_triangles<=2000 or not 0<=args.triangle_sample_count<=128:
        raise ValueError('maximum_2000_face_triangles_and_128_selected_triangles_required')
    if args.output.exists() or args.output.is_symlink():raise FileExistsError(args.output)
    # /private-work is the explicit private bind mount of the bounded container.
    if not any(args.output.resolve().is_relative_to(p) for p in (PRIVATE_ROOT,Path('/private-work'))):
        raise ValueError('private_output_directory_required')
    paths={'domain':args.domain,'boundary_report':args.boundary_report,
        'mesh_report':args.surface_dir/'mesh-report.json','connectivity':args.surface_dir/'surface-connectivity-private.json',
        'mesh':args.surface_dir/'intake-gas-surface-only.msh','source':Path(__file__)}
    hashes={k:sha(p) for k,p in paths.items()};manifest=json.loads(paths['boundary_report'].read_text())
    mesh_report=json.loads(paths['mesh_report'].read_text());snapshot=json.loads(paths['connectivity'].read_text())
    if (hashes['domain']!=manifest['exports']['domain_brep']['sha256'] or
            hashes['domain']!=mesh_report['native_BRep_sha256'] or
            hashes['boundary_report']!=mesh_report['gas_domain_report_sha256'] or
            hashes['mesh']!=mesh_report['persisted_surface']['MSH_sha256'] or
            hashes['connectivity']!=mesh_report['persisted_surface']['connectivity_sha256']):
        raise ValueError('native_and_persisted_surface_provenance_mismatch')
    points,elements=read_msh22(paths['mesh'])
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(paths['domain']),BRep_Builder()):raise ValueError('native_read_failed')
    indexed=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,TopAbs_FACE,indexed)
    if indexed.Extent()!=len(manifest['boundary_faces']):raise ValueError('native_face_count_mismatch')
    args.output.mkdir(parents=True,mode=0o700)
    report={'schema':'m64-sampled-surface-CAD-audit/v2','status':'running','inputs_sha256':hashes,
        'OCP_version':OCP.__version__,'coordinate_units':mesh_report['coordinate_units'],
        'geometry_modified':False,'mesh_modified':False,'acceptance_thresholds_modified':False,
        'mesh_accepted':False,'manufacturing_authorized':False,'global_Hausdorff_or_self_intersection_proven':False,
        'sampling':('native border probes only' if args.intrinsic_only else
            'vertices, barycentre and three edge midpoints of selected triangles; all triangle areas'),
        'triangle_selection':{'maximum_face_triangles':args.max_face_triangles,
            'requested_sample_count_zero_means_all':args.triangle_sample_count,
            'method':'evenly_spaced_indices_in_persisted_element_order_not_worst_case'},
        'normal_binding':'same_BRepExtrema_closest_support_via_native_UV_or_pcurve',
        'native_tolerances_modified':False,
        'faces':[]}
    def save(name):
        report['elapsed_seconds']=time.monotonic()-started
        with (args.output/(name+'.json')).open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False)
        (args.output/(name+'.json')).chmod(0o600)
    save('preregistration')
    try:
        for face_id in args.face_id:
            match=[r for r in snapshot['faces_private'] if r['source_face_id']==face_id]
            if len(match)!=1:raise ValueError('unique_snapshot_face_required')
            stored=match[0];triangles=stored['triangles'];tags=stored['triangle_tags']
            if not triangles or len(triangles)!=len(tags) or len(triangles)>args.max_face_triangles:
                raise ValueError('bounded_nonempty_face_triangle_count_required')
            for tag,nodes in zip(tags,triangles):
                e=elements.get(tag,{})
                if e.get('face_tag')!=stored['gmsh_face_tag'] or e.get('nodes')!=tuple(nodes):
                    raise ValueError('MSH_snapshot_triangle_or_face_mismatch')
            face=TopoDS.Face_s(indexed.FindKey(face_id));audit=FaceAudit(face)
            if args.intrinsic_only:
                row={'face_id':face_id,'role':manifest['boundary_faces'][face_id-1]['role'],
                    'intrinsic_border_diagnostic':sampled_border_resolution(face),
                    'summary':{'triangles_audited':0,'intrinsic_border_only':True}}
                report['faces'].append(row);save('face-%04d-intrinsic-checkpoint'%face_id)
                continue
            props=GProp_GProps();BRepGProp.SurfaceProperties_s(face,props)
            selected=sample_indices(len(triangles),args.triangle_sample_count)
            geometry=[triangle_geometry([points[n] for n in tri]) for tri in triangles]
            nodes=sorted({n for i in selected for n in triangles[i]});node_rows={n:audit.point(points[n]) for n in nodes}
            row={'face_id':face_id,'role':manifest['boundary_faces'][face_id-1]['role'],
                'BRep_valid':BRepCheck_Analyzer(face,True,False,True).IsValid(),
                'CAD_area':props.Mass(),'CAD_tolerance':audit.tolerance,'UV_bounds_private':list(audit.bounds),
                'U_periodic':audit.surface.IsUPeriodic(),'V_periodic':audit.surface.IsVPeriodic(),
                'U_closed':audit.surface.IsUClosed(),'V_closed':audit.surface.IsVClosed(),
                'nodes_private':node_rows,'selected_triangle_indices':selected,'triangles_private':[]}
            own_edges=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(face,TopAbs_EDGE,own_edges)
            row['adjacent_CAD_faces']=[]
            for i in range(1,indexed.Extent()+1):
                if i==face_id:continue
                other=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(indexed.FindKey(i),TopAbs_EDGE,other)
                if any(other.Contains(own_edges.FindKey(j)) for j in range(1,own_edges.Extent()+1)):
                    row['adjacent_CAD_faces'].append({'face_id':i,'role':manifest['boundary_faces'][i-1]['role']})
            for i in selected:
                tag,tri=tags[i],triangles[i]
                measurement=audit.triangle([points[n] for n in tri],[node_rows[n] for n in tri])
                measurement.update(triangle_tag=tag,ordered_nodes=tri);row['triangles_private'].append(measurement)
            samples=[p for t in row['triangles_private'] for p in t.get('samples',[])]
            normal_dots=[p['triangle_dot_CAD_normal'] for p in samples if p['triangle_dot_CAD_normal'] is not None]
            row['summary']={'triangles':len(triangles),'nodes':len({n for t in triangles for n in t}),
                'triangles_CAD_sampled':len(selected),'nodes_CAD_sampled':len(nodes),
                'all_triangles_CAD_sampled':len(selected)==len(triangles),
                'zero_area_triangles':sum(t['degenerate'] for t in geometry),
                'triangle_area_sum':math.fsum(t['area'] for t in geometry),
                'node_trimmed_distance_max':max(r['trimmed_face_distance_numeric'] for r in node_rows.values()),
                'sample_trimmed_distance_max':max((r['trimmed_face_distance_numeric'] for r in samples),default=None),
                'samples_without_inside_trim_projection':sum(not r['valid_trim_projection'] for r in samples),
                'sample_CAD_normal_missing':sum(r['normal_private'] is None for r in samples),
                'sample_normal_dot_min':min(normal_dots,default=None),
                'sample_normal_dot_max':max(normal_dots,default=None),
                'samples_with_negative_normal_dot':sum(x<0 for x in normal_dots),
                'nodes_without_inside_trim_projection':sum(not r['valid_trim_projection'] for r in node_rows.values()),
                'UV_signed_area_unavailable_triangles':sum('UV_signed_double_area' not in t for t in row['triangles_private']),
                'UV_signed_area_negative_triangles':sum(t.get('UV_signed_double_area',0)<0 for t in row['triangles_private']),
                'parametric_cross_sine_min':min((p['surface_parametric_cross_sine'] for p in samples if p['valid_trim_projection']),default=None)}
            row['summary']['relative_triangle_area_difference']=row['summary']['triangle_area_sum']/row['CAD_area']-1.
            report['faces'].append(row);save('face-%04d-checkpoint'%face_id)
        report['status']='sampled_local_CAD_diagnostics_complete_not_mesh_acceptance'
    except Exception as exc:report['status']='partial_diagnostic';report['error']=type(exc).__name__+': '+str(exc)
    report['all_inputs_unchanged']=all(sha(p)==hashes[k] for k,p in paths.items())
    report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    save('report')
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],'error':report.get('error'),
        'summaries':[r['summary'] for r in report['faces']]}))
    return 0 if report['status']=='sampled_local_CAD_diagnostics_complete_not_mesh_acceptance' else 3


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('domain','boundary-report','surface-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--face-id',type=int,action='append',required=True)
    parser.add_argument('--intrinsic-only',action='store_true')
    parser.add_argument('--max-face-triangles',type=int,default=500)
    parser.add_argument('--triangle-sample-count',type=int,default=0)
    resource.setrlimit(resource.RLIMIT_CPU,(50,55))
    raise SystemExit(run(parser.parse_args()))
