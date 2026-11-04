#!/usr/bin/env python3
"""Screen a provisional rotor revolution against three added open/witness surfaces."""
import argparse,importlib.metadata,json,math,sys,time
from pathlib import Path
import numpy as np
import fcl

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from review_surface_contacts import DTYPE,fixtures,load,query,sha
from review_rotor_sweep import between_sample_motion,moving_fixture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rotor',type=Path);p.add_argument('shaft',type=Path);p.add_argument('support',type=Path);p.add_argument('witnesses',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private work output required')
inputs=(a.rotor,a.shaft,a.support,a.witnesses)
expected=('20c63d8d2c13cfe906a4385ffc521881ec835d5dcd2dc646d295659b82bfb53c','aab59ff0dd10644138dd6a9ec970c7b1abb94f20f72fee0e6234500200759a91','89b86f3d353603b57ab71eaf8306d8681a2cec6110a734a5ba17eae4da274e98','479e2c5d129d37a5821dbbda59695f5910facda97492a47571787fd32f5ec769')
if tuple(sha(x) for x in inputs)!=expected: raise ValueError('input hash mismatch')
controls=fixtures(); moving_fixture();start=time.monotonic()
rotor=load(a.rotor,871078); targets={name:load(path,count) for name,path,count in [('shaft',a.shaft,2112),('support',a.support,94),('flange_witnesses',a.witnesses,221304)]}
r=np.memmap(a.rotor,mode='r',dtype=DTYPE,offset=84,shape=(871078,))['vertices']; radius=max(float(np.linalg.norm(np.asarray(r[i:i+100000,:,:2],dtype=float),axis=2).max()) for i in range(0,len(r),100000)); motion=between_sample_motion(radius,240)
phases={k:[] for k in targets}
for i in range(240):
 theta=2*math.pi*i/240;c,s=math.cos(theta),math.sin(theta);rotor.setTransform(fcl.Transform(np.array([[c,-s,0],[s,c,0],[0,0,1.]])))
 for name,target in targets.items(): phases[name].append({'phase_index':i,'angle_deg':i*1.5,**query(rotor,target)})
summary={}
for name,rows in phases.items():
 hits=sum(r['surface_crossing'] for r in rows); ds=[r['minimum_surface_distance_native_units'] for r in rows if not r['surface_crossing']]; low=min(ds) if ds else None
 summary[name]={'sampled_surface_crossings':hits,'minimum_sampled_distance_source_units':low,'continuous_lower_bound_source_units':low-motion-1e-4 if low is not None and hits==0 else None,'rigid_surface_separation_certified':bool(not hits and low is not None and low>motion+1e-4)}
if tuple(sha(x) for x in inputs)!=expected: raise ValueError('input changed during review')
report={'status':'rigid_open_surface_screen_not_physical_clearance','input_sha256':expected,'program_sha256':sha(__file__),'numpy_version':np.__version__,'python_fcl_version':importlib.metadata.version('python-fcl'),'samples':240,'axis_hypothesis':'Z through origin','maximum_rotor_radius_source_units':radius,'nearest_phase_motion_bound_source_units':motion,'rounding_margin_source_units':1e-4,'summary':summary,'phases':phases,'fixture_results':controls,'moving_fixture_passed':True,'elapsed_seconds':time.monotonic()-start,'scale_verified':False,'solid_containment_checked':False,'mating_joint_defined':False,'thermal_elastic_clearance_checked':False,'manufacturing_authorized':False}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary))
