"""Read-only topology, analytic normals and terminations of the new root feet."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def boundary_normal(edge,face,parameter):
    """Evaluate the stored edge pcurve, without projecting onto a support."""
    import numpy as np
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve2d,BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_REVERSED
    from OCP.gp import gp_Pnt,gp_Vec
    assert BRep_Tool.SameParameter_s(edge.wrapped),'Unresolved edge/pcurve parameter identity'
    uv=BRepAdaptor_Curve2d(edge.wrapped,face.wrapped).Value(parameter)
    surface=BRepAdaptor_Surface(face.wrapped,True)
    point,du,dv=gp_Pnt(),gp_Vec(),gp_Vec()
    surface.D1(uv.X(),uv.Y(),point,du,dv)
    normal=np.cross(np.array(du.Coord()),np.array(dv.Coord()))
    length=np.linalg.norm(normal)
    assert math.isfinite(length) and length>0,'Degenerate support differential'
    normal/=length
    if face.wrapped.Orientation()==TopAbs_REVERSED:normal=-normal
    return normal,{'uv':[uv.X(),uv.Y()],'support_point_mm':list(point.Coord()),
        'support_uv_bounds':[surface.FirstUParameter(),surface.LastUParameter(),
                             surface.FirstVParameter(),surface.LastVParameter()]}


def check(folder,base_step,output,expected_step_sha256):
    import numpy as np
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import import_step,import_brep,Vector
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    folder,base_step,output=map(Path,(folder,base_step,output))
    assert not output.exists() and sha(folder/'carrier.step')==expected_step_sha256
    plan=json.loads((folder/'construction-plan.json').read_text())
    assert sha(base_step)==plan['base_STEP_sha256']
    geometry=json.loads((folder/'geometry.json').read_text())
    assert geometry['CAD_valid'] and geometry['solid_count']==1
    assert geometry['geometry_sha256']['carrier.step']==expected_step_sha256
    before,after=import_step(base_step),import_step(folder/'carrier.step')
    old_edges=list(before.edges());new_edges=list(after.edges());faces=list(after.faces())
    old_bounds=np.array([[list(e.bounding_box().min),list(e.bounding_box().max)] for e in old_edges])
    old_tolerance=max(BRep_Tool.Tolerance_s(edge.wrapped) for edge in old_edges)
    footprints=[]
    for path in sorted(folder.glob('foot-window-trimmed-X*.brep')):
        foot=import_brep(path);box=foot.bounding_box()
        footprints.append({'label':path.name,'sha256':sha(path),'bounds_mm':[list(box.min),list(box.max)]})
    assert len(footprints)==2
    def query(point,shape):
        result=BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Shape(),shape.wrapped)
        result.Perform();assert result.IsDone();return result
    def old_edge_distance(point):
        bound=np.linalg.norm(np.maximum(np.maximum(old_bounds[:,0]-point,0),point-old_bounds[:,1]),axis=1)
        best=math.inf
        for index in np.argsort(bound):
            if bound[index]>best:break
            best=min(best,query(point,old_edges[index]).Value())
        return best
    def overlaps(a,b):
        return all(x<=w and z<=y for x,y,z,w in zip(a[0],a[1],b[0],b[1]))
    critical=[]
    for rule in plan['selected_edges']:
        point=np.array(rule['selection_probe_mm']);distance=query(point,after.shells()[0]).Value()
        critical.append({'mirror_X':rule['mirror_X'],'original_edge_index':rule['edge_index_zero_based'],
            'original_critical_edge_point_mm':point.tolist(),'distance_to_new_shell_mm':distance,
            'inside_material':after.solids()[0].is_inside(Vector(*point)),
            'buried_beyond_native_edge_tolerance':distance>old_tolerance})
    records=[]
    for index,edge in enumerate(new_edges):
        box=edge.bounding_box();bounds=[list(box.min),list(box.max)]
        if not any(overlaps(bounds,row['bounds_mm']) for row in footprints):continue
        middle=np.array(tuple(edge.position_at(.5)));distance=old_edge_distance(middle)
        native_tolerance=max(old_tolerance,BRep_Tool.Tolerance_s(edge.wrapped))
        if distance<=native_tolerance:continue
        adjacent=[i for i,face in enumerate(faces) if any(edge.wrapped.IsSame(item.wrapped) for item in face.edges())]
        row={'edge_index_zero_based':index,'length_mm':edge.length,'bounds_mm':bounds,
            'midpoint_distance_to_original_edges_mm':distance,'native_edge_tolerance_mm':native_tolerance,
            'adjacent_faces_zero_based':adjacent,
            'adjacent_surface_types':[str(BRepAdaptor_Surface(faces[i].wrapped,True).GetType()) for i in adjacent],
            'normal_probes':[]}
        if len(adjacent)==2:
            for fraction in (.25,.5,.75):
                point=np.array(tuple(edge.position_at(fraction)))
                parameter=query(point,edge).ParOnEdgeS2(1)[0]
                evaluated=[boundary_normal(edge,faces[i],parameter) for i in adjacent]
                normals=[item[0] for item in evaluated]
                supports=[item[1] for item in evaluated]
                for support in supports:
                    support['edge_point_error_mm']=float(np.linalg.norm(np.array(support['support_point_mm'])-point))
                angle=math.degrees(math.atan2(np.linalg.norm(np.cross(*normals)),float(normals[0]@normals[1])))
                probe={'arc_length_fraction':fraction,'point_mm':point.tolist(),'normal_angle_degrees':angle,
                    'normals':[n.tolist() for n in normals],'edge_parameter':parameter,'pcurve_supports':supports}
                if any(s['edge_point_error_mm']>native_tolerance for s in supports):
                    probe['character']='inconclusive'
                elif angle>plan['support_G1_normal_angle_degrees_max']:
                    difference=normals[0]-normals[1];difference/=np.linalg.norm(difference)
                    inside=[after.solids()[0].is_inside(Vector(*(point+sign*.01*difference))) for sign in (-1,1)]
                    probe['material_sides_at_0p01mm']=inside
                    probe['character']='reentrant' if all(inside) else ('convex' if not any(inside) else 'inconclusive')
                else:probe['character']='tangent_within_frozen_plan_probe_tolerance'
                row['normal_probes'].append(probe)
            row['maximum_normal_angle_degrees']=max(p['normal_angle_degrees'] for p in row['normal_probes'])
        else:row['topology_unresolved']=True
        records.append(row)
    failures=[row['edge_index_zero_based'] for row in records if len(row['adjacent_faces_zero_based'])!=2 or
              any(p['character'] in ('reentrant','inconclusive') for p in row['normal_probes'])]
    report={'source_sha256':sha(__file__),'STEP_sha256':expected_step_sha256,'base_STEP_sha256':sha(base_step),
        'construction_plan_sha256':sha(folder/'construction-plan.json'),'geometry_record_sha256':sha(folder/'geometry.json'),
        'footprints':footprints,'original_critical_edges':critical,'new_boundary_edges_in_footprints':records,
        'frozen_support_G1_probe_tolerance_degrees':plan['support_G1_normal_angle_degrees_max'],
        'new_reentrant_or_unresolved_edge_indices':failures,
        'new_reentrant_seam_probe_screen_pass':not failures and all(r['inside_material'] and r['buried_beyond_native_edge_tolerance'] for r in critical),
        'normal_evaluation':'Stored SameParameter edge pcurves and oriented support D1 derivatives; no nearest-point projection of a boundary normal.',
        'scope':'Finite analytic-normal probes at three fixed arclength fractions of each geometrically new edge in the foot bounds; unchanged edges excluded using native topology tolerances. Convex window cuts are reported separately. This is not an all-parameter G1 proof or an FE admission certificate.'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','base_step','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--expected-step-sha256',required=True)
    args=parser.parse_args();check(args.folder,args.base_step,args.output,args.expected_step_sha256)
