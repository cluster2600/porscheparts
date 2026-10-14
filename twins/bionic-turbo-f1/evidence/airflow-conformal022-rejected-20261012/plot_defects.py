import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).parent
rows=list(csv.DictReader((base/'defect-cell-centres.csv').open()))
points={name:np.array([[float(r[k])*1000 for k in ('x_m','y_m','z_m')] for r in rows if r['set']==name]) for name in ('concaveCells','underdeterminedCells')}
assert points['concaveCells'].shape==(6012,3) and points['underdeterminedCells'].shape==(18,3)
assert all(np.isfinite(p).all() for p in points.values())
report=json.loads((base/'interface-audit-022.json').read_text());worst=np.array([r['centre_m'] for r in report['worst_faces']])*1000
fig,ax=plt.subplots(1,2,figsize=(11,5),layout='constrained')
for name,label,colour,size in (('concaveCells','6 012 cellules concaves','#4578a4',5),('underdeterminedCells','18 faibles déterminants','#d62728',28)):
 p=points[name];ax[0].scatter(p[:,0],p[:,1],s=size,c=colour,alpha=.65,label=label)
 ax[1].scatter(np.linalg.norm(p[:,:2],axis=1),p[:,2],s=size,c=colour,alpha=.65)
theta=np.linspace(0,2*np.pi,361);ax[0].plot(38*np.cos(theta),38*np.sin(theta),'--',color='.3',lw=1,label='Interface nominale R = 38 mm')
ax[0].scatter(worst[:,0],worst[:,1],marker='x',s=35,c='#dd8500',label='20 faces : plus forts défauts de tangence')
ax[1].scatter(np.linalg.norm(worst[:,:2],axis=1),worst[:,2],marker='x',s=35,c='#dd8500')
ax[1].plot([38,38],[-4,33],'--',color='.3',lw=1)
ax[0].set(xlabel='X (mm)',ylabel='Y (mm)',title='Vue suivant l’axe de rotation',aspect='equal')
ax[1].set(xlabel='Distance à l’axe (mm)',ylabel='Z (mm)',title='Position radiale et axiale')
for a in ax:a.grid(alpha=.15)
fig.legend(*ax[0].get_legend_handles_labels(),loc='outside lower center',ncol=2,fontsize=9)
fig.suptitle('Cas 022 : maillage rejeté — aucun écoulement calculé',fontsize=14)
fig.savefig(base/'defects-022.png',dpi=180)
