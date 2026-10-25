"""Actual paired native CPU/CUDA timings and errors on the retained R2 carrier."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--collected',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    a.output.mkdir(parents=True,exist_ok=True);reports=[json.loads((a.collected/f'results/carrier-{key}/report.json').read_text())for key in ['cpu','cuda']]
    if any(r['status']!='passed'for r in reports)or not reports[1]['gpu_validated']:raise ValueError('Completed paired CUDA validation required')
    if reports[0]['source_sha256']!=reports[1]['source_sha256']:raise ValueError('Paired source/input identities differ')
    with np.load(a.bundle)as data:expected=data['expected_distances_mm'].copy()
    errors=[]
    for key in ['cpu','cuda']:
        with np.load(a.collected/f'results/carrier-{key}/distances.npz')as data:errors.append(abs(data['distances_mm']-expected))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False,'text.color':'#172630','axes.labelcolor':'#172630'})
    fig,axes=plt.subplots(1,2,figsize=(14,6),layout='constrained');colours=['#829995','#d48445'];times=[r['timing']['warm_full_pipeline_seconds']for r in reports];medians=list(map(np.median,times));speedup=medians[0]/medians[1]
    ax=axes[0];bars=ax.bar(['Native CPU','RTX A2000 / CUDA'],medians,color=colours,width=.55)
    for i,values in enumerate(times):ax.scatter(np.full(len(values),i),values,s=25,color='#172630',zorder=3)
    ax.bar_label(bars,labels=[f'{value:.3f} s'for value in medians],padding=6);ax.set_ylim(0,max(medians)*1.23);ax.set_ylabel('Full warm pipeline [seconds]');ax.set_title(f'{speedup:.1f}× median speedup on this fixture',loc='left',fontweight='bold');ax.text(.02,.92,'Fresh BVH + buffers + transfers + query + readback\nFive warm repetitions; same algorithm and inputs',transform=ax.transAxes,va='top',fontsize=10)
    ax=axes[1];bins=np.linspace(-10,-3.5,50)
    for name,error,colour in zip(['CPU','CUDA'],errors,colours):ax.hist(np.log10(np.maximum(error,1e-10)),bins=bins,histtype='step',linewidth=2,color=colour,label=f'{name}: max {error.max():.3g} mm')
    ax.axvline(-4,color='#b14b3b',linestyle='--',label='Fixed 0.0001 mm limit');ax.set_xlabel('log₁₀ absolute distance error [mm]');ax.set_ylabel('Query count');ax.set_title('Independent double-precision libigl oracle',loc='left',fontweight='bold');ax.legend(fontsize=10,loc='upper left');ax.set_yscale('log');ax.grid(axis='y',alpha=.15)
    fig.suptitle('993 CARRIER  /  REAL CUDA VALIDATION',fontweight='bold',fontsize=20);fig.supxlabel('1,218,348 triangles · 65,536 fixed queries · Warp 1.18.0 · zero query misses',fontsize=12);fig.savefig(a.output/'carrier-warp-cpu-cuda-validation.png',dpi=160);plt.close(fig)
    provenance=dict(source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.bundle,Path(__file__),*[a.collected/f'results/carrier-{k}/report.json'for k in ['cpu','cuda']]]},median_full_pipeline_seconds=dict(cpu=float(medians[0]),cuda=float(medians[1])),measured_fixture_speedup=float(speedup),universal_speedup_claimed=False,versions=dict(numpy=np.__version__,matplotlib=matplotlib.__version__))
    (a.output/'warp-figure-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(provenance['median_full_pipeline_seconds']))

if __name__=='__main__':main()
