#!/usr/bin/env python3
"""Render actual completed control and consistent-yes steady residual histories."""
import argparse,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(control,candidate,png,metadata):
    baseline=json.loads(control.read_text());result=json.loads(candidate.read_text())
    traces={'control':baseline['records']['control']['residual_trace_complete_iterations'],'consistent':result['residual_trace_complete_iterations']}
    fig,axes=plt.subplots(2,1,figsize=(10,6.5),sharex=True)
    for label,color in [('control','#2166ac'),('consistent','#d95f02')]:
        t=traces[label];caption=('consistent no (preserved control)' if label=='control' else 'consistent yes (one new case)')+'; '+str(len(t['iterations']))+' completed'
        axes[0].plot(t['iterations'],t['initial_max'],color=color,label=caption);axes[1].semilogy(t['iterations'],t['linear_final_max'],color=color)
    axes[0].axhline(1e-4,color='black',ls='--',lw=1,label='Unchanged initial p criterion: 1e-4')
    axes[1].axhline(1e-8,color='black',ls='--',lw=1,label='Unchanged linear absolute tolerance: 1e-8')
    for ax in axes:ax.axvspan(941,960,color='#e5e5e5',alpha=.65,zorder=-1);ax.grid(alpha=.25);ax.set_xlim(901,960)
    axes[0].set_ylabel('Maximum initial p residual\n(3 corrections per iteration)');axes[1].set_ylabel('Maximum final linear p residual\n(3 corrections per iteration)');axes[1].set_xlabel('Completed steady solver iteration (not physical time)')
    axes[0].legend(fontsize=8,loc='upper left');axes[1].legend(fontsize=8,loc='upper right')
    fig.suptitle('D1C native residuals; identical state at900 and MPI partition; fixed941-960 window')
    admission='Candidate passes frozen numerical gates; control does not.' if result['candidate_original_frozen_gates_passed'] else 'Candidate incomplete or not admitted; no completion inferred.'
    fig.text(.5,.01,admission+' Outlet reflux persists; no installed cooling validation.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.035,1,.94));fig.savefig(png,dpi=170);plt.close(fig)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    metadata.write_text(json.dumps({'status':'actual_completed_native_residual_samples_rendered','control_report_sha256':sha(control),'candidate_report_sha256':sha(candidate),'script_sha256':sha(Path(__file__)),'png_sha256':sha(png),'plotted_complete_samples':{k:len(t['iterations']) for k,t in traces.items()},'partial_tail_not_extrapolated':True,'physical_frequency_or_performance_established':False,'persistent_outlet_reflux_explicit':True},indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['control','candidate','png','metadata']:ap.add_argument(name,type=Path)
    a=ap.parse_args();plot(a.control,a.candidate,a.png,a.metadata)
