"""Read saved BREP face surfaces and compare every source tensor coefficient."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    from build123d import import_brep
    from OCP.BRep import BRep_Tool
    from OCP.Geom import Geom_BSplineSurface
    data=json.loads((a.inputs/'nurbs-control-nets.json').read_text());report=dict(status='incomplete',patches=[])
    for i,row in enumerate(data['patches']):
        path=a.inputs/f'patch-{i}.brep';solid=import_brep(path);actual=[];planes=0
        for face in solid.faces():
            s=BRep_Tool.Surface_s(face.wrapped)
            if not isinstance(s,Geom_BSplineSurface):planes+=1;continue
            actual.append(dict(U_degree=s.UDegree(),V_degree=s.VDegree(),U_knots=[s.UKnot(k)for k in range(1,s.NbUKnots()+1)],U_multiplicities=[s.UMultiplicity(k)for k in range(1,s.NbUKnots()+1)],V_knots=[s.VKnot(k)for k in range(1,s.NbVKnots()+1)],V_multiplicities=[s.VMultiplicity(k)for k in range(1,s.NbVKnots()+1)],poles=[[list(s.Pole(u,v).Coord())for v in range(1,s.NbVPoles()+1)]for u in range(1,s.NbUPoles()+1)],weights=[[s.Weight(u,v)for v in range(1,s.NbVPoles()+1)]for u in range(1,s.NbUPoles()+1)]))
        checks=[]
        for source in row['surfaces']:
            names=source['column_order'];expected=dict(U_degree=row['aligned_curve']['degree'],V_degree=len(names)-1,U_knots=row['aligned_curve']['knots'],U_multiplicities=row['aligned_curve']['multiplicities'],V_knots=[0.,1.],V_multiplicities=[len(names),len(names)],poles=[[source['control_columns'][key][u]for key in names]for u in range(len(source['control_columns'][names[0]]))],weights=[source['weights']for _ in source['control_columns'][names[0]]])
            matches=[k for k,s in enumerate(actual)if s==expected]
            checks.append(dict(surface=source['name'],exact_source_match_indices=matches,passed=len(matches)==1))
        report['patches'].append(dict(BREP_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),valid=solid.is_valid,solid_count=len(solid.solids()),BSpline_faces=len(actual),other_faces=planes,checks=checks,complete_native_readbacks=actual))
    report['status']='all_native_tensor_coefficients_exact'if all(p['valid']and p['solid_count']==1 and p['BSpline_faces']==4 and p['other_faces']==2 and all(c['passed']for c in p['checks'])for p in report['patches'])else'native_control_net_identity_refused'
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
    return int(report['status']!='all_native_tensor_coefficients_exact')

if __name__=='__main__':raise SystemExit(main())
