"""Fill only four declared closed root pockets detected in the saved CAD.

Every inner shell must match the declared small root region and negative
volume before its removal. All other external and through-cavity faces remain
in the retained outer shell; no remeshing or arbitrary hole filling is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();sys.path.insert(0,str(a.native_site.resolve()))
    from build123d import import_brep,export_brep,export_step,export_stl,Solid
    from OCP.BRepClass3d import BRepClass3d
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BRepLib import BRepLib
    from OCP.BRepTools import BRepTools
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    body=import_brep(a.body)
    if not body.is_valid or len(body.solids())!=1:raise ValueError('Expected one saved valid solid')
    solid=body.solids()[0];outer=BRepClass3d.OuterShell_s(solid.wrapped);rows=[]
    for shell in solid.shells():
        if shell.wrapped.IsSame(outer):continue
        box=shell.bounding_box();lo=list(box.min);hi=list(box.max);props=GProp_GProps();BRepGProp.VolumeProperties_s(shell.wrapped,props,1e-10,True,False);volume=props.Mass()
        in_x=(65<lo[0]<hi[0]<75)or(-75<lo[0]<hi[0]<-65);in_y=(32<lo[1]<hi[1]<36.5001)or(-36.5001<lo[1]<hi[1]<-32)
        row=dict(bounds_mm=[lo,hi],signed_volume_mm3=volume,declared_root_region=bool(in_x and in_y and lo[2]>-3 and hi[2]<3),negative_small_closed_void=-2<volume<0)
        rows.append(row)
    if len(rows)!=4 or not all(r['declared_root_region']and r['negative_small_closed_void']for r in rows):raise ValueError('Inner shells do not match the four observed root pockets')
    maker=BRepBuilderAPI_MakeSolid(outer)
    if not maker.IsDone():raise ValueError('Outer-shell solid failed')
    shape=maker.Solid();BRepLib.OrientClosedSolid_s(shape);result=Solid(shape)
    if not result.is_valid or len(result.solids())!=1 or len(result.shells())!=1:raise ValueError('Filled result is not one valid single-shell solid')
    props=GProp_GProps();BRepGProp.VolumeProperties_s(shape,props,1e-10,True,False);volume=props.Mass()
    export_brep(result,a.output/'candidate-native.brep');export_step(result,a.output/'candidate.step');BRepTools.Clean_s(shape);export_stl(result,a.output/'candidate-fine.stl',tolerance=.015,angular_tolerance=.08)
    local=[]
    for face in result.faces():
        box=face.bounding_box()
        if (69<box.min.X<73 or -73<box.max.X<-69)and box.min.Z>-3 and box.max.Z<3:
            surf=BRepAdaptor_Surface(face.wrapped);row=dict(type=str(surf.GetType()),bounds_mm=[list(box.min),list(box.max)])
            if str(surf.GetType()).endswith('GeomAbs_BSplineSurface'):
                s=surf.BSpline();row.update(U_degree=s.UDegree(),V_degree=s.VDegree(),U_poles=s.NbUPoles(),V_poles=s.NbVPoles(),U_rational=s.IsURational(),V_rational=s.IsVRational())
            local.append(row)
    report=dict(status='four_declared_closed_pockets_filled_native_valid',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.body,Path(__file__)]},removed_inner_shells=rows,retained_outer_shell_only=True,valid=result.is_valid,shells=len(result.shells()),native_volume_mm3=volume,mass_kg=volume*4.42e-6,mass_limit_kg=1.3,local_native_face_inventory=local,independent_radius_readback_complete=False,output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.output.iterdir()if p.is_file()},elapsed_seconds=time.monotonic()-start,manufacturing_authorized=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],mass_kg=report['mass_kg'],local_face_types=[r['type']for r in local])))

if __name__=='__main__':main()
