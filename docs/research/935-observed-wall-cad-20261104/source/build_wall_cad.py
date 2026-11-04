"""Create exact faceted references and admitted, source-trimmed cylindrical faces."""
import argparse
import json
from pathlib import Path
import numpy as np
from OCP.gp import gp_Pnt,gp_Pnt2d,gp_Ax3,gp_Dir
from OCP.Geom import Geom_CylindricalSurface
from OCP.GCE2d import GCE2d_MakeSegment
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakePolygon
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.BRepLib import BRepLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone


def save(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def area(shape):
    properties=GProp_GProps();BRepGProp.SurfaceProperties_s(shape,properties);return properties.Mass()


def wire(surface,ring,outer):
    points=np.asarray(ring,float)
    signed=np.sum(points[:-1,0]*points[1:,1]-points[1:,0]*points[:-1,1])
    if (signed>0)!=outer:points=points[::-1]
    maker=BRepBuilderAPI_MakeWire()
    for first,second in zip(points[:-1],points[1:]):
        curve=GCE2d_MakeSegment(gp_Pnt2d(*first),gp_Pnt2d(*second)).Value()
        edge=BRepBuilderAPI_MakeEdge(curve,surface)
        if not edge.IsDone():raise ValueError('Could not build a surface edge')
        maker.Add(edge.Edge())
    if not maker.IsDone():raise ValueError('Could not build a trim wire')
    return maker.Wire()


def cylinder_face(surface,domain):
    builder=BRepBuilderAPI_MakeFace(surface,wire(surface,domain['outer'],True),True)
    for ring in domain['holes']:builder.Add(wire(surface,ring,False))
    if not builder.IsDone():raise ValueError('Could not build a trimmed face')
    face=builder.Face()
    if not BRepLib.BuildCurves3d_s(face,1e-8):raise ValueError('Could not build native 3D curves')
    if not BRepCheck_Analyzer(face).IsValid():raise ValueError('Trimmed face failed native validity')
    return face


def compound(faces):
    result=TopoDS_Compound();builder=BRep_Builder();builder.MakeCompound(result)
    for face in faces:builder.Add(result,face)
    return result


def write_step(shape,path):
    writer=STEPControl_Writer()
    if writer.Transfer(shape,STEPControl_AsIs)!=IFSelect_RetDone or writer.Write(str(path))!=IFSelect_RetDone:
        raise ValueError('STEP export failed')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing CAD directory refused.')
    args.output.mkdir(parents=True)
    # Analytic area and periodic-parameter controls before using private inputs.
    surface=Geom_CylindricalSurface(gp_Ax3(gp_Pnt(0,0,0),gp_Dir(0,0,1),gp_Dir(1,0,0)),5.)
    control=cylinder_face(surface,{'outer':[[.2,0],[1,0],[1,2],[.2,2],[.2,0]],'holes':[[[.4,.5],[.4,1],[.6,1],[.6,.5],[.4,.5]]]})
    periodic=cylinder_face(surface,{'outer':[[6.1,0],[6.4,0],[6.4,1.5],[6.1,1.5],[6.1,0]],'holes':[]})
    checks={'trim_with_hole_area':abs(area(control)-7.5)<1e-7,'periodic_patch_area':abs(area(periodic)-2.25)<1e-7}
    if not all(checks.values()):raise SystemExit('Cylinder controls failed.')
    save(args.output/'native-controls.json',checks);write_step(compound([control,periodic]),args.output/'controls.step')
    domains=json.loads((args.preparation/'cad-domains.json').read_text());records=[]
    for model in domains:
        ident=model['id'];faces=[]
        with np.load(args.preparation/(ident+'-reference.npz'),allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
        for tri in v[f]:
            polygon=BRepBuilderAPI_MakePolygon()
            for point in tri:polygon.Add(gp_Pnt(*point))
            polygon.Close();maker=BRepBuilderAPI_MakeFace(polygon.Wire())
            if not maker.IsDone() or not BRepCheck_Analyzer(maker.Face()).IsValid():raise ValueError('Source reference face rejected; no triangle discarded.')
            faces.append(maker.Face())
        reference=compound(faces);write_step(reference,args.output/(ident+'-reference.step'))
        record={'id':ident,'reference_faces':len(faces),'reference_area_mm2':area(reference),'analytic_admitted':model['admitted']}
        if model['admitted']:
            surface=Geom_CylindricalSurface(gp_Ax3(gp_Pnt(*model['origin']),gp_Dir(*model['axis']),gp_Dir(*model['x_direction'])),model['radius'])
            fitted=[]
            for domain in model['domains']:
                face=cylinder_face(surface,domain)
                if model['source_orientation']<0:face.Reverse()
                fitted.append(face)
            result=compound(fitted)
            if not BRepCheck_Analyzer(result).IsValid():raise ValueError('Analytic compound failed native validity')
            write_step(result,args.output/(ident+'-analytic.step'))
            record.update(analytic_faces=len(fitted),analytic_area_mm2=area(result))
        records.append(record)
    save(args.output/'build-report.json',{'regions':records,'controls':checks,'baseline_changed':False,'solid_created':False,'physical_acceptance':False})
    print(json.dumps({'regions':records}))


if __name__=='__main__':main()
