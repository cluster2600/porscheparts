"""Build and independently read native transition facets with node-specific arithmetic guards."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'),'sha256').hexdigest()


def module(path,name,expected):
    assert sha(path)==expected
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def native_readback(path,points,triangles,fragment_ids,source_mask,verifier):
    from OCP.TopAbs import TopAbs_VERTEX,TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt
    from scipy.spatial import cKDTree
    shape = verifier.load(path);vm = verifier.indexed(shape,TopAbs_VERTEX)
    expected_ids = np.unique(triangles)
    assert len(np.unique(points[expected_ids],axis=0))==len(expected_ids)
    actual = np.array([[BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(i))).Coord(j) for j in (1,2,3)]
                       for i in range(1,vm.Extent()+1)])
    distances,nearest = cKDTree(points[expected_ids]).query(actual)
    mapped = expected_ids[nearest]
    original = source_mask[mapped]
    assert np.all(distances[original]==0),'Acquired original vertex moved'
    assert np.all(distances[~original]<=1e-8),'Constructed source-edge endpoint moved beyond arithmetic guard'
    # The frozen reader independently checks triangle coverage, winding, edges,
    # vertex fans and shell components against the bound fragment connectivity.
    topology = verifier.inspect_source(path,points,triangles,fragment_ids)
    maximum = 0.;fm = verifier.indexed(shape,TopAbs_FACE)
    for i in range(1,fm.Extent()+1):
        face = TopoDS.Face_s(fm.FindKey(i));surface = BRepAdaptor_Surface(face,True).Plane()
        local = verifier.indexed(face,TopAbs_VERTEX);assert local.Extent()==3
        for j in range(1,4):
            index = vm.FindIndex(local.FindKey(j));assert index>0
            maximum = max(maximum,surface.Distance(gp_Pnt(*actual[index-1])),
                          surface.Distance(gp_Pnt(*points[mapped[index-1]])))
    assert maximum<=1e-8,'Actual native support plane exceeds arithmetic guard'
    return dict(native_vertices=vm.Extent(),edges=topology['edges'],faces=topology['faces'],
                shells=topology['shells'],boundary_edges=topology['source_boundary_edges'],
                original_vertex_roundtrip_maximum_nominal_mm=float(distances[original].max()) if original.any() else 0.,
                constructed_endpoint_roundtrip_maximum_nominal_mm=float(distances[~original].max()) if (~original).any() else 0.,
                maximum_actual_native_support_plane_residual_nominal_mm=maximum,
                all_expected_fragments_once=True,original_winding=True,straight_edges=True,
                exact_fragment_edge_adjacency=True,exact_vertex_fans_and_shell_components=True,
                valid=True,zero_solids=True)


def export(builder,points,faces,path):
    used,inverse = np.unique(faces,return_inverse=True)
    v,f,mapping,groups,counts = builder.atlas(points[used],inverse.reshape(-1,3))
    assert np.array_equal(used[mapping[f]],faces)
    builder.export(builder.native_shape(v,f,groups),path)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--built',type=Path);parser.add_argument('--mode',choices=('build','check'),required=True)
    parser.add_argument('--controls-only',action='store_true')
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-transition-native-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    verifier = module(job['verifier'],'frozen_fragment_topology_reader','3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658')
    points = np.array([[0.,0.,-1.],[2.,0.,2.],[0.,2.,2.],[2/3,0.,0.],[0.,2/3,0.]])
    faces = np.array([[0,3,4],[3,1,2],[3,2,4]])
    mask = np.array([True,True,True,False,False])
    if args.mode=='build':
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound
        builder = module(job['builder'],'frozen_source_fragment_builder','fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e')
        export(builder,points,faces,args.output/'positive-control.step')
        moved = points.copy();moved[0,0]+=1e-9
        export(builder,moved,faces,args.output/'moved-original-control.step')
        bad = TopoDS_Compound();bb = BRep_Builder();bb.MakeCompound(bad)
        for face in faces:
            v,f,mapping,groups,_ = builder.atlas(points[face],np.array([[0,1,2]]))
            bb.Add(bad,builder.native_shape(v,f,groups))
        builder.export(bad,args.output/'unsewn-control.step')
        control = dict(actual_positive_and_two_negative_native_controls_written=True)
    else:
        assert args.built is not None
        control = native_readback(args.built/'positive-control.step',points,faces,np.arange(3),mask,verifier)
        for name,expected in [('moved-original','Acquired original vertex moved'),
                              ('unsewn','Native source edge was duplicated or introduced')]:
            try:native_readback(args.built/(name+'-control.step'),points,faces,np.arange(3),mask,verifier)
            except (AssertionError,ValueError) as error:assert expected in str(error),str(error)
            else:raise AssertionError('Negative native control accepted: '+name)
        control.update(moved_acquired_vertex_below_constructed_guard_refused=True,unsewn_same_facets_refused=True)
    rows = []
    if not args.controls_only:
        proof = json.loads(Path(job['proof']).read_text())
        assert proof['source_sha256']=='06bc7701651dcaef4ee632783fe8d715ecd2110f214ef833a7352f84ce858f54'
        assert proof['fragments_sha256']==sha(job['fragments']) and proof['each_original_triangle_exactly_tiled_by_two_opposite_halves']
        with np.load(job['fragments'],allow_pickle=False) as data:
            points,faces,mask = data['points'],data['triangles'],data['source_vertex_ids']>=0
            regions,sides = data['triangle_regions'],data['triangle_halfspaces']
        for region in range(1,6):
            for side,name in [(-1,'inside'),(1,'outside')]:
                ids = np.flatnonzero((regions==region)&(sides==side));filename='region-'+str(region)+'-'+name+'.step'
                if args.mode=='build':
                    path = args.output/filename;counts = export(builder,points,faces[ids],path)
                    row = dict(region=region,halfspace=side,derived_triangles=len(ids),topology=counts,step_sha256=sha(path))
                else:
                    path = args.built/filename;before = sha(path)
                    comparison = native_readback(path,points,faces[ids],ids,mask,verifier)
                    assert sha(path)==before
                    row = dict(region=region,halfspace=side,derived_triangles=len(ids),comparison=comparison,step_sha256=before)
                rows.append(row)
                print(json.dumps(dict(region=region,halfspace=side,mode=args.mode)),flush=True)
        assert len(rows)==10 and sum(row['derived_triangles'] for row in rows)==2178
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mode=args.mode,controls_only=args.controls_only,
                  controls=control,regions=rows,original_vertex_guard_nominal_mm=0,constructed_endpoint_arithmetic_guard_nominal_mm=1e-8,
                  caps_or_hidden_surfaces_added=False,full_bare_head_created=False,physical_acceptance=False,
                  manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
