#!/usr/bin/env python3
"""Plot only actual native60/40+20 traces; numerical iterations are not time."""
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_d2_result import native_table


def plot(previous,continuation,png,metadata):
    fig,axes=plt.subplots(2,2,figsize=(12,8));used={};counts={}
    colors=['#2063a8','#d67e19','#9235a4']
    for label,case,lo,hi,color in [('Témoin (60 pas)',previous/'current',961,1020,colors[0]),
                                  ('Prolongé (40 pas initiaux)',previous/'extended',961,1000,colors[1]),
                                  ('Prolongé (20 pas repris)',continuation,1001,1020,colors[2])]:
        key={'Témoin (60 pas)':'current60','Prolongé (40 pas initiaux)':'extended40','Prolongé (20 pas repris)':'extended20'}[label]
        tables={}
        for function in ['commonOutletFlux','commonPressureBandMean','rotorForces']:
            files=list((case/'postProcessing'/function).glob('*/*.dat'))
            if len(files)!=1:raise ValueError('One actual native table required')
            table=native_table(files[0]);table=table[(table[:,0]>=lo)&(table[:,0]<=hi)]
            if table[:,0].tolist()!=list(range(lo,hi+1)):raise ValueError('Contiguous native plotted window required')
            tables[function]=table;used[key+'/'+str(files[0].relative_to(case))]=hashlib.sha256(files[0].read_bytes()).hexdigest()
        log=case/'log.foamRun';text=log.read_text();points=[]
        for block in re.split(r'(?m)^Time = ',text)[1:]:
            if 'ExecutionTime = ' not in block:continue
            n=int(float(re.match(r'([0-9.eE+-]+)',block)[1]));values=[float(x) for x in re.findall(r'Solving for p, Initial residual = ([0-9.eE+-]+)',block)]
            if lo<=n<=hi:
                if not values:raise ValueError('Native pressure residual required')
                points.append((n,max(values)))
        if [n for n,v in points]!=list(range(lo,hi+1)):raise ValueError('Complete actual iteration blocks required')
        used[key+'/log.foamRun']=hashlib.sha256(log.read_bytes()).hexdigest();counts[key]=len(points)
        q,p,t=[tables[k] for k in ['commonOutletFlux','commonPressureBandMean','rotorForces']]
        axes[0,0].plot(q[:,0],q[:,1],color=color,label=label)
        axes[0,1].plot(p[:,0],p[:,1]*1.2,color=color,label=label)
        axes[1,0].plot(t[:,0],t[:,9]+t[:,12],color=color,label=label)
        axes[1,1].semilogy(*np.asarray(points).T,color=color,label=label)
    titles=['Débit orienté au plan commun (m³/s)','Pression statique moyenne de bande (Pa)',
            'Couple du fluide sur le rotor (N·m)','Maximum du résidu initial p par itération']
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title);ax.set_xlabel('Itération SIMPLE, sans dimension');ax.grid(alpha=.25)
        ax.axvline(1000.5,color='gray',linestyle=':',linewidth=1)
        ax.set_xlim(961,1020)
    axes[1,1].axhline(1e-4,color='#4b8051',linestyle='--',label='Seuil p gelé 10⁻⁴')
    axes[0,0].legend(fontsize=8);axes[1,1].legend(fontsize=8)
    fig.suptitle('D2 terminé : 60 / (40 + 20) : pression non stationnaire, comparaison inconclusive',fontsize=13)
    fig.text(.5,.012,'Traces natives exclusivement · reprise unique 1001–1020 · pas de temps physique ni gain airflow qualifié',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.95));fig.savefig(png,dpi=170);plt.close(fig)
    result={'status':'actual_native_completed_traces','completed_samples':counts,'source_sha256':used,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'PNG_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
            'no_extrapolation_or_synthetic_fields':True,'old_partial1001_excluded':True,
            'iterations_not_physical_time':True,'physical_validation_established':False,'airflow_improvement_proven':False}
    metadata.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['previous','continuation','png','metadata']:cli.add_argument(name,type=Path)
    args=cli.parse_args();plot(args.previous,args.continuation,args.png,args.metadata)
