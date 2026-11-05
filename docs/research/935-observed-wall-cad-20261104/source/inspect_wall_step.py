"""Reopen actual STEP exports and prepare independent scan-distance assessment."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.spatial import cKDTree
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_Plane
from OCP.TopAbs import TopAbs_FACE,TopAbs_SOLID,TopAbs_REVERSED
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from scripts.scan_feature_cad import shapes


def load(path):
    reader=STEPControl_Reader()
    if reader.ReadFile(str(path))!=IFSelect_RetDone or reader.TransferRoots()<1:raise ValueError('STEP reload failed')
    shape=reader.OneShape()
    if not BRepCheck_Analyzer(shape).IsValid():raise ValueError('Actual STEP shape is invalid')
    if shapes(shape,TopAbs_SOLID):raise ValueError('Unexpected solid in an observed surface export')
    return shape


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','cad','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing STEP inspection refused.')
    args.output.mkdir(parents=True);records=[]
    domains=json.loads((args.preparation/'cad-domains.json').read_text())
    for model in domains:
        ident=model['id']
        with np.load(args.preparation/(ident+'-reference.npz'),allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
        reference=load(args.cad/(ident+'-reference.step'));faces=shapes(reference,TopAbs_FACE)
        tree=cKDTree(v);expected={tuple(sorted(map(int,t))):i for i,t in enumerate(f)};seen=[];maximum=0.;negative=0
        for face in faces:
            surf=BRepAdaptor_Surface(face,True)
            if surf.GetType()!=GeomAbs_Plane:raise ValueError('Expected planar source facets')
            explorer=BRepTools_WireExplorer(BRepTools.OuterWire_s(face),face);points=[]
            while explorer.More():
                pt=BRep_Tool.Pnt_s(explorer.CurrentVertex());points.append([pt.X(),pt.Y(),pt.Z()]);explorer.Next()
            if len(points)!=3:raise ValueError('Reference triangle changed boundary structure')
            distance,indices=tree.query(np.asarray(points));maximum=max(maximum,float(distance.max()))
            key=tuple(sorted(map(int,indices)))
            if key not in expected:raise ValueError('Reference export introduced a triangle')
            original=v[f[expected[key]]];normal=np.cross(original[1]-original[0],original[2]-original[0]);normal/=np.linalg.norm(normal)
            direction=surf.Plane().Axis().Direction();native=np.array([direction.X(),direction.Y(),direction.Z()])
            if face.Orientation()==TopAbs_REVERSED:native=-native
            if float(normal@native)<1-1e-8:negative+=1
            seen.append(expected[key])
        checks={'all_source_triangles_exactly_once':len(seen)==len(f) and len(set(seen))==len(f),
            'vertex_roundtrip_under_1e-6mm':maximum<=1e-6,'source_orientation_preserved':negative==0}
        record={'id':ident,'reference_faces':len(faces),'reference_vertex_max_error_mm':maximum,
                'reference_normal_mismatches':negative,'reference_checks':checks,'zero_solids':True}
        if not all(checks.values()):raise ValueError('Reference STEP fidelity checks failed: '+json.dumps(record))
        if model['admitted']:
            path=args.cad/(ident+'-analytic.step');shape=load(path);analytic=shapes(shape,TopAbs_FACE)
            if len(analytic)!=len(model['domains']):raise ValueError('Analytic trim-face count changed')
            parameter_error=0.;normal_alignment=[]
            for face in analytic:
                surf=BRepAdaptor_Surface(face,True)
                if surf.GetType()!=GeomAbs_Cylinder:raise ValueError('Export lost analytic cylindrical surface')
                c=surf.Cylinder();parameter_error=max(parameter_error,abs(c.Radius()-model['radius']))
                direction=c.Axis().Direction();axis=np.array([direction.X(),direction.Y(),direction.Z()]);normal_alignment.append(abs(float(axis@model['axis'])))
            BRepMesh_IncrementalMesh(shape,.005,False,.1,True)
            vertices=[];triangles=[]
            for face in analytic:
                location=TopLoc_Location();mesh=BRep_Tool.Triangulation_s(face,location)
                if mesh is None:raise ValueError('Analytic face has no triangulation')
                transform=location.Transformation();points=[mesh.Node(i).Transformed(transform) for i in range(1,mesh.NbNodes()+1)]
                q=np.array([[x.X(),x.Y(),x.Z()] for x in points]);t=np.array([mesh.Triangle(i).Get() for i in range(1,mesh.NbTriangles()+1)],np.int64)-1
                if face.Orientation()==TopAbs_REVERSED:t=t[:,[0,2,1]]
                triangles.extend((t+len(vertices)).tolist());vertices.extend(q.tolist())
            np.savez_compressed(args.output/(ident+'-actual-step-mesh.npz'),vertices=np.asarray(vertices),triangles=np.asarray(triangles,np.int64))
            record.update(analytic_faces=len(analytic),all_surfaces_cylindrical=True,
                radius_roundtrip_max_error_mm=parameter_error,axis_alignment_min=min(normal_alignment),
                actual_step_tessellation_triangles=len(triangles),tessellation_deflection_mm=.005)
            if parameter_error>1e-8 or min(normal_alignment)<1-1e-10:raise ValueError('Analytic model parameter round trip failed')
        records.append(record)
    report={'regions':records,'actual_files_reopened':True,'physical_acceptance':False,'manufacturing_authorized':False}
    (args.output/'step-inspection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
