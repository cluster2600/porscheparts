#!/usr/bin/env python3
"""Plot native frequency samples and assumed excitation orders without mode tracking."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt


def render(source,output):
    if output.exists():raise FileExistsError(output)
    record=json.loads(source.read_text())
    if record['validated_campbell_diagram'] or record['mode_tracking_performed']:
        raise ValueError('This plot supports untracked frequency samples only')
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    for index,case in enumerate(record['cases']):
        table=case['coriolis_modes'] or case['prestressed_or_stationary_modes']
        ax.scatter([case['rpm_assumed']]*len(table),[v['frequency_hz'] for v in table],
                   color='#2456a6',marker='o',s=24,label='Native stationary / rotating Coriolis eigenvalues' if index==0 else None)
    speeds=np.linspace(0,max(c['rpm_assumed'] for c in record['cases']),101)
    for order in (1,11):
        ax.plot(speeds,speeds/60*order,'--',label=f'Assumed {order}× speed order')
    ax.set_xlabel('Assumed impeller speed (rpm)');ax.set_ylabel('Frequency (Hz)')
    ax.set_title('Fixed-bore frequency samples — no mode tracking or safe-speed inference')
    ax.grid(alpha=.2);ax.legend(loc='upper left');fig.savefig(output,dpi=180);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();render(a.source,a.output)
