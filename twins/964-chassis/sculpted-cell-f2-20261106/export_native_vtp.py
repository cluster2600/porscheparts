"""Losslessly serialise exact native indexed arrays for full-mesh viewing.

No reduction, point merging, offsets, normal calculation or geometric repair.
The original native field, STL and indexed arrays remain unchanged.
"""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import time
import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk,vtk_to_numpy
from vtkmodules.vtkCommonCore import vtkPoints,vtkVersion
from vtkmodules.vtkCommonDataModel import vtkCellArray,vtkPolyData
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter,vtkXMLPolyDataReader


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--indexed',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output directory')
    started=time.monotonic();receipt=json.loads((a.indexed/'report.json').read_text())
    if not receipt['reextracted_stl_byte_identical']:
        raise ValueError('Indexed native mesh lacks a byte-identical original STL witness')
    vp,tp=a.indexed/'vertices.f32',a.indexed/'triangles.i32'
    hashes={str(vp):sha(vp),str(tp):sha(tp)}
    if hashes[str(vp)]!=receipt['vertices_f32_sha256'] or hashes[str(tp)]!=receipt['triangles_i32_sha256']:
        raise ValueError('Original native buffers differ from their receipt')
    vertices=np.memmap(vp,dtype='<f4',mode='r').reshape((-1,3));triangles=np.memmap(tp,dtype='<i4',mode='r').reshape((-1,3))
    if len(vertices)!=receipt['vertex_count'] or len(triangles)!=receipt['triangle_count']:
        raise ValueError('Original native dimensions differ from their receipt')
    points=vtkPoints();points.SetData(numpy_to_vtk(vertices,deep=False));cells=vtkCellArray()
    if not cells.SetData(3,numpy_to_vtk(triangles.reshape(-1),deep=False)):
        raise ValueError('VTK rejected original int32 triangular indices')
    mesh=vtkPolyData();mesh.SetPoints(points);mesh.SetPolys(cells)
    a.output.mkdir(parents=True,mode=0o700);target=a.output/'native-cell.vtp'
    writer=vtkXMLPolyDataWriter();writer.SetFileName(str(target));writer.SetInputData(mesh)
    writer.SetDataModeToAppended();writer.EncodeAppendedDataOff();writer.SetCompressorTypeToZLib()
    if not writer.Write():raise ValueError('Full native VTP serialisation failed')
    reader=vtkXMLPolyDataReader();reader.SetFileName(str(target));reader.Update();restored=reader.GetOutput()
    restored_vertices=vtk_to_numpy(restored.GetPoints().GetData())
    restored_triangles=vtk_to_numpy(restored.GetPolys().GetConnectivityArray()).reshape((-1,3))
    if not np.array_equal(vertices,restored_vertices) or not np.array_equal(triangles,restored_triangles):
        raise ValueError('VTP readback changed original vertex coordinates or triangular index order')
    if any(sha(path)!=hashes[str(path)] for path in [vp,tp]):
        raise ValueError('Original native buffers changed during serialisation')
    report={'status':'full_native_VTP_lossless_readback_verified',
            'source_native_stl_sha256':receipt['source_stl_sha256'],
            'source_native_vdb_sha256':receipt['source_vdb_sha256'],
            'source_vertices_f32_sha256':hashes[str(vp)],'source_triangles_i32_sha256':hashes[str(tp)],
            'indexed_receipt_sha256':sha(a.indexed/'report.json'),'serialization_code_sha256':sha(__file__),
            'vtp_sha256':sha(target),'vtp_bytes':target.stat().st_size,
            'points':len(vertices),'triangles':len(triangles),'bounds_mm':list(mesh.GetBounds()),
            'whole_vertex_array_equal_after_readback':True,'whole_triangle_index_array_equal_after_readback':True,
            'vertex_and_triangle_order_retained':True,'points_merged':False,'geometry_reduced':False,
            'geometric_operation_performed':False,'vtk_version':vtkVersion.GetVTKVersion(),
            'elapsed_seconds':time.monotonic()-started,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'structural_or_manufacturing_qualification':False,'native_omniverse':False}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
