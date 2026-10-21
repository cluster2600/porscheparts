"""Plot full-cell quality distributions for the actual two TetGen checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--first',type=Path,required=True);p.add_argument('--refined',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(13,6),facecolor='#f4f7fb')
    fig.subplots_adjust(left=.07,right=.97,bottom=.20,top=.70,wspace=.24)
    for path,label,color in [(a.first,'Original · 927,734 cells','#647b91'),(a.refined,'Interior refinement · 1,163,760 cells','#237961')]:
        with np.load(path,allow_pickle=False)as data:
            for ax,key,title,xlabel in zip(axes,['mean_ratio','Jacobian_condition_2norm'],['Shape quality · larger is better','Local Jacobian conditioning · smaller is better'],['Mean ratio (regular tetrahedron = 1)','Condition number (2-norm)']):
                values=np.sort(data[key]);ax.plot(values,100*np.arange(1,len(values)+1)/len(values),label=label,color=color,linewidth=2)
                ax.set_xscale('log');ax.set_xlabel(xlabel);ax.set_ylabel('All cells at or below value (%)');ax.set_ylim(0,100);ax.set_title(title,fontsize=12,pad=15);ax.grid(alpha=.15);ax.set_facecolor('#f4f7fb')
    axes[0].legend(loc='upper left',fontsize=9,frameon=False)
    fig.text(.07,.88,'993 CARRIER  /  INTERIOR MESH REFINEMENT',fontsize=20,weight='bold',color='#1d334b')
    fig.text(.07,.80,'Same 603,152 boundary triangles and coordinates · complete empirical distributions',fontsize=12,color='#4c6078')
    fig.text(.07,.07,'All tetrahedra included. Quality diagnostics do not establish convergence or strength.',fontsize=11,color='#4c6078')
    target=a.output/'tetgen-quality-comparison.png';fig.savefig(target,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    (a.output/'provenance.json').write_text(json.dumps(dict(input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.first,a.refined,Path(__file__)]},output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),numpy=np.__version__,matplotlib=matplotlib.__version__,scope='Full empirical CDFs, no sampling or acceptance threshold'),indent=2)+'\n')

if __name__=='__main__':main()
