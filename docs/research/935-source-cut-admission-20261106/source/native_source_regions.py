"""Native acquired-region references and source-supported construction curves.

Unclipped outward facets retain original coordinates. Section curves use BREP
as their native topology-preserving format; the provisional stock planes are
not physical mating datums. The actual exported geometry is separately read
against original acquisition coordinates and rational edge intersections.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
    return h.hexdigest()


def module(path,name,digest):
    assert sha(path)==digest
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value


def write_brep(shape,path):
    from OCP.BRepTools import BRepTools
    assert not path.exists();assert BRepTools.Write_s(shape,str(path))


def read_brep(path):
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    shape=TopoDS_Shape();assert BRepTools.Read_s(shape,str(path),BRep_Builder());return shape


def wire(points,order=None):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex,BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire
    from OCP.gp import gp_Pnt
    vertices=[BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float,p))).Vertex() for p in points]
    order=list(range(len(vertices))) if order is None else order;builder=BRepBuilderAPI_MakeWire()
    for a,b in zip(order,order[1:]+order[:1]):builder.Add(BRepBuilderAPI_MakeEdge(vertices[a],vertices[b]).Edge())
    assert builder.IsDone();return builder.Wire()


def inspect_wire(path,expected,indexed):
    from OCP.TopAbs import TopAbs_VERTEX,TopAbs_EDGE,TopAbs_FACE,TopAbs_SOLID,TopAbs_WIRE
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Line
    from OCP.BRepCheck import BRepCheck_Analyzer
    from scipy.spatial import cKDTree
    shape=read_brep(path);vm=indexed(shape,TopAbs_VERTEX);em=indexed(shape,TopAbs_EDGE);wm=indexed(shape,TopAbs_WIRE)
    assert vm.Extent()==em.Extent()==len(expected) and wm.Extent()==1
    assert indexed(shape,TopAbs_FACE).Extent()==indexed(shape,TopAbs_SOLID).Extent()==0
    actual=np.array([[BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(i))).Coord(j) for j in (1,2,3)] for i in range(1,vm.Extent()+1)])
    distance,match=cKDTree(expected).query(actual)
    assert float(distance.max())<=1e-8 and len(set(map(int,match)))==len(expected)
    pairs=set()
    for i in range(1,em.Extent()+1):
        edge=TopoDS.Edge_s(em.FindKey(i));assert BRepAdaptor_Curve(edge).GetType()==GeomAbs_Line
        vertices=indexed(edge,TopAbs_VERTEX);assert vertices.Extent()==2
        ids=[int(match[vm.FindIndex(vertices.FindKey(j))-1]) for j in (1,2)]
        pair=tuple(sorted(ids));assert pair not in pairs;pairs.add(pair)
    wanted={tuple(sorted((i,(i+1)%len(expected)))) for i in range(len(expected))}
    assert pairs==wanted,'Stored wire segments differ from expected source segments'
    assert BRepCheck_Analyzer(shape).IsValid() and TopoDS.Wire_s(wm.FindKey(1)).Closed()
    return dict(vertices=len(expected),edges=len(expected),wires=1,closed_degree_two_loop=True,straight_edges=True,
                maximum_constructed_endpoint_roundtrip_nominal_mm=float(distance.max()),valid=True,zero_faces_and_solids=True)


def expected_section(vertices,codes,plane):
    n=list(map(F.from_float,map(float,plane)));points=[];rounding=0.
    for code in codes:
        a,b=divmod(int(code),len(vertices));p=list(map(F.from_float,map(float,vertices[a])));q=list(map(F.from_float,map(float,vertices[b])))
        da=sum((p[j]*n[j] for j in range(3)),n[3]);db=sum((q[j]*n[j] for j in range(3)),n[3]);assert da*db<0
        exact=[(da*q[j]-db*p[j])/(da-db) for j in range(3)]
        assert sum((exact[j]*n[j] for j in range(3)),n[3])==0
        rounded=list(map(float,exact));error=math.sqrt(math.fsum(float(F.from_float(rounded[j])-exact[j])**2 for j in range(3)))
        rounding=max(rounding,error);points.append(rounded)
    assert rounding<=1e-8
    return np.array(points),rounding


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--built',type=Path);parser.add_argument('--mode',choices=('build','check'),required=True)
    parser.add_argument('--controls-only',action='store_true')
    args=parser.parse_args();spec=json.loads(args.job.read_text());args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert spec['schema']=='935-source-cut-native-1'
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    verifier=module(spec['verifier'],'original_source_reader','3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658')
    fixture=np.array([[0.,0.,0.],[2.1234567890123457,0.,0.],[2.1234567890123457,3.141592653589793,0.],[0.,3.141592653589793,0.]])
    if args.mode=='build':
        builder=module(spec['builder'],'original_source_builder','fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e')
        write_brep(wire(fixture),args.output/'positive-control.brep')
        write_brep(wire(fixture,[0,2,1,3]),args.output/'crossed-control.brep')
        control=dict(actual_native_control_files_emitted=True,source_comparison_not_yet_performed=True)
    else:
        assert args.built is not None
        control=inspect_wire(args.built/'positive-control.brep',fixture,verifier.indexed)
        try:inspect_wire(args.built/'crossed-control.brep',fixture,verifier.indexed)
        except AssertionError as error:assert 'Stored wire segments differ' in str(error)
        else:raise AssertionError('Crossed native wire accepted')
        control['crossed_same_vertex_count_wire_refused']=True
    if args.controls_only:
        report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mode=args.mode,
                    controls=control,controls_only=True,seconds=time.monotonic()-started)
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return
    with np.load(spec['arrays'],allow_pickle=False) as p:vertices,faces=p['vertices'],p['triangles']
    planes=json.loads(Path(spec['planes']).read_text());inspection=json.loads(Path(spec['independent_report']).read_text());rows=[]
    for row in inspection['regions']:
        index=row['region'];source_path=Path(spec['independent_report']).parent/('private-region-'+str(index)+'.npz')
        assert sha(source_path)==row['private_region_sha256']
        with np.load(source_path,allow_pickle=False) as p:
            ids=p['fully_outward_source_face_ids'];codes=p['section_edge_codes'];proposed_points=p['rounded_section_points']
        assert 0<len(ids)<=30000 and len(ids)==row['fully_outward_faces']
        plane=np.array(planes[row['plane']]['keep_negative_halfspace_coefficients']);expected,rounding=expected_section(vertices,codes,plane)
        assert np.array_equal(expected,proposed_points)
        prefix='region-'+str(index);step=args.output/(prefix+'.step');brep=args.output/(prefix+'-section.brep')
        if args.mode=='build':
            source_vertices,inverse=np.unique(faces[ids],return_inverse=True)
            v,f,mapping,groups,topology=builder.atlas(vertices[source_vertices],inverse.reshape(-1,3))
            assert np.array_equal(source_vertices[mapping[f]],faces[ids])
            builder.export(builder.native_shape(v,f,groups),step);write_brep(wire(proposed_points),brep)
            rows.append(dict(region=index,source_faces=len(ids),section_nodes=len(codes),step_sha256=sha(step),brep_sha256=sha(brep),
                             topology=topology,source_data_unchanged=True,independent_readback_required=True))
        else:
            step=args.built/(prefix+'.step');brep=args.built/(prefix+'-section.brep')
            before=(sha(step),sha(brep));native=verifier.inspect_source(step,vertices,faces[ids],ids)
            assert native['vertex_roundtrip_maximum_mm']==0.0
            curve=inspect_wire(brep,expected,verifier.indexed)
            assert before==(sha(step),sha(brep))
            rows.append(dict(region=index,source_faces=len(ids),source_native_comparison=native,section_native_comparison=curve,
                             ideal_to_rounded_endpoint_maximum_nominal_mm=rounding,step_sha256=sha(step),brep_sha256=sha(brep),
                             source_coordinates_and_edge_intersection_origin_verified=True))
        print(json.dumps(dict(region=index,mode=args.mode,source_faces=len(ids))),flush=True)
    assert len(rows)==5
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mode=args.mode,controls=control,regions=rows,
                wire_format='OCCT BREP; native topology is inspected rather than assumed from STEP wireframe containers',
                source_points_or_triangles_clipped_or_capped=False,physical_acceptance=False,manufacturing_authorized=False,
                full_bare_head_created=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
