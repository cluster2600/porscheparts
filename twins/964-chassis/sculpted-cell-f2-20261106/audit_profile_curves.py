"""Screen canonical Catmull-Rom profiles before CAD, voxelisation or analysis.

Within-cubic loops are solved algebraically and candidate roots re-evaluated.
Inter-cubic crossings are only a finite polygonal sampling screen, not a
continuous global-curve or complete surface-injectivity proof.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np


def coefficients(points,index,closed):
    p=np.asarray(points,float)
    get=lambda k:p[k%len(p)] if closed else p[min(max(k,0),len(p)-1)]
    p0,p1,p2,p3=[get(index+j-1) for j in range(4)]
    return .5*(-p0+3*p1-3*p2+p3),.5*(2*p0-5*p1+4*p2-p3),.5*(-p0+p2),p1


def cubic_defects(a,b,c,d):
    evaluate=lambda t:((a*t+b)*t+c)*t+d
    solution,_,rank,_=np.linalg.lstsq(np.column_stack([a,b]),-c,rcond=1e-12)
    loops=[];stationary=[]
    if rank==2 and np.linalg.norm(a*solution[0]+b*solution[1]+c)<=1e-9:
        w,u=solution;v=u*u-w;disc=u*u-4*v
        if disc>1e-14:
            s,t=(u-np.sqrt(disc))/2,(u+np.sqrt(disc))/2
            if 1e-10<s<t<1-1e-10:
                residual=float(np.linalg.norm(evaluate(s)-evaluate(t)))
                if residual<=1e-8:
                    loops.append({'parameters':[float(s),float(t)],'point_mm':evaluate(s).tolist(),'position_residual_mm':residual})
    # A zero interior derivative makes this parametrisation nonregular, even
    # when a collinear retracing interval has no rank-two loop solution.
    axis=int(np.argmax(np.abs(3*a)+np.abs(2*b)+np.abs(c)))
    q=np.trim_zeros(np.array([3*a[axis],2*b[axis],c[axis]]),'f')
    for root in np.roots(q) if len(q)>1 else []:
        if abs(root.imag)<1e-10 and 1e-10<root.real<1-1e-10:
            t=float(root.real);residual=float(np.linalg.norm(3*a*t*t+2*b*t+c))
            if residual<=1e-8:stationary.append({'parameter':t,'derivative_norm_mm':residual})
    return loops,stationary


def polygon_screen(points,closed,low,high,density):
    values=[]
    for i in range(low,high):
        a,b,c,d=coefficients(points,i,closed)
        values.extend([((a*t+b)*t+c)*t+d for t in np.linspace(0,1,density,endpoint=False)])
    if not closed:
        a,b,c,d=coefficients(points,high-1,closed);values.append(a+b+c+d)
    values=np.asarray(values);centre=values.mean(axis=0)
    _,_,axes=np.linalg.svd(values-centre,full_matrices=False)
    plane_error=float(np.abs((values-centre)@axes[-1]).max())
    if plane_error>1e-7:return {'skipped_nonplanar_profile':True,'plane_residual_mm':plane_error,'crossings':[],'collinear_overlaps':[]}
    p=(values-centre)@axes[:2].T;q=np.roll(p,-1,axis=0) if closed else p[1:]
    if not closed:p=p[:-1]
    lo=np.minimum(p,q);hi=np.maximum(p,q);crossings=[];overlaps=[]
    cross=lambda x,y:x[...,0]*y[...,1]-x[...,1]*y[...,0]
    for i in range(len(p)):
        ids=np.flatnonzero(np.all(hi[i]>=lo,axis=1)&np.all(hi>=lo[i],axis=1));ids=ids[ids>i+1]
        if closed and i==0:ids=ids[ids<len(p)-1]
        if not len(ids):continue
        a,b=p[i],q[i];cc,dd=p[ids],q[ids];v=b-a
        o1=cross(v,cc-a);o2=cross(v,dd-a);o3=cross(dd-cc,a-cc);o4=cross(dd-cc,b-cc)
        intersects=(o1*o2<-1e-16)&(o3*o4<-1e-16)
        # A sampled crossing can land exactly on a nonadjacent sampled vertex.
        # Those touches must not disappear merely because a strict sign test is zero.
        def on_segment(point,start,end,orientation):
            return ((np.abs(orientation)<=1e-10)&np.all(point>=np.minimum(start,end)-1e-10,axis=-1)
                    &np.all(point<=np.maximum(start,end)+1e-10,axis=-1))
        intersects|=on_segment(cc,a,b,o1)|on_segment(dd,a,b,o2)|on_segment(a,cc,dd,o3)|on_segment(b,cc,dd,o4)
        for j in ids[intersects]:crossings.append([int(i),int(j)])
        if np.linalg.norm(v)>1e-10:
            same=(np.abs(o1)<=1e-10)&(np.abs(o2)<=1e-10)
            for j in ids[same]:
                projection=np.array([np.dot(p[j]-a,v),np.dot(q[j]-a,v)])/np.dot(v,v)
                if min(1,float(projection.max()))-max(0,float(projection.min()))>1e-8:
                    overlaps.append([int(i),int(j)])
    return {'skipped_nonplanar_profile':False,'plane_residual_mm':plane_error,
            'sampled_segments':len(p),'crossings':crossings,'collinear_overlaps':overlaps}


def audit(model,density=8):
    results=[]
    for component in model['components']:
        if component['type']=='planar_profile_cap':
            profiles=[(None,np.asarray(component['profile_mm'],float))];closed=True
        else:
            sections=np.asarray(component['sections_mm'],float);closed=component['closed_profile'];profiles=[]
            for twice_u in range(2*(len(sections)-1)+1):
                u=twice_u/2;i=min(int(u),len(sections)-2);t=u-i
                get=lambda k:sections[min(max(k,0),len(sections)-1)]
                p0,p1,p2,p3=get(i-1),get(i),get(i+1),get(i+2)
                profile=.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                profiles.append((u,profile))
        for u,profile in profiles:
            low,high=component.get('v_range',[0,len(profile) if closed else len(profile)-1]);loops=[];stationary=[]
            for i in range(int(low),int(high)):
                hits,zeros=cubic_defects(*coefficients(profile,i,closed))
                loops.extend([{'segment':i,**h} for h in hits]);stationary.extend([{'segment':i,**h} for h in zeros])
            global_screen=polygon_screen(profile,closed,int(low),int(high),density)
            results.append({'component':component['name'],'u':u,'closed_profile':closed,
                            'within_cubic_loops':loops,'interior_stationary_derivatives':stationary,
                            'finite_global_screen':global_screen,
                            'passed':not loops and not stationary and not global_screen['crossings'] and not global_screen['collinear_overlaps']})
    return {'profile_screen_passed':all(r['passed'] for r in results),'profile_count':len(results),
            'within_cubic_loop_count':sum(len(r['within_cubic_loops']) for r in results),
            'stationary_derivative_count':sum(len(r['interior_stationary_derivatives']) for r in results),
            'sampled_global_crossing_count':sum(len(r['finite_global_screen']['crossings']) for r in results),
            'sampled_collinear_overlap_count':sum(len(r['finite_global_screen']['collinear_overlaps']) for r in results),
            'profiles':results}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output file')
    source=a.model.read_bytes();model=json.loads(source)
    if model['status']!='assumed' or model['units']!='mm':raise ValueError('Expected an assumed millimetre canonical contract')
    result=audit(model)
    result.update(geometry_sha256=hashlib.sha256(source).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  global_sample_density_per_cubic=8,geometry_repaired=False,
                  scope='All canonical profile rows and U midpoints; algebraic within-cubic loops/interior stationary derivatives, finite planar polygon global-crossing screen. Not a continuous global-curve/full-surface-injectivity proof or independent engineering release.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['profile_screen_passed','profile_count','within_cubic_loop_count','stationary_derivative_count','sampled_global_crossing_count','sampled_collinear_overlap_count']}))
    if not result['profile_screen_passed']:raise SystemExit(1)


if __name__=='__main__':main()
