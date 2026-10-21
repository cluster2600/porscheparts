"""Exact slab-disjointness certificate for the additive source representation.

Reconstruct all eight frozen finite rosters byte for byte. A positive source
union cannot change membership where every added solid is disjoint. This
checks source preservation, not the altered boundary of a volume-mesh export.
"""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 a.output.mkdir(parents=True);s=Path(__file__).resolve().parent;root=s.parents[4];review_path=s.parent/'corner-slide-candidate-20261018/evidence/protected-root.json';contract_path=root/'parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013/interface-study.json';bracket_path=root/'twins/993-engine-mount-system-f0/derived/993-ENG-BRACKET-0001.stl'
 report=dict(status='incomplete',scope='Preservation of retained F0 source predicates for the unchanged parent plus two positive 3MF components; not a volume-mesh interface certificate',mechanical_mesh_admitted=False)
 try:
  import numpy as np
  def require(value,message):
   if not value:raise ValueError(message)
  review=json.loads(review_path.read_text());inspection=json.loads((s/'inputs/frozen-baseline-inspection.json').read_text());raw=gzip.decompress((s/'inputs/frozen-protected-rosters.json.gz').read_bytes());rosters=json.loads(raw);contract=json.loads(contract_path.read_text())
  require(hashlib.sha256(raw).hexdigest()==review['whole_contains_sha256'],'Frozen full roster receipt differs')
  require(sha(s/'inputs/frozen-baseline-inspection.json')==review['inspection_sha256'],'Frozen baseline inspection differs')
  require(sha(s/'inputs/frozen-inspection-source.py')==review['whole_outputs']['output-001/protected-input/inspection-source.py']['sha256'],'Frozen inspector source differs')
  require(sha(contract_path)==inspection['inputs_sha256']['contract'],'Frozen study contract differs')
  require(sha(bracket_path)==inspection['inputs_sha256']['F0_bracket.stl'],'Frozen comparator differs')
  require(review['study_assembly_screen_pass']and review['all8_complete_bool_rosters_zero'],'Original frozen source predicates not passed')
  evidence=root/'docs/reports/carrier-resume-20261020/evidence';assembly=json.loads((evidence/'certified-component-replay-001/assessment.json').read_text());audit=json.loads((evidence/'component-libigl-certified-001/assessment.json').read_text())
  require(sha(s/'carrier-additive-assembly-study.3mf')==assembly['archive_sha256']==audit['archive_sha256'],'Actual component archive differs')
  require(assembly['checks']['all_component_geometry_bytes_preserved']and audit['status']=='all_complete_component_surface_screens_passed','Whole source component screens not passed')
  require(assembly['components'][0]['source_sha256']==review['actual_STL_sha256'],'Retained full parent differs')
  helper=importlib.util.spec_from_file_location('_preserved_stl',s/'certified_patch_collapse.py');m=importlib.util.module_from_spec(helper);helper.loader.exec_module(m)
  bounds=[]
  for i in range(2):
   path=s/f'inputs/certified-patch-{i}.stl';require(sha(path)==assembly['components'][i+1]['source_sha256'],'Added source component differs');v,f=m.load_stl(path,np)
   lo=[F(float(x))for x in v.min(axis=0)];hi=[F(float(x))for x in v.max(axis=0)]
   require(hi[0]<=-65 or lo[0]>=65,'Patch overlaps central-pad interior in X')
   bounds.append((lo,hi))
  report['added_closed_component_bounds_mm']=[dict(minimum=list(map(str,lo)),maximum=list(map(str,hi)))for lo,hi in bounds]
  def disjoint_x(lo,hi):return all(hi<a0[0]or lo>b0[0]for a0,b0 in bounds)
  angles=np.arange(64)*2*np.pi/64;rows=[]
  require(len(rosters['records'])==8,'Whole eight-roster scope differs')
  for i,(x,y)in enumerate(contract['study_central_centres_xy_mm']):
   points=np.asarray([[float(x)+r*np.cos(angle),float(y)+r*np.sin(angle),z]for z in np.linspace(-15.9,3.9,17)for r in(0,2.5,5)for angle in angles]);digest=hashlib.sha256(points.tobytes()).hexdigest();lo=F(float(points[:,0].min()));hi=F(float(points[:,0].max()))
   require(disjoint_x(lo,hi),'Finite probe roster intersects an added source slab')
   for label in ['carrier','bracket']:
    record=rosters['records'][2*i+(label=='bracket')];require(record['mesh']==label and record['probe_bytes_sha256']==digest and record['probe_shape']==list(points.shape)and record['probe_dtype']==points.dtype.str,'Exact original full probe array differs')
    values=np.asarray(record['whole_bool_values'],dtype=np.bool_);require(record['complete']and len(values)==3264 and not values.any()and hashlib.sha256(values.tobytes()).hexdigest()==record['whole_bool_bytes_sha256'],'Original whole bool roster differs')
    rows.append(dict(call=record['call'],mesh=label,points=len(points),probe_bytes_sha256=digest,exact_original_probe_bytes_reconstructed=True,X_min_mm=str(lo),X_max_mm=str(hi),added_material_disjoint=True,original_true_count=0,source_union_membership_unchanged=True))
  report['all_eight_complete_rosters']=rows
  bore_tools=[]
  for x,y in contract['study_central_centres_xy_mm']:
   for role,radius in [('central_bore',contract['study_carrier_bore_radius_mm']),('tool_column',contract['study_tool_radius_mm'])]:
    lo=F(x)-F(radius);hi=F(x)+F(radius);require(disjoint_x(lo,hi),'Original bore/tool region intersects added source')
    bore_tools.append(dict(role=role,centre_xy_mm=[x,y],radius_mm=radius,exact_X_interval_mm=[str(lo),str(hi)],added_material_disjoint=True))
  report['complete_central_bore_and_tool_regions']=bore_tools
  end_regions=[]
  for x in contract['study_end_centres_x_mm']:
   for label,radius in [('bore',F(7)),('seats',F(float(15.999)))]:
    lo=F(x)-radius;hi=F(x)+radius;require(disjoint_x(lo,hi),'Frozen end region intersects added material');end_regions.append(dict(role=label,centre_X_mm=x,region_X_interval_mm=[str(lo),str(hi)],added_material_disjoint=True))
  report['frozen_end_regions']=end_regions
  bracket,_=m.load_stl(bracket_path,np);max_z=max(-F(float(z))-4 for z in bracket[:,2]);patch_min_z=min(lo[2]for lo,hi in bounds);gap=patch_min_z-max_z;require(gap>0,'Frozen transformed comparator not strictly separated from added material')
  report['full_transformed_comparator']=dict(pose='diag(1,-1,-1), translation Z=-4mm from frozen inspector',maximum_Z_mm=str(max_z),added_minimum_Z_mm=str(patch_min_z),exact_positive_Z_gap_mm=str(gap),new_material_collision_impossible=True)
  report['central_pad_ROI']=dict(X_interval_mm=[-65,65],added_material_intersects_only_boundary_planes_at_most=True,positive_3D_material_unchanged=True,boundary_shape_identity_proved=False)
  report['source_sha256']={str(p):sha(p)for p in [review_path,contract_path,bracket_path,s/'inputs/frozen-baseline-inspection.json',s/'inputs/frozen-protected-rosters.json.gz',s/'inputs/frozen-inspection-source.py',s/'carrier-additive-assembly-study.3mf',Path(__file__)]}
  report.update(status='scoped_source_preservation_certificate_passed',numpy_version=np.__version__,all_26112_finite_probe_memberships_unchanged=True,whole_frozen_native_inspector_rerun=False,global_volume_mesh_interface_admission=False)
 except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error));raise
 finally:(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k]for k in ['status','numpy_version','all_26112_finite_probe_memberships_unchanged']}))

if __name__=='__main__':main()
