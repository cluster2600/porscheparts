"""Render the actual exported boundary and an actual C3D4 mesh section."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--boundary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    with np.load(a.mesh,allow_pickle=False)as data:v=data['vertices'];cells=data['tetrahedra']
    with a.boundary.open()as stream:nv,nf=map(int,stream.readline().split());bv=np.loadtxt(stream,max_rows=nv);bf=np.loadtxt(stream,dtype=int)
    t=bv[bf];horizontal=np.array([1.,.12,0]);horizontal/=np.linalg.norm(horizontal);vertical=np.cross(np.array([.2,-.6,.77]),horizontal);vertical/=np.linalg.norm(vertical);depth=np.cross(horizontal,vertical)
    projected=np.stack([t@horizontal,t@vertical],axis=-1);normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None];colors=(.35+.6*np.abs(normal@np.array([.15,-.6,.78])))[:,None]*np.array([.27,.39,.53]);order=np.argsort((t@depth).mean(axis=1))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(15,6.8),facecolor='#f4f7fb');left=fig.add_axes([.045,.20,.58,.54],facecolor='#f4f7fb');right=fig.add_axes([.70,.22,.27,.52],facecolor='#f4f7fb')
    left.add_collection(PolyCollection(projected[order],facecolors=colors[order],edgecolors='#405870',linewidths=.12));left.autoscale_view();left.set_aspect('equal');left.axis('off')
    plane=82.5;xyz=v[cells];selected=cells[(xyz[:,:,0].min(axis=1)<plane)&(xyz[:,:,0].max(axis=1)>plane)];polygons=[]
    for cell in selected:
        points=v[cell];section=[p[1:]for p in points if p[0]==plane]
        for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
            a0,b0=points[i],points[j]
            if(a0[0]-plane)*(b0[0]-plane)<0:section.append((a0+(plane-a0[0])/(b0[0]-a0[0])*(b0-a0))[1:])
        section=np.unique(section,axis=0)
        if len(section)>=3:
            center=section.mean(axis=0);order=np.argsort(np.arctan2(section[:,1]-center[1],section[:,0]-center[0]));polygons.append(section[order])
    right.add_collection(PolyCollection(polygons,facecolors='#c3e1d8',edgecolors='#316958',linewidths=.45));right.autoscale_view();right.set_aspect('equal');right.set_xlabel('Y (mm)');right.set_ylabel('Z (mm)');right.set_title('Actual tetrahedron intersections\nSection at X = 82.5 mm',loc='left',fontsize=11,color='#1d334b',pad=15)
    fig.text(.045,.91,'993 CARRIER  /  PRESERVED-BOUNDARY MESH',fontsize=19,weight='bold',color='#1d334b');fig.text(.045,.84,f'{len(v):,} nodes   ·   {len(cells):,} C3D4 elements   ·   {nf:,} boundary triangles',fontsize=13,color='#4c6078')
    fig.text(.045,.12,'All exported boundary triangles shown. The section cuts actual tetrahedra; it is not a stress plot.',fontsize=10,color='#4c6078');fig.text(.045,.065,'TetGen pYMQ · exact input boundary retained · new mechanical cases and refinement remain open',fontsize=10,color='#4c6078')
    target=a.output/'carrier-volume-checkpoint.png';fig.savefig(target,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    (a.output/'volume-figure-provenance.json').write_text(json.dumps(dict(input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.mesh,a.boundary,Path(__file__)]},output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),versions=dict(numpy=np.__version__,matplotlib=matplotlib.__version__),section_plane_X_mm=plane,section_polygons=len(polygons),purpose='Actual numerical mesh illustration; not a stress or strength result'),indent=2)+'\n')

if __name__=='__main__':main()
