"""Measure actual root-face section facets and reference C3D10 Gauss locations."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
from mesh_local_root import sha


def section_segments(triangles,plane_x):
    """Intersect straight boundary facets with a fixed plane, with no snap."""
    import numpy as np
    result=[];coplanar=0
    for triangle in triangles:
        signed=triangle[:,0]-plane_x
        if np.all(signed==0):coplanar+=1;continue
        points=[]
        for a,b,da,db in zip(triangle,np.roll(triangle,-1,axis=0),signed,np.roll(signed,-1)):
            if da==0:points.append(tuple(a))
            if da*db<0:points.append(tuple(a+da/(da-db)*(b-a)))
        points=list(dict.fromkeys(points))
        if len(points)==2 and points[0]!=points[1]:result.append(points)
        elif len(points)>2:raise ValueError('Unresolved triangle-plane intersection')
    return np.asarray(result,dtype=float).reshape(-1,2,3),coplanar


def audit(folder,mesh_folder,output):
    import numpy as np
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import import_step,Compound
    from OCP.BRep import BRep_Tool
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt,gp_Dir,gp_Pln
    folder,mesh_folder,output=map(Path,(folder,mesh_folder,output));assert not output.exists()
    receipt=json.loads((mesh_folder/'surface-capture-receipt.json').read_text())
    mesh_metadata=json.loads((mesh_folder/'mesh.json').read_text())
    assert mesh_metadata['straight_midsides'] and mesh_metadata['element_order']==2,'This section audit requires straight affine C3D10 facets'
    assert receipt['STEP_sha256']==sha(folder/'carrier.step')
    for key,name in [('mesh_inp_sha256','mesh.inp'),('surface_entities_npz_sha256','surface-entities.npz'),
                     ('surface_entities_json_sha256','surface-entities.json')]:assert receipt[key]==sha(mesh_folder/name)
    reader=SOURCE.parent/'revalidation-20261016/audit_energy.py'
    module_spec=importlib.util.spec_from_file_location('frozen_root_mesh_reader',reader)
    energy=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(energy)
    tags,xyz,element_ids,connectivity=energy.read_mesh(mesh_folder/'mesh.inp')
    with np.load(mesh_folder/'mesh.npz',allow_pickle=False) as mesh,np.load(mesh_folder/'surface-entities.npz',allow_pickle=False) as captured:
        assert np.array_equal(tags,mesh['tags']) and np.allclose(xyz,mesh['xyz'],rtol=0,atol=1e-10)
        facets=captured['faces'];entity_tags=captured['entity_tags']
        canonical=lambda a:sorted(map(tuple,np.sort(a,axis=1)))
        assert canonical(facets)==canonical(mesh['faces']),'Captured surface facets differ from retained boundary'
    body=import_step(folder/'carrier.step');faces=list(body.faces())
    metadata=json.loads((mesh_folder/'surface-entities.json').read_text());reports=[]
    def query(point,shape):
        q=BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Shape(),shape.wrapped)
        q.Perform();assert q.IsDone();return q
    a=(5+3*math.sqrt(5))/20;b=(5-math.sqrt(5))/20
    barycentric=np.full((4,4),b);np.fill_diagonal(barycentric,a)
    gauss=np.einsum('gi,eij->egj',barycentric,xyz[connectivity[:,:4]])
    for selected in metadata['sections']:
        point=np.array(selected['point_on_blend_face_mm']);matches=[]
        for index,face in enumerate(faces):
            tolerance=BRep_Tool.Tolerance_s(face.wrapped)
            if query(point,face).Value()<=tolerance:matches.append(index)
        assert len(matches)==1,('Interior CAD blend probe must match exactly one STEP face',matches)
        face=faces[matches[0]];section=BRepAlgoAPI_Section(face.wrapped,gp_Pln(gp_Pnt(selected['plane_X_mm'],0,0),gp_Dir(1,0,0)))
        section.Build();assert section.IsDone();section_shape=Compound.cast(section.Shape())
        section_edges=list(section_shape.edges());assert len(section_edges)==1,'Section has multiple/disconnected curves; do not infer an arc subdivision count'
        edge=section_edges[0];local_faces=facets[entity_tags==selected['entity_tag']]
        ids=np.searchsorted(tags,local_faces)
        assert np.all(ids<len(tags)) and np.array_equal(tags[ids],local_faces)
        triangles=xyz[ids];segments,coplanar=section_segments(triangles,selected['plane_X_mm'])
        assert len(segments) and not coplanar,'Section is empty or coincides with boundary triangles'
        chords=np.linalg.norm(segments[:,1]-segments[:,0],axis=1)
        midpoint_errors=[query((start+end)/2,edge).Value() for start,end in segments]
        crossing=(triangles[:,:,0].min(axis=1)<=selected['plane_X_mm'])&(triangles[:,:,0].max(axis=1)>=selected['plane_X_mm'])
        corner_edges=np.concatenate([triangles[crossing][:,[0,1]],triangles[crossing][:,[1,2]],triangles[crossing][:,[2,0]]])
        lengths=np.linalg.norm(corner_edges[:,1]-corner_edges[:,0],axis=1)
        reference=np.array(selected['reference_IP_xyz_mm']);distances=np.linalg.norm(gauss-reference,axis=2)
        element,ip=np.unravel_index(np.argmin(distances),distances.shape);gp=gauss[element,ip]
        radius=selected['reference_section_radius_mm'];assert math.isfinite(radius) and radius>0
        box=face.bounding_box()
        reports.append({**selected,'STEP_face_index_zero_based':matches[0],
            'STEP_face_bounds_mm':[list(box.min),list(box.max)],'exact_CAD_section_length_mm':edge.length,
            'boundary_facet_section_segments':len(segments),'section_polyline_length_mm':float(chords.sum()),
            'section_chord_min_median_max_mm':[float(np.min(chords)),float(np.median(chords)),float(np.max(chords))],
            'maximum_sampled_chord_midpoint_distance_to_CAD_section_mm':max(midpoint_errors),
            'section_corner_edge_min_median_max_mm':[float(np.min(lengths)),float(np.median(lengths)),float(np.max(lengths))],
            'section_maximum_chord_over_declared_radius':float(chords.max()/radius),
            'measured_reference_h_mm':float(chords.max()),
            'measured_h_definition':'Maximum actual boundary-facet chord on the fixed-X blend section; the local halving targets this length, not the global mesh label.',
            'nearest_Gauss_to_reference_IP':{'element_id':int(element_ids[element]),'IP':int(ip+1),'xyz_mm':gp.tolist(),
                'distance_to_reference_IP_mm':float(distances[element,ip]),'distance_to_blend_face_mm':query(gp,face).Value()},
            'C3D10_Gauss_order':'IP1=(a,b,b,b),IP2=(b,a,b,b),IP3=(b,b,a,b),IP4=(b,b,b,a),a=(5+3sqrt(5))/20,b=(5-sqrt(5))/20'})
    report={'source_sha256':sha(__file__),'frozen_mesh_reader_sha256':sha(reader),'STEP_sha256':sha(folder/'carrier.step'),
            'surface_capture_receipt_sha256':sha(mesh_folder/'surface-capture-receipt.json'),
            'mesh_inp_sha256':sha(mesh_folder/'mesh.inp'),'mesh_npz_sha256':sha(mesh_folder/'mesh.npz'),
            'mesh_metadata':mesh_metadata,'sections':reports,
            'scope':'Actual generating CAD entity identities, fixed-X facet cuts, finite chord-midpoint distances and nearest Gauss point to the frozen reference hotspot. Not a global Hausdorff bound or a peak-convergence assertion.',
            'geometry_or_loads_modified':False}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','mesh_folder','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();audit(args.folder,args.mesh_folder,args.output)
