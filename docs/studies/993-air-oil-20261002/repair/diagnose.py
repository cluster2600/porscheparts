#!/usr/bin/env python3
"""Locate native kernel faults without modifying imported geometry."""
import argparse, hashlib, json, time
from pathlib import Path
import build123d as b
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box

MODES = ['SelfInterMode', 'SmallEdgeMode', 'RebuildFaceMode', 'ContinuityMode', 'CurveOnSurfaceMode']
ALL_MODES = ['ArgumentTypeMode', *MODES, 'TangentMode', 'MergeVertexMode', 'MergeEdgeMode']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def maps(s):
    out = {}
    for name, kind in [('face', TopAbs_FACE), ('edge', TopAbs_EDGE), ('vertex', TopAbs_VERTEX)]:
        m = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(s, kind, m); out[name] = m
    return out

def describe(raw, index):
    if raw.IsNull(): return {'null': True}
    row = {'kind': str(raw.ShapeType()), 'ids': {k:m.FindIndex(raw) for k,m in index.items()}}
    bb = Bnd_Box(); BRepBndLib.Add_s(raw,bb)
    row['bbox'] = list(bb.Get())
    if row['ids']['edge']:
        e = TopoDS.Edge_s(raw); c = BRepAdaptor_Curve(e)
        row.update(tolerance=BRep_Tool.Tolerance_s(e),same_parameter=BRep_Tool.SameParameter_s(e),
                   curve_type=str(c.GetType()), degenerated=BRep_Tool.Degenerated_s(e))
        row['endpoints'] = []
        for t in [c.FirstParameter(), c.LastParameter()]:
            p=c.Value(t); row['endpoints'].append([p.X(),p.Y(),p.Z()])
        row['adjacent_faces'] = []
        for i in range(1,index['face'].Extent()+1):
            f=TopoDS.Face_s(index['face'].FindKey(i)); fm=maps(f)
            if fm['edge'].FindIndex(e):
                row['adjacent_faces'].append({'id':i,'surface_type':str(BRepAdaptor_Surface(f).GetType()),'tolerance':BRep_Tool.Tolerance_s(f)})
    return row

def check(shape, modes=MODES, locate=False):
    c=BOPAlgo_ArgumentAnalyzer(); c.SetShape1(shape.wrapped)
    for mode in ALL_MODES: setattr(c,mode,mode in modes)
    t=time.monotonic(); c.Perform()
    index=maps(shape.wrapped) if locate else None
    faults=[]
    for r in c.GetCheckResult():
        row={'status':str(r.GetCheckStatus()),'max_distance_1':r.GetMaxDistance1(),'max_parameter_1':r.GetMaxParameter1()}
        if locate:
            row['faulty_shapes_1']=[describe(x,index) for x in r.GetFaultyShapes1()]
            row['faulty_shapes_2']=[describe(x,index) for x in r.GetFaultyShapes2()]
        faults.append(row)
    report={'modes':modes,'BRep_valid':bool(shape.is_valid),'solids':len(shape.solids()),
            'faces':len(shape.faces()),'edges':len(shape.edges()),'volume':shape.volume,
            'has_faulty':bool(c.HasFaulty()),'has_errors':bool(c.HasErrors()),'has_warnings':bool(c.HasWarnings()),
            'faults':faults,'elapsed_seconds':time.monotonic()-t}
    report['passed']=report['BRep_valid'] and not any(report[k] for k in ['has_faulty','has_errors','has_warnings'])
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('step',type=Path); ap.add_argument('output',type=Path)
    ap.add_argument('--modes',nargs='+',default=MODES); args=ap.parse_args()
    if args.output.exists(): raise ValueError('output_must_be_new')
    print('Reading', args.step, flush=True)
    original=sha(args.step); shape=b.import_step(args.step)
    r=check(shape,args.modes,True); r.update(input_sha256=original,input_unchanged=sha(args.step)==original)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='faults'}),flush=True)
    print('Faults:',[(x['status'],x['max_distance_1']) for x in r['faults']],flush=True)
