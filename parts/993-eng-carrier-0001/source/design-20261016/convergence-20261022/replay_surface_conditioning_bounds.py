"""Independently replay local edits and exact rational surface-change bounds.

A flip between convex projected graphs has its largest height difference at
its diagonal intersection. A general cap flip also admits H <= 2*L1(C-P),
where P lies on the shared edge: flattening C to P makes the triangulations
identical. An edge collapse moves each incident triangle by at most L1(u-v);
its deleted triangle images must remain covered by surviving edges.

All edits must stay inside one of four fixed open XY quadrants. The complete
surface is the union of these patches and an unchanged outside patch. Thus
the whole-surface bound is the largest regional sum, not the sum across
independent regions. This is geometry evidence, not a mechanical assessment.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(test,message):
    if not test:raise ValueError(message)
def ratio(pair):return Fraction(int(pair[0]),int(pair[1]))
def rational_points(points):return [[Fraction(float(x))for x in row]for row in points]
def cross(a,b):return a[0]*b[1]-a[1]*b[0]


def convex_flip_bound(points,drop):
    require(drop in (0,1,2),'Invalid projection axis');axis=[k for k in range(3)if k!=drop];a,b,c,d=rational_points(points);ab=[b[k]-a[k]for k in axis];cd=[d[k]-c[k]for k in axis];ac=[c[k]-a[k]for k in axis];den=cross(ab,cd);require(den!=0,'Parallel projected diagonals');t=cross(ac,cd)/den;u=cross(ac,ab)/den;require(0<t<1 and 0<u<1,'Projected quadrilateral is not strictly convex');bound=abs(a[drop]+t*(b[drop]-a[drop])-c[drop]-u*(d[drop]-c[drop]));return bound,t,u


def cap_flip_bound(points,cap):
    require(cap in (2,3),'Invalid cap point');q=rational_points(points);a,b=q[:2];c=q[cap];ab=[b[k]-a[k]for k in range(3)];den=sum(x*x for x in ab);require(den>0,'Zero shared edge');t=max(Fraction(0),min(Fraction(1),sum((c[k]-a[k])*ab[k]for k in range(3))/den));return 2*sum(abs(c[k]-a[k]-t*ab[k])for k in range(3)),t


def quadrant(points):
    signs=[]
    for k in (0,1):
        column=points[:,k]
        if np.all(column>0):signs.append(1)
        elif np.all(column<0):signs.append(0)
        else:raise ValueError('Edit crosses a fixed regional boundary')
    return 2*signs[0]+signs[1]


def region_roster(vertices,faces):
    t=vertices[faces];lo=t.min(1);hi=t.max(1);r=np.full(len(faces),-1,dtype=np.int8);valid=((lo[:,0]>0)|(hi[:,0]<0))&((lo[:,1]>0)|(hi[:,1]<0));r[valid]=(2*(lo[valid,0]>0)+(lo[valid,1]>0)).astype(np.int8);return r


def protected_roster(vertices,faces):
    t=vertices[faces];lo=t.min(1);hi=t.max(1);result=np.zeros(len(faces),bool)
    for lower,upper in [([-65,-100,-100],[65,100,100]),([-400,-100,-100],[-260,100,100]),([260,-100,-100],[400,100,100])]:result|=((hi>=lower)&(lo<=upper)).all(1)
    return result


def upper_float(value):
    answer=float(value)
    return math.nextafter(answer,math.inf)if Fraction(answer)<value else answer


def geometry_signature(vertices,faces):
    return dict(vertices_f64_le=hashlib.sha256(np.asarray(vertices,dtype="<f8").tobytes()).hexdigest(),triangles_u64_le=hashlib.sha256(np.asarray(faces,dtype="<u8").tobytes()).hexdigest())


def replay(reference,recipe,output_surface=None):
    inputs={str(reference):sha(reference)};z=np.load(reference,allow_pickle=False);v=z['vertices'].copy();f=z['triangles'].copy();require(v.ndim==2 and v.shape[1]==3 and np.isfinite(v).all(),'Finite source vertices required');require(f.ndim==2 and f.shape[1]==3 and f.dtype.kind in 'iu'and f.min()>=0 and f.max()<len(v),'Bounded source triangle indices required');regions=region_roster(v,f);protected=protected_roster(v,f);sums=[Fraction(0)for _ in range(4)];stages=[]
    for stage in recipe['stages']:
        path=Path(stage['ledger']);inputs[str(path)]=sha(path);ledger=json.loads(path.read_text());active=np.ones(len(f),bool);count=0;stage_total=Fraction(0)
        for operation in ledger['operations']:
            if stage['kind']=='edge_flip':
                i,j=map(int,operation['face_indices']);require(0<=i<len(f)and 0<=j<len(f)and i!=j and active[i]and active[j],'Invalid flip face indices');require(not protected[[i,j]].any(),'Flip changes a protected face');require(np.array_equal(f[[i,j]],operation['old_triangles']),'Flip input faces differ');a,b,c,d=map(int,operation['diagonal_vertex_indices']);require(len({a,b,c,d})==4 and min(a,b,c,d)>=0 and max(a,b,c,d)<len(v),'Invalid flip vertex roster');require(any(np.array_equal(np.roll(f[i],k),[a,b,c])for k in range(3))and any(np.array_equal(np.roll(f[j],k),[b,a,d])for k in range(3)),'Flip lacks oriented opposite edge pairing');proposed=np.asarray([[c,d,b],[d,c,a]],dtype=f.dtype);require(np.array_equal(proposed,operation['new_triangles']),'Flip output faces differ');points=v[[a,b,c,d]];region=quadrant(points);require(regions[i]==region and regions[j]==region,'Flip leaves its original regional patch');method=operation.get('bound_method','convex_overlay')
                if method=='convex_overlay':
                    bound,t,u=convex_flip_bound(points,int(operation['projection_drop_axis']));require(t==ratio(operation.get('bound_t',operation.get('intersection_t')))and u==ratio(operation.get('bound_u',operation.get('intersection_u'))),'Convex overlay intersection differs')
                elif method=='twice_cap_to_shared_edge_L1':
                    bound,t=cap_flip_bound(points,int(operation['cap_point_local_index']));require(t==ratio(operation['bound_t'])and operation['bound_u']is None,'Cap projection differs')
                else:raise ValueError('Unknown flip bound method')
                require(bound==Fraction(int(operation['gap_numerator']),int(operation['gap_denominator'])),'Flip displacement bound differs');f[[i,j]]=proposed
            elif stage['kind']=='edge_collapse':
                u,keep=int(operation['removed_vertex']),int(operation['retained_vertex']);require(0<=u<len(v)and 0<=keep<len(v)and u!=keep,'Invalid collapse vertex indices');iu=np.flatnonzero(active&np.any(f==u,1));iv=np.flatnonzero(active&np.any(f==keep,1));require(len(iu)>0 and len(iv)>0 and not protected[iu].any(),'Collapse changes a protected or absent vertex');rows=np.union1d(iu,iv);require(np.array_equal(rows,operation['affected_face_indices']),'Collapse incident face roster differs');region=quadrant(v[f[rows]].reshape(-1,3));require(np.all(regions[rows]==region),'Collapse leaves its original regional patch');edge=np.intersect1d(iu,iv);require(len(edge)==2,'Collapse edge is not paired');nu=set(map(int,f[iu].flat))-{u,keep};nk=set(map(int,f[iv].flat))-{u,keep};opposite=set(map(int,f[edge].flat))-{u,keep};require(len(opposite)==2 and nu&nk==opposite,'Collapse link condition failed');mapped=f[rows].copy();mapped[mapped==u]=keep;valid=(mapped[:,0]!=mapped[:,1])&(mapped[:,0]!=mapped[:,2])&(mapped[:,1]!=mapped[:,2]);require(int((~valid).sum())==2 and np.array_equal(rows[~valid],operation['deleted_face_indices']),'Deleted collapse face roster differs');survivor=mapped[valid];keys=[tuple(sorted(map(int,row)))for row in survivor];require(len(keys)==len(set(keys)),'Collapse creates duplicate faces');edges={tuple(sorted((int(row[k]),int(row[(k+1)%3]))))for row in survivor for k in range(3)};segments=[tuple(sorted(set(map(int,row))))for row in mapped[~valid]];require(all(len(segment)==2 and segment in edges for segment in segments),'Deleted triangle image is not covered');require([list(x)for x in segments]==operation['deleted_triangle_image_segments'],'Deleted triangle image receipt differs');bound=sum(abs(Fraction(float(x))-Fraction(float(y)))for x,y in zip(v[u],v[keep]));require(bound==Fraction(int(operation['l1_bound_numerator']),int(operation['l1_bound_denominator'])),'Collapse L1 bound differs');f[rows]=mapped;active[rows[~valid]]=False
            else:raise ValueError('Unknown conditioning stage')
            sums[region]+=bound;stage_total+=bound;count+=1
        require(stage_total==Fraction(int(ledger['total_bound_numerator']),int(ledger['total_bound_denominator'])),'Stage total bound differs')
        if stage['kind']=='edge_collapse':
            used=np.unique(f[active]);v=v[used];f=np.searchsorted(used,f[active]).astype(np.int32);regions=regions[active];protected=protected[active]
        signature=geometry_signature(v,f)
        if 'geometry_sha256'in stage:require(signature==stage['geometry_sha256'],'Complete stage geometry signature differs')
        if 'candidate'in stage:
            target=Path(stage['candidate']);inputs[str(target)]=sha(target);candidate=np.load(target,allow_pickle=False);require(np.array_equal(v,candidate['vertices'])and np.array_equal(f,candidate['triangles']),'Complete stage output differs from independent replay');candidate_sha=sha(target)
        else:
            require('geometry_sha256'in stage,'Portable replay requires complete stage geometry signatures');candidate_sha=stage.get('source_npz_sha256')
        stages.append(dict(kind=stage['kind'],operations=count,sequential_bound_mm=upper_float(stage_total),candidate_sha256=candidate_sha,geometry_sha256=signature))
    if output_surface is not None:np.savez_compressed(output_surface,vertices=v,triangles=f)
    return dict(status='exact_regional_conditioning_bounds_replayed',stages=stages,regional_bounds_mm=[upper_float(x)for x in sums],whole_surface_additional_change_upper_mm=upper_float(max(sums)),global_sum_for_comparison_mm=upper_float(sum(sums)),whole_surface_additional_bound_exact=dict(numerator=str(max(sums).numerator),denominator=str(max(sums).denominator)),input_sha256=inputs,source_sha256=sha(Path(__file__)),manufacturing_authorized=False)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--maximum-change-mm',default='0.007');p.add_argument('--output',type=Path,required=True);a=p.parse_args();require(not a.output.exists(),'Fresh output required');a.output.mkdir(parents=True);limit=Fraction(a.maximum_change_mm);require(0<limit<=Fraction(1,100),'Additional change limit must be positive and at most 0.01 mm');r=replay(a.reference,json.loads(a.recipe.read_text()),a.output/'candidate.npz');r['input_sha256'][str(a.recipe)]=sha(a.recipe);bound=r['whole_surface_additional_bound_exact'];require(Fraction(int(bound['numerator']),int(bound['denominator']))<=limit,'Regional surface-change limit exceeded');r['maximum_additional_change_mm']=float(limit);(a.output/'assessment.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='input_sha256'}))

if __name__=='__main__':main()
