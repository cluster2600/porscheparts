"""Read native quadratic rational coefficients and bound every root-arc point."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);sys.path.insert(0,str(a.native_site.resolve()))
    from build123d import import_brep
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    helper=Path(__file__).with_name('rational_cylinder_certificate.py');spec=importlib.util.spec_from_file_location('_root_radius_math',helper);maths=importlib.util.module_from_spec(spec);spec.loader.exec_module(maths)
    body=import_brep(a.body);rows=[]
    for face in body.faces():
        box=face.bounding_box()
        if not((69<box.min.X<73 or -73<box.max.X<-69)and box.min.Z>-3 and box.max.Z<3):continue
        adaptor=BRepAdaptor_Surface(face.wrapped)
        if not str(adaptor.GetType()).endswith('GeomAbs_BSplineSurface'):continue
        s=adaptor.BSpline()
        if (s.UDegree(),s.VDegree(),s.NbUPoles(),s.NbVPoles())!=(2,2,3,5):raise ValueError('Unexpected native root tensor dimensions')
        uk=[s.UKnot(i)for i in range(1,s.NbUKnots()+1)];vk=[s.VKnot(i)for i in range(1,s.NbVKnots()+1)];um=[s.UMultiplicity(i)for i in range(1,s.NbUKnots()+1)];vm=[s.VMultiplicity(i)for i in range(1,s.NbVKnots()+1)]
        if um!=[3,3]or len(uk)!=2 or uk[0]>=uk[1]:raise ValueError('Native U arc is not a single Bezier segment')
        poles=[[list(s.Pole(i,j).Coord())for j in range(1,6)]for i in range(1,4)];weights=[[s.Weight(i,j)for j in range(1,6)]for i in range(1,4)]
        # Exact tensor factorisation: radial coordinates/weights do not depend on V.
        for i in range(3):
            if any((poles[i][j][0],poles[i][j][2],weights[i][j])!=(poles[i][0][0],poles[i][0][2],weights[i][0])for j in range(1,5)):raise ValueError('Native radial tensor does not factor exactly')
        arc=[(F(poles[i][0][0]),F(poles[i][0][2]))for i in range(3)];w=[F(weights[i][0])for i in range(3)];den=w[0]+2*w[1]+w[2]
        middle=tuple((w[0]*arc[0][k]+2*w[1]*arc[1][k]+w[2]*arc[2][k])/den for k in range(2))
        centre=maths.centre_through_three([arc[0],middle,arc[2]])
        pieces=[maths.radial_bound([[point]for point in arc],[[x]for x in w],centre,F(3,5))]
        bound=F(pieces[0]['complete_radial_deviation_bound_mm'])
        rows.append(dict(bounds_mm=[list(box.min),list(box.max)],U_knots=uk,V_knots=vk,U_multiplicities=um,V_multiplicities=vm,poles_xyz_mm=poles,weights=weights,axis_parallel_Y_centre_XZ_Q=list(map(str,centre)),nominal_radius_mm=.6,complete_radial_deviation_bound_mm=str(bound),pieces=pieces))
    if len(rows)!=4:raise ValueError('Expected all four complete root fillet faces')
    maximum=max(F(row['complete_radial_deviation_bound_mm'])for row in rows);passed=maximum<=F(1,100000000)
    report=dict(status='complete_native_root_radial_geometry_certificate_passed'if passed else'root_radius_certificate_refused',scope='All points of all four native rational tensor faces, including their untrimmed support rectangles; exact radial tensor factorisation, no coefficient conversion or sampling. Radial geometric proximity is not a curvature-convergence claim.',faces=rows,maximum_complete_radial_deviation_mm=str(maximum),maximum_complete_radial_deviation_mm_float=float(maximum),fixed_readback_limit_mm=1e-8,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.body,helper,Path(__file__)]})
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','maximum_complete_radial_deviation_mm_float']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
