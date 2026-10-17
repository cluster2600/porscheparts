"""Convergence figure for the rib-root fillet study; reads only the committed summary."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def render(summary,output):
    if output.exists():raise FileExistsError(output)
    r=json.loads(summary.read_text());sizes=r['root_sizes_mm']
    fig,axes=plt.subplots(1,2,figsize=(11,5.2),constrained_layout=True)
    for radius,colour in zip(['0.0','0.2','0.4'],['#c0392b','#1f77b4','#2e7d32']):
        s=r['summary'][radius];label='sharp corner' if radius=='0.0' else f'assumed fillet r = {radius} mm'
        axes[0].plot(sizes,s['root_nodal_von_mises_mpa'],'o-',color=colour,label=label+' (nodal)')
        axes[0].plot(sizes,s['root_integration_point_von_mises_mpa'],'s--',color=colour,alpha=.6,label=label+' (integration point)')
        axes[1].plot(sizes,[1000*u for u in s['maximum_displacement_mm']],'o-',color=colour,label=label)
    axes[0].axhline(r['assumed_threshold_mpa'],color='#555',lw=1,ls=':');axes[0].text(sizes[2],r['assumed_threshold_mpa']-2.5,'assumed 40 MPa screen, not an allowable',ha='center',fontsize=8,color='#555')
    for ax,title,unit in [(axes[0],'Rib-root von Mises peak at 3.75 bar','MPa'),(axes[1],'Maximum displacement','µm')]:
        ax.set_xscale('log');ax.set_xticks(sizes,[f'{v:g}' for v in sizes]);ax.minorticks_off();ax.invert_xaxis();ax.set_xlabel('element size at the rib roots (mm)');ax.set_ylabel(unit);ax.set_title(title,fontsize=10);ax.grid(alpha=.3)
    axes[0].legend(fontsize=7,ncol=2,loc='upper center',bbox_to_anchor=(.5,-.17));axes[1].legend(fontsize=7,ncol=1,loc='upper center',bbox_to_anchor=(.5,-.17))
    fig.suptitle('Plane-strain quarter section, four ribs, CalculiX 2.21 CPE8; assumed E and ν; not a pressure qualification',fontsize=9)
    fig.savefig(output,dpi=130,metadata={'Software':None});plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,default=ROOT/'derived/fillet-convergence/fillet-convergence.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.summary,a.output)
