"""Plot retained conservative CFD-surface bounds; no flow or power quantities."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).resolve().parent
fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
for name,color in (('baseline','tab:blue'),('candidate','tab:orange')):
    report=json.loads((base/(name+'-profile-023.json')).read_text())
    rows=report['bands'];z=[.5*(r['z_low_mm']+r['z_high_mm']) for r in rows]
    axes[0].plot(z,[r['rotor_upper_mm'] for r in rows],color=color,linestyle='--',label=name+' : borne rotor')
    axes[0].plot(z,[r['stator_lower_mm'] for r in rows],color=color,label=name+' : borne stator')
    for profile in report['corridor']['open_profiles']:
        nodes=profile['nodes_z_radius_mm']
        axes[0].plot([n[0] for n in nodes],[n[1] for n in nodes],color=color,linestyle=':',label=name+' : interface ouverte')
    axes[1].plot(z,[r['gap_lower_mm'] for r in rows],color=color,label=name)
for ax in axes:
    ax.axvspan(-3.8,-3.5,color='red',alpha=.15,label='Fermeture arrière non résolue')
    ax.grid(alpha=.25);ax.legend(fontsize=8)
axes[0].set_ylabel('Rayon (mm)');axes[1].set_ylabel('Borne de séparation radiale (mm)')
axes[1].axhline(0,color='k',linewidth=.7);axes[1].set_xlabel('Coordonnée axiale z (mm)')
fig.suptitle('Surfaces CFD complètes — interface ouverte seulement, aucun écoulement validé')
fig.tight_layout();fig.savefig(base/'profiles-023.png',dpi=160)
