"""Plot actual paired known-solution repeats without treating them as carrier convergence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--replay',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();plan=json.loads((a.replay/'plan.json').read_text());sources=[a.replay/'plan.json'];rows=[]
    if (plan['iterations'],plan['threads'],plan['grid_dimension'])!=(500,8,20):raise ValueError('Original paired repeat fixture required')
    for mode in ['baseline','fixed']:
        stdout=a.replay/(mode+'-known-solution-test.stdout');receipt_path=a.replay/(mode+'-known-solution-test.json');receipt=json.loads(receipt_path.read_text());binary=a.replay/(mode+'-binary.json')
        if not receipt['process_reaped'] or sha(stdout)!=receipt['stdout_sha256']:raise ValueError('Actual reaped test receipt and output identity required')
        match=re.search(r'(\d+)/(\d+) iterations wrong, worst maxabs error ([0-9.e+-]+) \(tolerance ([0-9.e+-]+)\)',stdout.read_text())
        if not match:raise ValueError('Complete fixed-fixture summary required')
        bad,count=int(match[1]),int(match[2]);error,tolerance=float(match[3]),float(match[4])
        if count!=500 or tolerance!=.0001 or receipt['returncode']!=(1 if bad else 0) or (bad==0)!=(error<=tolerance):raise ValueError('Test result, fixed tolerance and exit code disagree')
        rows.append(dict(mode=mode,wrong=bad,total=count,worst_absolute_solution_error=error,fixed_tolerance=tolerance));sources +=[stdout,receipt_path,binary]
    if not rows[0]['wrong'] or rows[1]['wrong']:raise ValueError('Paired negative and corrected repeat controls required')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained');labels=['Original MT library','Corrected MT library'];colours=['#bd493e','#237a69'];counts=[r['wrong']for r in rows];errors=[r['worst_absolute_solution_error']for r in rows]
    axes[0].bar(labels,counts,color=colours,width=.55);axes[0].set_ylim(0,500);axes[0].set_ylabel('Wrong solutions out of 500');axes[0].set_title('Repeatability',loc='left',fontweight='bold')
    for index,count in enumerate(counts):axes[0].text(index,count+12,f'{count} / 500',ha='center',fontweight='bold')
    axes[1].bar(labels,errors,color=colours,width=.55);axes[1].set_yscale('log');axes[1].axhline(.0001,color='#323d43',linestyle='--',label='Fixed test tolerance: 0.0001');axes[1].set_ylabel('Worst absolute solution error [test units]');axes[1].set_title('Independent known solution',loc='left',fontweight='bold');axes[1].legend(loc='upper right',fontsize=9)
    for ax in axes:ax.grid(axis='y',alpha=.13);ax.set_axisbelow(True)
    fig.suptitle('SPOOLES / CONTROLLED SOURCE-PATCH REPLAY',fontsize=18,fontweight='bold');fig.supxlabel('Same Mac arm64 · 8 solver threads · 20 × 20 × 20 grid · 500 repeats per build\nLow-level numerical solver test. No carrier mesh-convergence or strength claim.',fontsize=10);a.output.mkdir(parents=True,exist_ok=False);image=a.output/'spooles-known-solution-replay.png';fig.savefig(image,dpi=160);plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(image),source_sha256={str(x):sha(x)for x in [*sources,Path(__file__)]},results=rows,carrier_convergence_demonstrated=False),indent=2)+'\n')


if __name__=='__main__':main()
