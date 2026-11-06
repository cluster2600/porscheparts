"""Measure actual saved half-patch registration against each other and prior source sections."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'),'sha256').hexdigest()


def positions(shape,indexed):
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    vertices = indexed(shape,TopAbs_VERTEX)
    return np.array([[BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))).Coord(j) for j in (1,2,3)]
                     for i in range(1,vertices.Extent()+1)])


def main():
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    from scipy.spatial import cKDTree
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-transition-native-registration-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    assert sha(job['verifier'])=='3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658'
    spec = importlib.util.spec_from_file_location('saved_shape_reader',job['verifier'])
    verifier = importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    with np.load(job['fragments'],allow_pickle=False) as data:
        points,faces,source,planes,codes = [data[key] for key in ('points','triangles','source_vertex_ids','node_plane_indices','source_edge_codes')]
        regions,sides = data['triangle_regions'],data['triangle_halfspaces']
    report = json.loads(Path(job['saved_report']).read_text())
    assert len(report['regions'])==10 and all(row['comparison']['original_vertex_roundtrip_maximum_nominal_mm']==0 for row in report['regions'])
    assert all(row['comparison']['constructed_endpoint_roundtrip_maximum_nominal_mm']<=1e-8 for row in report['regions'])
    lookup = {(int(p),int(c)):i for i,(p,c,s) in enumerate(zip(planes,codes,source)) if s==-1}
    rows = [];private = {}
    for item in job['regions']:
        region = item['region']
        with np.load(item['source_region'],allow_pickle=False) as data:section_codes = data['section_edge_codes']
        cut = np.array([lookup[(item['plane'],int(code))] for code in section_codes])
        actual = {}
        for side,name in [(-1,'inside'),(1,'outside')]:
            path = Path(job['saved_exports'])/('region-'+str(region)+'-'+name+'.step')
            row = next(row for row in report['regions'] if row['region']==region and row['halfspace']==side)
            assert sha(path)==row['step_sha256']
            used = np.unique(faces[(regions==region)&(sides==side)])
            native = positions(verifier.load(path),verifier.indexed)
            distance,nearest = cKDTree(points[used]).query(native);mapped = used[nearest]
            assert np.all(distance<=1e-8)
            selected = {int(key):[] for key in cut}
            for key,p in zip(mapped,native):
                if int(key) in selected:selected[int(key)].append(p)
            assert all(len(value)==1 for value in selected.values()),'Native section node not unique'
            actual[name] = np.array([selected[int(key)][0] for key in cut])
        wire = TopoDS_Shape();assert BRepTools.Read_s(wire,item['source_section_brep'],BRep_Builder())
        native = positions(wire,verifier.indexed);assert len(native)==len(cut)
        distance,nearest = cKDTree(points[cut]).query(native)
        assert len(set(map(int,nearest)))==len(cut) and np.all(distance<=1e-8)
        actual['prior_section'] = np.empty_like(native);actual['prior_section'][nearest] = native
        comparisons = {}
        for a,b in [('inside','outside'),('inside','prior_section'),('outside','prior_section')]:
            maximum = float(np.linalg.norm(actual[a]-actual[b],axis=1).max())
            assert maximum<=1e-8,'Actual native interface registration exceeds unchanged arithmetic guard'
            comparisons[a+'_to_'+b+'_maximum_nominal_mm'] = maximum
        rows.append(dict(region=region,matched_source_section_nodes=len(cut),one_to_one_source_node_registration=True,
                         comparisons=comparisons,native_patches_remain_separate_unsewn_references=True))
        private['region_'+str(region)+'_fragment_node_ids'] = cut
        for name,array in actual.items():private['region_'+str(region)+'_'+name] = array
    assert sum(row['matched_source_section_nodes'] for row in rows)==726
    np.savez_compressed(args.output/'private-actual-native-registration.npz',**private)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),regions=rows,
                  all_726_actual_saved_section_nodes_registered=True,arithmetic_guard_nominal_mm=1e-8,
                  proximity_sewing_or_vertex_movement_performed=False,physical_tolerance_verified=False,
                  full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('ALL_726_ACTUAL_SAVED_NATIVE_SECTION_NODES_REGISTERED',flush=True)


if __name__=='__main__':main()
