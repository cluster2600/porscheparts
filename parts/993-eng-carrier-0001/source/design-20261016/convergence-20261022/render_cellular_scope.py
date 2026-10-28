"""Actual R2 material sections for scoping cellular replacement, not a lattice render."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    raw=gzip.decompress(args.reference.read_bytes());digest=hashlib.sha256(raw).hexdigest()
    if digest!='396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0':raise ValueError('Retained complete R2 surface required')
    with io.StringIO(raw.decode())as stream:
        nv,nf=map(int,stream.readline().split());vertices=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int64)
    if vertices.shape!=(nv,3)or faces.shape!=(nf,3):raise ValueError('Complete input counts required')
    triangles=vertices[faces];fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained');counts={}
    for ax,offset,title in zip(axes,[140.,0.],['Hollow arm / X = 140 mm','Central plate / X = 0 mm']):
        delta=triangles[:,:,0]-offset;selected=triangles[(delta.min(1)<=0)&(delta.max(1)>=0)];segments=[]
        for tri in selected:
            points=[]
            for i,j in [(0,1),(1,2),(2,0)]:
                u,v=tri[i,0]-offset,tri[j,0]-offset
                if u==0:points.append(tri[i])
                if u*v<0:points.append(tri[i]-u/(v-u)*(tri[j]-tri[i]))
            if points:
                unique=np.unique(points,axis=0)
                if len(unique)==2:segments.append(unique[:,[1,2]])
                elif len(unique)==3:segments.extend(unique[[i,j]][:,[1,2]]for i,j in [(0,1),(1,2),(2,0)])
        if not segments:raise ValueError('Missing section')
        counts[str(offset)]=len(segments);ax.add_collection(LineCollection(segments,colors='#237a69',linewidths=1.6));ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('Y [mm]');ax.set_ylabel('Z [mm]');ax.set_title(title,loc='left',fontweight='bold');ax.grid(alpha=.15)
    fig.suptitle('993 R2 / WHERE CELLULAR REPLACEMENT CAN HELP',fontsize=18,fontweight='bold')
    fig.supxlabel('Actual full-mesh sections · nominal arm caps 1.5 mm / webs 1.61 mm · nominal central plate 8 mm\nExisting voids contain no solid mass to remove. No cellular candidate or mass saving is represented.',fontsize=10)
    args.output.mkdir(parents=True,exist_ok=True);image=args.output/'carrier-cellular-material-sections.png';fig.savefig(image,dpi=160);plt.close(fig)
    (args.output/'cellular-sections-provenance.json').write_text(json.dumps(dict(reference_sha256=digest,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),figure_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),section_segment_counts=counts,cellular_candidate_generated=False),indent=2)+'\n')


if __name__=='__main__':main()
