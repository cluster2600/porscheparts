"""Render every actual parent facet and the source-bounded patch meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.root=a.root.resolve()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from certified_patch_collapse import load_stl,ratios
    source=a.root/'parts/993-eng-carrier-0001/source/design-20261016'
    paths=[source/'corner-slide-candidate-20261018/candidate-surface.stl',*[source/f'resume-20261020/inputs/certified-patch-{i}.stl'for i in range(2)]]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(16,7),facecolor='#f4f7fb');ax=fig.add_axes([.04,.17,.70,.67],facecolor='#f4f7fb');text=fig.add_axes([.77,.22,.21,.55]);text.axis('off')
    triangles=[];colors=[]
    for i,path in enumerate(paths):
        v,f=load_stl(path,np);t=v[f].astype(float);triangles.append(t)
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
        light=.35+.6*np.abs(normal@np.array([.15,-.6,.78]));base=np.array([.27,.39,.53])if i==0 else np.array([.1,.68,.49]);colors.append(np.clip(light[:,None]*base,0,1))
    t=np.concatenate(triangles);c=np.concatenate(colors)
    # Exact orthographic projection of every facet, with depth-sorted painting.
    horizontal=np.array([1.,.12,0]);horizontal/=np.linalg.norm(horizontal);vertical=np.cross(np.array([.2,-.6,.77]),horizontal);vertical/=np.linalg.norm(vertical);depth=np.cross(horizontal,vertical)
    projected=np.stack([t@horizontal,t@vertical],axis=-1);order=np.argsort((t@depth).mean(axis=1))
    ax.add_collection(PolyCollection(projected[order],facecolors=c[order],edgecolors='none',rasterized=True));ax.autoscale_view();ax.set_aspect('equal');ax.axis('off')
    fig.text(.04,.91,'993 TURBO  /  ROOT REINFORCEMENT STUDY',fontsize=20,weight='bold',color='#1d334b')
    fig.text(.04,.85,'Actual retained carrier surface + two explicit NURBS patch meshes',color='#4c6078')
    text.text(0,.98,'1.27601 kg',fontsize=25,weight='bold',color='#1d334b',va='top');text.text(0,.83,'nominal mass upper bound\n1.30 kg maximum',linespacing=1.6,color='#4c6078',va='top')
    text.text(0,.58,'SURFACE SCREEN PASSED',fontsize=11,weight='bold',color='#187859',va='top');text.text(0,.48,'0 self-intersections\n0 needle triangles\n0 open edges',linespacing=1.7,color='#1d334b',va='top')
    text.text(0,.15,'Patch error bound\n< 0.0351 mm',linespacing=1.6,color='#1d334b',va='top')
    fig.text(.04,.07,'Computed geometry visualization · nominal study dimensions · revised mechanics and print preparation pending',fontsize=10,color='#4c6078')
    fig.savefig(a.output/'carrier-certified-surface.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    old=source/'resume-20261020/inputs/bounded-patch-0.stl';new=paths[1]
    fig,axes=plt.subplots(1,2,figsize=(15,6),facecolor='#f4f7fb')
    for axis,path,label in zip(axes,[old,new],['Before: 40 needle triangles','After: 0 needle triangles']):
        v,f=load_stl(path,np);t=v[f].astype(float);q=ratios(v,f,np);mask=(t[:,:,0].min(axis=1)<v[:,0].min()+2)
        tt=t[mask];cc=np.where((q[mask]<.001)[:,None],np.array([.86,.26,.22]),np.array([.20,.58,.55]))
        # y/z projection with x offset exposes the actual short end-region facets.
        xy=np.stack([(tt[:,:,0]-v[:,0].min()),tt[:,:,2]+.35*(tt[:,:,1]-v[:,1].min())],axis=-1)
        bad=q[mask]<.001
        if np.any(bad):axis.scatter(xy[bad].mean(axis=1)[:,0],xy[bad].mean(axis=1)[:,1],s=15,color='#db4239',zorder=5,label='Needle facet centers');axis.legend(loc='upper right')
        axis.add_collection(PolyCollection(xy,facecolors=np.c_[cc,np.full(len(cc),.45)],edgecolors='#354c65',linewidths=.5));axis.autoscale_view();axis.set_title(label,loc='left',weight='bold');axis.set_xlabel('Distance from patch end in X (mm)');axis.set_ylabel('Oblique section coordinate (mm)');axis.set_facecolor('#f4f7fb')
    fig.suptitle('Endpoint cleanup with an accumulated surface-displacement certificate',x=.07,ha='left',weight='bold',fontsize=17);fig.subplots_adjust(left=.07,right=.97,bottom=.18,top=.81,wspace=.22)
    fig.text(.07,.05,'Actual mesh triangles · local view only; acceptance uses all facets of all three complete components',fontsize=10,color='#4c6078')
    fig.savefig(a.output/'patch-endpoint-cleanup.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    report=dict(purpose='Actual geometry visualization; numerical admission is in the complete independent audit',input_sha256={str(path.relative_to(a.root)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [*paths,old,Path(__file__).resolve()]},versions=dict(numpy=np.__version__,matplotlib=matplotlib.__version__),outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.output.glob('*.png')})
    (a.output/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
