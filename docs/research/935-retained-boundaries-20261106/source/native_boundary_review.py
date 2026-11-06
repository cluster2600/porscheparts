"""Represent every verified source boundary as an unqualified native review object."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def indexed(shape,kind):
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopExp import TopExp
    result = TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,kind,result);return result


def edge_compound(points):
    from OCP.BRep import BRep_Builder
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex,BRepBuilderAPI_MakeEdge
    from OCP.TopoDS import TopoDS_Compound
    from OCP.gp import gp_Pnt
    builder = BRep_Builder();shape = TopoDS_Compound();builder.MakeCompound(shape)
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        start = BRepBuilderAPI_MakeVertex(gp_Pnt(*a)).Vertex();end = BRepBuilderAPI_MakeVertex(gp_Pnt(*b)).Vertex()
        edge = BRepBuilderAPI_MakeEdge(start,end);assert edge.IsDone();builder.Add(shape,edge.Edge())
    return shape


def inspect(shape,points,original_mask,representation):
    from OCP.TopAbs import TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_SOLID
    from OCP.BRep import BRep_Tool
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepTools import BRepTools_WireExplorer
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp
    from OCP.GeomAbs import GeomAbs_Line
    from scipy.spatial import cKDTree
    assert BRepCheck_Analyzer(shape).IsValid()
    vm,em,wm = [indexed(shape,k) for k in (TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE)]
    assert indexed(shape,TopAbs_FACE).Extent()==indexed(shape,TopAbs_SOLID).Extent()==0
    unique,inverse = np.unique(points,axis=0,return_inverse=True)
    original = np.zeros(len(unique),dtype=bool)
    for i,flag in zip(inverse,original_mask):original[i] |= bool(flag)
    actual = np.array([[BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(i))).Coord(j) for j in (1,2,3)] for i in range(1,vm.Extent()+1)])
    distance,nearest = cKDTree(unique).query(actual)
    assert np.all(distance[original[nearest]]==0),'Original source boundary coordinate moved'
    assert np.all(distance[~original[nearest]]<=1e-8),'Constructed boundary coordinate exceeds arithmetic guard'
    assert em.Extent()==len(points)
    pairs = Counter()
    for i in range(1,em.Extent()+1):
        edge = TopoDS.Edge_s(em.FindKey(i));assert BRepAdaptor_Curve(edge).GetType()==GeomAbs_Line
        a,b = [vm.FindIndex(vertex) for vertex in (TopExp.FirstVertex_s(edge),TopExp.LastVertex_s(edge))]
        assert a>0 and b>0;pairs[(int(nearest[a-1]),int(nearest[b-1]))]+=1
    wanted = Counter((int(a),int(b)) for a,b in zip(inverse,np.roll(inverse,-1)))
    assert pairs==wanted,'Native directed source edge multiset changed'
    if representation=='wire':
        assert len(unique)==len(points)==vm.Extent() and wm.Extent()==1
        wire = TopoDS.Wire_s(wm.FindKey(1));assert wire.Closed()
        walker = BRepTools_WireExplorer(wire);order = []
        while walker.More():
            order.append(int(nearest[vm.FindIndex(walker.CurrentVertex())-1]));walker.Next()
        expected_next = {int(a):int(b) for a,b in zip(inverse,np.roll(inverse,-1))}
        assert len(order)==len(points) and all(expected_next[a]==b for a,b in zip(order,order[1:]+order[:1])),'Native wire source walk changed'
    else:
        assert representation=='independent_edges' and wm.Extent()==0 and vm.Extent()==2*len(points)
    return dict(vertices=vm.Extent(),edges=em.Extent(),wires=wm.Extent(),faces=0,solids=0,
                original_coordinate_maximum_error_nominal_mm=float(distance[original[nearest]].max()) if original[nearest].any() else 0.,
                constructed_coordinate_maximum_error_nominal_mm=float(distance[~original[nearest]].max()) if (~original[nearest]).any() else 0.,
                every_directed_source_segment_once=True,valid=True,representation=representation,
                source_contact_coordinates_not_welded=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--mode',choices=('build','check'),required=True);parser.add_argument('--built',type=Path)
    parser.add_argument('--controls-only',action='store_true')
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-native-boundary-review-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    assert sha(job['wire_helper'])=='1951da30faf0c0c06b200ceadf54d38069ef6e5bf794b169d34f966abdea42a9'
    spec = importlib.util.spec_from_file_location('frozen_wire_reference',job['wire_helper'])
    helper = importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    fixture = np.array([[0.,0.,0.],[1.,0.,0.],[4/3,1.,1/3],[0.,1.,0.]])
    mask = np.array([True,True,False,True]);contact = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,0.],[-1.,0.,0.],[0.,-1.,0.]])
    if args.mode=='build':
        helper.write_brep(helper.wire(fixture),args.output/'nonplanar-control.brep')
        helper.write_brep(helper.wire(fixture[::-1]),args.output/'reversed-control.brep')
        moved = fixture.copy();moved[0,0]+=1e-9
        helper.write_brep(helper.wire(moved),args.output/'moved-original-control.brep')
        helper.write_brep(edge_compound(contact),args.output/'self-contact-edge-control.brep')
        control = dict(actual_nonplanar_and_source_contact_native_controls_written=True)
    else:
        assert args.built is not None
        control = inspect(helper.read_brep(args.built/'nonplanar-control.brep'),fixture,mask,'wire')
        inspect(helper.read_brep(args.built/'self-contact-edge-control.brep'),contact,np.ones(len(contact),dtype=bool),'independent_edges')
        for name,wanted in [('reversed','Native directed source edge multiset changed'),('moved-original','Original source boundary coordinate moved')]:
            try:inspect(helper.read_brep(args.built/(name+'-control.brep')),fixture,mask,'wire')
            except AssertionError as error:assert wanted in str(error),str(error)
            else:raise AssertionError('Native negative source-boundary control accepted')
        control.update(nonplanar_source_wire_preserved_without_face=True,reversed_source_walk_refused=True,
                       moved_original_below_constructed_guard_refused=True,self_contact_kept_as_independent_edges=True)
    rows = []
    if not args.controls_only:
        proof = json.loads(Path(job['independent_proof']).read_text())
        assert proof['source_sha256']=='68c0d319a02417bb12a52135c4f38d979ab1814688ec47d9c53ab39dd0be4d94'
        assert proof['all_surface_vertex_fans_independently_rejoined'] and proof['all_oriented_cycles_cover_every_edge_once']
        data = load(job['boundary']);review = json.loads(Path(job['review']).read_text())
        source = load(job['arrays']);fragments = load(job['fragments']);new = np.flatnonzero(fragments['source_vertex_ids']==-1)
        points = np.r_[source['vertices'],fragments['points'][new]]
        for index,(a,b) in enumerate(zip(data['cycle_offsets'][:-1],data['cycle_offsets'][1:])):
            ids = data['cycle_boundary_edge_ids'][a:b];nodes = data['boundary_global_nodes'][ids,0];p = points[nodes]
            representation = 'independent_edges' if review[index]['repeated_coordinate_visits'] else 'wire'
            filename = 'curve-'+str(index).zfill(4)+'.brep'
            if args.mode=='build':
                path = args.output/filename;shape = helper.wire(p) if representation=='wire' else edge_compound(p)
                helper.write_brep(shape,path);row = dict(curve=index,edges=len(ids),representation=representation,brep_sha256=sha(path))
            else:
                path = args.built/filename;before = sha(path)
                comparison = inspect(helper.read_brep(path),p,nodes<len(source['vertices']),representation);assert sha(path)==before
                row = dict(curve=index,edges=len(ids),representation=representation,comparison=comparison,brep_sha256=before)
            rows.append(row)
        assert len(rows)==968 and sum(row['edges'] for row in rows)==98874
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mode=args.mode,controls_only=args.controls_only,controls=control,
                  curves=rows,closed_native_wires=sum(r['representation']=='wire' for r in rows),
                  self_contact_independent_edge_references=sum(r['representation']=='independent_edges' for r in rows),
                  source_faces_or_solids_created=False,physical_classifications_accepted=0,any_curve_filled=False,
                  full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(mode=args.mode,curves=len(rows))),flush=True)


if __name__=='__main__':main()
