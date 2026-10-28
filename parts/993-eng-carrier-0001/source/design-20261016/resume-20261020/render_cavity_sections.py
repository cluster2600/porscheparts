"""Compare actual STL/indexed-surface sections; plotting is not a fit proof."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--radius-proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    def read(path):
        with path.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=int)
        return v[f]
    def section(t,axis,coordinates):
        d=t[:,:,axis];hit=t[(d.min(axis=1)<=0)&(d.max(axis=1)>=0)];segments=[]
        for tri in hit:
            points=[]
            for i,j in [(0,1),(1,2),(2,0)]:
                x,y=tri[i],tri[j]
                if x[axis]==0:points.append(x)
                if x[axis]*y[axis]<0:points.append(x-x[axis]/(y[axis]-x[axis])*(y-x))
            if not points:continue
            points=np.unique(points,axis=0)
            if len(points)==2:segments.append(points[:,coordinates])
            elif len(points)==3:
                for i,j in [(0,1),(1,2),(2,0)]:segments.append(points[[i,j]][:,coordinates])
        return np.asarray(segments)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(14,7),facecolor='#f4f7fb');fig.subplots_adjust(left=.07,right=.97,top=.70,bottom=.23,wspace=.25);counts={}
    for path,label,color,style in [(a.baseline,'Retained baseline','#7e8a9a','dashed'),(a.candidate,'Rounded cavity study','#247a65','solid')]:
        triangles=read(path)
        for ax,axis,coordinates,title,limits,ylabel in [(axes[0],1,[0,2],'Cavity end · XZ section at Y = 0 mm',[(63,82),(-6,8)],'Z (mm)'),(axes[1],2,[0,1],'Side junction · XY section at Z = 0 mm',[(63,82),(-36,-20)],'Y (mm)')]:
            lines=section(triangles,axis,coordinates);counts[label+':'+title]=len(lines);ax.add_collection(LineCollection(lines,colors=color,linestyles=style,linewidths=1.6,label=label));ax.set_xlim(*limits[0]);ax.set_ylim(*limits[1]);ax.set_aspect('equal');ax.set_xlabel('X (mm)');ax.set_ylabel(ylabel);ax.set_title(title,fontsize=12,pad=16);ax.grid(alpha=.14);ax.set_facecolor('#f4f7fb')
    axes[0].legend(loc='lower right',frameon=False,fontsize=10)
    axes[1].plot(70.0043161383,-24.494259132,'o',mfc='none',mec='#b95237',ms=10,mew=1.8);axes[1].annotate('Coarse hotspot projected into XY',(70.0043161383,-24.494259132),xytext=(66,-22),fontsize=9,color='#a14935',arrowprops=dict(arrowstyle='->',color='#a14935'))
    data=json.loads(a.radius_proof.read_text());radius=data['maximum_complete_radial_deviation_mm_float']
    fig.text(.07,.91,'993 CARRIER  /  CAVITY-END REDESIGN',fontsize=21,weight='bold',color='#1d334b');fig.text(.07,.83,'Native mass 1.277797 kg · R0.6 floor arcs · lateral junction remains under investigation',fontsize=12,color='#4c6078');fig.text(.07,.12,f'Complete native radial certificate: R0.6 mm with deviation ≤ {radius:.3g} mm on all four floor-arc faces.',fontsize=11,color='#247a65');fig.text(.07,.065,'Lines are actual mesh/plane intersections. Zooms illustrate geometry; the CAD certificate and mechanical screens are separate.',fontsize=10,color='#4c6078')
    target=a.output/'carrier-cavity-sections.png';fig.savefig(target,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    (a.output/'provenance.json').write_text(json.dumps(dict(source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.baseline,a.candidate,a.radius_proof,Path(__file__)]},figure_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),section_segment_counts=counts,numpy=np.__version__,matplotlib=matplotlib.__version__,scope='Actual sectional geometry illustration, not a complete distance or strength proof'),indent=2)+'\n')

if __name__=='__main__':main()
