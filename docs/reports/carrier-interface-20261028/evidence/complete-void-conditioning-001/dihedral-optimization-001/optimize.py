"""Direct signed-dihedral optimization with projection against original vertices."""
import numpy as np
import jax
jax.config.update('jax_enable_x64', True)
import jax.numpy as j
from scipy.optimize import minimize
CAP=.0049
TARGET=np.deg2rad(42.)

def prepare(v,f,seeds,closed=True):
 ring=np.full(len(v),99,np.int8);ring[np.asarray(seeds,int)]=0
 for depth in range(1,6):
  incident=np.any(ring[f]<depth,axis=1);ids=np.unique(f[incident]);ring[ids]=np.minimum(ring[ids],depth)
 moving=ring<4;patch=f[np.any(ring[f]<=4,axis=1)][:,[0,2,1]]
 ids=np.unique(patch);rev=np.full(len(v),-1,np.int64);rev[ids]=np.arange(len(ids));faces=rev[patch];move=np.flatnonzero(moving[ids])
 directed=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);keys=np.sort(directed,axis=1);order=np.lexsort((keys[:,1],keys[:,0]));keys=keys[order];starts=np.r_[0,np.flatnonzero(np.any(keys[1:]!=keys[:-1],axis=1))+1,len(keys)];counts=np.diff(starts);assert np.all((counts==1)|(counts==2));starts=starts[:-1][counts==2];pairs=np.stack([order[starts],order[starts+1]],axis=1);edge=directed[pairs[:,0]];assert np.array_equal(edge,directed[pairs[:,1]][:,::-1]);neighbors=pairs%len(faces)
 # Every edge of every changed face has both incident faces in this patch.
 paired_counts=np.bincount((pairs%len(faces)).reshape(-1),minlength=len(faces));affected=np.any(np.isin(faces,move),axis=1)
 if closed:assert np.all(paired_counts[affected]==3)
 original=v[ids];raw=np.cross(original[faces[:,1]]-original[faces[:,0]],original[faces[:,2]]-original[faces[:,0]]);area=np.linalg.norm(raw,axis=1);assert np.all(area>0)
 p0=j.asarray(original);ff=j.asarray(faces);ee=j.asarray(edge);nn=j.asarray(neighbors);mm=j.asarray(move);aa=j.asarray(area);normal0=j.asarray(raw/area[:,None])
 def positions(x):
  d=x.reshape(-1,3);d=d/j.maximum(1.,j.sqrt(j.sum(d*d,axis=1)+1e-24))[:,None]
  return p0.at[mm].add(CAP*d),d
 def geometry(x):
  p,d=positions(x);t=p[ff];raw=j.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);size=j.sqrt(j.sum(raw*raw,axis=1)+1e-40);normal=raw/size[:,None];a=normal[nn[:,0]];b=normal[nn[:,1]];delta=p[ee[:,1]]-p[ee[:,0]];unit=delta/j.sqrt(j.sum(delta*delta,axis=1)+1e-40)[:,None];sine=j.sum(unit*j.cross(a,b),axis=1);cosine=j.sum(a*b,axis=1);angle=j.arctan2(sine,cosine)
  return angle,size/aa,j.sum(raw*normal0,axis=1)/aa,d
 def loss(x):
  angle,ratio,alignment,d=geometry(x)
  return j.sum(j.maximum(-angle-TARGET,0.)**2)+100.*j.sum(j.maximum(.2-ratio,0.)**2+j.maximum(.2-alignment,0.)**2)+1e-7*j.sum(d*d)
 value_gradient=jax.jit(jax.value_and_grad(loss));inspect=jax.jit(geometry);position=jax.jit(positions)
 return ids,move,faces,ids[edge],value_gradient,inspect,position

def optimize(v,f,seeds,closed=True):
 ids,move,faces,edges,value_gradient,inspect,position=prepare(v,f,seeds,closed=closed);x=np.zeros(len(move)*3);initial=np.asarray(inspect(x)[0]);history=[]
 def fun(x):
  value,gradient=value_gradient(x);value=float(value);gradient=np.asarray(gradient,dtype=float);assert np.isfinite(value)and np.isfinite(gradient).all();return value,gradient
 # Independent centered directional-difference check at the actual input.
 rng=np.random.default_rng(993);direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);eps=1e-5;value,gradient=fun(x);finite=(fun(x+eps*direction)[0]-fun(x-eps*direction)[0])/(2*eps);automatic=float(gradient@direction);assert abs(finite-automatic)<1e-6*max(1.,abs(finite),abs(automatic)),(finite,automatic)
 def callback(x):
  a=np.asarray(inspect(x)[0]);history.append(dict(iteration=len(history)+1,maximum_reentrant_degrees=float(-np.degrees(a.min())),edges_above45=int((a<-np.pi/4).sum())))
 result=minimize(fun,x,jac=True,method='L-BFGS-B',bounds=[(-2.,2.)]*len(x),callback=callback,options=dict(maxiter=400,maxls=40,maxcor=20,ftol=1e-15,gtol=1e-10));p=np.asarray(position(result.x)[0]);angles,ratio,alignment,_=inspect(result.x);assert np.min(ratio)>.15 and np.min(alignment)>.15
 new=v.copy();new[ids]=p
 return new,dict(method='JAX float64 signed-dihedral objective / SciPy L-BFGS-B / original-reference Euclidean projection',author_cap_mm=CAP,target_degrees=42,patch_vertices=len(ids),optimized_vertices=len(move),patch_faces=len(faces),initial_patch_edges_above45=int((initial<-np.pi/4).sum()),initial_patch_maximum_degrees=float(-np.degrees(initial.min())),final_patch_edges_above45=int((np.asarray(angles)<-np.pi/4).sum()),final_patch_maximum_degrees=float(-np.degrees(np.min(angles))),minimum_face_area_ratio=float(np.min(ratio)),minimum_original_normal_projection_ratio=float(np.min(alignment)),gradient_control=dict(centered_finite_difference=finite,automatic_directional_derivative=automatic),optimizer_success=bool(result.success),optimizer_message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev),history=history)
