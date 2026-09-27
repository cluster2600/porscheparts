#!/usr/bin/env python3
"""Private text-BRep conversion and unsmoothed native surface tessellation.

The text conversion is checked for validity/counts, not global serialization
equivalence. The per-face surface mesh retains duplicate boundary vertices.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import time

from render_v5_v2 import save, sha


def expected_digest(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('lowercase_sha256_required')
    return value


def mesh_limits(points, triangles, lowest, highest, finite):
    return (type(points) is int and type(triangles) is int and type(lowest) is int and type(highest) is int
            and 3 <= points <= 6000000 and 1 <= triangles <= 2000000
            and finite is True and 0 <= lowest <= highest < points)


def run(candidate, digest, output):
    import numpy as np
    import OCP
    from OCP.BinTools import BinTools
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_SHELL, TopAbs_REVERSED
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_FormatVersion_VERSION_3
    from OCP.TopLoc import TopLoc_Location
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('exact_OCP_required')
    expected_digest(digest)
    if candidate.is_symlink() or sha(candidate) != digest:
        raise ValueError('exact_native_input_required')
    started = time.monotonic(); source_hash = sha(__file__)
    def indexed(shape, kind):
        table = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(shape,kind,table)
        return [table.FindKey(i) for i in range(1,table.Extent()+1)]
    def inspect(shape):
        return {'exact_BRepCheck_valid':BRepCheck_Analyzer(shape,True,False,True).IsValid(),
                'solids':len(indexed(shape,TopAbs_SOLID)),'shells':len(indexed(shape,TopAbs_SHELL)),
                'faces':len(indexed(shape,TopAbs_FACE))}
    shape = TopoDS_Shape()
    if not BinTools.Read_s(shape,str(candidate)):
        raise ValueError('binary_input_read_failed')
    before = inspect(shape)
    if not before['exact_BRepCheck_valid'] or before['solids'] != 1 or before['shells'] != 1:
        raise ValueError('one_valid_native_body_required')
    os.umask(0o077); output.mkdir(parents=True,mode=0o700,exist_ok=False)
    target = output/'candidate.brep'
    if not BRepTools.Write_s(shape,str(target),False,False,TopTools_FormatVersion_VERSION_3):
        raise ValueError('text_BRep_write_failed')
    reread = TopoDS_Shape()
    if not BRepTools.Read_s(reread,str(target),BRep_Builder()):
        raise ValueError('text_BRep_readback_failed')
    after = inspect(reread)
    conversion = {'schema':'private-native-text-BRep-conversion/v1','source_sha256':source_hash,
                  'input_binary_sha256':digest,'text_BRep_sha256':sha(target),
                  'text_BRep_bytes':target.stat().st_size,'before':before,'after':after,
                  'OCP_version':OCP.__version__,'text_format':'VERSION_3_without_triangles_or_normals',
                  'healing':False,'transforms':False,'BOP_check_performed':False,
                  'global_serialization_geometry_equivalence_proven':False,
                  'conversion_before_tessellation':True,'input_unchanged':sha(candidate)==digest}
    save(output/'conversion.json',conversion)
    if after != before:
        raise ValueError('text_validity_or_topology_count_changed')
    job = BRepMesh_IncrementalMesh(shape,.18,False,.25,False)
    if not job.IsDone():
        raise ValueError('native_tessellation_not_done')
    points, triangles = [], []
    for raw in indexed(shape,TopAbs_FACE):
        face = TopoDS.Face_s(raw); location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face,location)
        if mesh is None or mesh.NbTriangles() == 0:
            raise ValueError('face_missing_native_triangles')
        offset = len(points)
        points.extend(mesh.Node(i).Transformed(location.Transformation()).Coord() for i in range(1,mesh.NbNodes()+1))
        for i in range(1,mesh.NbTriangles()+1):
            a,b,c = mesh.Triangle(i).Get()
            if face.Orientation() == TopAbs_REVERSED:
                b,c = c,b
            triangles.append([offset+a-1,offset+b-1,offset+c-1])
    xyz, tri = np.asarray(points,dtype=np.float64), np.asarray(triangles,dtype=np.int64)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or tri.ndim != 2 or tri.shape[1] != 3
            or not mesh_limits(len(xyz),len(tri),int(tri.min()),int(tri.max()),bool(np.isfinite(xyz).all()))):
        raise ValueError('mesh_array_shape_or_bounds_failed')
    target_mesh = output/'surface.npz'; np.savez_compressed(target_mesh,points=xyz,triangles=tri)
    if sha(candidate) != digest or sha(__file__) != source_hash:
        raise ValueError('input_or_source_changed')
    save(output/'surface.json',{'schema':'private-native-surface-npz/v1','source_sha256':source_hash,
         'input_binary_sha256':digest,'surface_sha256':sha(target_mesh),'surface_bytes':target_mesh.stat().st_size,
         'OCP_version':OCP.__version__,'numpy_version':np.__version__,'native_faces':before['faces'],
         'points':len(xyz),'triangles':len(tri),'points_dtype':str(xyz.dtype),'triangles_dtype':str(tri.dtype),
         'linear_deflection':.18,'relative_deflection':False,'angular_deflection_radians':.25,
         'parallel':False,'smoothing':False,'welding':False,'decimation':False,'repair':False,
         'watertight_analysis_mesh_claimed':False,'geometric_error_certified':False,
         'input_unchanged':True,'source_unchanged':True,'wall_seconds':time.monotonic()-started})
    print(json.dumps({'text_BRep_sha256':sha(target),'surface_sha256':sha(target_mesh)}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--sha256',type=expected_digest,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); signal.alarm(600)
    run(args.candidate,args.sha256,args.output)
