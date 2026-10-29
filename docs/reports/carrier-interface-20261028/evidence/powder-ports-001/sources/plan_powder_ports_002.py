"""Search tapered escape routes; numerical candidates, not admitted manufacturing geometry."""
import hashlib,json,math,signal,time,gzip,io
from pathlib import Path
import numpy as np
import igl
w=Path('work/carrier-interface-20261028');out=w/'powder-port-routing-002';assert not out.exists();out.mkdir();signal.alarm(240);start=time.monotonic();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
body_path=w/'full-reconstructed-p10-001/candidate.npz';assert sha(body_path)=='93f14193e5135e644f920071c2b9da417ffe4b1efa60563be980d73d2d028f3b';body=np.load(body_path);low=body['vertices'].min(0);high=body['vertices'].max(0)
params=dict(grid_mm=.5,maximum_centres=128,retained_routes_per_network=24,axis_sampling_step_mm=.25,neck_inscribed_radius_mm=.75,mouth_inscribed_radius_mm=1.5,polygon_sides=64,hard_minimum_ligament_mm=1.,planning_clearance_mm=1.15,numerical_distance_reserve_mm=.0001,minimum_abs_axis_x_mm=68.5,maximum_axis_length_mm=40.,central_protected_box_mm=[[-65,-36,-4],[65,36,4]],flare_parent_boundary_reserve_mm=.1,manufacturing_authorized=False)
paths=[];data=[];inputs={str(body_path):sha(body_path)}
for rank in range(4):
 for sign in ['positive','negative']:
  path=w/('meshlib-seed-p10-r'+str(rank)+'-h0125-004')/(sign+'.npz');z=np.load(path);data.append((z['vertices'],z['triangles'].astype(np.int64)));paths.append(path);inputs[str(path)]=sha(path)
reference=Path('parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/picogk-R2-study/surface.mesh64.gz');raw=gzip.decompress(reference.read_bytes());assert hashlib.sha256(raw).hexdigest()=='396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0'
with io.StringIO(raw.decode())as stream:
 nv,nf=map(int,stream.readline().split());pv=np.loadtxt(stream,max_rows=nv);pf=np.loadtxt(stream,dtype=np.int64)
parent_tree=igl.AABB();parent_tree.init(pv,pf);inputs[str(reference)]=sha(reference)
for p in [Path('parts/993-eng-carrier-0001/source/design-20261016/inspect_protected.py'),Path('parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013/interface-study.json')]:inputs[str(p)]=sha(p)
(out/'contract.json').write_text(json.dumps(dict(parameters=params,input_sha256=inputs,source_sha256=sha(Path(__file__)),scope=__doc__),indent=2)+'\n')
inner=params['neck_inscribed_radius_mm']/math.cos(math.pi/params['polygon_sides']);outer=params['mouth_inscribed_radius_mm']/math.cos(math.pi/params['polygon_sides']);routes=[];summaries=[]
for index,(v,f)in enumerate(data):
 axes=[np.arange(a+.25,b,.5)for a,b in zip(v.min(0),v.max(0))];q=np.stack(np.meshgrid(*axes,indexing='ij'),axis=-1).reshape(-1,3);assert len(q)<500000
 inside=q[np.abs(igl.fast_winding_number(v,f,q))>.9];d,_,_=igl.point_mesh_squared_distance(inside,v,f);r=np.sqrt(np.maximum(0,d));eligible=(r>=inner+.025)&(abs(inside[:,0])>=params['minimum_abs_axis_x_mm']);points=inside[eligible];r=r[eligible];points=points[np.argsort(-r)[:params['maximum_centres']]]
 ov=[];of=[];offset=0
 for j,(vv,ff)in enumerate(data):
  if j==index:continue
  ov.append(vv);of.append(ff+offset);offset+=len(vv)
 ov=np.vstack(ov);of=np.vstack(of);tree=igl.AABB();tree.init(ov,of);candidates=[];outward=1 if v[:,1].mean()>0 else-1
 parent_d,_,_=parent_tree.squared_distance(pv,pf,points);parent_d=np.sqrt(np.maximum(0,parent_d))
 for centre,parent_radius in zip(points,parent_d):
  if parent_radius<=outer+params['flare_parent_boundary_reserve_mm']:continue
  maximum_flare=math.sqrt((parent_radius-params['flare_parent_boundary_reserve_mm'])**2-outer**2)
  for axis,direction in [(1,outward),(2,-1),(2,1)]:
   end=centre.copy();end[axis]=(high[axis]+2)if direction>0 else(low[axis]-2);length=float(np.linalg.norm(end-centre))
   if length>params['maximum_axis_length_mm']:continue
   n=int(math.ceil(length/params['axis_sampling_step_mm']))+1;t=np.linspace(0,1,n);line=centre[None,:]+t[:,None]*(end-centre);flare=min(maximum_flare,length-.5);radius=inner+np.minimum(1,t*length/flare)*(outer-inner);d,_,_=tree.squared_distance(ov,of,line);distance=np.sqrt(np.maximum(0,d));step=length/(n-1);slope=(outer-inner)/flare;bound=float(np.min(distance-radius)-(1+slope)*step/2-params['numerical_distance_reserve_mm'])
   if bound>=params['planning_clearance_mm']:candidates.append(dict(network=index,rank=index//2,sign='positive'if index%2==0 else'negative',axis=axis,direction=direction,start_mm=centre.tolist(),end_mm=end.tolist(),length_mm=length,flare_length_mm=flare,numerical_parent_free_ball_radius_mm=float(parent_radius),numerical_other_network_ligament_lower_mm=bound,line=line,radii=radius,step=step,slope=slope))
 candidates.sort(key=lambda r:(r['length_mm'],-r['numerical_other_network_ligament_lower_mm']));candidates=candidates[:params['retained_routes_per_network']];routes.append(candidates);summaries.append(dict(index=index,rank=index//2,sign='positive'if index%2==0 else'negative',eligible_centres=len(points),retained_safe_route_candidates=len(candidates)));print(json.dumps(summaries[-1]),flush=True)
selected=[];pair_results=[]
for rank in range(4):
 best=None
 for a in routes[2*rank]:
  for b in routes[2*rank+1]:
   separation=np.linalg.norm(a['line'][:,None,:]-b['line'][None,:,:],axis=2)-a['radii'][:,None]-b['radii'][None,:]
   lower=float(separation.min()-(1+a['slope'])*a['step']/2-(1+b['slope'])*b['step']/2-params['numerical_distance_reserve_mm'])
   if lower<params['planning_clearance_mm']:continue
   cost=a['length_mm']+b['length_mm']
   if best is None or cost<best[0]:best=(cost,a,b,lower)
 pair_results.append(dict(rank=rank,compatible_pair_found=best is not None,port_to_port_ligament_lower_mm=best[3]if best else None))
 if best:
  for r in best[1:3]:selected.append({k:v for k,v in r.items()if k not in ['line','radii','step','slope']})
report=dict(status='numerical_tapered_port_route_candidates_assessed',networks=summaries,pairs=pair_results,selected=selected,all_eight_routes_found=len(selected)==8,inside_classification='Fast winding candidate filter only; selected centres need independent bounded-side checks',continuous_axis_bound='Distance to closed surface is 1-Lipschitz; subtract radius slope and half-step sampling radius',formal_interval_certificate=False,independent_exact_clearance_checked=False,geometry_generated=False,manufacturing_authorized=False,elapsed_seconds=time.monotonic()-start);(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(dict(all_eight_routes_found=report['all_eight_routes_found'],pairs=pair_results)))
