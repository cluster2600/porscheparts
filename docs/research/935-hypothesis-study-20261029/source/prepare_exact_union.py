"""Double-precision fixture surfaces; analytically unite the one coaxial overlap."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import numpy as np

def tube(x,y,levels,n=48):
    angles=np.arange(n)*2*np.pi/n
    v=[[x+r*np.cos(t),y+r*np.sin(t),z] for z,r in levels for t in angles];f=[]
    for ring in range(len(levels)-1):
        for i in range(n):
            a=ring*n+i;b=ring*n+(i+1)%n;f.extend([[a,b,b+n],[a,b+n,a+n]])
    lo=len(v);v.append([x,y,levels[0][0]]);hi=len(v);v.append([x,y,levels[-1][0]])
    for i in range(n):f.extend([[lo,(i+1)%n,i],[hi,(len(levels)-1)*n+i,(len(levels)-1)*n+(i+1)%n]])
    return np.asarray(v,float),np.asarray(f,np.int64)

def off(path,v,f):
    with path.open('x') as s:
        s.write(f'OFF\n{len(v)} {len(f)} 0\n')
        for start in range(0,len(v),10000):s.write(''.join(f'{x:.17g} {y:.17g} {z:.17g}\n' for x,y,z in v[start:start+10000]))
        for start in range(0,len(f),10000):s.write(''.join(f'3 {x} {y} {z}\n' for x,y,z in f[start:start+10000]))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('frame',type=Path);p.add_argument('hypotheses',type=Path);p.add_argument('output',type=Path);p.add_argument('--fixtures-world',action='store_true');a=p.parse_args();a.output.mkdir()
    h=json.loads(a.hypotheses.read_text());frame=np.load(a.frame);offset=np.asarray(h['translation_after_ABC_mm']);d=np.load(a.source)
    off(a.output/'head.off',d['vertices'],d['triangles'])
    axes=defaultdict(list)
    for x,y,lo,hi in h['support_columns']:axes[x,y].append((lo,hi))
    vertices=[];faces=[];index=0;merged=0
    for (x,y),spans in axes.items():
        profiles=[];profile=None;upper=None
        for lo,hi in sorted(spans):
            if profile is not None and lo<upper:
                assert upper-1<lo<upper and hi>upper+1
                radius=1.2-.7*(lo-(upper-1));profile=profile[:-1]+[(lo,radius),(lo,1.2),(hi-1,1.2),(hi,.5)];upper=hi;merged+=1
            else:
                if profile is not None:profiles.append(profile)
                profile=[(lo,1.2),(hi-1,1.2),(hi,.5)];upper=hi
        profiles.append(profile)
        for profile in profiles:
            v,f=tube(x,y,profile);vertices.append(v if a.fixtures_world else (v-offset)@frame);faces.append(f+index);index+=len(v)
    v=np.concatenate(vertices);f=np.concatenate(faces);assert np.all(np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>0)
    off(a.output/'supports.off',v,f);np.savez_compressed(a.output/'supports.npz',vertices=v,triangles=f)
    cube=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    cf=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    plate=cube*np.asarray(h['base_plate_mm']);off(a.output/'plate.off',plate if a.fixtures_world else (plate-offset)@frame,cf)
    x,y,z=h['coupon_centre_mm'];v,f=tube(x,y,[(z-.5,6),(z+20,6)]);off(a.output/'coupon.off',v if a.fixtures_world else (v-offset)@frame,f)
    np.savetxt(a.output/'inverse-frame.txt',np.concatenate([frame.T.ravel(),offset]),fmt='%.17g')
    off(a.output/'control-A.off',cube*2,cf);off(a.output/'control-overlap.off',cube*2+1,cf);off(a.output/'control-contained.off',cube+.5,cf)
    (a.output/'preparation.json').write_text(json.dumps({'coaxial_overlaps_united_analytically':merged,'fixtures_in_world_frame':a.fixtures_world,'coordinate_precision':'float64 before exact rational construction','original_head_coordinates_unchanged':True,'circular_segments':48,'manufacturing_qualified':False},indent=2)+'\n')
    print('Prepared exact Boolean inputs',flush=True)
