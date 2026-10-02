"""Invariant checks shared by the accepted pcurve repair."""
import re,hashlib
from OCP.BRep import BRep_Tool
from OCP.TopoDS import TopoDS

def sections(path):
    txt=path.read_text(); out={}
    for start,end in [('Locations','Curve2ds'),('Curves','Polygon3D'),('Surfaces','Triangulations')]:
        a=re.search(r'^'+start+r' \d+',txt,re.M); z=re.search(r'^'+end+r' \d+',txt,re.M)
        if a and z: out[start]=hashlib.sha256(txt[a.start():z.start()].encode()).hexdigest()
    return out

def snapshots(index):
    cast={'edge':TopoDS.Edge_s,'face':TopoDS.Face_s,'vertex':TopoDS.Vertex_s}
    return {k:[BRep_Tool.Tolerance_s(cast[k](m.FindKey(i))) for i in range(1,m.Extent()+1)] for k,m in index.items()}
