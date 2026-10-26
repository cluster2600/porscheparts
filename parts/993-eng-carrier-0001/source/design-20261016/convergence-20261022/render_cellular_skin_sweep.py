"""Plot conditional mass and baseline energy for explicitly separate skin scenarios."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--assessment',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=json.loads(a.assessment.read_text());contract=a.assessment.with_name('contract.json');sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    if r['status']!='conditional_skin_sensitivity_screen_completed'or r['geometry_changed']or r['changed_geometry_stiffness_predicted']or r['printability_qualified']or sha(contract)!=r['contract_sha256']or a.output.exists():raise ValueError('Fresh actual conditional study required')
    rows=r['rows'];x=[v['skin_mm']for v in rows];mass=[1000*v['conditional_saving_kg']for v in rows];energy=[100*v['T10_baseline_energy_fraction']for v in rows]
    if len(x)<2 or sorted(set(x))!=x or any(v<0 for v in mass+energy)or r['original_skin_mm']not in x:raise ValueError('Ordered complete nonnegative scenarios required')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False});fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    for ax,y,title,unit,colour in zip(axes,[mass,energy],['Conditional mass saving','Baseline T10 energy in selected core'],['Mass saving [g]','Original dense-part elastic energy [%]'],['#237a69','#b57535']):
        ax.plot(x,y,'o-',color=colour);ax.axvline(r['original_skin_mm'],color='#69777c',linestyle='--',label='Original screen: 1.5 mm');ax.set_xlabel('Assumed retained analysis skin [mm]');ax.set_ylabel(unit);ax.set_title(title,loc='left',fontweight='bold');ax.set_ylim(0,max(y)*1.2);ax.grid(axis='y',alpha=.13);ax.legend(fontsize=9)
        for xx,yy in zip(x,y):ax.annotate(f'{yy:.2f}',(xx,yy),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
    fig.suptitle('993 CARRIER / CELLULAR CORE DESIGN SENSITIVITY',fontsize=18,fontweight='bold');fig.supxlabel('Fixed 10 mm bore keepout · relative density scenario 0.40 · same admitted CUDA geometry distances\nNo cellular carrier generated. Baseline energy fractions are not predicted stiffness losses or printable-wall limits.',fontsize=10);a.output.mkdir(parents=True);image=a.output/'cellular-skin-sensitivity.png';fig.savefig(image,dpi=160);plt.close(fig);(a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(image),source_sha256={str(f):sha(f)for f in [a.assessment,contract,Path(__file__)]},geometry_changed=False),indent=2)+'\n')


if __name__=='__main__':main()
