"""Plot accepted full-field observables; process success is never convergence."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--comparison',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=json.loads(args.comparison.read_text());rows=report['rows']
    if len(rows)<2:raise ValueError('At least two accepted full fields required')
    args.output.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained');labels=[r['label']for r in rows];colours=['#829995','#d48445','#697ea5'][:len(rows)]
    for ax,key,title,unit in zip(axes,['displacement_max_mm','compliance_Nmm','global_peak_VM_MPa'],['Maximum displacement','Compliance','Global integration-point peak'],['mm','N·mm','MPa']):
        bars=ax.bar(labels,[r[key]for r in rows],color=colours);ax.bar_label(bars,fmt='%.2f',padding=4);ax.set_ylim(0,max(r[key]for r in rows)*1.2);ax.set_title(title,loc='left',fontweight='bold');ax.set_ylabel(unit);ax.grid(axis='y',alpha=.15)
    fig.suptitle('993 CARRIER / SPATIAL REFINEMENT',fontsize=20,fontweight='bold');fig.supxlabel('Same continuous tractions and support patches · dense elastic reference · convergence not established',fontsize=11)
    name='carrier-spatial-comparison.png';fig.savefig(args.output/name,dpi=160);plt.close(fig)
    (args.output/'mechanics-figure-provenance.json').write_text(json.dumps(dict(comparison_sha256=hashlib.sha256(args.comparison.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),figure_sha256=hashlib.sha256((args.output/name).read_bytes()).hexdigest(),convergence_demonstrated=report['convergence_demonstrated']),indent=2)+'\n')


if __name__=='__main__':main()
