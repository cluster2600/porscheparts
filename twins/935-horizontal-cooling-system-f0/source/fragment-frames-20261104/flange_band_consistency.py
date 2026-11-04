#!/usr/bin/env python3
"""Check same-scan flange opening fits across two axial bands."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def rigid_fit(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float)
 if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=2 or len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all(): raise ValueError('invalid paired points')
 ac=a.mean(axis=0);bc=b.mean(axis=0);u,s,vt=np.linalg.svd((a-ac).T@(b-bc))
 if s[-1]<1e-10:raise ValueError('rank deficient pattern')
 correction=np.diag([1.,np.linalg.det(vt.T@u.T)]);r=vt.T@correction@u.T;t=bc-r@ac
 if np.linalg.det(r)<0.999999999:raise ValueError('reflection')
 return r,t


def analyze(a,b):
 r,t=rigid_fit(a,b); residual=np.linalg.norm(b-(a@r.T+t),axis=1); hold=[]
 for i in range(len(a)):
  keep=np.arange(len(a))!=i; ri,ti=rigid_fit(a[keep],b[keep]);hold.append(float(np.linalg.norm(b[i]-(ri@a[i]+ti))))
 return {'mean_centre_shift_source_units':float(np.linalg.norm(b.mean(axis=0)-a.mean(axis=0))),'rotation_degrees':float(np.degrees(np.arctan2(r[1,0],r[0,0]))),'in_sample_rms_source_units':float(np.sqrt(np.mean(residual**2))),'in_sample_max_source_units':float(residual.max()),'leave_one_out_rms_source_units':float(np.sqrt(np.mean(np.square(hold)))),'leave_one_out_max_source_units':float(max(hold)),'raw_pair_shift_min_source_units':float(np.linalg.norm(b-a,axis=1).min()),'raw_pair_shift_max_source_units':float(np.linalg.norm(b-a,axis=1).max())}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[4]/'work'
 if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private work output required')
 expected='da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c'
 if sha(a.report)!=expected:raise ValueError('flange report hash mismatch')
 d=json.loads(a.report.read_text()); rows=d['openings']
 if d['status']!='eight_lower_flange_opening_candidates_only' or len(rows)!=8 or any(d[k] is not False for k in ('same_scan_bands_are_independent_dimensions','source_unit_to_mm_verified','mounting_role_verified','through_holes_verified','bolt_pattern_defined','manufacturing_authorized')): raise ValueError('unexpected evidence status')
 for row in rows:
  if len(row['fits'])!=2 or [x['z_band_source_units'] for x in row['fits']]!=d['z_bands_source_units']:raise ValueError('band pairing changed')
 xy=[np.array([r['fits'][i]['fit_centre_xy_source_units'] for r in rows]) for i in (0,1)]
 result={'status':'same_scan_two_band_fit_consistency_not_mounting_datum','input_sha256':expected,'count':8,'same_scan_correlated':True,'summary':analyze(*xy),'scale_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
