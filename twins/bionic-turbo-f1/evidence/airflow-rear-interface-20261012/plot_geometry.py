"""Plot the verified candidate and the source-covered rear witness wall."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
base=Path(__file__).resolve().parent
g=json.loads((base/'geometry-027.json').read_text());n=np.array(g['profile']['nodes_z_radius_mm'])
r=json.loads((base/'native-readback.json').read_text());a=g['variants']['baseline']['annulus']
fig,axes=plt.subplots(1,2,figsize=(11,4.7))
axes[0].plot(n[:,0],n[:,1],label='Interface commune à 128 secteurs')
axes[0].axvline(-3.75,color='black',linestyle=':',label='Plan stator vérifié')
axes[0].set(xlabel='z (mm)',ylabel='Rayon aux sommets (mm)',title='Profil à pente bornée')
axes[0].legend(fontsize=8);axes[0].grid(alpha=.3)
t=np.linspace(0,2*np.pi,1025)
for inner,outer,color,label in ((a['annulus_inner_radius_mm'],a['annulus_outer_radius_mm'],'#dddddd','Anneau couvert par les deux STL'),(*r['stator_radial_extent_mm'],'#5b9fd4','Étendue radiale de la paroi témoin')):
    x=np.concatenate((outer*np.cos(t),inner*np.cos(t[::-1])))
    y=np.concatenate((outer*np.sin(t),inner*np.sin(t[::-1])))
    axes[1].fill(x,y,color=color,label=label)
axes[1].plot(32*np.cos(t),32*np.sin(t),color='#173650',linewidth=.8,label='Terminaison MRF, R = 32 mm')
axes[1].set(xlabel='x (mm)',ylabel='y (mm)',title='Plan du stator, z = −3,75 mm',aspect='equal')
axes[1].legend(fontsize=7,loc='upper right');axes[1].grid(alpha=.2)
fig.suptitle('Candidat géométrique et témoin local — aucun écoulement du turbo validé')
fig.tight_layout();fig.savefig(base/'geometry-027.png',dpi=170)
