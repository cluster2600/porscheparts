"""Independently read the complete VTP transport and bind canonical array hashes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOXML import vtkXMLPolyDataReader


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--indexed', type=Path, required=True)
    parser.add_argument('--transport', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path')
    report = json.loads((args.indexed/'report.json').read_text())
    if not report['reextracted_stl_byte_identical']:
        raise ValueError('Missing original native STL identity witness')
    vertices_path, faces_path = args.indexed/'vertices.f32', args.indexed/'triangles.i32'
    if (sha(vertices_path) != report['vertices_f32_sha256'] or
            sha(faces_path) != report['triangles_i32_sha256']):
        raise ValueError('Native source arrays changed')
    vertices = np.memmap(vertices_path, dtype='<f4', mode='r').reshape((-1, 3))
    triangles = np.memmap(faces_path, dtype='<i4', mode='r').reshape((-1, 3))
    transport_hash = sha(args.transport)
    reader = vtkXMLPolyDataReader()
    reader.SetFileName(str(args.transport))
    reader.Update()
    mesh = reader.GetOutput()
    read_vertices = np.asarray(vtk_to_numpy(mesh.GetPoints().GetData()), dtype='<f4')
    read_triangles = np.asarray(vtk_to_numpy(mesh.GetPolys().GetConnectivityArray()), dtype='<i4').reshape((-1, 3))
    same_vertices, same_triangles = np.array_equal(vertices, read_vertices), np.array_equal(triangles, read_triangles)
    if not same_vertices or not same_triangles:
        raise ValueError('Native vertices or triangular indices/order changed in transport')
    digest = lambda a: hashlib.sha256(memoryview(a).cast('B')).hexdigest()
    vp, fp = digest(read_vertices), digest(read_triangles)
    if vp != report['vertices_f32_sha256'] or fp != report['triangles_i32_sha256']:
        raise ValueError('Transport canonical array bytes differ')
    if sha(args.transport) != transport_hash:
        raise ValueError('Transport changed during verification')
    result = {'kind': 'lossless_native_transport_equality',
              'native_stl_sha256': report['source_stl_sha256'],
              'replayed_stl_sha256': report['reextracted_stl_sha256'],
              'transport_sha256': transport_hash, 'point_count': len(vertices),
              'triangle_count': len(triangles), 'vertices_equal': same_vertices,
              'triangles_equal': same_triangles,
              'source_vertices_sha256': report['vertices_f32_sha256'], 'readback_vertices_sha256': vp,
              'source_triangles_sha256': report['triangles_i32_sha256'], 'readback_triangles_sha256': fp,
              'hash_encoding': 'Little-endian float32 XYZ; little-endian int32 ordered triangular indices',
              'verifier_sha256': sha(__file__), 'indexed_receipt_sha256': sha(args.indexed/'report.json'),
              'structural_or_physical_validation': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
