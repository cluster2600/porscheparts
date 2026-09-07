#!/usr/bin/env python3
"""Inventory every private tolerance after a STEP round trip, without CAD edits."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','candidate-step','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-sha256',required=True);p.add_argument('--candidate-sha256',required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    if sha(a.source_step)!=a.source_sha256 or sha(a.candidate_step)!=a.candidate_sha256:raise ValueError('geometry provenance mismatch')
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    inventories={};local=[]
    for label,path in [('source',a.source_step),('candidate',a.candidate_step)]:
        shape=read_step(path)[0];parts={};maps={}
        for kind,enum,cast in [('faces',TopAbs_FACE,TopoDS.Face_s),('edges',TopAbs_EDGE,TopoDS.Edge_s),('vertices',TopAbs_VERTEX,TopoDS.Vertex_s)]:
            items=indexed(shape,enum);maps[kind]=items
            rows=[{'index_private':i,'tolerance':BRep_Tool.Tolerance_s(cast(items.FindKey(i)))} for i in range(1,items.Extent()+1)]
            values=[row['tolerance'] for row in rows]
            parts[kind]={'count':len(rows),'minimum':min(values),'maximum':max(values),
                          'histogram_exact_float_hex':dict(sorted(Counter(v.hex() for v in values).items())),
                          'rows_private':rows}
        if label=='candidate':
            for i in range(1,maps['faces'].Extent()+1):
                face=TopoDS.Face_s(maps['faces'].FindKey(i));surface=BRep_Tool.Surface_s(face)
                if surface.DynamicType().Name()=='Geom_BSplineSurface' and (surface.UDegree(),surface.VDegree())==(10,11):
                    edges=indexed(face,TopAbs_EDGE)
                    local.append({'face_index_private':i,'face_tolerance':BRep_Tool.Tolerance_s(face),
                                  'edge_tolerances':[BRep_Tool.Tolerance_s(TopoDS.Edge_s(edges.FindKey(j))) for j in range(1,edges.Extent()+1)]})
        inventories[label]=parts
    equal={kind:inventories['source'][kind]['histogram_exact_float_hex']==inventories['candidate'][kind]['histogram_exact_float_hex'] for kind in inventories['source']}
    result={'schema':'m64-reference-complete-tolerance-invariance/v1','source_sha256':a.source_sha256,'candidate_sha256':a.candidate_sha256,
            'global_tolerance_distributions_equal':equal,'complete_inventories_private':inventories,
            'modified_degree_faces_private':local,'distribution_equality_not_individual_topology_identity':True,
            'master_hash_unchanged':sha(a.source_step)==a.source_sha256,'geometry_modified':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report_sha256':sha(a.output),'global_tolerance_distributions_equal':equal,
                      'modified_degree_faces_private':local,'master_hash_unchanged':result['master_hash_unchanged']},indent=2))


if __name__=='__main__':main()
