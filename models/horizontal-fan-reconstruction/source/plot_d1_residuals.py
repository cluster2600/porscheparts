#!/usr/bin/env python3
"""Render completed native D1 residual samples; never invent the interrupted tail."""
import argparse,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(report,png,metadata):
    r=json.loads(report.read_text());fig,axes=plt.subplots(2,1,figsize=(10,6.5),sharex=True)
    for label,color in [('control','#2166ac'),('absolute','#d95f02')]:
        trace=r['records'][label]['residual_trace_complete_iterations'];caption='relTol = 0.01 : 60 completed' if label=='control' else 'relTol = 0 : 29 completed; interrupted at 930'
        axes[0].plot(trace['iterations'],trace['initial_max'],color=color,label=caption)
        axes[1].semilogy(trace['iterations'],trace['linear_final_max'],color=color)
    axes[0].axhline(1e-4,color='black',ls='--',lw=1,label='Frozen initial-pressure criterion: 1e-4')
    axes[1].axhline(1e-8,color='black',ls='--',lw=1,label='Linear absolute tolerance: 1e-8 (unchanged)')
    for ax in axes:
        ax.axvspan(901,920,color='#e5e5e5',alpha=.65,zorder=-1);ax.grid(alpha=.25);ax.set_xlim(901,960)
    axes[0].set_ylabel('Maximum initial p residual\n(3 corrections per iteration)');axes[1].set_ylabel('Maximum final linear p residual\n(3 corrections per iteration)');axes[1].set_xlabel('Completed steady solver iteration (not physical time)')
    axes[0].legend(fontsize=8,loc='upper left');axes[1].legend(fontsize=8,loc='upper right')
    fig.suptitle('D1 native residuals — shared initial checkpoint 900; shaded prospective paired window 901–920')
    fig.text(.5,.01,'Control not admitted on pressure; relTol = 0 target 960 incomplete. No physical-frequency or performance conclusion.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.035,1,.94));fig.savefig(png,dpi=170);plt.close(fig)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    metadata.write_text(json.dumps({'status':'actual_completed_native_residual_samples_rendered','source_report_sha256':sha(report),'script_sha256':sha(Path(__file__)),'png_sha256':sha(png),'plotted_complete_samples':{'control':60,'absolute':29},'interrupted930_not_plotted':True,'partial_tail_not_extrapolated':True,'physical_frequency_or_performance_established':False},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['report','png','metadata']:p.add_argument(name,type=Path)
    a=p.parse_args();plot(a.report,a.png,a.metadata)
