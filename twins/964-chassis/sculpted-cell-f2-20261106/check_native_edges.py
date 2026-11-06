"""Count boundary and nonmanifold edges of the complete native surface.

This is an edge-incidence check, not a vertex-link, material-connectivity,
load-path or manufacturing qualification. No geometry is changed.
"""
from pathlib import Path
import argparse,hashlib,json,resource,time
from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from vtkmodules.vtkIOXML import vtkXMLPolyDataReader


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--transport',type=Path,required=True)
    p.add_argument('--transport-receipt',type=Path,required=True);p.add_argument('--native-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output file')
    started=time.monotonic();transport=json.loads(a.transport_receipt.read_text());native=json.loads(a.native_report.read_text())
    if sha(a.transport)!=transport['vtp_sha256'] or native['stl_sha256']!=transport['source_native_stl_sha256']:
        raise ValueError('Native field/surface transport provenance differs')
    reader=vtkXMLPolyDataReader();reader.SetFileName(str(a.transport));reader.Update();mesh=reader.GetOutput();counts={}
    for kind in ['boundary','nonmanifold']:
        check=vtkFeatureEdges();check.SetInputData(mesh);check.FeatureEdgesOff();check.ManifoldEdgesOff()
        check.SetBoundaryEdges(kind=='boundary');check.SetNonManifoldEdges(kind=='nonmanifold');check.Update()
        counts[kind+'_edges']=check.GetOutput().GetNumberOfCells();del check
    result={'status':'native_edge_incidence_check_passed' if not any(counts.values()) else 'native_edge_incidence_check_failed',
            'geometry_sha256':native['geometry_sha256'],'native_stl_sha256':native['stl_sha256'],
            'native_vdb_sha256':native['vdb_sha256'],'transport_sha256':transport['vtp_sha256'],
            'native_report_sha256':sha(a.native_report),'transport_receipt_sha256':sha(a.transport_receipt),
            'code_sha256':sha(__file__),'vertices':mesh.GetNumberOfPoints(),'triangles':mesh.GetNumberOfCells(),
            **counts,'elapsed_seconds':time.monotonic()-started,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'whole_native_surface_checked':True,'geometry_changed':False,'vertex_link_manifoldness_verified':False,
            'material_component_connectivity_verified':False,'complete_edge_structural_junctions_verified':False,
            'strength_verified':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
    if any(counts.values()):raise SystemExit(1)


if __name__=='__main__':main()
