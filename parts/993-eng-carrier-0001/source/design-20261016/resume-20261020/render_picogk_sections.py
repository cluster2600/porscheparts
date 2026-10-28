"""Plot actual full-mesh plane intersections for the volumetric branch."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['baseline','before','after','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    def read(path):
        with path.open()as stream:
            nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
        if len(f)!=nf:raise ValueError('All triangles required')
        return v[f]
    def section(t,axis,offset,axes):
        d=t[:,:,axis]-offset;t=t[(d.min(1)<=0)&(d.max(1)>=0)];segments=[]
        for tri in t:
            points=[]
            for i,j in [(0,1),(1,2),(2,0)]:
                x,y=tri[i],tri[j];u=x[axis]-offset;v=y[axis]-offset
                if u==0:points.append(x)
                if u*v<0:points.append(x-u/(v-u)*(y-x))
            if points:
                q=np.unique(points,axis=0)
                if len(q)==2:segments.append(q[:,axes])
                elif len(q)==3:
                    for i,j in [(0,1),(1,2),(2,0)]:segments.append(q[[i,j]][:,axes])
        return np.asarray(segments)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,3,figsize=(16,7),facecolor='#f4f7fb');fig.subplots_adjust(left=.06,right=.97,top=.72,bottom=.25,wspace=.3)
    specs=[(1,0,[0,2],(60,90),(-8,12),'Root profile · Y = 0 mm','X (mm)','Z (mm)'),(2,0,[0,1],(60,90),(-36,-20),'Lateral junction · Z = 0 mm','X (mm)','Y (mm)'),(0,-50,[1,2],(-8.1,-6.9),(3.98,4.12),'Tool-column edge · X = −50 mm','Y (mm)','Z (mm)')]
    counts={}
    for path,label,color,style in [(a.baseline,'Retained baseline','#8b95a5','dashed'),(a.before,'PicoGK + MeshLib','#bd7646','dotted'),(a.after,'After nominal-pad restoration','#237a69','solid')]:
        triangles=read(path)
        for ax,(axis,offset,coordinates,xlim,ylim,title,xlabel,ylabel)in zip(axes,specs):
            lines=section(triangles,axis,offset,coordinates);counts[label+':'+title]=len(lines);ax.add_collection(LineCollection(lines,colors=color,linestyles=style,linewidths=1.5,label=label));ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_xlabel(xlabel);ax.set_ylabel(ylabel);ax.set_title(title,pad=16,fontsize=11);ax.grid(alpha=.15);ax.set_facecolor('#f4f7fb')
    for ax in axes[:2]:ax.set_aspect('equal')
    axes[2].axvline(-7.5,color='#7e8b9e',lw=.8,alpha=.6);axes[2].axhline(4,color='#7e8b9e',lw=.8,alpha=.6)
    axes[0].legend(loc='lower right',frameon=False,fontsize=8)
    fig.text(.06,.91,'993 CARRIER  /  VOLUMETRIC ROUNDING & PAD RESTORATION',fontsize=20,weight='bold',color='#1d334b');fig.text(.06,.83,'PicoGK closing R1 mm · 0.2 mm voxels · MeshLib surface · nominal Z = ±4 mm pad planes',fontsize=12,color='#4c6078');fig.text(.06,.13,'All lines come from actual mesh/plane intersections. The right panel uses different horizontal and vertical scales.',fontsize=11,color='#4c6078');fig.text(.06,.07,'Geometry illustration only. Whole-surface audits, nominal volume gauges and mechanical cases are separate recorded checks.',fontsize=10,color='#4c6078')
    image=a.output/'carrier-picogk-sections.png';fig.savefig(image,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    (a.output/'provenance.json').write_text(json.dumps(dict(source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.baseline,a.before,a.after,Path(__file__)]},figure_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),section_segment_counts=counts,numpy=np.__version__,matplotlib=matplotlib.__version__),indent=2)+'\n')

if __name__=='__main__':main()
