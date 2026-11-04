#!/usr/bin/env python3
"""Compare finite fitted axis spans without assigning a mating relationship."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.optimize import lsq_linear


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def segment_distance(a,b,c,d):
 a,b,c,d=(np.asarray(v,dtype=float) for v in (a,b,c,d)); matrix=np.column_stack((b-a,-(d-c)))
 if not np.isfinite(matrix).all() or np.linalg.norm(b-a)<1e-12 or np.linalg.norm(d-c)<1e-12: raise ValueError('invalid segment')
 fit=lsq_linear(matrix,c-a,bounds=(0,1),tol=1e-14,max_iter=1000)
 if not fit.success or np.any(fit.x<0) or np.any(fit.x>1): raise ValueError('segment minimization failed')
 return float(np.linalg.norm(a+fit.x[0]*(b-a)-c-fit.x[1]*(d-c)))


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('shaft',type=Path);p.add_argument('support',type=Path);p.add_argument('mapping',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 root=Path(__file__).resolve().parents[4]/'work'
 if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private output required')
 expected=('2cb88c11bb02f0d7ee5ea481a4887cd75d0cc48a718f22cc89a95ca8f8290e57','cb150f62fe4dbb683c06632a43245a9277e12e974c2925db123c01d3f1d25c67','11039619a1e206090b28ee919faaf4d2f96107d47a63809a9f77a39811cf0d04')
 if tuple(sha(x) for x in (a.shaft,a.support,a.mapping))!=expected: raise ValueError('input hash mismatch')
 shaft=json.loads(a.shaft.read_text());support=json.loads(a.support.read_text());mapping=json.loads(a.mapping.read_text()); m=np.array(mapping['shaft_cad_to_support_cad'],float)
 candidates=[p for p in support['patches'] if p['id']=='support-bore-arc-00']
 if len(candidates)!=1 or shaft['source_sha256']!=support['source_sha256'] or mapping['status']!='same_scan_coordinate_mapping_not_fit_validation': raise ValueError('unexpected input relationship')
 model=candidates[0]['models'][candidates[0]['preferred_model']]
 if model['type']!='cylinder' or model['functional_datum_verified'] or shaft['scale_verified'] or support['scale_verified']: raise ValueError('unqualified cylinder required')
 u=m[:3,2]; v=np.array(model['axis_in_seed_frame'],float);v/=np.linalg.norm(v); o=m[:3,3]; q=np.array(model['origin_in_seed_frame_source_units']); cross=np.cross(u,v); norm=np.linalg.norm(cross)
 if norm<1e-8 or not np.isclose(np.linalg.norm(u),1,atol=1e-9): raise ValueError('invalid or near-parallel axis')
 angle=float(np.degrees(np.arccos(np.clip(abs(u@v),0,1)))); infinite=float(abs((q-o)@cross)/norm)
 z=np.array([pt[2] for profile in shaft['profiles'] for pt in profile]); span=model['axial_span_source_units'];finite=segment_distance(o+u*z.min(),o+u*z.max(),q+v*span[0],q+v*span[1])
 if finite+1e-8<infinite: raise ValueError('finite axis distance smaller than infinite-line distance')
 result={'status':'same_scan_fitted_axis_comparison_not_a_mating_test','input_sha256':expected,'acute_axis_angle_degrees':angle,'infinite_axis_distance_source_units':infinite,'finite_fitted_axis_span_distance_source_units':finite,'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
 a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))

if __name__=='__main__': main()
