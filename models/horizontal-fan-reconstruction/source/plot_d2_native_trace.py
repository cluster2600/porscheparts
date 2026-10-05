#!/usr/bin/env python3
"""Plot real current60 and extended40 native traces; no invented continuation."""
import argparse,json,re
from pathlib import Path
import numpy as np
from analyze_d2_result import native_table,sha


def plot(root,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,7));sources={};counts={}
    for label,display,color in [('current','Sortie actuelle : 60 itérations','#2467ad'),('extended','Sortie éloignée : 40 complètes','#d16b24')]:
        case=root/'cases'/label;tables={}
        for name in ['commonOutletFlux','commonPressureBandMean','rotorForces']:
            file=next((case/'postProcessing'/name).glob('*/*.dat'));sources[str(file.relative_to(root))]=sha(file);a=native_table(file);tables[name]=a[a[:,0]>=961]
        q=tables['commonOutletFlux'];p=tables['commonPressureBandMean'];t=tables['rotorForces'];end=int(q[-1,0]);counts[label]=len(q)
        axes[0,0].plot(q[:,0],q[:,1],color=color,label=display);axes[0,1].plot(p[:,0],p[:,1]*1.2,color=color,label=display);axes[1,0].plot(t[:,0],t[:,9]+t[:,12],color=color,label=display)
        file=case/'log.foamRun';sources[str(file.relative_to(root))]=sha(file);rows=[]
        for block in re.split(r'(?m)^Time = ',file.read_text())[1:]:
            it=int(float(re.match(r'([\d.eE+-]+)',block)[1]))
            if it<=end:rows.append((it,max(map(float,re.findall(r'Solving for p, Initial residual = ([\d.eE+-]+)',block)))))
        a=np.array(rows);axes[1,1].semilogy(a[:,0],a[:,1],color=color,label=display)
    for ax,label in zip(axes.flat,['Débit du plan commun [m³/s]','Pression de bande commune [Pa]','Couple fluide sur rotor [N·m]','Maximum initial p par itération [sans unité]']):
        ax.set_ylabel(label);ax.set_xlabel('Itération stationnaire');ax.grid(alpha=.2);ax.axvline(1000,color='#777777',ls=':',lw=1);ax.set_xlim(961,1020)
    axes[1,1].axhline(1e-4,color='#a31b25',ls='--',label='Seuil original p');axes[0,0].legend(fontsize=8);axes[1,1].legend(fontsize=8)
    fig.suptitle('D2 : traces natives — comparaison stationnaire inconclusive',fontsize=14)
    fig.text(.5,.02,'V2 identique, consistent yes ; branche prolongée arrêtée pendant 1001. Aucune donnée extrapolée après 1000.',ha='center',fontsize=9);fig.tight_layout(rect=[0,.05,1,.94]);fig.savefig(output,dpi=150);plt.close(fig)
    meta={'status':'native_completed_iteration_trace_only','script_sha256':sha(Path(__file__)),'source_sha256':sources,'completed_samples':counts,'PNG_sha256':sha(output),'missing_extended_iterations_not_drawn':True,'steady_iteration_axis_not_physical_time':True,'physical_validation_established':False};output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');return meta


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();plot(a.root,a.output)
